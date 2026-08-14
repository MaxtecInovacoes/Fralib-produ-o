def test_llm_router_treats_522_as_transient_and_cascades(monkeypatch):
    import backend.agents.llm_router as router

    calls = []

    class FakeResponse:
        status_code = 522

    class FakeError(Exception):
        def __init__(self):
            super().__init__("provider_error 522")
            self.response = FakeResponse()

    def fake_try(model_id, system, user, temperature, max_tokens, api_key, base_url):
        calls.append(model_id)
        if len(calls) == 1:
            raise FakeError()
        return "ok", {"input_tokens": 10, "output_tokens": 20}

    monkeypatch.setattr(router, "_try_anthropic_call", fake_try)
    monkeypatch.setattr(router._time, "sleep", lambda *_args, **_kwargs: None)

    text, usage = router._call_anthropic(
        "claude-sonnet-4-6",
        "system",
        "user",
        0.2,
        512,
        api_key="test-key",
        base_url="https://example.test",
    )

    assert text == "ok"
    assert usage["input_tokens"] == 10
    assert len(calls) == 2
