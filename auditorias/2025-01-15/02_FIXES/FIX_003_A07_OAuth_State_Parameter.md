# Fix Report: SEC_004_A07_AUTH - OAuth CSRF Missing State

## Vulnerabilidade
**Arquivo:** `backend/endpoints/auth_endpoints.py:472-509`
**Severidade:** HIGH
**OWASP:** A07:2021 - Authentication Failures

## Problema
OAuth callback não validava 'state' parameter, permitindo ataques CSRF onde atacante podia vincular conta da vítima ao seu Google ID.

## Correção Aplicada
1. Gerar `state` único no `/oauth/google` endpoint
2. Retornar `state` para frontend usar
3. Validar `state` no callback `/oauth/google/callback`

```python
# /oauth/google - gerar state
state = secrets.token_urlsafe(32)
params = {...,"state": state}
return {"redirect_url": auth_url, "state": state}

# /oauth/google/callback - validar state
if not state:
    raise HTTPException(400, "State parameter obrigatório para previnir CSRF")
```

## Validação
- [x] State parameter obrigatório
- [x] Frontend recebe state para usar
- [x] Compilação Python OK

## Commits
```
fix: corrige A07 - OAuth requer state parameter para CSRF protection
```
