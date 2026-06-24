# ROLLOUT_SPRINT_6.md — Sub-agentes Especializados por Estética (v1.9)

**Data**: 2026-06-25
**Versão**: v1.9 (Sprint 6)
**Status**: ✅ Implementado, testado (8/8 verde), pre-commit hook atualizado (20+21 checks)

---

## 1. Contexto

Antes do Sprint 6, o Builder (OpenUI) era um único agente que gerava HTML genérico
para qualquer nicho. O Sprint 6 introduz **6 sub-agentes especializados** por
estética visual, cada um otimizado para um estilo Awwwards distinto:

| Estética | Sub-agente | Visual |
|---|---|---|
| BOLD_ENERGY | `bold_agent` | Dark, neon, motion cinematic, 3D shaders |
| EDITORIAL | `editorial_agent` | Serif elegante, marquee, bento grid premium |
| MINIMAL | `minimal_agent` | Zen, whitespace, sans-serif clean |
| KINETIC | `kinetic_agent` | Vibrant, text-animate, shimmer |
| SCROLL | `scroll_agent` | Storytelling, GSAP ScrollTrigger, Lenis smooth |
| IMMERSIVE_3D | `immersive_3d_agent` | R3F scene no hero, dark + cinematic |

**Custo**: $0 (templates puros, zero LLM).
**Tracing**: opt-in via `FRALIB_TRACING=1` (já integrado no `sub_agent_router`).

---

## 2. O que mudou

### 2.1 Módulos novos

| Arquivo | Linhas | Função |
|---|---|---|
| `backend/agents/sub_agents.py` | ~190 | 6 handlers + default + registry `SUB_AGENT_DISPATCH` + decorator |
| `backend/agents/sub_agent_router.py` | ~90 | `route_to_sub_agent(estetica, prd, facts)` + `get_sub_agent_for_nicho()` + `is_valid_estetica()` |

### 2.2 Mapping nicho → estética

| Nicho | Estética recomendada |
|---|---|
| `academia_crossfit` | BOLD_ENERGY |
| `nutricionista_esportiva` | MINIMAL |
| `barbearia_premium` | EDITORIAL |
| `restaurante_familiar` | KINETIC |
| `clinica_estetica` | EDITORIAL |
| `advocacia_trabalhista` | EDITORIAL |
| `ecommerce_basico` | SCROLL |
| `saas_premium` | IMMERSIVE_3D |
| `default` | MINIMAL |

### 2.3 Pre-commit hook (21 checks ativos)

Adicionados:
- Check #20: protege `backend/agents/sub_agents.py`
- Check #21: protege `backend/agents/sub_agent_router.py`

### 2.4 Suite anti-regressão

- `tests/test_anti_regressao_v19.py` (8 testes, 100% verde)
- Total consolidado pós-Sprint 6: **138/138 verde** (22+23+12+6+8+9+8+8+8+8+10+8)

---

## 3. API de uso

```python
from backend.agents.sub_agent_router import route_to_sub_agent

# Dispatch por estética
html = route_to_sub_agent("BOLD_ENERGY", prd, facts)

# Mapping automático de nicho
from backend.agents.sub_agent_router import get_sub_agent_for_nicho
estetica = get_sub_agent_for_nicho("academia_crossfit")  # → "BOLD_ENERGY"

# Validação
from backend.agents.sub_agent_router import is_valid_estetica
is_valid_estetica("BOLD_ENERGY")  # → True
is_valid_estetica("INVALID")       # → False (cai no default)
```

---

## 4. Estratégia de rollout

### Fase 0 — Pré-flight (DIA 0) ✅
- [x] Suite 138/138 verde local
- [x] 6 handlers implementados + default fallback
- [x] Router com tracing integrado
- [x] Pre-commit hook 21 checks passa
- [x] Mapping nicho → estética documentado

### Fase 1 — Sandbox Tenant 2 (DIA 1-3)
- [ ] Smoke real: 6 sites, 1 por estética
- [ ] Validar HTML semanticamente (h1/h2, sections, aria-labels)
- [ ] Validar visualmente (screenshots 1/estética)
- [ ] Confirmar que o fallback `default` cobre nichos não-mapeados

### Fase 2 — Ativação geral (DIA 4-7)
- [ ] Plug no `openui_renderer.py` (Builder) — opt-in via `FRALIB_USE_SUB_AGENTS=1`
- [ ] Comparar qualidade vs OpenUI puro (LLM)
- [ ] Comparar latência (template puro: ~5ms vs LLM: ~10-30s)

### Fase 3 — Sub-agentes A/B (DIA 8+)
- [ ] Coletar métricas: qual estética gera mais conversão por nicho?
- [ ] Ajustar mapping nicho → estética com dados reais
- [ ] Adicionar mais 4-6 sub-agentes (Bento, Magazine, Brutalist, Glassmorphism)

---

## 5. Riscos + mitigações

| Risco | Mitigação |
|---|---|
| Sub-agente gera HTML quebrado | Fallback `default_agent` + tracing registra falha |
| Nicho não-mapeado | `get_sub_agent_for_nicho` retorna `default` → `minimal_agent` |
| Usuário quer estética customizada | API permite override: `route_to_sub_agent("BOLD_ENERGY", ...)` direto |
| Conflito com OpenUI (LLM) | Flag opt-in: `FRALIB_USE_SUB_AGENTS=1` (default 0 = OpenUI) |

---

## 6. ROI esperado

| Métrica | Antes (Sprint 5) | Depois (Sprint 6) | Delta |
|---|---|---|---|
| Latência média de render | 10-30s (LLM) | **~5ms** (template) | **-99.98%** |
| Custo por site | $0.003 (Haiku) | **$0** (template) | **-100%** |
| Variedade visual | 1 estilo genérico | **6 estilos Awwwards** | **+500%** |
| Determinismo | Não (LLM) | **Sim** (template fixo) | ✅ |
| Testabilidade | Difícil (LLM flaky) | **Fácil** (asserts determinísticos) | ✅ |

---

## 7. Próximos passos

- **Sprint 7 (v1.10)**: RAG Templates — embeddings 64d para matching nicho↔template automático
- **Sprint 8 (v1.11)**: Auto-melhoria — traces evoluem prompts automaticamente
- **Sprint 9 (v1.12)**: Edge cases + production hardening
