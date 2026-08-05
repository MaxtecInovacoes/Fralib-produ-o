"""
Constantes, definições e helpers de fase do pipeline FraLib.
"""

from dataclasses import dataclass, field
from typing import Any, List

# ─── DEFINIÇÕES DE FASES ────────────────────────────────────────────────────

FASE_1_HUNTER = 1
FASE_2_CURADORIA = 2
FASE_3_JINA = 3
FASE_4_INTELIGENCIA = 4
FASE_5_FOTOS = 5
FASE_6_NICHO = 6
FASE_7_VARIACAO = 7
FASE_8_ARQUITETO = 8
FASE_9_BUILDER = 9
FASE_10_DEPLOY = 10
FASE_11_FRANZ = 11

TOTAL_FASES = 11

FASE_LABELS = {
    FASE_1_HUNTER: "Buscando leads...",
    FASE_2_CURADORIA: "Qualificando lead...",
    FASE_3_JINA: "Pesquisa de mercado...",
    FASE_4_INTELIGENCIA: "Analisando concorrência...",
    FASE_5_FOTOS: "Baixando fotos...",
    FASE_6_NICHO: "Analisando nicho...",
    FASE_7_VARIACAO: "Definindo variação estrutural...",
    FASE_8_ARQUITETO: "Arquitetando site...",
    FASE_9_BUILDER: "Gerando site no Builder...",
    FASE_10_DEPLOY: "Publicando site...",
    FASE_11_FRANZ: "Enviando contato...",
}

FASE_NAMES = {
    FASE_1_HUNTER: "hunter_kw",
    FASE_2_CURADORIA: "caio",
    FASE_3_JINA: "jina",
    FASE_4_INTELIGENCIA: "inteligencia",
    FASE_5_FOTOS: "fotos",
    FASE_6_NICHO: "agente_nicho",
    FASE_7_VARIACAO: "agente_variacao",
    FASE_8_ARQUITETO: "arquiteto_mestre",
    FASE_9_BUILDER: "builder_renderer",
    FASE_10_DEPLOY: "deploy",
    FASE_11_FRANZ: "franz",
}

# ─── DATACLASS DE ESTADO ────────────────────────────────────────────────────

@dataclass
class FraLibState:
    """Estado central do pipeline FraLib."""
    segmento: str = ""
    cidade: str = ""
    pipeline_id: str = ""
    run_id: str = ""
    tenant_id: int = 0
    lead_raw_data: dict = field(default_factory=dict)
    lead_obj: Any = None
    lead_id: str = ""
    lead_nome: str = ""
    lead_slug: str = ""
    qualificacao_caio: Any = None
    alex_result: Any = None
    jina_insights: str = ""
    briefing_theo: str = ""
    prd_arquiteto: Any = None
    html_sections: List[str] = field(default_factory=list)
    html_final: str = ""
    builder_output_dir: str = ""
    builder_manifest_path: str = ""
    liz_aprovado: bool = False
    liz_score: int = 0
    site_url: str = ""
    keyword_research: str = ""


# ─── HELPERS DE FASE ────────────────────────────────────────────────────────

def _pipeline_phase_key_impl(fase_num: int, label: str = "") -> str:
    """Gera chave de fase para persistência no DB."""
    fase_name = FASE_NAMES.get(fase_num, f"fase_{fase_num}")
    if label:
        return f"{fase_name}:{label}"
    return fase_name


def _progress_payload(fase_num: int, label: str = "") -> dict:
    """Gera payload de progresso SSE."""
    phase_key = _pipeline_phase_key_impl(fase_num, label)
    return {
        "type": "progress",
        "fase": fase_num,
        "phase": phase_key,
        "total": TOTAL_FASES,
        "label": label,
        "percent": round(min(fase_num, TOTAL_FASES) / TOTAL_FASES * 100),
    }


def _calcular_percentual_fase(fase_atual: int) -> int:
    """Calcula percentual de progresso baseado na fase atual."""
    return round(min(fase_atual, TOTAL_FASES) / TOTAL_FASES * 100)


# ─── HELPERS DE ESTADO ──────────────────────────────────────────────────────

def sincronizar_segmento_state(state: FraLibState, segmento: str) -> None:
    """Sincroniza segmento no state e objetos relacionados."""
    if not segmento:
        return
    state.segmento = segmento
    if getattr(state, "lead_raw_data", None):
        state.lead_raw_data["segmento"] = segmento
    try:
        if state.lead_obj and getattr(state.lead_obj, "lead", None):
            state.lead_obj.lead.segmento = segmento
    except Exception:
        pass


def aplicar_segmento_inferido(state: FraLibState, log_func=None, inferir_segmento_por_nome=None) -> None:
    """Aplica segmento inferido pelo nome do lead."""
    if inferir_segmento_por_nome is None:
        from agents.pipeline_identity import inferir_segmento_por_nome

    atual = state.segmento or getattr(getattr(state.lead_obj, "lead", None), "segmento", "")
    inferido = inferir_segmento_por_nome(state.lead_nome, atual)
    if inferido and inferido.lower() != (atual or "").lower():
        if log_func:
            log_func(
                f"  Segmento refinado: {atual} -> {inferido} (nome do lead)",
                "info",
            )
    sincronizar_segmento_state(state, inferido or atual)


# ─── VALIDAÇÃO DE OUTPUT ────────────────────────────────────────────────────

def validar_output(output: Any, min_chars: int = 50, must_contain: list = None) -> bool:
    """Valida que output não está truncado/quebrado antes de salvar."""
    if not output:
        return False
    text = output if isinstance(output, str) else str(output)
    if len(text) < min_chars:
        return False
    # Detectar resposta truncada (termina no meio de frase sem pontuação final)
    if must_contain:
        for marker in must_contain:
            if marker not in text:
                return False
    return True


def validar_html_completo(html: str, min_chars: int = 2000) -> bool:
    """Verifica se HTML está completo (tem tag de fechamento)."""
    if not html or len(html) < min_chars:
        return False
    return "</html>" in html.lower()


# ─── CONSTANTES DE TIER/SCORE ───────────────────────────────────────────────

SCORE_MINIMO_DEFAULT = 45
TIER_REJEITADO = "REJEITADO"
TIER_STANDARD = "STANDARD"
QUALIFICACAO_QUENTE = "QUENTE"
QUALIFICACAO_FRIO = "FRIO"

# ─── LOOKUP DE ERROS POR TIPO ───────────────────────────────────────────────

ERROR_TYPE_MAPPING = {
    "RATE_LIMIT": "RATE_LIMIT",
    "NO_LEADS": "NO_LEADS",
    "DEPLOY_FAIL": "DEPLOY_FAIL",
    "SCRAPER_FAIL": "SCRAPER_FAIL",
    "LLM_FAIL": "LLM_FAIL",
}

def detectar_tipo_erro(e: Exception) -> str:
    """Detecta tipo de erro para emissão de SSE tipado."""
    err_str = str(e).lower()
    if "rate" in err_str or "limit" in err_str:
        return "RATE_LIMIT"
    if any(x in err_str for x in ["nenhum lead", "no leads", "sem leads"]):
        return "NO_LEADS"
    if any(x in err_str for x in ["deploy", "nginx", "filesystem"]):
        return "DEPLOY_FAIL"
    if any(x in err_str for x in ["scraper", "playwright", "google maps"]):
        return "SCRAPER_FAIL"
    return "LLM_FAIL"
