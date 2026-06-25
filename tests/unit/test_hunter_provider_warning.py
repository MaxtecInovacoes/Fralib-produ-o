"""Testes para o warning de Hunter quando website E place_id estao vazios.

Cobre o caso onde o Google Maps nao devolveu website (seletor quebrado,
perfil sem ficha completa) e o Hunter persiste o lead assim mesmo.
Esse sinal permite auditoria via lead_supply_events.
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from services.hunter_provider import HunterProvider


def _make_provider(fetchone_return):
    """Cria HunterProvider com db mockado.

    fetchone_return: valor retornado por db.execute().fetchone() no INSERT.
    """
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = fetchone_return
    db.commit.return_value = None

    provider = HunterProvider(db=db, tenant_id=31, config={})
    return provider


def test_hunter_warns_on_missing_website_and_placeid():
    """Hunter deve chamar _log('warn', ...) quando website E place_id vazios."""
    provider = _make_provider(("inv-id-1",))

    captured = []
    provider._log = lambda level, msg, payload=None: captured.append(
        {"level": level, "msg": msg, "payload": payload}
    )

    candidate = {
        "lead": {
            "nome": "Carolina Ragugnetti",
            "cidade": "Pinheiros",
            "segmento": "nutricionista",
            "website": "",
            "place_id": "",
        },
        "score": 80,
        "tier": "PREMIUM",
    }
    inv_id, inserted = provider._store_candidate(candidate, "nutricionista", "Pinheiros")

    assert inserted is True
    assert inv_id == "inv-id-1"
    assert len(captured) == 1
    warn = captured[0]
    assert warn["level"] == "warn"
    assert "Carolina Ragugnetti" in warn["msg"]
    assert "website" in warn["msg"].lower() and "place_id" in warn["msg"].lower()
    assert warn["payload"]["inventory_id"] == "inv-id-1"
    assert warn["payload"]["lead_nome"] == "Carolina Ragugnetti"


def test_hunter_does_not_warn_when_website_present():
    """Quando website esta preenchido, NAO deve emitir warning."""
    provider = _make_provider(("inv-id-2",))

    captured = []
    provider._log = lambda level, msg, payload=None: captured.append(
        {"level": level, "msg": msg}
    )

    candidate = {
        "lead": {
            "nome": "Loja com Site",
            "cidade": "Sao Paulo",
            "segmento": "loja",
            "website": "https://lojacomsite.com.br",
            "place_id": "ChIJxyz",
        },
        "score": 70,
        "tier": "STANDARD",
    }
    provider._store_candidate(candidate, "loja", "Sao Paulo")

    # Sem warn — website presente
    assert all(c["level"] != "warn" for c in captured)


def test_hunter_does_not_warn_when_only_place_id_present():
    """Quando place_id existe (mesmo sem website), NAO emite warn.

    O warn so dispara quando AMBOS estao vazios — sinal claro de dado
    incompleto no Maps.
    """
    provider = _make_provider(("inv-id-3",))

    captured = []
    provider._log = lambda level, msg, payload=None: captured.append(
        {"level": level, "msg": msg}
    )

    candidate = {
        "lead": {
            "nome": "Restaurante com Place ID",
            "cidade": "Rio",
            "segmento": "restaurante",
            "website": "",
            "place_id": "ChIJabc",
        },
        "score": 50,
        "tier": "STANDARD",
    }
    provider._store_candidate(candidate, "restaurante", "Rio")

    assert all(c["level"] != "warn" for c in captured)


def test_hunter_warn_best_effort_when_log_fails():
    """Se _log falhar, Hunter NAO quebra o fluxo do INSERT."""
    provider = _make_provider(("inv-id-4",))

    def _raise(*_args, **_kwargs):
        raise RuntimeError("event sink indisponivel")

    provider._log = _raise  # noqa: E731

    candidate = {
        "lead": {
            "nome": "Teste",
            "cidade": "Cidade",
            "segmento": "teste",
            "website": "",
            "place_id": "",
        },
        "score": 0,
        "tier": "REJEITADO",
    }

    # Nao deve lancar excecao
    inv_id, inserted = provider._store_candidate(candidate, "teste", "Cidade")

    assert inserted is True
    assert inv_id == "inv-id-4"