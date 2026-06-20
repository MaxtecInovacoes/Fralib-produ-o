# 📋 SPEC: FraLib Premium Pipeline Upgrade

**Status:** ✅ APROVADA
**Data:** 2026-06-19
**Score Atual:** 5.4/10 → **Meta: 8.5/10**
**Owner:** Claude (com aprovação do usuário)

---

## 🎯 OBJETIVO (O QUÊ e PORQUÊ)

### O que construir:
Transformar o FraLib de "gerador de sites medianos" para "máquina de sites premium R$10K", aproveitando 100% do código que já existe mas está subutilizado, e adicionando as poucas peças que faltam.

### Por que:
- Sites saem iguais (sem `agente_variacao` rodando)
- Falta SEO/A11Y/LGPD nos prompts (4 críticos ausentes)
- 79 imports quebrados (sistema pode crashar)
- Quality Gate desativado por padrão (sites sem otimização)
- 3 arquivos mortos que confundem navegação
- Agentes inteligentes criados mas não conectados

---

## ✅ CRITÉRIOS DE ACEITE

| # | Critério | Métrica | Como medir |
|---|----------|---------|------------|
| 1 | Zero imports quebrados | 0 ocorrências | `bash scripts/fix_imports.sh` retorna 0 |
| 2 | Quality Gate sempre ativo | Sites passam por ele | `verify_all.sh` mostra gate ativo |
| 3 | Sites em PT-BR | 100% | `grep "pt-BR"` nos prompts de build |
| 4 | A11Y rules | Presente | Verificar `aria-`, `alt=`, semantic HTML |
| 5 | LGPD banner | Presente | `html_quality_gate` injeta |
| 6 | SEO meta tags | Presente | `og:`, `canonical` |
| 7 | agente_variacao roda | 100% | Pipeline chama `gerar_variacao()` |
| 8 | agente_nicho roda | 100% | Pipeline chama `gerar_briefing()` |
| 9 | Code morto deletado | 3 arquivos | `validador.py`, `design_guidelines.py`, `validation_enforcer.py` |
| 10 | Testimonials | Componente | Builder pode gerar |
| 11 | Pricing Table | Componente | Builder pode gerar |
| 12 | FAQ Accordion | Componente | Builder pode gerar |
| 13 | Page Transitions | Presente | `framer-motion` no output |
| 14 | Design Director | Agente novo | Decide direção por lead |
| 15 | Verde final | `verify_all.sh` exit 0 | Script retorna 🟢 |

---

## 🚫 FORA DE ESCOPO

- ❌ Migração completa para Claude Managed Agents SDK (beta, FASE 3+)
- ❌ Reescrever o pipeline do zero
- ❌ Mudar de Vite/React para Next.js
- ❌ Adicionar banco de dados novo
- ❌ Migrar kpalabz → outro LLM

---

## 🏗️ RESTRIÇÕES TÉCNICAS

| Restrição | Valor | Razão |
|-----------|-------|-------|
| Backend | Python 3.13 | Compatibilidade atual |
| Frontend builder | Vite + React + TS | Stack atual |
| LLM | kpalabz (`https://api.kpalabz.com/v1`) | Provider único |
| Modelo padrão | claude-sonnet-4-6 | Custo-benefício |
| Modelo leve | claude-haiku-4-5 | Tarefas simples |
| WhatsApp | whatsmeow (Go) | Keepalive ativo |
| Banco | PostgreSQL | Atual |
| PM2 | 5 processos | Atual |

---

## 📐 ARQUITETURA (após mudanças)

```
LEAD
  ↓
[FASE 1: Hunter] ──→ lead_inventory (DB)
  ↓
[FASE 2: Caio] ──→ qualificação (Python puro, OK)
  ↓
[FASE 3: Jina v2] ──→ inteligência estruturada
  ↓ v1 REMOVIDO (cascata confusa)
[FASE 4: agente_nicho] ──→ briefing nicho ← SEMPRE RODA
  ↓
[FASE 5: Design Director] ← NOVO (decide direção única)
  ↓
[FASE 6: agente_variacao] ──→ estrutura única ← SEMPRE RODA
  ↓
[FASE 7: Arquiteto Mestre / PRD]
  ↓
[FASE 8: Builder Vite]
  - System prompt ATUALIZADO (PT-BR + A11Y + SEO + LGPD)
  - Menciona GSAP, Lenis, Parallax, Video
  ↓
[FASE 9: HTML Quality Gate] ← SEMPRE ATIVO
  - Injeta fonts, OG tags, canonical, LGPD banner
  - Valida Fase 6 T1-T17
  ↓
[FASE 10: Contract Validator] ← SEMPRE ATIVO
  ↓
[FASE 11: Deploy]
```

