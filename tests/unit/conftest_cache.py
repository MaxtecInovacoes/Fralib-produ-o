"""conftest.py for cache tests - isolated from main conftest."""

from __future__ import annotations

import os
import sys

# Minimal setup for cache tests
os.environ["TESTING"] = "true"

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Avoid full server import
