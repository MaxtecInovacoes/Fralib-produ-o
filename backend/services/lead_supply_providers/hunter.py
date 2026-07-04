"""Hunter provider for lead supply engine.

Regra-mãe do projeto: minerar leads NOVOS de TODOS os pares (segmento, cidade)
configurados ate atingir estoque_alvo. Re-enfileira a si mesmo se a contagem
util ainda nao chegou no alvo, dentro de max_loops por execucao (anti-trap).
"""

from __future__ import annotations

import os
from typing import Any

from backend.core.db_imports import Session  # noqa: F401  — B3 DRY


# Numero maximo de loops internos Hunter->Hunter ate atingir o alvo.
# Evita travar o worker se API estiver off.
MAX_HUNTER_LOOPS = int(os.getenv("LEAD_SUPPLY_HUNTER_MAX_LOOPS", "6"))


async def run_hunter_job(db: Session, payload: dict[str, Any], tenant_id: int) -> dict[str, Any]:
    """Run the Hunter job to search and capture leads."""
    from backend.services.lead_supply_storage import get_or_create_config
    from backend.services.lead_supply_inventory import (
        _enqueue_caio,
        _existing_names,
        enqueue_hunter,
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
    if needed <= 0:
        _event(db, tenant_id, "hunter", "info", "Estoque alvo já está completo")
        return {"ok": True, "captured": 0, "needed": 0}

    batch_limit = max(1, min(int(os.getenv("LEAD_SUPPLY_HUNTER_BATCH", "8")), 20, needed))
    captured_total = 0
    loops = 0

    from lead_providers import create_facade

    facade = create_facade(db, tenant_id, cfg)
    provider_name = facade.provider_name
    _event(db, tenant_id, provider_name, "info",
           f"Usando provider: {provider_name} - meta {int(cfg['estoque_alvo'])}, util {useful}")

    # Loop interno: minera ate encher estoque OU esgotar todas regioes
    # (mesma logica do spec: "Hunter nao para enquanto alvo nao completo")
    while needed > 0 and loops < MAX_HUNTER_LOOPS:
        loops += 1
        captured_loop = 0
        for segmento, cidade in [(seg, cid) for seg in segmentos for cid in cidades]:
            if captured_loop >= batch_limit:
                break
            existentes = _existing_names(db, tenant_id, cidade)
            try:
                candidates = await facade.search(
                    segmentos=[segmento],
                    cidades=[cidade],
                    force=payload.get("force", False),
                    force_fresh=bool(payload.get("force_fresh", False)),
                    batch_limit=max(1, batch_limit - captured_loop),
                    score_minimo=int(cfg["score_minimo"]),
                    existing_names=existentes,
                )
            except Exception as exc:
                _event(db, tenant_id, provider_name, "error",
                       f"{provider_name.capitalize()} falhou em {segmento}/{cidade}: {str(exc)[:180]}")
                continue
            if not candidates:
                # Nada novo nesta regiao; proxima ou sair
                _event(db, tenant_id, provider_name, "info",
                       f"{provider_name.capitalize()} sem lead novo em {segmento}/{cidade} (loop {loops})")
                continue
            stored = facade.store_candidates(candidates, segmento, cidade)
            for (inv_id, inserted) in stored:
                if inserted:
                    captured_loop += 1
                    captured_total += 1
                    _enqueue_caio(db, tenant_id, inv_id)
                if captured_loop >= batch_limit:
                    break

        # Recalcula util apos este loop
        counts = status(db, tenant_id, limit=1)["counts"]
        useful = sum(counts.get(k, 0) for k in ("raw", "qualifying", "approved", "reserved", "in_production"))
        needed = max(0, int(cfg["estoque_alvo"]) - useful)

        if captured_loop == 0:
            # Nenhuma regiao rendeu nada - Hunter esgotado nesta rodada
            _event(db, tenant_id, provider_name, "warning",
                   f"{provider_name.capitalize()} esgotou ({loops}/{MAX_HUNTER_LOOPS} loops); sem leads novos em nenhuma regiao")
            break

    if captured_total:
        _event(db, tenant_id, provider_name, "success",
               f"{provider_name.capitalize()} capturou {captured_total} lead(s) em {loops} loop(s); util={useful}/{int(cfg['estoque_alvo'])}")
    else:
        _event(db, tenant_id, provider_name, "warning",
               f"{provider_name.capitalize()} nao encontrou lead novo nesta rodada")

    # Se ainda nao atingiu o alvo e terminamos os loops, agenda outra rodada
    # para daqui a 5 min (cooldown para nao martelar API)
    if needed > 0 and loops >= MAX_HUNTER_LOOPS and captured_total > 0:
        _event(db, tenant_id, "hunter", "info",
               f"Loop {MAX_HUNTER_LOOPS}/{MAX_HUNTER_LOOPS} atingido; reagendando Hunter em 5min")
        enqueue_hunter(db, tenant_id, delay_seconds=300, force=False)

    return {
        "ok": True,
        "captured": captured_total,
        "needed": needed,
        "useful": useful,
        "target": int(cfg["estoque_alvo"]),
        "loops": loops,
        "provider": provider_name,
    }
