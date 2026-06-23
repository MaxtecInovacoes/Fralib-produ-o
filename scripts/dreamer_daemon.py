"""Dreamer daemon — consolida lessons cross-tenant nightly (3h BRT).

Executa dreamer.run_dream(apply=True) periodicamente.
Pode ser agendado via PM2 cron_restart ou rodado como daemon em loop.

v1.1-baseline-2026-06-23: novo entry point para gap #5 do Sprint 0.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dreamer_daemon")


def main() -> None:
    """Loop principal: roda dreamer.run_dream(apply=True) a cada DREAMER_INTERVAL_SECONDS."""
    interval_seconds = int(os.getenv("DREAMER_INTERVAL_SECONDS", "86400"))
    logger.info(f"[DreamerDaemon] starting (interval={interval_seconds}s)")
    while True:
        try:
            from services.dreamer import run_dream  # type: ignore[import-not-found]

            stats = run_dream(apply=True)
            logger.info(
                f"[DreamerDaemon] dream OK: "
                f"tenants={stats.tenants_processed} "
                f"leads={stats.leads_analyzed} "
                f"lessons={stats.lessons_extracted}"
            )
        except Exception as e:
            logger.exception(f"[DreamerDaemon] dream failed: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
