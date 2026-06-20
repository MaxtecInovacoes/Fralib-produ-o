# SEC-003 — OWASP A01:2021 Broken Access Control
## Path Hardcoded Permite Acesso Cross-Tenant Se SITES_DIR Nao For /var/www/fralib/sites/

**Severidade:** HIGH
**OWASP Category:** A01:2021 — Broken Access Control
**Subcategoria:** Insecure Deployment / Path Traversal Condicional
**CWE:** CWE-22 (Path Traversal)
**Status:** Vulneravel (ambiente-dependente)

---

## 1. Localizacao

- **Arquivo:** `backend/endpoints/pipeline_edit_endpoints.py`
- **Endpoints afetados:**
  - `POST /api/pipeline/editar-secao` (linha 61)
  - `GET /api/pipeline/listar-secoes/{lead_id}` (linha 108)

---

## 2. Descricao da Vulnerabilidade

Os dois endpoints de edicao de secao de site usam **path absoluto hardcoded** para acessar os arquivos HTML:

```python
# pipeline_edit_endpoints.py linha 61
html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"

# pipeline_edit_endpoints.py linha 108 (mesmo padrao)
html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"
```

O arquivo `leads_crud.py` linha 229 usa corretamente a variavel de ambiente:

```python
# leads_crud.py linha 229 — CORRETO
html_path = f"{SITES_DIR}/{tenant_id}/{slug}/index.html"
```

onde `SITES_DIR` vem de `backend/core/config.py`.

**O problema:** Se `SITES_DIR` no ambiente de producao for configurado como um caminho diferente de `/var/www/fralib/sites/` (por exemplo, `/data/fralib/sites/`), os dois endpoints de `pipeline_edit_endpoints.py` continuarao lendo/escrevendo em `/var/www/fralib/sites/`, potencialmente acessando arquivos de **outros tenants** se o `tenant_id` divergir do `user_id`.

---

## 3. Impacto

**Impacto:** Se o ambiente de producao usa `SITES_DIR` diferente do path hardcoded:

1. Os endpoints `editar-secao` e `listar-secoes` operam no diretorio errado
2. Se `tenant_id != user_id`, um tenant pode acessar/escrever arquivos de outro tenant via path traversal atraves da variavel `tenant_id`
3. Um tenant malicioso pode manipular arquivos HTML de leads de outros tenants
4. O upload de foto em `leads_crud.py` tambem usa `SITES_DIR` (correto), criando **duas origens diferentes** para o mesmo recurso — arquivos de foto em um diretorio, arquivos HTML em outro

**Cenarios:**
- `SITES_DIR = /opt/data/sites` em producao, mas `pipeline_edit_endpoints.py` escreve em `/var/www/fralib/sites/5/` — possivelmente vazio ou de outro ambiente
- Se `tenant_id=3` mas `user_id=5` e `SITES_DIR=/data/sites`, o arquivo ficaria em `/data/sites/3/`, enquanto o upload de foto vai para `/var/www/fralib/sites/5/` — consistencia de dados rompida

---

## 4. Exploit Proof of Concept

```python
# Simulacao: SITES_DIR diferente do hardcoded path
# Configuracao real do ambiente:
#   SITES_DIR = /opt/fralib/sites
#   leads_crud.py upload_foto: /opt/fralib/sites/3/slug/assets/logo.webp
#   pipeline_edit_endpoints.py: /var/www/fralib/sites/3/slug/index.html
#
# Resultado: arquivos de um mesmo lead em DOIS diretorios diferentes
# Alem da inconsistencia, se tenant_id != user_id,
# o arquivo pode estar em diretorio de OUTRO tenant
```

---

## 5. Correcao Recomendada

Substituir o path hardcoded pelo `SITES_DIR` importado de `backend.core.config`:

```python
# No topo do arquivo, adicionar:
from backend.core.config import SITES_DIR

# Linha 61 e 108 — substituir:
# ANTES (vulneravel):
html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"

# DEPOIS (correto):
html_path = f"{SITES_DIR}/{tenant_id}/{slug}/index.html"
```

Garantir que `SITES_DIR` e' lido de `os.getenv("SITES_DIR", "/var/www/fralib/sites")` em `backend/core/config.py`, mantendo compatibilidade com o valor padrao.

---

## 6. Metadata

- **Analisado por:** Claude Security Auditor
- **Data:** 2025-01-15
- **Arquivo de referencia (correto):** `backend/endpoints/leads_crud.py` linha 229 — usa `SITES_DIR`
- **Severidade condicional:** HIGH apenas se `SITES_DIR != /var/www/fralib/sites/`
- **Protecoes existentes:**
  - Slug validado com regex estrito em `_site_slug_from_url_or_name()` (linha 34)
  - `lead_id` validado contra `user_id` antes de acessar arquivo
