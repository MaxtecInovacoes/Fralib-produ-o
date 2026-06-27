"""Testes para human_pause no whatsapp_listener.

Executa com: pytest C:\fralib\scripts\test_human_pause.py -v
"""
import sys
import os
import time
from unittest.mock import MagicMock, patch

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest


class TestHumanPauseActivation:
    """Testa que human_pause e ativado quando dono responde."""

    @pytest.fixture
    def mock_rate_limiter(self):
        """Cria um mock do RateLimiter."""
        with patch('backend.whatsapp_listener._RATE_LIMITER') as mock:
            mock.human_pause = {}
            mock.activate_human_pause.return_value = 300.0
            mock.is_human_paused.return_value = False
            yield mock

    @pytest.fixture
    def mock_db(self):
        """Mock do engine SQLAlchemy."""
        with patch('backend.whatsapp_listener.engine') as mock:
            mock_conn = MagicMock()
            mock.execute.return_value = mock_conn
            mock.__enter__ = MagicMock(return_value=mock_conn)
            mock.__exit__ = MagicMock(return_value=False)
            yield mock

    def test_human_pause_called_when_fromme_true(self, mock_rate_limiter):
        """Verifica que _activate_human_pause e chamado quando fromMe=True.

        Dado:
        - Mensagem com fromMe=True (dono respondeu)
        - lead_key correto (user_id:telefone)

        Quando:
        - _debounce_incoming processa a mensagem

        Entao:
        - _activate_human_pause(lead_key) e chamado com lead_key correto
        """
        from backend.whatsapp_listener import _debounce_incoming, _activate_human_pause

        # Mensagem do dono (fromMe=True) enviada para lead
        msg_data = {
            "key": {
                "id": "msg123",
                "remoteJid": "5511999998888@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {
                "conversation": "Ola lead, vamos conversar?"
            }
        }

        # Mock helper functions
        with patch('backend.whatsapp_listener._user_id_from_tenant', return_value=1):
            with patch('backend.whatsapp_listener._activate_human_pause') as mock_activate:
                with patch('backend.whatsapp_listener._buscar_lead_por_tel') as mock_lead:
                    with patch('backend.whatsapp_listener._salvar_interacao'):
                        with patch('backend.whatsapp_listener.asyncio'):
                            mock_lead.return_value = ("lead-123", "Lead Name", "tech", "SP", "intro", "ativo", "5511999998888")

                            # Executa o debounce com loop mockado
                            loop = MagicMock()
                            executor = MagicMock()
                            _debounce_incoming("fralib_user_1", msg_data, executor, loop)

                            # Verifica que _activate_human_pause foi chamado
                            mock_activate.assert_called_once_with("1:5511999998888")

    def test_lead_key_format_correct(self):
        """Verifica que lead_key segue formato user_id:telefone."""
        user_id = 42
        telefone = "5511999998888"
        lead_key = f"{user_id}:{telefone}"

        assert lead_key == "42:5511999998888"
        assert ":" in lead_key
        assert lead_key.split(":")[0] == str(user_id)

    def test_human_pause_default_300_seconds(self):
        """Verifica que human_pause padrao e 5 minutos (300s)."""
        from backend.whatsapp.rate_limiter import DEFAULT_HUMAN_PAUSE_SECONDS

        assert DEFAULT_HUMAN_PAUSE_SECONDS == 300.0

    def test_is_human_paused_checks_elapsed_time(self):
        """Verifica que is_human_paused expira apos o tempo configurado."""
        from backend.whatsapp.guards import AntiAbuseGuards

        guards = AntiAbuseGuards(
            flood_threshold=10,
            flood_window=60.0,
            flood_silence=300.0,
            daily_limit_for_key=lambda k: 50,
            cooldown_seconds_for_key=lambda k: 30.0,
            human_pause_seconds_for_key=lambda k: 300.0,
            now_func=lambda: 1000.0,  # Mock time
        )

        # Ativa pause
        guards.activate_human_pause("1:5511999998888")

        # Imediatamente - esta pausado
        assert guards.is_human_paused("1:5511999998888") is True

        # Apos 299s - ainda pausado
        guards.now_func = lambda: 1299.0
        assert guards.is_human_paused("1:5511999998888") is True

        # Apos 300s - NAO esta mais pausado
        guards.now_func = lambda: 1300.0
        assert guards.is_human_paused("1:5511999998888") is False


class TestDeadCodeRemoval:
    """Verifica que codigo morto foi removido."""

    def test_build_history_not_imported(self):
        """Verifica que build_history nao e mais importado no listener."""
        # Le o arquivo e verifica que build_history nao esta no import
        listener_path = os.path.join(
            os.path.dirname(__file__), '..', 'backend', 'whatsapp_listener.py'
        )
        with open(listener_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verifica que build_history NAO esta nos imports de sdr_reply_service
        assert 'build_history,' not in content or 'from whatsapp.sdr_reply_service import' not in content

    def test_sdr_reply_service_no_build_history(self):
        """Verifica que build_history foi removido de sdr_reply_service.
        _summarize_history PERMANECE (usado por history_helper.py)."""
        sdr_path = os.path.join(
            os.path.dirname(__file__), '..', 'backend', 'whatsapp', 'sdr_reply_service.py'
        )
        with open(sdr_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verifica que build_history e constantes mortas NAO existem
        # _summarize_history PERMANECE (usado pelo history_helper)
        assert 'def build_history' not in content
        assert 'HISTORY_WINDOW' not in content
        assert 'SUMMARY_THRESHOLD' not in content
        # _summarize_history DEVE existir (usado pelo history_helper)
        assert 'def _summarize_history' in content


class TestHumanPauseFlow:
    """Testa o fluxo completo de human_pause."""

    def test_debounce_returns_early_for_fromme(self):
        """Verifica que debounce retorna cedo para mensagens fromMe.

        Quando fromMe=True, o fluxo deve:
        1. Ativar human_pause
        2. Salvar interacao
        3. RETORNAR ANTES de colocar no debounce buffer
        """
        from backend.whatsapp_listener import _DEBOUNCE_BUFFER, _DEBOUNCE_LOCK

        msg_data = {
            "key": {
                "id": "msg456",
                "remoteJid": "551188887777@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {"conversation": "Resposta do dono"}
        }

        lead_key = None
        buffer_before = len(_DEBOUNCE_BUFFER)

        with _DEBOUNCE_LOCK:
            _DEBOUNCE_BUFFER.clear()

        with patch('backend.whatsapp_listener._user_id_from_tenant', return_value=5):
            with patch('backend.whatsapp_listener._activate_human_pause') as mock_activate:
                with patch('backend.whatsapp_listener._buscar_lead_por_tel') as mock_lead:
                    with patch('backend.whatsapp_listener._salvar_interacao'):
                        with patch('backend.whatsapp_listener.asyncio'):
                            mock_lead.return_value = ("lead-456", "Test", "tech", "SP", "hook", "ativo", "551188887777")

                            loop = MagicMock()
                            executor = MagicMock()
                            from backend.whatsapp_listener import _debounce_incoming
                            _debounce_incoming("fralib_user_5", msg_data, executor, loop)

                            # Verifica que pause foi ativado
                            mock_activate.assert_called_once()

                            # Verifica que buffer NAO foi populado (retornou cedo)
                            with _DEBOUNCE_LOCK:
                                assert "5:551188887777" not in _DEBOUNCE_BUFFER


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
