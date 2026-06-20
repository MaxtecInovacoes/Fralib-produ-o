# SEC_002_A07_AUTH.md — Google OAuth: Conta Criada como Ativa sem Confirmacao de Email (Session Fixation + Account Takeover)

## Metadata

| Campo | Valor |
|---|---|
| Severity | CRITICAL |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/endpoints/auth_endpoints.py` |
| Lines | 564–582 |
| CVSS 3.1 | 9.0 (Critical) — AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H |

## Vulnerabilidade

O callback do Google OAuth (`/api/auth/oauth/google/callback`) cria uma conta ativa imediatamente ao receber um email do Google, sem nenhuma verificacao de email:

```python
# auth_endpoints.py, linhas 564–582
else:
    # Cria novo usuário via Google OAuth
    now = datetime.utcnow()
    trial_expires = (now + timedelta(days=7)).isoformat()

    user_id = db.execute(
        text("""
            INSERT INTO users (email, nome, status, plano, data_cadastro, trial_expira, google_id)
            VALUES (:email, :nome, 'ativo', 'trial', :now, :trial_expires, :google_id)
            RETURNING id
        """),
        {
            "email": email,
            "nome": name,
            "now": now,
            "trial_expires": trial_expires,
            "google_id": google_id,
        }
    ).fetchone()[0]
    db.commit()
```

Note que `email_confirmado` nao e setado (default do banco ou pode ser NULL/True). Mesmo que o banco default seja `false`, o usuario pode fazer login imediatamente porque:
1. O fluxo normal de `/login` verifica `email_confirmado` antes de autenticar
2. **MAS** o callback do Google OAuth NAO passa pelo `/login` — ele gera JWT diretamente (linha 593)

```python
# Linha 588–593: JWT gerado sem checar email_confirmado
payload = {
    "sub": str(user_id),
    "email": email,
    "exp": datetime.utcnow() + timedelta(hours=24),
}
jwt_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

**Session Fixation:** Um atacante pode:
1. Criar uma conta com email fake via Google OAuth usando um email de vitima (se o Google confirmar)
2. OU, se o Google OAuth não valida email ownership adequadamente, forjar o email de vitima
3. Obter JWT valido sem nenhum tipo de confirmacao
4. Acessar a conta da vitima com todos os privilegios

**Comparacao com fluxo de registro normal:**
O registro por email (linhas 286-295) define `email_confirmado=false` e exige clique em link de confirmacao. O fluxo OAuth pula completamente essa etapa.

## Impacto

- **Session Fixation**: Token gerado sem validacao de email, permite acesso nao autorizado
- **Account Takeover**: Se um atacante conseguir Registrar email de vitima via Google OAuth (se Google nao validar ownership), a vitima perde acesso a propria conta
- **Contas "ativas" sem email verificado**: Usurpacao de identidade
- **Bypass de politicas de seguranca**: O sistema trata o usuario como "ativo" sem qualquer prova de ownership do email

## Exploit

```python
# Simulado — depende de Google OAuth nao validar email ownership
import requests

# Atacante tenta OAuth com email da vitima
# Se Google OAuth nao exigir verificacao de email:
# 1. Atacante registra em Google com email "vitima@empresa.com"
# 2. Usa /oauth/google/callback para obter token
# 3. Token da vitima e gerado sem confirmacao
# 4. Atacante acessa a conta da vitima

# Verificacao do problema: checar se email_confirmado e setado
#apos login OAuth
import requests
r = requests.get("/api/auth/me", headers={"Authorization": f"Bearer {oauth_token}"})
print(r.json())  # Mostra se email_confirmado e null/true/false
```

## Remediation

```python
# Apos criar usuario via OAuth, SEMPRE forcar confirmacao de email
else:
    now = datetime.utcnow()
    trial_expires = (now + timedelta(days=7)).isoformat()
    confirm_token = secrets.token_urlsafe(32)
    confirm_expires = (now + timedelta(hours=24)).isoformat()

    user_id = db.execute(
        text("""
            INSERT INTO users (email, nome, status, plano, data_cadastro,
                               trial_expira, google_id,
                               email_confirmado, confirm_token, confirm_expires)
            VALUES (:email, :nome, 'trial', 'trial', :now, :trial_expires, :google_id,
                    false, :ctoken, :cexp)
            RETURNING id
        """),
        {
            "email": email,
            "nome": name,
            "now": now,
            "trial_expires": trial_expires,
            "google_id": google_id,
            "ctoken": confirm_token,
            "cexp": confirm_expires,
        }
    ).fetchone()[0]
    db.commit()

    # Nao gerar JWT aqui — redirecionar para pagina de confirmacao
    # OU gerar token com claim "pending_email_confirmation=True"
    # que bloqueia operacoes ate confirmacao

    return {
        "status": "pending_confirmation",
        "mensagem": "Conta criada via Google. Confirme seu email para acessar.",
        "email": email,
        "requires_confirmation": True,
    }
```

## Referencia

- CWE-302: Authentication Bypass by Assumed-Immutable Data
- CWE-640: Password Change or Reset Weakness
- OWASP A07:2021 – Authentication Failures
- OWASP Session Fixation
- NIST SP 800-63C — Federation and Assertions
