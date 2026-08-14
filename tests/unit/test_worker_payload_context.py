from worker import _promote_context_from_lead_data


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
