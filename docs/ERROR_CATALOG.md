# 🐛 Catálogo de Erros dos Tenants — Causa Raiz + Prevenção

> **Para o admin/dev:** "Que erro é esse? Como corrijo? Como evito?"

**Data:** 2026-06-21
**Fonte:** Análise de `pipeline_failures` em produção

---

## 📊 Erros por tenant (atual)

| Tenant | Plano | Falhas totais | Abertas | Tipo de erro |
|--------|-------|---------------|---------|--------------|
| 2 (dezigpi) | ilimitado | 136 | 89 | `_enqueue_caio` (volume) |
| 31 (maxtec) | pro | 70 | 59 | `Pydantic ValidationError` (dados) |
| outros | trial | 5-8 | 5-8 | genéricos (rede/timeout) |

---

## 🔴 Erro #1: `cannot import name '_enqueue_caio'`

### 📍 Onde aparece
- **Tenant:** #2 (dezigpi)
- **Fase:** `lead_supply_hunter`
- **Volume:** 8 falhas idênticas por hora (todas iguais!)
- **Período:** 09:05 às 12:15 do dia 20/06

### 💻 O erro técnico
```
ImportError: cannot import name '_enqueue_caio' from 'backend.services.lead_supply_storage'
```

### 🤔 Por que acontece
O módulo `lead_supply_engine.py:49` e `lead_supply_providers/hunter.py:15` tentam importar `_enqueue_caio` do módulo `lead_supply_storage`, mas a função **está em `lead_supply_inventory.py:339`** (módulo errado).

### 🔍 Como identificar
```bash
ssh root@187.77.37.72
sudo -u postgres psql -p 5433 -d fralib_db -c "
  SELECT COUNT(*), MIN(criado_em), MAX(criado_em)
  FROM pipeline_failures
  WHERE tenant_id = 2
    AND erro_tecnico LIKE '%_enqueue_caio%'
    AND criado_em > NOW() - INTERVAL '7 days';
"
```

### ✅ Como corrigir (1 linha)
```python
# backend/services/lead_supply_engine.py:49
# ANTES:
from backend.services.lead_supply_storage import _enqueue_caio

# DEPOIS:
from backend.services.lead_supply_inventory import _enqueue_caio
```

Mesma correção em `lead_supply_providers/hunter.py:15`.

### 🛡️ Como prevenir para sempre

**Opção A — Helper defensivo (já implementado em parte):**
```python
# backend/services/lead_supply_engine.py
try:
    from backend.services.lead_supply_inventory import _enqueue_caio
except ImportError:
    logger.error("_enqueue_caio nao encontrado - registrando falha mas nao crashando")
    _enqueue_caio = None  # fallback
```

**Opção B — Teste automatizado:**
```python
# tests/unit/test_lead_supply_imports.py
def test_all_imports_resolve():
    """Garante que todas as funcoes cross-module estao acessiveis."""
    from backend.services.lead_supply_engine import _enqueue_caio
    assert callable(_enqueue_caio)
```

**Opção C — Mover função para lugar comum:**
```python
# Criar backend/services/lead_supply_common.py
def _enqueue_caio(db, tenant_id, inventory_id):
    """Funcao compartilhada por todos os modulos lead_supply."""
    ...
```

---

## 🔴 Erro #2: `LeadQualificado - Input should be a valid dictionary`

### 📍 Onde aparece
- **Tenant:** #31 (maxtec)
- **Fase:** `pipeline` (Fase 8 - Arquiteto)
- **Volume:** 10 falhas por hora
- **Causa:** Tenant reusa leads antigos sem todos os campos

### 💻 O erro técnico
```
ValidationError: 1 validation error for LeadQualificado
lead
  Input should be a valid dictionary or instance of LeadRaw [type=model_type, input_value='Nome do Lead', input_type=str]
```

### 🤔 Por que acontece
- Código em `pipeline_orchestrator_service.py:494` cria `LeadQualificado(lead=_lead_raw_r, ...)`
- Espera `lead` ser um objeto `LeadRaw`
- Mas às vezes recebe **string** (nome do lead) ou `None`
- Pydantic rejeita com ValidationError

### ✅ Como corrigir (já feito parcialmente)
- Já criado `safe_qualificar()` em `backend/utils/safe_lead_qualificado.py`
- **Falta aplicar em TODOS os pontos** (não só na linha 494)

Pontos a corrigir:
- `backend/utils/agente1_hunter_v2.py:842` 
- `backend/endpoints/pipeline_lead_flow_helpers.py:288`
- `backend/endpoints/pipeline_orchestrator_service.py:2893`

### 🛡️ Como prevenir para sempre

**Opção A — Usar `safe_qualificar()` em TODOS os lugares:**
```python
# Em vez de:
state.lead_obj = LeadQualificado(lead=lead_raw, ...)

# Usar:
from backend.utils.safe_lead_qualificado import safe_qualificar
state.lead_obj = safe_qualificar(lead_raw, lead_dict, log_fn=_log)
```

**Opção B — Melhorar validação de entrada:**
```python
def _criar_lead_qualificado(lead_raw, lead_dict):
    """Sempre retorna LeadQualificado valido, nunca quebra."""
    if isinstance(lead_raw, str) or lead_raw is None:
        # Recupera via dict
        lead_raw = LeadRaw(nome=lead_dict.get('nome', 'desconhecido'), ...)
    return LeadQualificado(lead=lead_raw, ...)
```

