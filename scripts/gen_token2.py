import sys
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')
from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')
from database import engine
from sqlalchemy import text
import jwt
import os
secret = os.getenv('JWT_SECRET_KEY', '')
with engine.connect() as conn:
    admin = conn.execute(text("SELECT id, email FROM users WHERE role='superadmin' LIMIT 1")).fetchone()
    token = jwt.encode({'sub': str(admin[0]), 'email': admin[1], 'is_superadmin': True, 'role': 'superadmin'}, secret, algorithm='HS256')
    print('TOKEN:', token)