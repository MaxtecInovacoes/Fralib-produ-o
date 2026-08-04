// generate.js — FraLib OpenUI HTML generation service
// Rewritten clean. Exports match server.js import expectations.
// NO decoration. NO duplication. Single Source of Truth.

const KPA_BASE_URL = process.env.ANTHROPIC_BASE_URL || 'https://deployflow.com.br/api/public/v1';

// ============================================================================
// SYSTEM PROMPT — O Curador
// ============================================================================
const SYSTEM_PROMPT_BASE = `Voce faz parte do orquestrador SEO/GEO 2026 do FraLib.

Sua funcao especifica: gerar o HTML final a partir do DesignerPRD.

Implemente:
- AGENTE 19 TRUST SIGNALS: certificados, cases, clientes, garantias, equipe, fotos, reviews, premios
- AGENTE 20 CONVERSION MAP: objetivo, CTA, prova, objecao, proxima acao por pagina
- AGENTE 14 CRO: CTAs, funis, lead magnets, provas, escassez, urgencia, garantias, WhatsApp
- AGENTE 16 TECHNICAL SEO: Core Web Vitals, lazy loading, AVIF/WebP, schema, JSON-LD
- AGENTE 17 AI SEARCH: perguntas, respostas, citacoes, dados, tabelas, FAQ, glossarios

REGRA: cada CTA, cada prova, cada secao deve ser OBRIGATORIA.

COPY DE ALTA CONVERSAO:
- PROIBIDO: delve, leverage, robust, seamless, journey, ecosystem, vibrant, holistic, embark
- ESPECIFICO: cada frase com numero OU nome proprio
- CTA: comando direto no imperativo
- ESTRUTURA variavel: 1 paragrafo aqui, 6 itens ali, caso real depois
- TOM: socio explicando pra amigo
- MAX 2 paragrafos por secao

O HTML DEVE:
- Dominar Google, Google Maps, Google Business
- Ser citado por ChatGPT, Gemini, Claude, Perplexity
- Core Web Vitals perfeitos (LCP < 2.5s, FID < 100ms, CLS < 0.1)
- schema.org LocalBusiness em JSON-LD
- Open Graph + Twitter Cards
- Mobile-first (375px, 768px, 1440px)
- Lazy loading em todas imagens
- Intersection Observer pra animacoes
- Respeite prefers-reduced-motion
- Sem emojis como icone de UI

# INJECAO DE DRAMA (tensao visual obrigatoria)
- MONUMENTAL TYPE: <h1> com clamp(3rem, 13vw, 15rem), leading-none, tracking-tighter, peso 800-900
- OVERLAP E ASSIMETRIA: margin-top negativo ou translateY, colunas desiguais (70/30, 60/40), nunca 50/50
- NEGATIVE SPACE: espacos vazios INTENCIONAIS (py-32/py-48)
- SIGNATURE ELEMENT: pelo menos UM: linha decorativa longa, gradiente radial, tipografia vazada, forma geometrica
- PROFUNDIDADE: sombras com OFFSET direcional, nunca blur central sem direcao`;

const LAYOUT_FAMILIES = {
  'split-hero': `Layout: SPLIT-HERO. Hero em duas colunas (texto 55% / visual 45%). Topologia zigzag. Footer com CTA WhatsApp.`,
  'center-hero': `Layout: CENTER-HERO. Hero centralizado stack. Secoes lineares. Cards em grid 3-col desktop, 1-col mobile.`,
  'fullscreen-hero': `Layout: FULLSCREEN-HERO. Hero 100vh. Scroll snap sections. Numeros animados na viewport.`,
  'asymmetric-magazine': `Layout: EDITORIAL-ASYMMETRIC. Hero central serif. Grid 2-col com 1 feature grande + cards. Tipografia serif display.`,
  'bento-grid': `Layout: BENTO-GRID. Hero minimalista. Features em bento grid. Visao geral em 1 scroll.`,
  'classic-centered': `Layout: CLASSIC-CENTERED. Hero tradicional. Secoes centradas max-width 800px. Layout linear.`,
};

