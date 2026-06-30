# MAPA COMPLETO DE ARQUIVOS - FRAUB
## Versão: Auditoria Independente 2026-06

---

## 🔴 MOTOR DE GERAÇÃO (FASE 9)

### PADRÃO: Vite/React
```
backend/services/
├── vite_react_renderer.py      ⭐ ORQUESTRADOR PRINCIPAL (4,800+ linhas)
├── vite_config.py              Configurações
├── vite_prompts.py             Prompts do sistema
├── vite_facts.py               Extração de facts
├── vite_file_extractor.py      Extração de arquivos TSX
├── vite_validator.py           Validação do projeto
├── vite_build_executor.py      Execução do build
├── vite_modules.py             Definições de módulos
├── vite_renderer_models.py      Modelos de dados
├── vite_config_helpers.py      Helpers de config
├── vite_block_registry.py      Registry de blocos
├── vite_theme_guard.py         Guard de tema
├── vite_templates.py           Templates
├── vite_visual_lanes.py        Lanes visuais
└── vite_prompts.py             Prompts
```

### FALLBACK: OpenUI
```
backend/services/
├── openui_renderer.py          ⭐ FALLBACK (não padrão!)
├── openui_contracts.py        Contratos do sistema
└── template_loader.py          🆕 Alternativa ZERO-LLM
```

### ORQUESTRADOR DO BUILDER
```
backend/services/
└── builder_worker.py          ⭐ COORDENA TODA A GERAÇÃO
```

---

## 🟢 PIPELINE 11 FASES

### ORQUESTRADORES
```
backend/
├── endpoints/
│   └── pipeline_orchestrator_service.py  ⭐ ORQUESTRADOR PRINCIPAL
│
├── services/
│   ├── pipeline_execution_core.py         Execução core
│   ├── pipeline_phase_helpers.py          Helpers de fase
│   ├── pipeline_executors.py              Executores de fase
│   └── pipeline_phases.py                 Constantes e state
```

### FASES DO PIPELINE

| Fase | Nome | Arquivo Principal | LLM? |
|-------|------|-------------------|------|
| 1 | HUNTER | `utils/agente1_hunter_v2.py` | ❌ |
| 2 | CAIO | `agents/caio.py` | ✅ Haiku |
| 3 | JINA | `agents/jina_research.py` | ✅ Haiku |
| 4 | INTELIGÊNCIA | `endpoints/pipeline_lead_flow_helpers.py` | ❌ |
| 5 | FOTOS | `agents/unsplash_fetcher.py` | ❌ |
| 6 | NICHO | `agents/agente_nicho.py` | ✅ Sonnet |
| 7 | VARIAÇÃO | `agents/agente_variacao.py` | ❌ (determinístico) |
| 8 | ARQUITETO | `agents/arquiteto_mestre.py` | ✅ Sonnet |
| 9 | BUILDER | `services/vite_react_renderer.py` | ❌ (padrão: none) |
| 10 | DEPLOY | `scripts/post-receive` | ❌ |
| 11 | FRANZ | `agents/sdr_langgraph/agent.py` | ✅ Sonnet |

---

## 🟡 QUALITY GATE

```
backend/agents/
├── html_quality_gate.py         ⭐ VALIDAÇÃO PRINCIPAL
├── html_contract_validator.py    Contratos
├── html_media_validator.py       Mídia
├── html_content_validator.py     Conteúdo
├── html_phase6_repair.py        Reparos
└── html_builder_repair.py        Reparos
```

---

## 🔵 SISTEMA DE VARIAÇÃO

```
backend/services/
├── variation_seed.py             ⭐ GERAÇÃO DETERMINÍSTICA
├── archetype_resolver.py          RESOLUÇÃO DE ARCHETYPE
├── studio_archetypes.json        6 ARCHETYPES VISUAIS
└── vite_theme_guard.py          GUARD DE TEMA

backend/agents/
└── agente_variacao.py           FASE 7 - GERA VARIAÇÃO
```

### 4 Eixos de Variação:
- `hero_layout`: split | center | asymmetric | fullbleed | video
- `motion_style`: sharp | smooth | minimal
- `copy_voice`: aggressive | friendly | authoritative
- `color_emphasis`: primary_dominant | secondary_dominant | balanced

