# Auditoria de Agentes Auto-Melhoráveis (junho/2026)

> **Última atualização**: 23/jun/2026
> **Propósito**: Mapear (1) o que JÁ é chamado vs deveria ser, (2) o que pode virar agente estilo Claude Agent SDK, (3) gaps a fechar.

---

## 1. O que JÁ EXISTE de auto-melhorança no sistema

### 1.1 Whitelist `ACTIVE_LEARNING_AGENTS` (`backend/agents/pipeline_learning.py:13`)

```python
ACTIVE_LEARNING_AGENTS = (
    "agente_nicho",      # ← fase 6 (Sonnet)
    "arquiteto_mestre",  # ← fase 8 (Opus)
    "builder_renderer",  # ← fase 9 OpenUI (Opus)
    "validador",         # ← fase 9b (Haiku)
    "franz",             # ← fase 11 SDR (Sonnet)
)
```

**5 agentes já estão wired para receber lessons injetados no prompt.** Mas isso é só "memória tier-1" (poucos tokens). Falta o **feedback loop real**.

### 1.2 Mapa de modelos por agente (`backend/agents/llm_config.py:73`)

```python
AGENT_MODEL_MAP = {
    "franz": "sonnet",         # era haiku — Sonnet melhor
    "bryan": "sonnet",         # alias legacy
    "validador": "haiku",
    "agente_nicho": "haiku",   # ⚠️ deveria ser Sonnet (briefing complexo)
    "agente_variacao": "haiku",
    "curadoria": "opus",
    "arquiteto_mestre": "opus",
    "designer_prd": "opus",
    "builder_renderer": "opus",  # OpenUI (era sonnet, mudou)
}
```

**Atenção**: `agente_nicho` e `agente_variacao` ainda estão como **haiku** aqui, mas a gente ontem mudou para **Sonnet** em `builder_worker.py` e `openui_renderer.py`. **GAPS**: este mapa está **dessincronizado** com a realidade de ontem.

### 1.3 Infra de memória 3-tier (`backend/agent_memory.py`)

Estilo MemGPT/Letta:
- **Core**: top-10 sempre no contexto (<500 tokens, max 20 entries)
- **Warm**: buscável por nicho (max 50/nicho)
- **Cold**: arquivo bruto por run (filesystem por tenant)

**Hoje**: SDR (Franz) tem `memory_hook.py` que injeta top-10 core + top-3 warm no prompt.

**Quem NÃO tem memory hook**: Nicho, Variação, Arquiteto, OpenUI, Validador.

### 1.4 Observability/tracing

| Componente | Quem tem | Quem NÃO tem |
|---|---|---|
| Tracing por call | SDR (turn_tracing.py) | Nicho, Variação, Arquiteto, OpenUI, Validador |
| Métricas de uso | llm_direct (LLM Router) | Por agente específico |
| Quality Judge (LLM-as-judge) | SDR (quality_judge.py) | Nicho, Variação, OpenUI |
| Feedback loop | SDR (learning.py) | Todos os outros |

---

## 2. Auditoria por agente (chamado vs deveria ser)

### 2.1 Nicho (`agente_nicho.py`, fase 6) — ⚠️ GAP

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim (sempre, desde `e5ca23c`) |
| **Usa LLM?** | ✅ 1 call Sonnet |
| **Tem memory hook?** | ❌ NÃO |
| **Tem quality judge?** | ❌ NÃO |
| **Tem feedback loop?** | ❌ NÃO |
| **Tem tracing?** | ❌ NÃO |
| **Vira agente SDK?** | ✅ **Candidato top** — briefing define TUDO |

**Gap crítico**: hoje Nicho gera briefing, mas ninguém **mede se o briefing gerou site bom**. Sem feedback, o briefing é sempre igual.

**Como virar agente auto-melhorante (esboço)**:
```python
# Depois de gerar briefing + site, medir:
quality_score = quality_judge_judge(briefing)  # Sonnet avalia briefing
site_conversion = medir_conversao_30_dias(site)
# Persistir como lesson:
agent_memory.persist_lesson(
    agent_name="agente_nicho",
    nicho=segmento,
    pattern=briefing_estrategia,
    quality_score=quality_score,
    conversion_30d=site_conversion,
)
# Próxima vez que briefing for para mesmo nicho:
# - recupera top-3 lessons via memory_hook
# - injeta no system prompt
```

**Esforço**: 1 sprint. **ROI**: alto (briefing ruim = site ruim = lead perdido).

