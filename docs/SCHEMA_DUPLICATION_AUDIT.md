# Auditoria: Duplicações de Schema e Caminho Canônico

Data: 2026-06-20
Auditor: Claude Code

## Resumo Executivo

O FraLib tem **duas tabelas de leads** e **múltiplos schemas** legacy. A fonte de verdade é clara, mas há código redundante que precisa ser eliminado.

---

## 1. As Duas Tabelas de Leads

### Tabela A: `leads` (FONTE CANÔNICA)
- **Schema:** `public.leads`
- **Criada em:** `backend/core/database.py` → `inicializar_database()`
- **Usada por:** Todo o pipeline, dashboard, SDR, analytics
- **Colunas principais:** id, nome, cidade, segmento, telefone, whatsapp, status, url_site, html_gerado, user_id

### Tabela B: `{schema_name}.leads` (LEGADO/ZOMBIE)
- **Schema:** `public.{tenant_schema}.leads` (ex: `tenant_1.leads`)
- **Criada em:** `backend/core/database.py` → `criar_schema_tenant()`
- **Status:** NUNCA USADA ATIVAMENTE
- **Verificação:** `criar_schema_tenant` é apenas `async def` e nunca é chamada no código

### Verificação:
```bash
grep -r "criar_schema_tenant" backend/ --include="*.py"
# Resultado: Apenas na definição, nunca chamada
```

### Ação Necessária:
1. ❌ **NÃO criar** novos schemas por tenant (custo de manutenção)
2. ✅ **Usar** `public.leads` com `user_id` (já implementado)
3. 🧹 **Limpar** código morto de `criar_schema_tenant` em `database.py`

---

## 2. Duplicações de Campos

### Campo: `users.nome` vs `users.name`
| Tabela | Campo | Status |
|--------|-------|--------|
| users | nome | ✅ CANÔNICO |
| users | name | ⚠️ COMPAT (ADD COLUMN IF NOT EXISTS) |

**Origem:** Migração antiga criou `name`, depois adicionaram `nome`

**Regra:** `users.nome` é a fonte de verdade. `users.name` é compat legacy.

### Campo: `users.plano` vs `users.plan`
| Tabela | Campo | Status |
|--------|-------|--------|
| users | plano | ✅ CANÔNICO |
| users | plan | ⚠️ COMPAT (mirrors plano) |

**Origem:** Documentado em ONE_TRUTH_CANONICAL_STATE.md

**Regra:** `users.plano` para decisões de billing. `users.plan` é espelho para compat.

### Campo: `leads.url_site` vs `leads.site_url`
| Tabela | Campo | Status |
|--------|-------|--------|
| leads | site_url | ✅ CANÔNICO |
| leads | url_site | ⚠️ DUPLICADO (ambos existem) |

**Verificação:**
```sql
-- Verificar uso em código
SELECT 'url_site' as campo, COUNT(*) as usos FROM leads WHERE url_site IS NOT NULL
UNION
SELECT 'site_url', COUNT(*) FROM leads WHERE site_url IS NOT NULL;
```

**Regra:** `site_url` é o campo correto. `url_site` é redundante.

---

## 3. Caminho de Dados: Admin → Leads

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO CANÔNICO (FONTE DE VERDADE)                  │
└─────────────────────────────────────────────────────────────────────────────┘

1. ADMIN (Frontend)
   │
   ▼ POST /api/pipeline/iniciar
   │
2. pipeline_start_endpoints.py
   │  └─ Valida: tenant_id, plano, créditos, cooldown
   │
   ▼ job_queue.enqueue()
   │
3. backend/core/job_queue.py
   │  └─ INSERT INTO jobs (tipo, payload, tenant_id, status='pending')
   │
   ▼ Worker polling
   │
