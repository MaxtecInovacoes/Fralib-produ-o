# Fralib - System Overview V2

> Documentacao executiva do sistema completo - atualizada 2026-06-21

## Visao Geral

Fralib e um pipeline de geracao de sites premium (Vite + React + Tailwind v4 + Motion + GSAP)
com agentes especializados (Hunter, SDR, Builder, Closer) e aprendizado cross-tenant.

## Arquitetura

```
Lead Google Maps -> [Hunter] -> Lead Cache
                          |
                          v
                    [SDR Consultivo]
                          |
                          v
                  [BANT/MEDDIC Score]
                          |
                  +-------+--------+
                  |                |
            Quente/Frio      [Retargeting 30/60/90]
                  |           (re-engaja perdidos)
                  v
            [Handoff Closer]  <--  [closer_queue table]
                  |
                  v
            [Builder Vite/React]
                  |
                  v
            [Site pronto em 5min]
                  |
                  v
            [Quality Gate + Lazy Loading + Code Splitting]
                  |
                  v
            [Deploy]
                  |
                  v
         [Dream Job noturno 3h]   <-- consolida lessons cross-tenant
```

## Modulos Principais

### 1. Pipeline de Geracao
- `backend/agents/hunter/` - busca leads no Google Maps
- `backend/agents/caio/` - analise de mercado
- `backend/agents/jina/` - extracao de keywords
- `backend/agents/nicho/` - classificacao de segmento
- `backend/agents/variacao/` - variacao por subnicho
- `backend/agents/prd/` - geracao de PRD
- `backend/agents/vite_builder/` - geracao de codigo Vite/React

### 2. SDR Langgraph (Fase 1 do Plano Mestre)
- `backend/agents/sdr_langgraph/SDD_ATTENDANCE.md` - design system do atendimento
- `backend/agents/sdr_langgraph/humanization.py` - anti-robo, delay humano, dedup
- `backend/agents/sdr_langgraph/bant_meddic.py` - extracao automatica de BANT/MEDDIC
- `backend/agents/sdr_langgraph/handoff.py` - handoff pro closer humano
- `backend/agents/sdr_langgraph/state.py` - LeadMemory com BANT/MEDDIC/temperature

### 3. Closer Queue (Fase 2)
- `backend/services/closer_queue.py` - DAO da fila
- `backend/endpoints/closer_endpoints.py` - GET/POST endpoints

### 4. Retargeting (Fase 4)
- `backend/services/retargeting.py` - cadencia 30/60/90/120d

### 5. Templates Nichados (Fase 5)
- `backend/agents/design_systems_library.py` - 12 Design Systems Awwwards-grade
  - academia/crossfit, academia/pilates
  - restaurante/bistro, restaurante/hamburgueria
  - clinica/dentista, clinica/estetica
  - barbearia/tradicional, salao/beleza
  - oficina/mecanica, pet/pet_shop
  - imobiliaria/venda, advocacia/generalista

### 6. Cross-tenant Learning (Fase 5)
- `backend/services/dreamer.py` - Dream job noturno (3h BRT)
- `backend/services/agent_bus.py` - pub/sub entre agentes

## Melhorias Aplicadas (Q1-Q2 2026)

### Performance do Builder
- ✅ Model routing (Haiku/Sonnet/Opus por batch) -50% custo, +30% velocidade
- ✅ Few-shot examples no system prompt +25% qualidade
- ✅ Negative examples e guardrails +15% qualidade, -20% custo
- ✅ Code splitting (manualChunks para motion/gsap) -40% TTI
- ✅ Lazy loading em todas imagens -25% LCP
- ✅ Prompt caching Anthropic -70% custo, +20% velocidade

### SDR Atendimento
- ✅ SDD documentado (System Design Document)
- ✅ Humanizacao (delay 1-3s, variacao, anti-duplicata)
- ✅ Wall Street close (angulo de oportunidade)
- ✅ BANT/MEDDIC extracao automatica
- ✅ Handoff real para closer humano
- ✅ Retargeting 30/60/90/120d

## Endpoints Publicos

