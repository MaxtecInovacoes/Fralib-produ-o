# 🔍 Relatório de Auditoria VPS - FraLib

**Data:** 2026-06-19  
**VPS:** 187.77.37.72  
**Projeto:** `/root/fralib`

---

## 📊 RESUMO EXECUTIVO

| Item | Status | Detalhes |
|------|--------|----------|
| **Commits** | ✅ Sincronizado | master = origin/master |
| **Importações** | ❌ **PROBLEMAS CRÍTICOS** | Módulos não encontrados |
| **Pipeline Tenant 2** | ❌ **47 falhas ativas** | API key 401 Unauthorized |
| **Serviços PM2** | ✅ Online | Todos os serviços rodando |
| **WhatsApp** | ⚠️ Desconectado | 8 jobs pending |

---

## 🚨 PROBLEMAS CRÍTICOS ENCONTRADOS

### 1. Importação Quebrada na VPS

**Erro:**
```
ERRO pipeline_orchestrator_service: No module named 'database'
ERRO vite_react_renderer: No module named 'vite_renderer_models'
```

**Causa Raiz:**
O arquivo `backend/endpoints/pipeline_orchestrator_service.py` na VPS tem:
```python
from database import (  # ❌ IMPORTE ABSOLUTO QUEBRADO
```

Deveria ser:
```python
from backend.core.database import (  # ✅ CORRETO
```

**Arquivos com problema:**
- `backend/endpoints/pipeline_orchestrator_service.py` (linha 13)

---

### 2. Pipeline Falhando - API Key Inválida

**Erro em todos os leads:**
```
"401 Client Error: Unauthorized for url: https://ia.namehost.com.br/v1/messages"
```

**Causa:** A API key do LiteLLM está inválida ou não está configurada corretamente.

**Estatísticas Tenant 2:**
| Métrica | Valor |
|---------|-------|
| Total Leads | 112 |
| Qualificados | 0 |
| Falhas Ativas | 47 |
| Jobs Running | 0 |
| Jobs Pending (WhatsApp) | 8 |

---

### 3. WhatsApp Desconectado

**8 jobs pending** com erro:
```
WhatsApp desconectado — retry em 300s
```

---

## 📁 COMPARAÇÃO LOCAL vs VPS

### Commits
| Local | VPS |
|-------|-----|
| b5c2e3f Refactor pipeline orchestrator into helpers | b5c2e3f ✅ |
| 2d6a90f fix: force named exports... | 2d6a90f ✅ |
| 9cb6a36 fix: wpp listener... | 9cb6a36 ✅ |

**Conclusão:** Commits sincronizados. O problema está no **conteúdo dos arquivos**, não nos commits.

### Arquivos Críticos

| Arquivo | Local | VPS | Status |
|---------|-------|-----|--------|
| `backend/core/database.py` | ✅ | ✅ | OK |
| `backend/services/vite_renderer_models.py` | ✅ | ✅ | OK |
| `pipeline_orchestrator_service.py` | Refatorado | ⚠️ Antigo | **CONFLITO** |

---

## 🔧 AÇÕES NECESSÁRIAS

### 🔴 PRIORIDADE 1: Corrigir Imports Quebrados

O arquivo na VPS está com import absoluto `from database import` que não funciona.
Precisa ser mudado para `from backend.core.database import`.

```bash
# Na VPS, editar:
nano /root/fralib/backend/endpoints/pipeline_orchestrator_service.py

# Mudar linha 13:
# De: from database import (
# Para: from backend.core.database import (

# Depois restart:
pm2 restart fralib
pm2 restart fralib-worker
```

### 🟡 PRIORIDADE 2: Verificar API Key LiteLLM

```bash
# Verificar se a variável está configurada:
ssh root@187.77.37.72 "grep -E 'LITELLM|API_KEY' /root/fralib/.env"

# Testar a API:
curl -H "Authorization: Bearer $(grep LITELLM_API_KEY /root/fralib/.env | cut -d= -f2)" \
     https://ia.namehost.com.br/v1/models
```

### 🟡 PRIORIDADE 3: Reconectar WhatsApp

```bash
# Verificar status do listener:
ssh root@187.77.37.72 "pm2 logs fralib-wpp-listener --lines 20 --nostream"
```

---

## 📋 COMANDOS PARA SINCRONIZAR

### Se quiser puxar mudanças do GitHub para VPS:

```bash
ssh root@187.77.37.72 "cd /root/fralib && git pull origin master && pm2 restart all"
```

### Se quiser fazer push das mudanças LOCAIS para GitHub:

```bash
# No seu computador local:
cd C:\fralib
git add .
git commit -m "fix: corrigir imports quebrados na VPS"
git push origin master
```

---

## ✅ CHECKLIST DE VERIFICAÇÃO

- [ ] Corrigir import `from database` → `from backend.core.database`
- [ ] Reiniciar serviços PM2
- [ ] Verificar API Key LiteLLM
- [ ] Reconectar WhatsApp
- [ ] Reprocessar os 47 leads com falha

---

## 📝 NOTAS

1. **O problema de imports** indica que a refatoração local (`b5c2e3f`) **NÃO FOI APLICADA CORRETAMENTE** na VPS, ou a VPS está rodando uma versão diferente do arquivo.

2. **Commits iguais, código diferente** = possivelmente a VPS foi editada manualmente ou houve um deploy incompleto.

3. **Recomendação:** Usar o fluxo `git pull` ao invés de editar arquivos diretamente na VPS.
