# Restore Pipeline — Commit a9030deb (22 Junho 2026 ~18:22)

## O que foi restaurado e por quê

Em 22 de junho de 2026, às ~18:22, a pipeline do FraLib estava funcional.
Após meses de mudanças, a pipeline atual não gera sites conforme o motor
OpenUI de junho. Este documento registra exatamente o que foi restaurado
para não regredir novamente.

## Commit de referência

```
a9030deb26b4325c87b0cd3acb00ea667f6bdf56
Data: 2026-06-22 17:39:55 -0300
Mensagem: feat(openui): system prompt expandido para 12 sistemas de motion
```

## Fluxo da pipeline (11 fases)

```
FASE 1  HUNTER           → Hunter captura leads no Google Maps
FASE 2  CURADORIA/CAIO   → Qualifica lead (score, tier, paleta)
FASE 3  JINA             → Pesquisa de mercado Jina AI
FASE 4  INTELIGENCIA     → Análise de concorrência
FASE 5  FOTOS            → Download de fotos
FASE 6  NICHO            → Análise de nicho
FASE 7  VARIACAO         → Variação estrutural
FASE 8  ARQUITETO        → Gera DesignerPRD via LLM
FASE 9  BUILDER          → Gera HTML completo via OpenUI
FASE 10 DEPLOY           → Publica site
FASE 11 FRANZ            → SDR outreach (WhatsApp)
```

## Arquivos RESTAURADOS (não remover!)

### Críticos (orquestração)
- `backend/services/pipeline_executors.py` — Orquestrador das 11 fases + retry
- `backend/services/pipeline_phases.py` — Constantes + FraLibState (15+ campos)
- `backend/services/pipeline_state.py` — Gerenciamento de estado da pipeline
- `backend/services/openui_renderer.py` — Motor OpenUI que gera HTML completo
- `backend/services/openui_contracts.py` — Contratos SEO/LGPD/motion injetados no prompt

### Agentes principais
- `backend/agents/jina_research.py` — Pesquisa de mercado Jina AI (Fase 3)
- `backend/agents/arquiteto_mestre.py` — Gera DesignerPRD via LLM (Fase 8)
- `backend/agents/caio.py` — Qualifica lead (score, tier, paleta)
- `backend/agents/designer_prd.py` — Schema + validação do PRD
- `backend/agents/design_context.py` — Contexto de design por segmento
- `backend/agents/design_director.py` — Diretor de design
- `backend/agents/component_library.py` — Biblioteca de componentes
- `backend/agents/craft_rules.py` — Regras de craftsmanship
- `backend/agents/color_enforcer.py` — Validação de cores
- `backend/agents/color_extractor.py` — Extração de cores
- `backend/agents/animation_injector.py` — Injeção de animações
- `backend/agents/hero_styles.py` — Estilos de hero por nicho
- `backend/agents/visual_archetypes.py` — Arquétipos visuais
- `backend/agents/visual_contract.py` — Contrato visual
- `backend/agents/visual_contract_gate.py` — Gate de contrato visual

### Validadores HTML
- `backend/agents/html_builder_repair.py` — Reparo automático de HTML
- `backend/agents/html_content_validator.py` — Validação de conteúdo
- `backend/agents/html_contract_validator.py` — Validação de contratos
- `backend/agents/html_media_validator.py` — Validação de mídia
- `backend/agents/html_phase6_repair.py` — Reparo fase 6
- `backend/agents/html_publication_helpers.py` — Helpers de publicação
- `backend/agents/html_quality_gate.py` — Quality gate HTML

### Outros agentes
- `backend/agents/lgpd_personalized.py` — LGPD personalizado por site
- `backend/agents/seo_context.py` — Contexto SEO por nicho
- `backend/agents/markdown_prd_parser.py` — Parser de PRD markdown
- `backend/agents/pipeline_checkpoint.py` — Checkpoints de pipeline
- `backend/agents/pipeline_identity.py` — Identidade do pipeline
- `backend/agents/pipeline_learning.py` — Aprendizado da pipeline
- `backend/agents/requirements_contract.py` — Contrato de requisitos
- `backend/agents/site_build_plan.py` — Plano de build do site
- `backend/agents/site_prompt_agent.py` — Prompt do site
- `backend/agents/site_skill_pack.py` — Skill pack do site
- `backend/agents/unsplash_fetcher.py` — Fetcher de fotos Unsplash
- `backend/agents/pexels_video.py` — Fetcher de vídeos Pexels
- `backend/agents/bloco_copy.py` — Bloco de copy do Arquiteto
- `backend/agents/bloco_estrutura.py` — Bloco de estrutura do Arquiteto
- `backend/agents/prompts_arquiteto.py` — Prompts do Arquiteto
- `backend/agents/agente_nicho.py` — Agente de nicho
- `backend/agents/agente_variacao.py` — Agente de variação
- `backend/agents/sub_nicho.py` — Sub-nicho
- `backend/agents/niche_resolver.py` — Resolvedor de nicho
- `backend/agents/nicho_data.py` — Dados de nicho
- `backend/agents/few_shot_examples.py` — Exemplos few-shot
- `backend/agents/keyword_research.py` — Pesquisa de keywords
- `backend/agents/validador.py` — Validador genérico
- `backend/agents/validation_enforcer.py` — Enforcement de validação
- `backend/agents/validation_layer.py` — Camada de validação
- `backend/agents/section_editor.py` — Editor de seções
- `backend/agents/skill_loader.py` — Loader de skills
- `backend/agents/trend_watcher.py` — Watcher de trends
- `backend/agents/handoff_types.py` — Tipos de handoff
- `backend/agents/token_tracker.py` — Tracker de tokens
- `backend/agents/memory.py` — Memória JSON por tenant
- `backend/agents/agent_rag.py` — RAG de agentes
- `backend/agents/builder_contract_utils.py` — Utilitários de contrato builder

