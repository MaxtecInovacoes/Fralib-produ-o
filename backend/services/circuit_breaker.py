"""
Circuit Breaker Pattern para chamadas LLM externas.

Evita cascata de falhas quando um provider está fora do ar.
Quando o circuit abre, falha rapidamente sem fazer chamadas.
"""
import time
import threading
from enum import Enum
from typing import Callable, Any
from functools import wraps


class CircuitState(Enum):
    CLOSED = "closed"      # Normal - requests pass through
    OPEN = "open"          # Falhando - requests blocked
    HALF_OPEN = "half_open"  # Testando - allow one request


class CircuitBreaker:
    """
    Circuit Breaker implementation thread-safe.

    Params:
        name: Identificador do circuit
        failure_threshold: Número de falhas para abrir o circuit
        recovery_timeout: Segundos antes de tentar novamente (half-open)
        expected_exceptions: Exceções que contam como falha
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Verificar se deve tentar half-open
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executa função com circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                print(f"[CircuitBreaker] '{self.name}' OPENED after {self._failure_count} failures")


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is blocked."""
    pass


# Circuit breakers globais por provider
_circuits: dict[str, CircuitBreaker] = {}
_circuits_lock = threading.Lock()


def get_circuit(provider: str) -> CircuitBreaker:
    """Retorna ou cria circuit breaker para um provider."""
    with _circuits_lock:
        if provider not in _circuits:
            _circuits[provider] = CircuitBreaker(
                name=f"llm_{provider}",
                failure_threshold=5,
                recovery_timeout=60,
            )
        return _circuits[provider]


def circuit_protected(provider: str):
    """Decorator para proteger funções com circuit breaker."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit = get_circuit(provider)
            return circuit.call(func, *args, **kwargs)
        return wrapper
    return decorator
