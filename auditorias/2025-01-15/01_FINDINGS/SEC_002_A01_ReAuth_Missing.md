# SEC-002 — OWASP A01:2021 Broken Access Control
## Missing Re-authentication: 2FA Desabilitado Sem Verificacao de Senha

**Severidade:** HIGH
**OWASP Category:** A01:2021 — Broken Access Control
**Subcategoria:** Privilege Escalation / Missing Re-authentication
**CWE:** CWE-285 (Improper Authorization)
**Status:** Vulneravel

---

## 1. Localizacao

- **Arquivo:** `backend/endpoints/auth_endpoints.py`
- **Endpoint:** `POST /auth/2fa/disable` (linha 460)
- **Dependencia:** `Depends(get_current_user)` — apenas verifica token JWT valido

---

## 2. Descricao da Vulnerabilidade

O endpoint `twofa_disable` permite que qualquer usuario autenticado via token JWT desative o 2FA da propria conta **sem fornecer a senha atual** ou qualquer outro fator de autenticacao.

```python
@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def twofa_disable(request: Request, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    db.execute(text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"), {"id": usuario["id"]})
    db.commit()
    return {"status": "ok", "mensagem": "2FA desativado"}
```

A unica protecao e `Depends(get_current_user)`, que apenas valida que o token JWT e valido e que a conta nao esta bloqueada. Nao ha verificacao de senha atual nem confirmacao do fator 2FA.

**Contraste com o endpoint de troca de senha**, que esta **CORRETAMENTE** protegido em `users_endpoints.py` linha 166-197:

```python
@router.put("/password")
async def update_password(
    data: UserPasswordUpdate,  # Contem current_password
    ...
):
    ...
    if not verify_password(current_password, row[0]):  # <-- verifica senha atual
        raise HTTPException(403, "Senha atual incorreta")
```

---

## 3. Impacto

**Impacto:** Um atacante com acesso a um token de sessao valido (e.g., via XSS, phishing, sessao deixada aberta em computador compartilhado) pode:

1. Fazer login na conta da vitima (mesmo com 2FA ativo, pois o token JWT ja foi emitido)
2. Desativar o 2FA sem fornecer o TOTP/2FA atual
3. Configurar seu proprio 2FA na conta da vitima
4. Conta permanentemente sequestrada — mesmo que a vitima recupere a senha

**Cenarios de ataque:**
- XSS persistente que faz requisicao automatica para `/auth/2fa/disable`
- Computador compartilhado onde usuario deixa sessao logada
- Malware de navegador que rouba cookies de sessao
- Ataque de redefinicao de senha onde atacante ja tem token

---

## 4. Exploit Proof of Concept

```html
<!-- XSS que desativa 2FA automaticamente -->
<script>
fetch('/auth/2fa/disable', {
  method: 'POST',
  credentials: 'include',  // inclui cookie de sessao
  headers: { 'Content-Type': 'application/json' }
});
</script>
```

```bash
# Sessao deixada aberta — qualquer um na maquina pode:
curl -X POST https://api.fralib.com/auth/2fa/disable \
  -H "Authorization: Bearer <token_da_vitima>"
# Resultado: 2FA desativado sem pedir senha
```

---

## 5. Correcao Recomendada

**Exigir senha atual antes de desativar 2FA:**

```python
class TwoFADisableRequest(BaseModel):
    current_password: str
    confirmation: str  # deve ser "DESATIVAR"

@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def twofa_disable(
    request: Request,
    body: TwoFADisableRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    if body.confirmation != "DESATIVAR":
        raise HTTPException(400, "Confirmação obrigatória: envie \"DESATIVAR\"")

    # Buscar hash da senha atual
    row = db.execute(
        text("SELECT password_hash FROM users WHERE id=:id"),
        {"id": usuario["id"]}
    ).fetchone()
    if not row:
        raise HTTPException(404, "Usuário não encontrado")

    # VERIFICAR SENHA ATUAL — mesmo padrao do endpoint /password
    if not verify_password(body.current_password, row[0]):
        raise HTTPException(403, "Senha atual incorreta")

    db.execute(
        text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"),
        {"id": usuario["id"]}
    )
    db.commit()

    # Invalidate all existing sessions (re-authentication required)
    from backend.core.auth import revoke_all_user_tokens
    revoke_all_user_tokens(db, usuario["id"])

    return {"status": "ok", "mensagem": "2FA desativado"}
```

**Observacao de defesa em profundidade:** Alem da senha, idealmente o endpoint deveria invalidar todos os tokens existentes apos desativar 2FA, exigindo re-login completo (com 2FA, que acabou de ser removido, como fallback).

---

## 6. Metadata

- **Analisado por:** Claude Security Auditor
- **Data:** 2025-01-15
- **Endpoint relacionado (correto):** `PUT /api/users/password` em `users_endpoints.py` — implementa corretamente a verificacao de `current_password`
- **Rate limiting presente:** Sim — `@limiter.limit("5/minute")` — atenua forca bruta mas nao elimina o vetor de ataque
- **Bloqueio por status:** Implementado em `auth.py` linha 153 — usuarios bloqueados nao podem acessar
