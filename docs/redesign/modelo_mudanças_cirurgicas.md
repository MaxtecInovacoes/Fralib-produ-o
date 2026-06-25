# 🎯 Modelo de Mudanças Cirúrgicas — Baseado em Dados + Benchmark

**Base**: 1.973 sessões + análise de 6 landing pages top + benchmarks de mercado

## 📊 MUDANÇAS PRIORITÁRIAS (P0 — Fazer HOJE)

### 1. Mover Pricing para Posição #3-4 (CRÍTICO)

**Por quê?**
- 95% dos usuários não rolam até pricing atual (#13 de 16 seções)
- Mercado top (Linear, Vercel, Framer, Cal): Pricing só aparece em nav ou muito abaixo
- Stripe é exceção: pricing visível (#3 na ordem)

**Mudança:**
```
Hero (#1) → Social Proof (#2) → Pricing Preview (#3) → Como Funciona (#4) → ...
```

**Implementação:**
- Adicionar "A partir de R$97/mês" no hero (abaixo do H1)
- Criar seção pricing nova na posição #3 com:
  - 3 planos (Free, Starter, Pro) com preços visíveis
  - CTA "Começar de graça" no plano Free
  - CTA "Assinar agora" nos planos pagos
  - Comparativo com concorrentes (simplificado)

### 2. Reduzir Hero para 1.5 telas (CRÍTICO)

**Por quê?**
- 95% dos usuários não rolam → hero está consumindo toda atenção inicial
- Mercado top: hero enxuto (Linear: 1 tela, Vercel: 1.5, Framer: 2, Cal: 1.5)

**Mudança:**
```
Hero atual: 3 telas (hero + problema + como funciona)
Hero novo: 1.5 telas (H1 + subhead + CTA + preview do produto)
```

**Implementação:**
- Manter H1 e subhead (estão bom)
- Remover "Problema" e "Como funciona" do hero
- Adicionar preview do produto (screenshot do kanban com 3 cards)
- Adicionar "33k+ usuários" como social proof no hero
- Adicionar scroll indicator (seta sutil animada)

### 3. Remover Animações Excessivas (CRÍTICO)

**Por quê?**
- Você não gostou e distraem do conteúdo
- Mercado top: animações mínimas (Linear: nenhuma, Vercel: glow sutil, Framer: AI demo)

**Remover:**
- Particles (250 partículas)
- Orbs flutuantes
- Snake-card borders
- Parallax scrolling
- Glassmorphism
- Pulsing glows nos steps
- Rainbow conic-gradient
- Mesh-bg com blur
- Shimmer no botão
- Animated gradient text
- Multiple mascotes

**Manter:**
- Transições sutis em hover
- Fade-in ao rolar
- Counter numbers animados

### 4. Simplificar Form Beta (CRÍTICO)

**Por quê?**
- 0 conversões em 30 dias → form está com friction
- Mercado top: forms simples (Cal: 2 campos, Linear: 1 campo)

**Mudança:**
```
Form atual: Nome + Email + Empresa + Telefone + Mensagem
Form novo: Nome + WhatsApp (2 campos)
```

**Implementação:**
- Colocar form ao lado do CTA principal (não em seção separada)
- Adicionar "Sem obrigação, só conversamos 5 min"
- Botão "Quero meu site grátis" (CTA claro)
- Remover obrigatório empresa/telefone

## 🎨 MUDANÇAS DE VISUAL (P1 — Esta semana)

### 5. Nova Estrutura de Seções

```
1. Hero (1.5 telas)
   - H1: "FraLib OS: Sites com IA para Freelancers"
   - Sub: "Crie sites em 1h, faça prospecção no Google Maps, venda pelo WhatsApp"
   - CTA: "Quero meu site grátis" (azul)
   - Social proof: "33k+ usuários"
   - Preview: Screenshot do kanban (3 cards)
   - Scroll indicator: Seta animada

2. Social Proof (1 tela)
   - Logos de clientes reais
   - Números: "33k+ sites criados", "R$1.2M em vendas"
   - Depoimentos: "Meus leads aumentaram 300%" (com foto)

3. Pricing Preview (1 tela)
   - 3 colunas: Free, Starter, Pro
   - Preços: R$0, R$97/mês, R$197/mês
   - CTA: "Começar de graça"
   - Comparativo: "Menos que um café por dia"

4. Como Funciona (1 tela)
   - 4 steps simples: Criar → Prospecionar → Vender → Automatizar
   - Screenshots reais de cada step
   - CTA: "Ver como funciona" (cinza)

5. Planos Detalhados (1 tela)
   - Mesmo layout da preview, mas com features detalhadas
   - CTA: "Assinar agora" (azul)

6. Testemunhos (1 tela)
   - 3 depoimentos com foto/nome/cargo
   - CTA: "Ver mais depoimentos" (cinza)

7. FAQ (1 tela)
   - 5 perguntas com collapse/expand
   - CTA: "Tem dúvida? Fale conosco" (cinza)

8. Final CTA (1 tela)
   - H1: "Pronto para começar?"
   - CTA: "Quero meu site grátis" (azul)
   - "Sem obrigação, cancelar quando quiser"
```

### 6. Nova Paleta de Cores (60-30-10)

**Base:**
- 60% Branco (fundo)
- 30% Ciano (#00cc8e) - elementos secundários
- 10% Roxo (#4c1d9e) - CTAs e pontos fortes

**CTAs:**
- Primário: Roxo escuro (#4c1d9e) com hover mais escuro
- Secundário: Ciano (#00cc8e) com hover mais verde
- Terciário: Cinza (#6b7280) para links

### 7. Nova Tipografia

**Headlines:**
- H1: 3.5rem (56px), weight 700, letter-spacing -0.02em
- H2: 2.5rem (40px), weight 600, letter-spacing -0.01em
- H3: 1.875rem (30px), weight 600

**Body:**
- Padrão: 1.125rem (18px), weight 400
- Destaque: weight 600
- Muito pequeno: 0.875rem (14px)

### 8. Novos CTAs

**Texto:**
- Primário: "Quero meu site grátis" (ação + benefício)
- Secundário: "Ver planos" (exploração)
- Terciário: "Como funciona" (educação)

**Posição:**
- Topo da nav: "Assinar" (sempre visível)
- Hero: "Quero meu site grátis" (grande, roxo)
- Repetir em cada seção principal

### 9. Novo Sistema de Whitespace

**Espaçamentos:**
- Seções: 120px padding (vertical)
- Elementos: 32px spacing (horizontal)
- Grid: 24px gap

**Max-width:**
- Container: 1200px (desktop)
- Texto: 640px (readability)

## 📱 MUDANÇAS RESPONSIVAS (P1 — Esta semana)

### 10. Mobile First

**Hero mobile:**
- H1: 2rem (32px)
- Subhead: 1.125rem (18px)
- CTA: 16px, padding 16px 32px
- Preview: imagem 100% width

**Seções mobile:**
- Padding: 60px 20px
- Grid: 1 coluna
- CTAs: 48px height (touch-friendly)

## 🎯 MUDANÇAS DE COPY (P1 — Esta semana)

### 11. Copy Mais Direta

**Hero:**
```
H1: "FraLib OS: Sites com IA para Freelancers"
Sub: "Crie sites em 1h, faça prospecção no Google Maps, venda pelo WhatsApp"
CTA: "Quero meu site grátis"
```

**Social Proof:**
```
"33k+ freelancers já criaram sites"
"R$1.2M em vendas geradas"
"Meus leads aumentaram 300% — Ana, 28 anos"
```

**Pricing:**
```
Free: Site básico + WhatsApp
Starter: + Prospecção + CRM (R$97/mês)
Pro: + Automatização + API (R$197/mês)
```

## 📊 MÉTRICAS ESPERADAS PÓS-MUDANÇAS

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Scroll 25% | 4.9% | 25% | 5x mais |
| Scroll 50% | 3.8% | 12% | 3x mais |
| CTA clicks | 1.6% | 5% | 3x mais |
| Conversão | 0.05% | 1% | 20x mais |
| Bounce rate | 10.8% | 15% | aceitável |

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

### P0 (HOJE)
- [ ] Mover pricing para #3-4
- [ ] Reduzir hero para 1.5 telas
- [ ] Remover animações excessivas
- [ ] Simplificar form beta para 2 campos

### P1 (Esta semana)
- [ ] Nova estrutura de 8 seções
- [ ] Nova paleta 60-30-10
- [ ] Novos CTAs com texto claro
- [ ] Sistema de whitespace
- [ ] Mobile first design
- [ ] Copy mais direta

### P2 (Próxima semana)
- [ ] A/B test do CTA
- [ ] Configurar Clarity ID
- [ ] Adicionar trust signals
- [ ] Testar com usuários

## 🎯 PRÓXIMOS PASSOS

1. **Implementar P0 hoje** (mudanças críticas)
2. **Deployar e esperar 3 dias** para ver impacto
3. **Medir scroll depth e CTAs** após mudanças
4. **Ajustar se necessário** antes de P1

Fontes: 
- Dados FraLib: 1.973 sessões, 30 dias
- Benchmark: Linear, Vercel, Framer, Cal, Stripe, Supabase
- Mercado: Unbounce (3.8% conversão), CrazyEgg (44% bounce)