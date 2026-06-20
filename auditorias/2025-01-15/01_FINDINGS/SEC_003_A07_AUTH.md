# SEC_003_A07_AUTH.md — Email Confirmation Token Transmitido via GET Request (URL)

## Metadata

| Campo | Valor |
|---|---|
| Severity | HIGH |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/endpoints/auth_endpoints.py` |
| Lines | 334–348 |
| CVSS 3.1 | 7.5 (High) — AV:N/AC:H/PR:N/UI:R/C:H/I:N/A:N |

## Vulnerabilidade

O token de confirmacao de email e transmitido como parametro de query string em uma requisicao GET:

```python
# auth_endpoints.py, linhas 334–348
@router.get("/confirmar-email")
@limiter.limit("10/minute")
async def confirmar_email(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT id, confirm_expires FROM users WHERE confirm_token = :token"),
        {"token": token}
    ).fetchone()
    if not user:
        return _pagina_confirmacao("Link invalido", ...)
```

O token e transmitido diretamente na URL:
```
GET /api/auth/confirmar-email?token=xyz123...
```

Isso expoe o token a multiplos vetores de interceptacao:

1. **Browser History**: URLs com tokens ficam gravadas permanentemente no historico do navegador
2. **Referer Header**: Se a pagina de email tiver imagens/CDN externos, o token e enviado no header `Referer`
3. **Server Logs**: Apache/Nginx/logs de aplicacao registram a URL completa com token em texto plano
4. **Proxy/Corporate Firewall**: Proxies corporativos fazem log de URLs acessadas
5. **Email Server**: Logs do servidor de email (Resend) contem a URL completa

**Informacao Adicional**: Alem da exposicao, o token tem vida longa (24h de expiracao, mas pode ser reutilizado indefinidamente ate confirmar) e NAO e invalidado apos ser reutilizado (nao ha rotacao).

## Impacto

- **Account Takeover**: Qualquer pessoa com acesso aos logs do servidor, historico de browser, ou emails interceptados pode confirmar email de usuario
- **Exposicao em Logs**: Arquivos de log de accessos web conterao tokens em texto plano, violando GDPR/LGPD
- **Vazamento por Referer**: Plugins de analytics ou imagens em emails podem vazar tokens para terceiros
- **Persistência**: Tokens em logs podem ser encontrados em backups de logs meses/anos apos gerados

## Exploit

```bash
# 1. Acessar logs de servidor (ex: falha de seguranca, acesso indevido)
grep "confirmar-email" /var/log/nginx/access.log

# Resultado: IPs, timestamps e tokens em texto plano
# 192.168.1.1 - - [15/Jan/2025:10:00:00 +0000] \
#   "GET /api/auth/confirmar-email?token=abc123def456... HTTP/1.1" 302

# 2. Usar token para confirmar email
curl "https://app.seunegociofralib.site/api/auth/confirmar-email?token=abc123def456..."

# Conta da vitima ativada pelo atacante
```

## Remediation

1. **Mudar para POST com body JSON** (OWASP recommended):

```python
@router.post("/confirmar-email")
@limiter.limit("10/minute")
async def confirmar_email(request: Request, data: dict, db: Session = Depends(get_db)):
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token obrigatorio")
    ...
```

2. **Ou usar path parameter** (mais limpo):
```python
@router.post("/confirmar-email/{token}")
async def confirmar_email(request: Request, token: str, db: Session = Depends(get_db)):
    ...
```

3. **Invalidar token apos uso** (obrigatorio):
```python
db.execute(text("""
    UPDATE users SET email_confirmado=true,
                     confirm_token=NULL,
                     confirm_expires=NULL,
                     confirm_token_used_at=NOW()
    WHERE id=:id
"""), {"id": user[0]})
```

4. **Truncar logs de URL** no Nginx:
```nginx
location /api/auth/confirmar-email {
    access_log off;  # Desligar log deste endpoint
    # OU mascarar parametro
    log_format masked '$remote_addr - $request_uri';
    # Substituir token nos logs
}
```

## Referencia

- CWE-598: Information Exposure Through Query Strings in URL
- OWASP A07:2021 – Authentication Failures
- OWASP ASVS 2.2.5 — Verify that secrets, tokens, and passwords are not displayed in URLs
- NIST SP 800-63B — Secrets sent via URLs are prohibited
