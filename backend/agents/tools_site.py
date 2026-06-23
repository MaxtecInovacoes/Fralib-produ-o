"""Tools dinâmicas para agentes do pipeline de site (Sprint 2).

5 tools disponíveis para Nicho/Arquiteto/Validador/OpenUI:
- retrieve_similar_briefings(nicho, top_k=5)
- retrieve_top_templates(subnicho)
- check_site_quality(slug)
- save_pipeline_lesson(lesson, score, confianca)
- get_nicho_history(nicho, limit=10)

Padrão de invocação: TOOLS_DISPATCH + call_tool(). As tools NAO sao
chamadas pelo LLM (nao temos Claude Agent SDK runtime aqui). O
orquestrador chama a tool ANTES do LLM call e injeta resultado no
user prompt, mantendo backward-compat total.

Reuso:
- CoreMemory.get_para_agente (backend/agent_memory.py:152)
- WarmMemory.buscar (backend/agent_memory.py:189)
- SUB_NICHO_TEMPLATES (backend/agents/agente_variacao.py)
- persist_lesson_with_score (backend/agents/memory_hook_site.py)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# TOOL 1: retrieve_similar_briefings
# ════════════════════════════════════════════════════════════════════

def retrieve_similar_briefings(nicho: str, top_k: int = 5) -> list[dict]:
    """Recupera briefings anteriores do mesmo nicho (Warm memory).

    Args:
        nicho: segmento do lead (academia_crossfit, nutricionista_esportiva, etc).
        top_k: quantos briefings retornar (default 5, max 10).

    Returns:
        Lista de dicts [{agente, conteudo, confianca, vezes_usado, fonte}].
        Lista vazia se nicho nunca foi visto (cold start).
    """
    if not nicho:
        return []
    top_k = max(1, min(10, top_k))
    try:
        from backend.agent_memory import WarmMemory, MemoryEntry
        warm = WarmMemory()
        entries: list[MemoryEntry] = warm.buscar(nicho=nicho, tipo="agent_lesson", top_k=top_k)
        return [
            {
                "agente": e.agente,
                "conteudo": e.conteudo,
                "confianca": e.confianca,
                "vezes_usado": e.vezes_usado,
                "fonte": e.fonte,
            }
            for e in entries
        ]
    except Exception as e:
        logger.warning(f"[tools_site] retrieve_similar_briefings falhou: {e}")
        return []


# ════════════════════════════════════════════════════════════════════
# TOOL 2: retrieve_top_templates
# ════════════════════════════════════════════════════════════════════

def retrieve_top_templates(subnicho: str) -> dict:
    """Recupera template canonico de SUB_NICHO_TEMPLATES para o subnicho.

    Args:
        subnicho: subnicho canonico (nutricionista_esportiva, academia_crossfit, etc).

    Returns:
        Dict com chaves: template_estrutura, template_hero, template_prova_social,
        template_cta, template_faq, ordem_das_secoes, angulo_de_comunicacao.
        Dict vazio {} se subnicho nao mapeado.
    """
    if not subnicho:
        return {}
    try:
        from backend.agents.agente_variacao import SUB_NICHO_TEMPLATES
        if subnicho in SUB_NICHO_TEMPLATES:
            return dict(SUB_NICHO_TEMPLATES[subnicho])
        return {}
    except Exception as e:
        logger.warning(f"[tools_site] retrieve_top_templates falhou: {e}")
        return {}


# ════════════════════════════════════════════════════════════════════
# TOOL 3: check_site_quality
# ════════════════════════════════════════════════════════════════════

def check_site_quality(slug: str) -> dict:
    """Recupera metricas de qualidade de site ja publicado.

    Args:
        slug: identificador do site (ex: academia-crossfit-vila-mariana).

    Returns:
        Dict {score, problemas, lgpd_ok, gerado_em}. Vazio se site nao encontrado.
        NAO chama LLM - apenas consulta dados persistidos.
    """
    if not slug:
        return {}
    try:
        from pathlib import Path
        # Procura relatorio de QA no diretorio do site
        sites_root = Path("/var/www/fralib/sites")
        if not sites_root.exists():
            sites_root = Path("C:/fralib/sites")
        for tenant_dir in sites_root.iterdir() if sites_root.exists() else []:
            site_dir = tenant_dir / slug
            if not site_dir.is_dir():
                continue
            qa_file = site_dir / "_qa_result.json"
            if qa_file.exists():
                import json
                data = json.loads(qa_file.read_text(encoding="utf-8"))
                return {
                    "score": float(data.get("score", 0.0)),
                    "problemas": data.get("problemas", []),
                    "lgpd_ok": data.get("lgpd_ok", False),
                    "gerado_em": data.get("gerado_em", ""),
                }
        return {}
    except Exception as e:
        logger.warning(f"[tools_site] check_site_quality falhou: {e}")
        return {}


# ════════════════════════════════════════════════════════════════════
# TOOL 4: save_pipeline_lesson (write - requer lock, ja tratado)
# ════════════════════════════════════════════════════════════════════

def save_pipeline_lesson(
    lesson: str,
    score: float = 0.0,
    confianca_base: float = 0.7,
    agente: str = "agente_nicho",
    nicho: str = "default",
) -> bool:
    """Persiste lesson em Warm memory com score do validador como multiplicador.

    Args:
        lesson: texto da lesson aprendida (curto, ex: "USP funciona: bioimpedancia + plano alimentar").
        score: 0-10 do validador LLM-as-judge. Multiplicador:
               >=7.0 -> 1.2x, >=5.0 -> 1.0x, <5.0 -> 0.5x.
        confianca_base: confianca inicial (default 0.7).
        agente: nome do agente que gerou a lesson.
        nicho: segmento do lead.

    Returns:
        True se persistiu, False caso contrario.
    """
    if not lesson or not nicho:
        return False
    try:
        from backend.agents.memory_hook_site import persist_lesson_with_score
        persist_lesson_with_score(
            agente=agente,
            nicho=nicho,
            conteudo=lesson,
            validador_score=float(score),
            confianca_base=confianca_base,
        )
        return True
    except Exception as e:
        logger.warning(f"[tools_site] save_pipeline_lesson falhou: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
# TOOL 5: get_nicho_history (read-only Cold memory + Warm core)
# ════════════════════════════════════════════════════════════════════

def get_nicho_history(nicho: str, limit: int = 10) -> list[dict]:
    """Recupera historico consolidado do nicho (Core + Warm + Cold).

    Args:
        nicho: segmento do lead.
        limit: maximo de entries (default 10).

    Returns:
        Lista de dicts ordenados por data (mais recente primeiro).
    """
    if not nicho:
        return []
    limit = max(1, min(20, limit))
    history: list[dict] = []
    try:
        # Core: lessons globais
        from backend.agent_memory import CoreMemory
        core = CoreMemory()
        core_entries = [
            {
                "tipo": "core",
                "agente": e.agente,
                "conteudo": e.conteudo,
                "confianca": e.confianca,
                "data": e.atualizado_em,
            }
            for e in core.entries
            if e.agente and nicho.lower() in (e.conteudo or "").lower()
        ]
        history.extend(core_entries[:limit])

        # Warm: lessons por nicho
        from backend.agent_memory import WarmMemory
        warm = WarmMemory()
        warm_entries = warm.buscar(nicho=nicho, top_k=limit)
        history.extend([
            {
                "tipo": "warm",
                "agente": e.agente,
                "conteudo": e.conteudo,
                "confianca": e.confianca,
                "data": e.atualizado_em,
            }
            for e in warm_entries
        ])
    except Exception as e:
        logger.warning(f"[tools_site] get_nicho_history falhou: {e}")

    # Ordena por data (mais recente primeiro) e dedup por conteudo
    seen: set[str] = set()
    unique: list[dict] = []
    for item in sorted(history, key=lambda x: x.get("data", ""), reverse=True):
        if item["conteudo"] not in seen:
            seen.add(item["conteudo"])
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


# ════════════════════════════════════════════════════════════════════
# DISPATCH + INVOCACAO
# ════════════════════════════════════════════════════════════════════

TOOLS_DISPATCH: dict[str, Any] = {
    "retrieve_similar_briefings": retrieve_similar_briefings,
    "retrieve_top_templates": retrieve_top_templates,
    "check_site_quality": check_site_quality,
    "save_pipeline_lesson": save_pipeline_lesson,
    "get_nicho_history": get_nicho_history,
}


SUPPORTED_TOOLS: tuple[str, ...] = tuple(TOOLS_DISPATCH.keys())


def call_tool(name: str, **kwargs: Any) -> Any:
    """Invoca tool pelo nome.

    Args:
        name: nome da tool (uma de SUPPORTED_TOOLS).
        **kwargs: argumentos passados para a tool.

    Returns:
        Resultado da tool. Levanta ValueError se tool nao existe.
    """
    fn = TOOLS_DISPATCH.get(name)
    if fn is None:
        raise ValueError(f"Tool '{name}' nao existe. Tools: {SUPPORTED_TOOLS}")
    return fn(**kwargs)


def list_tools() -> list[str]:
    """Retorna lista de tools disponiveis."""
    return list(SUPPORTED_TOOLS)
