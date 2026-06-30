from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')
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