---

## 🧪 TASKS (quebra do plano)

### FASE A: Fundação (30 min)
- [ ] A1: Criar `docs/specs/SPEC_premium_upgrade.md` ✅ ESTE ARQUIVO
- [ ] A2: Criar `scripts/fix_imports.sh` (automatiza 79 fixes)
- [ ] A3: Criar `scripts/check_agents_alive.sh` (detecta código morto)
- [ ] A4: Criar `scripts/upgrade_falib.sh` (executa tudo)

### FASE B: Correções Críticas (1-2h)
- [ ] B1: Executar fix_imports.sh (corrige 79 imports)
- [ ] B2: Ativar Quality Gate (mudar default em pipeline_flow_config.py)
- [ ] B3: Adicionar PT-BR/A11Y/SEO/LGPD ao VITE_REACT_SYSTEM_PROMPT
- [ ] B4: Deletar validador.py, design_guidelines.py, validation_enforcer.py
- [ ] B5: Verificar que imports ainda funcionam

### FASE C: Conectar Agentes (2-3h)
- [ ] C1: Ativar agente_nicho (remover skip por default)
- [ ] C2: Ativar agente_variacao (remover skip por default)
- [ ] C3: Remover fallback Jina v1 (só v2)
- [ ] C4: Testar pipeline com lead real
- [ ] C5: Medir tokens e tempo

### FASE D: Componentes Premium (4-6h)
- [ ] D1: Adicionar Testimonials ao prompt + component_library
- [ ] D2: Adicionar Pricing Table
- [ ] D3: Adicionar FAQ Accordion
- [ ] D4: Adicionar Page Transitions (framer-motion)

### FASE E: Agente Design Director (3-4h)
- [ ] E1: Criar `backend/agents/design_director.py`
- [ ] E2: System prompt inteligente (decide direção)
- [ ] E3: Integrar ao pipeline_orchestrator
- [ ] E4: Testar com 3 leads diferentes

### FASE F: Validação (1h)
- [ ] F1: `bash scripts/verify_all.sh` retorna 🟢
- [ ] F2: `bash scripts/upgrade_falib.sh` completa sem erro
- [ ] F3: Gerar 1 site de teste (medir qualidade)
- [ ] F4: Commitar tudo

---

## 🔴 DEFINIÇÃO DE VERDE

```bash
$ bash scripts/verify_all.sh
🟢 VERDE - pode fazer deploy!
```

E:
- 0 imports quebrados
- Quality Gate ativo
- Sites com LGPD + SEO + PT-BR + A11Y
- agente_nicho + agente_variacao rodando
- Código morto removido

---

## 📊 MÉTRICAS pós-deploy

| Métrica | Como medir | Esperado |
|---------|-----------|----------|
| Import errors | `scripts/check_imports.py` | 0 |
| Quality Gate ativo | `pipeline_flow_config.py` | True |
| Tempo médio site | `jobs.last_phase_at` | < 60s |
| Sites com LGPD | `data-lgpd-banner` no HTML | 100% |
| Sites únicos | hash do design system | > 90% |

---

## 🚨 RISCOS e MITIGAÇÕES

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Mudar flag do Quality Gate quebra algo | Baixa | Testar com 1 lead antes |
| Ativar agente_variacao gera erros | Média | Validar output antes de publicar |
| Deletar arquivos quebra imports | Baixa | Grep antes de deletar |
| Design Director consome muito LLM | Média | Usar haiku, prompt compacto |
| Componentes novos quebram Builder | Baixa | Testar em isolamento |

---

## 📝 NOTAS

- **AGENTS.md** será atualizado com o novo fluxo
- **verify_all.sh** será expandido para checar novos critérios
- **Commits** serão granulares por fase (A, B, C, D, E, F)

---

**APROVAÇÃO:** Usuário autorizou
**PRÓXIMA AÇÃO:** FASE A (Fundação - scripts)
