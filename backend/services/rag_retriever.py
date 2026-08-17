"""
rag_retriever — Módulo RAG vetorial genérico para o FraLib.

Usa pgvector + embeddings Anthropic para indexar e buscar documentos
por similaridade semântica. Integra com observability.py para indexar
automaticamente pipeline_traces ao completar.

Uso:
    from backend.services.rag_retriever import init_rag_table, add_document, search

    init_rag_table(engine)
    add_document(engine, tenant_id=1, content="Pipeline Builder falhou...",
                 metadata={"tipo": "falha", "step": "builder"}, source="pipeline_trace")
    results = search(engine, tenant_id=1, query="Builder timeout", top_k=5)
"""


import json
import logging
from typing import Any

from sqlalchemy import text
from backend.core.database import engine

logger = logging.getLogger("rag_retriever")

# Dimensão do modelo text-embedding-3-small
_EMBEDDING_DIM: int = 1536
_TABLE_NAME: str = "rag_documents"
_HNSW_M: int = 16
_HNSW_EF_CONSTRUCTION: int = 64


# ===== EMBEDDING =====

def _get_embedding(text_str: str) -> list[float] | None:
    """Gera embedding via Anthropic text-embedding-3-small.

    Usa ia_manager.pick_key('anthropic') para round-robin de chaves.
    Retorna None se falhar (best-effort, não crasha pipeline).
    """
    if not text_str or not text_str.strip():
        return None

    # Truncar para limite do modelo (8K tokens ≈ 6K chars para pt-BR)
    text_truncated = text_str[:8000]

    try:
        from services.ia_manager import pick_key
        key, base_url, _ = pick_key("anthropic")
    except Exception as exc:
        logger.error("[RAG] ia_manager indisponível: %s", exc)
        key, base_url = None, None

    if not key:
        logger.warning("[RAG] sem API key Anthropic para embeddings")
        return None

    url = f"{base_url}/v1/embeddings"

    try:
        import httpx
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "text-embedding-3-small",
                "input": text_truncated,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("data", [{}])[0].get("embedding")

        if embedding and len(embedding) == _EMBEDDING_DIM:
            return embedding

        logger.warning(
            "[RAG] embedding inesperado (dim=%s)",
            len(embedding) if embedding else 0,
        )
        return None

    except Exception as exc:
        logger.error("[RAG] falha ao gerar embedding: %s", exc)
        return None


# ===== DDL =====

def init_rag_table(engine_=None) -> None:
    """Cria tabela rag_documents + índice HNSW se não existirem.

    Best-effort: catch exceptions, não crasha se pgvector indisponível.
    """
    eng = engine_ or engine
    try:
        with eng.connect() as conn:
            # Habilitar extensão pgvector
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            except Exception as ext_err:
                logger.warning("[RAG] pgvector indisponível: %s", ext_err)

            # Tabela principal
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({_EMBEDDING_DIM}),
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    source VARCHAR(100) DEFAULT 'unknown',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # HNSW index para cosine similarity (mais rápido que IVFFlat em datasets pequenos/médios)
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_{_TABLE_NAME}_hnsw
                ON {_TABLE_NAME}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = {_HNSW_M}, ef_construction = {_HNSW_EF_CONSTRUCTION})
            """))

            # Índice para filtrar por tenant_id
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_{_TABLE_NAME}_tenant
                ON {_TABLE_NAME} (tenant_id, created_at DESC)
            """))

            conn.commit()
            logger.info("[RAG] tabela %s inicializada", _TABLE_NAME)

    except Exception as exc:
        logger.error("[RAG] init_rag_table falhou: %s", exc)


# ===== CRUD =====

