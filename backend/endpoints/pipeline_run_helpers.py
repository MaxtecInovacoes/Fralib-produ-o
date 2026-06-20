"""Helpers extracted from the pipeline execution monolith."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import text


def maybe_schedule_autorun_next_lead(
    *,
    db_factory,
    tenant_id: int,
    cooldowns_by_plan: dict[str, int],
    logger,
    log_fn,
    run_next_lead_fn,
) -> None:
    """Schedule the next existing lead after cooldown when the tenant can auto-run."""
    try:
        with db_factory() as db:
            plano_row = db.execute(
                text("SELECT plano, plano_pago FROM users WHERE id=:id"),
                {"id": tenant_id},
            ).fetchone()
            plano = (plano_row[0] if plano_row else "trial") or "trial"
            plano_pago = plano_row[1] if plano_row else False
            fila = db.execute(
                text(
                    "SELECT id, segmento, cidade FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1"
                ),
                {"uid": tenant_id},
            ).fetchone()
            if not fila or not plano_pago:
                return
            cooldown = cooldowns_by_plan.get(plano, 3600)
            lead_id = str(fila[0])
            logger.info(
                "[Pipeline] Auto-run: lead %s na fila, agendando em %ss",
                lead_id,
                cooldown,
            )
            log_fn(
                f"Proximo pipeline automatico em {cooldown // 60}min ({fila[1]} - {fila[2]})",
                "info",
            )

            async def _auto_run_delayed():
                await asyncio.sleep(cooldown)
                try:
                    await run_next_lead_fn(lead_id, tenant_id)
                except Exception as err:
                    logger.warning("[Pipeline] Auto-run erro: %s", err)

            asyncio.create_task(_auto_run_delayed())
    except Exception as err:
        logger.warning("[Pipeline] Auto-run check erro: %s", err)

