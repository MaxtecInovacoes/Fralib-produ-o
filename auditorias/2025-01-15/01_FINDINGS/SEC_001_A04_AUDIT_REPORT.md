# OWASP A04:2021 — Cryptographic Failures
## Audit Report — 2025-01-15

---

## Resumo da Auditoria

**Alcance auditado:**
- `server.py`
- `backend/config.py`
- `backend/core/jwt_config.py`
- `backend/endpoints/auth_endpoints.py`

**Dependencias complementares verificadas:**
- `backend/core/auth.py` (revogacao de token, middleware de autenticacao)
- `backend/utils/password_utils.py` (hash de senhas)

---

## Verificacoes OWASP A04 Realizadas

| # | Verificacao                                            | Resultado |
|---|--------------------------------------------------------|-----------|
| 1 | Segredos hardcoded no codigo fonte                     | PASS      |
| 2 | Senhas armazanadas sem sal ou com algoritmos fracos     | PASS      |
| 3 | Algoritmos criptograficos fracos ou deprecated         | PASS      |
| 4 | Falta de HTTPS (cookie secure flag)                    | PASS      |
| 5 | Tokens JWT em URLs (expostos em logs)                  | FAIL (SEC_001) |
| 6 | Falta de sal para senhas                                | PASS      |
| 7 | Dados sensiveis expostos em logs                        | FAIL (SEC_001) |
| 8 | Armazenamento inseguro de secrets em env                | PASS      |

---

## Resultado: FALHAS ENCONTRADAS (1)

### SEC_001 — Vazamento de Tokens JWT em Logs (CRITICAL)

Filtro `_TokenMaskFilter` em `server.py:433-447` usa regex incompleto que
nao mascara headers `Authorization: Bearer`, tokens em parametros com nomes
diferentes de `token=`, nem codigos OAuth.

**Arquivo:** `server.py`
**Linha:** 433–447
**Severidade:** CRITICAL
**Arquivo de finding:** `SEC_001_A04_CRYPTO.md`

---

## Boas Praticas Encontradas

### 1. Seguranca de Senhas (PASS)
`backend/utils/password_utils.py`:
- Usa `bcrypt` com 12 rounds (recomendacao OWASP)
- Sal gerado automaticamente por `bcrypt.gensalt()`
- Limite de 72 bytes imposto para evitar truncamento bcrypt
- `verify_password` usa `bcrypt.checkpw` (comparacao de tempo constante)

### 2. Configuracao JWT (PASS)
`backend/core/jwt_config.py`:
- Segredo lido exclusivamente de `JWT_SECRET_KEY` via `os.getenv`
- Valida tamanho minimo de 32 bytes antes de aceitar
- Lanca `ValueError` na inicializacao se secreto ausente
- Algoritmo HS256 aceito para arquitetura de servico unico

`backend/core/auth.py`:
- `SECRET_KEY` carregado via `get_jwt_secret()` com validacao
- Blacklist de tokens via Redis (SHA-256 do token como chave)
- TTL da blacklist corresponde a expiracao do token

### 3. Cookies com Secure Flag (PASS)
`server.py:332-340` e `auth_endpoints.py:150-171`:
- Flag `secure` configurada dinamicamente com base em:
  - Override via `FRALIB_COOKIE_SECURE` (valores permitidos: 0/false/1/true)
  - Header `X-Forwarded-Proto`
  - Variavel `FRALIB_ENV=prod`
- `samesite=lax` presente em todos os cookies
- `httponly=True` no cookie de sessao

### 4. TOTP / 2FA (PASS)
`auth_endpoints.py:182-199`:
- Implementacao RFC 6238compliant
- SHA-1 HMAC e padrao para TOTP (nao e vulnerabilidade)
- Janela de desvio de 1 token (protecao contra race condition)
- Remocao de codigo em `totp_disable` implementada

### 5. CSRF Protection (PASS)
- Token CSRF gerado com `secrets.token_urlsafe(32)` (256 bits)
- Dupla validacao: cookie + header em `backend/core/auth.py:_verify_cookie_csrf`
- Protecao aplicada a metodos POST/PUT/PATCH/DELETE

### 6. Sem Hardcoded Secrets (PASS)
Todos os arquivos analisados leem segredos exclusivamente de variaveis
de ambiente. Nenhum segredo encontrado hardcoded no codigo fonte.

### 7. Algoritmos Criptograficos (PASS)
- `jwt.encode` usa `HS256` — aceitavel para arquiteturas com segredo
  compartilhado entre componentes do mesmo servico
- `bcrypt` para senhas — estado da arte para hashes de senha
- `hmac.new` + `hashlib.sha1` para TOTP — conforme RFC 6238
- `secrets.token_urlsafe` para tokens CSRF, reset, confirmacao — CSPRNG

---

## Recomendacoes

1. **URGENTE:** Corrigir `_TokenMaskFilter` em `server.py` para cobrir
   `Authorization: Bearer`, `access_token=`, `jwt=`, `session=`, `code=`
   e tokens no corpo de requisicoes.
2. Substituir `print()` em `auth_endpoints.py` por `logging.getLogger()`
   com filtro de sanitizacao.
3. Configurar `uvicorn` para nvel de log de access que nao inclua headers
   de Authorization.

---

## Conclusao

**1 falha CRITICAL** de cryptographic failure encontrada.
As demais verificacoes OWASP A04 passaram — a codebase demonstra boas
praticas de criptografia no armazenamento de senhas, gerenciamento de
tokens e configuracao de cookies.