### 6 Archetypes:
- BOLD_ENERGY (academia, fitness)
- WARM_LOCAL (barbearia, salao)
- ZEN_PURE (clinica, estetica)
- LUXURY_ELITE (restaurante, pizzaria)
- MODERN_TECH (energia solar)
- PROFESSIONAL_TRUST (advocacia)

---

## 🟣 CORE

```
backend/core/
├── database.py                  ⭐ BANCO DE DADOS
├── job_queue.py                 ⭐ FILA DE JOBS
├── config.py                   Config
├── auth.py                     Auth
├── jwt_config.py               JWT
├── rate_limiter.py             Rate limit
└── retry_helper.py             Retry
```

---

## ⚪ ENDPOINTS

```
backend/endpoints/
├── pipeline_*.py               50+ arquivos de pipeline
├── leads_*.py                  Gestão de leads
├── whatsapp_*.py                Integração WhatsApp
├── health_*.py                 Health checks
├── metrics_*.py                Métricas
├── auth_*.py                   Auth
├── admin_*.py                  Admin
├── cron_*.py                   Cron jobs
└── ... (mais 30+ arquivos)
```

---

## 💜 AGENTS

```
backend/agents/
├── caio.py                     ⭐ Qualificação
├── agente_nicho.py             Briefing
├── agente_variacao.py          Variação
├── arquiteto_mestre.py        DesignerPRD
├── html_quality_gate.py        Validação
├── jina_research.py           Pesquisa
├── unsplash_fetcher.py         Fotos
├── pexels_video.py            Vídeos
├── pipeline_checkpoint.py       Checkpoints
├── pipeline_identity.py        Identidade
├── pipeline_learning.py        Aprendizado
├── designer_prd.py             PRD
├── design_director.py          Design
├── site_prompt_agent.py       Prompt
├── llm_*.py                   10+ arquivos LLM
├── sdr_langgraph/             Franz (SDR WhatsApp)
│   ├── agent.py
│   ├── orchestrator.py
│   ├── state_machine.py
│   ├── quality_judge.py
│   ├── learning.py
│   └── ... (20+ arquivos)
└── ... (mais 50+ arquivos)
```

---

## 🟠 SCRIPTS

```
scripts/
├── post-receive                ⭐ DEPLOY HOOK
├── pipeline_smoke.py          Diagnóstico
├── controlled_pipeline_run.py  Execução controlada
├── pipeline_harness.py         Testes de pipeline
├── audit_published_sites.py   Auditoria
├── vps_sync_deploy_hook.py    Sync deploy
├── generate_system_file_catalog.py
└── ... (mais 20+ arquivos)
```

---

## 🔴 ARQUIVOS IMPORTANTES

```
RAIZ/
├── CLAUDE.md                   ⭐ ÍNDICE DE ENTRADA
├── AGENTS.md                  ⭐ FONTE CANÔNICA
├── server.py                  API server
├── worker.py                  Worker
├── pipeline.py                CLI de pipeline
├── Makefile                   Comandos
├── config.py                 Config
└── observability.py           Observabilidade
```

---

## 📊 ESTATÍSTICAS

| Categoria | Qtd Arquivos |
|-----------|--------------|
| backend/services/ | ~80 |
| backend/agents/ | ~100+ |
| backend/endpoints/ | ~60 |
| backend/core/ | ~15 |
| scripts/ | ~30 |
| tests/ | ~50 |
| **TOTAL** | **~335** |

---

## ⚠️ ARQUIVOS SUSPEITOS (Verificar uso)

```
# Provavelmente LEGADO:
backend/services/vite_*     ⭐ SÃO O PADRÃO, não legado!
backend/services/openui_*    ⭐ FALLBACK

# Provavelmente NÃO USADO:
tests/unit/test_vite_*      Verificar se são executados
scripts/test_*.py           Verificar se são executados
```

---

## 🔧 DIAGNÓSTICO DE PROBLEMAS

### Sites saindo iguais?
1. Verificar: `docs/DIAGNOSTICO_VARIACAO_SITES.md`
2. Verificar logs de variação
3. Verificar manifest do builder

### Pipeline falhando?
1. Verificar: `python pipeline.py smoke --dry-run`
2. Verificar logs em `logs/`
3. Verificar fila em `jobs`

### LLM não respondendo?
1. Verificar `ANTHROPIC_API_KEY`
2. Verificar `FRALIB_BUILDER_ENGINE`
3. Verificar `FRALIB_VITE_LLM_POLICY`
