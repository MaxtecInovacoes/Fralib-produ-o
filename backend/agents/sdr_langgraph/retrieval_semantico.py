"""Retrieval semântico para o SDR (Franz) — Sprint 3B.

5 funções para indexar/buscar conversas SDR por similaridade SEMANTICA
(nao só keyword/JSONL tail como Sprint 3A). Reuso total do Sprint 3A:

- retrieve_similar_conversations: ja existe em tools_sdr.py (keyword/tail)
- save_sdr_lesson: ja existe (multiplicador 1.5x/0.3x)
- sdr_conversations_<nicho>.jsonl: ja gravado por record_conversation_outcome
- learning._tenant_dir: path base

Esta camada ADICIONA:
1. _embed(text) -> list[float]: vetor 64-d (TF-IDF mini OU sentence-transformers)
2. index_conversation(user_id, nicho, lead_id, text, metadata): adiciona embedding
3. search_similar_conversations(user_id, nicho, query, top_k=5): cosine similarity
4. _load_index / _save_index: persiste em memory/u<int>/sdr_embeddings_<nicho>.json
5. _cosine(a, b): similaridade cosseno entre 2 vetores

Backend de embedding (lazy import):
- Se sentence-transformers + torch disponiveis: usa modelo multilingual (384d)
- Senao: TF-IDF mini com vocabulario canonico dos 8 nichos (64d, deterministico)

Opt-in: FRALIB_SDR_USE_RAG=1 (default False = backward-compat total).
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# BACKEND: TF-IDF mini (fallback deterministico, 64-d)
# ════════════════════════════════════════════════════════════════════

# 64 termos canonicos que discriminam nicho/objecao/gatilho no SDR.
# Saos os high-signal tokens de sdr_playbook.py + objecoes_comuns.
# DEDUP aplicado (dict.fromkeys preserva ordem, remove duplicatas).
_RAW_VOCAB: list[str] = [
    # Nicho
    "academia", "crossfit", "musculacao", "personal", "aluno",
    "nutricionista", "nutricao", "atleta", "consultorio", "dieta",
    "barbearia", "barba", "corte", "agendamento", "vip",
    "restaurante", "cardapio", "delivery", "almoco", "jantar",
    "clinica", "estetica", "procedimento", "antes_depois", "anamnese",
    "advocacia", "trabalhista", "processo", "rescisao", "honorario",
    "ecommerce", "loja", "produto", "frete", "marketplace",
    # Tom/gatilho
    "familia", "resultado", "comunidade", "premium", "agilidade",
    "garantia", "depoimento", "parcelamento", "desconto", "frete_gratis",
    # Objecoes
    "caro", "tempo", "instagram", "site", "marketing",
    "marketplace", "consulta", "marcar", "orcamento",
    # Quantificadores
    "rapido", "minuto", "mes", "semana", "dia", "horario",
    "pico", "tarde", "manha", "noite", "sabado", "domingo",
]
TFIDF_VOCAB: list[str] = list(dict.fromkeys(_RAW_VOCAB))  # dedup preserving order
EMBED_DIM = len(TFIDF_VOCAB)  # dinamico (atualmente 64, mas flexivel a mudancas)


def _embed_tfidf(text: str) -> list[float]:
    """Embedding deterministico 64-d baseado em TF (term frequency).

    Nao usa IDF aqui (sem corpus estatistico). Pesos sao uniformes.
    Para RAG SDR com 5-50 conversas por nicho, TF puro ja funciona.
    """
    if not text:
        return [0.0] * EMBED_DIM
    tokens = re.findall(r"\w+", text.lower())
    vec = [0.0] * EMBED_DIM
    for tok in tokens:
        # Match exato
        if tok in TFIDF_VOCAB:
            vec[TFIDF_VOCAB.index(tok)] += 1.0
            continue
        # Match parcial (substring): se token contem termo canonico
        for i, term in enumerate(TFIDF_VOCAB):
            if term in tok or tok in term:
                vec[i] += 0.5
                break
    # Normaliza L2 para cosine similarity estavel
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


# ════════════════════════════════════════════════════════════════════
# BACKEND: sentence-transformers (opt-in, se instalado)
# ════════════════════════════════════════════════════════════════════

_ST_MODEL = None
_ST_BACKEND_TRIED = False
_ST_AVAILABLE = False


def _try_load_sentence_transformers() -> bool:
    """Tenta carregar modelo multilingual mini (uma vez por processo)."""
    global _ST_MODEL, _ST_BACKEND_TRIED, _ST_AVAILABLE
    if _ST_BACKEND_TRIED:
        return _ST_AVAILABLE
    _ST_BACKEND_TRIED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        # Modelo mini (80MB), multilingual, suficiente para PT-BR nichos
        _ST_MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        _ST_AVAILABLE = True
        logger.info("[retrieval_semantico] sentence-transformers carregado OK")
    except Exception as e:
        logger.info(f"[retrieval_semantico] sentence-transformers indisponivel: {e}")
        _ST_AVAILABLE = False
    return _ST_AVAILABLE


def _embed_st(text: str) -> list[float]:
    """Embedding via sentence-transformers (384d)."""
    if _ST_MODEL is None:
        return _embed_tfidf(text)  # fallback
    vec = _ST_MODEL.encode(text or "", convert_to_numpy=True)
    return vec.tolist()


def _embed(text: str) -> list[float]:
    """Embedding canonico: sentence-transformers se disponivel, senao TF-IDF."""
    if _try_load_sentence_transformers():
        return _embed_st(text)
    return _embed_tfidf(text)


def current_backend() -> str:
    """Retorna nome do backend ativo ('sentence-transformers' ou 'tfidf')."""
    return "sentence-transformers" if _try_load_sentence_transformers() else "tfidf"


# ════════════════════════════════════════════════════════════════════
# INDEX STORE: memory/u<int>/sdr_embeddings_<nicho>.json
# ════════════════════════════════════════════════════════════════════

def _embeddings_path(user_id: int, nicho: str) -> Path:
    """Path do indice de embeddings por nicho."""
    base = Path(__file__).resolve().parents[2] / "memory" / f"u{int(user_id)}"
    base.mkdir(parents=True, exist_ok=True)
    safe_nicho = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(nicho or "default"))[:60]
    return base / f"sdr_embeddings_{safe_nicho}.json"


def _load_index(user_id: int, nicho: str) -> list[dict]:
    """Carrega indice de embeddings (lista de {lead_id, text, vec, metadata})."""
    path = _embeddings_path(user_id, nicho)
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[retrieval_semantico] _load_index falhou: {e}")
        return []


def _save_index(user_id: int, nicho: str, index: list[dict]) -> bool:
    """Persiste indice de embeddings (atomic write)."""
    path = _embeddings_path(user_id, nicho)
    try:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        logger.warning(f"[retrieval_semantico] _save_index falhou: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
# COSINE SIMILARITY
# ════════════════════════════════════════════════════════════════════

def _cosine(a: list[float], b: list[float]) -> float:
    """Cosseno entre 2 vetores. Retorna 0.0 se algum vetor for zero/None."""
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        # Se dimensoes diferentes, trunca para o menor (defensivo)
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ════════════════════════════════════════════════════════════════════
# TOOL 1: index_conversation
# ════════════════════════════════════════════════════════════════════

def index_conversation(
    user_id: int,
    nicho: str,
    lead_id: str,
    text: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Indexa uma conversa SDR (lead_id + text + embedding) para retrieval futuro.

    Args:
        user_id: tenant id.
        nicho: segmento canonico.
        lead_id: id do lead (chave unica do index).
        text: snippet da conversa (max 1000 chars).
        metadata: dict opcional (converteu, intent_final, duracao_turnos, etc).

    Returns:
        Dict {indexed: bool, backend: str, dim: int, total_in_index: int}.
        {indexed: False} se user_id=0, text vazio ou lead_id vazio.
    """
    if not user_id or not text or not text.strip() or not lead_id:
        return {"indexed": False, "reason": "missing_required_fields"}
    text_clean = text.strip()[:1000]
    backend = current_backend()
    vec = _embed(text_clean)
    index = _load_index(user_id, nicho)
    # Dedup por lead_id (atualiza se ja existe)
    existing_idx = None
    for i, entry in enumerate(index):
        if entry.get("lead_id") == lead_id:
            existing_idx = i
            break
    entry = {
        "lead_id": lead_id,
        "text": text_clean,
        "vec": vec,
        "metadata": metadata or {},
        "ts": __import__("datetime").datetime.now().isoformat(),
        "backend": backend,
    }
    if existing_idx is not None:
        index[existing_idx] = entry
    else:
        index.append(entry)
    ok = _save_index(user_id, nicho, index)
    return {
        "indexed": ok,
        "backend": backend,
        "dim": len(vec),
        "total_in_index": len(index) if ok else 0,
    }


