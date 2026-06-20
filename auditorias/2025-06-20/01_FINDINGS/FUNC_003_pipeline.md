# FUNC_003 - Pipeline de Geração

## Resumo Executivo

**Data:** 2025-06-20
**Status Geral:** OPERACIONAL - Todos os testes passando
**Smoke Test:** PASS (16.47s em modo dry-run)

---

## Fases Verificadas

| Fase | Status | Agente | Issues |
|-------|--------|--------|--------|
| 1 | OK | Hunter + Keyword Research | Paralelização OK (ThreadPoolExecutor) |
| 2 | OK | Caio (Qualificação) | Executado em paralelo com Jina |
| 3 | OK | Jina AI (Inteligência Mercado) | Cache + fallback v1 implementados |
| 4 | OK | Design Director (OKLch tokens) | Checkpoint + continuação implementados |
| 5 | OK | Fotos (Unsplash/Pexels) | Preparação de assets no `prepare_lead_intelligence_assets` |
| 6 | OK | Agente Nicho | Checkpoint + fast-path implementados |
| 7 | OK | Agente Variação | Checkpoint + fast-path implementados |
| 8 | OK | Arquiteto Mestre | PRD cache + design contracts |
| 9 | OK | Builder (Open Design) | Quality gate + repair loop (max 3 attempts) |
| 10 | OK | Deploy | Sitemap + robots.txt + permissões |
| 11 | OK | Franz/SDR | Enfileiramento assíncrono via job_queue |

---

## Problemas de Integração

### 1. Jina Fallback Silencioso (NÃO-BLOQUEANTE)
**Severidade:** Baixa
**Local:** `backend/endpoints/pipeline_orchestrator_service.py:1058-1083`
**Descrição:** Quando Jina v2 falha, tenta fallback v1. Se ambos falham, continua sem insights (SEO incompleto).
```python
except Exception as fallback_err:
    logger.warning(f"[Pipeline] Jina fallback v1 também falhou: {fallback_err}")
    return {"insights": "", "intel": {}, "cached": False, "error": str(e)}
```
**Recomendação:** Adicionar métrica para monitorar taxa de falha do Jina.

### 2. Keyword Research Falha Silenciosa (NÃO-BLOQUEANTE)
**Severidade:** Baixa
**Local:** `backend/endpoints/pipeline_orchestrator_service.py:592-594`
**Descrição:** Se keyword research falha, continua com string vazia.
```python
except Exception as _e:
    logger.warning(f"[Pipeline] Keyword research erro: {_e}")
```
**Recomendação:** O SEO do site ficará incompleto. Considerar retry.

### 3. Design Director Falha Não-Bloqueante
**Severidade:** Baixa
**Local:** `backend/endpoints/pipeline_orchestrator_service.py:1409-1411`
**Descrição:** Se Design Director falha, pipeline continua sem direção criativa.
```python
except Exception as _dd_err:
    logger.warning(f"[Pipeline] Design Director erro (continuando sem): {_dd_err}")
    state.direcao_criativa = None
```

### 4. Franz/SDR Enqueue Falha Não-Bloqueante
**Severidade:** Baixa
**Local:** `backend/endpoints/pipeline_orchestrator_service.py:2178-2182`
**Descrição:** Se Franz não consegue enfileirar, site é gerado mas outreach não acontece.
```python
except Exception as e:
    logger.warning(f"[Pipeline] Franz enqueue erro (não bloqueia): {e}")
    _sdr_stage_final = "sdr_enqueue_failed"
```
**Nota:** Esta é uma falha não-bloqueante por design - site é gerado mesmo se SDR falhar.

### 5. Banco de Dados SQLite Local (Desenvolvimento)
**Severidade:** Informacional
**Local:** `scripts/pipeline_smoke.py:104-106`
**Descrição:** Em Windows, smoke test pula validação de locks do banco.
```python
if (os.getenv("DATABASE_URL") or "").startswith("sqlite"):
    print("  sqlite local DB ok; stale job SQL skipped")
    return
```

---

## Testes de Integração Faltantes

### 1. Teste de Pipeline Completo com Lead Real
**Prioridade:** Alta
**Descrição:** Executar pipeline completo com um lead real para validar todas as fases.
**Arquivo sugerido:** `tests/integration/test_pipeline_complete_lead.py`

