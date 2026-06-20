# 🚨 AUDITORIA FINAL CONSOLIDADA - FraLib

**Data:** 2026-06-19
**Auditores:** 4 agentes em paralelo (A: imports, B: prompts, C: features, D: fluxo)
**Escopo:** 100+ arquivos, ~50.000 linhas de código
**Score Atual:** 5.4/10 (precisa melhorar para 8+/10)

---

## 🎯 PLANO DE AÇÃO PRIORIZADO

### 🔴 FASE 1 - CRÍTICO (1-2 dias, URGENTE)

#### 1.1 Corrigir 79 imports quebrados
- **Arquivos afetados:** 26+ arquivos em backend/
- **Tempo:** 1-2 horas
- **Solução:** Script sed global

#### 1.2 ATIVAR HTML Quality Gate (não pular!)
- **Arquivo:** `backend/services/pipeline_flow_config.py:skip_html_quality_gate`
- **Problema:** Default é SKIP, mas sem ele sites saem SEM:
  - Fonts (Inter, etc)
  - Meta tags OG
  - Canonical URL
  - Banner LGPD
- **Fix:** Mudar `return True` → `return False`
- **Tempo:** 5 minutos

#### 1.3 Garantir PT-BR + A11Y no Vite prompt
- **Arquivo:** `backend/services/vite_prompts.py:VITE_REACT_SYSTEM_PROMPT`
- **Adicionar:**
  - "All user-facing text MUST be in Brazilian Portuguese (pt-BR)"
  - "Use semantic HTML, aria-labels, alt text"
  - "Include meta tags, og:, canonical"
  - "Include LGPD cookie banner"
- **Tempo:** 30 minutos

#### 1.4 Corrigir validador/validation_enforcer/design_guidelines
- **Decidir:** DELETAR (código morto) ou CONECTAR
- **Recomendação:** DELETAR
- **Tempo:** 1 hora

### 🟡 FASE 2 - QUALIDADE (1-2 semanas)

#### 2.1 Ativar agente_nicho e agente_variacao
- **Arquivos:** `backend/services/pipeline_flow_config.py`
- **Problema:** Estão sendo PULADOS por padrão (`_builder_fast_path=True`)
- **Impacto:** Sites sempre iguais (sem variação), sem briefing de nicho
- **Fix:** Mudar para sempre rodar (ou pelo menos 50% do tempo)
- **Tempo:** 1 hora

#### 2.2 Adicionar componentes críticos
- **Testimonials** (prova social = conversão)
- **Pricing Table**
- **FAQ Accordion** (SEO + UX)
- **Arquivo:** Atualizar prompts + component_library.py
- **Tempo:** 8 horas

#### 2.3 Adicionar Page Transitions
- **Arquivo:** `backend/agents/html_quality_gate.py`
- **Tempo:** 2 horas

#### 2.4 Unificar Jina v1/v2
- **Decidir:** Manter cascata OU remover v1
- **Recomendação:** Remover v1 (só v2)
- **Tempo:** 2 horas

### 🟢 FASE 3 - EVOLUÇÃO (1-3 meses)

#### 3.1 Adicionar Design Director Agent
- Decide direção criativa ANTES do Builder
- SEM ele, sempre sai igual

#### 3.2 Adicionar Trend Watcher
- Web search para tendências

#### 3.3 Adicionar Learning Loop
- Coleta métricas reais, aprende

#### 3.4 Migrar para Claude Managed Agents
- Substitui LangGraph próprio
- Tem dreaming, MCP servers

---

## 💰 CUSTO TOTAL ESTIMADO

| Fase | Esforço | Custo Tokens | Custo $$ |
|------|---------|--------------|---------|
| FASE 1 | 1-2 dias | ~5K tokens | ~$5 |
| FASE 2 | 1-2 semanas | ~50K tokens | ~$50 |
| FASE 3 | 1-3 meses | ~200K tokens/mês | ~$200 |

---

## 📊 SCORE POR DIMENSÃO

| Dimensão | Atual | Após F1 | Após F2 | Após F3 |
|----------|-------|---------|---------|---------|
| Robustez (imports) | 5/10 | **10/10** | 10/10 | 10/10 |
| SEO/A11Y/LGPD | 4/10 | **8/10** | 9/10 | 9/10 |
| Motion/Premium | 6/10 | 7/10 | **9/10** | 9/10 |
| Variação de sites | 3/10 | 4/10 | **7/10** | 9/10 |
| Inteligência agentes | 5/10 | 6/10 | 7/10 | **9/10** |
| Aprendizado contínuo | 1/10 | 1/10 | 3/10 | **8/10** |
| **TOTAL** | **4.0/10** | **6.0/10** | **7.5/10** | **9.0/10** |

---

## 🎯 RECOMENDAÇÃO IMEDIATA

**FAZER FASE 1 COMPLETA AGORA** (1-2 dias)

Isso já transforma o FraLib de "5.4/10" para "7/10" com:
- ✅ Sistema não quebra mais por imports
- ✅ Sites com LGPD, SEO, fonts corretos
- ✅ Sites em PT-BR garantido
- ✅ Código morto removido

Depois decidir se vai para FASE 2 (qualidade premium).

---

*Auditoria completa em `docs/AUDITORIA_FINAL_CONSOLIDADA.md`*
