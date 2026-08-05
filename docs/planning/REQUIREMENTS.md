# Requirements: FraLib OS — Pipeline Automatizado de Sites Animados

**Defined:** 2026-05-09
**Core Value:** O lead recebe um site profissional animado antes de saber que quer comprar — a venda acontece depois que ele já viu o produto.

## v1 Requirements

### Animações (Liam)

- [ ] **ANIM-01**: Pipeline gera animation_profile por nicho (advocacia, academia, clínica, restaurante, etc.)
- [ ] **ANIM-02**: Hero section com gradiente CSS animado + typewriter no H1 + CTA com pulse animation
- [ ] **ANIM-03**: Scroll animations com Intersection Observer (fade-in, slide-up) em todas as seções
- [ ] **ANIM-04**: Micro-interações em botões (hover scale + shadow) e CTAs (pulse contínuo)
- [ ] **ANIM-05**: Intensidade de animação adaptada ao nicho (suave para saúde/jurídico, energético para fitness/gastronomia)
- [ ] **ANIM-06**: Todas as animações em CSS/JS puro inline — zero dependências externas

### Franz SDR

- [ ] **Franz-01**: State machine avança corretamente: intro → proof → link → value → price → close
- [ ] **Franz-02**: Cada estado tem mensagem personalizada por tier (PREMIUM=consultivo, BASIC=hard sell)
- [ ] **Franz-03**: Transição automática de estado baseada na resposta do lead
- [ ] **Franz-04**: Timeout por estado (lead sem resposta em X horas → próximo estado ou encerrar)
- [ ] **Franz-05**: Log de cada transição de estado no PostgreSQL

### Stripe (Pagamento)

- [ ] **STRIPE-01**: Checkout Stripe integrado ao pipeline (link de pagamento gerado automaticamente)
- [ ] **STRIPE-02**: Webhook Stripe processa pagamento confirmado → ativa plano do lead
- [ ] **STRIPE-03**: Planos definidos: BASIC / STANDARD / PREMIUM com preços em BRL
- [ ] **STRIPE-04**: Franz envia link de pagamento Stripe no estado "price" da state machine
- [ ] **STRIPE-05**: Landing page exibe planos com preços e botão de checkout Stripe

### Pipeline (Correções e Melhorias)

- [ ] **PIPE-01**: Reprocessar pipeline completo funciona (Liam → Liz → Deploy → Franz no reprocessar)
- [ ] **PIPE-02**: SSE logs migrados de deque para PostgreSQL LISTEN/NOTIFY
- [ ] **PIPE-03**: alex.py refatorado em módulos ≤ 300 linhas
- [ ] **PIPE-04**: Arquiteto Mestre migrado de Opus para Sonnet (economia sem perda de qualidade)
- [ ] **PIPE-05**: Hunter assíncrono (Playwright async) para reduzir tempo de scraping

### Landing Page

- [ ] **LAND-01**: Landing page alinhada com os 3 planos de preço (BASIC/STANDARD/PREMIUM)
- [ ] **LAND-02**: Botão de checkout Stripe em cada plano
- [ ] **LAND-03**: Seção de demonstração com exemplo de site gerado pelo pipeline

## v2 Requirements

### Elementos 3D

- **3D-01**: Spline embeds para nichos premium (arquitetura, imobiliária, tech)
- **3D-02**: Curadoria de elementos Spline por nicho (biblioteca interna)

### Expansão do Pipeline

- **EXP-01**: Hunter assíncrono com múltiplas fontes (Google Maps + Instagram + LinkedIn)
- **EXP-02**: Painel de aprovação do cliente (preview antes de publicar)
- **EXP-03**: Iteração automática: lead pede ajuste → pipeline regenera seção específica
- **EXP-04**: Mercado Pago como opção adicional de pagamento (PIX)

### Qualidade Visual

- **VIS-01**: Vídeo de fundo no hero para nichos premium
- **VIS-02**: Partículas animadas (canvas) para tech/startup
- **VIS-03**: Parallax avançado em seções de depoimentos

## Out of Scope

| Feature | Reason |
|---------|--------|
| Open Design como motor de geração | Depende de CLI instalado, não tem modo headless puro |
| AntiGravity | Ferramenta visual sem API, não integrável em pipeline headless |
| App mobile | Web-first, mobile fica para v3+ |
| CMS / edição pelo cliente | Pipeline é geração automática, não plataforma de edição |
| Mercado Pago | Stripe escolhido para v1 |
| Spline 3D | Requer curadoria manual por nicho, fica para v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANIM-01 | Phase 1 | Pending |
| ANIM-02 | Phase 1 | Pending |
| ANIM-03 | Phase 1 | Pending |
| ANIM-04 | Phase 1 | Pending |
| ANIM-05 | Phase 1 | Pending |
| ANIM-06 | Phase 1 | Pending |
| Franz-01 | Phase 2 | Pending |
| Franz-02 | Phase 2 | Pending |
| Franz-03 | Phase 2 | Pending |
| Franz-04 | Phase 2 | Pending |
| Franz-05 | Phase 2 | Pending |
| STRIPE-01 | Phase 3 | Pending |
| STRIPE-02 | Phase 3 | Pending |
| STRIPE-03 | Phase 3 | Pending |
| STRIPE-04 | Phase 3 | Pending |
| STRIPE-05 | Phase 3 | Pending |
| PIPE-01 | Phase 4 | Pending |
| PIPE-02 | Phase 4 | Pending |
| PIPE-03 | Phase 4 | Pending |
| PIPE-04 | Phase 4 | Pending |
| PIPE-05 | Phase 4 | Pending |
| LAND-01 | Phase 5 | Pending |
| LAND-02 | Phase 5 | Pending |
| LAND-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-09*
*Last updated: 2026-05-09 após inicialização*
