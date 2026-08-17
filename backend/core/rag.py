"""
rag.py — RAG vetorial com pgvector.

Indexa e busca semanticamente:
  - leads (qualificação: contexto de leads similares)
  - pipeline_failures (busca de erros passados parecidos)

Embeddings via LLM (text-embedding-3-small). Modelo configurável por env.
Tabelas de embeddings vivem no schema public (extensão pgvector).

Uso:
    from backend.core.rag import index_lead, search_leads, index_failure, search_failures

    # Indexar um lead (chamar após qualificação Caio)
    index_lead(lead_id="abc", tenant_id=1, text="Restaurante japonês em Curitiba",
               metadata={"tier": "PREMIUM", "segmento": "gastronomia"})

    # Buscar leads similares
    results = search_leads("restaurante japonês em Curitiba", tenant_id=1, limit=5)

    # Indexar erro de pipeline
    index_failure(lead_id="abc", tenant_id=1,
                  text="OpenUI timeout após 300s — Builder chunk 2/4 falhou",
                  step_name="builder")

    # Buscar erros similares (troubleshooting)
    errors = search_failures("OpenUI Builder timeout", limit=10)
"""


import logging
import os
from typing import Any

from backend.core.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("fralib.rag")

_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
_EMBEDDING_DIM = 1536  # text-embedding-3-small


# ===== EMBEDDING (LLM call) =====

