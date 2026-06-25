# FraLib vs Mercado — Benchmark Comparativo

**Data da análise**: Junho/2026
**Amostra FraLib**: 1.973 sessões únicas (30 dias)

## 📊 TABELA COMPARATIVA

| Métrica | FraLib | Mercado SaaS | Gap | Veredito |
|---------|--------|--------------|-----|----------|
| **Bounce rate** | 10.8% | 44-48% (SaaS/IT) | ✅ -33pp | **MUITO MELHOR** |
| **Scroll 25%+** | 4.9% | ~50-60% | ❌ -45pp | **CRÍTICO** |
| **Scroll 50%+** | 3.8% | ~30% | ❌ -26pp | **CRÍTICO** |
| **CTA click rate** | 1.6% | 3-8% | ❌ -1.4pp a -6.4pp | **MUITO BAIXO** |
| **Conversão total** | 0.05% | 3.8% (mediana SaaS) | ❌ -3.75pp | **PÉSSIMO** |
| **Tempo médio** | 252s | ~120-180s | ✅ +72s | **BOM** |
| **Pages/session** | 1.05 | 1.3-1.8 | ❌ -0.25 | **BAIXO** |

## 🏆 O QUE ESTAMOS FAZENDO MELHOR QUE O MERCADO

1. **Bounce rate 10.8% vs 44% do mercado SaaS**
   - Significa: o HERO convence as pessoas a ficarem
   - Copy/H1 do hero está bom
   - Não mexer

2. **Tempo médio 252s (4min)**
   - Visitantes que ficam, engajam profundamente
   - Conteúdo tem qualidade

## 🚨 O QUE ESTAMOS FAZENDO MUITO PIOR

### 1. SCROLL DEPTH (95% dos usuários não rolam!)

**Mercado**: 50-60% rolam até 25%, 30% até 50%
**FraLib**: 4.9% até 25%, 3.8% até 50%

**Por quê?**
- Hero muito "gordo" (consome toda atenção inicial)
- Falta gancho visual pra continuar descendo
- CTAs集中在 no hero, depois some
- Animações pesadas distraem do conteúdo

**Benchmark de referência (Linear, Vercel, Framer, Cal.com)**:
- Hero enxuto (1 tela e meia no máximo)
- CTA primário + preview do produto acima da dobra
- Cada seção tem um "gancho" visual forte (número, imagem, stat)
- Repeat CTAs em cada seção importante

### 2. CTA CLICK RATE (1.6% vs 3-8% do mercado)

**Mercado**: 3-8% clicam em algum CTA
**FraLib**: 1.6% clicam

**Por quê?**
- Apenas 22 cliques no hero CTA em 30 dias
- Apenas 1 clique em trial, 1 em pro
- Pricing está MUITO abaixo (95% não chega lá)
- CTA hero pode estar competindo com outros elementos visuais

**Benchmark (Cal.com, Linear, Vercel)**:
- CTA primário no **canto superior direito** da nav (sempre visível)
- CTA grande e óbvio abaixo do H1
- "Get started" / "Sign up" / "Deploy Now" como texto do CTA
- Repetir CTA em cada seção principal

### 3. CONVERSÃO (0.05% vs 3.8% do mercado)

**Mercado SaaS**: 3.8% conversão mediana
**FraLib**: 0.05% (apenas 1 trial + 1 pro em 30 dias)

**Por quê?**
- Pricing longe do hero
- Form beta ninguém envia (0 conversões!)
- Apenas 4.9% chega a qualquer CTA de pricing

## 🎯 BENCHMARKS DAS TOP LANDING PAGES

### Linear.app (referência de clareza)
- **Pricing**: NÃO está na landing principal → vai para /pricing
- **Estrutura**: 7-8 seções principais
- **CTA**: "Coding Sessions →" no hero, "Get started" no footer
- **Copy**: Headlines declarativas curtas, sem ponto final
- **Social proof**: "33,000 product teams" no hero
- **Padrão de features**: Numeradas (1.1, 1.2, 1.3...) como FIG 0.x
- **Visual**: Whitespace generoso, tipografia grande, screenshots reais

### Vercel.com (referência de movimento)
- **Pricing**: NÃO está na landing principal → só link na nav
- **Estrutura**: 8 seções
- **CTA primário**: "Deploy Now" (ação específica, não genérica)
- **Social proof**: Customer logos + números específicos ("100M monthly visits")
- **Visual**: Dark mode hero, glow effects, código em destaque
- **Repetição CTA**: Deploy + plugin install snippet em seção dedicada

