"""Recovery seguro de runtime (fila/locks), sem apagar histórico útil."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

for _rel in ("backend", "backend/core"):
    sys.path.insert(0, os.path.join(ROOT, _rel))

from database import SessionLocal
import job_queue


def main() -> int:
    db = SessionLocal()
    try:
        reaped = job_queue.reap_dead_workers(db, dead_after_minutes=5)
        finalized = job_queue.finalize_exhausted_jobs(db)
        print(
            "OK recover_runtime: "
            f"jobs_ressuscitados={reaped} "
            f"jobs_finalizados={finalized}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