// Mapping from design direction keys (from design_context.py) to archetypes
const DIRECAO_TO_ARCHETYPE = {
  // Industrial/Bold → industrial-bold
  'industrial': 'industrial-bold',
  'bold': 'industrial-bold',
  'neobold': 'industrial-bold',
  'neon-industrial': 'industrial-bold',
  'tech-bold': 'industrial-bold',
  'construct': 'industrial-bold',
  // Editorial/Asymmetric → editorial-asymmetric (DEFAULT)
  'editorial': 'editorial-asymmetric',
  'editorial-asymmetric': 'editorial-asymmetric',
  'editorial-clean': 'editorial-asymmetric',
  'editorial-serif': 'editorial-asymmetric',
  'magazine': 'editorial-asymmetric',
  'asymmetric': 'editorial-asymmetric',
  // Minimal → apple-minimalist
  'minimal': 'apple-minimalist',
  'minimal-clean': 'apple-minimalist',
  'apple': 'apple-minimalist',
  'clean': 'apple-minimalist',
  'modern-minimal': 'apple-minimalist',
  'flat': 'apple-minimalist',
  // Futurist → dark-futurist
  'futurist': 'dark-futurist',
  'dark-futurist': 'dark-futurist',
  'cyber': 'dark-futurist',
  'neon': 'dark-futurist',
  'tech-dark': 'dark-futurist',
  'digital': 'dark-futurist',
  'cyberpunk': 'dark-futurist',
  // Organic/Warm → organic-warm
  'organic': 'organic-warm',
  'warm': 'organic-warm',
  'organic-warm': 'organic-warm',
  'earth': 'organic-warm',
  'natural': 'organic-warm',
  'terracotta': 'organic-warm',
  'boho': 'organic-warm',
  // Corporate/Trust → corporate-trust
  'corporate': 'corporate-trust',
  'trust': 'corporate-trust',
  'corporate-trust': 'corporate-trust',
  'classic': 'corporate-trust',
  'premium': 'corporate-trust',
  'luxury': 'corporate-trust',
  // NEW: Brutalism
  'brutal': 'brutal-bold',
  'brutalism': 'brutal-bold',
  'raw': 'brutal-bold',
  'neo-brutal': 'brutal-bold',
  // NEW: Luxury/Sophisticated
  'luxury-sophisticated': 'luxury-sophisticated',
  'elegant': 'luxury-sophisticated',
  'haute': 'luxury-sophisticated',
  'refined': 'luxury-sophisticated',
  'sophisticated': 'luxury-sophisticated',
  // NEW: Friendly/Playful
  'friendly': 'friendly-playful',
  'playful': 'friendly-playful',
  'fun': 'friendly-playful',
  'colorful': 'friendly-playful',
  'youth': 'friendly-playful',
  // NEW: Energetic/Vibrant
  'energetic': 'energetic-vibrant',
  'vibrant': 'energetic-vibrant',
  'bold-color': 'energetic-vibrant',
  'pop': 'energetic-vibrant',
  // NEW: Neomorphic/Soft
  'neomorphic': 'neomorphic-soft',
  'soft': 'neomorphic-soft',
  'soft-ui': 'neomorphic-soft',
  'clay': 'neomorphic-soft',
  'claymorphism': 'neomorphic-soft',
  // NEW: Glassmorphism
  'glass': 'glassmorphism',
  'glassmorphism': 'glassmorphism',
  'frosted': 'glassmorphism',
  'transparent': 'glassmorphism',
};

