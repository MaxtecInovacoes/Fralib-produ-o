# PLAYBOOK — PIPELINE FRA LIB VALIDADA (Tenant 2 / VPS Nova)

**Última validação:** 2026-07-30 23:59 UTC | **Status:** ✅ PONTA-A-PONTA FUNCIONAL
**Site gerado:** https://app.seunegociofralib.site/sites/2/nova-imperio-gym-236f7cb9/

---

## 🎯 OBJETIVO

Este documento permite a **qualquer IA** reproduzir a pipeline de testes isolada que gerou um site real e deployado. Contém os comandos exatos, estado da VPS, e o script de teste E2E.

---

## 📋 ESTADO VALIDADO DA ESTEIRA

### Cadeia completa (8 estágios) — TODOS OK

```
[1] BANCO       ✅ Carrega lead direto do Postgres
[2] HUNTER      ✅ Valida lead_data (passa direto)
[3] CAIO        ✅ tier=MORNO, score=55, qualificado
[4] ARQUITETO   ✅ PRD com 6 seções (~35s via LLM)
[5] BUILDER     ✅ HTML 131KB via 4 chunks LLM (~200s)
[6] QA v2       ✅ Vision score 7.9/10 PASSED (~111s)
[7] DEPLOY      ✅ Site salvo em /var/www/fralib/sites/...
[8] FRANZ       ✅ Lead marcado para outreach
```

### Métricas da última execução válida

| Métrica | Valor |
|---------|-------|
| HTML final | **131.719 bytes** (~128 KB) |
| Tempo total | ~8 min 30s |
| Vision QA | **7.9/10** (PASSED) |
| Chunks LLM | 4 sucessos em 4 tentativas |
| Erros | NENHUM |

---

## 🏗️ INFRAESTRUTURA (VPS Nova)

### Acesso
```
SSH:      ssh -i ~/.ssh/id_ed25519 root@100.124.56.36  (via Tailscale)
Projeto:  /opt/fralib/
OpenUI:   /root/fralib/openui-service-wandb/ (serviço systemd)
Domínio:  https://app.seunegociofralib.site
```

### Containers Docker rodando

| Container | Função | Porta | Status |
|-----------|--------|-------|--------|
| `fralib-api` (systemd) | API FastAPI | 8000 | active |
| `fralib-worker-pipeline-1` | Consome fila pipeline_lead | - | running |
| `fralib-worker-cron-1` | lead_supply_hunter, lead_production_tick | - | healthy |
| `fralib-worker-franz-1` | SDR WhatsApp | - | healthy |
| `fralib-postgres-1` | PostgreSQL | 15434→5432 | healthy |
| `fralib-redis-1` | Cache | 16379→6379 | healthy |
| `fralib-openui` | Python HTML generation via LiteLLM (systemd) | 7878 | active |

### Variáveis de ambiente críticas

**`/opt/fralib/.env`:**
```bash
DATABASE_URL=postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db
ANTHROPIC_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0
ANTHROPIC_BASE_URL=https://deployflow.com.br/api/public/v1
LLM_BASE_URL=https://deployflow.com.br/api/public/v1
DEPLOYFLOW_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0  # mesma que ANTHROPIC_API_KEY
DEPLOYFLOW_BASE_URL=https://deployflow.com.br/api/public/v1
FRALIB_PUBLIC_URL=https://app.seunegociofralib.site
FRALIB_SKIP_HTML_QUALITY_GATE=0
```

**`/root/fralib/openui-service-wandb/backend/.env`:**
```bash
ANTHROPIC_API_KEY=dh-live-5MI2EvgUoAuoLAnP4jn0  # MESMA chave
ANTHROPIC_BASE_URL=https://deployflow.com.br/api/public/v1
MODEL=claude-sonnet-4-6
MAX_TOKENS=64000
PORT=7878
NODE_ENV=production
```

---

## 🚀 COMO EXECUTAR A PIPELINE DE TESTE (PASSO-A-PASSO)

### 1. Pré-requisitos (verificar antes de tudo)

```bash
ssh -i ~/.ssh/id_ed25519 root@100.124.56.36

# Containers rodando?
docker ps --format '{{.Names}} {{.Status}}' | grep fralib

# OpenUI ativo?
systemctl is-active fralib-openui

# Health checks
curl -s http://localhost:7878/v1/models
docker exec fralib-postgres-1 pg_isready -U fralib_user -d fralib_db
```

### 2. Teste E2E Isolado (qualquer lead do tenant 2)

O script `test_chain.py` está em `/opt/fralib/test_chain.py`.

```bash
# Executar direto (requer venv ativo)
cd /opt/fralib && .venv/bin/python test_chain.py
```

**O que o script faz:**
1. Carrega lead `236f7cb9-99c8-456a-ab62-0fa3de88f81d` ("Nova Imperio Gym") direto do banco
2. Constrói `PipelineState` manualmente (sem worker, sem fila)
3. Executa cada step do Manager: `step_hunter` → `step_caio` → `step_arquiteto` → `step_builder` → `step_quality_gate` → `step_deploy` → `step_franz`
4. Imprime status de cada agente + URL final do deploy

