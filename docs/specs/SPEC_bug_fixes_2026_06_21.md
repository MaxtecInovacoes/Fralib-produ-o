# 📋 SPEC: Correção dos 2 Bugs Críticos (Tenant 2 e Tenant 31)

**Data:** 2026-06-21
**Autor:** ECC Loop
**Status:** Aprovado

---

## 🎯 OBJETIVO (O QUÊ e PORQUÊ)

### O que construir:
Corrigir 2 bugs críticos que geram 148 falhas abertas (89 Tenant 2 + 59 Tenant 31) e adicionar testes que impedem regressão.

### Por que:
- Tenant 2: 8 falhas/hora de `ImportError: _enqueue_caio` (8x/hora martelando)
- Tenant 31: 10 falhas/hora de `Pydantic ValidationError: LeadQualificado`
- Total: ~18 falhas/hora = **432 falhas/dia** se não corrigir
- Sistema de alertas já emite email (mas ninguém olha)
- Histórico cresce infinitamente até limpeza (7d)

---

## ✅ CRITÉRIOS DE ACEITE

| # | Critério | Métrica | Como medir |
|---|----------|---------|------------|
| 1 | Bug #1 corrigido | 0 ocorrências em produção (1h) | `grep _enqueue_caio em pipeline_failures recentes` |
| 2 | Bug #2 corrigido | 0 ocorrências em produção (1h) | `grep "Input should be a valid" em pipeline_failures recentes` |
| 3 | Testes bug verdes | 19/19 PASS | `python tests/bugs/run_bug_tests.py` |
| 4 | Suite completa | 141/141 PASS | 122 (existente) + 19 (novos) |
| 5 | API não quebrou | /health 200 OK | `curl http://localhost:8000/health` |
| 6 | Tenant 2 funciona | Consegue processar lead | Trigger manual via admin |
| 7 | Tenant 31 funciona | Consegue reprocessar lead | Trigger manual via admin |
| 8 | Sem regressão 24h | Bugs não voltam | Query SQL após 24h |

---

## 🚫 FORA DE ESCOPO

- ❌ Refatorar `agente1_hunter_v2.py` (fonte de leads, tem validação prévia)
- ❌ Limpar 148 falhas antigas (são histórico, importante manter)
- ❌ Adicionar Prometheus/Loki (decisão pausada com gatilho)
- ❌ Mover `_enqueue_caio` para `lead_supply_common.py` (refator maior, próxima sprint)

---

## 🏗️ RESTRIÇÕES TÉCNICAS

| Restrição | Valor | Razão |
|-----------|-------|-------|
| Não mudar schema | apenas código Python | Rollback seguro |
| Não mudar comportamento existente | só adiciona fallback | LeadRaw válido continua igual |
| Suite deve passar | 141/141 | Sem regressão |
| Tempo de correção | < 5 min por arquivo | Bug simples |
| Rollback | < 30s via git revert | Segurança |

---

## 📐 ARQUITETURA

### Bug #1: Import errado (1 linha)

```
ANTES (quebrado):
backend/services/lead_supply_providers/hunter.py
  linha 71: _enqueue_caio(db, tenant_id, inv_id)  # função NÃO importada
  linha 15: from ...lead_supply_storage import _enqueue_caio  # módulo errado

DEPOIS (correto):
backend/services/lead_supply_providers/hunter.py
  linha 15: from backend.services.lead_supply_inventory import _enqueue_caio
  linha 71: _enqueue_caio(db, tenant_id, inv_id)  # OK
```

### Bug #2: LeadQualificado sem fallback (2 lugares)

```
ANTES (quebrado):
backend/endpoints/pipeline_orchestrator_service.py:2893
  _lead_qualificado = LeadQualificado(lead=lead_raw, ...)  # falha se lead_raw=None
backend/endpoints/pipeline_lead_flow_helpers.py:288
  state.lead_obj = LeadQualificado(lead=lead_raw, ...)  # mesmo problema

DEPOIS (defensivo):
  _lead_qualificado = safe_qualificar(lead_raw, lead_dict, log_fn=_log)  # nunca falha
  state.lead_obj = safe_qualificar(lead_raw, lead_dict, log_fn=_log)
```

---

## 🧪 TASKS

### Task 1: Spec (este arquivo) ✅

### Task 2: Correção código (paralelo)
- [ ] Bug #1: 1 linha em `lead_supply_providers/hunter.py`
- [ ] Bug #2a: 7 linhas em `pipeline_orchestrator_service.py:2893`
- [ ] Bug #2b: 7 linhas em `pipeline_lead_flow_helpers.py:288`
- **Verde:** grep pelos 2 padrões em `pipeline_failures` retorna 0

### Task 3: Testes (verde)
- [ ] `tests/bugs/test_bug_enqueue_caio.py` (5 testes)
- [ ] `tests/bugs/test_bug_lead_qualificado.py` (8 testes)
- [ ] `tests/bugs/test_regression_tenant_failures.py` (6 testes)
- [ ] `tests/bugs/run_bug_tests.py` (runner)
- **Verde:** `python run_bug_tests.py` retorna 19/19 PASS

### Task 4: Deploy + validação
- [ ] Commit + push + pull VPS
- [ ] Reiniciar fralib-api fralib-worker
- [ ] Verificar /health
- [ ] Aguardar 1h
- [ ] Query SQL para confirmar 0 bugs novos
- **Verde:** query retorna 0

---

## ⚠️ RISCOS + MITIGAÇÃO

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Import errado quebra hunter | Baixa | Médio | safe_qualificar já tem try/except |
| safe_qualificar muda dados | Baixa | Alto | Helper é read-only (só transforma) |
| Tenant 2 perde leads | Baixa | Médio | try/except em volta da chamada |
| Testes flaky | Baixa | Baixo | Tests com mocks (sem DB real) |
| Deploy quebra API | Baixa | Alto | Commit pequeno + verificação imediata |

---

## 🛡️ ROLLBACK

```bash
git revert HEAD
git push origin master
ssh root@187.77.37.72 "cd /root/fralib && git pull && systemctl restart fralib-api fralib-worker"
# Volta em 30 segundos
```

---

## 🎯 VERIFICAÇÃO

```bash
# 1. Testes
python tests/bugs/run_bug_tests.py
# 2. Deploy
ssh root@187.77.37.72 "cd /root/fralib && git pull && systemctl restart fralib-api"
# 3. Verificar
curl http://localhost:8000/health
# 4. Aguardar 1h
# 5. Query SQL
sudo -u postgres psql -p 5433 -d fralib_db -c "
  SELECT COUNT(*) FROM pipeline_failures
  WHERE criado_em > NOW() - INTERVAL '1 hour'
    AND (erro_tecnico LIKE '%_enqueue_caio%'
         OR erro_tecnico LIKE '%Input should be a valid%');"
# Esperado: 0
```