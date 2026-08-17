"""
safe_lead_qualificado.py
========================
Helper defensivo para criar LeadQualificado sem quebrar pipeline.

Resolve o bug onde lead_obj recebia string/None em vez de LeadRaw,
causando 'Input should be a valid dictionary' em Pydantic.

Uso:
    from backend.utils.safe_lead_qualificado import safe_qualificar

    state.lead_obj = safe_qualificar(lead_raw, lead_dict, log_fn=_log)
"""

from typing import Any, Optional

from backend.utils.agente1_hunter_v2 import LeadQualificado, LeadRaw


def safe_qualificar(
    lead_raw: Any,
    lead_dict: Optional[dict] = None,
    log_fn: Optional[callable] = None,
) -> LeadQualificado:
    """Cria LeadQualificado de forma defensiva.

    Args:
        lead_raw: LeadRaw, dict, str ou None (tenta converter)
        lead_dict: dict alternativo se lead_raw for string
        log_fn: funcao de log opcional

    Returns:
        LeadQualificado valido.

    Raises:
        RuntimeError: se lead_raw for invalido E lead_dict for vazio — sem fallback.
    """
    _log = log_fn or (lambda msg, level="info": None)

    # Caso 1: ja eh LeadRaw - perfeito
    if isinstance(lead_raw, LeadRaw):
        pass
    # Caso 2: eh dict - converte (mesmo que parcial)
    elif isinstance(lead_raw, dict):
        lead_raw = _dict_to_leadraw(lead_raw)
    # Caso 3: eh string (nome) ou None - recupera via lead_dict
    elif isinstance(lead_raw, str) or lead_raw is None:
        _log(f"[safe_qualificar] lead_raw={type(lead_raw).__name__}, usando lead_dict", "warning")
        if not lead_dict:
            raise RuntimeError(
                f"[safe_qualificar] lead_raw={type(lead_raw).__name__} e lead_dict vazio — "
                f"sem dados suficientes para qualificar lead, sem fallback"
            )
        lead_raw = _dict_to_leadraw(lead_dict)
    else:
        # Tipo desconhecido - tenta usar como dict
        _log(f"[safe_qualificar] tipo inesperado {type(lead_raw).__name__}", "warning")
        try:
            lead_raw = LeadRaw(**dict(lead_raw))
        except Exception:
            raise ValueError(f"Tipo nao suportado: {type(lead_raw).__name__}")

    # Extrai metadados
    score = 50
    tier = "STANDARD"
    if isinstance(lead_dict, dict):
        score = int(lead_dict.get("score") or 50)
        tier = lead_dict.get("tier") or "STANDARD"

    return LeadQualificado(
        lead=lead_raw,
        score=score,
        tier=tier,
        razoes=[],
        sinais=[],
        presenca_digital="SITE" if getattr(lead_raw, "website", None) else "ZERO_PRESENCA",
        dados_suficientes=True,
        caio_resultado=(lead_dict or {}).get("_caio_resultado"),
    )


def _dict_to_leadraw(data: dict) -> LeadRaw:
    """Converte dict (parcial) em LeadRaw, preenchendo campos faltantes."""
    defaults = {
        "nome": data.get("nome", "desconhecido"),
        "cidade": data.get("cidade", ""),
        "segmento": data.get("segmento", ""),
        "telefone": data.get("telefone", ""),
        "whatsapp": data.get("whatsapp", ""),
        "rating": float(data.get("rating", 0)),
        "total_avaliacoes": int(data.get("total_avaliacoes", 0)),
        "reviews": data.get("reviews", []) or [],
        "fotos": data.get("fotos", []) or [],
        "website": data.get("website", "") or "",
        "endereco": data.get("endereco", "") or "",
        "maps_url": data.get("maps_url", "") or "",
        "horarios": data.get("horarios", []) or [],
        "atributos": data.get("atributos", []) or [],
        "servicos": data.get("servicos", []) or [],
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "faixa_preco": data.get("faixa_preco"),
        "logo_url": data.get("logo_url"),
        "google_maps_embed": data.get("google_maps_embed", "") or "",
        "place_id": data.get("place_id", "") or "",
    }
    return LeadRaw(**defaults)