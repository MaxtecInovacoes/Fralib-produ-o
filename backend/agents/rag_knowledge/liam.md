# Conhecimento RAG - Liam (Gerador de HTML)

## Missao
Gerar HTML cinematografico, responsivo e otimizado para negocios locais.
Sites dignos de premio - dark/light mode, animacoes GSAP, SEO local, LGPD.
Cada site deve ser UNICO - sem templates fixos. Criatividade maxima com os dados reais do lead.

## Stack Tecnologico

- Tailwind CSS 3.4+ via CDN
- GSAP 3.12+ com ScrollTrigger
- Lenis 1.0+ (smooth scroll)
- Google Fonts (Montserrat, Inter, Poppins, Playfair Display)
- Schema.org JSON-LD

## Performance Obrigatoria

### Google Fonts (NUNCA render-blocking)
`html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;900&family=Inter:wght@300;400;500&display=swap&subset=latin-ext" rel="stylesheet">
`

### Scripts (SEMPRE defer)
`html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/@studio-freight/lenis@1.0.42/dist/lenis.min.js" defer></script>
`

### Imagens (SEMPRE lazy + srcset quando possivel)
`html
<img src="foto.webp" loading="lazy" decoding="async" alt="descricao" class="w-full h-full object-cover">
`

## Guardrails Criticos

### NUNCA fazer
- NUNCA exibir precos, valores, mensalidades, tabelas de preco
- Usar sempre: Consulte valores, Solicite orcamento, Fale conosco
- NUNCA usar lorem ipsum ou texto generico
- NUNCA usar cores hardcoded - sempre CSS variables
- NUNCA usar caminhos relativos (./assets/) - sempre absolutos (/sites/slug/assets/)
- NUNCA usar opacity:0 no CSS inicial (quebra SEO)
- NUNCA usar emojis - usar SVG icons
- NUNCA usar gradientes genericos
- NUNCA repetir o mesmo layout de hero em todos os sites

### SEMPRE fazer
- SEMPRE usar paleta CSS variables fornecida (--color-primary, --color-secondary)
- SEMPRE adicionar comentarios de secao: <!-- SECTION:hero --> e <!-- /SECTION:hero -->
- SEMPRE incluir banner LGPD com aceitar/rejeitar
- SEMPRE incluir link politica de privacidade no footer
- SEMPRE usar H1 unico: Nome + Segmento + Cidade
- SEMPRE usar H2 para cada secao principal
- SEMPRE usar H3 para subsecoes (servicos, depoimentos)
- SEMPRE adicionar loading=lazy em imagens
- SEMPRE adicionar aria-label em botoes e links
- SEMPRE usar clamp() para tipografia responsiva
- SEMPRE adicionar :hover states em botoes e cards
- SEMPRE usar prefers-reduced-motion para desativar animacoes quando solicitado

## Dark Mode

Quando briefing indicar DARK MODE:
- background: #0a0a0a
- surface: #1a1a1a
- texto: #f0f0f5
- usar cores vibrantes do cliente como acento
- bordas com rgba(255,255,255,0.08)
- sombras com rgba(0,0,0,0.5)

