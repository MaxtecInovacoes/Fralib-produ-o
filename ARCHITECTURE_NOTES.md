# Arquitetura Modular - FraLib

> **Este arquivo é histórico/operacional. A fonte única de verdade da arquitetura
> e da pipeline é [`AGENTS.md`](../AGENTS.md). Se este doc divergir de `AGENTS.md`,
> `AGENTS.md` vence.**

## ⚠️ AVISO IMPORTANTE

**Estes arquivos NÃO são monolitos:**
- `frontend/js/site-editor.js`
- `frontend/js/pixel-office.js`
- `backend/services/openui_renderer.py` (gerador canônico de sites)
- `backend/services/builder_worker.py` (orquestra OpenUI vs Vite/React)
- `backend/endpoints/pipeline_orchestrator_service.py` (orquestrador da pipeline)
- `backend/agents/design_context.py`
- `backend/agents/llm_direct.py`
- `backend/agents/sdr_langgraph/agent.py` (Franz/SDR)

Todos são **shims de compatibilidade**, **orquestradores** ou **entry points canônicos**
que coordenam módulos modulares.

## O Que São Shims?

Um **shim** é um arquivo de compatibilidade que existe para:
1. Manter API backward compatibility.
2. Carregar módulos na ordem correta.
3. Re-exportar símbolos para código legado.

**Shims são intencionais e necessários.** Não são código técnico-debt.

## O Que São Orquestradores?

Um **orquestrador** é um arquivo que:
1. Coordena múltiplos módulos.
2. Gerencia fluxo de dados entre módulos.
3. Não contém lógica de negócio isolada.

**Orquestradores são arquitetura válida.** Separam "o quê fazer" de "como fazer".

## Identificação de Shims/Orquestradores (situação atual)

### JavaScript/Frontend
```
frontend/js/site-editor.js      → SHIM (carrega 8 módulos)
frontend/js/pixel-office.js     → SHIM (carrega 5 módulos)
```

### Python/Backend
```
backend/services/openui_renderer.py                  → ENTRY POINT CANÔNICO (gerador de sites)
backend/services/builder_worker.py                    → ORQUESTRADOR (OpenUI vs Vite/React)
backend/endpoints/pipeline_orchestrator_service.py   → ORQUESTRADOR (ordem real da pipeline)
backend/agents/design_context.py                     → ORQUESTRADOR
backend/agents/llm_direct.py                         → ORQUESTRADOR
backend/agents/sdr_langgraph/agent.py                → ORQUESTRADOR (Franz/SDR)
```

## Como Identificar um Shim

1. **Comentário no topo** indicando que é shim.
2. **Imports de módulos** no mesmo diretório.
3. **Código mínimo** - apenas bootstrapping.
4. **Sem lógica de negócio** isolada.

Exemplo de shim:
```javascript
/**
 * Compatibility shim — loads all modular components in dependency order.
 * New development should use /js/module-name/ modules.
 */
import './module/state.js';
import './module/editing.js';
// ...
```

## Como Identificar um Orquestrador

1. **Muitos imports** de módulos do mesmo diretório/pacote.
2. **Funções que chamam funções** de outros módulos.
3. **Pouca lógica standalone** - a maioria chama outros módulos.
4. **Docstring mencionando "orquestrador"**.

## Critérios para SER Monolito (NÃO são os arquivos acima)

Um arquivo é monolito se:
- ❌ Tem 1000+ linhas de lógica de negócio.
- ❌ Não importa de módulos complementares.
- ❌ Contém dados, lógica E apresentação misturados.
- ❌ Não pode ser testado isoladamente.

## Como Evitar Falsos Positivos em Auditorias

1. ✅ Verificar se há pasta/arquivos com mesmo nome + `_` (ex: `site-editor/` junto de `site-editor.js`).
2. ✅ Procurar por comentários "shim", "compatibility", "deprecated".
3. ✅ Contar imports vs. código standalone.
4. ✅ Verificar se o arquivo apenas faz `import X; X.y();`.

## Estrutura de Diretórios Esperada

```
frontend/js/
├── site-editor.js          ← SHIM (14 linhas)
└── site-editor/
    ├── bootstrap.js
    ├── state.js
    ├── history.js
    ├── editing.js
    ├── commands.js
    ├── sync.js
    ├── save.js
    └── ai.js

backend/services/
├── openui_renderer.py      ← ENTRY POINT CANÔNICO (gerador de sites)
├── openui_contracts.py     ← 7 contratos para o system prompt
├── builder_worker.py       ← orquestra OpenUI vs Vite/React
└── vite_react_renderer.py  ← Vite/React Studio Premium (opt-in)

backend/agents/
├── design_context.py       ← ORQUESTRADOR
├── design_tokens.py        ← MÓDULO DE DADOS
├── sub_nicho.py            ← MÓDULO DE LÓGICA
├── hero_styles.py          ← MÓDULO DE ESTILOS
├── design_prompts.py       ← MÓDULO DE PROMPTS
├── caio.py                 ← qualificação determinística
├── agente_nicho.py         ← Nicho (LLM Sonnet)
├── agente_variacao.py      ← Variação (LLM Haiku)
├── arquiteto_mestre.py     ← DesignerPRD (LLM Sonnet)
├── bloco_estrutura.py      ← Design Director
├── bloco_copy.py           ← Copy Senior
└── html_quality_gate.py    ← quality gate determinístico
```

## Comandos Úteis

### Listar todos os shims
```bash
grep -l "compatibility shim\|SHIM\|deprecated" frontend/js/*.js backend/**/*.py
```

### Verificar se arquivo é orquestrador
```bash
wc -l arquivo.py
grep "^from\|^import" arquivo.py | wc -l
```

### Ver estrutura modular
```
find . -name "*.py" -o -name "*.js" | xargs grep -l "MODULAR\|module\|from backend"
```

---

**Data da última consolidação:** 2026-06-22 (operação "Uma Verdade Só")
**Fonte única de verdade:** [`AGENTS.md`](../AGENTS.md)