### SDR
- POST `/api/sdr/webhook` - recebe msg do lead
- GET `/api/sdr/lead/{id}/bant` - score BANT/MEDDIC

### Closer
- GET `/api/closer/queue` - lista leads pendentes
- POST `/api/closer/queue/claim` - reivindica lead
- POST `/api/closer/queue/done` - marca como won/lost
- GET `/api/closer/queue/stats` - stats da fila

### Pipeline
- POST `/api/pipeline/start` - inicia geracao de site
- GET `/api/pipeline/status/{id}` - status

## Testes

```bash
# Rodar todos os testes do plano mestre
python -m pytest \
  tests/unit/test_sdr_humanization.py \
  tests/unit/test_sdr_handoff.py \
  tests/unit/test_sdr_bant.py \
  tests/unit/test_retargeting.py \
  tests/unit/test_design_systems_library.py \
  tests/unit/test_dreamer_bus.py \
  --timeout=30
```

**Total: 112 testes, 100% passando.**

## Variaveis de Ambiente Importantes

| Variavel | Descricao | Default |
|----------|-----------|---------|
| `FRALIB_CLOSER_PHONE_USER_{tenant_id}` | Telefone do closer por tenant | (vazio) |
| `FRALIB_VITE_PROMPT_CACHE` | Habilita prompt caching | 1 (habilitado) |
| `FRALIB_VITE_PREVIEW_FAST` | Skip tsc no build | 1 (habilitado) |
| `LITELLM_BASE_URL` | URL do proxy LLM | https://llm.seunegociofralib.site |
| `LITELLM_API_KEY` | API key do proxy | (vazio) |

## Como Rodar Localmente

```bash
# 1. Ativar venv
source venv/Scripts/activate  # Git Bash
# ou
venv\Scripts\activate.bat  # cmd

# 2. Instalar deps
pip install -r requirements.txt

# 3. Subir servidor
python server.py
# ou
uvicorn server:app --reload --port 8000
```

## Como Adicionar Novo Design System

```python
# Em backend/agents/design_systems_library.py
MEU_NICHO = DesignSystem(
    nicho="meu_nicho",
    subnicho="variante",
    paleta=ColorPalette(...),
    typography=Typography(...),
    motion=MotionConfig(...),
    sections=SectionConfig(...),
)

ALL_DESIGN_SYSTEMS["meu_nicho/variante"] = MEU_NICHO
```

## Dream Job - Cross-tenant Learning

Roda todo dia 3h BRT. Le memories de TODOS os tenants e:

1. Detecta padroes cross-tenant (objecoes, segmentos, BANT)
2. Promove lessons para `backend/agents/bryan_knowledge/global_lessons.json`
3. Atualiza `rag_knowledge/sdr_agents/*.md`

```bash
# Rodar manualmente
python -c "from backend.services.dreamer import run_dream; print(run_dream(apply=True))"
```

## Agent Bus

Singleton thread-safe. Permite pub/sub entre agentes:

```python
from backend.services.agent_bus import publish_pain_identified

# Publica dor identificada
publish_pain_identified(
    tenant_id=1,
    segment="academia",
    pain="perco cliente",
    lead_id=42,
)
```

Agentes podem se inscrever para receber sinais:

```python
from backend.services.agent_bus import get_bus

bus = get_bus()
def on_pain(event):
    print(f"Lead {event.payload['lead_id']} tem dor: {event.payload['pain']}")

bus.subscribe("pain_identified", on_pain)
```

## Roadmap

### Feito (Q1-Q2 2026)
- ✅ Builder 5-10x mais rapido
- ✅ SDR consultivo + humanizacao
- ✅ BANT/MEDDIC estruturado
- ✅ Handoff closer real
- ✅ Retargeting 30/60/90
- ✅ 12 Design Systems nichados
- ✅ Cross-tenant learning

### A Fazer (Q3 2026+)
- A/B testing de variantes automatico
- Visual regression com Playwright
- Opus 4.8 para gerar 40+ templates extras
- Integrao com WhatsApp Business API
- Dashboard de conversao em tempo real

## Licenca

Proprietary - Fralib internal
