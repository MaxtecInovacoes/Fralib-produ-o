"""
Testes unitários para superadmin_endpoints.py

Cobre as operações administrativas:
- Listagem de tenants
- Estatísticas globais
- Ações de admin (toggle, set-plan, etc)
"""
import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from unittest.mock import ANY

# Setup path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from sqlalchemy import text


class TestSuperadminConfig:
    """Testes para configuração do superadmin."""

    def test_get_superadmin_config_retorna_emails(self):
        """Deve retornar lista de emails do superadmin."""
        from backend.endpoints.superadmin_endpoints import get_superadmin_config
        from unittest.mock import MagicMock

        mock_user = {"id": 1, "email": "admin@test.com", "role": "superadmin"}

        result = get_superadmin_config(user=mock_user)

        assert result["ok"] is True
        assert "superadmin_emails" in result
        assert isinstance(result["superadmin_emails"], list)


class TestSuperadminMetrics:
    """Testes para métricas globais do sistema."""

    def test_get_metrics_retorna_estrutura_completa(self, db_session):
        """Deve retornar métricas do sistema."""
        from backend.endpoints.superadmin_endpoints import get_metrics
        from unittest.mock import MagicMock

        mock_user = {"id": 1, "email": "admin@test.com"}

        # Criar dados de teste
        db_session.execute(
            text("""
                INSERT INTO users (id, email, nome, tenant_id, plano, status, creditos, plano_pago)
                VALUES (100, 'user1@test.com', 'User 1', 100, 'pro', 'ativo', 100, true),
                       (101, 'user2@test.com', 'User 2', 101, 'starter', 'ativo', 50, true)
            """)
        )
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, user_id, status, processado)
                VALUES ('lead-1', 'Lead 1', 100, 'concluido', true),
                       ('lead-2', 'Lead 2', 100, 'pendente', false),
                       ('lead-3', 'Lead 3', 101, 'concluido', true)
            """)
        )
        db_session.commit()

        result = get_metrics(db=db_session, user=mock_user)

        assert result["ok"] is True
        assert "metrics" in result
        metrics = result["metrics"]

        assert "totalUsers" in metrics
        assert "activeUsers" in metrics
        assert "totalLeads" in metrics
        assert "sitesGerados" in metrics
        assert "tokensInput" in metrics
        assert "tokensOutput" in metrics
        assert "custoTotalUSD" in metrics
        assert "pagantes" in metrics


class TestSuperadminListUsers:
    """Testes para listagem de usuários."""

    def test_list_users_retorna_lista_completa(self, db_session):
        """Deve retornar lista de todos os usuários."""
        from backend.endpoints.superadmin_endpoints import list_users

        mock_user = {"id": 1, "email": "admin@test.com"}

        # Criar usuários de teste
        db_session.execute(
            text("""
                INSERT INTO users (id, email, nome, tenant_id, plano, status, creditos, plano_pago)
                VALUES
                    (200, 'alice@test.com', 'Alice', 200, 'pro', 'ativo', 200, true),
                    (201, 'bob@test.com', 'Bob', 201, 'starter', 'ativo', 100, true),
                    (202, 'charlie@test.com', 'Charlie', 202, 'trial', 'trial', 1, false)
            """)
        )
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, user_id, status, processado)
                VALUES
                    ('lead-a', 'Lead A', 200, 'concluido', true),
                    ('lead-b', 'Lead B', 200, 'pendente', false),
                    ('lead-c', 'Lead C', 201, 'concluido', true)
            """)
        )
        db_session.commit()

        result = list_users(db=db_session, user=mock_user)

        assert result["ok"] is True
        assert "users" in result
        assert "total" in result
        assert result["total"] == 3

        # Verificar estrutura de usuário
        user = result["users"][0]
        assert "id" in user
        assert "email" in user
        assert "plano" in user
        assert "creditos" in user
        assert "total_leads" in user
        assert "sites_prontos" in user