**Para testar outro lead:** edite a constante `LEAD_ID = "..."` no topo do script.

### 3. Saída esperada (sucesso)

```
============================================================
[BANCO] OK 11 campos carregados
[HUNTER] OK → qualifying (0.0s)
[CAIO] OK tier=MORNO score=55 (0.0s)
[ARQUITETO] OK PRD gerado: Nova Império Gym | 6 secoes (34.9s)
[BUILDER] OK HTML gerado: 131719 chars | model=claude-sonnet-4-6 (199.8s)
[QUALITY GATE] OK score=7.9/10 passed=True (111.5s)
[DEPLOY] OK site em https://app.seunegociofralib.site/sites/2/nova-imperio-gym-236f7cb9/ (0.0s)
[FRANZ] OK lead marcado para outreach (0.0s)

✅ PIPELINE PONTA-A-PONTA FUNCIONOU!
HTML salvo em: /var/www/fralib/sites/2/nova-imperio-gym-236f7cb9/index.html
```

---

## 🧩 ARQUITETURA TÉCNICA

### Fluxo de dados

```
┌──────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│ test_    │───▶│ Manager  │───▶│ step_*     │───▶│ Deploy   │
│ chain.py │    │ FSM      │    │ functions  │    │ (nginx)  │
└──────────┘    └──────────┘    └─────┬──────┘    └──────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
   ┌─────────┐                  ┌──────────┐                  ┌──────────┐
   │ OpenUI  │ ◀──HTTP 7878────│ Builder  │                  │ Postgres │
   │ Python  │                  │ agent.py │                  │ :15434   │
   └─────────┘                  └──────────┘                  └──────────┘
```

### wandb/openui Python + LiteLLM (single-shot)

**Arquivo:** `/root/fralib/openui-service-wandb/backend/openui/generate.py`

Endpoints:
- `POST /generate` — single-shot (usa LiteLLM proxy → DeployFlow → Claude)
- `GET /v1/models` — health check (list models do LiteLLM)

Lógica:
1. Builder injeta `_lead_rating`, `_lead_reviews_count`, `_lead_telefone` no PRD antes de enviar
2. OpenUI recebe PRD completo → chama LiteLLM com `max_tokens=64000`, `model=claude-sonnet-4-6`
3. LiteLLM proxy roteia para DeployFlow (`https://deployflow.com.br/api/public/v1`)
4. Retorna HTML completo em uma única chamada (sem chunking)
5. Builder injeta contratos determinísticos: LGPD, favicon, JSON-LD, motion.js

### Por que single-shot substituiu chunking

wandb/openui com LiteLLM proxy lida diretamente com a sobrecarga do modelo. O proxy gerencia rate limiting e retry internamente. Uma única chamada de até 64K tokens é mais simples, mais rápida e evita a complexidade de concatenar HTML fragmentado. Se DeployFlow retornar 529, o retry é tratado no nível do Builder (`step_builder` no manager), não no OpenUI.

---

## 🔧 PADRÕES E REGRAS (NÃO QUEBRAR)

### Código (CLAUDE.md)
1. NÃO usar LangGraph — orquestrador é FSM pura
2. NÃO usar renderers alternativos — Builder OpenUI é o único caminho
3. NÃO duplicar agentes — melhore `agent.py` existente
4. NÃO mexer em `agents/_shared/` (só tem `_text_utils.py`)
5. Git: `SKIP_V11_PROTECTION=1 git commit -m "..."` se v1.1 protection bloquear

### Deploy
- Push: `git push origin master` → post-receive hook na VPS
- Não rebuildar containers sem necessidade — volumes persistem mudanças em `/opt/fralib/backend/`
- Para mudanças em `agent.py` ou outros arquivos do `backend/`: restart `fralib-api` (systemd) + `fralib-worker`
- Para mudanças em `openui-service-wandb/`: restart `fralib-openui` (systemd)

### Logs
- Worker unificado: `docker logs -f fralib-worker-1`
- OpenUI: `journalctl -u fralib-openui -f`
- API: `journalctl -u fralib-api -f`

---

## 📂 ESTRUTURA DE DOCUMENTOS NA VPS

