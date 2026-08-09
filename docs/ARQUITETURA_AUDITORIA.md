# Auditoria de Arquitetura — FraLib

**Data:** 2026-08-09
**Propósito:** SSOT (Single Source of Truth) — identificar monolitos, legados, duplicatas e conflitos.

## Categorias

| Código | Significado |
|--------|------------|
| **[ATIVA]** | Código em produção, importado pelo fluxo principal |
| **[LEGADO]** | Código morto, pastas `_arquivo`, `bak`, implementações antigas |
| **[DUPLICADO]** | Nome ou conteúdo já existe em outro lugar canônico |
| **[CONFLITO]** | Mesma função em dois lugares, ou mesma coisa de formas diferentes |

---

## Bloco 1 — `backend/agents/arquiteto/` (Arquiteto Mestre)

### Tabela de Arquivos

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `arquiteto_mestre.py` | 506 | **[ATIVA]** | Implementação dict-based do PRD. Usado pelo manager (FSM) e fase_08_arquiteto |
| `arquiteto_agent_loop.py` | 493 | **[ATIVA]** | Managed Agent Loop (tool_use iteration). Usado por pipeline_endpoints e leads_endpoints |
| `arquiteto_tools.py` | 358 | **[ATIVA]** | 8 ferramentas para o agent loop (keyword research, design system, animation, SEO, craft rules, etc.) |
| `prompts_arquiteto.py` | ~150 | **[ATIVA]** | System prompts (DesignDirector, CopySenior) + helpers (limpar_texto_review, selecionar_top_reviews, montar_brief_estruturado, clean_json) |
| `design_context.py` | 1142 | **[ATIVA]** | ORQUESTRADOR (não monólito). 50+ DIRECOES_VISUAIS (OKLch), 6 CRAFT_PROFILES, 16 NICHOS, 11 HERO_STYLES, 5 SUB_NICHOS. Funções: get_design_context(), get_design_context_prompt() |
| `design_system_selector.py` | ~399 | **[ATIVA]** | Seleciona design system por segmento. 16 CURATED_DESIGN_SYSTEMS, SEGMENT_DESIGN_MAP, CATEGORY_AFFINITY. Integração com FRALIB_DS_DIR |
| `bloco_estrutura.py` | 281 | **[ATIVA]** | Bloco 1 — Estrutura + Layout. LLM call (sonnet→haiku). 14 params. _force_academia_direction() + _fallback_instrucao_criativa() |
| `bloco_copy.py` | 439 | **[ATIVA]** | Bloco 2 — Copy por seção. LLM call com 4 níveis de fallback (sonnet→haiku→retry→determinístico). 19 params |
| `craft_rules.py` | 329 | **[ATIVA]** + **[DUPLICADO INTERNO]** | ANTI_SLOP + TYPOGRAPHY_RULES + COLOR_RULES + ANIMATION_RULES + AUTOCRITICA_TEMPLATE. **TYPOGRAPHY_HIERARCHY definido 2x (linhas 187-216 e 256-278). LAWS_OF_UX definido 2x (linhas 218-253 e 280-312).** |
| `visual_archetypes.py` | 39 | **[ATIVA]** | Mapeia visual_dna → archetype_id. Usado por visual_contract.py e site_build_plan.py |
| `markdown_prd_parser.py` | 220 | **[ATIVA]** | Parses markdown PRD output → dict estruturado. Usado por bloco_estrutura e bloco_copy |
| `sub_nicho.py` | 247 | **[ATIVA]** | Sub-nicho detection e context enrichment. Usado por bloco_estrutura |
| `design_director.py` | 345 | **[ATIVA]** | Orquestra design_context + craft_rules + sub_nicho para construir o creative brief |
| `seo_context.py` | 62 | **[ATIVA]** | SEO framework por nicho. 14 nichos com schema.org, H1, keywords, FAQ template |
| `handoff_types.py` | 74 | **[ATIVA]** | Pydantic: HandoffBase, NichoBriefing, VariacaoEstrutural, ValidacaoResultado |
| `requirements_contract.py` | 79 | **[ATIVA]** | Contrato factual determinístico (requirements_contract) |
| `visual_contract.py` | 106 | **[ATIVA]** | Contrato visual determinístico (visual_contract) — acceptance criteria, required sections, hero, footer |
| `site_build_plan.py` | 178 | **[ATIVA]** | Plano de build determinístico (site_build_plan) — IA, section_plan, style_guide, media_plan, SEO |
| `arquiteto/agent.py` | — | **[NÃO EXISTE]** | Violação do template padrão de agente. Código do arquiteto está espalhado em ~18 arquivos soltos na pasta backend/agents/ |
| `arquiteto/agent.py.bak.20260730_171314` | — | **[LEGADO]** | Backup do antigo agent.py (2026-07-30). Schema DesignerPRD antiga sem campos novos |
| `designer_prd.py` | 893 | **[CONFLITO]** | Self-identifica como LEGADO no header mas **ATIVAMENTE importado** pelo manager 3x (linhas 209, 384, 531) e por test_builder_prd_spec.py. Pydantic: DesignerPRD, ColorPalette, AnimationSpec, SectionSpec. field_validators. gerar_prd() + fallback |

