"""
Agent Bus - pub/sub entre agentes para compartilhamento de sinais.

Agentes publicam eventos:
- SDR: "lead respondeu", "objecao identificada", "BANT completo", "hota", "lost"
- Hunter: "lead encontrado", "score ICP"
- Builder: "site pronto", "variante escolhida"

Outros agentes assinam eventos relevantes:
- Design system aprende: lead com dor X -> proximo site prioriza secao Y
- SDR aprende: site do concorrente Y -> usar como prova social
- Hunter aprende: segmento Z converte mais -> priorizar

Implementacao: in-memory pub/sub. Em prod, troca por Redis pub/sub.
"""

import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal

log = logging.getLogger("agent-bus")


AgentName = Literal["sdr", "hunter", "builder", "design", "nicho", "closer"]
EventType = Literal[
    "lead_responded",
    "objection_detected",
    "bant_complete",
    "site_ready",
    "variant_chosen",
    "pain_identified",
    "deal_won",
    "deal_lost",
    "opt_out",
    "retarget_queued",
]


@dataclass(frozen=True)
class BusEvent:
    event_type: EventType
    agent: AgentName
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tenant_id: int = 0
    segment: str = ""


class AgentBus:
    """In-memory pub/sub thread-safe."""

    def __init__(self, max_history: int = 1000):
        self._subscribers: dict[EventType, list[Callable[[BusEvent], None]]] = defaultdict(list)
        self._history: deque[BusEvent] = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._stats: dict[str, int] = defaultdict(int)

    def subscribe(self, event_type: EventType, callback: Callable[[BusEvent], None]) -> None:
        """Registra callback pra um tipo de evento."""
        with self._lock:
            self._subscribers[event_type].append(callback)
        log.info(f"[BUS] Subscriber added for {event_type}")

    def publish(self, event: BusEvent) -> int:
        """Publica evento. Retorna numero de subscribers notificados."""
        with self._lock:
            self._history.append(event)
            self._stats[event.event_type] += 1
            callbacks = list(self._subscribers.get(event.event_type, []))
        notified = 0
        for cb in callbacks:
            try:
                cb(event)
                notified += 1
            except Exception as e:
                log.error(f"[BUS] Subscriber failed for {event.event_type}: {e}")
        log.info(
            f"[BUS] Published {event.event_type} from {event.agent} "
            f"-> {notified}/{len(callbacks)} notified"
        )
        return notified

    def get_recent(self, event_type: EventType | None = None, limit: int = 50) -> list[BusEvent]:
        """Retorna eventos recentes."""
        with self._lock:
            events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_stats(self) -> dict[str, int]:
        """Retorna contagem de eventos por tipo."""
        with self._lock:
            return dict(self._stats)


# Singleton global
_bus: AgentBus | None = None


def get_bus() -> AgentBus:
    """Retorna instancia singleton do AgentBus."""
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus


# ════════════════════════════════════════════════════════════════════
# CONVENIENCE PUBLISH HELPERS
# ════════════════════════════════════════════════════════════════════

def publish_objection_detected(
    *,
    tenant_id: int,
    segment: str,
    objection: str,
    lead_id: int,
    response_template: str = "",
) -> int:
    """Helper: publica deteccao de objecao."""
    return get_bus().publish(BusEvent(
        event_type="objection_detected",
        agent="sdr",
        tenant_id=tenant_id,
        segment=segment,
        payload={
            "lead_id": lead_id,
            "objection": objection,
            "response_template": response_template,
        },
    ))


def publish_pain_identified(
    *,
    tenant_id: int,
    segment: str,
    pain: str,
    lead_id: int,
) -> int:
    """Helper: publica identificacao de dor."""
    return get_bus().publish(BusEvent(
        event_type="pain_identified",
        agent="sdr",
        tenant_id=tenant_id,
        segment=segment,
        payload={"lead_id": lead_id, "pain": pain},
    ))


def publish_site_ready(
    *,
    tenant_id: int,
    segment: str,
    variant: str,
    lead_id: int,
    url: str = "",
) -> int:
    """Helper: publica site pronto."""
    return get_bus().publish(BusEvent(
        event_type="site_ready",
        agent="builder",
        tenant_id=tenant_id,
        segment=segment,
        payload={"lead_id": lead_id, "variant": variant, "url": url},
    ))


def publish_deal_won(
    *,
    tenant_id: int,
    segment: str,
    lead_id: int,
    bant_score: int = 0,
) -> int:
    """Helper: publica won."""
    return get_bus().publish(BusEvent(
        event_type="deal_won",
        agent="sdr",
        tenant_id=tenant_id,
        segment=segment,
        payload={"lead_id": lead_id, "bant_score": bant_score},
    ))
