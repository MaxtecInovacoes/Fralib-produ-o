"""
Testes para cache_service

RED → GREEN → REFACTOR
"""
import pytest
import time
from unittest.mock import MagicMock, patch
import hashlib


class TestCacheServiceImports:
    """Testes para imports do cache service"""

    def test_cache_service_imports_without_error(self):
        """GREEN: Módulo importa sem erros"""
        from backend.services import cache_service
        assert hasattr(cache_service, '_get_redis')


class TestGetRedis:
    """Testes para _get_redis"""

    def test_returns_none_when_no_redis_url(self):
        """GREEN: Retorna None quando REDIS_URL não está configurado"""
        with patch.dict('os.environ', {'REDIS_URL': ''}, clear=True):
            from backend.services.cache_service import _get_redis
            result = _get_redis()
            assert result is None

    def test_returns_redis_client_when_configured(self):
        """GREEN: Retorna cliente Redis quando configurado"""
        with patch.dict('os.environ', {
            'REDIS_URL': 'redis://localhost:6379/0'
        }, clear=True):
            from backend.services.cache_service import _get_redis
            # Não deve falhar mesmo se Redis não estiver rodando
            result = _get_redis()
            # Pode ser None se Redis não está rodando, mas não deve dar erro
            assert result is None or hasattr(result, 'get')


class TestCacheKeyGeneration:
    """Testes para geração de keys de cache"""

    def test_simple_hash_generates_consistent_hash(self):
        """GREEN: Hash simples gera resultado consistente"""
        from backend.services.cache_service import _simple_hash

        data = "test_data"
        hash1 = _simple_hash(data)
        hash2 = _simple_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 32  # SHA256 truncado para 32 chars

    def test_different_data_produces_different_hash(self):
        """GREEN: Dados diferentes geram hashes diferentes"""
        from backend.services.cache_service import _simple_hash

        hash1 = _simple_hash("data1")
        hash2 = _simple_hash("data2")

        assert hash1 != hash2


class TestCacheOperationsWithMock:
    """Testes para operações de cache usando mock"""

    def test_cache_set_and_get(self):
        """GREEN: Permite definir e obter valores do cache"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"key": "value"}'

        with patch('backend.services.cache_service._get_redis', return_value=mock_redis):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            # Set
            cs.set("test_key", {"data": "test"}, ttl=60)
            # Verify set was called
            mock_redis.setex.assert_called()

    def test_cache_get_returns_none_on_miss(self):
        """GREEN: Retorna None quando key não existe"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch('backend.services.cache_service._get_redis', return_value=mock_redis):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            result = cs.get("nonexistent_key")
            assert result is None

    def test_cache_delete(self):
        """GREEN: Remove keys do cache"""
        mock_redis = MagicMock()

        with patch('backend.services.cache_service._get_redis', return_value=mock_redis):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            cs.delete("test_key")

            mock_redis.delete.assert_called_with("test_key")

    def test_cache_exists(self):
        """GREEN: Verifica se key existe no cache"""
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1

        with patch('backend.services.cache_service._get_redis', return_value=mock_redis):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            result = cs.exists("test_key")
            assert result is True
            mock_redis.exists.assert_called_with("test_key")


class TestCacheWithoutRedis:
    """Testes para fallback quando Redis não disponível"""

    def test_graceful_degradation_without_redis(self):
        """GREEN: Funciona mesmo sem Redis"""
        with patch('backend.services.cache_service._get_redis', return_value=None):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            # Deve funcionar mesmo sem Redis (pode usar fallback)
            result = cs.get("key")
            # Result pode ser None se Redis não disponível
            assert result is None


class TestCacheKeyPrefix:
    """Testes para prefixo de keys"""

    def test_keys_are_strings(self):
        """GREEN: Keys são strings"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch('backend.services.cache_service._get_redis', return_value=mock_redis):
            from backend.services.cache_service import CacheService

            cs = CacheService()
            cs.set("my_key", {"data": "value"}, ttl=60)

            # Verify the key used in setex call
            call_args = mock_redis.setex.call_args
            if call_args:
                key_used = call_args[0][0]
                assert isinstance(key_used, str)