### Análise de Imports (quem importa arquiteto)

| Importador | Importa | Linha |
|------------|---------|-------|
| `backend/agents/manager/agent.py` | `arquiteto_mestre.gerar_arquiteto_mestre_prd` | 208 |
| `backend/agents/manager/agent.py` | `designer_prd.DesignerPRD, ColorPalette, AnimationSpec, SectionSpec` | 209, 384, 531 |
| `backend/services/pipeline_fases/fase_08_arquiteto.py` | `arquiteto_mestre.gerar_arquiteto_mestre_prd` | 21 |
| `backend/endpoints/pipeline_endpoints.py` | `arquiteto_mestre.gerar_arquiteto_mestre_prd` | 61 |
| `backend/endpoints/pipeline_endpoints.py` | `arquiteto_agent_loop.gerar_arquiteto_mestre_prd_agent` | 65 |
| `backend/endpoints/leads_endpoints.py` | `arquiteto_mestre.gerar_arquiteto_mestre_prd` | 343 |
| `backend/endpoints/leads_endpoints.py` | `arquiteto_agent_loop.gerar_arquiteto_mestre_prd_agent` | 346 |
| `tests/unit/test_builder_prd_spec.py` | `designer_prd.DesignerPRD, ColorPalette, AnimationSpec, SectionSpec` | 23 |
| `backend/agents/design_director.py` | `design_context, sub_nicho, craft_rules` | — |
| `backend/agents/design_director.py` | `design_system_selector` | — |
| `backend/agents/design_system_selector.py` | `design_context.ALIASES` | 325-327 |
| `backend/agents/bloco_estrutura.py` | `llm_direct, markdown_prd_parser, prompts_arquiteto, visual_archetypes` | — |
| `backend/agents/bloco_copy.py` | `llm_direct, prompts_arquiteto, markdown_prd_parser` | — |
| `backend/agents/arquiteto_agent_loop.py` | `arquiteto_tools` | — |
| `backend/agents/arquiteto_tools.py` | `design_context, seo_context, design_system_selector, craft_rules, visual_archetypes` | — |

### Fonte da Verdade

| Conceito | Arquivo Canônico | Observação |
|----------|-----------------|------------|
| PRD generation (FSM) | `arquiteto_mestre.py` | Usado pelo manager |
| PRD generation (Agent Loop) | `arquiteto_agent_loop.py` | Usado por endpoints |
| Design tokens | `design_context.py` | ORQUESTRADOR — 50+ directions, 6 profiles |
| Craft rules | `craft_rules.py` | ⚠️ DUPLICADO INTERNO |
| Copy generation | `bloco_copy.py` | Novo sistema em blocos |
| Estrutura/layout | `bloco_estrutura.py` | Novo sistema em blocos |
| SEO framework | `seo_context.py` | 14 nichos mapeados |
| Design system selection | `design_system_selector.py` | 16 curated + FRALIB_DS_DIR |
| Contratos determinísticos | `requirements_contract.py`, `visual_contract.py`, `site_build_plan.py` | Pipeline novo pós-PRD |

### ⚠️ CONFLITOS IDENTIFICADOS

#### CONFLITO #1: DesignerPRD — Duas implementações ativas do mesmo schema

