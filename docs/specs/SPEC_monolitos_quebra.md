# 📋 SPEC: Quebra de Monolitos - INVESTIGAÇÃO COMPLETA

**Data:** 2026-06-19
**Modo:** LOCAL (sem push)
**Investigação:** 3 agentes paralelos

---

## 🎯 DECISÕES BASEADAS NA INVESTIGAÇÃO

### Decisão 1: `openui_renderer.py` (2253 linhas)

**Status:** PARALELO (manter)
- É fallback do Vite (`FRALIB_BUILDER_ENGINE=openui`)
- Tem testes que dependem dele
- Custo de manter é baixo
- **Ação:** NÃO TOCAR nesta fase

### Decisão 2: `pipeline_prd_builder.py` (1130 linhas)

**Status:** QUEBRAR EM 5 MÓDULOS
- 5 funções CORE (75% lógica)
- **ZERO testes nas core** ⚠️
- Duplicação de lógica detectada

**Módulos criados:**
| Arquivo | LOC | Risco | Esforço |
|---------|-----|-------|---------|
| `pipeline_validators.py` | ~150 | BAIXO | 2h |
| `pipeline_media.py` | ~150 | BAIXO | 1.5h |
| `pipeline_builders.py` | ~350 | MÉDIO | 4h |
| `pipeline_prompt_agent.py` | ~200 | MÉDIO | 3h |
| `pipeline_prd_builder.py` (wrapper) | ~50 | BAIXO | 1h |

**Total:** 11.5h

### Decisão 3: `pipeline_orchestrator_service.py` (3120 linhas)

**Status:** QUEBRAR EM 12 MÓDULOS (3 fases)

**FASE 1 - Infraestrutura (~456 linhas, baixo risco):**
1. `pipeline_llm_context.py` (~12 linhas)
2. `pipeline_sse_handler.py` (~32 linhas)
3. `pipeline_trace_helpers.py` (~57 linhas)
4. `pipeline_heartbeat.py` (~37 linhas)
5. `pipeline_lead_persistence.py` (~318 linhas)

**FASE 2 - Lógica de fases (~700 linhas, médio risco):**
6. `pipeline_intel_assets.py`
7. `pipeline_nicho_variacao.py`
8. `pipeline_prd_postprocess.py`
9. `pipeline_html_validation.py`
10. `pipeline_deploy_publish.py`

**FASE 3 - Cleanup (~350 linhas, opcional):**
11. `pipeline_error_handling.py`
12. `pipeline_finalization.py`

**Total:** ~1500 linhas removidas do orchestrator

### Decisão 4: `html_sanitizer.py` (2665 linhas)

**Status:** DELETAR (confirmado morto)

---

## 📅 PLANO DE EXECUÇÃO ORDENADO

### FASE 0: Limpeza Imediata (5 min)
- [ ] **DELETAR** `html_sanitizer.py`
- [ ] Validar `verify_all.sh` continua 🟢

### FASE 1: Pré-requisitos (3h)
- [ ] Criar testes de contrato para `pipeline_prd_builder` (5 funções core)
- [ ] Criar testes E2E básicos
- [ ] Criar benchmark script (antes/depois)

### FASE 2: pipeline_orchestrator FASE 1 (8h)
- [ ] Extrair `pipeline_llm_context.py` + teste
- [ ] Extrair `pipeline_sse_handler.py` + teste
- [ ] Extrair `pipeline_trace_helpers.py` + teste
- [ ] Extrair `pipeline_heartbeat.py` + teste
- [ ] Extrair `pipeline_lead_persistence.py` + teste
- [ ] **VALIDAÇÃO:** 1 lead E2E + benchmark

### FASE 3: pipeline_prd_builder (12h)
- [ ] Validators primeiro (mais isolado)
- [ ] Media segundo (com HTTP mock)
- [ ] Builders (com testes de contrato)
- [ ] Prompt Agent
- [ ] Wrapper de compatibilidade
- [ ] **VALIDAÇÃO:** benchmark comparativo

### FASE 4: pipeline_orchestrator FASE 2 (8h)
- [ ] intel_assets, nicho_variacao
- [ ] prd_postprocess, html_validation
- [ ] deploy_publish
- [ ] **VALIDAÇÃO:** produção real

---

## 🛡️ MECANISMOS DE SEGURANÇA

### Para CADA extração:
1. **Snapshot** do estado atual (benchmark_before.json)
2. **Extrair** função para novo módulo
3. **Importar** no orchestrator
4. **Rodar** testes unitários
5. **Rodar** benchmark E2E
6. **Comparar** output
7. **Commit** se OK, **reverter** se pior

### Critérios de "Não Quebrou":
- Pipeline success rate: igual ou melhor
- HTML output: idêntico (mesmo conteúdo)
- Tempo de execução: < 1.1x
- Logs SSE: normais
- Crédito descontado: 1 (igual)

---

## 📋 PRÉ-REQUISITOS ANTES DE COMEÇAR

### Testes a criar ANTES:
- [ ] `tests/unit/test_pipeline_prd_contracts.py` - contratos das 5 funções core
- [ ] `tests/e2e/test_pipeline_complete.py` - 1 lead end-to-end
- [ ] `scripts/benchmark_pipeline.py` - comparação antes/depois

### Documentação:
- [ ] Mapa de funções/módulos
- [ ] Lista de entrypoints públicos
- [ ] Contratos de cada função core

---

## ⚠️ ARQUIVOS QUE NÃO VOU TOCAR

| Arquivo | Razão |
|---------|-------|
| `database.py` | Crítico, funciona |
| `whatsapp_listener.py` | Keepalive já implementado |
| `whatsmeow_/*.go` | Keepalive Go já feito |
| `openui_renderer.py` | Fallback válido |
| Outros monolitos menores | Prioridade depois |

---

## 🎯 MÉTRICAS DE SUCESSO

| Métrica | Antes | Meta |
|---------|-------|------|
| Linhas em `pipeline_orchestrator_service.py` | 3120 | < 1500 |
| Linhas em `pipeline_prd_builder.py` | 1130 | < 200 |
| Testes nas funções core | 0% | 80% |
| Try/except silenciosos | 30+ | < 10 |
| Tempo de pipeline | X | < 1.1x |
| HTML output parity | 100% | 100% |

---

## 🚀 PRIMEIROS PASSOS IMEDIATOS

### AGORA (FASE 0):
1. ✅ DELETAR `html_sanitizer.py`
2. ✅ Rodar `verify_all.sh` para confirmar
3. ✅ Criar testes E2E básicos

### HOJE (FASE 1 + 2):
1. ✅ Criar testes de contrato para `pipeline_prd_builder`
2. ✅ Criar benchmark script
3. ✅ Extrair primeiros 3 helpers do orchestrator

### ESTA SEMANA:
- Completar FASE 1 e FASE 2

---

*Atualizado em: 2026-06-19*
*Baseado em investigação de 3 agentes em paralelo*
