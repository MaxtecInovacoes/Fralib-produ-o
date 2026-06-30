# AUDITORIA INDEPENDENTE DA FRALIB
## Versão CORRIGIDA - Verificada diretamente no código

> **IMPORTANTE**: Esta auditoria foi feita verificando o código-fonte diretamente,
> sem considerar auditorias anteriores. Foram encontradas **discrepâncias significativas**
> entre o que foi dito antes e o que o código REAL diz.

---

## 🔴 DESCOBERTA CRUCIAL #1: Motor Padrão

### O QUE O CÓDIGO DIZ (Verificado):

**Arquivo: `backend/services/builder_worker.py:41`**
```python
_CANONICAL_BUILDER_ENGINE = "vite_react"
```

**Arquivo: `backend/services/builder_worker.py:44-51`**
```python
def _apply_canonical_vite_react_runtime_defaults() -> None:
    """Align the official builder runtime with the approved cinematic preview path."""
    os.environ.setdefault("FRALIB_BUILDER_ENGINE", "vite_react")
    os.environ.setdefault("FRALIB_VITE_LLM_POLICY", "none")
    os.environ.setdefault("FRALIB_VITE_CINEMATIC_STUDIO", "1")
    os.environ.setdefault("FRALIB_VITE_DISABLE_STUDIO_FALLBACK", "1")
    os.environ.setdefault("FRALIB_ALLOW_OPENUI_FALLBACK", "0")
```

### ✅ VERDADE:

| Motor | Status Real |
|-------|-------------|
| **Vite/React** | ✅ PADRÃO (desde Sprint 12.9) |
| **OpenUI** | ⚠️ FALLBACK (desabilitado em produção!) |

**OpenUI SÓ roda se:**
- `FRALIB_ALLOW_OPENUI_FALLBACK=1`
- E Vite/React falhar

---

## 🔴 DESCOBERTA CRUCIAL #2: Política LLM

### O QUE O CÓDIGO DIZ:

**Arquivo: `backend/services/builder_worker.py:47`**
```python
os.environ.setdefault("FRALIB_VITE_LLM_POLICY", "none")
```

**Arquivo: `backend/services/vite_react_renderer.py:410-420`**
```python
def _get_llm_policy() -> str:
    raw = os.getenv("FRALIB_VITE_LLM_POLICY", "none").strip().lower().replace("-", "_")
```

### ✅ POLÍTICAS DISPONÍVEIS:

| Política | LLM | Custo | Descrição |
|----------|-----|-------|-----------|
| `none` | ❌ ZERO | $0 | Studio determinístico (padrão) |
| `copy_only` | ✅ Mínimo | ~$0.001 | LLM só para texto |
| `creative_plan` | ✅ Médio | ~$0.005 | LLM para copy + planejamento |

### ✅ VERDADE:

**O sistema PADRÃO é ZERO LLM no builder!**

---

## 🟡 DESCOBERTA #3: Estrutura de Arquivos

### ARQUIVOS DO MOTOR (Verificados):

```
backend/services/
├── vite_react_renderer.py      # ⭐ ORQUESTRADOR PRINCIPAL (4,800+ linhas)
├── vite_config.py              # Configurações
├── vite_prompts.py             # Prompts
├── vite_facts.py               # Facts extraction
├── vite_file_extractor.py      # Extração de arquivos
├── vite_validator.py           # Validação
├── vite_build_executor.py      # Execução do build
├── vite_modules.py             # Definições de módulos
├── vite_renderer_models.py     # Modelos de dados
├── vite_config_helpers.py      # Helpers de config
├── vite_block_registry.py      # Registry de blocos
├── vite_theme_guard.py         # Guard de tema
├── vite_templates.py           # Templates
├── vite_visual_lanes.py        # Lanes visuais
├── vite_prompts.py             # Prompts
│
├── openui_renderer.py          # ⚠️ FALLBACK (não é padrão!)
├── template_loader.py          # 🆕 Templates (alternativa zero-LLM)
│
├── builder_worker.py           # ⭐ ORQUESTRADOR DO BUILDER
├── html_quality_gate.py        # ⭐ VALIDAÇÃO (determinístico)
├── lgpd_injector.py           # Injeção LGPD
└── html_sanitizer.py          # Sanitização
```

### PROPORÇÃO REAL:

| Categoria | Qtd Arquivos | Status |
|-----------|--------------|--------|
| Vite/React (ativo) | ~15 | ✅ PADRÃO |
| OpenUI (ativo) | ~3 | ⚠️ FALLBACK |
| Template (ativo) | ~1 | 🆕 ZERO-LLM |
| Vite "órfão"? | ~0 | ❌ NÃO - É PADRÃO! |

---

## 🟡 DESCOBERTA #4: Pipeline 11 Fases

### O QUE O CÓDIGO DIZ:

**Arquivo: `backend/services/pipeline_phases.py:10-49`**

```python
FASE_1_HUNTER = 1          # "Buscando leads..."
FASE_2_CURADORIA = 2       # "Qualificando lead..." (Caio)
FASE_3_JINA = 3            # "Pesquisa de mercado..."
FASE_4_INTELIGENCIA = 4    # "Analisando concorrência..."
FASE_5_FOTOS = 5           # "Baixando fotos..."
FASE_6_NICHO = 6           # "Analisando nicho..."
FASE_7_VARIACAO = 7        # "Definindo variação estrutural..."
FASE_8_ARQUITETO = 8       # "Arquitetando site..."
FASE_9_BUILDER = 9         # "Gerando site no Builder..."
FASE_10_DEPLOY = 10        # "Publicando site..."
FASE_11_FRANZ = 11         # "Enviando contato..."

TOTAL_FASES = 11
```

