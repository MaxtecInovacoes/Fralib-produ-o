import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
backend = ROOT / "backend"
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

from endpoints import pipeline_run_helpers as helpers


def test_maybe_schedule_autorun_next_lead_skips_when_no_plan_or_queue(monkeypatch):
    calls = []

    class FakeLogger:
        def info(self, *args, **kwargs):
            calls.append(("info", args, kwargs))

        def warning(self, *args, **kwargs):
            calls.append(("warning", args, kwargs))

    class FakeDB:
        def execute(self, *args, **kwargs):
            class Result:
                def fetchone(self_inner):
                    return None

            return Result()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(helpers.asyncio, "create_task", lambda coro: calls.append(("task", coro)))

    helpers.maybe_schedule_autorun_next_lead(
        db_factory=FakeDB,
        tenant_id=2,
        cooldowns_by_plan={"pro": 1800},
        logger=FakeLogger(),
        log_fn=lambda *args, **kwargs: calls.append(("log", args, kwargs)),
        run_next_lead_fn=lambda *args, **kwargs: None,
    )

    assert calls == []
