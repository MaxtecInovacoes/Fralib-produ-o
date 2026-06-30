# PIPELINE COMPLETO - AUDITORIA (Hunter → Deploy)

## 📋 RESUMO DO FLUXO

```
LEAD ENTRADA
    ↓
[1] HUNTER ──────────────────────────────────────────────────────────────────┐
    ↓                                                                   │
[2] CAIO (Qualificação)                                                   │
    ↓                                                                   │
[3] JINA (Pesquisa)                                                      │
    ↓                                                                   │
[4] INTELIGÊNCIA (Assets)                                                │
    ↓                                                                   │
[5] FOTOS (Unsplash/Pexels)                                             │
    ↓                                                                   │
[6] AGENTE NICHO (Briefing)                                              │
    ↓                                                                   │
[7] AGENTE VARIAÇÃO (Estrutura) ───────────────────────────────────────► │
    ↓                                                                   │
[8] ARQUITETO MESTRE (DesignerPRD)                                       │
    ↓                                                                   │
[9] BUILDER RENDERER ──────────────────────────────────────────────────► │
    ↓                                                                   │
[9b] QUALITY GATE ──────────────────────────────────────────────────────► │
    ↓                                                                   │
[10] DEPLOY ───────────────────────────────────────────────────────────► │
    ↓                                                                   │
[11] FRANZ (WhatsApp)                                                    │
    ↓                                                                   │
LEAD COM SITE PUBLICADO + CONTATO WHATSAPP
```

---

## FASE 1: HUNTER (Captura de Leads)

### Arquivo:
```
utils/agente1_hunter_v2.py
```

### O que faz:
- Scraping de Google Maps
- Captura: nome, endereço, telefone, avaliações, fotos
- Busca por nicho/geolocalização

### Status: ✅ ATIVO

### Sem LLM: 
```
[1] HUNTER (determinístico)
    └─ Scraping, sem IA
```

---

## FASE 2: CAIO (Qualificação)

### Arquivo:
```
backend/agents/caio.py
```

### O que faz:
- Scoring determinístico do lead
- Regras: segmentação, dados obrigatórios, score
- Decisão: qualificado / não qualificado / reprocessar

### Status: ✅ ATIVO

### Sem LLM:
```
[2] CAIO (determinístico)
    └─ Scoring com regras fixas
```

---

## FASE 3: JINA (Pesquisa de Mercado)

### Arquivo:
```
utils/jina_intelligence.py
```

### O que faz:
- Web scraping + LLM (Haiku)
- Pesquisa de concorrência
- Análise de reviews
- PAA (People Also Ask)

### Status: ✅ ATIVO

### Com LLM:
```
[3] JINA (Haiku)
    └─ ~5% do custo LLM
```

---

## FASE 4: INTELIGÊNCIA (Consolidação)

### Arquivo:
```
backend/endpoints/pipeline_lead_flow_helpers.py
```

### O que faz:
- Consolida assets da fase 3
- Prepara contexto para nicho

### Status: ✅ ATIVO

### Sem LLM:
```
[4] INTELIGÊNCIA (determinístico)
    └─ Consolidação de dados
```

---

## FASE 5: FOTOS (Mídia)

### Arquivos:
```
backend/agents/unsplash_fetcher.py
backend/agents/pexels_video.py
```

### O que faz:
- Busca fotos em Unsplash
- Busca vídeos em Pexels
- Seleção de mídia por nicho

### Status: ✅ ATIVO

### Sem LLM:
```
[5] FOTOS (determinístico)
    └─ APIs Unsplash/Pexels
```

---

## FASE 6: AGENTE NICHO (Briefing)

### Arquivo:
```
backend/agents/agente_nicho.py
```

### O que faz:
- Gera `NichoBriefing` via LLM
- Define: público-alvo, diferencial, tom, keywords
- 1 call LLM/lead (Sonnet)

### Status: ✅ ATIVO

### Com LLM:
```
[6] AGENTE NICHO (Sonnet)
    └─ ~5% do custo LLM
```

### Subnicho Templates (8 mapeados):
| Subnicho | Template |
|----------|----------|
| nutricionista_esportiva | organic |
| nutricionista_clinica | editorial |
| clinica_estetica | minimal |
| barbearia_premium | brutalist |
| academia_crossfit | brutalist |
| restaurante_familiar | organic |
| advocacia_trabalhista | corporate |
| default | corporate |

---

## FASE 7: AGENTE VARIAÇÃO (Estrutura Visual)

### Arquivo:
```
backend/agents/agente_variacao.py
```

### O que faz:
- Define ordem das seções
- Define template visual (hero, cards, etc)
- **Template determinístico** para 8 subnichos
- Fallback LLM (Haiku) se não mapeado

### Status: ✅ ATIVO

### Com/Sem LLM:
```
[7] AGENTE VARIAÇÃO
    ├─ 8 subnichos → TEMPLATE (determinístico)
    └─ demais → LLM Haiku (fallback)
```

