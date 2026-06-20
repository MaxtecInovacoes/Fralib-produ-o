# SEC_006_A07_AUTH.md — Token Revocation is No-Op When Redis is Unavailable

## Metadata

| Campo | Valor |
|---|---|
| Severity | MEDIUM |
| OWASP Category | A07:2021 – Authentication Failures |
| File | `backend/core/auth.py` |
| Lines | 40–52 |
| CVSS 3.1 | 5.9 (Medium) — AV:N/AC:H/PR:N/UI:N/C:H/I:N/A:N |

## Vulnerabilidade

A funcao `revoke_token` retorna sem fazer nada se o Redis nao estiver disponivel:

```python
# auth.py, linhas 40–52
def revoke_token(token: str) -> None:
    """Adiciona token à blacklist até expiração."""
    redis = _get_redis()
    if not redis:
        return  # <-- NO-OP: token NAO e revogado!
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                             options={"verify_exp": False})
        exp = payload.get("exp", 0)
    except Exception:
        exp = int(time.time()) + 86400  # Default 24h <-- Fallback inseguro
    ttl = max(1, exp - int(time.time()))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis.setex(f"revoked_token:{token_hash}", ttl, "1")
```

O fallback de 24h (86400 segundos) e usado quando o decode falha. Isso significa que:
1. Se Redis cair, usuarios NAO poderao fazer logout (tokens continuarao validos)
2. Se o token for invalido/malformado, e atribuido TTL de ate 24h de qualquer forma
3. O TTL maximo pode ser maior que a vida util original do token (se `exp` e muito alto ou a diferenca de tempo e grande)

**Cenario de exploito:**
- Usuario faz login em computador publico
- Usuario clica logout
- Redis esta fora do ar
- `revoke_token` faz nothing
- Token JWT continua valido por ate 24h mais
- Atacante com acesso ao mesmo computador usa o token para acessar a conta

## Impacto

- **Sessao persistindo apos logout**: Computadores compartilhados/comprometidos permanecem autenticados
- **Indisponibilidade de seguranca**: Falha em componente nao critico (Redis) desabilita controle de seguranca (revogacao)
- **Fail-open**: Sistema falha de forma insegura ao inves de falhar fechado
- **TLS/TTL indefinido**: Fallback de 24h pode ultrapassar a vida util real do token

## Remediation

```python
def revoke_token(token: str) -> None:
    """Adiciona token à blacklist até expiração."""
    redis = _get_redis()
    if not redis:
        # FAIL SECURE: logar erro critico e lancar excecao
        # Nao deixar token存活 apos logout intencional
        import logging
        logging.error(
            "[AUTH] Redis indisponivel — revoke_token falhou. "
            f"Token nao pode ser revogado. Audience: logout request."
        )
        raise RuntimeError(
            "Token revocation unavailable — authentication service degraded. "
            "Please try again later."
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                             options={"verify_exp": False})
        exp = payload.get("exp", 0)
    except jwt.InvalidTokenError:
        # Token invalido — nao ha o que revogar, mas logar
        import logging
        logging.warning(f"[AUTH] Tentativa de revogar token invalido.")
        return  # OK: token invalido ja nao funciona

    now = int(time.time())
    if exp <= now:
        return  # Ja expirou, nao ha o que revogar

    # TTL = min(expiry, original_max_24h) para bound
    ttl = min(max(1, exp - now), 86400)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis.setex(f"revoked_token:{token_hash}", ttl, "1")
```

Adicionalmente, garantir que o Redis seja configurado com alta disponibilidade (Sentinel/Cluster) para que a revogacao nao falhe em producao.

## Referencia

- CWE-404: Improper Resource Shutdown or Release
- CWE-755: Improper Handling of Exceptional Conditions
- OWASP A07:2021 – Authentication Failures
- OWASP Session Management Cheat Sheet — Session Termination
