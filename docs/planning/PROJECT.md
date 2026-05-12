# FraLib OS — Pipeline Automatizado de Sites Animados

## What This Is

FraLib OS é um pipeline 100% automatizado que, dado um segmento e cidade, busca leads no Google Maps, qualifica-os, gera um site institucional animado e profissional personalizado por nicho, publica online e envia o link via WhatsApp — sem nenhuma intervenção humana do início ao fim.

O sistema já existe e funciona end-to-end. Este projeto foca em elevar a qualidade visual (animações por nicho inspiradas no Open Design), corrigir o Bryan SDR (state machine travada), integrar pagamento via Stripe e fechar o ciclo completo lead → site → venda.

## Core Value

O lead recebe um site profissional animado, publicado e personalizado para o seu nicho antes mesmo de saber que quer comprar — a venda acontece depois que ele já viu o produto.

## Requirements

### Validated

- ✓ Pipeline Hunter → Caio → Theo → Arquiteto → Liam → Deploy → Liz → Bryan funcionando end-to-end
- ✓ Liam gera HTML por seções em paralelo (~35k chars)
- ✓ Deploy automático em seunegociofralib.site/sites/{slug}/
- ✓ WhatsApp via MeoWhats integrado
- ✓ PostgreSQL como banco principal
- ✓ Retry automático de erros 502/503/529 da API Claude
- ✓ Unsplash + paleta por nicho (substituiu Alex)
- ✓ SSE logs em tempo real no dashboard

### Active

- [ ] Animações por nicho no Liam (animation_profile por segmento — scroll, hero, micro-interações)
- [ ] Hero section animada: gradiente dinâmico + typewriter no H1 + CTA com pulse
- [ ] Micro-interações em botões, formulários e CTAs
- [ ] Scroll animations com Intersection Observer (CSS/JS puro, sem deps externas)
- [ ] Bryan SDR: corrigir state machine (intro → proof → link → value → price → close)
- [ ] Stripe: integração de pagamento (checkout, webhook, ativação de plano)
- [ ] Landing page alinhada com planos de preço e Stripe
- [ ] Reprocessar pipeline completo (Liam/Liz/Deploy/Bryan no reprocessar)
- [ ] Refatorar alex.py (1.028 linhas → módulos ≤300 linhas)
- [ ] SSE logs: trocar deque por PostgreSQL LISTEN/NOTIFY

### Out of Scope

- Spline 3D embeds — requer curadoria manual por nicho, fica para v2
- Open Design como motor de geração — usar apenas como referência de padrões visuais
- AntiGravity — ferramenta visual sem API, não integrável no pipeline headless
- Mercado Pago — Stripe escolhido para v1
- App mobile — web-first
- Painel de edição pelo cliente — pipeline é geração automática, não CMS

## Context

**Stack atual (VPS 187.77.37.72):**
- Python 3 + FastAPI + Uvicorn + PM2
- PostgreSQL porta 5433 (fralib_db)
- Nginx + SSL (seunegociofralib.site)
- Claude Opus (geração principal) + Haiku (Caio)
- Playwright (Hunter/Google Maps)
- Jina AI (Theo/pesquisa de concorrentes)
- MeoWhats WebSocket porta 3001
- Pydantic v2 para validação

**Agentes do pipeline:**
1. Hunter — scrapa Google Maps por segmento+cidade
2. Caio — qualifica lead (score 0-100, tier PREMIUM/STANDARD/BASIC/REJEITADO)
3. Theo — estratégia visual (briefing, paleta, animações GSAP, SEO)
4. Arquiteto Mestre — gera DesignerPRD (funde Theo+Caio+paleta nicho, WCAG AA)
5. Liam — gera HTML final seção por seção em paralelo
6. Liz — QA do HTML (HTML, SEO, responsividade, acessibilidade)
7. Bryan — SDR WhatsApp (mensagem personalizada por tier)
8. Alex — desativado (substituído por Unsplash+paleta)

**Referências de qualidade visual:**
- Open Design (github.com/nexu-io/open-design): 31 skills + 72 design systems. Usar como referência de padrões de layout e animação, não como ferramenta integrada.
- Especialistas identificados: sites animados vendem por R$10k-R$25k. Diferencial = animações por nicho (advocacia=suave, academia=energético, clínica=clean).
- Skills disponíveis localmente: ui-animation, motion-designer, ui-ux-pro-max, high-end-visual-design, design-taste-frontend, color-palette, theme-factory.

## Constraints

- **Automação total**: Zero intervenção humana do Hunter ao Bryan. Qualquer feature que exija ação manual é out of scope.
- **CSS/JS puro**: Animações sem dependências externas (sem GSAP, sem Framer Motion) — o HTML precisa ser self-contained para deploy estático.
- **Limite de linhas**: Arquivos Python ≤ 300 linhas. Arquivos maiores devem ser divididos em módulos.
- **VPS**: Toda execução roda na VPS 187.77.37.72. Mudanças locais precisam ser deployadas via SCP + pm2 restart.
- **Modelo**: Liam usa Claude Opus (qualidade máxima de HTML). Caio usa Haiku (economia). Não inverter.
- **Stripe**: Pagamento via Stripe (não Mercado Pago). PIX via Stripe Brazil quando disponível.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Open Design como referência, não motor | Depende de CLI instalado, não tem modo headless puro | — Pending |
| CSS/JS puro para animações | HTML self-contained para deploy estático sem deps | — Pending |
| Stripe para pagamento | Mais robusto, melhor para escalar internacionalmente | — Pending |
| Animações por nicho (não genéricas) | Advocacia≠Academia — personalização aumenta valor percebido | — Pending |
| PostgreSQL LISTEN/NOTIFY para SSE | deque atual perde logs em restart do PM2 | — Pending |

---
*Last updated: 2026-05-09 após inicialização do projeto*
