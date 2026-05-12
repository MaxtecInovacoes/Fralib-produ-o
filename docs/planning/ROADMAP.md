# Roadmap: FraLib OS

**Project:** FraLib OS — Pipeline Automatizado de Sites Animados
**Started:** 2026-05-09
**Goal:** Pipeline 100% automatizado: lead → site animado por nicho → WhatsApp → pagamento Stripe → ativação

---

## Phase 1 — Animações por Nicho no Liam

**Goal:** Liam gera sites com animações profissionais adaptadas ao nicho do lead. Diferencial visual que justifica o preço premium.

**Requirements:** ANIM-01 a ANIM-06

**Plans:**
1. `animation_profile.py` — módulo que mapeia nicho → perfil de animação (intensidade, tipo, timing)
2. Melhorar prompt do Liam para receber e aplicar o animation_profile
3. Hero section animada: gradiente CSS + typewriter + CTA pulse (CSS/JS inline)
4. Scroll animations com Intersection Observer em todas as seções
5. Micro-interações em botões e formulários

**Done when:** Liam gera HTML com animações diferentes para advocacia vs academia vs clínica, todas em CSS/JS puro inline.

---

## Phase 2 — Bryan SDR: State Machine Completa

**Goal:** Bryan avança corretamente pelos estados da conversa até fechar a venda, com timeout automático e log no banco.

**Requirements:** BRYAN-01 a BRYAN-05

**Plans:**
1. Mapear e corrigir a state machine atual (por que fica travada em "intro")
2. Implementar transições automáticas baseadas na resposta do lead
3. Timeout por estado (X horas sem resposta → próximo estado)
4. Log de transições no PostgreSQL
5. Testes de fluxo completo (intro → close)

**Done when:** Bryan conduz uma conversa completa do intro ao fechamento sem intervenção humana.

---

## Phase 3 — Stripe: Pagamento Integrado

**Goal:** Pipeline gera link de pagamento Stripe automaticamente. Bryan envia o link no estado "price". Webhook ativa o plano após pagamento.

**Requirements:** STRIPE-01 a STRIPE-05

**Plans:**
1. Definir planos BASIC/STANDARD/PREMIUM com preços em BRL
2. Integrar Stripe SDK no pipeline (criar checkout session)
3. Webhook Stripe → ativar plano no banco
4. Bryan envia link Stripe no estado "price"
5. Testes de fluxo completo (checkout → webhook → ativação)

**Done when:** Lead recebe link de pagamento via WhatsApp, paga, e o plano é ativado automaticamente.

---

## Phase 4 — Pipeline: Correções e Performance

**Goal:** Pipeline robusto, sem bugs conhecidos, com performance melhorada.

**Requirements:** PIPE-01 a PIPE-05

**Plans:**
1. Corrigir reprocessar completo (Liam/Liz/Deploy/Bryan)
2. Migrar SSE logs de deque para PostgreSQL LISTEN/NOTIFY
3. Refatorar alex.py em módulos ≤ 300 linhas
4. Migrar Arquiteto Mestre de Opus para Sonnet
5. Hunter assíncrono (Playwright async)

**Done when:** Pipeline reprocessa sem bugs, logs são confiáveis, todos os arquivos ≤ 300 linhas.

---

## Phase 5 — Landing Page com Planos e Stripe

**Goal:** Landing page alinhada com os planos de preço, com checkout Stripe e demonstração do produto.

**Requirements:** LAND-01 a LAND-03

**Plans:**
1. Redesign da landing page com seção de planos (BASIC/STANDARD/PREMIUM)
2. Botão de checkout Stripe em cada plano
3. Seção de demonstração com exemplo real de site gerado
4. Deploy e testes

**Done when:** Visitante da landing page consegue ver os planos, clicar em "Contratar" e ser redirecionado para o checkout Stripe.

---

## Milestones

| Milestone | Phases | Target |
|-----------|--------|--------|
| v1.0 — Sites Animados | Phase 1 | Após Phase 1 |
| v1.1 — SDR Completo | Phase 2 | Após Phase 2 |
| v1.2 — Monetização | Phase 3 + 5 | Após Phase 3+5 |
| v1.3 — Pipeline Robusto | Phase 4 | Após Phase 4 |

---
*Roadmap created: 2026-05-09*
*Last updated: 2026-05-09 após inicialização*
