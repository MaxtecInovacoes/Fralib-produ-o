# SEC_001_A04_CRYPTO — Vazamento de Tokens JWT em Logs do Servidor

## Metadata

| Campo         | Valor                                                          |
|---------------|----------------------------------------------------------------|
| Severity      | CRITICAL                                                       |
| OWASP Category| A04:2021 — Cryptographic Failures                              |
| Finding ID    | SEC_001                                                        |
| File          | `server.py`                                                    |
| Line(s)       | 433–447                                                        |
| Date          | 2025-01-15                                                     |
| Auditor       | Security Auditor (Claude Code)                                 |

---

## 1. Vulnerabilidade

### Localizacao

`server.py`, linhas 433–447 — classe `_TokenMaskFilter`:

```python
class _TokenMaskFilter(logging.Filter):
    _pat = _re_log.compile(r'(token=)[A-Za-z0-9\-_\.]+')
    def filter(self, record):
        if record.args:
            try:
                record.args = tuple(
                    self._pat.sub(r'\1[REDACTED]', a) if isinstance(a, str) else a
                    for a in record.args
                )
            except Exception:
                pass
        return True
```

### Descricao

O regex `r'(token=)[A-Za-z0-9\-_\.]+'` so mascara parametros de query string
chamados literalmente `token=`. O padrao **nao captura** nenhum dos seguintes
vetores de vazamento:

| Vetor                                         | Mascaredo? | Motivo                                                    |
|-----------------------------------------------|------------|-----------------------------------------------------------|
| `Authorization: Bearer eyJ...`                 | NAO        | Regex nao procura prefixo "Bearer" nem "Authorization"  |
| `?access_token=eyJ...`                        | NAO        | Nome do parametro diferente de `token=`                  |
| `?jwt=eyJ...`                                 | NAO        | Nome do parametro diferente de `token=`                  |
| `?session=eyJ...`                            | NAO        | Nome do parametro diferente de `token=`                  |
| `?code=4/0Ade...` (OAuth authorization code) | NAO        | Regex busca `token=` obrigatoriamente                    |
| Corpo da requisicao (POST/PUT)               | NAO        | Filter so atua em args de log, nao no corpo da requisicao |

Adicionalmente, o filtro so atua sobre o logger `uvicorn.access` — tokens
emitidos via `print()` (usado em `auth_endpoints.py` linhas 63, 64, 92, 94,
108, 110, 399, 401) vao para `stdout` e **nao passam por nenhum filtro**.

### Codigo Exemplo (Exploit Simulado)

```
# Log uvicorn com Authorization header exposto:
GET /api/auth/me HTTP/1.1
Host: api.seunegociofralib.site
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# O log recorded no access.log:
# 187.77.37.72 - - [15/Jan/2025:10:23:01 +0000] "GET /api/auth/me HTTP/1.1" 200 ...
#   <- O header Authorization completo aparecera no log de access se
#      logging configuracao uvicorn incluir headers.
```

---

## 2. Impacto

- **Autenticacao**: Um ator com acesso de leitura aos logs do servidor (infra
  compartilhada, bucket S3, log aggregator, ELK stack) pode extrair tokens JWT
  validos e assumir a sessao de qualquer usuario.
- **Escalacao**: O payload JWT contem `sub` (user_id) e `email` — com o token
  o atacante tem identidade e acesso completo ao tenant da vitima.
- **Lateral Movement**: Token de admin ou superadmin vazado concede acesso
  administrativo.
- **Validade**: Tokens JWT tem duracao de 24 horas (`auth_endpoints.py` linha
  136: `exp = datetime.utcnow() + timedelta(hours=24)`), tempo suficiente
  para exploitar.

---

## 3. Classificacao OWASP

Pertence a **A04:2021 — Cryptographic Failures**:
> "Security misconfigurations or missing encryption in transit leading to
> exposure of sensitive data (e.g. tokens, credentials)."

O texto explicito do codigo (linha 429) confirma a intencao de mascarar
tokens: `"Filtro para mascarar JWT token nos logs de acesso do uvicorn"`.
A implementacao esta incompleta, configurando uma falsa sensacao de seguranca.

---

## 4. Remedio

### 4.1 Correcao do Regex (Minimizacao de Dano)

Expandir o padrao para cobrir os vetores conhecidos:

```python
class _TokenMaskFilter(logging.Filter):
    # Cobre: token=, access_token=, jwt=, session=, auth=, code= (OAuth)
    # e o padrao JWT nu (header eyJ...) em contextos onde apareca como valor.
    _pat = _re_log.compile(
        r'((?:access_token|jwt|session|auth|code|token)[=:])'
        r'([A-Za-z0-9\-_\.]+|eyJ[A-Za-z0-9\-_\.]+)'
    )
    _bearer_pat = _re_log.compile(
        r'(Authorization:\s*Bearer\s+)([A-Za-z0-9\-_\.]+)'
    )
    def filter(self, record):
        if record.args:
            try:
                record.args = tuple(
                    self._bearer_pat.sub(r'\1[REDACTED]', a)
                    if isinstance(a, str)
                    else self._pat.sub(r'\1[REDACTED]', a)
                    if isinstance(a, str)
                    else a
                    for a in record.args
                )
            except Exception:
                pass
        return True
```

### 4.2 Configurar uvicorn para Nao Logar Headers de Autenticacao

Em `server.py` ou no comando de execucao, configurar `uvicorn` com
`--access-log` customizado ou usar o modulo `logging` do Python para
filtrar headers antes da saida.

### 4.3 Eliminar print() com Informacao Sensivel

Substituir `print()` em `auth_endpoints.py` por `logging.getLogger(__name__).info()`
e configurar o logger para niver `INFO` sem expor dados de contexto.

### 4.4 Alternativa de Defesa em Profundidade

Emitir tokens com `jti` (JWT ID) unico e registra-los no Redis blacklist
imediatamente apos emissao, reduzindo a janela de risco em caso de vazamento.

---

## 5. Status

**ABERTO** — Corrigir regex e configurar logging de access para filtrar
headers Authorization antes da emissao.