### Framer.com (referência de demo)
- **Pricing**: NÃO está na landing principal
- **Estrutura**: 8 seções
- **CTA**: "Get started for free" no hero + final
- **Demo**: Produto sendo usado no hero (não só screenshot)
- **Social proof**: Miro, Mixpanel, Perplexity, Zapier, StackAI
- **Visual**: AI agent editando site ao vivo (prova de funcionamento)

### Cal.com (referência de clareza extrema)
- **Pricing**: 3 tiers com preço visível (Free, $16, $37)
- **Estrutura**: 10 seções
- **CTA**: "Get started" SEMPRE visível (top right + final de cada seção)
- **Copy**: Texto claro, "No credit card required" abaixo do CTA
- **Trust signals**: HIPAA, SOC 2, usado em healthcare
- **Repetição**: "Talk to sales" aparece em TODA seção

### Stripe.com (referência de pricing visível)
- **Pricing**: Mostra pricing na landing principal (#3 na ordem)
- **Estrutura**: Nav → Hero → Pricing → Demos → Features
- **CTA**: Repetido em cada seção

## 🛠️ GAPS ESPECÍFICOS PARA CORRIGIR

### Gap #1: Hero está prendendo mas não empurrando
- ✅ Bounce rate bom = hero convence
- ❌ Scroll baixo = hero não convence a continuar

**Ação**: Manter copy do hero. Adicionar **scroll indicator** (seta animada sutil) e "preview" do que vem abaixo (mini-cards, números).

### Gap #2: Pricing invisível
- ❌ Pricing está na seção #13 de 16
- ❌ 95% dos usuários nunca chega lá

**Ação**: Mover pricing para **#3-4 da ordem** (após social proof). Adicionar **pricing teaser no hero** ("A partir de R$97/mês").

### Gap #3: CTA único no hero
- ❌ 22 cliques no hero CTA / 1973 sessões = 1.1%
- ✅ Mercado: 3-8%

**Ação**: Adicionar **CTA secundário** ("Ver planos" ou "Como funciona"). CTA principal com cor de alto contraste (regra 60-30-10 → roxo 10%).

### Gap #4: Form beta ninguém envia
- ❌ 0 conversões em 30 dias
- ❌ Form deve ter friction (muitos campos? mal posicionado?)

**Ação**: Investigar form beta. Reduzir para **2 campos** (nome + WhatsApp). Adicionar ao lado do CTA principal, não em seção separada.

### Gap #5: Animações excessivas
- ❌ Você não gostou
- ❌ Mercado top (Linear, Vercel, Framer) tem animações mínimas

**Ação**: Remover particles, orbs, snake-card, parallax, glassmorphism. Manter transições sutis em hover.

## 🎯 PLANO DE AÇÕES PRIORIZADAS

### P0 — Crítico (fazer HOJE)
1. Mover pricing para posição #3-4
2. Adicionar "a partir de R$97" no hero
3. Remover animações excessivas (particles, orbs, snake-card, parallax, glassmorphism)
4. Reduzir form beta para 2 campos

### P1 — Importante (esta semana)
5. Adicionar scroll indicator no hero
6. Adicionar CTA secundário ("Ver planos")
7. Repetir CTA em cada seção principal
8. Adicionar social proof logo após hero ("33k users" → números reais do FraLib)

### P2 — Melhoria (próxima semana)
9. Adicionar preview do produto no hero (screenshot do kanban)
10. Implementar Heatmap Clarity (já temos snippet, falta configurar ID)
11. A/B test do texto do CTA ("Assinar" → "Quero meu site")
12. Adicionar trust signals (LGPD, segurança, etc)

## 📈 META PÓS-REDESIGN

Se as mudanças funcionarem:
- Scroll 25%: **4.9% → 25%** (5x mais)
- Scroll 50%: **3.8% → 12%** (3x mais)
- CTA click: **1.6% → 5%** (3x mais)
- Conversão: **0.05% → 1%** (20x mais)

## 📚 Fontes

- Unbounce Conversion Benchmark Report 2024: https://unbounce.com/conversion-benchmark-report/
- WordStream Conversion Benchmarks: https://www.wordstream.com/blog/ws/2022/08/19/conversion-benchmarks
- CrazyEgg Bounce Rate Study: https://www.crazyegg.com/blog/bounce-rate/
- HubSpot Landing Page Stats: https://blog.hubspot.com/marketing/landing-page-stats
- Linear.app (análise direta)
- Vercel.com (análise direta)
- Framer.com (análise direta)
- Cal.com (análise direta)
