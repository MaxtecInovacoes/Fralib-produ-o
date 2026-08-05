"""Stub hunter agent — real hunter logic lives in lead_supply_engine."""
def get_agent(*args, **kwargs):
    class _Stub:
        async def run(self, *a, **kw):
            return {"ok": True, "stub": True}
    return _Stub()
