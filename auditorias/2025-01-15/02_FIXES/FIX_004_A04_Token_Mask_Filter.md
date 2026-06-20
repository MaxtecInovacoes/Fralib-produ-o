# Fix Report: SEC_001_A04_CRYPTO - JWT Token Log Leak

## Vulnerabilidade
**Arquivo:** `server.py:433-447`
**Severidade:** CRITICAL
**OWASP:** A04:2021 - Cryptographic Failures

## Problema
O filtro `_TokenMaskFilter` apenas mascarava `token=valor` em query strings. Headers Authorization com Bearer tokens, access_token, code OAuth não eram mascarados.

## Correção Aplicada
Regex expandido cobrindo múltiplos vetores de vazamento:

```python
class _TokenMaskFilter(logging.Filter):
    _patterns = [
        _re_log.compile(r'(token=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(Bearer\s+)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(access_token=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(jwt=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(session=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(code=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(refresh_token=)[A-Za-z0-9\-_\.+=/]+'),
        _re_log.compile(r'(eyJ[A-Za-z0-9\-_\.+=/]{10,})'),
    ]
```

## Validação
- [x] Bearer tokens mascarados
- [x] access_token=, jwt=, session=, code= mascarados
- [x] JWT format (eyJ...) mascarado
- [x] Compilação Python OK

## Commits
```
fix: corrige A04 - expande TokenMaskFilter para cobrindo múltiplos vetores
```