- **`designer_prd.py`** (893 LOC) — Pydantic models antigos, auto-marcado como LEGADO, mas **ativamente importado** pelo manager (3x) e testes (1x)
- **Contratos novos** (`requirements_contract.py`, `visual_contract.py`, `site_build_plan.py`) — Sistema determinístico pós-PRD que substitui gradualmente o DesignerPRD

**Risco:** Se designer_prd.py for removido sem atualizar os imports do manager, o pipeline FSM quebra. O manager usa DesignerPRD em 3 pontos diferentes (linhas 209, 384, 531) com campos específicos.

**Ação pendente:** Aguardando aprovação do usuário para:
1. Mapear exatamente quais campos do DesignerPRD são usados em cada import
2. Definir se os contratos novos cobrem 100% dos casos de uso
3. Apenas após aprovação: migrar manager para contratos novos + remover designer_prd.py

#### CONFLITO #2: Duas implementações do Arquiteto Mestre

- **`arquiteto_mestre.py`** (506 LOC) — Implementação dict-based, usada pelo manager FSM
- **`arquiteto_agent_loop.py`** (493 LOC) — Managed Agent Loop com tool_use iteration, usada por endpoints HTTP

Ambas geram PRDs mas com abordagens diferentes:
- `arquiteto_mestre.py`: Chamada LLM direta, parse manual
- `arquiteto_agent_loop.py`: Loop de agentes com ferramentas (8 tools), MAX_ITERATIONS=8

**Risco:** Dois caminhos divergentes para a mesma saída (PRD). Mudanças em um não refletem no outro.

**Ação pendente:** Aguardando aprovação para decidir: consolidar em uma implementação ou manter paralelas com contrato de interface comum.

### 🔴 DUPLICADOS INTERNOS

#### DUPLICADO #1: TYPOGRAPHY_HIERARCHY em `craft_rules.py`

- Definido em linhas 187-216 e novamente em linhas 256-278
- Conteúdo idêntico em ambas as definições
- `get_craft_rules()` concatena ambas (linha 315-316), gerando output duplicado

#### DUPLICADO #2: LAWS_OF_UX em `craft_rules.py`

- Definido em linhas 218-253 e novamente em linhas 280-312
- Conteúdo idêntico em ambas as definições
- `get_craft_rules()` concatena ambas, gerando output duplicado

**Risco:** Prompts enviados ao LLM contêm regras de tipografia e UX duplicadas, desperdiçando tokens.

**Ação pendente:** Aguardando aprovação para remover a segunda ocorrência de cada constante.

---

## Bloco 2 — `backend/agents/manager/` (Orquestrador FSM)

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `manager/agent.py` | 932 | **[ATIVA]** | FSM pura (NÃO LangGraph). PIPELINE_STEPS = [hunter, caio, arquiteto, builder, qa, deploy, franz]. Imports designer_prd 3x + arquiteto_mestre 1x |

### Análise de Imports (quem importa manager)
- Nenhum arquivo importa o manager diretamente — o manager é o topo do fluxo

### Fonte da Verdade
- Orquestração FSM: `manager/agent.py`