---

## FASE 8: ARQUITETO MESTRE (DesignerPRD)

### Arquivo:
```
backend/services/pipeline_fases/fase_08_arquiteto.py
```

### O que faz:
- Orquestrador: 1 call própria
- Delega para:
  - `bloco_estrutura` (2 calls)
  - `bloco_copy` (4 calls)
- Total: ~7 calls LLM/lead

### Status: ✅ ATIVO

### Com LLM:
```
[8] ARQUITETO MESTRE (Sonnet)
    ├─ Orquestrador: 1 call
    ├─ Bloco Estrutura: 2 calls
    └─ Bloco Copy: 4 calls
    Total: ~7 calls/lead (~20% custo LLM)
```

### Arquivos relacionados:
```
backend/agents/bloco_estrutura.py
backend/agents/bloco_copy.py
backend/agents/site_prompt_agent.py
```

---

## FASE 9: BUILDER RENDERER (Geração do Site)

### Arquivo Principal:
```
backend/services/builder_worker.py
```

### Engines disponíveis:

#### 1. OpenUI (PADRÃO)
```
backend/services/openui_renderer.py
```

**Fluxo:**
```
builder_worker.py
    ↓
openui_renderer.py
    ├─ Compose system prompt (7 contratos)
    ├─ Call LLM (Sonnet → Opus fallback)
    ├─ Extract HTML
    ├─ Apply 46 patches
    └─ Return OpenUIRenderResult
```

#### 2. Vite/React (LEGADO)
```
backend/services/vite_react_renderer.py
```

**Status: ⚠️ BLOQUEADO**
- Só roda via `FRALIB_BUILDER_ENGINE=vite_react`
- 14 arquivos em desuso

#### 3. Templates (NOVO)
```
backend/services/template_loader.py
```

**Fluxo:**
```
builder_worker.py (FRALIB_USE_TEMPLATES=1)
    ↓
template_loader.py
    ├─ generate_variation()
    ├─ load_template()
    └─ render_with_variation()
    Zero LLM, zero custo!
```

### Status: ✅ ATIVO

### Custo LLM:
```
[9] BUILDER RENDERER (OpenUI)
    └─ ~70% do custo LLM total
```

---

## FASE 9b: QUALITY GATE (Validação)

### Arquivo:
```
backend/agents/html_quality_gate.py
```

### O que valida:

| Verificação | O que bloqueia |
|-------------|----------------|
| Contract | PRD sem seções estruturadas |
| Emoji | HTML com emoji visível |
| Placeholder | Placeholder visual |
| Mídia mínima | Menos imagens do que mínimo |
| Endereço | Endereço real não aparece |
| E-mail | E-mail não confirmado |
| Dados falsos | Dados fake inventados |
| Motion | Animação faltando quando exigida |
| Hero | Hero sem mídia/CTA/H1 |
| Footer | Footer ausente |

### Loop de Retry:
```
Tentativa 1 (Sonnet) → Falha → 
Tentativa 2 (Sonnet) → Falha →
Tentativa 3 (Opus) → Falha → BLOQUEIA
```

### Status: ✅ ATIVO

### Sem LLM (determinístico):
```
[9b] QUALITY GATE (regex + lxml)
    └─ 38 funções de validação
```

---

## FASE 10: DEPLOY (Publicação)

### Arquivos:
```
backend/endpoints/pipeline_phase_helpers.py
scripts/post-receive
```

### Fluxo:
```
Pipeline completa → Verifica lock →
Copia HTML para /var/www/fralib/sites/<tenant>/<slug> →
Gera sitemap.xml + robots.txt →
Hook git post-receive
```

### Deploy steps:
1. `git push origin master`
2. Hook `scripts/post-receive` na VPS
3. Valida artefato
4. Copia para diretório público
5. Reinicia serviços (systemd)

### Status: ✅ ATIVO

### Sem LLM:
```
[10] DEPLOY (determinístico)
    └─ Cópia de arquivos + reinício
```

---

## FASE 11: FRANZ (SDR WhatsApp)

### Arquivo:
```
backend/agents/sdr_langgraph/agent.py
```

### O que faz:
- FSM LangGraph para conversa WhatsApp
- 2 calls LLM/turno (Sonnet)
- Aprendizado via feedback
- Integração whatsmeow (porta 3001)

### Status: ✅ ATIVO

### Com LLM:
```
[11] FRANZ (Sonnet)
    └─ ~5% do custo LLM
    └─ Auto-melhoria: learning.py + quality_judge.py
```

### Memória:
```
backend/agents/sdr_langgraph/learning.py
backend/agents/sdr_langgraph/quality_judge.py
backend/memory/u1/franz_lead_*.json
```

---

## 📊 MAPA DE CUSTO LLM

```
Custo total por site gerado (100%):

[3] JINA          ████░░░░░░  ~5%
[6] AGENTE NICHO  █████░░░░░  ~5%
[8] ARQUITETO     ████████████░░░░░░░░░░░░░  ~20%
[9] BUILDER       ████████████████████████████████████████░░░░░░  ~70%
[11] FRANZ        ████░░░░░░  ~5%
```

