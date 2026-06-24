# Analytics da Landing — FraLib OS

## O que está sendo rastreado

### 1. Eventos básicos (`fralib-tracker.js`)
- `view` — pageview
- `scroll_depth` — profundidade de scroll (25%, 50%, 75%, 90%, 100%) + seção visível
- `time_spent` — tempo total na página (segundos)
- `bounce` — saída em <8s sem scroll
- `section_view` — usuário entrou na seção (visibility > 50%)
- `exit_section` — última seção visível antes do exit

### 2. Funil de conversão
- `funnel_scroll_25` — rolou 25% da página
- `funnel_scroll_50` — rolou 50% da página
- `funnel_cta_clicked` — clicou em qualquer CTA (whatsapp, plano, signup)
- `funnel_form_viewed` — formulário de beta entrou no viewport
- `funnel_form_submitted` — enviou o formulário

### 3. Cliques (com contexto)
- `click_whatsapp` — link wa.me (seção + texto)
- `click_plano_trial` / `click_plano_starter` / `click_plano_pro` — planos
- `click_signup` — botão de cadastro (nav / hero / cta-final)
- `click_nav_anchor` — âncora do menu
- `click_button` — botão genérico

### 4. Heatmap
- **Microsoft Clarity** — heatmap + session recording (free, sem limite)
- **Meta Pixel** — eventos de conversão (Contact, Lead, InitiateCheckout, CompleteRegistration)

## Como rodar as análises

As queries SQL estão em `queries_analise_comportamento.sql`.

### Visão geral (rode após 7 dias de dados)

```sql
-- 1. Bounce rate
SELECT
    COUNT(*) AS total_sessoes,
    COUNT(*) FILTER (WHERE evento = 'bounce') AS bounces,
    ROUND(100.0 * COUNT(*) FILTER (WHERE evento = 'bounce') / COUNT(*), 2) AS bounce_rate_pct
FROM landing_analytics
WHERE criado_em >= NOW() - INTERVAL '7 days'
  AND evento IN ('view', 'bounce');
```

### Identificar onde os usuários saem

```sql
-- Última seção antes do exit
SELECT valor_extra, COUNT(*)
FROM landing_analytics
WHERE evento = 'exit_section'
  AND criado_em >= NOW() - INTERVAL '7 days'
GROUP BY valor_extra
ORDER BY COUNT(*) DESC;
```

Se `pricing` ou `cta-final` aparecem no topo = CTAs não estão sendo vistos!

### Funil de conversão

```sql
-- Taxa de conversão por etapa
SELECT
    'visit'           AS etapa, COUNT(*) FILTER (WHERE evento = 'view')                  AS usuarios
FROM landing_analytics WHERE criado_em >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 'scroll_25',     COUNT(*) FILTER (WHERE evento = 'funnel_scroll_25')     FROM ...
UNION ALL
SELECT 'cta_clicked',   COUNT(*) FILTER (WHERE evento = 'funnel_cta_clicked')   FROM ...
UNION ALL
SELECT 'form_submitted',COUNT(*) FILTER (WHERE evento = 'funnel_form_submitted')FROM ...;
```

## Interpretando os dados

### Bounce rate
- **<40%**: Bom
- **40-60%**: Aceitável
- **>60%**: Problema sério — copy/H1 não convence

### Scroll depth
- **>50% dos usuários rolam até 75%**: Boa engajamento
- **<30% rolam até 50%**: Problema no hero ou nas primeiras seções

### Funil
- **visit → scroll_25 < 60%**: Hero está perdendo gente
- **scroll_50 → cta_clicked < 10%**: CTAs estão mal posicionados ou copy fraca
- **cta_clicked → form_submitted < 20%**: Formulário tem friction

### Exit section
- Se a seção com mais exits é uma seção INTERMEDIÁRIA → considerar mover/condensar/remover
- Se é o CTA final → bom sinal (usuários estão chegando ao fim!)

## Dashboard recomendado (criar após 7 dias)

Ferramenta: Metabase (free, self-hosted) ou Streamlit custom

Métricas em tempo real:
1. Bounce rate (últimas 24h, 7d, 30d)
2. Funil de conversão visual
3. Top 5 seções com mais exit
4. CTAs mais clicados (com heatmap de posição)
5. Tempo médio por seção
6. Taxa de conversão visitor → form_submitted

## Ações por achado

### Se bounce rate > 60%
- Reescrever H1 (mais benefício, menos feature)
- Adicionar social proof IMEDIATAMENTE após hero
- Reduzir animações no hero

### Se scroll_25 → scroll_50 tem drop > 40%
- Seções intermediárias estão longas demais
- Condensar Problema/Como Funciona em uma única seção
- Adicionar mais whitespace

### Se cta_clicked < 5% dos visitors
- CTAs estão mal posicionados
- Cor do CTA não contrasta
- Copy do CTA não convence ("Assinar" → "Quero meu site grátis")

### Se exit_section é uma seção no meio
- Mover para depois do CTA
- Condensar conteúdo
- Remover se não é essencial
