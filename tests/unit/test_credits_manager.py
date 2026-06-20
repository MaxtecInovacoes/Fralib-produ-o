"""
Testes unitários para credits_manager.py

Cobre as operações de gerenciamento de créditos:
- Verificação de permissão para executar pipeline
- Débito de créditos
- Recarga de créditos
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

# Setup path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from sqlalchemy import text


class TestVerificacaoCredito:
    """Testes para verificação de crédito e permissão de pipeline."""

    def test_validar_permissao_pipeline_usuario_nao_encontrado(self, db_session):
        """Usuário inexistente deve retornar allowed=False."""
        from backend.services.credits_manager import validar_permissao_pipeline

        result = validar_permissao_pipeline(db_session, 99999)

        assert result["allowed"] is False
        assert result["reason"] == "user_not_found"

    def test_validar_permissao_pipeline_usuario_bloqueado(self, db_session, test_user):
        """Usuário com status bloqueado deve ser negado."""
        from backend.services.credits_manager import validar_permissao_pipeline

        # Atualizar status para bloqueado
        db_session.execute(
            text("UPDATE users SET status = 'bloqueado' WHERE id = :id"),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = validar_permissao_pipeline(db_session, test_user["id"])

        assert result["allowed"] is False
        assert result["reason"] == "status_bloqueado"

    def test_validar_permissao_pipeline_trial_com_credito(self, db_session, test_user):
        """Usuário trial com crédito disponível deve ser permitido."""
        from backend.services.credits_manager import validar_permissao_pipeline

        # Trial com 1 crédito
        db_session.execute(
            text("""
                UPDATE users SET plano = 'trial', plano_pago = false,
                creditos = 1, status = 'trial'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = validar_permissao_pipeline(db_session, test_user["id"])

        assert result["allowed"] is True
        assert result["plano"] == "trial"
        assert result["creditos_restantes"] == 1

    def test_validar_permissao_pipeline_trial_sem_credito(self, db_session, test_user):
        """Usuário trial sem créditos deve ser negado."""
        from backend.services.credits_manager import validar_permissao_pipeline

        db_session.execute(
            text("""
                UPDATE users SET plano = 'trial', plano_pago = false,
                creditos = 0, status = 'trial'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = validar_permissao_pipeline(db_session, test_user["id"])

        assert result["allowed"] is False
        assert result["reason"] == "limite_plano"
        assert result["action"] == "upgrade"

    def test_validar_permissao_pipeline_plano_ilimitado(self, db_session, test_user):
        """Usuário com plano ilimitado deve ter créditos altos."""
        from backend.services.credits_manager import validar_permissao_pipeline

        db_session.execute(
            text("""
                UPDATE users SET plano = 'ilimitado', plano_pago = true,
                creditos = 0, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = validar_permissao_pipeline(db_session, test_user["id"])

        assert result["allowed"] is True
        assert result["creditos_restantes"] == 99999
        assert result["limite_mensal"] == 99999

    def test_validar_permissao_pipeline_cooldown_ativo(self, db_session, test_user):
        """Pipeline em cooldown deve ser negado com tempo restante."""
        from backend.services.credits_manager import validar_permissao_pipeline

        # Criar usuário pro com cooldown recente
        agora = datetime.now()
        db_session.execute(
            text("""
                UPDATE users SET plano = 'pro', plano_pago = true,
                creditos = 100, ultimo_deploy_at = :ts, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"], "ts": agora}
        )
        db_session.commit()

        result = validar_permissao_pipeline(db_session, test_user["id"])

        assert result["allowed"] is False
        assert result["reason"] == "cooldown"
        assert "cooldown_restante_seg" in result


class TestDebitoCredito:
    """Testes para débito de créditos."""

    def test_consumir_credito_diario_starter(self, db_session, test_user):
        """Débito deve decrementar créditos para plano starter."""
        from backend.services.credits_manager import consumir_credito_diario

        db_session.execute(
            text("""
                UPDATE users SET plano = 'starter', plano_pago = true,
                creditos = 180, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consumir_credito_diario(db_session, test_user["id"], "Restaurante Teste")

        assert result is True

        # Verificar que crédito foi decrementado
        user = db_session.execute(
            text("SELECT creditos, sites_used FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()
        assert user.creditos == 179
        assert user.sites_used == 1

    def test_consumir_credito_diario_nao_fica_negativo(self, db_session, test_user):
        """Crédito não deve ficar negativo após débito."""
        from backend.services.credits_manager import consumir_credito_diario

        db_session.execute(
            text("""
                UPDATE users SET plano = 'starter', plano_pago = true,
                creditos = 0, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consumir_credito_diario(db_session, test_user["id"], "Teste")

        assert result is True

        user = db_session.execute(
            text("SELECT creditos FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()
        assert user.creditos == 0

    def test_consumir_credito_ilimitado_nao_decrementa(self, db_session, test_user):
        """Plano ilimitado não deve ter créditos decrementados."""
        from backend.services.credits_manager import consumir_credito_diario

        db_session.execute(
            text("""
                UPDATE users SET plano = 'ilimitado', plano_pago = true,
                creditos = 0, sites_used = 5, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consumir_credito_diario(db_session, test_user["id"], "Teste Ilimitado")

        assert result is True

        user = db_session.execute(
            text("SELECT sites_used FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()
        assert user.sites_used == 6

    def test_consumir_credito_diario_registra_transacao(self, db_session, test_user):
        """Débito deve registrar transação no histórico."""
        from backend.services.credits_manager import consumir_credito_diario

        db_session.execute(
            text("""
                UPDATE users SET plano = 'pro', plano_pago = true,
                creditos = 50, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        consumir_credito_diario(db_session, test_user["id"], "Lead Restaurante")

        # Verificar transação
        transacao = db_session.execute(
            text("""
                SELECT tipo, tokens_consumidos, descricao
                FROM token_transactions
                WHERE user_id = :uid
                ORDER BY id DESC LIMIT 1
            """),
            {"uid": test_user["id"]}
        ).fetchone()

        assert transacao is not None
        assert transacao.tipo == "ciclo"
        assert transacao.tokens_consumidos == 1
        assert "Lead Restaurante" in transacao.descricao


class TestRecargaCredito:
    """Testes para recarga automática de créditos."""

    def test_reset_mensal_lazy_recarrega_no_mes_novo(self, db_session, test_user):
        """Créditos devem ser recarregados quando muda o mês."""
        from backend.services.credits_manager import _reset_mensal_lazy, PLAN_CREDITOS_PADRAO

        # Simular último reset em mês anterior
        mes_passado = (datetime.now() - timedelta(days=40)).replace(day=1).date().isoformat()
        db_session.execute(
            text("""
                UPDATE users SET plano = 'pro', plano_pago = true,
                creditos = 0, last_reset_date = :last_reset
                WHERE id = :id
            """),
            {"id": test_user["id"], "last_reset": mes_passado}
        )
        db_session.commit()

        limite_pro = PLAN_CREDITOS_PADRAO.get("pro", 360)

        result = _reset_mensal_lazy(db_session, test_user["id"], "pro", 0)

        assert result == limite_pro

        user = db_session.execute(
            text("SELECT creditos, last_reset_date FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()
        assert user.creditos == limite_pro
        assert user.last_reset_date is not None

    def test_reset_mensal_lazy_nao_recarrega_no_mes_atual(self, db_session, test_user):
        """Créditos não devem ser recarregados se reset foi este mês."""
        from backend.services.credits_manager import _reset_mensal_lazy

        hoje = datetime.now().date().isoformat()
        db_session.execute(
            text("""
                UPDATE users SET plano = 'pro', plano_pago = true,
                creditos = 100, last_reset_date = :last_reset
                WHERE id = :id
            """),
            {"id": test_user["id"], "last_reset": hoje}
        )
        db_session.commit()

        result = _reset_mensal_lazy(db_session, test_user["id"], "pro", 100)

        # Não deve recarregar, retorna créditos atuais
        assert result == 100


class TestPlanoTemSDR:
    """Testes para verificação de SDR por plano."""

    def test_plano_pro_tem_sdr(self):
        """Plano pro deve ter SDR disponível."""
        from backend.services.credits_manager import plano_tem_sdr

        assert plano_tem_sdr("pro", "ativo", None) is True

    def test_plano_starter_nao_tem_sdr(self):
        """Plano starter não deve ter SDR."""
        from backend.services.credits_manager import plano_tem_sdr

        assert plano_tem_sdr("starter", "ativo", None) is False

    def test_plano_agency_tem_sdr(self):
        """Plano agency deve ter SDR."""
        from backend.services.credits_manager import plano_tem_sdr

        assert plano_tem_sdr("agency", "ativo", None) is True

    def test_usuario_bloqueado_nao_tem_sdr(self):
        """Usuário bloqueado não deve ter SDR mesmo com plano pro."""
        from backend.services.credits_manager import plano_tem_sdr

        assert plano_tem_sdr("pro", "bloqueado", None) is False

    def test_trial_ativo_tem_sdr(self):
        """Trial ativo deve ter SDR."""
        from backend.services.credits_manager import plano_tem_sdr

        assert plano_tem_sdr("trial", "ativo", None) is True


class TestGetUserTokens:
    """Testes para consulta de tokens do usuário."""

    def test_get_user_tokens_retorna_estrutura_correta(self, db_session, test_user):
        """Deve retornar estrutura completa com todos os campos."""
        from backend.services.credits_manager import get_user_tokens

        db_session.execute(
            text("""
                UPDATE users SET
                    plano = 'pro', creditos = 250, creditos_max = 360,
                    plano_pago = true, status = 'ativo', sites_used = 10,
                    sites_hoje = 2
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = get_user_tokens(db_session, test_user["id"])

        assert "user_id" in result
        assert "email" in result
        assert "plano" in result
        assert "creditos" in result
        assert "creditos_max" in result
        assert "limite_diario" in result
        assert "limite_mensal" in result
        assert result["plano"] == "pro"
        assert result["creditos"] == 250

    def test_get_user_tokens_usuario_inexistente(self, db_session):
        """Usuário inexistente deve retornar erro."""
        from backend.services.credits_manager import get_user_tokens

        result = get_user_tokens(db_session, 99999)

        assert "erro" in result


class TestConsumeEdicao:
    """Testes para consumo de créditos de edição."""

    def test_consume_edicao_plano_pro_sucesso(self, db_session, test_user):
        """Edição em plano pro deve consumir 1 crédito."""
        from backend.services.credits_manager import consume_edicao

        db_session.execute(
            text("""
                UPDATE users SET plano = 'pro', plano_pago = true,
                creditos = 10, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consume_edicao(db_session, test_user["id"])

        assert result is True

        user = db_session.execute(
            text("SELECT creditos FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()
        assert user.creditos == 9

    def test_consume_edicao_plano_ilimitado_nao_consome(self, db_session, test_user):
        """Edição em plano ilimitado não deve consumir créditos."""
        from backend.services.credits_manager import consume_edicao

        db_session.execute(
            text("""
                UPDATE users SET plano = 'ilimitado', plano_pago = true,
                creditos = 0, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consume_edicao(db_session, test_user["id"])

        assert result is True

    def test_consume_edicao_plano_starter_bloqueado(self, db_session, test_user):
        """Edição em plano starter deve ser bloqueada."""
        from backend.services.credits_manager import consume_edicao

        db_session.execute(
            text("""
                UPDATE users SET plano = 'starter', plano_pago = true,
                creditos = 100, status = 'ativo'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = consume_edicao(db_session, test_user["id"])

        assert result is False


class TestAtivarPlano:
    """Testes para ativação de plano."""

    def test_ativar_plano_pro(self, db_session, test_user):
        """Ativação de plano pro deve configurar corretamente."""
        from backend.services.credits_manager import ativar_plano

        db_session.execute(
            text("""
                UPDATE users SET plano = 'trial', plano_pago = false,
                creditos = 1, status = 'trial'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.commit()

        result = ativar_plano(db_session, test_user["id"], "pro")

        assert result is True

        user = db_session.execute(
            text("SELECT plano, plano_pago, creditos, status FROM users WHERE id = :id"),
            {"id": test_user["id"]}
        ).fetchone()

        assert user.plano == "pro"
        assert user.plano_pago is True
        assert user.creditos == 360  # Limite do pro
        assert user.status == "ativo"


class TestTrialCreditWait:
    """Testes para lógica de crédito trial aguardando SDR."""

    def test_trial_credit_waits_for_sdr_delivery_true(self, db_session, test_user):
        """Trial deve aguardar entrega SDR antes de consumir crédito."""
        from backend.services.credits_manager import trial_credit_waits_for_sdr_delivery

        # Trial com site concluído mas SDR pendente
        db_session.execute(
            text("""
                UPDATE users SET plano = 'trial', plano_pago = false,
                creditos = 1, status = 'trial', trial_expires_at = null
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, user_id, status, sdr_stage)
                VALUES ('lead-trial', 'Teste Trial', :uid, 'concluido', 'pendente_wpp')
            """),
            {"uid": test_user["id"]}
        )
        db_session.commit()

        result = trial_credit_waits_for_sdr_delivery(db_session, test_user["id"])

        assert result is True

    def test_trial_credit_waits_for_sdr_delivery_false(self, db_session, test_user):
        """Trial sem SDR pendente não deve aguardar."""
        from backend.services.credits_manager import trial_credit_waits_for_sdr_delivery

        db_session.execute(
            text("""
                UPDATE users SET plano = 'trial', plano_pago = false,
                creditos = 1, status = 'trial'
                WHERE id = :id
            """),
            {"id": test_user["id"]}
        )
        # Não cria lead com SDR pendente
        db_session.commit()

        result = trial_credit_waits_for_sdr_delivery(db_session, test_user["id"])

        assert result is False
