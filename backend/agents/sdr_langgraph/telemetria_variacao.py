"""Telemetria de Variacao para o SDR (Franz) - Sprint 3C.

5 funcoes para rastrear qual template/conversao converteu melhor por nicho:
- record_variacao_outcome: persiste resultado de uma conversa
- get_variacao_stats: stats agregados por template (total, converteram, taxa)
- rank_variacoes_by_conversion: ranking por taxa de conversao desc
- get_best_variacao_for_nicho: melhor template para o nicho (ou None se cold start)
- format_variacao_stats_for_prompt: injecao no LLM prompt

Reuso:
- learning._tenant_dir (backend/agents/sdr_langgraph/learning.py:45)
- tools_sdr._conversations_path (pattern append-only)
- retrieval_semantico._save_index (atomic write pattern)

Opt-in: FRALIB_SDR_USE_TELEMETRIA=1 (default False = backward-compat).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# STORE: memory/u<int>/variacoes_telemetria.json (append-only)
# ════════════════════════════════════════════════════════════════════

MAX_ENTRIES_PER_FILE = 10000  # cap defensivo contra explosao


def _telemetria_path(user_id: int) -> Path:
    """Path do log de telemetria por user_id."""
    base = Path(__file__).resolve().parents[2] / "memory" / f"u{int(user_id)}"
    base.mkdir(parents=True, exist_ok=True)
    return base / "variacoes_telemetria.jsonl"


def _load_entries(user_id: int) -> list[dict]:
    """Carrega todas as entries do JSONL (cold start: [])."""
    path = _telemetria_path(user_id)
    if not path.is_file():
        return []
    try:
        entries: list[dict] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except Exception as e:
        logger.warning(f"[telemetria_variacao] _load_entries falhou: {e}")
        return []


def _save_entries(user_id: int, entries: list[dict]) -> bool:
    """Persiste entries (atomic write, cap automatico)."""
    if len(entries) > MAX_ENTRIES_PER_FILE:
        # Rota: mantem as N mais recentes
        entries = entries[-MAX_ENTRIES_PER_FILE:]
    path = _telemetria_path(user_id)
    try:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
        return True
    except Exception as e:
        logger.warning(f"[telemetria_variacao] _save_entries falhou: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
# TOOL 1: record_variacao_outcome
# ════════════════════════════════════════════════════════════════════

def record_variacao_outcome(
    user_id: int,
    nicho: str,
    template_id: str,
    converteu: bool,
    duracao_turnos: int = 0,
    lead_id: str = "",
    lead_score: float = 0.0,
    variacao_meta: Optional[dict] = None,
) -> dict:
    """Registra outcome de uma conversa SDR (qual template converteu).

    Args:
        user_id: tenant id.
        nicho: segmento canonico (academia_crossfit, etc).
        template_id: id do template de variacao usado (ex: "v_energetico_manha").
        converteu: True se lead virou cliente, False caso contrario.
        duracao_turnos: quantos turnos a conversa durou.
        lead_id: id do lead (rastreio).
        lead_score: score Caio do lead (0-100).
        variacao_meta: dict opcional com extras (tom, angulo, etc).

    Returns:
        Dict {recorded: bool, total_entries: int, niche_total: int}.
    """
    if not user_id or not nicho or not template_id:
        return {"recorded": False, "reason": "missing_required_fields"}
    entry = {
        "nicho": nicho,
        "template_id": template_id,
        "converteu": bool(converteu),
        "duracao_turnos": int(duracao_turnos),
        "lead_id": lead_id or "",
        "lead_score": float(lead_score),
        "variacao_meta": variacao_meta or {},
        "ts": __import__("datetime").datetime.now().isoformat(),
    }
    entries = _load_entries(user_id)
    entries.append(entry)
    ok = _save_entries(user_id, entries)
    niche_total = sum(1 for e in entries if e.get("nicho") == nicho)
    return {
        "recorded": ok,
        "total_entries": len(entries) if ok else 0,
        "niche_total": niche_total,
    }


# ════════════════════════════════════════════════════════════════════
# TOOL 2: get_variacao_stats
# ════════════════════════════════════════════════════════════════════

def get_variacao_stats(
    user_id: int,
    nicho: str,
    template_id: Optional[str] = None,
) -> list[dict]:
    """Stats agregados por template (nicho inteiro ou template especifico).

    Args:
        user_id: tenant id.
        nicho: segmento canonico.
        template_id: se fornecido, retorna so esse template. Senao, todos.

    Returns:
        Lista de dicts {template_id, total, converteram, taxa_conversao,
        duracao_media, score_medio}. Vazio se user_id=0 ou nicho sem dados.
    """
    if not user_id or not nicho:
        return []
    entries = _load_entries(user_id)
    filtered = [e for e in entries if e.get("nicho") == nicho]
    if template_id:
        filtered = [e for e in filtered if e.get("template_id") == template_id]
    if not filtered:
        return []
    # Agrupa por template_id
    by_template: dict[str, list[dict]] = {}
    for e in filtered:
        tid = e.get("template_id", "unknown")
        by_template.setdefault(tid, []).append(e)
    stats: list[dict] = []
    for tid, items in by_template.items():
        total = len(items)
        converteram = sum(1 for i in items if i.get("converteu"))
        taxa = converteram / total if total > 0 else 0.0
        duracao_media = sum(int(i.get("duracao_turnos", 0)) for i in items) / total
        score_medio = sum(float(i.get("lead_score", 0)) for i in items) / total
        stats.append({
            "template_id": tid,
            "total": total,
            "converteram": converteram,
            "taxa_conversao": round(taxa, 4),
            "duracao_media": round(duracao_media, 2),
            "score_medio": round(score_medio, 2),
        })
    return stats


# ════════════════════════════════════════════════════════════════════
# TOOL 3: rank_variacoes_by_conversion
# ════════════════════════════════════════════════════════════════════

def rank_variacoes_by_conversion(
    user_id: int,
    nicho: str,
    min_amostra: int = 3,
) -> list[dict]:
    """Ranking de templates por taxa de conversao (desc).

    Args:
        user_id: tenant id.
        nicho: segmento canonico.
        min_amostra: minimo de conversas por template para entrar no ranking.
            Templates com < min_amostra sao excluidos (estatistica fraca).

    Returns:
        Lista ordenada por taxa_conversao desc: [{template_id, total,
        converteram, taxa_conversao, ...}]. Vazio se nenhum template
        atinge min_amostra (cold start).
    """
    stats = get_variacao_stats(user_id, nicho)
    qualifying = [s for s in stats if s["total"] >= min_amostra]
    qualifying.sort(key=lambda x: x["taxa_conversao"], reverse=True)
    return qualifying


# ════════════════════════════════════════════════════════════════════
# TOOL 4: get_best_variacao_for_nicho
# ════════════════════════════════════════════════════════════════════

def get_best_variacao_for_nicho(
    user_id: int,
    nicho: str,
    min_amostra: int = 3,
) -> Optional[str]:
    """Retorna template_id com melhor taxa de conversao para o nicho.

    Args:
        user_id: tenant id.
        nicho: segmento canonico.
        min_amostra: minimo de conversas para considerar confiavel.

    Returns:
        template_id (str) ou None se cold start (sem templates qualificados).
    """
    ranking = rank_variacoes_by_conversion(user_id, nicho, min_amostra=min_amostra)
    if not ranking:
        return None
    return ranking[0]["template_id"]


# ════════════════════════════════════════════════════════════════════
# TOOL 5: format_variacao_stats_for_prompt
# ════════════════════════════════════════════════════════════════════

def format_variacao_stats_for_prompt(stats: list[dict]) -> str:
    """Formata ranking para injecao no LLM prompt.

    Args:
        stats: lista retornada por rank_variacoes_by_conversion ou
            get_variacao_stats.

    Returns:
        String formatada (vazia se stats vazio).
    """
    if not stats:
        return ""
    lines = ["TELEMETRIA DE VARIACOES (historico real deste nicho):"]
    for i, s in enumerate(stats[:5], 1):
        taxa_pct = s["taxa_conversao"] * 100
        lines.append(
            f"  {i}. {s['template_id']}: {s['converteram']}/{s['total']} "
            f"({taxa_pct:.0f}%) | duracao_media={s['duracao_media']:.1f} turnos"
        )
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# TOOLS_DISPATCH + call_tool + list_tools (padrao Sprint 3A/3B)
# ════════════════════════════════════════════════════════════════════

TOOLS_DISPATCH: dict[str, callable] = {
    "record_variacao_outcome": record_variacao_outcome,
    "get_variacao_stats": get_variacao_stats,
    "rank_variacoes_by_conversion": rank_variacoes_by_conversion,
    "get_best_variacao_for_nicho": get_best_variacao_for_nicho,
    "format_variacao_stats_for_prompt": format_variacao_stats_for_prompt,
}


def call_tool(name: str, **kwargs) -> Any:
    """Dispatcher: invoca tool por nome. Retorna None se tool nao existe."""
    fn = TOOLS_DISPATCH.get(name)
    if fn is None:
        logger.warning(f"[telemetria_variacao] call_tool: tool '{name}' nao encontrada")
        return None
    try:
        return fn(**kwargs)
    except Exception as e:
        logger.warning(f"[telemetria_variacao] call_tool '{name}' falhou: {e}")
        return None


def list_tools() -> list[str]:
    """Lista nomes das 5 tools disponiveis."""
    return list(TOOLS_DISPATCH.keys())