---

## 🔌 SERVIÇOS EXTERNOS

| Serviço | Porta | Arquivo |
|---------|-------|---------|
| API FraLib | 8000 | server.py |
| WhatsApp | 3001 | whatsmeow (systemd) |
| PostgreSQL | 5433 | job_queue.py |

### Systemd Services:
```
fralib-api          (1G RAM, 150% CPU)
fralib-worker       (2G RAM, 200% CPU)
fralib-franz        (512M RAM, 100% CPU)
fralib-wpp-listener (512M RAM, 100% CPU)
fralib-hermes       (256M RAM, 50% CPU)
```

---

## 🗄️ BANCO DE DADOS (PostgreSQL)

### Tabelas canônicas:
```
public.jobs              - Fila de jobs
lead_inventory           - Reserva de leads
pipeline_failures       - Jobs esgotados
pipeline_state          - Lock lógico por tenant
```

### Conexão:
```python
DATABASE_URL=postgresql://localhost:5433/fralib_db
client_encoding=UTF8  # IMPORTANTE: não usar LATIN1
```

---

## 📁 ARQUIVOS DO PIPELINE

### Estrutura:
```
C:\fralib\
├── backend/
│   ├── services/
│   │   ├── pipeline_phases.py          # Enum das 11 fases
│   │   ├── pipeline_executors.py       # Execução
│   │   ├── builder_worker.py           # Orquestrador builder
│   │   ├── openui_renderer.py         # GERADOR PADRÃO
│   │   └── ...
│   ├── agents/
│   │   ├── caio.py                    # Qualificação
│   │   ├── agente_nicho.py           # Briefing
│   │   ├── agente_variacao.py         # Variação
│   │   ├── arquiteto_mestre.py        # DesignerPRD
│   │   ├── html_quality_gate.py      # Validação
│   │   └── sdr_langgraph/            # Franz
│   ├── endpoints/
│   │   ├── pipeline_orchestrator_service.py
│   │   └── ...
│   └── core/
│       └── job_queue.py              # Fila PostgreSQL
├── scripts/
│   ├── pipeline_smoke.py              # Diagnóstico
│   ├── post-receive                   # Deploy hook
│   └── ...
├── tests/
│   ├── test_regression_patches.py    # 46 patches
│   └── ...
└── pipeline.py                         # CLI
```

---

## 🚨 PROBLEMAS DO PIPELINE

### 1. Cache Global sem Tenant (CRÍTICO)
- `keyword_cache` - global
- `jina_cache` - global
- `design_director_cache` - global
- `unsplash_cache` - global
- `pexels_cache` - global
- `prd_cache` - global

**Impacto**: Leads diferentes podem ver dados de outros.

### 2. Motor Vite Legado
- 14 arquivos sem uso
- 6 testes órfãos
- 2 scripts órfãos

**Impacto**: Manutenção desnecessária.

### 3. Dívida de UI
- `dashboard.html` vs `admin.html`
- Redirecionamentos incompletos

**Impacto**: Confusão para usuários.

---

## ✅ CHECKLIST DE AUDITORIA

### Antes de cada deploy:

```bash
# 1. Smoke test (sem LLM)
python pipeline.py smoke --dry-run

# 2. Teste de regressão
pytest tests/test_regression_patches.py

# 3. Verificar lock
python scripts/check_uncommitted.sh
```

### Métricas a monitorar:

| Métrica | Meta |
|---------|------|
| Tempo médio render | < 30s |
| Taxa de sucesso quality gate | > 90% |
| Custo LLM/site | < $0.05 |
| Testes verdes | 100% |

---

## 🎯 CONCLUSÃO

### Pipeline CANÔNICA (11 fases):
1. ✅ HUNTER (determinístico)
2. ✅ CAIO (determinístico)
3. ✅ JINA (LLM ~5%)
4. ✅ INTELIGÊNCIA (determinístico)
5. ✅ FOTOS (APIs)
6. ✅ AGENTE NICHO (LLM ~5%)
7. ✅ AGENTE VARIAÇÃO (template/LLM)
8. ✅ ARQUITETO MESTRE (LLM ~20%)
9. ✅ **BUILDER RENDERER** (LLM ~70%) ← MOTOR PRINCIPAL
10. ✅ QUALITY GATE (determinístico)
11. ✅ DEPLOY (determinístico)
12. ✅ FRANZ (LLM ~5%)

### Motor de Geração:
- **PADRÃO**: OpenUI (HTML estático, ~70% custo LLM)
- **NOVO**: Templates (determinístico, $0 custo)
- **LEGADO**: Vite/React (bloqueado, 14 arquivos)

### Ação imediata:
1. Manter OpenUI funcionando
2. Considerar Templates para custo zero
3. Avaliar remoção de arquivos Vite órfãos