class TestSuperadminToggleUser:
    """Testes para ativar/desativar usuários."""

    def test_toggle_user_bloqueia_usuario(self, db_session):
        """Toggle deve bloquear usuário ativo."""
        from backend.endpoints.superadmin_endpoints import toggle_user

        mock_user = {"id": 1, "email": "admin@test.com"}

        # Criar usuário ativo
        db_session.execute(
            text("""
                INSERT INTO users (id, email, status)
                VALUES (300, 'user-toggle@test.com', 'ativo')
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        result = toggle_user(
            user_id=300,
            request=mock_request,
            db=db_session,
            user=mock_user
        )

        assert result["ok"] is True
        assert result["new_status"] == "bloqueado"

    def test_toggle_user_desbloqueia_usuario(self, db_session):
        """Toggle deve desbloquear usuário bloqueado."""
        from backend.endpoints.superadmin_endpoints import toggle_user

        mock_user = {"id": 1, "email": "admin@test.com"}

        db_session.execute(
            text("""
                INSERT INTO users (id, email, status)
                VALUES (301, 'user-untoggle@test.com', 'bloqueado')
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        result = toggle_user(
            user_id=301,
            request=mock_request,
            db=db_session,
            user=mock_user
        )

        assert result["ok"] is True
        assert result["new_status"] == "ativo"

    def test_toggle_superadmin_nao_permitido(self, db_session):
        """Não deve ser possível desativar superadmin."""
        from fastapi import HTTPException
        from backend.endpoints.superadmin_endpoints import toggle_user
        from backend.core.config import SUPERADMIN_EMAILS

        mock_user = {"id": 1, "email": "admin@test.com"}

        # Inserir superadmin
        if SUPERADMIN_EMAILS:
            admin_email = SUPERADMIN_EMAILS[0]
        else:
            admin_email = "superadmin@fralib.com"

        db_session.execute(
            text("""
                INSERT INTO users (id, email, status)
                VALUES (302, :email, 'ativo')
            """),
            {"email": admin_email}
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        with pytest.raises(HTTPException) as exc_info:
            toggle_user(
                user_id=302,
                request=mock_request,
                db=db_session,
                user=mock_user
            )

        assert exc_info.value.status_code == 403

    def test_toggle_usuario_inexistente_retorna_404(self, db_session):
        """Toggle em usuário inexistente retorna 404."""
        from fastapi import HTTPException
        from backend.endpoints.superadmin_endpoints import toggle_user

        mock_user = {"id": 1, "email": "admin@test.com"}

        mock_request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            toggle_user(
                user_id=99999,
                request=mock_request,
                db=db_session,
                user=mock_user
            )

        assert exc_info.value.status_code == 404


class TestSuperadminSetPlan:
    """Testes para alteração de plano."""

    def test_set_plan_pro_sucesso(self, db_session):
        """Alteração para plano pro deve funcionar."""
        from backend.endpoints.superadmin_endpoints import set_plan

        mock_user = {"id": 1, "email": "admin@test.com"}

        db_session.execute(
            text("""
                INSERT INTO users (id, email, plano, status, creditos)
                VALUES (400, 'user-plan@test.com', 'trial', 'trial', 1)
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"
        mock_request.json = AsyncMock(return_value={"plano": "pro"})

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            set_plan(
                user_id=400,
                request=mock_request,
                db=db_session,
                user=mock_user
            )
        )

        assert result["ok"] is True
        assert result["plano"] == "pro"

        user = db_session.execute(
            text("SELECT plano, plano_pago, status, creditos FROM users WHERE id = :id"),
            {"id": 400}
        ).fetchone()

        assert user.plano == "pro"
        assert user.plano_pago is True
        assert user.status == "ativo"
        assert user.creditos == 360

    def test_set_plan_starter_nao_e_pago(self, db_session):
        """Plano starter não deve ser pago."""
        from backend.endpoints.superadmin_endpoints import set_plan

        mock_user = {"id": 1, "email": "admin@test.com"}

        db_session.execute(
            text("""
                INSERT INTO users (id, email, plano, plano_pago, status)
                VALUES (401, 'user-starter@test.com', 'trial', false, 'trial')
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"plano": "starter"})

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            set_plan(
                user_id=401,
                request=mock_request,
                db=db_session,
                user=mock_user
            )
        )

        assert result["ok"] is True

        user = db_session.execute(
            text("SELECT plano_pago, status FROM users WHERE id = :id"),
            {"id": 401}
        ).fetchone()

        assert user.plano_pago is False

    def test_set_plan_invalido_retorna_erro(self, db_session):
        """Plano inválido deve retornar erro 400."""
        from fastapi import HTTPException
        from backend.endpoints.superadmin_endpoints import set_plan

        mock_user = {"id": 1, "email": "admin@test.com"}

        db_session.execute(
            text("""
                INSERT INTO users (id, email)
                VALUES (402, 'user-invalid@test.com')
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"plano": "plano_inexistente"})

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                set_plan(
                    user_id=402,
                    request=mock_request,
                    db=db_session,
                    user=mock_user
                )
            )

        assert exc_info.value.status_code == 400


class TestSuperadminSetCreditos:
    """Testes para definição manual de créditos."""

    def test_set_creditos_sucesso(self, db_session):
        """Definição de créditos deve funcionar."""
        from backend.endpoints.superadmin_endpoints import set_creditos

        mock_user = {"id": 1, "email": "admin@test.com"}

        db_session.execute(
            text("""
                INSERT INTO users (id, email, creditos, creditos_max)
                VALUES (500, 'user-creditos@test.com', 100, 180)
            """)
        )
        db_session.commit()

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.json = AsyncMock(return_value={"creditos": 500})

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            set_creditos(
                user_id=500,
                request=mock_request,
                db=db_session,
                user=mock_user
            )
        )

        assert result["ok"] is True
        assert result["creditos"] == 500

        user = db_session.execute(
            text("SELECT creditos, creditos_max FROM users WHERE id = :id"),
            {"id": 500}
        ).fetchone()

        assert user.creditos == 500
        assert user.creditos_max == 500


class TestSuperadminUsage:
    """Testes para consulta de uso de tokens."""

    def test_get_usage_retorna_timeline(self, db_session):
        """Deve retornar timeline de uso."""
        from backend.endpoints.superadmin_endpoints import get_usage

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = get_usage(db=db_session, user=mock_user, periodo="48h")

        assert result["ok"] is True
        assert result["periodo"] == "48h"
        assert "totals" in result
        assert "totals_all" in result
        assert "timeline" in result
        assert "by_agent" in result
        assert "by_user" in result

    def test_get_usage_periodo_invalido_default_48h(self, db_session):
        """Período inválido deve usar default de 48h."""
        from backend.endpoints.superadmin_endpoints import get_usage

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = get_usage(db=db_session, user=mock_user, periodo="invalid")

        assert result["periodo"] == "48h"


class TestSuperadminDashboardOverview:
    """Testes para dashboard de overview."""

    def test_dashboard_overview_retorna_kpis(self, db_session):
        """Deve retornar KPIs principais."""
        from backend.endpoints.superadmin_endpoints import dashboard_overview

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = dashboard_overview(db=db_session, user=mock_user)

        assert "sites" in result
        assert "taxa_sucesso_24h" in result
        assert "falhas_24h" in result
        assert "custo" in result
        assert "fila" in result


class TestSuperadminDashboardPipeline:
    """Testes para dashboard de pipeline."""

    def test_dashboard_pipeline_retorna_metricas(self, db_session):
        """Deve retornar métricas de pipeline."""
        from backend.endpoints.superadmin_endpoints import dashboard_pipeline

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = dashboard_pipeline(db=db_session, user=mock_user, period="7d")

        assert "total_runs" in result
        assert "sucesso" in result
        assert "falhas" in result
        assert "taxa_sucesso" in result
        assert "falhas_por_fase" in result
        assert "tempo_por_fase" in result


class TestSuperadminDashboardCosts:
    """Testes para dashboard de custos."""

    def test_dashboard_costs_por_dia(self, db_session):
        """Deve retornar custos agrupados por dia."""
        from backend.endpoints.superadmin_endpoints import dashboard_costs

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = dashboard_costs(db=db_session, user=mock_user, period="7d", group_by="day")

        assert result["group_by"] == "day"
        assert "data" in result

    def test_dashboard_costs_por_agente(self, db_session):
        """Deve retornar custos por agente."""
        from backend.endpoints.superadmin_endpoints import dashboard_costs

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = dashboard_costs(db=db_session, user=mock_user, period="7d", group_by="agent")

        assert result["group_by"] == "agent"
        assert "data" in result

    def test_dashboard_costs_por_modelo(self, db_session):
        """Deve retornar custos por modelo."""
        from backend.endpoints.superadmin_endpoints import dashboard_costs

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = dashboard_costs(db=db_session, user=mock_user, period="7d", group_by="model")

        assert result["group_by"] == "model"
        assert "data" in result


class TestSuperadminQueueControls:
    """Testes para controles de fila."""

    def test_pause_queue_retorna_sucesso(self, db_session):
        """Pausa de fila deve funcionar."""
        from backend.endpoints.superadmin_endpoints import pause_queue

        mock_user = {"id": 1, "email": "admin@test.com"}

        mock_request = MagicMock()

        result = pause_queue(db=db_session, user=mock_user, request=mock_request)

        assert result["ok"] is True
        assert "pausada" in result["mensagem"]

    def test_resume_queue_retorna_sucesso(self, db_session):
        """Retomada de fila deve funcionar."""
        from backend.endpoints.superadmin_endpoints import resume_queue

        mock_user = {"id": 1, "email": "admin@test.com"}

        mock_request = MagicMock()

        result = resume_queue(db=db_session, user=mock_user, request=mock_request)

        assert result["ok"] is True
        assert "retomada" in result["mensagem"]


class TestSuperadminCostsProjection:
    """Testes para projeção de custos."""

    def test_costs_projection_retorna_projecao(self, db_session):
        """Deve retornar projeção mensal de custos."""
        from backend.endpoints.superadmin_endpoints import costs_projection

        mock_user = {"id": 1, "email": "admin@test.com"}

        result = costs_projection(db=db_session, user=mock_user)

        assert "custo_7d" in result
        assert "custo_diario_medio" in result
        assert "projecao_mensal" in result
        assert "runs_diario_medio" in result
        assert "projecao_runs_mensal" in result
