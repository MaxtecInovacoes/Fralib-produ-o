"""Standard SQLAlchemy imports for backend endpoints and services.

Canônico para B3 do plano DRY (codex/dry-refactor).

Elimina a duplicação de:
    from sqlalchemy.orm import Session
    from sqlalchemy import text
em 50+ arquivos (endpoints, services, lead_supply_providers).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = ["Session", "text"]
