import os
import sys
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from utils import agente1_hunter_v2 as hunter


def _invalid_cached_lead(nome):
    lead = hunter.LeadRaw(
        nome=nome,
        cidade="Curitiba",
        segmento="pizzaria",
        telefone="",
        whatsapp="",
        rating=4.8,
        total_avaliacoes=20,
    )
    return hunter.LeadQualificado(
        lead=lead,
        score=40,
        tier="STANDARD",
        razoes=[],
        sinais={},
        presenca_digital={},
        dados_suficientes=False,
    )


@pytest.mark.asyncio
async def test_single_lead_hunter_uses_small_maps_pool_and_deadline(monkeypatch):
    captured = {}

    async def fake_gosom(segmento, cidade, limite):
        captured["gosom_limite"] = limite
        return []

    class FakeScraper:
        def __init__(self, headless=True):
            captured["headless"] = headless

        async def buscar(
            self,
            query,
            cidade,
            limite,
            leads_existentes=None,
            candidate_acceptor=None,
            max_duration_secs=None,
        ):
            captured["query"] = query
            captured["cidade"] = cidade
            captured["maps_limite"] = limite
            captured["max_duration_secs"] = max_duration_secs
            return []

    monkeypatch.setenv("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", "150")
    monkeypatch.setenv("FRALIB_HUNTER_SINGLE_LEAD_CANDIDATES", "6")
    monkeypatch.setenv("FRALIB_HUNTER_MAPS_SEARCH_LIMIT", "24")
    monkeypatch.setattr(hunter, "buscar_gosom", fake_gosom)
    monkeypatch.setattr(hunter, "GoogleMapsScraper", FakeScraper)

    leads = await hunter.buscar_leads_google_maps(
        cidade="Curitiba",
        segmento="pizzaria",
        limite=10,
        leads_existentes=set(),
        force_fresh=True,
        user_id=31,
        score_minimo=45,
        aprovados_necessarios=1,
    )

    assert leads == []
    assert captured["gosom_limite"] == 18
    assert captured["maps_limite"] == 18
    assert captured["max_duration_secs"] <= 145
    assert captured["max_duration_secs"] > 100


@pytest.mark.asyncio
async def test_invalid_cache_does_not_stop_fresh_maps_search(monkeypatch):
    captured = {"scraper_called": False}

    async def fake_gosom(segmento, cidade, limite):
        return []

    class FakeScraper:
        def __init__(self, headless=True):
            pass

        async def buscar(self, *args, **kwargs):
            captured["scraper_called"] = True
            return []

    monkeypatch.setattr(hunter, "buscar_gosom", fake_gosom)
    monkeypatch.setattr(hunter, "GoogleMapsScraper", FakeScraper)
    monkeypatch.setattr(hunter, "_buscar_leads_prontos_usuario", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        hunter,
        "_buscar_cache_leads",
        lambda *args, **kwargs: [_invalid_cached_lead(f"Lead {i}") for i in range(8)],
    )

    leads = await hunter.buscar_leads_google_maps(
        cidade="Curitiba",
        segmento="pizzaria",
        limite=10,
        leads_existentes=set(),
        force_fresh=True,
        user_id=31,
        score_minimo=45,
        aprovados_necessarios=1,
    )

    assert leads == []
    assert captured["scraper_called"] is True


@pytest.mark.asyncio
async def test_rejected_maps_candidates_are_not_saved_to_cache(monkeypatch):
    async def fake_gosom(segmento, cidade, limite):
        return [
            {
                "nome": "Pizzaria Sem WhatsApp",
                "tipo": "pizzaria",
                "telefone": "",
                "rating": 4.8,
                "reviews": 10,
                "depoimentos": [],
            }
        ]

    monkeypatch.setattr(hunter, "buscar_gosom", fake_gosom)
    monkeypatch.setattr(hunter, "_salvar_cache_leads", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache should not be saved")))

    leads = await hunter.buscar_leads_google_maps(
        cidade="Curitiba",
        segmento="pizzaria",
        limite=10,
        leads_existentes=set(),
        force_fresh=False,
        user_id=31,
        score_minimo=45,
        aprovados_necessarios=1,
    )

    assert leads == []


def test_env_int_clamps_capture_settings(monkeypatch):
    monkeypatch.setenv("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", "999")
    assert hunter._env_int("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", 170, 30, 180) == 180

    monkeypatch.setenv("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", "abc")
    assert hunter._env_int("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", 170, 30, 180) == 170


def test_ready_pool_recovers_failed_segment_compatible_leads(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE leads (
                    id TEXT, user_id INTEGER, nome TEXT, cidade TEXT, segmento TEXT,
                    telefone TEXT, whatsapp TEXT, rating REAL, score INTEGER, tier TEXT,
                    status TEXT, processado BOOLEAN, dados_completos TEXT, criado_em TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO leads VALUES (
                    'lead-1', 2, 'Nova Imperio Gym', 'Campina Grande Do Sul',
                    'Sala de fitness', '(41) 98436-6027', '(41) 98436-6027',
                    4.7, 50, 'STANDARD', 'erro', 0, :dados, '2026-06-02T16:29:21'
                )
                """
            ),
            {
                "dados": json.dumps(
                    {
                        "endereco": "Rodovia do Caqui, 1788 - Jardim Paulista, Campina Grande do Sul - PR",
                        "reviews": [{"autor": "Cliente", "texto": "Treino muito bom", "rating": 5}],
                        "total_avaliacoes": 12,
                    }
                )
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO leads VALUES (
                    'lead-2', 2, 'Nutricionista Priscila Botelho', 'Campina Grande Do Sul',
                    'Nutricionista', '(41) 99999-0000', '(41) 99999-0000',
                    4.8, 70, 'STANDARD', 'erro', 0, :dados, '2026-06-02T16:30:00'
                )
                """
            ),
            {
                "dados": json.dumps(
                    {
                        "endereco": "Rua Central, 100 - Campina Grande do Sul - PR",
                        "reviews": [{"autor": "Cliente", "texto": "Atendimento ótimo", "rating": 5}],
                        "total_avaliacoes": 20,
                    }
                )
            },
        )

    monkeypatch.setitem(sys.modules, "database", SimpleNamespace(engine=engine))

    leads = hunter._buscar_leads_prontos_usuario(
        2, "academia", "Campina Grande Do Sul", 5
    )

    assert [item.lead.nome for item in leads] == ["Nova Imperio Gym"]
