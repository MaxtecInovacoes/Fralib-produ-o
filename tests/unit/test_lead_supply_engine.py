import json
import os
import sys


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
for rel in ("backend", "backend/core", "backend/endpoints", "backend/services"):
    sys.path.insert(0, os.path.join(ROOT, rel))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.lead_supply_engine import (
    _ensure_lead_row,
    _existing_names,
    dedupe_key,
    default_targets,
    normalize_list,
)


def test_default_targets_respect_plan_daily_caps():
    starter = default_targets("starter", meta_diaria=50)
    pro = default_targets("pro", meta_diaria=50)

    assert starter["meta_diaria"] == 6
    assert starter["estoque_alvo"] >= 180
    assert pro["meta_diaria"] == 12
    assert pro["estoque_alvo"] >= 360


def test_dedupe_prefers_stable_contact_markers():
    lead_a = {
        "nome": "Academia Centro",
        "cidade": "Curitiba",
        "telefone": "(41) 99999-0000",
        "endereco": "Rua A, 10",
    }
    lead_b = {
        "nome": "Academia Centro Unidade 2",
        "cidade": "Curitiba",
        "telefone": "5541999990000",
        "endereco": "Rua B, 20",
    }

    assert dedupe_key(31, lead_a) == dedupe_key(31, lead_b)
    assert dedupe_key(32, lead_a) != dedupe_key(31, lead_a)


def test_normalize_list_accepts_commas_newlines_and_dedupes():
    assert normalize_list("academia, restaurante\nAcademia; nutricionista") == [
        "academia",
        "restaurante",
        "nutricionista",
    ]


def test_lead_unique_index_is_tenant_scoped():
    db_schema = open(os.path.join(ROOT, "backend", "core", "database.py"), encoding="utf-8").read()
    supply_storage = open(
        os.path.join(ROOT, "backend", "services", "lead_supply_storage.py"),
        encoding="utf-8",
    ).read()

    for source in (db_schema, supply_storage):
        assert "DROP INDEX IF EXISTS idx_leads_unique" in source
        assert "idx_leads_tenant_phone_city_unique" in source
        assert "ON leads (user_id, telefone, cidade)" in source


def test_status_exposes_lead_supply_diagnostics_contract():
    source = open(
        os.path.join(ROOT, "backend", "services", "lead_supply_inventory.py"),
        encoding="utf-8",
    ).read()

    assert '"discard_breakdown": discard_breakdown' in source
    assert '"nicho_cidade_breakdown": nicho_cidade_breakdown' in source
    assert '"gap_para_meta": gap_para_meta' in source
    assert '"caio_motivo": r[8] or ""' in source
    assert "SELECT caio_motivo, COUNT(*)" in source
    assert "status='discarded'" in source


def test_existing_names_does_not_block_recoverable_failed_leads():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE leads (user_id INTEGER, cidade TEXT, nome TEXT, status TEXT, processado BOOLEAN)"))
        conn.execute(text("CREATE TABLE lead_inventory (tenant_id INTEGER, cidade TEXT, nome TEXT, status TEXT)"))
        conn.execute(
            text("INSERT INTO leads VALUES (2, 'Campina Grande Do Sul', 'Nova Imperio Gym', 'erro', 0)")
        )
        conn.execute(
            text("INSERT INTO leads VALUES (2, 'Campina Grande Do Sul', 'High Fitness Academia', 'concluido', 1)")
        )
        conn.execute(
            text("INSERT INTO lead_inventory VALUES (2, 'Campina Grande Do Sul', 'Lead Em Estoque', 'raw')")
        )
        conn.execute(
            text("INSERT INTO lead_inventory VALUES (2, 'Campina Grande Do Sul', 'Lead Retry', 'error_retry')")
        )

    with Session(engine) as db:
        names = _existing_names(db, 2, "Campina Grande Do Sul")

    assert "nova imperio gym" not in names
    assert "high fitness academia" in names
    assert "lead em estoque" in names
    assert "lead retry" not in names


def test_ensure_lead_row_reuses_existing_contact_for_recovered_inventory():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE leads (
                    id TEXT PRIMARY KEY,
                    nome TEXT,
                    cidade TEXT,
                    segmento TEXT,
                    telefone TEXT,
                    whatsapp TEXT,
                    rating REAL,
                    score INTEGER,
                    tier TEXT,
                    status TEXT,
                    user_id INTEGER,
                    criado_em TEXT,
                    atualizado_em TEXT,
                    processado BOOLEAN,
                    tentativas INTEGER,
                    dados_completos TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE lead_inventory (
                    id TEXT PRIMARY KEY,
                    tenant_id INTEGER,
                    lead_id TEXT,
                    nome TEXT,
                    cidade TEXT,
                    status TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO leads (
                    id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,
                    user_id,criado_em,atualizado_em,processado,tentativas,dados_completos
                )
                VALUES (
                    'lead-old','Nova Imperio Gym','Campina Grande Do Sul','Sala de fitness',
                    '(41) 98436-6027','(41) 98436-6027',4.7,40,'STANDARD','erro',
                    2,'2026-06-01T10:00:00','2026-06-01T10:00:00',0,1,:dados
                )
                """
            ),
            {"dados": json.dumps({"endereco": "Antigo"})},
        )
        conn.execute(
            text(
                """
                INSERT INTO lead_inventory
                VALUES ('inv-1', 2, NULL, 'Nova Imperio Gym', 'Campina Grande Do Sul', 'reserved')
                """
            )
        )

    item = {
        "id": "inv-1",
        "nome": "Nova Imperio Gym",
        "cidade": "Campina Grande Do Sul",
        "segmento": "academia",
        "telefone": "(41) 98436-6027",
        "whatsapp": "(41) 98436-6027",
        "rating": 4.7,
        "score_caio": 50,
        "tier": "STANDARD",
        "endereco": "Rodovia do Caqui, 1788",
        "dados": {"website": "", "maps_url": ""},
    }

    with Session(engine) as db:
        lead_id = _ensure_lead_row(db, 2, item)
        count = db.execute(text("SELECT COUNT(*) FROM leads")).scalar()
        lead = db.execute(
            text("SELECT status, processado, segmento, score FROM leads WHERE id='lead-old'")
        ).fetchone()
        inventory_lead_id = db.execute(text("SELECT lead_id FROM lead_inventory WHERE id='inv-1'")).scalar()

    assert lead_id == "lead-old"
    assert count == 1
    assert lead == ("processando", 0, "academia", 50)
    assert inventory_lead_id == "lead-old"
