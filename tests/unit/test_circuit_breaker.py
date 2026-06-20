"""
Testes para circuit_breaker

RED → GREEN → REFACTOR
"""
import pytest
import time
from unittest.mock import MagicMock, patch


class TestCircuitBreakerInit:
    """Testes para inicialização do Circuit Breaker"""

    def test_initial_state_is_closed(self):
        """GREEN: Circuit breaker inicia no estado fechado"""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_initial_failure_count_is_zero(self):
        """GREEN: Contador de falhas inicia em 0"""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb._failure_count == 0


class TestCircuitBreakerOpen:
    """Testes para transição para estado aberto"""

    def test_opens_after_threshold_failures(self):
        """GREEN: Abre após N falhas consecutivas"""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            cb._on_failure()

        assert cb.state == CircuitState.OPEN

    def test_opens_on_exception(self):
        """GREEN: Abre quando exceção esperada ocorre"""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=1)

        def failing_func():
            raise ValueError("Test error")

        # A exceção é propagada E o circuit abre
        with pytest.raises(ValueError):
            cb.call(failing_func)

        # Verificar que abriu após a falha
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerCall:
    """Testes para método call"""

    def test_call_executes_successful_function(self):
        """GREEN: call executa função bem-sucedida"""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test")

        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"

    def test_call_blocks_when_open(self):
        """GREEN: call bloqueia quando circuit está aberto"""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60)
        cb._state = CircuitState.OPEN
        cb._last_failure_time = time.time()

        with pytest.raises(CircuitOpenError):
            cb.call(lambda: "result")

    def test_call_propagates_non_expected_exceptions(self):
        """GREEN: Exceções não esperadas são propagadas"""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", expected_exceptions=(ValueError,))

        def other_error():
            raise TypeError("Unexpected error")

        with pytest.raises(TypeError):
            cb.call(other_error)


class TestCircuitBreakerHalfOpen:
    """Testes para estado half-open"""

    def test_half_open_after_recovery_timeout(self):
        """GREEN: Transita para half-open após timeout"""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=1)
        cb._state = CircuitState.OPEN
        cb._last_failure_time = time.time() - 2  # 2 segundos atrás

        # Após timeout, estado deve ser HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