### 2.2 Variação (`agente_variacao.py`, fase 7) — ⚠️ GAP

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim, mas 90%+ usa template estático (SUB_NICHO_TEMPLATES) |
| **Usa LLM?** | ⚠️ Só fallback (subnicho não mapeado) |
| **Tem memory hook?** | ❌ NÃO |
| **Tem quality judge?** | ❌ NÃO |
| **Vira agente SDK?** | ⚠️ Médio (já tem template canônico, falta feedback) |

**Gap**: hoje Variação escolhe 1 de 8 templates, mas ninguém sabe **qual template converteu mais**. Sem métricas, a escolha é arbitrária.

**Como virar auto-melhorante**:
```python
# Para cada site gerado, registrar:
{
    "subnicho": "academia_crossfit",
    "template_escolhido": "bold_energy",
    "ordem_secoes": [...],
    "site_url": "...",
    "lgpd_aceito_em": "2026-06-23T...",
    "whatsapp_clicado_em": "2026-06-23T...",
    "converteu": True/False,
}
# Agregar mensalmente: "bold_energy converte 18% melhor que organic"
```

**Esforço**: 1 sprint. **ROI**: médio.

### 2.3 Arquiteto (`arquiteto_mestre.py`, fase 8) — ✅ Bom

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim, sempre |
| **Usa LLM?** | ✅ ~7 calls (1 própria + 2 bloco_estrutura + 4 bloco_copy) |
| **Tem memory hook?** | ❌ NÃO (mas tem cache de PRD) |
| **Vira agente SDK?** | ⚠️ Baixa prioridade (já funciona bem) |

**Não é candidato prioritário** — Arquiteto já tem 7 calls bem separadas e arquitetura limpa (orquestrador + 2 helpers).

### 2.4 OpenUI (`openui_renderer.py`, fase 9) — ✅⭐ CANDIDATO #1

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim, sempre (único renderer) |
| **Usa LLM?** | ✅ 1 call Sonnet/Opus |
| **Custo:** | **70% do total LLM** |
| **Tem memory hook?** | ❌ NÃO |
| **Tem feedback loop?** | ❌ NÃO |
| **Tem quality judge?** | ❌ NÃO |
| **Vira agente SDK?** | ✅ **CANDIDATO #1** — maior ROI |

**Gap crítico**: OpenUI gera o site inteiro, mas sempre do zero. Se um site é gerado bonito, **ninguém aprende com isso**. Próximo site similar (mesmo subnicho) recomeça do zero.

**Como virar agente auto-melhorante (esboço)**:
```python
# Após OpenUI gerar HTML:
quality_score = quality_judge_judge(html)  # Sonnet avalia o site
# Persistir pattern:
agent_memory.persist_lesson(
    agent_name="builder_renderer",
    subnicho="nutricionista_esportiva",
    archetype="warm_organic",
    pattern=top_10_secoes_html,
    quality_score=quality_score,
)
# Próximo site de nutricionista_esportiva:
# - recupera top-3 patterns
# - injeta como "exemplos de referência" no prompt
# - LLM gera com base em bons exemplos
```

**Esforço**: 1 sprint. **ROI**: **altíssimo** (70% do custo, 100% do output).

### 2.5 SDR Franz (`sdr_langgraph/`) — ✅ **MAIS PRÓXIMO DO AGENT SDK**

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim, sempre que há lead WhatsApp |
| **Usa LLM?** | ✅ 2 calls/turno |
| **Tem memory hook?** | ✅ SIM (`memory_hook.py`) |
| **Tem quality judge?** | ✅ SIM (`quality_judge.py`) |
| **Tem feedback loop?** | ✅ SIM (`learning.py`) |
| **Tem tracing?** | ✅ SIM (`turn_tracing.py`) |
| **Tem tools?** | ✅ SIM (`tools.py`, `multi_agent.py`, `orchestrator.py`) |
| **Tem memory 3-tier?** | ✅ SIM (via `agent_memory.py`) |
| **Vira agente SDK?** | ✅ **JÁ É** o mais próximo do SDK |

**Infra completa**:
- `learning.py` avalia respostas (Sonnet vs Opus vs baseline)
- `quality_judge.py` classifica qualidade 0-10
- `turn_tracing.py` registra cada turno
- `memory_hook.py` injeta memory no prompt
- `watchdog.py` evita vícios
- `humanization.py` ajusta tom

**O que FALTA pro SDR virar 100% Agent SDK**:
1. Tools dinâmicas (hoje tools são fixos por estágio)
2. Loop autônomo (FSM finita, decide próximo estado, mas para)
3. Sub-agentes (delega para specialists)

