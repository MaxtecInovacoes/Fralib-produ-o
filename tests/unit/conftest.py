"""Standalone conftest for whatsapp phone-health tests.

Adiciona backend/ ao sys.path e isola este test module do conftest raiz
(tests/conftest.py importa `server` que falha em CHECKPOINT_DIR).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Set testing mode
os.environ.setdefault("TESTING", "true")

# JWT secret + DATABASE_URL requeridos por backend.core.auth/database
# antes de qualquer import que puxe a cadeia (endpoints → auth → database).
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-32-bytes-min")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/test",
)

# Minimal path setup
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))