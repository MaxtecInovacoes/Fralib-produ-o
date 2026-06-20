"""
Testes unitários para leads_endpoints.py

Cobre as operações CRUD dos leads:
- Criação manual de lead
- Listagem de leads
- Deleção de lead
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

# Setup path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'backend'))


class TestLeadManualCreation:
    """Testes para a criação manual de leads via POST /api/leads/manual"""

    def test_criar_lead_manual_sem_briefing_retorna_lead_id(self, db_session, test_user):
        """Criação de lead sem briefing deve retornar lead_id sem job_id."""
        from backend.endpoints.leads_crud import criar_lead_manual
        from backend.endpoints.leads_crud_models import LeadManualRequest

        req = LeadManualRequest(
            nome="João Silva",
            telefone="11999999999",
            whatsapp="11988888888",
            nicho="Advocacia",
            cidade="São Paulo",
            score=75
        )

        # Mock do background_tasks
        mock_bg = MagicMock()

        result = criar_lead_manual(
            req=req,
            background_tasks=mock_bg,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True
        assert "lead_id" in result
        assert result["job_id"] is None
        assert "Lead criado" in result["mensagem"]

        # Verificar que lead foi inserido no banco
        lead = db_session.execute(
            text("SELECT * FROM leads WHERE id = :id"),
            {"id": result["lead_id"]}
        ).fetchone()

        assert lead is not None
        assert lead.nome == "João Silva"
        assert lead.cidade == "São Paulo"
        assert lead.segmento == "Advocacia"

    def test_criar_lead_manual_com_briefing_retorna_job_id(self, db_session, test_user):
        """Criação de lead com briefing deve retornar job_id para o pipeline."""
        from backend.endpoints.leads_crud import criar_lead_manual
        from backend.endpoints.leads_crud_models import LeadManualRequest

        req = LeadManualRequest(
            nome="Maria Santos",
            telefone="21999999999",
            nicho="Restaurante",
            cidade="Rio de Janeiro",
            briefing="Preciso de um site para meu restaurante italiano",
            score=80
        )

        mock_bg = MagicMock()

        # Mock do job_queue para não falhar
        with patch('backend.endpoints.leads_crud.job_queue') as mock_jq:
            mock_jq.enqueue.return_value = "job-123-abc"

            result = criar_lead_manual(
                req=req,
                background_tasks=mock_bg,
                db=db_session,
                usuario=test_user
            )

        assert result["ok"] is True
        assert "lead_id" in result
        assert result["job_id"] == "job-123-abc"
        assert "Site enfileirado" in result["mensagem"]

    def test_criar_lead_com_telefone_vazio_usa_telefone_como_whatsapp(self, db_session, test_user):
        """Quando whatsapp não é fornecido, deve usar o telefone como whatsapp."""
        from backend.endpoints.leads_crud import criar_lead_manual
        from backend.endpoints.leads_crud_models import LeadManualRequest

        req = LeadManualRequest(
            nome="Pedro Costa",
            telefone="31977777777",
            nicho="Clinica",
            cidade="Belo Horizonte"
        )

        mock_bg = MagicMock()

        result = criar_lead_manual(
            req=req,
            background_tasks=mock_bg,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True

        # Verificar que whatsapp foi preenchido com telefone
        lead = db_session.execute(
            text("SELECT whatsapp, telefone_whatsapp FROM leads WHERE id = :id"),
            {"id": result["lead_id"]}
        ).fetchone()

        assert lead.whatsapp == "31977777777"
        assert lead.telefone_whatsapp == "31977777777"


class TestLeadDeletion:
    """Testes para a deleção de leads via DELETE /api/leads/{lead_id}"""

    def test_deletar_lead_existente_retorna_sucesso(self, db_session, test_user):
        """Deleção de lead existente deve retornar sucesso."""
        from backend.endpoints.leads_crud import deletar_lead

        # Criar lead primeiro
        lead_id = "lead-test-delete-123"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Lead para Deletar", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = deletar_lead(
            lead_id=lead_id,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True
        assert "deletado com sucesso" in result["mensagem"]

        # Verificar que lead foi removido
        lead = db_session.execute(
            text("SELECT id FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead is None

    def test_deletar_lead_inexistente_retorna_404(self, db_session, test_user):
        """Deleção de lead inexistente deve retornar 404."""
        from fastapi import HTTPException

        from backend.endpoints.leads_crud import deletar_lead

        with pytest.raises(HTTPException) as exc_info:
            deletar_lead(
                lead_id="lead-inexistente-999",
                db=db_session,
                usuario=test_user
            )

        assert exc_info.value.status_code == 404
        assert "não encontrado" in exc_info.value.detail

    def test_deletar_lead_remove_interacoes_relacionadas(self, db_session, test_user):
        """Deleção de lead deve remover interações associadas."""
        from backend.endpoints.leads_crud import deletar_lead

        # Criar lead e interações
        lead_id = "lead-with-interacoes"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Lead com Interações", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.execute(
            text("""
                INSERT INTO interacoes (lead_id, mensagem, direcao)
                VALUES (:lid, 'Olá!', 'entrada'), (:lid, 'Oi!', 'saida')
            """),
            {"lid": lead_id}
        )
        db_session.commit()

        # Verificar que interações existem
        interacoes_before = db_session.execute(
            text("SELECT COUNT(*) FROM interacoes WHERE lead_id = :lid"),
            {"lid": lead_id}
        ).scalar()
        assert interacoes_before == 2

        # Deletar lead
        result = deletar_lead(
            lead_id=lead_id,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True

        # Verificar que interações foram removidas
        interacoes_after = db_session.execute(
            text("SELECT COUNT(*) FROM interacoes WHERE lead_id = :lid"),
            {"lid": lead_id}
        ).scalar()
        assert interacoes_after == 0


class TestLeadUpdate:
    """Testes para atualização de leads via PATCH /api/leads/{lead_id}"""

    def test_atualizar_lead_campos_permitidos(self, db_session, test_user):
        """Atualização deve aceitar apenas campos permitidos."""
        from backend.endpoints.leads_crud import atualizar_lead

        # Criar lead
        lead_id = "lead-para-atualizar"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Nome Antigo", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = atualizar_lead(
            lead_id=lead_id,
            request_data={"nome": "Nome Novo", "status": "qualificado"},
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True

        # Verificar atualização
        lead = db_session.execute(
            text("SELECT nome, status FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.nome == "Nome Novo"
        assert lead.status == "qualificado"

    def test_atualizar_lead_sem_campos_retorna_ok(self, db_session, test_user):
        """Atualização sem campos deve retornar ok sem modificar nada."""
        from backend.endpoints.leads_crud import atualizar_lead

        lead_id = "lead-sem-campos"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Nome Original", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = atualizar_lead(
            lead_id=lead_id,
            request_data={},
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True

        # Nome não deve ter mudado
        lead = db_session.execute(
            text("SELECT nome FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.nome == "Nome Original"

    def test_atualizar_lead_alias_whatsapp(self, db_session, test_user):
        """Campo 'whatsapp' deve ser mapeado para 'telefone_whatsapp'."""
        from backend.endpoints.leads_crud import atualizar_lead

        lead_id = "lead-whatsapp-alias"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Teste", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = atualizar_lead(
            lead_id=lead_id,
            request_data={"whatsapp": "11988888888"},
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True

        lead = db_session.execute(
            text("SELECT telefone_whatsapp FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.telefone_whatsapp == "11988888888"


class TestLeadListing:
    """Testes para listagem de leads."""

    def test_get_leads_capturados_retorna_lista(self, db_session, test_user):
        """Listagem de leads capturados deve retornar estrutura correta."""
        # Criar leads capturados
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, cidade, segmento, user_id, status, score, tier)
                VALUES
                    ('cap-1', 'Restaurante A', 'São Paulo', 'Restaurante', :uid, 'capturado', 70, 'STANDARD'),
                    ('cap-2', 'Bar B', 'Rio de Janeiro', 'Bar', :uid, 'capturado', 85, 'PREMIUM')
            """),
            {"uid": test_user["tenant_id"]}
        )
        db_session.commit()

        from backend.endpoints.leads_queries import get_leads_capturados

        result = get_leads_capturados(db=db_session, usuario=test_user)

        assert "leads" in result
        assert "total" in result
        assert result["total"] == 2
        assert len(result["leads"]) == 2

    def test_get_leads_incompletos_retorna_leads_incompletos(self, db_session, test_user):
        """Listagem de leads incompletos deve filtrar por score e status."""
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, cidade, segmento, user_id, status, score)
                VALUES
                    ('inc-1', 'Teste A', 'SP', 'Bar', :uid, 'pendente', 15),
                    ('inc-2', NULL, 'RJ', 'Restaurante', :uid, 'pendente', 60),
                    ('inc-3', 'Teste C', 'BH', 'Clinica', :uid, 'rejeitado', 50)
            """),
            {"uid": test_user["tenant_id"]}
        )
        db_session.commit()

        from backend.endpoints.leads_queries import get_leads_incompletos

        result = get_leads_incompletos(db=db_session, usuario=test_user)

        assert "leads" in result
        assert "total" in result
        # Deve incluir: score < 20 (inc-1), nome NULL (inc-2), status = rejeitado (inc-3)
        assert result["total"] >= 3


class TestLeadStatusTransitions:
    """Testes para transições de status de leads."""

    def test_aprovar_lead_pipeline_muda_status_para_qualificado(self, db_session, test_user):
        """Aprovação manual deve mudar status para 'qualificado'."""
        from backend.endpoints.leads_crud import aprobar_lead_pipeline

        lead_id = "lead-para-aprovar"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status, score)
                VALUES (:id, :nome, :tel, :uid, 'pendente', 20)
            """),
            {"id": lead_id, "nome": "Lead Aprovado", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = aprobar_lead_pipeline(
            lead_id=lead_id,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True
        assert "aprovado" in result["mensagem"].lower()

        lead = db_session.execute(
            text("SELECT status, score FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.status == "qualificado"
        assert lead.score == 50

    def test_descartar_lead_muda_status_para_descartado(self, db_session, test_user):
        """Descartar lead deve mudar status para 'descartado'."""
        from backend.endpoints.leads_queries import descartar_lead

        lead_id = "lead-para-descartar"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Lead Descartado", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        result = descartar_lead(
            lead_id=lead_id,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True
        assert "descartado" in result["mensagem"].lower()

        lead = db_session.execute(
            text("SELECT status FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.status == "descartado"


class TestLeadFeedback:
    """Testes para registro de feedback de leads."""

    def test_registrar_feedback_convertido_atualiza_status(self, db_session, test_user):
        """Feedback 'convertido' deve atualizar status do lead."""
        from backend.endpoints.leads_crud_models import FeedbackRequest
        from backend.endpoints.leads_crud_sdr import registrar_feedback

        lead_id = "lead-para-feedback"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, segmento, user_id, status)
                VALUES (:id, :nome, :tel, :seg, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Lead Feedback", "tel": "11999999999", "seg": "Restaurante", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        req = FeedbackRequest(resultado="convertido", observacao="Fechou contrato!")

        result = registrar_feedback(
            lead_id=lead_id,
            req=req,
            db=db_session,
            usuario=test_user
        )

        assert result["ok"] is True
        assert "convertido" in result["mensagem"].lower()

        lead = db_session.execute(
            text("SELECT status FROM leads WHERE id = :id"),
            {"id": lead_id}
        ).fetchone()
        assert lead.status == "convertido"

    def test_registrar_feedback_resultado_invalido_retorna_erro(self, db_session, test_user):
        """Feedback com resultado inválido deve retornar erro 400."""
        from fastapi import HTTPException

        from backend.endpoints.leads_crud_models import FeedbackRequest
        from backend.endpoints.leads_crud_sdr import registrar_feedback

        lead_id = "lead-feedback-invalido"
        db_session.execute(
            text("""
                INSERT INTO leads (id, nome, telefone, user_id, status)
                VALUES (:id, :nome, :tel, :uid, 'pendente')
            """),
            {"id": lead_id, "nome": "Teste", "tel": "11999999999", "uid": test_user["tenant_id"]}
        )
        db_session.commit()

        req = FeedbackRequest(resultado="invalido", observacao="")

        with pytest.raises(HTTPException) as exc_info:
            registrar_feedback(
                lead_id=lead_id,
                req=req,
                db=db_session,
                usuario=test_user
            )

        assert exc_info.value.status_code == 400