### Serviços
- `backend/services/pipeline_renderer_support.py` — Suporte ao renderer
- `backend/services/pipeline_sdr_delivery.py` — Entrega SDR
- `backend/services/pipeline_prd_builder.py` — Builder de PRD
- `backend/services/pipeline_prompt_agent.py` — Prompt do agente
- `backend/services/pipeline_validators.py` — Validadores
- `backend/services/pipeline_media.py` — Mídia
- `backend/services/pipeline_phase_tracking.py` — Tracking de fases
- `backend/services/pipeline_builders.py` — Builders
- `backend/services/pipeline_cache_control.py` — Cache
- `backend/services/pipeline_flow_config.py` — Config de fluxo
- `backend/services/site_health_check.py` — Health check
- `backend/services/sdr_gateway.py` — Gateway SDR
- `backend/services/sdr_settings.py` — Settings SDR
- `backend/services/lead_supply_engine.py` — Motor de supply de leads
- `backend/services/hunter_provider.py` — Provider Hunter
- `backend/services/lead_providers.py` — Providers de lead
- `backend/services/maps_provider.py` — Provider Google Maps
- `backend/services/lead_supply_events.py` — Eventos de supply
- `backend/services/lead_supply_filters.py` — Filtros de supply
- `backend/services/lead_supply_inventory.py` — Inventário de leads
- `backend/services/lead_supply_storage.py` — Storage de leads
- `backend/services/builder_worker.py` — Worker builder
- `backend/services/motion_runtime.js` — Runtime de motion

### Utils
- `backend/utils/jina_intelligence.py` — Inteligência Jina
- `backend/utils/agente1_hunter_v2.py` — Hunter v2
- `backend/utils/google_local_scraper.py` — Scraper Google Local
- `backend/utils/google_scraper_core.py` — Core scraper
- `backend/utils/validation_layer.py` — Camada de validação
- `backend/utils/schema_builder.py` — Builder de schema
- `backend/utils/secrets_crypto.py` — Criptografia
- `backend/utils/espionar_concorrencia.py` — Espionagem de concorrência
- `backend/utils/safe_lead_qualificado.py` — Lead qualificado seguro

### Diretórios de conhecimento
- `backend/agents/rag_knowledge/` — RAG knowledge base
- `backend/agents/skill_packs/` — Skill packs (design-motion, impeccable, etc)
- `backend/agents/bryan_knowledge/` — Knowledge base Bryan
- `backend/agents/segment_knowledge/` — Knowledge por segmento
- `backend/agents/sdr_langgraph/` — SDR com FSM + Orchestrator
- `backend/services/lead_supply_providers/` — Providers de lead
- `backend/services/pipeline_fases/` — Fases da pipeline

## Como executar a pipeline

### Via worker (automático)
```bash
# Worker consome jobs da fila PostgreSQL
docker compose -f docker-compose.prod.yml up -d worker

# Disparar pipeline para um lead
curl -X POST http://localhost:8000/api/pipeline/reprocessar/{lead_id} \
  -H "Authorization: Bearer {token}"
```

### Via endpoint direto
```bash
# Pipeline SSE (stream de progresso)
curl -N -H "Authorization: Bearer {token}" \
  "http://localhost:8000/api/pipeline/executar?tenant_id=2&lead_id={lead_id}"
```

### Via script Python
```python
from backend.services.pipeline_executors import executar_pipeline_completa
from backend.services.pipeline_state import FraLibState

state = FraLibState(
    tenant_id=2,
    lead_id="123",
    segmento="academia",
    cidade="Curitiba",
)
resultado = executar_pipeline_completa(state)
```

## Variáveis de ambiente necessárias

```env
# LLM Providers
ANTHROPIC_BASE_URL=https://api.kpalabz.com/v1
ANTHROPIC_API_KEY=sk-...
GOOGLE_API_KEY=...

# Banco
DATABASE_URL=postgresql://fralib_user:password@localhost:15434/fralib_db

# Redis
REDIS_URL=redis://localhost:16379/0

# Sites
FRALIB_SITES_DIR=/var/www/fralib/sites
FRALIB_SITES_ROOT=/var/www/fralib/sites
FRALIB_BUILDER_SANDBOX_ROOT=/tmp/fralib_builder
FRALIB_BUILDER_MANIFEST_DIR=/app/logs/builder_manifests
```

## O que NÃO deve ser alterado sem documentar

1. **NÃO remover** `backend/services/pipeline_executors.py` — é o orquestrador
2. **NÃO remover** `backend/services/pipeline_phases.py` — define as 11 fases
3. **NÃO remover** `backend/services/openui_renderer.py` — motor OpenUI
4. **NÃO remover** `backend/agents/jina_research.py` — pesquisa de mercado
5. **NÃO simplificar** `FraLibState` — tem 15+ campos por propósito
6. **NÃO substituir** `pipeline_executors.py` por steps simplificados

## Backup

Backup do estado anterior ao restore: `/tmp/fralib-backup-antes-restore.tar.gz`
Commit de referência: `a9030deb` (22 junho 2026)
Data do restore: 2026-08-05
