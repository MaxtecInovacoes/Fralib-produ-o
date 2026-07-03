"""Sprint 1.7: circuit breaker por stage do SDR.

NUNCA cai pra template generico. Em vez disso:
- 3 falhas seguidas do MESMO stage em <5min -> circuito abre
- Circuito aberto: novas chamadas nao tentam LLM
- Caller (agent.py) marca needs_human_followup e nao envia mensagem

Estado em memoria (process-local). Se o worker cair e voltar, o circuito
reseta — isso e aceitavel, melhor que persistir em Redis so pra isso.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque


class CircuitOpenError(Exception):
    """Levantada quando circuit breaker esta aberto para o stage."""

    def __init__(self, stage: str, opened_at: float):
        self.stage = stage
        self.opened_at = opened_at
        super().__init__(f"circuit open for stage '{stage}'")


class StageCircuitBreaker:
    """Circuit breaker indexado por stage.

    Janela: WINDOW_SECONDS (padrao 300s = 5min).
    Threshold: FAILURE_THRESHOLD (padrao 3 falhas).
    Quando aberto: novas tentativas em call_llm_for_stage sao bloqueadas.
    """

    WINDOW_SECONDS = 300.0
    FAILURE_THRESHOLD = 3

    def __init__(
        self,
        window_seconds: float = WINDOW_SECONDS,
        failure_threshold: int = FAILURE_THRESHOLD,
        clock: callable = time.monotonic,
    ) -> None:
        self.window_seconds = window_seconds
        self.failure_threshold = failure_threshold
        self._clock = clock
        self._failures: dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        self._opened_at: dict[str, float] = {}

    def _prune(self, stage: str, now: float) -> Deque[float]:
        buf = self._failures.setdefault(stage, deque())
        cutoff = now - self.window_seconds
        while buf and buf[0] < cutoff:
            buf.popleft()
        return buf

    def allow(self, stage: str) -> bool:
        """Retorna True se o circuito esta fechado (pode tentar)."""
        with self._lock:
            return stage not in self._opened_at

    def record_failure(self, stage: str) -> None:
        """Registra falha. Pode abrir o circuito se atingir threshold."""
        with self._lock:
            now = self._clock()
            buf = self._prune(stage, now)
            buf.append(now)
            if (
                len(buf) >= self.failure_threshold
                and stage not in self._opened_at
            ):
                self._opened_at[stage] = now

    def record_success(self, stage: str) -> None:
        """Reseta contadores e fecha o circuito."""
        with self._lock:
            self._failures.pop(stage, None)
            self._opened_at.pop(stage, None)

    def guard(self, stage: str) -> None:
        """Levanta CircuitOpenError se circuito estiver aberto."""
        with self._lock:
            opened_at = self._opened_at.get(stage)
        if opened_at is not None:
            raise CircuitOpenError(stage, opened_at)

    def is_open(self, stage: str) -> bool:
        with self._lock:
            return stage in self._opened_at

    def opened_stages(self) -> dict[str, float]:
        """Snapshot dos circuitos abertos (stage -> timestamp)."""
        with self._lock:
            return dict(self._opened_at)


_breaker = StageCircuitBreaker()


def get_breaker() -> StageCircuitBreaker:
    """Retorna o breaker singleton do processo."""
    return _breaker


def reset_for_test() -> None:
    """Limpa estado. Apenas pra testes."""
    with _breaker._lock:
        _breaker._failures.clear()
        _breaker._opened_at.clear()
