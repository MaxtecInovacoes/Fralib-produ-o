sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
from _env import load_env  # noqa: E402  — B4 DRY
load_env()
from backend.core.database import engine
from sqlalchemy import text
import jwt
import os
secret = os.getenv('JWT_SECRET_KEY', '')
with engine.connect() as conn:
    admin = conn.execute(text("SELECT id, email FROM users WHERE role='admin' LIMIT 1")).fetchone()
    if admin:
        token = jwt.encode({'sub': str(admin[0]), 'email': admin[1], 'is_superadmin': True, 'role': 'superadmin'}, secret, algorithm='HS256')
        print(token)