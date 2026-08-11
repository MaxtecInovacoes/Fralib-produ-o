"""Initialize local dev database schema.

Usage:
    python scripts/init_local_db.py

Loads .env.local and creates all tables via inicializar_database().
"""
import sys
import os

# Ensure backend package is importable from scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Load .env.local (preferred) or .env
from dotenv import load_dotenv

env_file = os.path.join(os.path.dirname(__file__), "..", ".env.local")
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()

from sqlalchemy import create_engine
from backend.core.schema_init import inicializar_database


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Create .env.local first.")
        sys.exit(1)

    print(f"[init_local_db] DATABASE_URL={db_url}")
    engine = create_engine(db_url, pool_pre_ping=True)

    try:
        inicializar_database(engine)
        print("[init_local_db] Done. Schema ready.")
    except Exception as exc:
        print(f"[init_local_db] ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
