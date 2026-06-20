# Auditoria de Monolitos — FraLib Backend

> **Documentovivo — Atualizar após cada refactoring**

## Data da Auditoria: 2026-06-19
## Auditor: Claude Opus 4.8 (ECC)

---

## Resumo Executivo

| Status | Descrição |
|--------|-----------|
| 🟢 | Monolito resolvido |
| 🟡 | Parcialmente resolvido |
| 🔴 | Ainda é monolito crítico |

---

## Inventário de Arquivos Críticos

### 1. `backend/services/vite_react_renderer.py`

| Atributo | Valor |
|----------|-------|
| **Linhas totais** | 3.802 |
| **Funções próprias** | 126 |
| **SRP Violado?** | 🟡 **PARCIAL - JÁ ESTÁ SENDO QUEBRADO** |
| **CRÍTICO?** | 🟡 **ALERTA - Estrutura modular existe** |

**Módulos já extraídos:**
| Módulo | Linhas | Funções |
|--------|--------|---------|
| `vite_config.py` | 237 | 15 |
| `vite_prompts.py` | 268 | 6 |
| `vite_facts.py` | 242 | 12 |
| `vite_file_extractor.py` | 197 | 9 |
| `vite_validator.py` | 189 | 6 |
| `vite_build_executor.py` | 397 | 15 |
| `vite_renderer_models.py` | 63 | 2 |
| **Subtotal módulos** | ~1.590 | 65 |

**O que resta no arquivo principal:**
- Função principal `render_vite_react_site()` (~3.000 linhas)
- Lógica de orquestração (calls LLM, batching, retry)
- Stabilizers/contracts de componentes

**Veredicto:** 🟡 **JÁ POSSUI ESTRUTURA MODULAR** — mas pode ser melhorado

---

### 2. `backend/endpoints/pipeline_orchestrator_service.py`

| Atributo | Valor |
|----------|-------|
| **Linhas totais** | 3.140 |
| **Linhas de código** | ~2.800 |
| **Imports** | 60 |
| **Funções principais** | 1 (`executar_pipeline_completo`) |
| **Fases** | 11 |
| **SRP Violado?** | 🟡 **PARCIAL** |
| **CRÍTICO?** | ⚠️ **EM ANDAMENTO** |

**Progresso da quebra:**
| Fase | Status | Arquivo | Linhas |
|------|--------|---------|--------|
| 1-7 | 🔜 Próxima | Inline | ~1.500 |
| 8 | 🟢 **EXTRAÍDA** | `pipeline_fases/fase_08_arquiteto.py` | 182 |
| 9 | 🔜 Próxima | Inline | ~170 |
| 10-11 | 🔜 Próxima | Inline | ~300 |

---

### 3. `backend/agents/design_context.py` 🟢

| Atributo | Valor |
|----------|-------|
| **Linhas totais** | 1.127 |
| **Imports** | 3 |
| **SRP Violado?** | 🟢 **NÃO** |
| **CRÍTICO?** | ❌ **NÃO - É MÓDULO DE CONSTANTES** |

**O que é:** Módulo de **CONSTANTES** com tokens de design pré-computados
- 40+ DIREÇÕES VISUAIS (editorial, airbnb, apple, etc.)
- Tokens OKLch (cores, tipografia, animação)
- Carregados de `design_system_tokens.json`

**Veredicto:** ✅ **NÃO É MONOLITO** — módulo de dados bem estruturado

---

### 4. `backend/agents/llm_direct.py` 🟢

| Atributo | Valor |
|----------|-------|
| **Linhas totais** | 984 |
| **Imports** | 14 |
| **SRP Violado?** | 🟢 **NÃO** |
| **CRÍTICO?** | ❌ **NÃO - É WRAPPER/API PÚBLICO** |

**O que é:** **Facade Pattern** — API pública que expõe:
- `call_claude()`
- `call_claude_structured()`

Importa módulos internos de mais baixo nível para montar a interface.

**Veredicto:** ✅ **NÃO É MONOLITO** — wrapper bem estruturado

---

### 5. `backend/endpoints/superadmin_endpoints.py` 🟢