const ARCHETYPE_PROMPTS = {
  'industrial-bold': `Site NEO-INDUSTRIAL. Border-2/4 com cores solidas. Sombras SOLIDAS sem blur. Tipografia display GIGANTE peso 800-900. PROIBIDO border-radius > 4px. Motion: parallax agressivo. SIGNATURE: tipografia MONUMENTAL 15vw, grids 70/30, uppercase, tracking:-0.03em, bordas EXPESSAS.`,
  'editorial-asymmetric': `Site EDITORIAL-ASYMMETRIC. Tipografia serif display (Fraunces/Newsreader) pesos 400-700. Layout ASIMETRICO colunas desiguais. Espacamento ARY (py-24/py-32). Sombras LEVES. Motion: fade sutil + reveal-soft. SIGNATURE: whitespace EXAGERADO, bordas FINISSIMAS 0.5px, serif peso 300-400, letter-spacing:0.03em.`,
  'apple-minimalist': `Site APPLE-MINIMALIST. SF Pro display, branco puro. Hero centralizado stack. Bordas rounded-16px. Sombras shadow-sm. Motion: fade-minimal 200-400ms.`,
  'dark-futurist': `Site DARK-FUTURIST. Fundo #0A0A0F, texto neon (cyan/violet). Grotesk geometrica (Unbounded/Space Grotesk). Bordas sharp. Motion: glitch, magnetic-3d, scan-lines.`,
  'organic-warm': `Site ORGANIC-WARM. Paleta terrosa (marrom+amber+creme). Quicksand + Fraunces. Bordas 12-24px. Sombras LEVES. Motion: fade-organic 300-900ms.`,
  'corporate-trust': `Site CORPORATE-TRUST. Serif classica (Playfair) + sans (Source Sans). Paleta navy+gold. Bordas sharp (0px). Sombras flat. Motion: minimal-fade 200-600ms.`,
  'brutal-bold': `Site BRUTAL-BOLD. Tipografia pesada (Archivo Black/Oswald). Cores saturadas em bloco. Grid rigido. Sombras SOLIDO offset. Bordas sharp 0px. motion: slide-up abrupto. SIGNATURE: borders 4px solid black, uppercase total, backgrounds cores puras (red/blue/yellow), sem gradients.`,
  'luxury-sophisticated': `Site LUXURY-SOPHISTICATED. Tipografia serif elegante (Cormorant/Cinzel). Espacamento GENEROSO. Ouro/metais como acentos. Bordas FINAS. Motion: fade-slow 800-1200ms. SIGNATURE: serif, espacamento duplo, cores metalicas (gold/silver/bronze), backgrounds escuros ou whitespaces extremos.`,
  'friendly-playful': `Site FRIENDLY-PLAYFUL. Tipografia arredondada (Nunito/Quicksand). Cores pastels + vibrantes. Bordas rounded-2xl/3xl. Sombras soft. Motion: bounce-leve, scales. SIGNATURE: rounded-xl++, cores sortidas, icons emoji-style, micro-animacoes funs.`,
  'energetic-vibrant': `Site ENERGETIC-VIBRANT. Tipografia bold+italic. Cores neon saturadas. Layout dinamico com angulos. Motion: shake, pulse, slide-fast. SIGNATURE: gradients, angulos 15deg, cores complementares vibrantes, kinetic typography.`,
  'neomorphic-soft': `Site NEOMORPHIC-SOFT. Fundo unico (cinza/creme). Bordas rounded-full. Sombras DUAS (luz + sombra) para efeito elevado/afundado. Motion: scale-soft. SIGNATURE: mesma cor para bg e surface, sombras suaves opostas, sem bordas visiveis.`,
  'glassmorphism': `Site GLASSMORPHISM. Backdrop-blur. Bordas semitransparentes. Fundo com gradiente+ruido. Motion: float-leve. SIGNATURE: backdrop-filter blur, bordas gradient, transparencias, depth via opacidade.`,
};

