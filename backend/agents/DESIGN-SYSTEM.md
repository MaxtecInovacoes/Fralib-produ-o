# DESIGN SYSTEM FRALIB - 47 Itens Obrigatórios

## 1. SEO LOCAL (10 itens)
- [ ] `title_com_cidade` — `<title>Nome do Negócio em Cidade, UF</title>`
- [ ] `meta_description_com_cidade` — `<meta name="description" content="...Cidade...">` 
- [ ] `schema_local_business` — JSON-LD com `@type: LocalBusiness`
- [ ] `google_business_profile_link` — Link para `g.page/` ou `google.com/maps`
- [ ] `backlinks_diretorios_locais` — Links para Guia Mais, Apontador
- [ ] `faq_schema` — JSON-LD com `@type: FAQPage`
- [ ] `long_tail_keywords` — Keywords de cauda longa no conteúdo
- [ ] `alt_text_com_cidade` — `alt="Serviço em Cidade"`
- [ ] `nap_consistency` — Nome, Endereço, Telefone consistentes
- [ ] `google_maps_embed` — `<iframe src="https://www.google.com/maps/embed...">`

## 2. CONVERSÃO (8 itens)
- [ ] `prova_social` — Reviews/depoimentos visíveis
- [ ] `urgencia_escassez` — "Vagas limitadas", "Oferta por tempo limitado"
- [ ] `lead_magnet` — Oferta gratuita (avaliação, consulta, desconto)
- [ ] `cta_primario_hero` — CTA principal na seção hero
- [ ] `cta_repetido_3x` — CTA repetido pelo menos 3x na página
- [ ] `whatsapp_flutuante` — Botão WhatsApp fixo no canto inferior
- [ ] `notificacoes_conversao` — "X pessoas viram isso hoje"
- [ ] `visto_por_x_pessoas` — Contador de visualizações

## 3. PERFORMANCE (10 itens)
- [ ] `imagens_webp` — Todas as imagens em formato `.webp`
- [ ] `lazy_loading` — `loading="lazy"` em todas as imagens
- [ ] `preconnect_fontes` — `<link rel="preconnect" href="https://fonts.googleapis.com">`
- [ ] `css_critico_inline` — CSS crítico inline no `<head>`
- [ ] `minificacao` — CSS/JS minificados
- [ ] `lcp_menor_2_5s` — LCP < 2.5s (imagem hero otimizada)
- [ ] `prefetch_paginas` — `<link rel="prefetch">` para páginas internas
- [ ] `srcset_responsivo` — `srcset` em imagens para diferentes resoluções
- [ ] `aspect_ratio` — `aspect-ratio` definido em imagens/vídeos
- [ ] `placeholder_blur` — Placeholder blur enquanto imagem carrega

## 4. ACESSIBILIDADE (6 itens)
- [ ] `contraste_wcag_aa` — Contraste mínimo 4.5:1 (WCAG AA)
- [ ] `alt_text_todas_imagens` — `alt` em todas as `<img>`
- [ ] `navegacao_teclado` — Navegação completa via teclado (Tab/Enter)
- [ ] `aria_labels` — `aria-label` em botões e links sem texto
- [ ] `prefers_reduced_motion` — `@media (prefers-reduced-motion: reduce)`
- [ ] `skip_links` — `<a href="#main">Pular para conteúdo</a>`

## 5. MOBILE (4 itens)
- [ ] `mobile_first` — Design mobile-first com breakpoints
- [ ] `touch_targets_48px` — Botões/links com mínimo 48x48px
- [ ] `menu_hamburger` — Menu hambúrguer em mobile
- [ ] `viewport_meta_tag` — `<meta name="viewport" content="width=device-width, initial-scale=1.0">`

## 6. ANALYTICS (5 itens)
- [ ] `google_analytics_4` — GA4 com `gtag.js`
- [ ] `facebook_pixel` — Facebook Pixel com `fbq`
- [ ] `event_tracking` — Eventos de clique em CTAs
- [ ] `conversoes_configuradas` — Conversões configuradas no GA4
- [ ] `retargeting_ativo` — Pixel de retargeting ativo

## 7. SEGURANÇA (4 itens)
- [ ] `https_ssl` — Site servido via HTTPS
- [ ] `content_security_policy` — Header `Content-Security-Policy`
- [ ] `x_frame_options` — Header `X-Frame-Options: SAMEORIGIN`
- [ ] `x_content_type_options` — Header `X-Content-Type-Options: nosniff`

---

## REGRAS DE DESIGN OBRIGATÓRIAS

### Tipografia
- Heading: Playfair Display, Syne, ou Cormorant Garamond
- Body: Inter, DM Sans, ou Plus Jakarta Sans
- Accent: Montserrat ou Space Grotesk
- Tamanho mínimo body: 16px
- Line-height mínimo: 1.6

### Cores
- Nunca usar azul genérico (#3b82f6, #2563eb) como cor primária
- Paleta deve ser extraída do negócio (logo, fotos)
- Contraste mínimo WCAG AA (4.5:1)
- Dark mode obrigatório via `prefers-color-scheme`

### Animações
- Usar GSAP + ScrollTrigger para animações de scroll
- Usar Lenis para smooth scroll
- `prefers-reduced-motion` obrigatório
- Duração máxima: 0.8s
- Easing: `cubic-bezier(0.25, 1, 0.5, 1)` ou `ease-out`

### Layout
- Mobile-first com Tailwind CSS
- Grid de 12 colunas
- Espaçamento: múltiplos de 4px (4, 8, 16, 24, 32, 48, 64)
- Bordas arredondadas: 8px, 12px, 16px, 24px
- Sombras: `shadow-sm`, `shadow-md`, `shadow-lg`

### Seções Obrigatórias
1. Hero — CTA principal + headline com cidade
2. Sobre — História e diferenciais
3. Serviços/Planos — Cards com preços
4. Depoimentos — Reviews reais dos clientes
5. Localização — Google Maps embed
6. Contato — Formulário + WhatsApp CTA
7. Footer — NAP + links legais
