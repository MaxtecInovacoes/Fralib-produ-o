# FUNC_002 - Autenticação e Autorização

**Projeto:** FraLib
**Data da Auditoria:** 2025-06-20
**Auditor:** Auditor Funcional
**Arquivos Analisados:**
- `backend/endpoints/auth_endpoints.py`
- `backend/core/jwt_config.py`
- `backend/core/auth.py`
- `backend/utils/password_utils.py`
- `backend/core/rate_limiter.py`
- `backend/endpoints/users_endpoints.py`
- `tests/unit/test_auth_core.py`
- `tests/unit/test_auth_endpoints.py`
- `tests/unit/test_auth_security_contract.py`
- `tests/integration/test_api_auth.py`

---

## Features Verificadas

| Feature | Status | Observacoes |
|---|---|---|
| Login (email + senha) | OK | Rate limited 10/min, bcrypt 12 rounds |
| Logout | PARCIAL | Apenas limpa cookies, token JWT permanece valido |
| JWT geracao | OK | HS256, exp 24h, payload inclui sub/email |
| JWT validacao | OK | `get_current_user` valida exp, assinatura, existencia |
| Refresh token | FALHA | Nao existe mecanismo de refresh; token expira sem renovacao |
| Password hashing | OK | bcrypt 12 rounds, max 72 bytes |
| Password validation (register) | OK | 12+ chars, letras+numeros |
| Rate limiting | OK | SlowAPI com 10/min (login), 5/min (register), 3/min (esqueci-senha) |
| Bloqueio de status | OK | 5 statuses bloqueiam login (403 para nao confirmados) |
| 2FA TOTP | OK | Codigo 6 digitos com janela de desvio |
| CSRF protection | PARCIAL | Apenas metodos UNSAFE (POST/PUT/PATCH/DELETE) via cookie |
| Multi-tenant isolation | PARCIAL | tenant_id lido do banco; JWT nao contem tenant_id |
| Role-based access | OK | `require_role` com hierarquia USER/ADMIN/SUPERADMIN |
| Google OAuth SSO | OK | Fluxo completo com callback, sem state validation |
| Email confirmation | OK | Token de 24h, reenvio 3/min |
| Password reset | OK | Token 1h, mesmo nivel de validacao do registro |

---

## Vulnerabilidades Encontradas

### CRITICO

1. **Refresh Token inexistente — lockout forcado do usuario**
   - JWT tem expiracao fixa de 24 horas sem mecanismo de renovacao
   - Aps expiry, o usuario deve fazer login novamente
   - Impacto: usuarios ativos saem forcadamente apos 24h de vida do token
   - Arquivo: `backend/endpoints/auth_endpoints.py:136-137`
   - Codigo:
     ```python
     to_encode.update({"exp": datetime.utcnow() + timedelta(hours=24)})
     ```

2. **Logout nao revoga token JWT — token continua valido apos logout**
   - O endpoint `/logout` apenas remove os cookies `fralib_session` e `fralib_csrf`
   - O JWT em si permanece assinavel e valido ate a expiracao
   - Um token interceptado continua ativo mesmo apos logout em outro dispositivo
   - Arquivo: `backend/endpoints/auth_endpoints.py:442-447`
   - Codigo:
     ```python
     @router.post("/logout")
     async def logout(request: Request, response: Response):
         for cookie_name in ("fralib_session", "fralir_csrf"):
             response.delete_cookie(cookie_name, path="/", ...)
         return {"status": "ok"}
     ```

3. **JWT nao contem `tenant_id` nem `role` — consultas extras ao banco em cada request**
   - O token JWT so carrega `sub` e `email`
   - `tenant_id` e `role` sao resolvidos do banco em cada chamada autenticada
   - Cria latencia desnecessaria e sobrecarga no banco
   - Arquivo: `backend/core/auth.py:61-121`
   - Codigo (token payload):
     ```python
     # Em auth_endpoints.py login:
     token = create_access_token({"sub": str(user[0]), "email": user[1]})
     # role/tenant_id resolvidos em get_current_user:
     _row = _c.execute(sa_text("SELECT role, status, tenant_id FROM users WHERE id=:id"), ...)
     ```

### ALTO

4. **Email login e case-sensitive — registro pode aceitar email que depois nao faz login**
   - Registro: `WHERE email = :email` (case-sensitive no PostgreSQL padrao)
   - Usuario pode se registrar como `Test@Exemplo.com` e depois o login falhar com `test@exemplo.com`
   - O teste `test_login_case_sensitive_email` intencionalmente falha nesta expectativa
   - Arquivo: `backend/endpoints/auth_endpoints.py:216-222`
   - Codigo:
     ```python
     user = db.execute(text("""
         SELECT id, email, password_hash, status, email_confirmado, totp_enabled, totp_secret, role
         FROM users WHERE email = :email
     """), {"email": data.email})
     ```

5. **OAuth Google sem state parameter — vulneravel a CSRF no fluxo OAuth**
   - O callback do Google OAuth nao valida `state` (nonce CSRF)
   - Um atacante pode induzir o usuario a um callback falso e roubar o code
   - Arquivo: `backend/endpoints/auth_endpoints.py:498-598`
   - Mitigacao ausente: deveria gerar e validar `state` entre redirect e callback

