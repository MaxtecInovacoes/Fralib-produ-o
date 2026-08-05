"""
test_idor_multitenant.py — Testes de isolamento multi-tenant (IDOR).

Verifica que usuario A nao consegue manipular dados (leads, falhas) pertencentes
ao usuario B atraves dos endpoints corrigidos contra IDOR.

Rotas cobertas:
- POST /api/leads/{id}/feedback         -> UPDATE leads SET status (leads_endpoints.py:706)
- POST /api/leads/{id}/enviar-mensagem  -> UPDATE leads SET sdr_stage (leads_endpoints.py:800)
- POST /api/pipeline/reprocessar/{id}   -> UPDATE leads SET status='capturado' (pipeline_endpoints.py:1556)
- POST /api/falhas/{id}/reenfileirar    -> UPDATE pipeline_failures SET resolvido (falhas_endpoints.py:175)

Os UPDATEs internos do pipeline (linhas 864, 1499, 1534) so executam em background
task chamada apos validacao de ownership; o teste valida que o ponto de entrada HTTP
nega o acesso, o que garante que esses UPDATEs nunca rodem para um lead de outro user.
"""
import os
import sys
import pytest
from datetime import datetime, timedelta
import jwt
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

# Garante que TESTING e DATABASE_URL estao setados antes de importar o app
os.environ.setdefault("TESTING", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:fralib2024@localhost:5433/fralib_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")


def _token_for(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _headers(user_id: int, email: str) -> dict:
    return {"Authorization": f"Bearer {_token_for(user_id, email)}"}


@pytest.fixture
def two_users(db_session):
    """Cria dois usuarios isolados (A e B) e devolve seus ids/emails."""
    from utils.password_utils import hash_password

    rows = db_session.execute(
        text(
            """
            INSERT INTO users (email, password_hash, nome, tenant_id)
            VALUES
                (:ea, :ph, 'User A', 1),
                (:eb, :ph, 'User B', 2)
            RETURNING id, email
            """
        ),
        {
            "ea": "user_a@test.fralib",
            "eb": "user_b@test.fralib",
            "ph": hash_password("Test123!@#"),
        },
    ).fetchall()
    db_session.commit()

    user_a = {"id": rows[0][0], "email": rows[0][1]}
    user_b = {"id": rows[1][0], "email": rows[1][1]}
    return user_a, user_b


@pytest.fixture
def lead_de_a(db_session, two_users):
    """Lead pertencente ao user A com site ja gerado (para passar pre-checks)."""
    user_a, _ = two_users
    lead_id = f"lead_a_{user_a['id']}"

    db_session.execute(
        text(
            """
            INSERT INTO leads (
                id, user_id, nome, telefone, whatsapp, segmento, cidade,
                status, processado, site_url, sdr_stage, rating,
                criado_em, atualizado_em
            ) VALUES (
                :id, :uid, 'Lead Do A', '11999990000', '11999990000',
                'Nutricionista', 'Sao Paulo',
                'concluido', true, 'https://exemplo.fralib/lead-do-a',
                'pendente_wpp', 4.5,
                NOW()::text, NOW()::text
            )
            """
        ),
        {"id": lead_id, "uid": user_a["id"]},
    )
    db_session.commit()
    return lead_id


@pytest.fixture
def falha_de_a(db_session, two_users):
    """Falha de pipeline pertencente ao user A."""
    user_a, _ = two_users
    row = db_session.execute(
        text(
            """
            INSERT INTO pipeline_failures (
                lead_id, lead_nome, fase, payload, checkpoint_id,
                tenant_id, resolvido, criado_em
            ) VALUES (
                'lead_falha_a', 'Lead Falha A', 'liam',
                '{}'::jsonb, NULL, :tid, FALSE, NOW()
            )
            RETURNING id
            """
        ),
        {"tid": user_a["id"]},
    ).fetchone()
    db_session.commit()
    return row[0]


@pytest.fixture
async def http():
    from server import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ===== TESTES =====

@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_b_nao_pode_dar_feedback_no_lead_do_a(
    db_session, http, two_users, lead_de_a
):
    """User B tenta marcar lead do A como convertido -> deve falhar (404)
       e status do lead deve permanecer inalterado."""
    user_a, user_b = two_users

    r = await http.post(
        f"/api/leads/{lead_de_a}/feedback",
        headers=_headers(user_b["id"], user_b["email"]),
        json={"resultado": "convertido", "observacao": "tentativa IDOR"},
    )

    assert r.status_code == 404, (
        f"Esperado 404 (lead nao pertence ao user B), recebi {r.status_code}: {r.text}"
    )

    # Confirmar que o status do lead nao mudou no banco
    status_atual = db_session.execute(
        text("SELECT status FROM leads WHERE id=:id"), {"id": lead_de_a}
    ).scalar()
    assert status_atual == "concluido", (
        f"Status do lead foi alterado por outro tenant! status={status_atual}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_a_pode_dar_feedback_no_proprio_lead(
    db_session, http, two_users, lead_de_a
):
    """Sanity: o dono deve conseguir registrar feedback normalmente."""
    user_a, _ = two_users

    r = await http.post(
        f"/api/leads/{lead_de_a}/feedback",
        headers=_headers(user_a["id"], user_a["email"]),
        json={"resultado": "convertido", "observacao": "feedback ok"},
    )

    assert r.status_code == 200, f"Owner devia conseguir: {r.status_code} {r.text}"

    status_atual = db_session.execute(
        text("SELECT status FROM leads WHERE id=:id"), {"id": lead_de_a}
    ).scalar()
    assert status_atual == "convertido"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_b_nao_pode_enviar_mensagem_no_lead_do_a(
    db_session, http, two_users, lead_de_a
):
    """User B tenta acionar Franz no lead do A -> deve 404.
       Mesmo que falhe por outra razao (WPP desconectado), sdr_stage NAO
       pode ser alterado."""
    _, user_b = two_users
    sdr_antes = db_session.execute(
        text("SELECT sdr_stage FROM leads WHERE id=:id"), {"id": lead_de_a}
    ).scalar()

    r = await http.post(
        f"/api/leads/{lead_de_a}/enviar-mensagem",
        headers=_headers(user_b["id"], user_b["email"]),
    )

    assert r.status_code in (400, 404, 500), (
        f"Esperado falha (lead nao pertence), recebi {r.status_code}: {r.text}"
    )
    assert r.status_code == 404 or "Lead nao encontrado" in r.text or "WhatsApp" in r.text

    sdr_depois = db_session.execute(
        text("SELECT sdr_stage FROM leads WHERE id=:id"), {"id": lead_de_a}
    ).scalar()
    assert sdr_antes == sdr_depois, "sdr_stage foi alterado por outro tenant!"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_b_nao_pode_reprocessar_lead_do_a(
    db_session, http, two_users, lead_de_a
):
    """User B tenta reprocessar lead do A -> 404 e status nao muda."""
    _, user_b = two_users

    r = await http.post(
        f"/api/pipeline/reprocessar/{lead_de_a}",
        headers=_headers(user_b["id"], user_b["email"]),
    )

    assert r.status_code == 404, (
        f"Esperado 404, recebi {r.status_code}: {r.text}"
    )

    status_atual = db_session.execute(
        text("SELECT status FROM leads WHERE id=:id"), {"id": lead_de_a}
    ).scalar()
    assert status_atual == "concluido", (
        f"Reprocessar de outro tenant alterou status! status={status_atual}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_b_nao_pode_reenfileirar_falha_do_a(
    db_session, http, two_users, falha_de_a
):
    """User B tenta reenfileirar falha do A -> 404 e resolvido continua FALSE."""
    _, user_b = two_users

    r = await http.post(
        f"/api/falhas/{falha_de_a}/reenfileirar",
        headers=_headers(user_b["id"], user_b["email"]),
    )

    assert r.status_code == 404, (
        f"Esperado 404, recebi {r.status_code}: {r.text}"
    )

    resolvido = db_session.execute(
        text("SELECT resolvido FROM pipeline_failures WHERE id=:id"),
        {"id": falha_de_a},
    ).scalar()
    assert resolvido is False or resolvido == 0, (
        f"Falha do user A foi resolvida por outro tenant! resolvido={resolvido}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_b_nao_ve_lead_do_a_em_listagem(
    db_session, http, two_users, lead_de_a
):
    """Sanity geral: leads do user A nao aparecem na listagem do user B."""
    _, user_b = two_users

    r = await http.get(
        "/api/leads/sites",
        headers=_headers(user_b["id"], user_b["email"]),
    )

    if r.status_code == 200:
        data = r.json()
        sites = data if isinstance(data, list) else data.get("sites", data.get("leads", []))
        ids = [s.get("id") if isinstance(s, dict) else s for s in sites]
        assert lead_de_a not in ids, (
            f"Lead de outro tenant vazou na listagem: {ids}"
        )