// ============================================================================
// buildSystemPrompt
// ============================================================================
export function buildSystemPrompt(prd) {
  // Resolve archetype: explicit > direction key mapping > default
  let archetype = prd?.design_tokens?.archetype;
  if (!archetype || !ARCHETYPE_PROMPTS[archetype]) {
    const dirKey = prd?.design_tokens?.dir_key;
    if (dirKey && DIRECAO_TO_ARCHETYPE[dirKey]) {
      archetype = DIRECAO_TO_ARCHETYPE[dirKey];
    } else if (!archetype) {
      archetype = 'editorial-asymmetric';
    }
  }
  const layoutFam = prd?.layout_dna?.layout_family || 'asymmetric-magazine';
  const archetypeBrief = prd?.design_system?.archetype_briefing || ARCHETYPE_PROMPTS[archetype] || ARCHETYPE_PROMPTS['editorial-asymmetric'];
  const layoutBrief = LAYOUT_FAMILIES[layoutFam] || LAYOUT_FAMILIES['asymmetric-magazine'];
  const sectionRange = prd?.layout_dna?.section_count_range || [5, 8];
  const tokens = prd?.design_tokens || {};
  const palette = tokens.palette || {};
  const typo = tokens.typography || {};

  const BOLD_ARCHETYPES = new Set(['industrial-bold', 'dark-futurist']);
  const boldBlock = BOLD_ARCHETYPES.has(archetype) ? [
    '',
    '# DIRETRIZES DE POLO BOLD (OBRIGATORIO)',
    '- HERO: <h1> DEVE ter classe .hero-headline, MAXIMO 3 palavras.',
    '- SECOES: cada <section> DEVE ter .section-pole.',
    '- CARDS: cada card DEVE ter .card-pole.',
    '- BOTOES: cada CTA DEVE ter .btn-pole.',
    '- Sem paragrafos longos no hero.',
  ].join('\n') : '';

  return [
    SYSTEM_PROMPT_BASE, '',
    '# DESIGN BRIEFING INJETADO (AUTORITATIVO)',
    archetypeBrief, boldBlock, '',
    `# LAYOUT_FAMILY: ${layoutFam}`,
    layoutBrief, '',
    `# ESCOPO: gere entre ${sectionRange[0]} e ${sectionRange[1]} secoes.`,
    'Escolha secoes que contem a historia do lead no content_flow.', '',
    '# TOKENS AUTORITATIVOS (use exatamente)',
    `palette: ${JSON.stringify(palette)}`,
    `typography: ${JSON.stringify(typo)}`,
    `radius: ${JSON.stringify(tokens.radius || {})}`, '',
    '# DIRETRIZ DO DIRETOR DE ARTE',
    prd?.builder_directive || 'Aplique o Design System do archetype autoritativo.', '',
    '# REGRAS ANTI-CLICHE',
    '- NAO use blue-500 / red-500 / gray-500 / slate-9xx',
    '- NAO use font-family sem Google Fonts link rel',
    '- NAO force 6 secoes fixas',
    '- PALETTE PRIMARY eh DEFINITIVA', '',
    '# RESPONSE FORMAT',
    'Responda APENAS com HTML completo: <!DOCTYPE html> ate </html>.',
    'NAO use markdown, fences, comentarios explicativos.',
  ].join('\n');
}

// ============================================================================
// buildUserPrompt
// ============================================================================
export function buildUserPrompt(prd) {
  const sectionsTexto = (prd.sections || [])
    .map(s => `- ${s.name}: ${s.title} | ${(s.content || '').slice(0, 100)}`)
    .join('\n');
  return `Negocio: ${prd.business_name || ''}
Cidade: ${prd.cidade || ''}
Segmento: ${prd.segmento || ''}

Hero: ${JSON.stringify(prd.hero || {})}
Sections: ${sectionsTexto}
CTAs: ${JSON.stringify(prd.ctas || [])}
FAQs: ${JSON.stringify(prd.faqs || [])}
Paleta: ${JSON.stringify(prd.paleta || {})}
SEO keywords: ${JSON.stringify(prd.seo_keywords || [])}
Motion: ${JSON.stringify(prd.motion_directives || {})}

Gere o HTML completo.`;
}

// ============================================================================
// extractHTML
// ============================================================================
export function extractHTML(text) {
  text = text.trim();
  for (const prefix of ['```html', '```HTML', '```']) {
    if (text.startsWith(prefix)) {
      text = text.slice(prefix.length).trimStart();
    }
  }
  if (text.endsWith('```')) {
    text = text.slice(0, -3).trimEnd();
  }
  let match = text.match(/<!DOCTYPE html>[\s\S]*?<\/html>/i);
  if (match) return match[0];
  match = text.match(/<html[\s\S]*?<\/html>/i);
  if (match) return match[0];
  if (/<!DOCTYPE html>|<html/i.test(text)) {
    if (!/<\/body>/i.test(text)) text += '\n</body>';
    if (!/<\/html>/i.test(text)) text += '\n</html>';
    return text;
  }
  return text;
}

