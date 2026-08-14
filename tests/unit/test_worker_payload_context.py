from worker import _needs_lead_hydration, _promote_context_from_lead_data


def test_promote_context_from_lead_data_fills_missing_segmento_and_cidade():
    payload = {
        "lead_id": "abc",
        "lead_data": {
            "nome": "Start Academia",
            "cidade": "Campina Grande do Sul",
            "segmento": "academia",
        },
    }

    normalized = _promote_context_from_lead_data(payload)

    assert normalized["cidade"] == "Campina Grande do Sul"
    assert normalized["segmento"] == "academia"


def test_promote_context_from_lead_data_preserves_explicit_payload_values():
    payload = {
        "lead_id": "abc",
        "cidade": "Curitiba",
        "segmento": "pilates",
        "lead_data": {
            "nome": "Start Academia",
            "cidade": "Campina Grande do Sul",
            "segmento": "academia",
        },
    }

    normalized = _promote_context_from_lead_data(payload)

    assert normalized["cidade"] == "Curitiba"
    assert normalized["segmento"] == "pilates"


def test_needs_lead_hydration_when_lead_data_missing_required_fields():
    payload = {
        "lead_id": "abc",
        "lead_data": {
            "nome": "Start Academia",
            "cidade": "",
            "segmento": "",
        },
    }

    assert _needs_lead_hydration(payload) is True


def test_needs_lead_hydration_false_when_required_fields_present():
    payload = {
        "lead_id": "abc",
        "lead_data": {
            "nome": "Start Academia",
            "cidade": "Campina Grande do Sul",
            "segmento": "academia",
        },
    }

    assert _needs_lead_hydration(payload) is False
