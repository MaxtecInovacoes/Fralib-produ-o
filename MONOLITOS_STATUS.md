# Monolitos - Status Final

> **ATENÇÃO:** Após análise detalhada, nenhum arquivo do FraLib é um verdadeiro monolito.
> Todos já estão parcial ou totalmente modularizados.

## Resumo da Análise (2026-06-20)

| # | Arquivo | Linhas | Status | Módulos |
|---|---------|--------|--------|---------|
| 1 | `frontend/js/site-editor.js` | 1,021 | ✅ **REFATORADO** | 8 módulos em `/js/site-editor/` |
| 2 | `frontend/js/pixel-office.js` | 935 | ✅ **SHIM** | 5 módulos em `/js/pixel-office/` |
| 3 | `backend/services/vite_react_renderer.py` | 3,809 | ✅ **PARCIAL** | 9 módulos |
| 4 | `backend/endpoints/pipeline_orchestrator_service.py` | 3,143 | ✅ **PARCIAL** | ~20 módulos |
| 5 | `backend/agents/design_context.py` | 1,127 | 🔄 **EM REFATORAÇÃO** | 5 módulos sendo criados |
| 6 | `backend/agents/llm_direct.py` | 972 | ✅ **PARCIAL** | 10 módulos |
| 7 | `backend/agents/sdr_langgraph/agent.py` | 907 | ✅ **PARCIAL** | 8 módulos |

## Critérios para "Monolito"

Um arquivo é considerado monolito se:
- **NÃO** possui módulos complementares no mesmo diretório
- **NÃO** é apenas um "loader" que importa de módulos existentes
- Contém lógica misturada sem separação clara

## Conclusão

**NENHUM arquivo no FraLib é um verdadeiro monolito.**

Todos os arquivos "suspeitos" já possuem módulos complementares que extraem lógica, dados e funcionalidades para arquivos separados.

## Ações Recomendadas

1. **site-editor.js** → Remover shim após validar que módulos carregam
2. **pixel-office.js** → Remover shim (módulos existem)
3. **design_context.py** → Concluir refatoração (5 módulos em criação)
4. **Demais** → Marcar como "parcialmente modularizado" e monitorar

## Documentação por Arquivo

### Arquivos Refatorados Completamente

#### `frontend/js/site-editor.js` ✅
- Shim de compatibilidade
- Módulos reais em `/js/site-editor/`:
  - `bootstrap.js` - Namespace `window._ed`
  - `state.js` - Estado global
  - `history.js` - Undo/redo
  - `editing.js` - Edição
  - `commands.js` - Comandos
  - `sync.js` - Sincronização
  - `save.js` - Persistência
  - `ai.js` - AI

#### `frontend/js/pixel-office.js` ✅
- Shim de compatibilidade
- Módulos reais em `/js/pixel-office/`:
  - `palette.js` - Paleta e funções de desenho
  - `sprites.js` - Factory de sprites
  - `agents.js` - Classes Agent/Bubble
  - `layout.js` - Layout e loop
  - `index.js` - Documentação

### Arquivos Parcialmente Modularizados

#### `backend/services/vite_react_renderer.py` (3,809 → ~1,800)
Módulos:
- `vite_config.py` (236)
- `vite_config_helpers.py` (249)
- `vite_prompts.py` (267)
- `vite_facts.py` (240)
- `vite_file_extractor.py` (203)
- `vite_validator.py` (195)
- `vite_build_executor.py` (397)
- `vite_modules.py` (127)
- `vite_renderer_models.py` (63)
- **Total extraído:** ~1,977 linhas

#### `backend/endpoints/pipeline_orchestrator_service.py` (3,143 → ~2,500)
Módulos:
- `pipeline_execution_core.py` (190)
- `pipeline_phase_helpers.py` (359)
- `pipeline_lead_flow_helpers.py` (303)
- `pipeline_lead_persistence.py` (561)
- `pipeline_status_endpoints.py` (254)
- `pipeline_trace_helpers.py` (222)
- `pipeline_heartbeat.py` (160)
- `pipeline_start_endpoints.py` (169)
- +12 arquivos menores
- **Total extraído:** ~3,107 linhas

#### `backend/agents/llm_direct.py` (972 → ~700)
Módulos:
- `llm_providers.py` (694)
- `llm_router.py` (392)
- `llm_anthropic.py` (362)
- `llm_client.py` (359)
- `llm_context.py` (258)
- `llm_tracking.py` (250)
- `llm_config.py` (239)
- `llm_openai.py` (238)
- `llm_google.py` (189)
- `llm_agent_config.py` (107)
- **Total extraído:** ~3,088 linhas

#### `backend/agents/sdr_langgraph/agent.py` (907 → ~500)
Módulos:
- `state.py` (197)
- `tools.py` (278)
- `prompts.py` (359)
- `learning.py` (318)
- `multi_agent.py` (279)
- `watchdog.py` (189)
- `compat.py` (509)
- `nodes/__init__.py`
- **Total extraído:** ~2,342 linhas

#### `backend/agents/design_context.py` (1,127 → em refatoração)
Módulos em criação:
- `design_tokens.py` (~466)
- `sub_nicho.py` (~196)
- `hero_styles.py` (~199)
- `nicho_data.py` (~206)
- `design_prompts.py` (~42)

---

## Conclusão Final

✅ **O FraLib NÃO tem monolitos.**

Todos os arquivos identificados como "monolíticos" são na verdade:
1. **Shims de compatibilidade** (carregam módulos modulares)
2. **Orquestradores** (importam e coordenam módulos)
3. **Parcialmente modularizados** (lógica extraída para módulos)

A refatoração está em andamento para completar a modularização do `design_context.py`.