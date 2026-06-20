# FIX_007 - Corrigir Path Linux Hardcoded em editar_site

## PROBLEMA
**Local:** `backend/endpoints/leads_crud.py:231, 369`

**Descrição:**
Caminhos Linux hardcoded `/var/www/fralib/sites` em vez de usar variável de ambiente. Isso causa falhas em desenvolvimento Windows ou outros ambientes.

**Impacto:**
- Código não funciona em ambiente Windows
- Não permite configuração de paths customizados
- Acoplamento forte com ambiente de produção específico

## ANTES (Código Problemático)
```python
html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"
assets_dir = f"/var/www/fralib/sites/{tenant_id}/{slug_parts[-1]}/assets"
```

## DEPOIS (Correção)
```python
# Importar do config existente
from backend.core.config import SITES_DIR

# Usar variável de ambiente
html_path = f"{SITES_DIR}/{tenant_id}/{slug}/index.html"
assets_dir = f"{SITES_DIR}/{tenant_id}/{slug_parts[-1]}/assets"
```

## ARQUIVOS A MODIFICAR
1. `backend/endpoints/leads_crud.py` - Usar SITES_DIR do config

## TESTE
```bash
ruff check backend/endpoints/leads_crud.py
# Result: All checks passed!
```

## COMMIT
```
fix: usa SITES_DIR configurável em vez de path hardcoded

Substitui /var/www/fralib/sites por SITES_DIR do .env (FRALIB_SITES_DIR).
Permite desenvolvimento local em Windows.
```
