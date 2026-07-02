"""FraLib package config compatibility exports.

This package exists for registry modules, but older code imports constants from
``backend.config``. Keep those constants here so package resolution does not
shadow ``backend/config.py`` with an empty module.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRALIB_ROOT = BACKEND_DIR.parent.resolve()

CHECKPOINT_DIR = os.getenv("FRALIB_CHECKPOINT_DIR", str(FRALIB_ROOT / "checkpoints"))
SITES_DIR = os.getenv("FRALIB_SITES_DIR", "/var/www/fralib/sites")

SITE_DOMAIN = os.getenv("FRALIB_SITE_DOMAIN", "https://seunegociofralib.site")
FRALIB_DOMAIN = os.getenv("FRALIB_DOMAIN", "https://fralib.com.br")

DS_DIR = os.getenv("FRALIB_DS_DIR", "/root/open-design/design-systems")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5433/fralib_db",
)

WA_PHONE_PREFIX = os.getenv("WA_PHONE_PREFIX", "55")

__all__ = [
    "BACKEND_DIR",
    "FRALIB_ROOT",
    "CHECKPOINT_DIR",
    "SITES_DIR",
    "SITE_DOMAIN",
    "FRALIB_DOMAIN",
    "DS_DIR",
    "DATABASE_URL",
    "WA_PHONE_PREFIX",
]
