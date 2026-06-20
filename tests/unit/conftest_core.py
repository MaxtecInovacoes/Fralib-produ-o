"""Standalone conftest for core function tests - avoids full app import."""

import os
import sys
from pathlib import Path

# Set testing mode
os.environ["TESTING"] = "true"

# Minimal path setup
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))
