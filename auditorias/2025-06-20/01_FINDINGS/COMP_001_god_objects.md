# COMP_001 - Refatoração de God Objects

## Problema
Dois arquivos com responsabilidade excessiva:
1. `backend/services/vite_react_renderer.py` - **3.809 linhas, 100+ funções**
2. `backend/endpoints/pipeline_orchestrator_service.py` - **3.143 linhas**

## Análise: vite_react_renderer.py

### Funções por Categoria (100+ funções)

| Categoria | Qtd | Descrição |
|-----------|-----|-----------|
| Config getters | 15 | `_env_int`, `_single_model_mode_enabled`, etc |
| Proxy LLM | 12 | `_call_proxy_openai_chat`, `_proxy_credentials`, etc |
| File extraction | 8 | `extract_vite_project_files`, `_extract_tagged_file_blocks`, etc |
| Project validation | 12 | `validate_vite_dist`, `_validate_studio_project`, etc |
| Contract stabilization | 15 | `_stabilize_navbar_contract`, `_ensure_lgpd_banner_contract`, etc |
| Default templates | 20 | `_default_hero_section_tsx`, `_default_footer_tsx`, etc |
| Build helpers | 8 | `write_vite_project`, `build_vite_project`, etc |
| Facts processing | 10 | `_facts_business`, `_facts_publication_url`, etc |

## Estratégia de Refatoração

### Fase 1: Extração de Config (Quick Win)
```
vite_react_renderer.py
  → vite_config.py (15 config getters já existem em services/)
  → vite_config_helpers.py (NEW - config helpers)
```

### Fase 2: Extração de Templates
```
vite_react_renderer.py
  → vite_templates.py (NEW - 20+ default template functions)
```

### Fase 3: Extração de Contracts
```
vite_react_renderer.py
  → vite_contracts.py (NEW - contract stabilization)
```

### Fase 4: Extração de File Processing
```
vite_react_renderer.py
  → vite_file_extractor.py (EXISTE - mover funções restantes)
```

## Arquivos Recomendados

| Arquivo | Responsabilidade | Linhas Estimadas |
|---------|-----------------|------------------|
| vite_react_renderer.py | Core + orchestration | ~600 |
| vite_config.py | Config existente | ~200 |
| vite_config_helpers.py | NEW - config helpers | ~300 |
| vite_templates.py | NEW - default templates | ~800 |
| vite_contracts.py | NEW - contract stabilization | ~600 |
| vite_file_extractor.py | File extraction (EXISTE +扩展) | ~400 |

## Esforço Estimado
- **Fase 1**: 2h (Quick win - não muda comportamento)
- **Fase 2**: 4h (Templates são independentes)
- **Fase 3**: 4h (Contracts dependem de templates)
- **Fase 4**: 2h (Funções bem isoladas)

**Total**: ~12h para 3.809 → ~600 linhas (-84%)

## Problema Adicional: Duplicação de Funções

| Função | vite_config.py | vite_react_renderer.py |
|--------|---------------|------------------------|
| `_env_int` | ✅ Definida | ✅ Duplicada inline |
| `_model_repair_attempts` | ✅ Definida | ✅ Duplicada inline |
| `_single_model_mode_enabled` | ✅ Definida | ✅ Duplicada inline |
| `_preview_fast_enabled` | ✅ Definida | ✅ Duplicada inline |
| `_batch_first_enabled` | ✅ Definida | ✅ Duplicada inline |
| `_batch_first_project_attempts` | ✅ Definida | ✅ Duplicada inline |
| `_batch_spacing_seconds` | ✅ Definida | ✅ Duplicada inline |
| `_batch_max_tokens` | ✅ Definida | ✅ Duplicada inline |
| `_batch_token_budget` | ✅ Definida | ✅ Duplicada inline |
| `_batch_format_repair_budget` | ✅ Definida | ✅ Duplicada inline |
| `_studio_min_source_chars` | ✅ Definida | ✅ Duplicada inline |
| `_studio_min_classnames` | ✅ Definida | ✅ Duplicada inline |
| `_studio_min_images` | ✅ Definida | ✅ Duplicada inline |
| `_studio_min_components` | ✅ Definida | ✅ Duplicada inline |
| `_transient_proxy_retry_delay_seconds` | ✅ Definida | ✅ Duplicada inline |

### Causa Raiz
O try/except import em vite_react_renderer.py falha silenciosamente, usando definições inline ao invés de imports.

### Solução Parcial Criada
- `vite_config_helpers.py` - novo módulo com funções de configuração (150 linhas)
