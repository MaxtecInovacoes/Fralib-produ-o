# PIPELINE_FIX_PLAN.md — Plano Executável para Claude Code

**Data:** 2026-07-30 | **Projeto:** FraLib SaaS | **Objetivo:** Pipeline ponta-a-ponta funcional

---

## 0. RESUMO EXECUTIVO

A pipeline FraLib (Hunter → Caio → Arquiteto → Builder → Quality Gate v2 → Deploy → Franz) passou por refatoração massiva. Muitos bugs do histórico **JÁ FORAM CORRIGIDOS** no código atual. Este plano foca no que **REALMENTE FALTA** para a pipeline rodar ponta-a-ponta.

### Estado atual dos bugs históricos (validado em 2026-07-30):

| Bug histórico | Status atual | Evidência |
|---|---|---|
| #1 NameError `pesquisar_referencias_jina` | ✅ CORRIGIDO | Arquivo `pipeline_orchestrator_service.py` não existe mais |
| #2 Playwright sync em asyncio | ✅ CORRIGIDO | `playwright_intel.py` não existe mais |
| #3 dict access no worker | ✅ CORRIGIDO | `worker.py:46` usa `job["payload"]` (dict access correto) |
| #4 `_text_only_fallback` mascara falhas QA | ✅ CORRIGIDO | `evaluator.py:612` agora `raise RuntimeError` em vez de fallback sintético |
| #5 UnicodeEncodeError Windows | ❓ VERIFICAR | `scripts/generate_test_sites.py:284` precisa de `sys.stdout.reconfigure` |
| #6 DATABASE_URL hardcoded | ✅ CORRIGIDO | `generate_test_sites.py:34` usa `os.environ.get("DATABASE_URL")` |
| #7 DB_URL hardcoded check_locks | ✅ CORRIGIDO | `check_locks.py:17` usa `os.environ.get("DATABASE_URL")` |
| #8 DeployFlow rate limit | ❌ DEPENDÊNCIA EXTERNA | Precisa de NVIDIA_API_KEYS ativas + GOOGLE_API_KEY no Hunter |
| #9 101 jobs travados | ✅ CORRIGIDO | Causa raiz (bugs 1+2) eliminada |
| #10 23+ leads_cache sem converter | ❌ PENDENTE | Caio rejeita 100% por falta de celular — ver Fase 4 |
| #11 14k+ production_ticks sem pipeline_lead | ❌ PENDENTE | Mesma causa acima |
| #12 3 módulos Knowledge Core faltantes | ✅ CORRIGIDO | `knowledge_journal.py`, `confidence.py`, `semantic_diff.py` existem |
| #13 Chromium no container | ❌ PENDENTE | `playwright install chromium` no Dockerfile |

### Bug NOVO descoberto na inspeção (não está no histórico):

| Bug | Arquivo | Causa | Impacto |
|---|---|---|---|
| N1 | `pipeline_error.log` (25 jul) | Traceback referencia arquivos inexistentes (`openui_renderer.py`, `builder_worker.py`, `pipeline_execution_core.py`) — **log legacy**, código já refatorado | NENHUM — log velho, código atual não tem esses arquivos |

---

## 1. ARQUITETURA ATUAL (como funciona HOJE)

```
Hunter (backend/agents/hunter/agent.py)
  ↓ lead_data + market_intelligence
Caio (backend/agents/caio/agent.py) — qualificação determinística
  ↓ tier QUENTE/MORNO/FRIO + score
Arquiteto (backend/agents/arquiteto/agent.py) — LLM gera DesignerPRD
  ↓ PRD com design_tokens, layout_dna, design_system
Builder (backend/agents/builder/agent.py)
  ↓ POST http://localhost:7878/generate → OpenUI service (Python)
  ↓ HTML + injeções deterministicas (LGPD, favicon, JSON-LD, motion)
Quality Gate v2 (quality_gate_v2/evaluator.py)
  ↓ Playwright screenshots → Vision LLM (DeployFlow) → score 0-10
  ↓ Repair loop se < 7.5 (max 3 tentativas)
Deploy (manager/agent.py:step_deploy)
  ↓ sites/<tenant>/<slug>-<lead_id>/index.html + metadata.json
  ↓ UPDATE leads SET status='concluido', sdr_stage='pendente_wpp'
Franz (backend/agents/franz/agent.py)
  ↓ Cron dispatcher pega leads WHERE status='concluido' AND sdr_stage='pendente_wpp'
  ↓ WhatsApp via whatsmeow (:3001) → mensagem inicial SDR
```