4. worker.py
   │  └─ SELECT FOR UPDATE SKIP LOCKED FROM jobs WHERE status='pending'
   │
   ▼ fases do pipeline:
   │
   ├─► Hunter → INSERT INTO lead_inventory (status='raw')
   │            └─ provider: hunter, google_maps, manual
   │
   ├─► Caio → UPDATE lead_inventory SET status='approved/discarded'
   │          score_caio, tier, caio_motivo
   │
   ├─► Design Director → design_context.py
   │     └─ Gera: NichoBriefing, design_tokens
   │
   ├─► Arquiteto Mestre → designer_prd.py
   │     └─ Gera: DesignerPRD (hero, sobre, servicos, contato)
   │
   ├─► Skill Renderer → liam_renderer.py
   │     └─ Gera: HTML via LLM
   │
   ├─► Quality Gate → html_quality_gate.py
   │     └─ Valida HTML antes de aceitar
   │
   └─► PRODUÇÃO
        │
        ├─► INSERT INTO leads (FONTE CANÔNICA)
        │     Campos: id, nome, cidade, segmento, telefone, whatsapp,
        │             site_url (NÃO url_site), status='concluido',
        │             html_gerado, user_id (tenant)
        │
        ├─► INSERT INTO llm_budget_ledger
        │     Campos: tenant_id, job_id, run_id, agent, model,
        │             input_tokens, output_tokens, cost_usd
        │
        └─► INSERT INTO pipeline_run_spans
              Campos: run_id, tenant_id, fase_nome, duracao_ms, custo_usd

┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXOS LEGADO (À ELIMINAR)                         │
└─────────────────────────────────────────────────────────────────────────────┘

❌ criar_schema_tenant() → Cria schema separado por tenant
   └─ Problema: Manutenção duplicada, queries complexas

❌ LeadDB class em database.py → Só para compat, não usar
   └─ Código: backend/core/database.py:162-255

❌ pipeline_queue (tabela) → jobs é a fonte
   └─ Manter apenas para audit/referência

❌ pipeline_state.rodando → jobs.last_phase é a fonte
   └─ Manter apenas para compat legacy
```

---

## 4. Verificações a Fazer

### 4.1 Verificar se `criar_schema_tenant` é usada:
```bash
grep -rn "criar_schema_tenant" backend/
# Esperado: Apenas na definição (database.py:73)
```

### 4.2 Verificar queries que usam schema dinâmico:
```bash
grep -rn "FROM.*\{.*\}" backend/ --include="*.py"
# Esperado: Nenhum resultado ou apenas em código dead
```

### 4.3 Verificar uso de url_site vs site_url:
```bash
grep -rn "url_site" backend/ --include="*.py" | wc -l
grep -rn "site_url" backend/ --include="*.py" | wc -l
# Esperado: url_site = 0 (ou apenas leitura), site_url = muitos
```

---

## 5. Plano de Limpeza

### Fase 1: Identificar Uso (Safety Check)
```python
# scripts/audit_schema_duplication.py
def audit_duplications():
    """
    1. Conta registros em cada tabela duplicada
    2. Verifica se schemas legacy têm dados
    3. Identifica código que escreve em schemas legacy
    """
```

### Fase 2: Migrar Dados (Se Necessário)
```sql
-- Se {schema}.leads tem dados, migrar para public.leads
INSERT INTO public.leads (id, nome, cidade, ...)
SELECT id, nome, cidade, ...
FROM tenant_X.leads;
```

### Fase 3: Eliminar Código Morto
1. Remover `async def criar_schema_tenant()` de `database.py`
2. Remover classe `LeadDB` se não for usada
3. Padronizar `site_url` em todos os endpoints (remover `url_site`)
4. Remover colunas duplicadas de `users` (manter compat com warning)

### Fase 4: Garantir Consistência
1. Adicionar CONSTRAINT para evitar duplicação de `site_url`/`url_site`
2. Criar trigger/rule para normalizar writes
3. Adicionar teste de schema integrity

---

## 6. Regras de Ouro

| Situação | Ação |
|----------|------|
| Novo lead entra no sistema | → `lead_inventory` (status=raw) |
| Lead aprovado pelo Caio | → `lead_inventory` (status=approved) |
| Site é gerado | → `leads` (INSERT) + `lead_inventory` (lead_id link) |
| Dashboard mostra leads | → `leads` WHERE user_id=? |
| Analytics de tokens | → `llm_budget_ledger` |
| Status do pipeline | → `jobs` + `pipeline_failures` |

**NUNCA escrever diretamente em:**
- Schemas por tenant (`tenant_X.leads`)
- `pipeline_queue` (apenas ler para compat)
- `pipeline_state.rodando` (apenas ler para compat)
- `users.plan` (apenas ler, escrever em `users.plano`)

---

## 7. Script de Verificação

```bash
# Rodar para verificar integridade
python pipeline.py smoke --dry-run
python scripts/audit_one_truth.py --pretty
```

Se todos passarem → schema está consistente.
Se falhar → há writes em fontes não-canônicas.
