"""Transparência pro Lead (Sprint 1.5).

Quando o ``whatsapp_listener`` decide silenciar o Franz (cooldown / paused /
handoff), o lead fica sem retorno visível. Isso gera dúvida ("o bot travou?").
O presente módulo enfileira uma msg curta de status na ``outbound_queue``
ANTES do silêncio, desde que o tenant tenha ``transparency_enabled=True``
(na chave ``sdr_settings.transparency_enabled``; default: ``True``).

Estados suportados:
    cooldown  →  "Já te respondo em 5 min, tá? 🙂"
    paused    →  "Vou chamar o humano, ok?"
    handoff   →  "Vou te conectar com o {nome}, ok?"

Regras:
    - Msgs curtas (<200 chars), tom humano.
    - Não envia se ``transparency_enabled=False`` para o tenant.
    - Não envia se já houver msg idêntica na fila (idempotência da
      ``enqueue_outbound``).
    - Sempre ``source="transparency"`` e ``priority=2`` (alta).
    - Falha transparente: nunca quebra o listener.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("transparency")

# Bind lazy para permitir monkeypatch em testes
# (e.g. ``patch("backend.whatsapp.transparency.enqueue_outbound", ...)``).
enqueue_outbound: Any = None  # type: ignore[assignment]


def _get_enqueue_outbound() -> Any:
    """Resolve ``enqueue_outbound`` (lazy + respeita monkeypatch)."""
    global enqueue_outbound
    if enqueue_outbound is None:
        from backend.services.outbound_queue import enqueue_outbound as _eob
        enqueue_outbound = _eob
    return enqueue_outbound

# ════════════════════════════════════════════════════════════════════════════
# Templates de status (curtos, < 200 chars, tom humano)
# ════════════════════════════════════════════════════════════════════════════

# Cada estado -> (template_func, max_chars)
# Templates devem ser human-friendly e usar o maximo de 200 chars.
_STATUS_TEMPLATES: dict[str, str] = {
    # Estado 'cooldown' — Franz esta pausado por ja ter respondido ha pouco
    "cooldown": "Ja te respondo em 5 min, ta? 🙂",

    # Estado 'paused' — humano assumiu (handoff automatico)
    "paused": "Vou chamar o humano, ok?",

    # Estado 'handoff' — transferencia para alguem do time
    "handoff": "Vou te conectar com o time, ok? 🙂",
}

# Fallback generico (caso estado nao mapeado — usado em testes)
_DEFAULT_TEMPLATE = "Recebi sua msg, ja te respondo. 🙂"

# Limite duro (defesa contra templates malformados)
_MAX_STATUS_LEN = 200


# ════════════════════════════════════════════════════════════════════════════
# Settings lookup (opt-in settings; respeita default True)
# ════════════════════════════════════════════════════════════════════════════

def get_transparency_settings(tenant_id: int | str | None) -> dict[str, Any]:
    """Retorna settings de transparencia para o tenant.

    Fallback chain:
        1) ``backend.services.sdr_settings.fetch_sdr_settings`` (canônico).
        2) ``{"transparency_enabled": True}`` (default).

    Nunca levanta exceção — falha como "enabled" para preservar UX.
    """
    try:
        from backend.services.sdr_settings import fetch_sdr_settings
        # fetch_sdr_settings exige db, nao engine. Tentar carregar do env.
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            return {"transparency_enabled": True}
        from sqlalchemy import create_engine
        engine = create_engine(database_url, pool_pre_ping=False)
        with engine.connect() as conn:
            settings = fetch_sdr_settings(conn, int(tenant_id))  # type: ignore[arg-type]
        # Default True se nao vier explicitamente False.
        return {
            "transparency_enabled": bool(
                settings.get("transparency_enabled", True)
            ),
        }
    except Exception as exc:
        # Falha aberta (enabled) para preservar UX.
        logger.debug(
            "[transparency] get_transparency_settings fallback (default=True): %s",
            exc,
        )
        return {"transparency_enabled": True}


# ════════════════════════════════════════════════════════════════════════════
# API principal
# ════════════════════════════════════════════════════════════════════════════

def build_status_message(state: str, **fmt: Any) -> str:
    """Constroi a msg curta de status para o estado.

    Args:
        state: 'cooldown' | 'paused' | 'handoff'
        **fmt: placeholders para substituicao (ex: ``nome='Joao'``).

    Returns:
        String <= 200 chars, sem chaves JSON, pronta para envio.
    """
    template = _STATUS_TEMPLATES.get(state, _DEFAULT_TEMPLATE)
    try:
        msg = template.format(**fmt) if fmt else template
    except Exception:
        msg = template
    # Defesa dura contra templates malformados:
    if len(msg) > _MAX_STATUS_LEN:
        msg = msg[: _MAX_STATUS_LEN - 1] + "…"
    return msg


def _enqueue_safely(
    engine: Any,
    tenant_id: int,
    lead_id: int | str,
    phone: str,
    message: str,
) -> Optional[int]:
    """Enfileira msg na outbound_queue. Falha transparentemente.

    Resolucao via ``_get_enqueue_outbound`` (lazy + patch-friendly).
    """
    try:
        fn = _get_enqueue_outbound()
        return fn(
            engine=engine,
            tenant_id=tenant_id,
            lead_id=str(lead_id),
            phone=phone,
            message=message,
            source="transparency",
            priority=2,
            delay_sec=0,
        )
    except Exception as exc:
        logger.warning("[transparency] enqueue falhou (no-bloqueante): %s", exc)
        return None


def send_status_message_if_paused(
    tenant_id: int | str | None,
    lead_id: int | str,
    state: str,
    *,
    engine: Any = None,
    phone: str = "",
    **fmt: Any,
) -> Optional[int]:
    """Enfileira msg curta de status quando o Franz vai silenciar.

    Args:
        tenant_id: tenant do lead.
        lead_id: id do lead.
        state: 'cooldown' | 'paused' | 'handoff'.
        engine: SQLAlchemy engine (opcional; sem ele, no-op).
        phone: telefone do lead (necessario para envio real).
        **fmt: placeholders (ex: ``nome='Maria'`` para handoff personalizado).

    Returns:
        ID da msg enfileirada, ou None se desativado/erro.
    """
    # 1) Tenant config — se desativado, no-op silencioso.
    try:
        settings = get_transparency_settings(tenant_id)
    except Exception:
        settings = {"transparency_enabled": True}
    if not settings.get("transparency_enabled", True):
        return None

    # 2) Estado nao mapeado → no-op silencioso.
    if state not in _STATUS_TEMPLATES:
        return None

    # 3) Msg curta e sanitizada.
    message = build_status_message(state, **fmt)

    # 4) Enfileirar. Engine/phone opcionais — em prod sao sempre preenchidos.
    return _enqueue_safely(
        engine=engine,
        tenant_id=int(tenant_id or 0),
        lead_id=lead_id,
        phone=phone,
        message=message,
    )


__all__ = [
    "send_status_message_if_paused",
    "build_status_message",
    "get_transparency_settings",
    "enqueue_outbound",
]