# ════════════════════════════════════════════════════════════════════
# TOOL 2: search_similar_conversations
# ════════════════════════════════════════════════════════════════════

def search_similar_conversations(
    user_id: int,
    nicho: str,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict]:
    """Busca conversas similares por cosseno (semantica) no nicho.

    Args:
        user_id: tenant id.
        nicho: segmento canonico.
        query: texto da query (mensagem do lead ou contexto).
        top_k: quantas conversas retornar (default 5, max 10).
        min_score: similaridade minima (0.0 a 1.0, default 0).

    Returns:
        Lista ordenada por score desc: [{lead_id, text, metadata, score}].
        Lista vazia se user_id=0, query vazia ou indice vazio.
    """
    if not user_id or not query or not query.strip():
        return []
    top_k = max(1, min(10, top_k))
    min_score = max(0.0, min(1.0, min_score))
    index = _load_index(user_id, nicho)
    if not index:
        return []
    query_vec = _embed(query.strip()[:1000])
    scored: list[dict] = []
    for entry in index:
        vec = entry.get("vec", [])
        if not vec:
            continue
        score = _cosine(query_vec, vec)
        if score < min_score:
            continue
        scored.append({
            "lead_id": entry.get("lead_id", ""),
            "text": entry.get("text", "")[:200],
            "metadata": entry.get("metadata", {}),
            "score": round(score, 4),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ════════════════════════════════════════════════════════════════════
# TOOL 3: reindex_from_jsonl (migra conversas do Sprint 3A para RAG)
# ════════════════════════════════════════════════════════════════════

def reindex_from_jsonl(user_id: int, nicho: str) -> dict:
    """Reindexa todas as conversas do JSONL do Sprint 3A no indice semantico.

    Idempotente: re-rodar atualiza embeddings (nao duplica).
    Usar 1x na primeira vez que FRALIB_SDR_USE_RAG=1 for ativado.
    """
    if not user_id:
        return {"reindexed": 0, "reason": "missing_user_id"}
    try:
        # Reusa path do Sprint 3A
        from .tools_sdr import _conversations_path

        path = _conversations_path(user_id, nicho)
        if not path.is_file():
            return {"reindexed": 0, "reason": "no_jsonl_yet"}
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    lead_id = entry.get("lead_id", "")
                    snippet = entry.get("snippet", "")
                    if not lead_id or not snippet:
                        continue
                    index_conversation(
                        user_id, nicho, lead_id, snippet,
                        metadata={
                            "converteu": entry.get("converteu", False),
                            "intent_final": entry.get("intent_final", ""),
                            "duracao_turnos": entry.get("duracao_turnos", 0),
                            "tom_usado": entry.get("tom_usado", ""),
                            "gatilho_conversao": entry.get("gatilho_conversao", ""),
                        },
                    )
                    count += 1
                except json.JSONDecodeError:
                    continue
        return {"reindexed": count, "backend": current_backend()}
    except Exception as e:
        logger.warning(f"[retrieval_semantico] reindex_from_jsonl falhou: {e}")
        return {"reindexed": 0, "reason": f"error: {e}"}


# ════════════════════════════════════════════════════════════════════
# TOOL 4: format_search_results_for_prompt
# ════════════════════════════════════════════════════════════════════

def format_search_results_for_prompt(results: list[dict]) -> str:
    """Formata resultados de busca semantica para injecao no prompt.

    Args:
        results: lista retornada por search_similar_conversations.

    Returns:
        String formatada (vazia se results vazio).
    """
    if not results:
        return ""
    lines = ["CONVERSAS SIMILARES (RAG semantico — score cosseno):"]
    for i, r in enumerate(results[:3], 1):
        score = r.get("score", 0.0)
        meta = r.get("metadata", {})
        status = "CONVERTEU" if meta.get("converteu") else "perdeu"
        gatilho = meta.get("gatilho_conversao") or "(sem gatilho)"
        snippet = r.get("text", "")[:120]
        lines.append(
            f"  {i}. score={score:.2f} | {status} | gatilho: {gatilho}"
        )
        if snippet:
            lines.append(f"     \"{snippet}\"")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# TOOLS_DISPATCH + call_tool + list_tools (padrao Sprint 3A)
# ════════════════════════════════════════════════════════════════════

TOOLS_DISPATCH: dict[str, callable] = {
    "index_conversation": index_conversation,
    "search_similar_conversations": search_similar_conversations,
    "reindex_from_jsonl": reindex_from_jsonl,
    "format_search_results_for_prompt": format_search_results_for_prompt,
    "current_backend": current_backend,
}


def call_tool(name: str, **kwargs) -> Any:
    """Dispatcher: invoca tool por nome. Retorna None se tool nao existe."""
    fn = TOOLS_DISPATCH.get(name)
    if fn is None:
        logger.warning(f"[retrieval_semantico] call_tool: tool '{name}' nao encontrada")
        return None
    try:
        return fn(**kwargs)
    except Exception as e:
        logger.warning(f"[retrieval_semantico] call_tool '{name}' falhou: {e}")
        return None


def list_tools() -> list[str]:
    """Lista nomes das 5 tools disponiveis."""
    return list(TOOLS_DISPATCH.keys())