### Entry points:
- `server.py` — FastAPI :8000 (15 routers essenciais em `_ESSENTIAL_ROUTERS`)
- `worker.py` — daemon que consome fila Postgres (4 tipos de job)
- `openui-service-wandb/backend/openui/generate.py` — Python :7878 (wandb/openui + LiteLLM proxy)

### Orquestração:
- `manager/agent.py` — FSM pura (7 estados), `run_pipeline(state)` percorre steps
- `worker.py` — `claim_next()` busca job na fila → roda `_run_pipeline_job` ou `_run_supply_job`
- `lead_supply_engine.py` —/enqueue jobs, loop de inventário, fechar ciclo

---

## 2. O QUE FAZER (plano de execução para Claude Code)

### FASE 1: Correção do bug #5 (UnicodeEncodeError Windows) [TRIVIAL]

**Arquivo:** `scripts/generate_test_sites.py`

**Problema:** `print()` com acento pt-BR crasha em Windows com `cp1252`.

**Fix:** Adicionar logo após os imports:
```python
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
```

**Verificação:**
```bash
cd C:/fralib
python scripts/generate_test_sites.py --help  # não deve crashar
```

---

### FASE 2: Chromium no container Docker [INFRA]

**Arquivo:** `Dockerfile`

**Problema:** Playwright está instalado via `pip install playwright` mas os browser binaries não estão no container. Sem Chromium, o Quality Gate v2 não tira screenshots → falha em todos os jobs de pipeline_lead.

**Fix:** Adicionar after pip install:
```dockerfile
RUN playwright install chromium --with-deps
```