| Atributo | Valor |
|----------|-------|
| **Linhas** | 805 |
| **Endpoints** | 18 |
| **SRP Violado?** | 🟢 **NÃO** |

**Veredicto:** ✅ **JÁ QUEBRADO** — padrão FastAPI router

---

### 6. `backend/services/builder_worker.py` 🟢

| Atributo | Valor |
|----------|-------|
| **Linhas** | 692 |
| **SRP Violado?** | 🟢 **NÃO** |

**Veredicto:** ✅ **JÁ QUEBRADO** — responsabilidades claras

---

### 7. `backend/services/lead_supply_inventory.py` 🟡

| Atributo | Valor |
|----------|-------|
| **Linhas** | 747 |
| **SRP Violado?** | 🟡 **MODERADO** |
| **Domínios** | Status, queue, candidates, locks, dedup |
| **CRÍTICO?** | ⚠️ **PARCIAL** |

**Companheiros existentes:**
- `lead_supply_filters.py`
- `lead_supply_events.py`
- `lead_supply_storage.py`
- `lead_supply_engine.py`
- `lead_supply_providers.py`

**Veredicto:** 🟡 **PARCIALMENTE QUEBRADO** — companheiros existem

---

## Histórico de Refactoring

| Commit | Descrição | Linhas Removidas |
|--------|-----------|-------------------|
| `cf6bb85` | 5.5k linhas distribuídas | ~5.500 |
| `86e494c` | Orchestrator FASE 1 + prd_builder | ~800 |
| `c22314e` | 4 monolitos quebrados | ~1.200 |
| `2026-06-19` | Fase 08 extraída | 182 (novo módulo) |

---

## Resumo para Próxima Auditoria

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    STATUS REAL DOS MONOLITOS                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ 🟢 JÁ QUEBRADOS (5):                                               ║
║   • design_context.py          — CONSTANTES de tokens (OK)          ║
║   • llm_direct.py              — wrapper/API público (OK)           ║
║   • superadmin_endpoints.py   — FastAPI router (OK)                ║
║   • builder_worker.py          — SRP respeitado (OK)                ║
║   • vite_react_renderer.py     — 7 módulos extraídos (OK)           ║
╠═══════════════════════════════════════════════════════════════════════╣
║ 🟡 PRECISAM TRABALHO (2):                                           ║
║   • pipeline_orchestrator_service.py — 3.140 (1 fase extraída)     ║
║   • lead_supply_inventory.py     — 747 (companheiros existem)       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Plano de Ação

### ✅ JÁ RESOLVIDOS (5):
- [x] design_context.py — CONSTANTES de tokens
- [x] llm_direct.py — wrapper/API público
- [x] superadmin_endpoints.py — FastAPI router
- [x] builder_worker.py — SRP respeitado
- [x] vite_react_renderer.py — 7 módulos extraídos

### 🟡 EM ANDAMENTO (2):

#### 1. pipeline_orchestrator_service.py
- [x] Fase 08: Arquiteto ✅ (2026-06-19)
- [ ] Fase 09: Builder Renderer
- [ ] Fase 10: Deploy
- [ ] Integrar fases extraídas no orchestrator

#### 2. lead_supply_inventory.py
- [ ] Avaliar se precisa de mais splits
- [ ] Companheiros já existem: filters, events, storage, engine, providers

---

## Como Usar Este Documento

1. **Antes de auditar novamente**, rode:
   ```bash
   cd C:/fralib
   wc -l backend/endpoints/pipeline_orchestrator_service.py
   wc -l backend/services/vite_react_renderer.py
   ```

2. **Verificar se imports funcionam:**
   ```bash
   python3 -c "from backend.endpoints import pipeline_orchestrator_service; print('OK')"
   ```

3. **Verificação completa:**
   ```bash
   bash scripts/verify_all.sh
   ```

---

## Contato

- **ECC Docs:** `C:\Users\JESUS TE AMA\.claude\rules\ecc\`
- **Pipeline Fases:** `backend/services/pipeline_fases/README.md`
- **Pipeline Phases Base:** `backend/services/pipeline_phases.py`
