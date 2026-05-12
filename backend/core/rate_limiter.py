from slowapi import Limiter
from slowapi.util import get_remote_address

# Instancia unica compartilhada por server.py e todos os endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
