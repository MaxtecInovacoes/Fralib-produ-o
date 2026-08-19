"""Hunter provider for lead supply engine."""


import os
from typing import Any

from sqlalchemy.orm import Session


async def run_hunter_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """Run the Hunter job to search and capture leads."""
    from backend.services.lead_supply_storage import get_or_create_config
    from backend.services.lead_supply_inventory import (
        _enqueue_caio,
        _existing_names,
        status,
    )
    from backend.services.lead_supply_events import _event
    from backend.services.lead_supply_filters import normalize_list

    cfg = get_or_create_config(db, tenant_id)
    if not cfg["ativo"] or cfg["hunter_pausado"]:
        _event(db, tenant_id, "hunter", "info", "Hunter pausado pelo usuário")
        return {"ok": True, "paused": True}
    segmentos = normalize_list(payload.get("segmentos") or cfg["segmentos"])
    cidades = normalize_list(payload.get("cidades") or cfg["cidades"])
    if not segmentos or not cidades:
        _event(db, tenant_id, "hunter", "warning", "Informe ao menos um nicho e uma cidade")
        return {"ok": False, "error": "configuracao_incompleta"}
    counts = status(db, tenant_id, limit=1)["counts"]
    useful = sum(counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production"))
    needed = max(0, int(cfg["estoque_alvo"]) - useful)
    if payload.get("force"):
        needed = max(needed, int(payload.get("quantidade") or 1))
    # Margem de 1.5x para absorver descartes do Caio sem parar a esteira
    needed = int(needed * 1.5)
    if needed <= 0:
        _event(db, tenant_id, "hunter", "info", "Estoque alvo já está completo")
        return {"ok": True, "captured": 0, "needed": 0}

    batch_limit = max(1, min(int(os.getenv("LEAD_SUPPLY_HUNTER_BATCH") or "8"), 20, needed))
    captured = 0
    _event(db, tenant_id, "hunter", "info", f"Hunter buscando até {batch_limit} lead(s) para abastecer estoque")

    from backend.services.lead_providers import create_facade

    facade = create_facade(db, tenant_id, cfg)
    provider_name = facade.provider_name
    _event(db, tenant_id, provider_name, "info", f"Usando provider: {provider_name}")

    for segmento, cidade in [(seg, cid) for seg in segmentos for cid in cidades]:
        if captured >= batch_limit:
            break
        existentes = _existing_names(db, tenant_id, cidade)
        try:
            candidates = await facade.search(
                segmentos=[segmento],
                cidades=[cidade],
                force=payload.get("force", False),
                force_fresh=bool(payload.get("force_fresh", False)),
                batch_limit=max(1, batch_limit - captured),
                score_minimo=int(cfg["score_minimo"]),
                existing_names=existentes,
            )
        except Exception as exc:
            _event(db, tenant_id, provider_name, "error", f"{provider_name.capitalize()} falhou em {segmento}/{cidade}: {str(exc)[:180]}")
            continue
        stored = facade.store_candidates(candidates, segmento, cidade)
        for (inv_id, inserted) in stored:
            if inserted:
                captured += 1
                _enqueue_caio(db, tenant_id, inv_id)
            if captured >= batch_limit:
                break
    if captured:
        _event(db, tenant_id, provider_name, "success", f"{provider_name.capitalize()} adicionou {captured} lead(s) ao inventário")
    else:
        _event(db, tenant_id, provider_name, "warning", f"{provider_name.capitalize()} não encontrou lead novo nesta rodada")
    return {"ok": True, "captured": captured, "needed": needed, "provider": provider_name}
