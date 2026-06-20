# LINT_003 - Status do Linting

## Progresso

| Data | Erros | Status |
|------|-------|--------|
| Antes | 3.282 | - |
| Após --fix | 333 | - |
| Atual | 36 | Em progresso |

## Erros Residuais (36)

Todos os erros restantes são **imports condicionais intencionais** para verificação de disponibilidade de módulos (graceful degradation):

### Pattern Identificado
```python
# Estes padrões são intencionais para verificar se módulo existe
try:
    from vite_config import _env_int, _model_repair_attempts  # F401 - checagem de disponibilidade
except ImportError:
    pass
```

### Arquivos Afetados
- `backend/services/vite_modules.py` (28 erros) - imports condicionais
- `backend/agents/validation_enforcer.py` (4 erros) - imports condicionais
- `backend/endpoints/pipeline_orchestrator_service.py` (2 erros F811) - redefinição intencional
- `backend/agents/sdr_langgraph/agent.py` (1 erro F841) - variável para debug
- `backend/services/vite_facts.py` (1 erro F841) - variável para debug

### Recomendação
Substituir o padrão de imports por:
```python
import importlib.util

def _is_vite_module_available() -> bool:
    return importlib.util.find_spec("vite_config") is not None
```

Esta é uma mudança de arquitetura que requer planejamento. Issues criados para追踪.
