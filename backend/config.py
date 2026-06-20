"""
FraLib Central Config — fonte única de paths, URLs e constantes.
Importar como: from config import SITE_DOMAIN, CHECKPOINT_DIR, ...
"""

import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.resolve()
FRALIB_ROOT = BACKEND_DIR.parent.resolve()

CHECKPOINT_DIR = os.getenv("FRALIB_CHECKPOINT_DIR", str(FRALIB_ROOT / "checkpoints"))
SITES_DIR = os.getenv("FRALIB_SITES_DIR", "/var/www/fralib/sites")

# ─── URLs ────────────────────────────────────────────────────────
SITE_DOMAIN = os.getenv("FRALIB_SITE_DOMAIN", "https://seunegociofralib.site")
FRALIB_DOMAIN = os.getenv("FRALIB_DOMAIN", "https://fralib.com.br")

# ─── Design system references ────────────────────────────────────
DS_DIR = os.getenv("FRALIB_DS_DIR", "/root/open-design/design-systems")

# ─── Database ────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5433/fralib_db",
)

# ─── WhatsApp ────────────────────────────────────────────────────
WA_PHONE_PREFIX = os.getenv("WA_PHONE_PREFIX", "55")