**Verificação:** Buildar container e rodar:
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm fralib-app playwright --version
# Deve mostrar versão sem erro
```

**Nota:** Se rodando localmente (não Docker):
```bash
cd C:/fralib
.venv/Scripts/python.exe -m playwright install chromium
```

---

### FASE 3: Relaxes Caio para leads sem celular [LÓGICA]

**Arquivos:** `backend/agents/caio/agent.py` + `backend/agents/caio/schemas.py`

**Problema (bug #10):** Caio rejeita 100% dos leads de São Paulo por falta de celular. Hunter via Overpass nem sempre tem telefone. 23+ leads_cache acumulados sem converter. 14k+ production_ticks gerados mas nehum pipeline_lead dispara.

**Diagnóstico:** Verificar a regra de qualificação do Caio:
```bash
cd C:/fralib
grep -n "telefone\|whatsapp\|celular\|qualificado" backend/agents/caio/agent.py | head -20
```

**Fix proposta:**
- Se lead tem telefone fixo mas não celular: tier MORNO (não REJEITADO)
- Se lead tem nome + cidade + segmento mas sem telefone: tier FRIO (passa para Franz tentar contato via nome/business)
- Apenas REJEITADO se: sem nome OU sem cidade OU sem segmento
- Franz deve conseguir mensagens via website/e-mail/Google Maps se sem WhatsApp direto

**Verificação:**
```bash
cd C:/fralib
python -c "
from backend.agents.caio.agent import LeadInput, qualificar
lead = LeadInput(nome='Test SP', cidade='São Paulo', segmento='academia', telefone='', whatsapp='')
out = qualificar(lead)
print(f'tier={out.tier} score={out.score} qualificado={out.qualificado}')
# Deve ser MORNO ou FRIO, não REJEITADO
"
```

---

### FASE 4: Verificar chaves LLM ativas (.env) [CONFIG]

**Problema (bug #8):** DeployFlow rate limit + pool NVIDIA vazio → pipeline falha no Builder/QA.

**Verificação:**
```bash
cd C:/fralib
# Verificar chaves críticas estão preenchidas
grep -E "^(NVIDIA_API_KEYS|DEPLOYFLOW_API_KEY|GOOGLE_API_KEY|ANTHROPIC_API_KEY|LLM_API_KEY)=" .env | sed 's/=.*/=<set>/'
```

**Ação se chaves vazias:**
- `NVIDIA_API_KEYS` — configurar pelo menos 1 chave NVIDIA (gratuita, 1000 req/mês) como fallback do LLM
- `DEPLOYFLOW_API_KEY` — se rate limited, aguardar reset (~47h) ou usar NVIDIA como primary
- `GOOGLE_API_KEY` — necessária para PlacesAPI do Hunter (mineração de leads com telefone)

**Teste de conectividade LLM:**
```bash
cd C:/fralib
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
from backend.services.llm_router import call_llm
text, usage = call_llm('anthropic', os.getenv('LLM_MODEL', 'claude-sonnet-4-6'), 'You are a test.', 'Say OK', 0.1, 10)
print(f'LLM OK: {text[:50]}... usage={usage}')
"
```

---

### FASE 5: Teste E2E local da pipeline [VALIDAÇÃO]

**Executar pipeline completa com 1 lead mock:**
```bash
cd C:/fralib
python -c "
from backend.agents.manager.agent import run_pipeline, PipelineState
state = PipelineState(
    tenant_id=1,
    segmento='academia',
    cidade='Curitiba',
    lead_data={
        'nome': 'Academia Teste',
        'cidade': 'Curitiba',
        'segmento': 'academia',
        'telefone': '41999887766',
        'whatsapp': '41999887766',
        'rating': 4.5,
        'reviews_count': 50,
        'website': '',
    }
)
state.run_id = 'test-e2e-001'
result = run_pipeline(state)
print(f'Final state: {result.current_state}')
print(f'Error: {result.error}')
print(f'History: {result.history}')
if result.deploy_url:
    print(f'Site deployado: {result.deploy_url}')
"

# Verificar que o site foi criado
ls -la sites/1/

# Abrir o HTML no navegador para inspeção visual
# sites/1/<slug>-<lead_id>/index.html
```

**⚠ Pré-requisitos para E2E:**
1. OpenUI service rodando: `systemctl restart fralib-openui` (porta 7878)
2. Postgres rodando (DATABASE_URL configurada)
3. LLM API keys válidas (DeployFlow ou NVIDIA)
4. Playwright + Chromium instalados (para QA v2)
5. Se QA v2 falhar por falta de Vision API, setar `FRALIB_SKIP_HTML_QUALITY_GATE=1` para teste

---

### FASE 6: Smoke tests da suite existente [VALIDAÇÃO]
```bash
cd C:/fralib
# Smoke tests sem LLM
python pipeline.py smoke --dry-run

# Tests de agentes
.venv/Scripts/python.exe -m pytest tests/agents/ -v --tb=short 2>&1 | tail -30

# Se algum teste falhar, anotar e reportar
```

---

### FASE 7: Franz / WhatsApp E2E [VALIDAÇÃO]

**Verificar que o lead concluído entra na fila do Franz:**
```bash
# Após FASE 5, verificar no banco:
psql "$DATABASE_URL" -c "
    SELECT id, nome, status, sdr_stage, site_url
    FROM leads
    WHERE status = 'concluido' AND sdr_stage = 'pendente_wpp'
    ORDER BY atualizado_em DESC LIMIT 5;
"

