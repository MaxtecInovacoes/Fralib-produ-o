# TEST_001 - Cobertura de Testes

## Status Atual

| Métrica | Valor | Meta |
|---------|-------|------|
| Coverage Total | **9%** | 80% |
| Testes Coletados | 697 | - |
| Testes Passando | 19+ | - |

## Arquivos Críticos SEM Testes (Priority Order)

| Arquivo | Linhas | Prioridade | Módulos para Testar |
|---------|--------|-------------|---------------------|
| `vite_react_renderer.py` | 3.809 | 🔴 CRÍTICO | Funções de renderização |
| `pipeline_orchestrator_service.py` | 3.143 | 🔴 CRÍTICO | Orquestração de pipeline |
| `vite_config_helpers.py` | 249 | 🟡 ALTA | Config getters |
| `agent_router.py` | 123 | 🟡 ALTA | Router de agentes |
| `cache_service.py` | 150+ | 🟡 ALTA | Cache Redis |
| `circuit_breaker.py` | 200+ | 🟡 ALTA | Circuit breaker pattern |

## Plano TDD

### Fase 1: Testes para vite_config_helpers (Quick Win)
- Testar `_env_int` com defaults
- Testar `_single_model_mode_enabled`
- Testar `_model_candidates`
- Testar `_normalize_model_alias`

### Fase 2: Testes para cache_service
- Testar cache hit
- Testar cache miss
- Testar fallback quando Redis indisponível

### Fase 3: Testes para circuit_breaker
- Testar estado fechado → aberto
- Testar timeout e recuperação
- Testar falha rápida

### Fase 4: Testes para agent_router
- Testar `calcular_complexidade_lead`
- Testar `get_model`
- Testar `escalate`

## Cobertura Atual por Módulo

| Módulo | Coverage Atual |
|--------|---------------|
| backend/core | 14% |
| backend/agents | 8% |
| backend/endpoints | 12% |
| backend/services | 5% |
| backend/utils | 15% |
| backend/whatsapp | 25% |