def _get_embedding(text_str: str) -> list[float] | None:
    """Gera embedding via LLM. Retorna None se falhar (best-effort)."""
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("DEPLOYFLOW_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.anthropic.com"
    if not api_key:
        logger.warning("RAG: sem API key para embeddings")
        return None
    try:
        import httpx
        # Anthropic embeddings endpoint
        if "anthropic" in base_url.lower() or base_url == "https://api.anthropic.com":
            url = f"{base_url}/v1/embeddings"
        else:
            url = f"{base_url}/v1/embeddings"

        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": _EMBEDDING_MODEL, "input": text_str[:8000]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("data", [{}])[0].get("embedding")
        if embedding and len(embedding) == _EMBEDDING_DIM:
            return embedding
        logger.warning("RAG: embedding inesperado (dim=%s)", len(embedding) if embedding else 0)
        return None
    except Exception as exc:
        logger.error("RAG: falha ao gerar embedding: %s", exc)
        return None


# ===== LEADS RAG =====

def index_lead(
    lead_id: str,
    tenant_id: int,
    text: str,
    metadata: dict | None = None,
) -> int | None:
    """Indexa um lead no vetor. Chame após qualificação Caio. Retorna embedding_id."""
    if not text or not text.strip():
        return None
    db = SessionLocal()
    try:
        # Verificar se já indexado
        existing = db.execute(text("""
            SELECT id FROM lead_embeddings WHERE lead_id = :lid AND tenant_id = :tid
        """), {"lid": lead_id, "tid": tenant_id}).fetchone()
        if existing:
            # Re-index (upsert)
            db.execute(text("""
                DELETE FROM lead_embeddings WHERE lead_id = :lid AND tenant_id = :tid
            """), {"lid": lead_id, "tid": tenant_id})

        import json as _json
        embedding = _get_embedding(text)
        if embedding is None:
            return None

        row = db.execute(text("""
            INSERT INTO lead_embeddings (lead_id, tenant_id, embedding, texto, metadata)
            VALUES (:lid, :tid, CAST(:emb AS vector), :txt, CAST(:meta AS JSONB))
            RETURNING id
        """), {
            "lid": lead_id,
            "tid": tenant_id,
            "emb": str(embedding),
            "txt": text[:4000],
            "meta": _json.dumps(metadata or {}),
        }).fetchone()
        db.commit()
        return int(row[0]) if row else None
    except Exception as exc:
        db.rollback()
        logger.error("index_lead() falhou: %s", exc)
        return None
    finally:
        db.close()


def search_leads(
    query: str,
    tenant_id: int | None = None,
    limit: int = 10,
    min_similarity: float = 0.7,
) -> list[dict[str, Any]]:
    """Busca leads semanticamente similares. Retorna lista de dicts."""
    db = SessionLocal()
    try:
        embedding = _get_embedding(query)
        if embedding is None:
            return []

        tid_filter = "AND tenant_id = :tid" if tenant_id else ""
        params = {"emb": str(embedding), "lim": max(1, min(int(limit), 50)), "min_sim": min_similarity}
        if tenant_id:
            params["tid"] = tenant_id

        rows = db.execute(text(f"""
            SELECT le.id, le.lead_id, le.tenant_id, le.texto, le.metadata,
                   1 - (le.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM lead_embeddings le
            WHERE 1 - (le.embedding <=> CAST(:emb AS vector)) >= :min_sim
              {tid_filter}
            ORDER BY le.embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """), params).fetchall()

        return [
            {
                "id": r[0],
                "lead_id": r[1],
                "tenant_id": r[2],
                "texto": r[3],
                "metadata": r[4] if isinstance(r[4], dict) else None,
                "similarity": round(float(r[5]), 4),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("search_leads() falhou: %s", exc)
        return []
    finally:
        db.close()


# ===== FAILURES RAG =====

def index_failure(
    lead_id: str,
    tenant_id: int,
    text: str,
    step_name: str,
    metadata: dict | None = None,
) -> int | None:
    """Indexa um erro de pipeline para busca semântica futura (troubleshooting)."""
    if not text or not text.strip():
        return None
    db = SessionLocal()
    try:
        embedding = _get_embedding(f"[{step_name}] {text}")
        if embedding is None:
            return None

        row = db.execute(text("""
            INSERT INTO failure_embeddings (lead_id, tenant_id, step_name, embedding, texto, metadata)
            VALUES (:lid, :tid, :step, CAST(:emb AS vector), :txt, CAST(:meta AS JSONB))
            RETURNING id
        """), {
            "lid": lead_id,
            "tid": tenant_id,
            "step": step_name[:50],
            "emb": str(embedding),
            "txt": text[:4000],
            "meta": _json.dumps(metadata or {"step": step_name}),
        }).fetchone()
        db.commit()
        return int(row[0]) if row else None
    except Exception as exc:
        db.rollback()
        logger.error("index_failure() falhou: %s", exc)
        return None
    finally:
        db.close()


def search_failures(
    query: str,
    step_name: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Busca erros de pipeline semanticamente similares (troubleshooting)."""
    db = SessionLocal()
    try:
        embedding = _get_embedding(query)
        if embedding is None:
            return []

        step_filter = "AND step_name = :step" if step_name else ""
        params = {"emb": str(embedding), "lim": max(1, min(int(limit), 50))}
        if step_name:
            params["step"] = step_name

        rows = db.execute(text(f"""
            SELECT fe.id, fe.lead_id, fe.tenant_id, fe.step_name, fe.texto, fe.metadata,
                   1 - (fe.embedding <=> CAST(:emb AS vector)) AS similarity
            FROM failure_embeddings fe
            WHERE 1 - (fe.embedding <=> CAST(:emb AS vector)) >= 0.6
              {step_filter}
            ORDER BY fe.embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """), params).fetchall()

        return [
            {
                "id": r[0],
                "lead_id": r[1],
                "tenant_id": r[2],
                "step_name": r[3],
                "texto": r[4],
                "metadata": r[5] if isinstance(r[5], dict) else None,
                "similarity": round(float(r[6]), 4),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("search_failures() falhou: %s", exc)
        return []
    finally:
        db.close()


# ===== INDEX MANAGEMENT =====

def purge_old_embeddings(older_than_days: int = 90) -> dict[str, int]:
    """Remove embeddings antigos (leads + failures)."""
    db = SessionLocal()
    result = {"lead": 0, "failure": 0}
    try:
        r1 = db.execute(text("""
            DELETE FROM lead_embeddings
            WHERE criado_em < NOW() - INTERVAL ':d days'
        """), {"d": max(1, int(older_than_days))})
        r2 = db.execute(text("""
            DELETE FROM failure_embeddings
            WHERE criado_em < NOW() - INTERVAL ':d days'
        """), {"d": max(1, int(older_than_days))})
        db.commit()
        result["lead"] = r1.rowcount
        result["failure"] = r2.rowcount
    except Exception as exc:
        db.rollback()
        logger.error("purge_old_embeddings() falhou: %s", exc)
    finally:
        db.close()
    return result
