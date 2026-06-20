# SEC_005_A07_AUTH.md — Information Disclosure: Google OAuth Configuration Status Leaked

## Metadata

| Campo | Valor |
|---|---|
| Severity | MEDIUM |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/endpoints/auth_endpoints.py` |
| Lines | 604–613 |
| CVSS 3.1 | 5.3 (Medium) — AV:N/AC:L/PR:N/UI:N/C:L/I:N/A:N |

## Vulnerabilidade

O endpoint `/api/auth/oauth/google/config` revela publicamente se a funcionalidade Google OAuth esta configurada e habilitada:

```python
# Linhas 604–613
@router.get("/oauth/google/config")
async def google_oauth_config_status():
    """Retorna status da configuração Google OAuth."""
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    return {
        "enabled": bool(client_id),
        "configured": bool(client_id and os.getenv("GOOGLE_CLIENT_SECRET")),
        "message": "Google OAuth configurado" if client_id
                   else "Configure GOOGLE_CLIENT_ID no .env",
    }
```

Este endpoint NAO requer autenticacao (nao tem `Depends(get_current_user)`), sendo completamente publicamente acessivel.

**Informacao vazada:**
- `enabled: true` -> Google OAuth esta configurado
- `configured: true` -> Both `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` estao no ambiente
- `message`: Indica o que falta configurar

## Impacto

- **Reconhecimento de infraestrutura**: Atacante identifica que Google OAuth esta disponivel, revelando estrategia de autenticacao
- **Reduz barreira de ataque**: Sabendo que Google OAuth existe, atacante pode focar em ataques de OAuth CSRF, phishing de login Google, ou exploits especificos de OAuth
- **Enumeração de configuracao de seguranca**: Informa ao atacante quais mecanismos de autenticao a aplicacao suporta
- **Conformidade**: Informacao sobre metodos de autenticacao e considerada dado de seguranca interno

## Exploit

```bash
curl https://app.seunegociofralib.site/api/auth/oauth/google/config

# Resposta (Google OAuth NAO configurado):
{"enabled": false, "configured": false, "message": "Configure GOOGLE_CLIENT_ID no .env"}

# Resposta (Google OAuth configurado):
{"enabled": true, "configured": true, "message": "Google OAuth configurado"}

# Atacante agora sabe: OAuth existe, pode tentar atacar
```

## Remediation

**Opcao 1 — Remover o endpoint completamente** (se nao for usado pelo frontend):
```python
# Deletar o endpoint /oauth/google/config
```

**Opcao 2 — Proteger com autenticacao** (se o frontend precisar do status):
```python
@router.get("/oauth/google/config")
async def google_oauth_config_status(usuario: dict = Depends(get_current_user)):
    ...
```

**Opcao 3 — Retornar sempre resposta generica** (se o frontend precisa saber se habilitou ou nao):
```python
@router.get("/oauth/google/config")
async def google_oauth_config_status():
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    # Nunca revelar se GOOGLE_CLIENT_SECRET existe
    return {
        "enabled": bool(client_id),
        "message": "Google OAuth configurado" if client_id
                   else "Metodo de login nao disponivel",
    }
```

## Referencia

- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- OWASP A01:2021 — Broken Access Control (related)
- OWASP A07:2021 – Authentication Failures
- OWASP API Security Cheat Sheet
