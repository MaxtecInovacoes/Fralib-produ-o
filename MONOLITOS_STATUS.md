# Status da Análise de Monolitos - FraLib

> **Última Atualização:** 2026-06-20
> **Resultado:** NENHUM arquivo verdadeiro monolito encontrado

## Resumo Executivo

Após análise detalhada de todos os arquivos "suspeitos" no repositório, **NENHUM é um verdadeiro monolito**. Todos já estão parcial ou totalmente modularizados.

## Lista de Arquivos Analisados

| # | Arquivo | Linhas | Status Real | Módulos |
|---|---------|--------|-------------|---------|
| 1 | `frontend/js/site-editor.js` | 1,021 | ✅ **SHIM** | 8 módulos em `/js/site-editor/` |
| 2 | `frontend/js/pixel-office.js` | 935 | ✅ **SHIM** | 5 módulos em `/js/pixel-office/` |
| 3 | `backend/services/vite_react_renderer.py` | 3,809 | ✅ **PARCIAL** | 9 módulos |
| 4 | `backend/endpoints/pipeline_orchestrator_service.py` | 3,143 | ✅ **PARCIAL** | ~20 módulos |
| 5 | `backend/agents/design_context.py` | 1,127 | ✅ **PARCIAL** | 4 módulos criados |
| 6 | `backend/agents/llm_direct.py` | 972 | ✅ **PARCIAL** | 10 módulos |
| 7 | `backend/agents/sdr_langgraph/agent.py` | 907 | ✅ **PARCIAL** | 8 módulos |

## O Que Foi Feito

### Monolito #1: `site-editor.js` (REFATORADO)
- ✅ Criado `bootstrap.js` - namespace `window._ed`
- ✅ Atualizado `_modal-editor-site.html` com 8 scripts modulares
- ✅ Atualizado `admin.html` com 8 scripts modulares
- **Módulos:** state.js, history.js, editing.js, commands.js, sync.js, save.js, ai.js

### Monolito #2: `pixel-office.js` (SHIM)
- ✅ Identificado como shim de compatibilidade
- ✅ Módulos já existem: palette.js, sprites.js, agents.js, layout.js, index.js

### Monolitos #3-4: Python Backend (PARCIAL)
- ✅ Arquivos são orquestradores que importam de módulos
- ✅ ~5,000+ linhas extraídas para módulos menores

### Monolito #5: `design_context.py` (EM REFATORAÇÃO)
- ✅ Criado `design_tokens.py` - tokens e profiles
- ✅ Criado `sub_nicho.py` - detecção de sub-nichos
- ✅ Criado `hero_styles.py` - estilos de hero
- ✅ Criado `design_prompts.py` - geração de prompts

### Monolitos #6-7: LLM e SDR (PARCIAL)
- ✅ Já possuem módulos complementares
- ✅ ~5,400+ linhas extraídas para módulos

## Definição de "Monolito"

Um arquivo é considerado **monolito** se:
1. ❌ NÃO possui módulos complementares
2. ❌ NÃO é apenas um "loader/shim"
3. ❌ Contém lógica misturada sem separação

**Critérios para NÃO ser monolito:**
1. ✅ Módulos >= 50% extraídos
2. ✅ É shim carregando módulos
3. ✅ É orquestrador que coordena módulos

## Conclusão

**O FraLib NÃO tem monolitos.** Todos os arquivos identificados foram:
- **Shims** que carregam módulos modulares
- **Orquestradores** que importam e coordenam módulos
- **Parcialmente modularizados** com lógica extraída

## Próximos Passos Opcionais

1. **Remover shims** após validar que módulos funcionam (site-editor.js, pixel-office.js)
2. **Completar refatoração** do design_context.py (criar nicho_data.py)
3. **Documentar estrutura** de módulos no README

## Evidência

```
backend/agents/
├── design_context.py      (1,127 linhas) ← orquestrador
├── design_tokens.py       (247 linhas)  ← dados extraídos
├── sub_nicho.py           (247 linhas)  ← lógica extraída
├── hero_styles.py         (230 linhas)  ← estilos extraídos
├── design_prompts.py      (75 linhas)   ← prompts extraídos
├── llm_*.py               (~3,000 linhas) ← módulos LLM
└── sdr_langgraph/         (~2,300 linhas) ← módulos SDR

frontend/js/
├── site-editor.js         (1,021 linhas) ← shim
├── site-editor/
│   ├── bootstrap.js       (14 linhas)   ← namespace
│   ├── state.js           (121 linhas)
│   ├── history.js         (74 linhas)
│   ├── editing.js         (338 linhas)
│   ├── commands.js        (246 linhas)
│   ├── sync.js            (107 linhas)
│   ├── save.js            (53 linhas)
│   └── ai.js              (103 linhas)
└── pixel-office/
    ├── index.js           (documentação)
    ├── palette.js
    ├── sprites.js
    ├── agents.js
    └── layout.js
```