### Ações Recomendadas
- Consolidar imports de designer_prd para contratos novos (pendente aprovação CONFLITO #1)
- Manter como está até resolução dos conflitos do Bloco 1

---

## Bloco 3 — `backend/agents/builder/` (Renderizador de Sites)

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `builder/agent.py` | — | **[ATIVA]** | Builder principal (OpenUI) |
| `builder/quality_gate.py` | — | **[ATIVA]** | Quality Gate v2 — Vision LLM pontua design |
| `builder_contract_utils.py` | — | **[ATIVA]** | Utilitários de contrato (archetype_id_from_visual_dna, first_value, list_value) |
| `builder_prd_spec.py` | — | **[ATIVA]** | Converte DesignerPRD → spec para renderer |
| (outros arquivos builder) | — | **[PENDENTE]** | Necessária leitura detalhada |

### Análise de Imports (quem importa builder)
- Importado pelo manager FSM (step_builder)
- Usado por test_builder_prd_spec.py

### Fonte da Verdade
- Builder: `builder/agent.py` (único renderer permitido — regra FraLib)

### Ações Recomendadas
- Pendente leitura detalhada dos arquivos do builder

---

## Bloco 4 — `backend/agents/caio/` (Qualificação de Leads)

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `caio/agent.py` | — | **[ATIVA]** | Qualifica leads com tier + score |

### Análise de Imports (quem importa caio)
- Importado pelo manager FSM (step_caio)

### Fonte da Verdade
- Caio: `caio/agent.py`

### Ações Recomendadas
- Pendente leitura detalhada

---

## Bloco 5 — `backend/agents/hunter/` (Mineração de Leads)

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `hunter/agent.py` | — | **[ATIVA]** | Mineração de leads via Jina + Google |

### Análise de Imports (quem importa hunter)
- Importado pelo manager FSM (step_hunter)

### Fonte da Verdade
- Hunter: `hunter/agent.py`

### Ações Recomendadas
- Pendente leitura detalhada

---

## Bloco 6 — `backend/agents/franz/` (SDR WhatsApp)

| Arquivo | LOC (aprox) | Categoria | Observações |
|---------|-------------|-----------|-------------|
| `franz/agent.py` | — | **[ATIVA]** | SDR WhatsApp com 15 ângulos de conversão |
| `franz/memory.py` | — | **[ATIVA]** | Memória semântica + episódica |
| `franz/learning.py` | — | **[ATIVA]** | Auto-aprendizado |

### Análise de Imports (quem importa franz)
- Importado pelo manager FSM (step_franz)

### Fonte da Verdade
- Franz: `franz/agent.py`

### Ações Recomendadas
- Pendente leitura detalhada

---

## Resumo Executivo

### Arquivos por Categoria

| Categoria | Quantidade | Arquivos |
|-----------|-----------|----------|
| **[ATIVA]** | ~25 | arquiteto_mestre, arquiteto_agent_loop, arquiteto_tools, prompts_arquiteto, design_context, design_system_selector, bloco_estrutura, bloco_copy, craft_rules, visual_archetypes, markdown_prd_parser, sub_nicho, design_director, seo_context, handoff_types, requirements_contract, visual_contract, site_build_plan, manager/agent.py, builder/*, caio/agent.py, hunter/agent.py, franz/* |
| **[LEGADO]** | 1 | arquiteto/agent.py.bak.20260730_171314 |
| **[DUPLICADO]** | 2 (interno) | TYPOGRAPHY_HIERARCHY ×2, LAWS_OF_UX ×2 (craft_rules.py) |
| **[CONFLITO]** | 1 | designer_prd.py (ativo mas marcado como legado) + arquiteto_mestre vs arquiteto_agent_loop (2 impls do mesmo PRD) |

### ⚠️ Ações Críticas Pendentes (requerem aprovação)

1. **CONFLITO #1 — designer_prd.py**: Mapear uso no manager → migrar para contratos novos → remover
2. **CONFLITO #2 — arquiteto_mestre vs arquiteto_agent_loop**: Consolidar ou manter paralelas com interface comum
3. **DUPLICADO #1 — TYPOGRAPHY_HIERARCHY**: Remover segunda ocorrência (linhas 256-278)
4. **DUPLICADO #2 — LAWS_OF_UX**: Remover segunda ocorrência (linhas 280-312)
5. **Estrutura faltante**: `arquiteto/agent.py` não existe — código espalhado em ~18 arquivos soltos

### Arquitetura: Evolução Monolito → Blocos

```
OLD (monólito): designer_prd.py (893 LOC)
    ↓ evolução
NEW (blocos):
    bloco_estrutura → estrutura + layout (LLM)
    bloco_copy → copy por seção (LLM)
    design_context → orquestrador de tokens/profiles/nichos
    craft_rules → regras anti-slop + tipografia + cores + animação
    prompts_arquiteto → system prompts + helpers
    arquiteto_tools → 8 ferramentas para agent loop
    arquiteto_agent_loop → managed agent iteration
    visual_archetypes → mapeamento visual_dna → archetype
    markdown_prd_parser → parsing de PRD markdown → dict
    sub_nicho → detecção de sub-nicho
    design_director → orquestração do creative brief
    seo_context → framework SEO por nicho
    requirements_contract + visual_contract + site_build_plan → contratos determinísticos pós-PRD
```

**Conclusão:** O arquiteto evoluiu de monólito para arquitetura em blocos bem-modularizada. O conflito principal é que o manager ainda usa o monólito antigo (designer_prd.py) enquanto os endpoints usam a arquitetura nova (agent loop + blocos).