# Verificar whatsmeow ativo (apenas se VPS):
# systemctl is-active whatsmeow
# curl -s http://localhost:3001/api/sessions
```

**Para testar Franz localmente (sem whatsmeow):**
```bash
cd C:/fralib
python -c "
from backend.agents.franz.agent import FranzAgent
agent = FranzAgent()
# Verificar que agent carrega sem erro
print('Franz agent carregado OK')
"
```

---

## 3. PRIORIZAÇÃO

| Fase | Prioridade | Esforço | Bloqueia pipeline? |
|---|---|---|---|
| FASE 1 | Baixa | 2 min | Não (apenas Windows local) |
| FASE 2 | Alta | 10 min | **SIM** — QA v2 precisa de Chromium |
| FASE 3 | Alta | 15 min | **SIM** — leads não passam do Caio |
| FASE 4 | Crítica | 5 min | **SIM** — LLM não responde |
| FASE 5 | Crítica | 10 min | Valida tudo |
| FASE 6 | Média | 5 min | Confirma regressões |
| FASE 7 | Média | 10 min | Valida outreach |

**Ordem executar:** FASE 4 → FASE 2 → FASE 3 → FASE 5 → FASE 6 → FASE 7 → FASE 1

---

## 4. PADRÕES E REGRAS (NÃO QUEBRAR)

1. **NÃO mexer em `agents/_shared/`** — só existe `agents/_text_utils.py` (compat)
2. **NÃO usar LangGraph** — orquestrador é FSM pura
3. **NÃO usar scrapers pagos** — só open-source (Overpass, Nominatim, PlacesAPI)
4. **NÃO usar renderers alternativos** — Builder OpenUI é o único caminho
5. **NÃO duplicar agentes** — se precisar estender, melhore `agent.py` existente
6. **NÃO criar arquivos novos** sem verificar se há agente/pasta apropriado
7. **Git push com bypass de v1.1 protection:** `SKIP_V11_PROTECTION=1 git commit -m "..."`
8. **Backup antes de mudanças grandes:** ver MEMORY.md linha 30

---

## 5. REFERÊNCIAS RÁPIDAS

### Arquivos críticos:
- `backend/agents/manager/agent.py` — FSM orquestrador (748 linhas)
- `backend/agents/builder/agent.py` — Builder (132 linhas,薄 proxy para OpenUI)
- `backend/agents/builder/quality_gate_v2/evaluator.py` — Vision QA (626 linhas)
- `backend/services/llm_router.py` — Router LLM multi-provider (482 linhas)
- `openui-service-wandb/backend/openui/generate.py` — Geração HTML via LiteLLM proxy (single-shot)
- `worker.py` — Daemon fila Postgres (157 linhas)
- `server.py` — FastAPI entry point (15 routers essenciais)

### Providers LLM:
- **Primary:** DeployFlow (`https://deployflow.com.br/api/public/v1`) — usa `x-api-key`
- **Fallback:** NVIDIA API Keys (configurar se DeployFlow rate limited)
- **Vision QA:** DeployFlow (modelos vision via `/chat/completions`)

### VPS:
- SSH: `ssh root@187.77.37.72` (ou `ssh fralib` se configurado)
- Services: `fralib-api`, `fralib-worker`, `fralib-openui`, `fralib-proxy`, `meowhats`
- Deploy: `git push origin master` → post-receive hook
- Postgres: porta 5433
- OpenUI: porta 7878

---

## 6. CHECKLIST FINAL

- [ ] FASE 1: `sys.stdout.reconfigure` em `generate_test_sites.py`
- [ ] FASE 2: `playwright install chromium` no Dockerfile
- [ ] FASE 3: Caio relaxa qualificação para leads sem celular
- [ ] FASE 4: `.env` tem NVIDIA_API_KEYS + DEPLOYFLOW_API_KEY + GOOGLE_API_KEY preenchidas
- [ ] FASE 5: Pipeline E2E com lead mock → state=done + site deployado
- [ ] FASE 6: `pytest tests/agents/` — todos passam
- [ ] FASE 7: Lead concluído aparece com `sdr_stage='pendente_wpp'` no banco
