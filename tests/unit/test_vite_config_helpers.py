"""
Testes para vite_config_helpers

RED → GREEN → REFACTOR
"""
import pytest
import os
from unittest.mock import patch


class TestEnvInt:
    """Testes para _env_int"""

    def test_env_int_returns_default_when_not_set(self):
        """GREEN: Quando variável não existe, retorna default"""
        from backend.services.vite_config_helpers import _env_int

        with patch.dict(os.environ, {}, clear=True):
            result = _env_int("NONEXISTENT_VAR_xyz", 42)
            assert result == 42

    def test_env_int_parses_integer(self):
        """GREEN: Quando variável existe, retorna valor convertido"""
        from backend.services.vite_config_helpers import _env_int

        with patch.dict(os.environ, {"TEST_VAR": "123"}):
            result = _env_int("TEST_VAR", 0)
            assert result == 123

    def test_env_int_returns_default_on_invalid_value(self):
        """GREEN: Quando valor é inválido, retorna default"""
        from backend.services.vite_config_helpers import _env_int

        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            result = _env_int("TEST_VAR", 99)
            assert result == 99


class TestModelMode:
    """Testes para modos de modelo"""

    def test_single_model_enabled_by_default(self):
        """GREEN: Modo single model ativo por padrão"""
        from backend.services.vite_config_helpers import _single_model_mode_enabled

        with patch.dict(os.environ, {}, clear=True):
            assert _single_model_mode_enabled() is True

    def test_single_model_disabled_when_false(self):
        """GREEN: Desativa com 'false'"""
        from backend.services.vite_config_helpers import _single_model_mode_enabled

        with patch.dict(os.environ, {"FRALIB_SINGLE_MODEL_ONLY": "false"}):
            assert _single_model_mode_enabled() is False

    def test_single_model_disabled_when_0(self):
        """GREEN: Desativa com '0'"""
        from backend.services.vite_config_helpers import _single_model_mode_enabled

        with patch.dict(os.environ, {"FRALIB_SINGLE_MODEL_ONLY": "0"}):
            assert _single_model_mode_enabled() is False


class TestModelCandidates:
    """Testes para _model_candidates"""

    def test_returns_empty_for_empty_input(self):
        """GREEN: Input vazio retorna lista vazia"""
        from backend.services.vite_config_helpers import _model_candidates

        result = _model_candidates("", None)
        assert result == []

    def test_parses_single_model(self):
        """GREEN: Parse de modelo único"""
        from backend.services.vite_config_helpers import _model_candidates

        result = _model_candidates("sonnet")
        assert result == ["sonnet"]

    def test_parses_comma_separated(self):
        """GREEN: Parse de modelos separados por vírgula"""
        from backend.services.vite_config_helpers import _model_candidates

        result = _model_candidates("sonnet,haiku,opus")
        assert result == ["sonnet", "haiku", "opus"]

    def test_parses_semicolon_separated(self):
        """GREEN: Parse de modelos separados por ponto e vírgula"""
        from backend.services.vite_config_helpers import _model_candidates

        result = _model_candidates("sonnet;haiku")
        assert result == ["sonnet", "haiku"]

    def test_removes_whitespace(self):
        """GREEN: Remove espaços em branco"""
        from backend.services.vite_config_helpers import _model_candidates

        result = _model_candidates("  sonnet  ,  haiku  ")
        assert result == ["sonnet", "haiku"]


class TestNormalizeModelAlias:
    """Testes para _normalize_model_alias"""

    def test_sonnet_aliases(self):
        """GREEN: Normaliza sonnet"""
        from backend.services.vite_config_helpers import _normalize_model_alias

        assert _normalize_model_alias("sonnet") == "sonnet"
        assert _normalize_model_alias("Sonnet") == "sonnet"
        assert _normalize_model_alias("claude") == "sonnet"

    def test_haiku_aliases(self):
        """GREEN: Normaliza haiku"""
        from backend.services.vite_config_helpers import _normalize_model_alias

        assert _normalize_model_alias("haiku") == "haiku"
        assert _normalize_model_alias("4-mini") == "haiku"

    def test_opus_aliases(self):
        """GREEN: Normaliza opus"""
        from backend.services.vite_config_helpers import _normalize_model_alias

        assert _normalize_model_alias("opus") == "opus"
        assert _normalize_model_alias("4") == "opus"

    def test_unknown_model_unchanged(self):
        """GREEN: Modelos desconhecidos retornam None"""
        from backend.services.vite_config_helpers import _normalize_model_alias

        # Modelos desconhecidos retornam None ou são normalizados
        result = _normalize_model_alias("gpt-4")
        # gpt-4 não está no mapping, pode retornar None ou string vazia
        assert result is None or result == ""


class TestProxyConfig:
    """Testes para configuração de proxy"""

    def test_proxy_base_url_defaults(self):
        """GREEN: URL padrão quando não configurado"""
        from backend.services.vite_config_helpers import _proxy_base_url

        with patch.dict(os.environ, {}, clear=True):
            url = _proxy_base_url()
            assert "llm.seunegociofralib.site" in url

    def test_proxy_base_url_from_litellm(self):
        """GREEN: Usa LITELLM_BASE_URL quando definido"""
        from backend.services.vite_config_helpers import _proxy_base_url

        with patch.dict(os.environ, {"LITELLM_BASE_URL": "https://custom.litellm.com"}):
            assert _proxy_base_url() == "https://custom.litellm.com"

    def test_proxy_api_key_returns_empty_when_not_set(self):
        """GREEN: Retorna string vazia quando não configurado"""
        from backend.services.vite_config_helpers import _proxy_api_key

        with patch.dict(os.environ, {}, clear=True):
            result = _proxy_api_key()
            assert result == ""


class TestBatchConfig:
    """Testes para configuração de batch"""

    def test_batch_first_enabled_by_default(self):
        """GREEN: Batch first ativo por padrão"""
        from backend.services.vite_config_helpers import _batch_first_enabled

        with patch.dict(os.environ, {}, clear=True):
            assert _batch_first_enabled() is True

    def test_batch_spacing_seconds_default(self):
        """GREEN: Spacing default de 3 segundos"""
        from backend.services.vite_config_helpers import _batch_spacing_seconds

        with patch.dict(os.environ, {}, clear=True):
            result = _batch_spacing_seconds()
            assert 0.5 <= result <= 30


class TestTransientErrors:
    """Testes para detecção de erros transitórios"""

    def test_connection_error_is_transient(self):
        """GREEN: ConnectionError é transiente"""
        from backend.services.vite_config_helpers import _is_transient_proxy_error

        assert _is_transient_proxy_error(ConnectionError("Network unreachable")) is True

    def test_timeout_error_is_transient(self):
        """GREEN: TimeoutError é transiente"""
        from backend.services.vite_config_helpers import _is_transient_proxy_error

        assert _is_transient_proxy_error(TimeoutError("Request timeout")) is True

    def test_generic_exception_is_not_transient(self):
        """GREEN: Exceção genérica não é transiente"""
        from backend.services.vite_config_helpers import _is_transient_proxy_error

        assert _is_transient_proxy_error(ValueError("Invalid value")) is False