### 2. Teste de Recovery/Checkpoint
**Prioridade:** Alta
**Descrição:** Testar que pipeline retoma corretamente a partir de cada fase usando checkpoint.
**Cobertura atual:** Parcial - `pipeline_checkpoint.py` existe mas não há teste dedicado.

### 3. Teste de Fast-Path (Builder)
**Prioridade:** Média
**Descrição:** Testar que `_builder_fast_path` e `_prompt_agent_flow` funcionam corretamente.
**Verificar:** `backend/services/pipeline_flow_config.py`

### 4. Teste de SDR/Franz Isolado
**Prioridade:** Média
**Descrição:** Testar que Franz/SDR enfileira corretamente após deploy.
**Cobertura atual:** `tests/unit/test_pipeline_sdr_delivery.py` - básico.

### 5. Teste de Qualidade HTML Gate
**Prioridade:** Média
**Descrição:** Testar repair loop com HTML inválido.
**Verificar:** `backend/agents/html_quality_gate.py`

### 6. Teste de Retry em Cada Fase
**Prioridade:** Média
**Descrição:** Testar que retry exponencial funciona para cada fase com falha simulada.

### 7. Teste de Concurrent Pipeline
**Prioridade:** Alta
**Descrição:** Verificar que múltiplos pipelines para mesmo tenant não conflitam.
**Cobertura atual:** `tests/integration/test_job_queue_concurrency.py` - básico.

---

## Contratos Validados pelo Smoke Test

| Contrato | Status | Descrição |
|----------|--------|-----------|
| PRD Sections | OK | `REQUIRED_SECTIONS` garantidas |
| Landing Visual | OK | `check_landing_visual_lock.py` |
| Frontend Canonical | OK | `verify_frontend_canonical.py` |
| Deploy Contract | OK | `check_deploy_contract.py` |
| Phase 6 Contracts | OK | `test_builder_publication_phase6_contract.py` |
| Context Terms | OK | Termos legados não encontrados |

---

## Endpoints Verificados

| Endpoint | Método | Função | Status |
|----------|--------|--------|--------|
| `/api/pipeline/iniciar` | POST | Inicia pipeline | OK |
| `/api/pipeline/status` | GET | Status + fase atual | OK |
| `/api/pipeline/cooldown-status` | GET | Status cooldown | OK |
| `/api/pipeline/stats` | GET | Estatísticas do pipeline | OK |
| `/api/pipeline/parar` | POST | Para pipeline | OK |
| `/api/pipeline/pausar` | POST | Pausa pipeline | OK |
| `/api/pipeline/retomar` | POST | Retoma pipeline | OK |
| `/api/pipeline/cancelar` | POST | Cancela jobs | OK |
| `/api/pipeline/reset` | POST | Reset estado | OK |
| `/api/pipeline/ciclos` | GET | Lista ciclos | OK |

---

## Features PRD Implementadas

| PRD | Status | Implementação |
|-----|--------|---------------|
| PRD #4: Token Tracker | OK | `agents/token_tracker.py` |
| PRD #6: Ledger Pattern | OK | `pipeline_ledger.py` |
| PRD #7: Agent Router | OK | `agent_router.py` |
| PRD #8: PRD Cache | OK | `prd_cache.py` |
| PRD #10: Observability | OK | `observability.py` + spans |
| PRD #11: Memory Tiered | OK | `agent_memory.py` |

---

## Conclusão

O pipeline de geração está **FUNCIONAL** e bem estruturado. Todos os smoke tests passam e a arquitetura demonstra:

1. **Resiliência:** Failures não-bloqueantes em agentes secundários (Jina, Design Director)
2. **Checkpoint:** Sistema de recovery implementado
3. **Paralelização:** Caio + Jina executam em paralelo
4. **Fast-Path:** Builder pode pular agentes de briefing
5. **Qualidade:** HTML quality gate com repair loop
6. **Observabilidade:** Traces, tokens, ledger

**Recomendações:**
1. Adicionar testes de integração para pipeline completo
2. Monitorar taxa de falha do Jina e Keyword Research
3. Considerar retry para fases críticas (não apenas não-bloqueantes)