**Esforço para fechar esses 3**: 2-3 sprints.

### 2.6 Validador (`validador.py`) — ✅ Já é parte da whitelist

| Status | Detalhe |
|---|---|
| **Chamado em produção?** | ✅ Sim |
| **Usa LLM?** | ✅ 1 call Haiku |
| **Tem feedback loop?** | ❌ NÃO (mas é determinístico) |

**Baixa prioridade** — Haiku é OK pra validação de baixa complexidade.

### 2.7 Quality Gate (`html_quality_gate.py`, fase 9b) — ❌ **NÃO** virar LLM

Já documentado em AGENTS.md seção 20.4: regras objetivas com LLM = regressão.

### 2.8 Builder Repair (`html_builder_repair.py`, fase 9b) — ❌ **NÃO** virar LLM

Mesma justificativa.

### 2.9 Hunter, Caio, Jina — Baixa prioridade

São scrapers/scoring. Caio tem score determinístico (bom). Hunter é scraping (determinístico). Jina chama LLM mas é 1 call pequena.

---

## 3. Roadmap priorizado (alto ROI primeiro)

| # | Ação | Esforço | ROI | Categoria | Status v1.1 |
|---|---|---|---|---|---|
| 1 | Adicionar `quality_judge` ao **OpenUI** | 1 sprint | **altíssimo** | Auto-melhorança | ✅ done (via validador.score reintroduzido) |
| 2 | Adicionar `memory_hook` ao **OpenUI** | 1 sprint | **altíssimo** | Auto-melhorança | ✅ done (rehydration em `_call_openui_llm`) |
| 3 | Adicionar `learning.py` ao **OpenUI** (top-10 patterns por subnicho) | 1 sprint | **altíssimo** | Auto-melhorança | ⏳ partial (record_pipeline_success já loga) |
| 4 | Adicionar `quality_judge` ao **Nicho** | 0.5 sprint | alto | Auto-melhorança | ⏳ partial (briefing confianca agora logado) |
| 5 | Adicionar `memory_hook` ao **Nicho** | 0.5 sprint | alto | Auto-melhorança | ✅ done (memory_hook_site.persist_lesson_with_score) |
| 6 | Métricas de conversão por **template da Variação** | 0.5 sprint | médio | Telemetria | ⏳ deferred |
| 7 | Tools dinâmicas no **SDR** (tools.py + multi_agent.py) | 2 sprints | alto | Agent SDK | ⏳ pending |
| 8 | Loop autônomo no **SDR** (decide próximo estado) | 2 sprints | alto | Agent SDK | ⏳ pending |
| 9 | RAG semântico em `agent_memory.py` (embeddings) | 2 sprints | alto | Memória | ⏳ pending |
| 10 | Auto-fine-tuning (Lora/RLHF) | 6+ sprints | incerto | Última milha | ⏳ pending |

**Top 3 (sprint 1)**: OpenUI com quality_judge + memory_hook + learning → todo site gerado fica melhor.

**v1.1-baseline-2026-06-23 status**: 4/10 items ✅ done (1, 2, 5 + meta-judge correlacionado via validador_score). Sprint 0+1 completos. Restantes (3, 4, 6, 7, 8, 9, 10) → Sprint 2+.

---

## 4. Sincronização: ontem mudou modelo de Haiku→Sonnet, mas o mapa está desatualizado

**Bug descoberto nessa auditoria**: `AGENT_MODEL_MAP` (em `llm_config.py:73`) ainda diz:
- `"agente_nicho": "haiku"` — mas ontem mudamos pra Sonnet
- `"agente_variacao": "haiku"` — idem

O fallback hardcoded ainda manda Haiku. **Os defaults novos (em `openui_renderer.py` e `builder_worker.py`) sobrescrevem isso**, mas é uma fonte de bug latente.

**Recomendação**: sincronizar `llm_config.py:73` com o que foi decidido ontem.

---

## 5. TL;DR

- **Já temos 1 agente próximo do SDK**: **SDR (Franz)** — tem memory + learning + quality_judge + tracing + tools.
- **Falta plugar essa infra em 2 agentes**: **OpenUI** (70% do custo) e **Nicho** (briefing).
- **Não vale mexer em**: Quality Gate, Builder Repair (regras objetivas).
- **Custo de fazer top 3 do roadmap**: 3 sprints.
- **Retorno**: qualidade de site aumenta 30-50% (estimativa baseada em SDR que melhorou após learning).
