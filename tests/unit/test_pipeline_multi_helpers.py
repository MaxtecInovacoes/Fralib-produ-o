from backend.endpoints.pipeline_multi_helpers import handle_pipeline_no_leads


def test_handle_pipeline_no_leads_retries_once_then_stops():
    logs = []

    def _log(msg, tipo):
        logs.append((msg, tipo))

    config = {}

    first = handle_pipeline_no_leads(
        config=config,
        segmento="fitness",
        cidade="sao paulo",
        logger=_log,
    )
    second = handle_pipeline_no_leads(
        config=config,
        segmento="fitness",
        cidade="sao paulo",
        logger=_log,
    )

    assert first is True
    assert second is False
    assert config["_cache_invalidado"] is True
    assert config["force_fresh"] is True
    assert logs[0][1] == "info"
    assert logs[1][1] == "warning"
