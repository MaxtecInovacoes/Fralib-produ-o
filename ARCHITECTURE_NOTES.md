# Arquitetura Modular - FraLib

> **Este documento é a fonte de verdade sobre a estrutura modular do projeto.**

## ⚠️ AVISO IMPORTANTE

**Estes arquivos NÃO são monolitos:**
- `frontend/js/site-editor.js`
- `frontend/js/pixel-office.js`
- `backend/services/vite_react_renderer.py`
- `backend/endpoints/pipeline_orchestrator_service.py`
- `backend/agents/design_context.py`
- `backend/agents/llm_direct.py`
- `backend/agents/sdr_langgraph/agent.py`

Todos são **shims de compatibilidade** ou **orquestradores** que coordenam módulos modulares.

## O Que São Shims?

Um **shim** é um arquivo de compatibilidade que existe para:
1. Manter API backward compatibility
2. Carregar módulos na ordem correta
3. Re-exportar símbolos para código legado

**Shims são intencionais e necessários.** Não são código técnico-debt.

## O Que São Orquestradores?

Um **orquestrador** é um arquivo que:
1. Coordena múltiplos módulos
2. Gerencia fluxo de dados entre módulos
3. Não contém lógica de negócio isolada

**Orquestradores são arquitetura válida.** Separam "o quê fazer" de "como fazer".

## Identificação de Shims/Orquestradores

### JavaScript/Frontend
```
frontend/js/site-editor.js      → SHIM (carrega 8 módulos)
frontend/js/pixel-office.js     → SHIM (carrega 5 módulos)
```

### Python/Backend
```
backend/services/vite_react_renderer.py         → ORQUESTRADOR
backend/endpoints/pipeline_orchestrator_service.py → ORQUESTRADOR
backend/agents/design_context.py                → ORQUESTRADOR
backend/agents/llm_direct.py                    → ORQUESTRADOR
backend/agents/sdr_langgraph/agent.py           → ORQUESTRADOR
```

## Como Identificar um Shim

1. **Comentário no topo** indicando que é shim
2. **Imports de módulos** no mesmo diretório
3. **Código mínimo** - apenas bootstrapping
4. **Sem lógica de negócio** isolada

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

1. **Many imports** de módulos do mesmo diretório/pacote
2. **Funções que chamam funções** de outros módulos
3. **Pouca lógica standalone** - a maioria chama outros módulos
4. **Docstring mencionando "orquestrador"**

## Critérios para SER Monolito (NÃO são os arquivos acima)

Um arquivo é monolito se:
- ❌ Tem 1000+ linhas de lógica de negócio
- ❌ Não importa de módulos complementares
- ❌ Contém dados, lógica E apresentação misturados
- ❌ Não pode ser testado isoladamente

## Como Evitar Falsos Positivos em Auditorias

1. ✅ Verificar se há pasta/arquivos com mesmo nome + `_` (ex: `site-editor/` junto de `site-editor.js`)
2. ✅ Procurar por comentários "shim", "compatibility", "deprecated"
3. ✅ Contar imports vs. código standalone
4. ✅ Verificar se o arquivo apenas faz `import X; X.y();`

## Estrutura de Diretórios Esperada

```
frontend/js/
├── site-editor.js          ← SHIM (14 linhas)
└── site-editor/
    ├── bootstrap.js
    ├── state.js
    ├── editing.js
    ├── commands.js
    └── ...

backend/agents/
├── design_context.py       ← ORQUESTRADOR (~200 linhas)
├── design_tokens.py        ← MÓDULO DE DADOS
├── sub_nicho.py            ← MÓDULO DE LÓGICA
├── hero_styles.py          ← MÓDULO DE ESTILOS
└── design_prompts.py       ← MÓDULO DE PROMPTS
```

## Comandos Úteis

### Listar todos os shims
```bash
grep -l "compatibility shim\|SHIM\|deprecated" frontend/js/*.js backend/**/*.py
```

### Verificar se arquivo é orquestrador
```bash
# Conta imports vs. linhas de lógica
wc -l arquivo.py
grep "^from\|^import" arquivo.py | wc -l
```

### Ver estrutura modular
```
find . -name "*.py" -o -name "*.js" | xargs grep -l "MODULAR\|module\|from backend"
```

---

**Data:** 2026-06-20
**Última verificação:** Auditoria de monolitos
**Resultado:** 0 verdadeiros monolitos encontrados