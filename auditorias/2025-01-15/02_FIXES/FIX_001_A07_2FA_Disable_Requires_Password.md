# Fix Report: SEC_002_A07_AUTH - 2FA Disable Without Password

## Vulnerabilidade
**Arquivo:** `backend/endpoints/auth_endpoints.py:460-465`
**Severidade:** HIGH
**OWASP:** A07:2021 - Authentication Failures

## Problema
O endpoint `POST /auth/2fa/disable` permitia desativar 2FA apenas com token de sessão válido, sem exigir senha atual. Qualquer atacante com token de sessão (XSS, cookie roubado) poderia desativar o 2FA e sequestrar a conta.

## Correção Aplicada
Adicionada verificação de senha atual obrigatória no body da requisição:

```python
@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def twofa_disable(request: Request, data: dict, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Desabilitar 2FA requer senha atual para prevenir desativação por atacante."""
    current_password = data.get("current_password")
    if not current_password:
        raise HTTPException(status_code=400, detail="Senha atual obrigatória")

    # Verifica senha atual
    row = db.execute(text("SELECT password_hash FROM users WHERE id=:id"), {"id": usuario["id"]}).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="Conta sem senha configurada")
    if not verify_password(current_password, row[0]):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    db.execute(text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"), {"id": usuario["id"]})
    db.commit()
    return {"status": "ok", "mensagem": "2FA desativado"}
```

## Validação
- [x] Verificação de senha atual obrigatória
- [x] Rate limiting mantido (5/minute)
- [x] Mensagens de erro genéricas para não revelar informações
- [x] Compilação Python OK

## Commits
```
fix: corrige A07 - 2FA disable requer senha atual
```