### FLUXO REAL:

```
[1] HUNTER ─────► [2] CAIO ─────► [3] JINA ─────► [4] INTELIGÊNCIA
      │               │               │                │
      ▼               ▼               ▼                ▼
  Google Maps    Scoring LLM     Web Scraping    Consolidação
  (scraper)     (Haiku?)       + LLM Haiku       (dados)
                                                          │
[5] FOTOS ───────────────────────────────────────────────┘
      │
      ▼
  Unsplash/Pexels
  (API)
      │
      ▼
[6] NICHO ─────► [7] VARIAÇÃO ─────► [8] ARQUITETO
      │               │                   │
      ▼               ▼                   ▼
  Agente Nicho    Variação 4-eixos   DesignerPRD
  (Sonnet)       (determinístico)     (Sonnet)
                                          │
                                          ▼
                              [9] BUILDER ─────► [10] DEPLOY
                                   │                │
                                   ▼                ▼
                            Vite/React ou      git push
                            OpenUI (fallback)   post-receive
                                   │                │
                                   ▼                ▼
                              Quality Gate      Published site
                              (determinístico)      │
                                                  ▼
                                           [11] FRANZ
                                               WhatsApp
```

---

## 🟢 VERIFICAÇÕES DE DEPENDÊNCIA

### Quem IMPORTA o Vite/React?

```bash
# Verificado via grep:
backend/services/builder_worker.py:395
    from backend.services.vite_react_renderer import render_vite_react_site
```

**Resultado:** Só o `builder_worker.py` importa Vite/React diretamente.

### Quem IMPORTA o OpenUI?

```bash
# Verificado via grep:
backend/services/builder_worker.py:335
    from services.openui_renderer import render_with_template
backend/services/builder_worker.py:351
    from services.openui_renderer import render_openui_site
```

**Resultado:** Só o `builder_worker.py` importa OpenUI.

### Quem IMPORTA o Builder Worker?

```bash
# Verificado via grep:
backend/endpoints/pipeline_orchestrator_service.py
backend/endpoints/pipeline_phase_helpers.py
```

**Resultado:** Só 2 arquivos - o orquestrador e helpers.

---

## 🔵 RESUMO: O QUE É REALMENTE USADO

### MOTOR DE GERAÇÃO (FASE 9):

| Arquivo | Uso Real | Prioridade |
|---------|----------|------------|
| `vite_react_renderer.py` | ✅ PADRÃO | 1ª |
| `openui_renderer.py` | ⚠️ FALLBACK | 2ª |
| `template_loader.py` | 🆕 ALTERNATIVA | 3ª |

### PIPELINE ORQUESTRADOR:

| Arquivo | Uso Real |
|---------|----------|
| `pipeline_orchestrator_service.py` | ✅ ORQUESTRADOR PRINCIPAL |
| `pipeline_execution_core.py` | ✅ EXECUÇÃO CORE |
| `pipeline_phase_helpers.py` | ✅ HELPERS DE FASE |
| `pipeline_executors.py` | ✅ EXECUTORES DE FASE |
| `pipeline_phases.py` | ✅ CONSTANTES |

### QUALITY GATE:

| Arquivo | Uso Real |
|---------|----------|
| `html_quality_gate.py` | ✅ VALIDAÇÃO (determinístico) |
| `html_contract_validator.py` | ✅ CONTRATOS |
| `html_media_validator.py` | ✅ MÍDIA |
| `html_content_validator.py` | ✅ CONTEÚDO |
| `html_phase6_repair.py` | ✅ REPAROS |
| `html_builder_repair.py` | ✅ REPAROS |

---

## ⚠️ DISCREPÂNCIAS ENCONTRADAS

### Auditoria Anterior vs Realidade:

| Afirmação Anterior | Realidade |
|--------------------|-----------|
| "OpenUI é o PADRÃO" | ❌ **ERRADO!** Vite/React é o PADRÃO |
| "OpenUI gera 70% do custo" | ❌ **ERRADO!** Vite/React com `none` é ZERO custo |
| "Vite/React é LEGADO" | ❌ **ERRADO!** É o motor CANÔNICO |
| "14 arquivos Vite órfãos" | ❌ **ERRADO!** São o sistema PADRÃO |

---

## ✅ CONCLUSÃO

### SISTEMA REAL:

1. **Motor Padrão:** Vite/React (`FRALIB_BUILDER_ENGINE=vite_react`)
2. **Política LLM:** `none` (ZERO custo por padrão!)
3. **Pipeline:** 11 fases coordenadas pelo `pipeline_orchestrator_service.py`
4. **Validação:** Quality Gate determinístico (sem LLM)

### CUSTO REAL POR SITE:

| Etapa | LLM | Custo Estimado |
|-------|-----|----------------|
| Fase 2 (Caio) | Haiku | ~$0.001 |
| Fase 3 (Jina) | Haiku | ~$0.002 |
| Fase 6 (Nicho) | Sonnet | ~$0.005 |
| Fase 8 (Arquiteto) | Sonnet | ~$0.020 |
| Fase 9 (Builder) | NENHUM (padrão!) | $0 |
| **TOTAL** | | **~$0.028** |

---

## 📋 AÇÕES NECESSÁRIAS

1. **CORRIGIR DOCUMENTAÇÃO**: CLAUDE.md e AGENTS.md podem estar desatualizados
2. **VERIFICAR openui_contracts.py**: Se OpenUI é fallback, os contratos ainda fazem sentido?
3. **AUDITAR Testes**: Verificar se existem testes para Vite/React e OpenUI
4. **LIMPAR** arquivos órfãos REAIS (se existirem)