// ============================================================================
// injectRequired — JSON-LD + WhatsApp (único que precisa injetar)
// ============================================================================
export function injectRequired(html, prd) {
  html = injectJSONLD(html, prd);
  html = injectFloatingWhatsApp(html, prd);
  return html;
}

function injectFloatingWhatsApp(html, prd) {
  if (/wa-floating/i.test(html)) return html;
  const ctaUrl = (prd?.ctas || []).find(c => /wa\.me/.test(c.url || ''))?.url || 'https://wa.me/';
  const btn = `<!-- FLOATING-WHATSAPP-CRO -->
<a href="${ctaUrl}" target="_blank" rel="noopener"
   class="wa-floating" aria-label="Fale conosco pelo WhatsApp"
   style="position:fixed;bottom:24px;right:24px;z-index:9998;width:60px;height:60px;border-radius:50%;background:#25D366;color:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(37,211,102,0.4);transition:transform 0.2s ease,box-shadow 0.2s ease;text-decoration:none;animation:wa-pulse 2s ease-in-out infinite">
  <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
  </svg>
</a>
<style>
@keyframes wa-pulse { 0% { box-shadow:0 4px 16px rgba(37,211,102,0.4); transform:scale(1); } 50% { box-shadow:0 4px 24px rgba(37,211,102,0.7); transform:scale(1.08); } 100% { box-shadow:0 4px 16px rgba(37,211,102,0.4); transform:scale(1); } }
.wa-floating:hover { transform:scale(1.12) !important; box-shadow:0 6px 28px rgba(37,211,102,0.6) !important; }
@media (max-width:768px) { .wa-floating { width:52px;height:52px;bottom:16px;right:16px; } .wa-floating svg { width:26px;height:26px; } }
</style>`;
  if (html.includes('</body>')) return html.replace('</body>', btn + '</body>', 1);
  return html + btn;
}

function escapeJSONLD(str) {
  return String(str || '')
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"');
}

function injectJSONLD(html, prd) {
  if (/application\/ld\+json/i.test(html)) return html;
  const nome = escapeJSONLD(prd?.business_name || 'Negocio');
  const cidade = escapeJSONLD(prd?.cidade || '');
  const segmento = escapeJSONLD(prd?.segmento || 'negocio local');
  let telephone = '';
  for (const cta of (prd?.ctas || [])) {
    const digits = (cta.url || '').replace(/\D/g, '');
    if (digits.startsWith('55') && digits.length >= 12) {
      telephone = digits;
      break;
    }
  }
  const ld = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": nome,
    "description": `${nome} em ${cidade}`,
    "address": { "@type": "PostalAddress", "addressLocality": cidade, "addressCountry": "BR" },
    "url": "https://seunegociofralib.site/",
    "priceRange": "$$",
    "openingHoursSpecification": [{
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
      "opens": "08:00", "closes": "20:00"
    }],
    "areaServed": { "@type": "City", "name": cidade },
    "additionalProperty": [{ "@type": "PropertyValue", "name": "segmento", "value": segmento }]
  };
  if (telephone) {
    ld.telephone = `+${telephone}`;
  }
  const schema = `<script type="application/ld+json">${JSON.stringify(ld)}</script>`;
  return html.replace('</head>', schema + '</head>');
}