```
/opt/fralib/
├── docs/
│   ├── ARCHITECTURE_SPEC.md          # Spec original (Knowledge-Centered OS)
│   ├── ARCHITECTURE_DIAGRAM.md       # Diagrama de agentes
│   ├── DESIGN_DECISIONS.md           # Decisões de design por agente
│   ├── SDR_ERROR_REFERENCE.md        # Erros conhecidos do Franz
│   ├── VPS_SETUP.md                  # Setup da VPS
│   ├── AGENT_MAPPING_ANALYSIS.md     # Mapeamento de agentes
│   ├── lead-request-system-map.md    # Sistema de pedidos de lead
│   ├── PIPELINE_FIX_PLAN.md          # Plano original de fixes
│   ├── BRIEF_CLAUDE_VPS_TENANT2.md   # Brief para Claude Code mecânico
│   ├── PLAYBOOK_PIPELINE_VALIDADA.md # ← ESTE ARQUIVO
│   ├── BUGS_E_ACERTOS.md            # ← Cronologia de bugs/fixes
│   └── ARQUITETURA_DEPLOY.md         # ← Infra Docker + systemd
├── test_chain.py                     # Script E2E isolado
├── backend/
│   ├── agents/
│   │   ├── manager/agent.py          # FSM orquestrador (FIXES: linha 541)
│   │   ├── hunter/agent.py           # Mineração de leads
│   │   ├── caio/agent.py             # Qualificação determinística
│   │   ├── arquiteto/agent.py        # DesignerPRD via LLM (FIX: retry 529)
│   │   ├── builder/agent.py          # HTML gen (single-shot, max_tokens=64000)
│   │   ├── builder/quality_gate_v2/  # Vision QA (FIX: removido executable_path)
│   │   └── franz/agent.py            # SDR WhatsApp
│   └── services/
│       ├── lead_supply_engine.py     # Loop inventário (FIX: f-string linha 977)
│       ├── llm_router.py             # Multi-provider LLM
│       └── ...
├── worker.py                         # Daemon fila
├── docker-compose.prod.yml           # Orquestração Docker
└── .env                              # Variáveis de ambiente

/root/fralib/openui-service-wandb/
├── backend/
│   ├── openui/
│   │   ├── main.py               # FastAPI app (LiteLLM proxy + /generate)
│   │   ├── generate.py           # POST /generate → LiteLLM → DeployFlow
│   │   ├── __init__.py
│   │   └── pyproject.toml        # Dependencies (fastapi, uvicorn, litellm)
│   └── .env                      # FRA_GENERATION_MODEL, FRA_GENERATION_MAX_TOKENS
└── Dockerfile                    # Build da imagem OpenUI Python
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

Para confirmar que tudo está funcionando:

```bash
# 1. Containers
docker ps | grep fralib
# Esperado: app-1, worker-pipeline-1, worker-cron-1, worker-franz-1, postgres-1, redis-1, open-seo

# 2. OpenUI
curl -s http://localhost:7878/v1/models
# Esperado: lista de modelos do LiteLLM (ex: claude-sonnet-4-6)

# 3. Test E2E
cd /opt/fralib && .venv/bin/python test_chain.py 2>&1 | grep -E "OK|FAIL|DONE"
# Esperado: 8 linhas "OK", 0 "FAIL", 1 "DONE"

# 4. Site acessível
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://app.seunegociofralib.site/sites/2/nova-imperio-gym-236f7cb9/
# Esperado: HTTP 200

# 5. Postgres leads
docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c "SELECT id, nome, status, site_url IS NOT NULL FROM leads WHERE user_id = 2 LIMIT 5"
# Esperado: status=concluido + site_url preenchido
```

---

## 🎓 COMO ESTENDER PARA OUTROS TENANTS

### Replicar para tenant N:

1. **Banco**: confirmar que `user_id = N` tem leads qualificados:
   ```bash
   docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c \
     "SELECT id, nome, status FROM leads WHERE user_id = N AND status = 'pendente' LIMIT 5"
   ```

2. **Test E2E**: copiar `test_chain.py` e mudar `LEAD_ID` para um lead do tenant N

3. **Worktree local**: editar `LEAD_ID = "<uuid do lead do tenant N>"` e rodar

4. **Verificar**: mesmo checklist acima com `user_id = N`

### Caveats conhecidos

- Cada chamada LLM custa ~$0.05-0.20 (Vision QA + 4 chunks do Builder)
- Tempo total ~8-10min por lead
- DeployFlow pode retornar 529 — retry automático cuida disso
- Se persistir 429/503 por >5min, verificar rate limit no painel DeployFlow

---

## 📞 CONTATOS E RECURSOS

| Item | Valor |
|------|-------|
| Tailscale VPS | `100.124.56.36` |
| Domínio produção | `https://app.seunegociofralib.site` |
| SSH key | `~/.ssh/id_ed25519` |
| Playbook Claude | `https://hermes-agent.nousresearch.com/docs` |
| DeployFlow painel | `https://deployflow.com.br` |

---

## ✨ CONQUISTAS DESTA SESSÃO

- ✅ Pipeline 100% funcional (Hunter → Franz ponta-a-ponta)
- ✅ Bug da chave truncada OpenUI resolvido
- ✅ Executable_path Windows removido do QA v2
- ✅ DeployFlow API key configurada para Vision QA
- ✅ Chunking + retry implementados para evitar 529
- ✅ Timeout Builder ajustado para 600s
- ✅ Domínio atualizado para `app.seunegociofralib.site`
- ✅ f-string bug corrigido em `lead_supply_engine.py`
- ✅ SyntaxError no manager corrigido
- ✅ Site de 131KB deployado e acessível publicamente