def add_document(
    engine_=None,
    *,
    tenant_id: int,
    content: str,
    metadata: dict[str, Any] | None = None,
    source: str = "unknown",
) -> int | None:
    """Gera embedding do conteúdo e insere no vetor.

    Args:
        engine_: SQLAlchemy engine (usa o global se None).
        tenant_id: ID do tenant para isolamento multi-tenant.
        content: Texto do documento a indexar.
        metadata: Metadados opcionais (tipo, step, score, etc).
        source: Origem do documento (pipeline_trace, failure, etc).

    Returns:
        ID do documento inserido, ou None se falhar (best-effort).
    """
    if not content or not content.strip():
        return None

    embedding = _get_embedding(content)
    if embedding is None:
        return None

    eng = engine_ or engine
    try:
        with eng.connect() as conn:
            row = conn.execute(text(f"""
                INSERT INTO {_TABLE_NAME}
                    (tenant_id, content, embedding, metadata, source)
                VALUES
                    (:tid, :content, CAST(:emb AS vector({_EMBEDDING_DIM})), CAST(:meta AS JSONB), :source)
                RETURNING id
            """), {
                "tid": tenant_id,
                "content": content[:5000],
                "emb": str(embedding),
                "meta": json.dumps(metadata or {}, ensure_ascii=False),
                "source": source[:100],
            }).fetchone()
            conn.commit()
            doc_id = int(row[0]) if row else None
            logger.debug("[RAG] documento inserido: id=%s source=%s", doc_id, source)
            return doc_id

    except Exception as exc:
        logger.error("[RAG] add_document falhou: %s", exc)
        return None


# ===== SEARCH =====

def search(
    engine_=None,
    *,
    tenant_id: int,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.6,
) -> list[dict[str, Any]]:
    """Busca documentos semanticamente similares à query.

    Gera embedding da query → cosine similarity → retorna top_k documentos.

    Args:
        engine_: SQLAlchemy engine (usa o global se None).
        tenant_id: ID do tenant para filtrar resultados.
        query: Texto da busca (será embeddado).
        top_k: Quantidade máxima de resultados (1-20).
        min_similarity: Similaridade mínima (0-1) para filtrar resultados ruins.

    Returns:
        Lista de dicts com: id, content, metadata, source, similarity.
        Lista vazia se falhar (best-effort).
    """
    embedding = _get_embedding(query)
    if embedding is None:
        return []

    eng = engine_ or engine
    top_k_clamped = max(1, min(int(top_k), 20))

    try:
        with eng.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT
                    id,
                    content,
                    metadata,
                    source,
                    created_at,
                    1 - (embedding <=> CAST(:emb AS vector({_EMBEDDING_DIM}))) AS similarity
                FROM {_TABLE_NAME}
                WHERE tenant_id = :tid
                  AND 1 - (embedding <=> CAST(:emb AS vector({_EMBEDDING_DIM}))) >= :min_sim
                ORDER BY embedding <=> CAST(:emb AS vector({_EMBEDDING_DIM}))
                LIMIT :lim
            """), {
                "emb": str(embedding),
                "tid": tenant_id,
                "min_sim": min_similarity,
                "lim": top_k_clamped,
            }).fetchall()

        results = []
        for r in rows:
            meta = r[2]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}

            results.append({
                "id": r[0],
                "content": r[1],
                "metadata": meta,
                "source": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "similarity": round(float(r[5]), 4),
            })

        logger.debug("[RAG] search retornou %s resultados para tenant=%s", len(results), tenant_id)
        return results

    except Exception as exc:
        logger.error("[RAG] search falhou: %s", exc)
        return []


# ===== HELPERS =====

def delete_document(engine_=None, *, doc_id: int) -> bool:
    """Remove documento por ID. Retorna True se removido."""
    eng = engine_ or engine
    try:
        with eng.connect() as conn:
            row = conn.execute(text(f"""
                DELETE FROM {_TABLE_NAME} WHERE id = :did RETURNING id
            """), {"did": doc_id}).fetchone()
            conn.commit()
            return row is not None
    except Exception as exc:
        logger.error("[RAG] delete_document falhou: %s", exc)
        return False


def purge_tenant_documents(engine_=None, *, tenant_id: int, older_than_days: int = 90) -> int:
    """Remove documentos antigos de um tenant. Retorna quantidade removida."""
    eng = engine_ or engine
    try:
        with eng.connect() as conn:
            row = conn.execute(text(f"""
                DELETE FROM {_TABLE_NAME}
                WHERE tenant_id = :tid
                  AND created_at < NOW() - INTERVAL ':d days'
            """), {"tid": tenant_id, "d": max(1, int(older_than_days))}).fetchone()
            conn.commit()
            return row[0] if row else 0
    except Exception as exc:
        logger.error("[RAG] purge_tenant_documents falhou: %s", exc)
        return 0