// ============================================================================
// generateHTML — main export (single-shot LLM call)
// ============================================================================
export async function generateHTML(prd, opts = {}) {
  const { usar_llm = true } = opts;
  if (!usar_llm) {
    throw new Error('usar_llm=false is not supported by the canonical OpenUI service');
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY not set in environment');

  const model = process.env.MODEL || 'claude-sonnet-4-6';
  const maxTokens = parseInt(process.env.MAX_TOKENS || '16000', 10);
  const baseUrl = process.env.ANTHROPIC_BASE_URL || KPA_BASE_URL;

  const systemPrompt = buildSystemPrompt(prd);
  const useXApiKey = baseUrl.includes('deployflow.com.br') || baseUrl.includes('localhost') || baseUrl.includes('127.0.0.1');
  const authHeader = useXApiKey ? { 'x-api-key': apiKey } : { 'Authorization': `Bearer ${apiKey}` };

  const response = await fetch(`${baseUrl}/messages`, {
    method: 'POST',
    headers: {
      ...authHeader,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      temperature: 0.7,
      system: systemPrompt,
      messages: [{ role: 'user', content: buildUserPrompt(prd) }],
      tools: [],
      thinking: { type: 'disabled' },
      stream: false,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`${response.status} ${errText}`);
  }

  const data = await response.json();
  const rawText = data.content?.find(b => b.type === 'text')?.text || '';
  const usage = data.usage || { input_tokens: 0, output_tokens: 0 };
  if (!rawText) throw new Error('Claude returned no text block');

  let html = extractHTML(rawText);
  html = injectDesignTokensIntoHead(html, prd);
  html = injectHeroPatternBackground(html, prd);
  html = applyEliteRefinements(html, prd);
  html = applyCinematicTexture(html, prd);
  html = applySignatureElement(html, prd);
  html = injectRequired(html, prd);

  return { html, model, attempts: 1, success: true, usage };
}

// ============================================================================
// Helpers for design tokens
// ============================================================================
const ARCHETYPES_NO_TAILWIND = new Set(['industrial-bold', 'corporate-trust', 'dark-futurist']);

function escapeJsStr(s) {
  return String(s).replace(/['\\]/g, c => '\\' + c);
}

// ============================================================================
// injectDesignTokensIntoHead — Inject CSS variables from PRD design_tokens
// into <head> so the LLM MUST use the correct colors (Single Source of Truth).
// ============================================================================
export function injectDesignTokensIntoHead(html, prd) {
  // Remove duplicate Tailwind CDN script if LLM added one
  if (html.includes('</head>')) {
    html = html.replace(/<script src=["']https:\/\/cdn\.tailwindcss\.com["']><\/script>/g, '');
  }

  // Extract design tokens from PRD
  const tokens = prd?.design_tokens?.tokens || {};
  const archetype = prd?.design_tokens?.archetype || 'editorial-asymmetric';

  if (!tokens || Object.keys(tokens).length === 0) {
    return html;
  }

  // Build :root CSS variables block
  const tokenEntries = Object.entries(tokens)
    .filter(([key]) => key.startsWith('--'))
    .map(([key, value]) => `    ${key}: ${value};`)
    .join('\n');

  // Build anti-slop directive + archetype marker
  const antiSlopDirective = `    /* ═══ DESIGN TOKENS (archetype: ${archetype}) ═══ */\n` +
    `    /* VOCÊ DEVE usar ESTAS variáveis CSS — NÃO inventar cores hardcoded. */\n` +
    `    /* Exemplo correto: background: var(--bg); color: var(--fg); */\n` +
    `    /* Exemplo ERRADO: background: #ffffff; color: #1a1a1a; */\n` +
    `    /* Se o hero precisa de cor diferente, use var(--accent) com opacidade. */\n`;

  const cssBlock = `<style>\n:root {\n${antiSlopDirective}${tokenEntries}\n}\n</style>`;

  // Inject before </head>
  if (html.includes('</head>')) {
    html = html.replace('</head>', `${cssBlock}\n</head>`);
  } else if (html.includes('<body')) {
    html = html.replace('<body', `${cssBlock}\n<body`);
  }

  return html;
}

// ============================================================================
// Hero Patterns SVG
// ============================================================================
const HERO_PATTERNS = {
  dots: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="1" fill="currentColor" opacity="0.10"/></svg>`,
  grid: `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path d="M 48 0 L 0 0 0 48" fill="none" stroke="currentColor" stroke-width="0.5" opacity="0.08"/></svg>`,
  topo: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M0 32 Q 16 16, 32 32 T 64 32" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.10"/><path d="M0 48 Q 16 32, 32 48 T 64 48" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.07"/></svg>`,
  diagonal: `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><path d="M-2 14 L 14 -2 M-2 26 L 26 -2 M-2 38 L 38 -2 M14 40 L 40 14 M26 40 L 40 26" stroke="currentColor" stroke-width="0.6" opacity="0.08"/></svg>`,
  blobby: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" preserveAspectRatio="none"><path d="M40,-65C50,-55 60,-50 65,-40C70,-30 60,-15 45,-5C30,5 15,5 5,15C-5,25 -10,40 -5,55C0,70 15,80 30,80C45,80 60,70 75,60C90,50 105,40 110,25C115,10 110,-10 100,-25C90,-40 70,-50 55,-60C40,-70 30,-75 40,-65Z" fill="currentColor" opacity="0.08"/></svg>`,
  noise: `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9"/></filter><rect width="100" height="100" filter="url(#n)" opacity="0.08"/></svg>`,
};

export function injectHeroPatternBackground(html, prd) {
  const patternSvgKey = prd?.design_tokens?.pattern_svg;
  if (!patternSvgKey || patternSvgKey === 'none') return html;
  const svg = HERO_PATTERNS[patternSvgKey];
  if (!svg) return html;

  const b64 = Buffer.from(svg).toString('base64');
  const css = `<style>
.bg-pattern {
  background-image: url("data:image/svg+xml;base64,${b64}");
  background-repeat: repeat;
  background-size: ${patternSvgKey === 'blobby' ? 'cover' : '32px 32px'};
}
</style>`;

  if (html.includes('</head>')) return html.replace('</head>', css + '</head>', 1);
  return css + html;
}

// ============================================================================
// applyEliteRefinements — alt text + scrim + text-shadow
// ============================================================================
function escapeHtmlAttr(s) {
  return String(s || '')
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"');
}

function nearestSectionTitle(html, imgIndex) {
  const head = html.slice(0, imgIndex);
  const m = head.match(/<h([1-3])[^>]*>([\s\S]*?)<\/h\1>/gi);
  if (m) {
    const last = m[m.length - 1].replace(/<[^>]+>/g, '').trim();
    if (last) return last;
  }
  return '';
}

export function applyEliteRefinements(html, prd) {
  const businessName = (prd?.business_name || '').trim();

  // 0. Luxo global: filtro de contraste/brilho + vinheta + bento asymmetry
  if (!/ELITE-LUXE-FILTER/.test(html)) {
    const luxe = `<style>
img { filter: contrast(1.1) brightness(0.9); }
[style*="background-image"]::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%);
}
[style*="background-image"] { position: relative; }
@media (max-width: 768px) {
  section.hero img, .hero img,
  section.hero [style*="background-image"], .hero [style*="background-image"] {
    min-height: 45vh; width: 100%; object-fit: cover; display: block;
  }
}
[class*="grid"]:has(> .card:nth-child(3)) { grid-template-columns: 1fr 1fr !important; }
[class*="grid"]:has(> .card:nth-child(3)) > .card:first-child { grid-column: 1 / -1; }
@media (max-width: 768px) {
  [class*="grid"]:has(> .card:nth-child(3)) { grid-template-columns: 1fr !important; }
}
/* ELITE-LUXE-FILTER */
</style>`;
    if (html.includes('</head>')) {
      html = html.replace('</head>', luxe + '</head>', 1);
    } else {
      html = luxe + html;
    }
  }

  // 1. Alt text em <img> sem alt
  html = html.replace(/<img\b([^>]*)>/gi, (full, attrs) => {
    if (/\balt\s*=/.test(attrs)) return full;
    const idx = html.indexOf(full);
    let title = nearestSectionTitle(html, idx);
    let alt = businessName;
    if (title) alt = businessName ? `${businessName} — ${title}` : title;
    else if (businessName) alt = businessName;
    else alt = 'imagem do site';
    return `<img${attrs} alt="${escapeHtmlAttr(alt)}">`;
  });

  // 2. Scrim de contraste AA em secoes com background-image
  html = html.replace(
    /(<[^>]+\bstyle\s*=\s*["'])([^"']*background-image[^"']*)(["'])/gi,
    (full, pre, styleBody, post) => {
      if (/ELITE-SCRIM/.test(styleBody)) return full;
      const scrim = 'linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5))';
      const sep = /,(?![^(]*\))/.test(styleBody) ? ',' : '';
      const newBody = styleBody.trim().replace(/;$/, '');
      return `${pre}${scrim}${sep} ${newBody}; /* ELITE-SCRIM */${post}`;
    }
  );

  // 3. Text-shadow em todo h1/h2
  html = html.replace(/<(h[12])\b([^>]*)>/gi, (full, tag, attrs) => {
    if (/\btext-shadow\b/.test(attrs)) return full;
    if (/\bstyle\s*=/.test(attrs)) {
      return full.replace(/style\s*=\s*(["'])([^"']*)\1/i,
        (s, q, body) => `style=${q}${body.replace(/;$/, '')}; text-shadow:0 2px 4px rgba(0,0,0,0.3)${q}`);
    }
    return `<${tag}${attrs} style="text-shadow:0 2px 4px rgba(0,0,0,0.3)">`;
  });

  return html;
}

// ============================================================================
// applySignatureElement — backdrop marquee
// ============================================================================
function escapeSignatureText(str) {
  return String(str || '')
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>');
}

export function applySignatureElement(html, prd) {
  if (/ELITE-SIGNATURE-APPLIED/.test(html)) return html;

  const businessName = (prd?.business_name || '').trim() || 'NEGOCIO';
  const name = escapeSignatureText(businessName);

  const heroRe = /<section\b[^>]*class\s*=\s*["'][^"']*hero[^"']*["'][^>]*>/i;
  const anySectionRe = /<section\b[^>]*>/i;
  const m = html.match(heroRe) || html.match(anySectionRe);
  if (!m) return html;

  const marquee = `<div class="elite-signature" aria-hidden="true" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-5deg);font-size:30vw;line-height:1;font-weight:900;white-space:nowrap;pointer-events:none;z-index:-1;opacity:0.05;color:transparent;-webkit-text-stroke:2px #888;text-stroke:2px #888;user-select:none;letter-spacing:-0.02em;/* ELITE-SIGNATURE-APPLIED */">${name}</div>`;

  let sectionTag = m[0];
  if (!/\bposition\s*:\s*relative/.test(sectionTag)) {
    if (/\bstyle\s*=\s*["']/.test(sectionTag)) {
      sectionTag = sectionTag.replace(/style\s*=\s*(["'])([^"']*)\1/i,
        (s, q, body) => `style=${q}${body.replace(/;$/, '')};position:relative${q}`);
    } else {
      sectionTag = sectionTag.replace(/<section\b([^>]*)>/i, `<section$1 style="position:relative">`);
    }
  }

  return html.replace(m[0], sectionTag + marquee);
}

// ============================================================================
// applyCinematicTexture — grain
// ============================================================================
const GRAIN_ARCHETYPES = new Set(['industrial-bold', 'dark-futurist', 'editorial-asymmetric']);

function buildGrainCss() {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">' +
    '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="2" stitchTiles="stitch"/></filter>' +
    '<rect width="100%" height="100%" filter="url(#g)"/></svg>';
  const b64 = Buffer.from(svg).toString('base64');
  return `<style>
.cinematic-grain::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 1;
  background-image: url("data:image/svg+xml;base64,${b64}");
  background-size: 120px 120px;
  opacity: 0.04;
  mix-blend-mode: overlay;
}
/* ELITE-GRAIN-APPLIED */
</style>`;
}

export function applyCinematicTexture(html, prd) {
  const archetype = prd?.design_system?.archetype || prd?.design_tokens?.archetype || 'editorial-asymmetric';
  if (!GRAIN_ARCHETYPES.has(archetype)) return html;
  if (/ELITE-GRAIN-APPLIED/.test(html)) return html;

  const grainCss = buildGrainCss();
  if (html.includes('</head>')) {
    html = html.replace('</head>', grainCss + '</head>', 1);
  } else {
    html = grainCss + html;
  }

  if (/<body\b[^>]*>/i.test(html)) {
    html = html.replace(/<body\b([^>]*)>/i, (full, attrs) => {
      if (/class\s*=/.test(attrs)) {
        return full.replace(/class\s*=\s*(["'])([^"']*)\1/i,
          (s, q, body) => `class=${q}${body} cinematic-grain${q}`);
      }
      return `<body${attrs} class="cinematic-grain">`;
    });
  }
  return html;
}
