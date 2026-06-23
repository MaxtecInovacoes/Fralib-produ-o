# Pipeline Flow Canonical (junho/2026)

> **Última atualização**: 23/jun/2026 — commit `564a59b`
> **Propósito**: Documentar COMO a pipeline funciona HOJE, sem ambiguidade.
> Se o código mudar, atualizar este doc PRIMEIRO e o código DEPOIS.

---

## 1. Visão geral em 1 frase

Pipeline processa 1 lead do funil SDR → site publicado, em **11 fases sequenciais** com **~5 calls LLM/lead** (sendo **70% do custo no OpenUI**).

---

## 2. As 11 fases (em ordem)

| # | Fase | Módulo | Função | LLM? |
|---|---|---|---|---|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Scraping Google Maps/Maps | ❌ |
| 2 | Caio | `agents/caio.py` | Scorer determinístico de lead (0-100) | ❌ |
| 3 | Jina | `utils/jina_intelligence.py` | Análise web (concorrentes, reviews) | ✅ 1 call |
| 4 | SDR (Franz) | `agents/sdr_langgraph/` | Conversa WhatsApp + qualifica | ✅ 2 calls/turno |
| 5 | (entrada) | Hunter + Caio + Jina | Dados consolidados | — |
| 6 | **Nicho** | `agents/agente_nicho.py` | Briefing do nicho + subnicho | ✅ 1 call |
| 7 | **Variação** | `agents/agente_variacao.py` | Ordem de seções + template | ⚠️ 0 ou 1 call |
| 8 | **Arquiteto** | `agents/arquiteto_mestre.py` | Orquestra bloco_estrutura + bloco_copy | ✅ ~7 calls |
| 8a | bloco_estrutura | `agents/bloco_estrutura.py` | Gera estrutura/seções | ✅ 2 calls |
| 8b | bloco_copy | `agents/bloco_copy.py` | Gera copy (4 chamadas) | ✅ 4 calls |
| 8c | **site_prompt_agent** | `agents/site_prompt_agent.py` (re-export) + `prompt_agent_builder.py` + `prompt_agent_context.py` + `prompt_agent_helpers.py` | Monta `builder_prompt` (string única) | ❌ |
| 9 | **OpenUI** | `services/openui_renderer.py` | Renderiza HTML final | ✅ 1 call (Sonnet/Opus) |
| 9b | Quality Gate | `agents/html_quality_gate.py` | Valida contratos (38 checks) | ❌ |
| 9b | Builder Repair | `agents/html_builder_repair.py` | Repara HTML (13 patches) | ❌ |
| 10 | Deploy | `services/builder_worker.py` → publish | Publica em `/var/www/fralib/sites/<tenant>/<slug>/` | ❌ |

---

## 3. Fluxo do `builder_prompt` (input do OpenUI)

```
PRD (DesignerPRD)
    ↓
build_prompt_agent_payload(prd)  ← site_prompt_agent
    ├── _business_context    → nome, cidade, telefone, segmento
    ├── _qualification_context → score Caio, tier
    ├── _research_context    → Jina insights
    ├── _seo_context         → keywords primárias
    ├── _content_context     → copy do Arquiteto
    ├── _media_context       → imagens/vídeos
    ├── _design_context      → visual_dna, archetype
    ├── _publication_context → URL canônica, OG tags
    ├── _section_request     → ordem_das_secoes
    ├── resolve_niche_context → subnicho detectado
    ├── _visual_direction_contract → design system
    └── render_builder_prompt() → STRING ÚNICA
            ↓
    builder_prompt (~3-8KB natural language)
            ↓
    OpenUI (1 call Sonnet/Opus)
            ↓
    HTML final (landing page completa)
```

**Arquivos críticos** (em ordem de dependência):
- `backend/agents/prompt_agent_builder.py` (210L) — entry point
- `backend/agents/prompt_agent_context.py` (582L) — 13 builders
- `backend/agents/prompt_agent_helpers.py` (369L) — formatação
- `backend/agents/site_prompt_agent.py` (112L) — re-exporter

**Total**: 1161 linhas que montam a string pro OpenUI.

---

## 4. Calls LLM por lead (resumo)

| Call | Quem | Modelo | Custo ~USD |
|---|---|---|---|
| Jina | fase 3 | Sonnet | $0.01 |
| Nicho | fase 6 | Sonnet | $0.01 |
| Variação | fase 7 | (só fallback) | $0 ou $0.01 |
| bloco_estrutura | 8a | Sonnet | $0.03 |
| bloco_copy (4) | 8b | Sonnet | $0.05 |
| **OpenUI** | fase 9 | **Sonnet (Opus fallback)** | **$0.15** |
| SDR (Franz) | fase 4 | Sonnet (2/turno) | $0.02/turno |
| **Total/lead** | | | **~$0.25** |

**70% do custo = OpenUI.** Otimizar OpenUI = otimizar 70%.

---

## 5. Como verificar se está funcionando

```bash
# Smoke dry-run
python pipeline.py smoke --dry-run

# Validar pipeline (7 etapas, ~70s)
python scripts/validar_pipeline.py

# Apenas anti-regressão
python scripts/validar_pipeline.py --etapa 7

# Suite completa de testes
pytest tests/test_anti_regressao_estado.py -v
pytest tests/test_subnicho_templates.py -v
pytest tests/test_html_sanitizer.py -v
pytest tests/test_lgpd_injector.py -v
```

---

## 6. Arquivos que NÃO devem sumir (anti-regressão)

Ver `tests/test_anti_regressao_estado.py` (22 testes). Os críticos:

- `backend/services/openui_renderer.py` (único renderer)
- `backend/services/builder_worker.py` (entry point)
- `backend/services/html_sanitizer.py` (fecha h2 órfão)
- `backend/services/lgpd_injector.py` (LGPD com consent_key único)
- `backend/agents/agente_nicho.py` (briefing)
- `backend/agents/agente_variacao.py` (template + 8 subnichos)
- `backend/agents/arquiteto_mestre.py` (orquestrador)
- `backend/agents/bloco_estrutura.py` (estrutura LLM)
- `backend/agents/bloco_copy.py` (copy LLM)
- `backend/agents/site_prompt_agent.py` (monta prompt)
- `backend/agents/prompt_agent_builder.py` (entry real)
- `backend/agents/sdr_langgraph/agent.py` (Franz FSM)
- `backend/agents/html_quality_gate.py` (38 checks)
- `backend/agents/html_builder_repair.py` (13 repairs)

**Tag canônica**: `v1.0-baseline-2026-06-23`