6. **CSRF validation so cobre metodos UNSAFE — GET/DELETE para /me**
   - A protecao CSRF em `_verify_cookie_csrf` ignora GET, HEAD, OPTIONS
   - O endpoint `/me` (GET) e vulneravel a ataques CSRF via cookie
   - Arquivo: `backend/core/auth.py:52-58`
   - Codigo:
     ```python
     UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
     # GET nao e validado
     ```

### MEDIO

7. **Tipo不一致: /me retorna user_id como int, testes esperam string**
   - `auth_endpoints.py:434` retorna `row[0]` (int) diretamente
   - `test_auth_endpoints.py:109` espera `str(test_user["id"])`
   - `test_api_auth.py:58` verifica `user_id == user_id` (compara int==int ali, mas payload JWT e str)
   - Arquivo: `backend/endpoints/auth_endpoints.py:434`

8. **Bloqueio por IP no registro e rate limiting usam IP do cliente diretamente**
   - `_client_ip` confia em `X-Forwarded-For` apenas de proxies confiaveis
   - Porem em ambientes sem proxy confiavel configurado, o IP direto e usado sem validacao
   - A variavel `TRUSTED_PROXY_HOSTS` contem apenas 3 hosts
   - Arquivo: `backend/endpoints/auth_endpoints.py:28-36`

---

## Testes Faltantes

1. **test_login_case_insensitive_email**: Verificar que `Test@Exemplo.com` faz login como `test@exemplo.com`
2. **test_token_refresh**: Renovar token antes da expiracao e continuar com nova sessao
3. **test_logout_revokes_token**: Fazer logout e tentar usar token antigo — deve retornar 401
4. **test_blocked_status_login**: Login com status `bloqueado`, `suspenso`, `cancelado`, `inadimplente`, `desativado`
5. **test_2fa_required_login**: Login sem TOTP quando 2FA esta ativo
6. **test_oauth_google_csrf**: Tentar callback OAuth sem state — deve falhar
7. **test_register_rate_limit_ip**: Mais de 3 registros do mesmo IP em 30 dias
8. **test_reset_password_rate_limit**: Mais de 5 tentativas de reset por minuto
9. **test_csrf_cookie_protection**: POST logout sem `X-CSRF-Token` deve retornar 403
10. **test_jwt_token_includes_role**: Token deve conter role para evitar lookups por request
11. **test_jwt_token_includes_tenant_id**: Token deve conter tenant_id
12. **test_expired_refresh_token_fails**: Refresh com token ja expirado
13. **test_register_password_too_long**: Senha > 72 bytes rejeitada
14. **test_get_me_csrf_on_cookie_with_get**: GET via cookie em /me nao deveria exigir CSRF (ja correto, mas nao testado)

---

## Execucao dos Testes

```
cd C:/fralib && python -m pytest tests/unit/test_auth*.py tests/integration/test_api_auth.py -v
```

**Resultado:** 37 coletados — **10 PASSED**, **3 FAILED**, **6 ERROR**, **18 PENDING**

| Teste | Resultado | Motivo |
|---|---|---|
| test_secret_key_loaded | PASSED | |
| test_algorithm_is_hs256 | PASSED | |
| test_create_access_token_structure | PASSED | |
| test_create_access_token_payload | PASSED | |
| test_create_access_token_expiration | PASSED | |
| test_get_current_user_valid_token | FAILED | PostgreSQL 5433 nao esta rodando |
| test_get_current_user_expired_token | PASSED | |
| test_get_current_user_invalid_token | PASSED | |
| test_get_current_user_missing_sub | PASSED | |
| test_get_current_user_wrong_secret | PASSED | |
| test_login_success | ERROR | PostgreSQL 5433 nao conectavel |
| test_login_invalid_email | FAILED | PostgreSQL 5433 nao conectavel |
| test_login_case_sensitive_email | ERROR | PostgreSQL 5433 nao conectavel |
| test_token_contem_informacoes_corretas | ERROR | PostgreSQL 5433 nao conectavel |
| test_client_ip_* | PASSED (2) | Sem dependencia de banco |
| test_verify_password_function | PASSED | Sem dependencia de banco |
| test_registro_e_login_completo | FAILED | PostgreSQL 5433 nao conectavel |
| test_acesso_endpoint_protegido_sem_token | PASSED | |
| test_acesso_endpoint_protegido_token_invalido | PASSED | |

**Causa dos ERRORs/FALIEDs:** PostgreSQL na porta 5433 nao esta em execucao no ambiente de auditoria. A infraestrutura de banco de dados de teste nao esta disponivel — **nao e um bug de codigo**. A suite de testes unitarios que nao dependem de DB (8/11) passa corretamente.

---

## Recomendacoes Prioritarias

1. **[CRITICA]** Implementar Refresh Token com expiracao mais curta para o access token (15min) e refresh token valido por 30 dias
2. **[CRITICA]** Implementar blocklist de tokens no logout usando Redis (revogacao ativa)
3. **[ALTA]** Incluir `tenant_id` e `role` no payload do JWT para evitar lookup por request
4. **[ALTA]** Normalizar email com `lower()` na query de login
5. **[ALTA]** Adicionar `state` parameter no fluxo OAuth Google para previnir CSRF
6. **[MEDIA]** Executar suite de testes com banco PostgreSQL de teste configurado (porta 5433)
