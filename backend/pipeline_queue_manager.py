"""
Pipeline Queue Manager — controle de concorrência global
Limita pipelines simultâneos para não estourar rate limit da API.
Máximo: 3 pipelines ao mesmo tempo (configurável via MAX_CONCURRENT).
"""
import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field

MAX_CONCURRENT = 3          # pipelines rodando ao mesmo tempo
AVG_PIPELINE_MINUTES = 7    # estimativa de duração para calcular espera

@dataclass
class QueueEntry:
    user_id: int
    position: int
    entered_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None

class PipelineQueueManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._running: Dict[int, float] = {}   # user_id -> started_at
        self._waiting: list[QueueEntry] = []   # fila de espera ordenada
        self._next_pos = 1

    async def try_enter(self, user_id: int) -> dict:
        """
        Tenta entrar na fila.
        Retorna:
          {can_run: True}  — pode rodar agora
          {can_run: False, position: N, wait_minutes: N, message: str}
        """
        async with self._lock:
            # Limpar entradas antigas de running (segurança: >30min = travado)
            now = time.time()
            self._running = {
                uid: t for uid, t in self._running.items()
                if now - t < 1800
            }

            # Se usuário já está rodando, não deixa rodar de novo
            if user_id in self._running:
                return {
                    "can_run": False,
                    "position": 0,
                    "wait_minutes": 0,
                    "message": "Voce ja tem um pipeline rodando. Aguarde ele terminar."
                }

            # Se usuário já está na fila de espera
            for entry in self._waiting:
                if entry.user_id == user_id:
                    wait = entry.position * AVG_PIPELINE_MINUTES
                    return {
                        "can_run": False,
                        "position": entry.position,
                        "wait_minutes": wait,
                        "message": f"Voce esta na posicao {entry.position} da fila. Estimativa: ~{wait} minutos."
                    }

            # Tem vaga?
            if len(self._running) < MAX_CONCURRENT:
                self._running[user_id] = now
                return {"can_run": True}

            # Sem vaga — entrar na fila
            pos = len(self._waiting) + 1
            entry = QueueEntry(user_id=user_id, position=pos)
            self._waiting.append(entry)
            wait = (len(self._running) + pos - 1) * AVG_PIPELINE_MINUTES
            return {
                "can_run": False,
                "position": pos,
                "wait_minutes": wait,
                "message": (
                    f"Sistema ocupado com {len(self._running)} pipeline(s) rodando. "
                    f"Voce e o {pos}° na fila. Estimativa de espera: ~{wait} minutos. "
                    f"Seu pipeline sera iniciado automaticamente quando houver vaga."
                )
            }

    async def release(self, user_id: int):
        """Libera slot quando pipeline termina e promove próximo da fila."""
        async with self._lock:
            self._running.pop(user_id, None)
            if self._waiting:
                next_entry = self._waiting.pop(0)
                # Reposicionar os restantes
                for i, e in enumerate(self._waiting):
                    e.position = i + 1
                self._running[next_entry.user_id] = time.time()
                return next_entry.user_id  # retorna quem foi promovido
        return None

    def status(self) -> dict:
        """Retorna status atual da fila (sem lock — apenas leitura)."""
        now = time.time()
        return {
            "running": len(self._running),
            "max_concurrent": MAX_CONCURRENT,
            "waiting": len(self._waiting),
            "slots_free": max(0, MAX_CONCURRENT - len(self._running)),
            "queue": [
                {
                    "position": e.position,
                    "wait_minutes": e.position * AVG_PIPELINE_MINUTES,
                    "waiting_since_seconds": int(now - e.entered_at),
                }
                for e in self._waiting
            ]
        }


# Singleton global — importar de qualquer lugar
pipeline_queue = PipelineQueueManager()
