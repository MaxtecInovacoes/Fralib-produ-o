# SEC_004_A07_AUTH.md — CSRF Vulnerability: Google OAuth Callback Missing State Parameter

## Metadata

| Campo | Valor |
|---|---|
| Severity | HIGH |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/endpoints/auth_endpoints.py` |
| Lines | 502–601 |
| CVSS 3.1 | 8.0 (High) — AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:H |

## Vulnerabilidade

O callback do Google OAuth (`/api/auth/oauth/google/callback`) nao implementa o parametro `state`, que e obrigatorio segundo o RFC 6749 (OAuth 2.0) para previnir ataques CSRF.

```python
# Linhas 489–497: geracao da URL de autorizacao — SEM state
params = {
    "client_id": client_id,
    "redirect_uri": os.getenv("FRALIB_PUBLIC_URL", "https://seunegociofralib.site")
        + "/api/auth/oauth/google/callback",
    "response_type": "code",
    "scope": "openid email profile",
    "access_type": "offline",
    "prompt": "select_account",
}
auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
return {"redirect_url": auth_url}

# Linhas 502–601: callback — NAO valida state
@router.get("/oauth/google/callback")
async def google_oauth_callback(request: Request, code: str, db: Session = Depends(get_db)):
    # Nao recebe parametro state!
    # Nao valida state!
    ...
    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": jwt_token, ...}
```

**Ataque CSRF:** Um atacante pode forcar o login da vitima em uma conta OAuth controlada pelo atacante:

1. Atacante registra app no Google OAuth com seu proprio `client_id`
2. Cria link malicioso pointing para `/api/auth/oauth/google/callback` com code gerado por ele
3. Vitima clica no link (ou e redirecionada via iframe/body)
4. Se vitima ja esta logada no Google, o Google emite code valido
5. Backend troca code por info do atacante (email, name, google_id)
6. Backend cria/consegue conta e emite JWT para a vitima
7. Vitima agora esta logada com email/conta do atacante
8. Atacante pode coletar dados da vitima ou realizar acciones em nome dela

## Impacto

- **Account Linking CSRF**: Vitima vinculada acidentalmente a conta OAuth de atacante
- **Persistence**: Problema persiste mesmo apos logout, pois a conta ja esta linkada
- **Data Exfiltration**: Se a vitima inserir dados sensiveis apos login, vao para conta do atacante
- **Violation of OAuth 2.0**: Nao conformidade com RFC 6749

## Exploit

```html
<!-- Pagina maliciosa -->
<body>
<img src="https://app.seunegociofralib.site/api/auth/oauth/google/callback?code=ATRARED_CODE" width="0" height="0">
<!-- Ou via redirect automatico -->
<script>
  // Atacante configurou Google OAuth com redirect_uri pointing para callback
  window.location = "https://accounts.google.com/o/oauth2/v2/auth?client_id=ATACANTE_ID&...";
</script>
</body>
```

## Remediation

```python
# 1. Gerar state no endpoint de redirect
from urllib.parse import urlencode
import secrets, hashlib

@router.get("/oauth/google")
async def google_oauth_redirect(request: Request):
    ...
    # Gerar state com high entropy
    state_token = secrets.token_urlsafe(32)
    # Armazenar state no Redis ou cookie assinado com audience binding
    # Exemplo minimo com cookie httponly:
    state_hash = hashlib.sha256(state_token.encode()).hexdigest()
    response = JSONResponse({"redirect_url": auth_url})
    response.set_cookie("oauth_state", state_hash, httponly=True,
                        samesite="lax", secure=True, max_age=600)
    return response

# 2. Validar state no callback
@router.get("/oauth/google/callback")
async def google_oauth_callback(request: Request, code: str, state: str = "",
                                 db: Session = Depends(get_db)):
    # Validar state
    if not state:
        raise HTTPException(400, "State obrigatorio")
    expected_hash = request.cookies.get("oauth_state")
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    if not secrets.compare_digest(expected_hash, state_hash):
        raise HTTPException(400, "State invalido")
    # Limpar cookie state
    ...
```

## Referencia

- CWE-352: Cross-Site Request Forgery
- RFC 6749 Section 10.12 — CSRF Attack
- OWASP A07:2021 – Authentication Failures
- OWASP OAuth 2.0 Security Cheat Sheet
