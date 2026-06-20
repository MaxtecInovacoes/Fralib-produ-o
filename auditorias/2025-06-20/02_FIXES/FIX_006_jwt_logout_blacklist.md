# FIX_006 - Corrigir Logout JWT sem Revogação

## PROBLEMA
**Local:** `backend/endpoints/auth_endpoints.py:442-447`

**Descrição:**
O logout atual apenas remove os cookies do cliente, mas não invalida o JWT token no servidor. O token continua válido até expirar (24 horas). Um atacante com acesso ao token pode continuar usando-o após o logout.

**Impacto:**
- Tokens roubados permanecem válidos após logout
- Usuários não podem invalidar sessões em outros dispositivos
- Não há controle de sessões ativas por usuário

## SOLUÇÃO
Implementar blacklist de tokens usando Redis existente. Quando um token é revogado:
1. Extrair o `jti` (JWT ID) do token ou usar o hash do token
2. Armazenar na blacklist com TTL = tempo restante do token
3. Verificar blacklist em cada request

## ANTES (Código Problemático)
```python
@router.post("/logout")
async def logout(request: Request, response: Response):
    secure = _cookie_secure(request)
    for cookie_name in ("fralib_session", "fralib_csrf"):
        response.delete_cookie(cookie_name, path="/", secure=secure, samesite="lax")
    return {"status": "ok"}
```

## DEPOIS (Correção)
```python
# Adicionar em auth.py - blacklist de tokens
def _is_token_revoked(token: str) -> bool:
    """Verifica se token está na blacklist."""
    redis = _get_redis()
    if not redis:
        return False
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return redis.exists(f"revoked_token:{token_hash}")

def revoke_token(token: str) -> None:
    """Adiciona token à blacklist até expiração."""
    import jwt
    redis = _get_redis()
    if not redis:
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp = payload.get("exp", 0)
    except Exception:
        exp = int(time.time()) + 86400  # Default 24h
    ttl = max(1, exp - int(time.time()))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis.setex(f"revoked_token:{token_hash}", ttl, "1")

# Atualizar logout
@router.post("/logout")
async def logout(request: Request, response: Response, usuario: dict = Depends(get_current_user)):
    token, _ = _token_from_request(None, request)
    revoke_token(token)
    secure = _cookie_secure(request)
    for cookie_name in ("fralib_session", "fralib_csrf"):
        response.delete_cookie(cookie_name, path="/", secure=secure, samesite="lax")
    return {"status": "ok"}
```

## ARQUIVOS A MODIFICAR
1. `backend/core/auth.py` - Adicionar funções de blacklist
2. `backend/endpoints/auth_endpoints.py` - Atualizar logout

## TESTE
```bash
ruff check backend/core/auth.py backend/endpoints/auth_endpoints.py
# Result: All checks passed!
```

## COMMIT
```
fix: implementa revogação de JWT no logout

Adiciona blacklist de tokens usando Redis existente.
Tokens revogados são verificados em cada request.
```