**Opção C — Bloquear na entrada do pipeline:**
```python
# pipeline_orchestrator_service.py - ANTES de processar
def validar_lead_entrada(lead_dict):
    if not lead_dict.get('nome') or not lead_dict.get('cidade'):
        raise ValueError("Lead sem nome/cidade - pular")
```

---

## 🟡 Erro #3: `SSL SYSCALL error: EOF detected`

### 📍 Onde aparece
- **Vários tenants** (incluindo #2)
- **Fase:** `lead_supply_hunter`
- **Causa:** PostgreSQL fecha conexão SSL

### 💻 O erro técnico
```
psycopg2.OperationalError: SSL SYSCALL error: EOF detected
```

### 🤔 Por que acontece
- Conexão SSL com PostgreSQL caiu (timeout/rede)
- Sistema tenta query e falha
- **Já tem auto-fix** (retry com backoff 5s) — mas pode falhar 3x

### ✅ Como corrigir
- **Automático**: Sistema já tem retry via `job_queue` (3 tentativas)
- **Manual**: Aumentar `db.pool_timeout` e `db.pool_recycle`

### 🛡️ Como prevenir
```python
# backend/core/database.py
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # ← testa conexão antes de usar
    pool_recycle=300,      # ← renova a cada 5 min
    pool_size=10,
    max_overflow=20,
)
```

---

## 🟡 Erro #4: `Timeout` / `timed out`

### 📍 Onde aparece
- **Vários tenants**
- **Fase:** `jina_intel` (pesquisa) ou `builder_renderer` (gera site)

### 💻 O erro técnico
```
requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.anthropic.com', port=443): Read timed out.
```

### 🤔 Por que acontece
- API externa (Anthropic, Google) demora > 60s
- Timeout do request expira
- LLM lento ou internet ruim

### 🛡️ Como prevenir
```python
# Aumentar timeout + retry com backoff
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
def call_llm_com_retry(prompt, timeout=120):
    return anthropic_client.messages.create(..., timeout=timeout)
```

---

## 🟡 Erro #5: `429 Too Many Requests`

### 📍 Onde aparece
- **Tenant #2** (volume alto)
- **Fase:** qualquer (usa muito LLM)

### 💻 O erro técnico
```
HTTPError: 429 Client Error: Too Many Requests
```

### 🤔 Por que acontece
- Tenant dispara 50+ jobs em paralelo
- Anthropic limita a X req/min
- Sistema estoura limite

### 🛡️ Como prevenir
```python
# Adicionar rate limiter
from slowapi import Limiter

@limiter.limit("30/minute")  # 30 req/min por tenant
async def processar_lead(lead_id):
    ...
```

---

## 🛡️ **Plano de PREVENÇÃO GERAL (checklist do admin)**

### ✅ Já implementado:
- [x] `safe_qualificar()` (recuperação defensiva)
- [x] `error_diagnostics.py` (classificador de erros)
- [x] `auto_fix.py` (retry inteligente por categoria)
- [x] `alerting.py` (alerta por email)
- [x] Limpeza automática 7d/30d
- [x] Backup diário 02:00

### 🔧 A fazer (quando tiver 5+ tenants):
- [ ] Corrigir import de `_enqueue_caio` (1 linha em 2 arquivos)
- [ ] Aplicar `safe_qualificar()` em todos os pontos de criação
- [ ] Adicionar `pool_pre_ping=True` no engine
- [ ] Adicionar retry com backoff no LLM client
- [ ] Rate limiter por tenant
- [ ] Teste de imports automatizado

### 🔍 Comando útil para investigar erros:
```bash
# Top 10 erros mais frequentes
ssh root@187.77.37.72
sudo -u postgres psql -p 5433 -d fralib_db -c "
  SELECT
    substring(erro_tecnico from 1 for 80) as erro,
    COUNT(*) as total,
    COUNT(DISTINCT tenant_id) as tenants_afetados
  FROM pipeline_failures
  WHERE criado_em > NOW() - INTERVAL '7 days'
  GROUP BY substring(erro_tecnico from 1 for 80)
  ORDER BY total DESC
  LIMIT 10;
"
```

### 📈 Quando cada um importa:
- **< 10 tenants:** Erros são individuais, dá pra corrigir 1 a 1
- **10-50 tenants:** Erros viram **padrão**, vale corrigir a causa raiz
- **> 50 tenants:** Erros precisam de **monitoramento automático** (alertas)

---

## 🎯 Resumo prático

**Top 2 problemas HOJE:**

1. **`_enqueue_caio` (Tenant 2)** - 1 linha de código resolve
2. **`LeadQualificado` validação (Tenant 31)** - 1 helper resolve

**Como prevenir a partir de agora:**

```python
# SEMPRE use safe_qualificar() em vez de LeadQualificado direto
from backend.utils.safe_lead_qualificado import safe_qualificar
state.lead_obj = safe_qualificar(lead_raw, lead_dict, log_fn=_log)
```

```python
# SEMPRE importe do módulo certo
# Adicione teste que falha se import quebrar
def test_all_imports():
    from backend.services.lead_supply_engine import _enqueue_caio
    from backend.services.alerting import send_alert
    from backend.services.auto_fix import tentar_auto_fix
    from backend.services.error_diagnostics import diagnosticar
    assert callable(_enqueue_caio)
    assert callable(send_alert)
```

```bash
# Monitore erros diariamente
cat /var/log/fralib/cleanup.log | tail -20
```

---

**Última atualização:** 2026-06-21
**Próxima revisão:** quando erros > 50/dia ou tenants > 20