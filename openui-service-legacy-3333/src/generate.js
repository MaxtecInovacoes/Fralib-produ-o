// FraLib usa KPA Labs (kpalabz.com) — endpoint /v1/messages com header x-api-key
// Sem SDK para evitar o Bearer token que o KPA nao aceita
const KPA_BASE_URL = process.env.ANTHROPIC_BASE_URL || 'https://api.kpalabz.com/v1';

// ══════════════════════════════════════════════════════════════════════
// SYSTEM_PROMPT — O Curador, nao o carcereiro.
// Fase 2: deixa o LLM escolher 5-8 secoes dentro de LAYOUT_FAMILY.
// Archetype injetado pelo designerPRD.design_tokens.archetype.
// ══════════════════════════════════════════════════════════════════════
const SYSTEM_PROMPT_BASE = `Voce faz parte do orquestrador SEO/GEO 2026 do FraLib.

Sua funcao especifica: gerar o HTML final a partir do DesignerPRD.

Implemente:
- AGENTE 19 TRUST SIGNALS: certificados, cases, clientes, garantias, equipe, fotos, reviews, premios
- AGENTE 20 CONVERSION MAP: objetivo, CTA, prova, objecao, proxima acao por pagina
- AGENTE 14 CRO: CTAs, funis, lead magnets, provas, escassez, urgencia, garantias, WhatsApp
- AGENTE 16 TECHNICAL SEO: Core Web Vitals, lazy loading, AVIF/WebP, schema, JSON-LD
- AGENTE 17 AI SEARCH: perguntas, respostas, citacoes, dados, tabelas, FAQ, glossarios

REGRA: cada CTA, cada prova, cada secao deve ser OBRIGATORIA.

COPY DE ALTA CONVERSAO (skill fralib-conversion-copy):
- PROIBIDO: delve, leverage, robust, seamless, journey, ecosystem, vibrant, holistic, embark
- ESPECIFICO: cada frase com numero OU nome proprio (NAO 'clientes satisfeitos',
  SIM 'Joao, 42 anos, perdeu 12kg em 4 meses')
- CTA: comando direto no imperativo ('Agendar aula gratis', NAO 'Saiba mais')
- ESTRUTURA variavel: 1 paragrafo aqui, 6 itens ali, caso real depois
- TOM: socio explicando pra amigo, NAO marketing speak
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
- Sem 'Bem-vindo' em lugar nenhum

# INJECAO DE DRAMA (tensao visual obrigatoria — NUNCA site chapado)
O FraLib nao gera sites genericos; gera POSTERS INTERATIVOS DE LUXO. Cada
pagina precisa ter tensao, profundidade e um momento de impacto.

- MONUMENTAL TYPE: o <h1> do hero DEVE usar tipografia gigante
  (clamp(3rem, 13vw, 15rem)), leading-none, tracking-tighter, peso 800-900.
  O titulo domina a viewport — eh o elemento mais importante da pagina.
- OVERLAP E ASSIMETRIA: PROIBIDO alinhar tudo em caixas perfeitas e centralizar
  sem tensao. Use margin-top negativo ou translateY para fazer elementos
  sobreporem uns aos outros. Colunas desiguais (70/30, 60/40), nunca 50/50.
  O design DEVE ter atrito visual — elementos "respirando" e se cruzando.
- NEGATIVE SPACE: use espacos vazios INTENCIONAIS para criar foco (py-32/py-48).
  O vazio faz parte da composicao, nao eh acidente.
- SIGNATURE ELEMENT (OBRIGATORIO): toda pagina PRECISA de um elemento de
  assinatura que a torne memoravel — pelo menos UM destes:
  * um fio/linha decorativa longa cortando a pagina (border-top grossa ou SVG)
  * um gradiente radial de fundo atras do hero (luz de palco)
  * uma tipografia de contorno VAZADO gigante (texto com -webkit-text-stroke,
    transparente) posicionada atras do conteudo (absolute, z-index baixo)
  * uma forma geometrica abstrata em absolute (circulo/arco assimetrico)
- PROFUNDIDADE: sombras com OFFSET direcional (ex: 6px 6px 0 cor solida ou
  0 20px 40px rgba(0,0,0,.3)), nunca blur central sem direcao. Camadas > plano.`;

const LAYOUT_FAMILIES = {
  'split-hero': `Layout: SPLIT-HERO.
- Hero em duas colunas (texto esquerda 55% / imagem ou elemento visual direita 45%)
- Topologia zigzag: secao grande, depois pequena, depois grande (alternando)
- Pode usar testemunho gigante como prova de autoridade
- Footer com CTA secundario WhatsApp`,
  'center-hero': `Layout: CENTER-HERO.
- Hero centralizado stack (titulo no centro, sub, CTA embaixo, prova social)
- Secoes lineares (mesmo peso, fluxo vertical limpo)
- Numeros/stats aparecem 1x so, no topo apos hero
- Cards em grid 3-col desktop, 1-col mobile`,
  'fullscreen-hero': `Layout: FULLSCREEN-HERO.
- Hero ocupa 100vh, fundo escuro ou imagem full bleed
- Titulo gigante centralizado, CTA pill embaixo
- Scroll snap sections (cada uma ocupa viewport)
- Numeros animados quando entram na viewport`,
  'asymmetric-magazine': `Layout: EDITORIAL-ASYMMETRIC / MAGAZINE.
- Hero classico central (titulo serif gigante + sub + CTA)
- Secoes em grid 2-col com 1 feature grande + 2-3 cards menores
- Imagens editorial (retrato, close, ambiente)
- Tipografia serif display, espacamento generoso`,
  'bento-grid': `Layout: BENTO-GRID.
- Hero minimalista, foco em 1 CTA
- Features em bento grid (cards de tamanhos diferentes: 1 grande + 3-4 pequenos)
- Visao geral em 1 scroll (nao tem scrolling longo)
- Numeros em destaque, design compacto`,
  'classic-centered': `Layout: CLASSIC-CENTERED.
- Hero tradicional: titulo + sub + CTA + imagem
- Secoes centradas com max-width 800px
- Layout linear e conservador, foco no conteudo
- Numeros discretos, sem excentricidades`,
};

const ARCHETYPE_PROMPTS = {
  'industrial-bold': `Voce esta construindo um site NEO-INDUSTRIAL.
- Use border-2 ou border-4 com cores solidas (preto, vermelho intenso)
- Sombras SOLIDAS sem blur (shadow-[6px_6px_0px_0px_rgba(0,0,0,1)])
- Tipografia display GIGANTE em peso 800-900
- PROIBIDO qualquer border-radius > 4px no hero/CTAs
- Motion: parallax agressivo, marquee horizontal, scroll-linked
- SIGNATURE LAYOUT BOLD: tipografia MONUMENTAL 15vw (font-size:15vw;line-height:0.85) nos h1; grids 70/30 assimétricos (NUNCA 50/50); text-transform:uppercase; tracking:-0.03em; sem subtexto longo abaixo do h1; bordas EXPESSAS (border-4)`,
  'editorial-asymmetric': `Voce esta construindo um site EDITORIAL-ASYMMETRIC.
- Tipografia serif display (Fraunces ou Newsreader) em pesos 400-700
- Layout ASIMETRICO com colunas de tamanhos desiguais
- Espacamento ARY (py-24 py-32), paragrafos respiram
- Sombras LEVES (shadow-sm), bordas 0-8px
- Motion: fade sutil + reveal-soft, parallax apenas 0.10
- SIGNATURE LAYOUT LUXURY: whitespace EXAGERADO (py-32/py-48 mínimo); bordas FINÍSSIMAS 0.5px solid var(--primary) entre seções ou cards; tipografia serif display peso 300-400 com letter-spacing:0.03em; espaço negativo DOMINANTE — o vazio é o elemento principal de composição; linhas decorativas horizontais finas (1px) separando blocos`,
  'apple-minimalist': `Voce esta construindo um site APPLE-MINIMALIST.
- Tipografia SF Pro display, branco puro no fundo
- Hero centralizado stack, secoes lineares
- Bordas rounded-16px (rounded-2xl Tailwind) ou pill
- Sombras shadow-sm, espacamento generoso
- Motion: fade-minimal 200-400ms, hover-lift leve`,
  'dark-futurist': `Voce esta construindo um site DARK-FUTURIST.
- Fundo #0A0A0F ou similar, texto neon (cyan ou violet)
- Tipografia grotesk geometrica (Unbounded ou Space Grotesk)
- Bordas sharp (0-2px), nenhum radius > 0px exceto pill para CTAs
- Motion: glitch, magnetic-3d, scan-lines, data-stream
- Tom cyber, futurista, com glow`,
  'organic-warm': `Voce esta construindo um site ORGANIC-WARM.
- Paleta terrosa (marrom + amber + creme), papel cru de fundo
- Tipografia Quicksand (sans humanista) + Fraunces (serif quente)
- Bordas 12-24px (radius generoso), sombras LEVES ou zero
- Pattern de fundo topo/folha sutil (svg)
- Motion: fade-organic 300-900ms, hover-grow gentil`,
  'corporate-trust': `Voce esta construindo um site CORPORATE-TRUST.
- Tipografia serif classica (Playfair Display) + sans (Source Sans)
- Paleta navy + gold, espacamento generoso, layout linear
- Bordas sharp (0px), sombras flat (shadow-flat ou zero)
- Motion: minimal-fade 200-600ms, underline-reveal nos links
- Tom: profissional, conservador, autoridade clara`,
};

// Bloco final do system prompt, varia por archetype + layout_family.
function buildSystemPrompt(prd) {
  const archetype = (prd?.design_tokens?.archetype) || 'editorial-asymmetric';
  const layoutFam = (prd?.layout_dna?.layout_family) || 'asymmetric-magazine';
  const archetypeBrief = (prd?.design_system?.archetype_briefing)
    || ARCHETYPE_PROMPTS[archetype]
    || ARCHETYPE_PROMPTS['editorial-asymmetric'];
  const layoutBrief = LAYOUT_FAMILIES[layoutFam] || LAYOUT_FAMILIES['asymmetric-magazine'];
  const sectionRange = (prd?.layout_dna?.section_count_range) || [5, 8];
  const tokens = prd?.design_tokens || {};
  const palette = tokens.palette || {};
  const typo = tokens.typography || {};

  // Polo BOLD (industrial-bold, dark-futurist): impacto cinematografico.
  // Exige as classes semanticas do design-system-tokens.css para os ~500
  // tokens (radius 0, shadow 8px, skew -5deg, uppercase) ativarem.
  const BOLD_ARCHETYPES = new Set(['industrial-bold', 'dark-futurist']);
  const boldBlock = BOLD_ARCHETYPES.has(archetype) ? [
    '',
    '# DIRETRIZES DE POLO BOLD (OBRIGATORIO — impacto cinematografico)',
    '- HERO: o <h1> DEVE ter a classe .hero-headline e no MAXIMO 3 palavras.',
    '- SECOES: cada <section> DEVE ter a classe .section-pole.',
    '- CARDS: cada card/box DEVE ter a classe .card-pole.',
    '- BOTOES: cada CTA/<button>/<a class="btn"> DEVE ter a classe .btn-pole.',
    '- Sem paragrafos longos no hero: frases curtas de impacto.',
    '- O uppercase/italico do titulo vem do CSS (data-pole); NAO force inline.',
  ].join('\n') : '';

  return [
    SYSTEM_PROMPT_BASE,
    '',
    `# DESIGN BRIEFING INJETADO (AUTORITATIVO — NAO INVENTE OUTROS VALORES)`,
    archetypeBrief,
    boldBlock,
    '',
    `# LAYOUT_FAMILY: ${layoutFam}`,
    layoutBrief,
    '',
    `# ESCOPO: gere entre ${sectionRange[0]} e ${sectionRange[1]} secoes (range, NAO fixo).`,
    'Escolha secoes que contem a historia do lead no content_flow definido.',
    'NAO force estrutura rigida.',
    '',
    '# TOKENS AUTORITATIVOS (use exatamente)',
    `palette: ${JSON.stringify(palette)}`,
    `typography: ${JSON.stringify(typo)}`,
    `radius: ${JSON.stringify(tokens.radius || {})}`,
    '',
    '# REGRAS ANTI-CLICHE',
    '- NAO use blue-500 / red-500 / gray-500 / slate-9xx (defaults Tailwind)',
    '- NAO use font-family sem Google Fonts link rel',
    '- NAO force 6 secoes fixas',
    '- NAO use rounded-md default sem justificativa do archetype',
    '- PALETTE PRIMARY eh DEFINITIVA. Se faltar, falha em vez de cair no default',
    '',
    '# RESPONSE FORMAT',
    'Responda APENAS com HTML completo: <!DOCTYPE html> ate </html>.',
    'NAO use markdown, fences, comentarios explicativos, tool_code.',
    'NAO corte no meio. O tailwind.config sera injetado automaticamente pelo servico.',
  ].join('\n');
}

// ── helpers ─────────────────────────────────────────────────────────────────

function buildUserPrompt(prd) {
  const sectionsTexto = (prd.sections || [])
    .map(s => `- ${s.name}: ${s.title} | ${(s.content || '').slice(0, 100)}`)
    .join('\n');
  return `Negócio: ${prd.business_name || ''}
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

function extractHTML(text) {
  text = text.trim();
  // Remove code fences
  for (const prefix of ['```html', '```HTML', '```']) {
    if (text.startsWith(prefix)) {
      text = text.slice(prefix.length).trimStart();
    }
  }
  if (text.endsWith('```')) {
    text = text.slice(0, -3).trimEnd();
  }

  // Match <!DOCTYPE ... </html>
  let match = text.match(/<!DOCTYPE html>[\s\S]*?<\/html>/i);
  if (match) return match[0];

  // Match <html ... </html>
  match = text.match(/<html[\s\S]*?<\/html>/i);
  if (match) return match[0];

  // Partial: has DOCTYPE/html but no closing — close it
  if (/<!DOCTYPE html>|<html/i.test(text)) {
    if (!/<\/body>/i.test(text)) text += '\n</body>';
    if (!/<\/html>/i.test(text))  text += '\n</html>';
    return text;
  }

  return text;
}

function injectRequired(html, prd) {
  html = injectLGPD(html);
  html = injectFavicon(html, prd);
  html = injectJSONLD(html, prd);
  html = injectMotion(html);
  html = injectFloatingWhatsApp(html, prd);
  return html;
}

function injectFloatingWhatsApp(html, prd) {
  if (/wa-floating/i.test(html)) return html;
  const ctaUrl = (prd?.ctas || []).find(c => /wa\.me/.test(c.url || ''))?.url || 'https://wa.me/';
  const btn = `<!-- FLOATING-WHATSAPP-CRO -->
<a href="${ctaUrl}" target="_blank" rel="noopener"
   class="wa-floating" aria-label="Fale conosco pelo WhatsApp"
   style="position:fixed;bottom:24px;right:24px;z-index:9998;
          width:60px;height:60px;border-radius:50%;
          background:#25D366;color:#fff;
          display:flex;align-items:center;justify-content:center;
          box-shadow:0 4px 16px rgba(37,211,102,0.4);
          transition:transform 0.2s ease,box-shadow 0.2s ease;
          text-decoration:none;animation:wa-pulse 2s ease-in-out infinite">
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

export function injectLGPD(html) {
  if (/lgpd-banner/i.test(html)) return html;
  // Mini-toast no canto inferior esquerdo: max-height 15vh, nao cobre o CTA.
  // Botao X visivel para o Vision LLM nao considerar "obstaculo".
  const banner = `<div id="lgpd-banner" role="dialog" aria-label="Aviso de privacidade" style="position:fixed;left:16px;bottom:16px;max-width:340px;max-height:15vh;overflow:auto;background:linear-gradient(135deg, color-mix(in srgb, var(--primary, #1a1a1a) 82%, transparent), color-mix(in srgb, var(--accent, #333) 82%, transparent));backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;z-index:9999;font-family:system-ui,sans-serif;font-size:13px;line-height:1.4;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.18)"><div style="flex:1">Usamos cookies e dados para melhorar sua experiencia. Ao continuar, voce concorda com nossa <a href="/privacidade" style="color:#4ade80;text-decoration:underline">Politica de Privacidade</a> e com a LGPD.</div><div style="display:flex;gap:6px;align-items:center"><button onclick="document.getElementById('lgpd-banner').style.display='none';try{localStorage.setItem('lgpd-accepted','1')}catch(e){}" style="background:#22c55e;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-weight:600;white-space:nowrap">Aceitar</button><button aria-label="Fechar aviso" onclick="document.getElementById('lgpd-banner').style.display='none';try{localStorage.setItem('lgpd-dismissed','1')}catch(e){}" style="background:transparent;color:#fff;border:1px solid #555;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:16px;line-height:1;display:flex;align-items:center;justify-content:center;flex-shrink:0">×</button></div></div><script>try{if(localStorage.getItem("lgpd-accepted")==="1"||localStorage.getItem("lgpd-dismissed")==="1"||localStorage.getItem("lgpd-rejected")==="1"){document.addEventListener("DOMContentLoaded",function(){var b=document.getElementById("lgpd-banner");if(b)b.style.display="none";});}}catch(e){}</script>`;
  return html.replace('</body>', banner + '</body>');
}

function injectFavicon(html, prd) {
  if (/data:image\/svg/i.test(html) || /rel="icon"/i.test(html)) return html;
  const primary = (prd?.paleta?.primary) || '#FF5722';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="${primary}"/><text x="16" y="22" font-size="18" text-anchor="middle" fill="#fff" font-family="sans-serif" font-weight="bold">F</text></svg>`;
  const b64 = Buffer.from(svg).toString('base64');
  const link = `<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,${b64}"><link rel="apple-touch-icon" href="data:image/svg+xml;base64,${b64}">`;
  return html.replace('</head>', link + '</head>');
}

function escapeJSONLD(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function injectJSONLD(html, prd) {
  if (/application\/ld\+json/i.test(html)) return html;
  const nome     = escapeJSONLD(prd?.business_name || 'Negocio');
  const cidade   = escapeJSONLD(prd?.cidade || '');
  const segmento = escapeJSONLD(prd?.segmento || 'negocio local');
  let telephone = '';
  for (const cta of (prd?.ctas || [])) {
    const digits = (cta.url || '').replace(/\D/g, '');
    if (digits.startsWith('55') && digits.length >= 12) {
      telephone = `"telephone": "+${digits}",`;
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
    ld.telephone = `+${telephone.match(/\d+/g).join('')}`;
  }
  const schema = `<script type="application/ld+json">${JSON.stringify(ld)}</script>`;
  return html.replace('</head>', schema + '</head>');
}

function injectMotion(html) {
  const hasGSAP    = /cdn\.jsdelivr\.net\/npm\/gsap/i.test(html);
  const hasLenis   = /cdn\.jsdelivr\.net\/npm\/lenis/i.test(html);
  const hasInit    = /new Lenis/i.test(html);

  const lenisCSS  = `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.css">`;
  const lenisJS   = `<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.js"></script>`;
  const gsapJS    = `<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script><script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>`;

  const initScript = `<script>
(function(){
  'use strict';
  if(typeof Lenis!=='undefined'){
    var lenis=new Lenis({duration:1.2,easing:function(t){return Math.min(1,1.001-Math.pow(2,-10*t));},direction:'vertical',gestureDirection:'vertical',smooth:true,smoothTouch:false,touchMultiplier:2,wheelMultiplier:1,lerp:0.1});
    function raf(time){lenis.raf(time);requestAnimationFrame(raf);}
    requestAnimationFrame(raf);
    if(typeof gsap!=='undefined'&&typeof ScrollTrigger!=='undefined'){gsap.registerPlugin(ScrollTrigger);lenis.on('scroll',ScrollTrigger.update);gsap.ticker.add(function(time){lenis.raf(time*1000);});gsap.ticker.lagSmoothing(0);}
  } else if(typeof gsap!=='undefined'&&typeof ScrollTrigger!=='undefined'){gsap.registerPlugin(ScrollTrigger);}
  document.addEventListener('DOMContentLoaded',function(){
    if(typeof gsap==='undefined')return;
    if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    if(typeof ScrollTrigger!=='undefined'){
      gsap.utils.toArray('section').forEach(function(section,i){
        gsap.from(section,{opacity:0,y:60,duration:0.8,delay:i*0.1,ease:'power2.out',scrollTrigger:{trigger:section,start:'top 85%',end:'top 50%',toggleActions:'play none none reverse'}});
      });
    }
  });
})();
</script>`;

  if (!hasLenis || !hasGSAP) {
    let assets = '';
    if (!hasLenis) assets += lenisCSS + lenisJS;
    if (!hasGSAP)  assets += gsapJS;
    html = html.replace('</head>', assets + '</head>');
  }

  if (!hasInit) {
    html = html.replace('</body>', initScript + '</body>');
  }

  return html;
}

// ── main export ─────────────────────────────────────────────────────────────

export async function generateHTML(prd, opts = {}) {
  const { usar_llm = true } = opts;

  if (!usar_llm) {
    throw new Error('usar_llm=false is not supported by the canonical OpenUI service');
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY not set in environment');
  }

  const model     = process.env.MODEL || 'claude-sonnet-4-6';
  const maxTokens = parseInt(process.env.MAX_TOKENS || '16000', 10);
  const baseUrl   = process.env.ANTHROPIC_BASE_URL || KPA_BASE_URL;

  // Fase 2: system prompt vir a curador (archetype + layout_family).
  const systemPrompt = buildSystemPrompt(prd);

  // Detecta se endpoint aceita x-api-key (KPA Labs / DeployFlow) ou Bearer (LiteLLM/Anthropic)
  const useXApiKey = baseUrl.includes('kpalabz.com')
    || baseUrl.includes('deployflow.com.br')
    || baseUrl.includes('localhost')
    || baseUrl.includes('127.0.0.1');
  const authHeader = useXApiKey
    ? { 'x-api-key': apiKey }
    : { 'Authorization': `Bearer ${apiKey}` };

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
      // temperature 0.7 da variacao visual sem perder coerencia do archetype.
      temperature: 0.7,
      system: systemPrompt,
      messages: [{ role: 'user', content: buildUserPrompt(prd) }],
      tools: [],   // impede o proxy KPA de devolver <tool_code>
      thinking: { type: 'disabled' }, // evita thinking blocks em proxies
      stream: false, // essencial: LiteLLM proxy retorna SSE mesmo sem stream:true
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`${response.status} ${errText}`);
  }

  const data = await response.json();
  const rawText = data.content?.find(b => b.type === 'text')?.text || '';
  const usage = data.usage || { input_tokens: 0, output_tokens: 0 };
  if (!rawText) {
    throw new Error('Claude returned no text block');
  }
  let html = extractHTML(rawText);

  // Fase 2: injeta tailwind.config (paleta/tipografia/radius) + Hero Patterns
  // SVG baseado em design_tokens/pattern_svg ANTES de injectRequired.
  html = injectDesignTokensIntoHead(html, prd);
  html = injectHeroPatternBackground(html, prd);
  // Fase "Busca pelo 9.0": rede de segurança determinística de acessibilidade.
  // Alt text + scrim de contraste AA + text-shadow — NÃO depende do LLM acertar.
  html = applyEliteRefinements(html, prd);
  // Fase 9.1 — Injeção de Drama: grão cinematográfico (grain) seletivo por archetype.
  html = applyCinematicTexture(html, prd);
  // Fase 9.2 — Signature Element: backdrop marquee determinístico (nome em
  // contorno vazado, 30vw, -5deg, opacity 0.05) — força fator UAU sem depender do LLM.
  html = applySignatureElement(html, prd);
  html = injectRequired(html, prd);

  return { html, model, attempts: 1, success: true, usage };
}


// ══════════════════════════════════════════════════════════════════════
// Fase 2 — Injetor de Design Tokens no <head> do HTML
// Gera <script src="tailwindcss CDN"> + <script>tailwind.config = {...}</script>
// com cores/tipografia/radius autorais vindos do design_tokens (PRD).
// ══════════════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════════════
// Fase 2/3 — Injetor de Design Tokens no <head> do HTML.
// CONSOME design_system novo do Builder (Fase 2) quando presente, com
// fallback para design_tokens (Fase 1).
//
// Regra anti-cliche: archetypes high-density (industrial-bold,
// corporate-trust, dark-futurist) NAO recebem Tailwind CDN — eles exigem
// CSS escrito a mao para o look "raw". Tailwind so para archetypes
// permissivos (apple-minimalist, organic-warm, editorial-asymmetric).
// ══════════════════════════════════════════════════════════════════════

const ARCHETYPES_NO_TAILWIND = new Set([
  'industrial-bold',
  'corporate-trust',
  'dark-futurist',
]);

function escapeJsStr(s) {
  return String(s).replace(/['\\]/g, (c) => '\\' + c);
}

function buildGoogleFontsUrl(display, body, mono) {
  const families = [display, body, mono].filter(Boolean);
  if (!families.length) return '';
  // Pesos canonicos cobrem 99% dos casos.
  return 'https://fonts.googleapis.com/css2?family=' +
    families.map(f => f.replace(/\s+/g, '+') + ':wght@400;500;600;700;900').join('&family=') +
    '&display=swap';
}

function buildCssVarsBlock(palette, typo, radius) {
  // Vars CSS deterministicas: nada de Tailwind utility no :root.
  return `<style>:root {
  --primary: ${palette.primary || '#111111'};
  --accent: ${palette.accent || '#222222'};
  --ink: ${palette.ink || '#FFFFFF'};
  --paper: ${palette.paper || '#FAFAFA'};
  --surface: ${palette.surface || '#F0F0F0'};
  --radius-default: ${radius.default || '8px'};
  --radius-sharp: ${radius.sharp || '0px'};
  --radius-pill: ${radius.pill || '9999px'};
  --font-display: '${typo.display || 'Inter'}', sans-serif;
  --font-body: '${typo.body || 'Inter'}', sans-serif;
  --font-mono: '${typo.mono || 'monospace'}', monospace;
}
body { background: var(--paper); color: var(--ink); font-family: var(--font-body); }
h1, h2, h3 { font-family: var(--font-display); }
code, pre, .mono { font-family: var(--font-mono); }
/* Override autoritativo de radius — archetypes high-density usam sharp */
.btn, button { border-radius: var(--radius-default); }
</style>`;
}

function injectDesignTokensIntoHead(html, prd) {
  // Fase 3 - prioriza design_system (campos Builder), fallback design_tokens.
  const ds = prd?.design_system || {};
  const tokens = prd?.design_tokens || {};
  if (!tokens.palette && !ds.google_fonts_url) {
    return html;
  }

  const palette = tokens.palette || {};
  const typo = tokens.typography || {};
  const radius = tokens.radius || {};
  const archetype = ds.archetype || tokens.archetype || 'editorial-asymmetric';
  const allowTailwind = !ARCHETYPES_NO_TAILWIND.has(archetype);

  let preconnect = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>';
  // 1. Google Fonts: prioriza ds.google_fonts_url canonico do Builder.
  let googleFonts = '';
  if (ds.google_fonts_url) {
    googleFonts = `<link href="${ds.google_fonts_url}" rel="stylesheet">`;
  } else if (typo.display || typo.body || typo.mono) {
    const url = buildGoogleFontsUrl(typo.display, typo.body, typo.mono);
    googleFonts = `<link href="${url}" rel="stylesheet">`;
  }

  // 2. Tailwind: prioriza ds.tailwind_config_inline autoritativo do Builder.
  //    So injeta CDN se archetype permitir e LLM estiver usando Tailwind de fato.
  let tailwindConfig = '';
  if (ds.tailwind_config_inline) {
    tailwindConfig = ds.tailwind_config_inline;
  } else if (allowTailwind && tokens.palette) {
    // Fallback: monta config inline a partir dos tokens.
    tailwindConfig = `<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        'primary': '${escapeJsStr(palette.primary)}',
        'accent':  '${escapeJsStr(palette.accent)}',
        'ink':     '${escapeJsStr(palette.ink)}',
        'paper':   '${escapeJsStr(palette.paper)}',
        'surface': '${escapeJsStr(palette.surface)}',
      },
      fontFamily: {
        display: ['${escapeJsStr(typo.display || 'Inter')}', 'sans-serif'],
        body:    ['${escapeJsStr(typo.body || 'Inter')}', 'sans-serif'],
        mono:    ['${escapeJsStr(typo.mono || 'JetBrains Mono')}', 'monospace'],
      },
      borderRadius: {
        'sharp':   '${escapeJsStr(radius.sharp || '0px')}',
        'default': '${escapeJsStr(radius.default || '8px')}',
        'pill':    '${escapeJsStr(radius.pill || '9999px')}',
      },
    },
  },
};
</script>`;
  }

  // 3. Tailwind CDN: so se (a) archetype permite E (b) ha tailwindConfig.
  //    O Quality Gate pune 'tailwind-cdn-sem-config' (-20). So faz sentido
  //    injetar CDN se ha config autoritativo junto.
  const tailwindBootstrap = (allowTailwind && tailwindConfig)
    ? '<script src="https://cdn.tailwindcss.com"></script>'
    : '';

  // 4. CSS vars no :root (sempre — util tanto com quanto sem Tailwind).
  const cssVars = (palette && typo)
    ? buildCssVarsBlock(palette, typo, radius)
    : '';

  const block = preconnect + googleFonts + tailwindBootstrap + tailwindConfig + cssVars;

  if (html.includes('</head>')) {
    // Remove CDN preexistente (LLM as vezes coloca mesmo apos instruido a nao).
    html = html.replace(/<script src=["']https:\/\/cdn\.tailwindcss\.com["']><\/script>/g, '');
    return html.replace('</head>', block + '</head>', 1);
  }
  return block + html;
}


// ══════════════════════════════════════════════════════════════════════
// Fase 2 — Hero Patterns SVG (5 padroes: dots, grid, topo, diagonal, blobby)
// Pattern choice vem de design_tokens.pattern_svg. (none -> nao injeta)
// ══════════════════════════════════════════════════════════════════════
const HERO_PATTERNS = {
  dots: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="1" fill="currentColor" opacity="0.10"/></svg>`,
  grid: `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path d="M 48 0 L 0 0 0 48" fill="none" stroke="currentColor" stroke-width="0.5" opacity="0.08"/></svg>`,
  topo: `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M0 32 Q 16 16, 32 32 T 64 32" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.10"/><path d="M0 48 Q 16 32, 32 48 T 64 48" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.07"/></svg>`,
  diagonal: `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><path d="M-2 14 L 14 -2 M-2 26 L 26 -2 M-2 38 L 38 -2 M14 40 L 40 14 M26 40 L 40 26" stroke="currentColor" stroke-width="0.6" opacity="0.08"/></svg>`,
  blobby: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" preserveAspectRatio="none"><path d="M40,-65C50,-55 60,-50 65,-40C70,-30 60,-15 45,-5C30,5 15,5 5,15C-5,25 -10,40 -5,55C0,70 15,80 30,80C45,80 60,70 75,60C90,50 105,40 110,25C115,10 110,-10 100,-25C90,-40 70,-50 55,-60C40,-70 30,-75 40,-65Z" fill="currentColor" opacity="0.08"/></svg>`,
  noise: `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9"/></filter><rect width="100" height="100" filter="url(#n)" opacity="0.08"/></svg>`,
};

// ══════════════════════════════════════════════════════════════════════
// Fase "Busca pelo 9.0" — Rede de Segurança de Acessibilidade (determinística).
// O LLM falha em alt-text e contraste AA mesmo quando pedido; o Vision LLM
// penaliza isso (Start Academia tirou 7.5 por isso). Estas regras são
// aplicadas NO HTML após a geração, sem depender do LLM acertar:
//   1. alt: toda <img> sem alt recebe "Nome — Título da seção".
//   2. contraste AA: seção com background-image ganha scrim
//      linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5)) como camada superior.
//   3. text-shadow: reforço de legibilidade em todo h1/h2.
// Idempotente: pula se já aplicado.
// ══════════════════════════════════════════════════════════════════════

function escapeHtmlAttr(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Conjectura o "título da seção" mais próximo: sobe no DOM pro <h1/h2/h3>
// anterior, senão usa o business_name. Evita entity-tags {{...}} no HTML.
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

  // 0. Filtro de "luxo" global (Fase 9.2, Passo 5): equaliza fotos de bancos
  //    diferentes com contraste/brilho e vinheta, criando atmosfera cinematografica.
  //    Idempotente via guarda ELITE-LUXE-FILTER.
  if (!/ELITE-LUXE-FILTER/.test(html)) {
    const luxe = `<style>
img { filter: contrast(1.1) brightness(0.9); }
[style*="background-image"]::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%);
}
[style*="background-image"] { position: relative; }
/* Hero mobile: garante protagonismo da imagem (nao esmagada pelo texto) */
@media (max-width: 768px) {
  section.hero img, .hero img,
  section.hero [style*="background-image"], .hero [style*="background-image"] {
    min-height: 45vh; width: 100%; object-fit: cover; display: block;
  }
}
/* ELITE-LUXE-FILTER */
/* Fase 9.3 — Bento Asymmetry: quebra simetria de grids com 3+ cards.
   Regra: grid com 3+ .cards diretos vira bento (1 card grande no topo,
   2 cards pequenos abaixo). Idempotente pelo guarda acima. */
[class*="grid"]:has(> .card:nth-child(3)) {
  grid-template-columns: 1fr 1fr !important;
}
[class*="grid"]:has(> .card:nth-child(3)) > .card:first-child {
  grid-column: 1 / -1;
}
@media (max-width: 768px) {
  [class*="grid"]:has(> .card:nth-child(3)) {
    grid-template-columns: 1fr !important;
  }
}
</style>`;
    if (html.includes('</head>')) {
      html = html.replace('</head>', luxe + '</head>', 1);
    } else {
      html = luxe + html;
    }
  }

  // 1. Alt text em <img> sem alt.
  html = html.replace(/<img\b([^>]*)>/gi, (full, attrs) => {
    if (/\balt\s*=/.test(attrs)) return full; // já tem alt
    // índice desta <img> no html original p/ achar o heading mais próximo.
    const idx = html.indexOf(full);
    let title = nearestSectionTitle(html, idx);
    let alt = businessName;
    if (title) alt = businessName ? `${businessName} — ${title}` : title;
    else if (businessName) alt = businessName;
    else alt = 'imagem do site';
    return `<img${attrs} alt="${escapeHtmlAttr(alt)}">`;
  });

  // 2. Scrim de contraste AA em seções com background-image.
  //    Injeta gradiente escuro como PRIMEIRO background (camada superior),
  //    preservando a imagem abaixo. Idempotente via guarda de "ELITE-SCRIM".
  html = html.replace(
    /(<[^>]+\bstyle\s*=\s*["'])([^"']*background-image[^"']*)(["'])/gi,
    (full, pre, styleBody, post) => {
      if (/ELITE-SCRIM/.test(styleBody)) return full;
      const scrim = 'linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5))';
      // Se já há múltiplos backgrounds, o gradiente entra antes.
      const sep = /,(?![^(]*\))/.test(styleBody) ? ',' : '';
      const newBody = styleBody.trim().replace(/;$/, '');
      return `${pre}${scrim}${sep} ${newBody}; /* ELITE-SCRIM */${post}`;
    }
  );

  // 3. Text-shadow em todo h1/h2 (legibilidade sobre qualquer fundo).
  html = html.replace(/<(h[12])\b([^>]*)>/gi, (full, tag, attrs) => {
    if (/\btext-shadow\b/.test(attrs) || /\bstyle\s*=/.test(attrs) && /text-shadow/.test(attrs)) {
      return full;
    }
    if (/\bstyle\s*=/.test(attrs)) {
      // anexa ao style existente
      return full.replace(/style\s*=\s*(["'])([^"']*)\1/i,
        (s, q, body) => `style=${q}${body.replace(/;$/, '')}; text-shadow:0 2px 4px rgba(0,0,0,0.3)${q}`);
    }
    return `<${tag}${attrs} style="text-shadow:0 2px 4px rgba(0,0,0,0.3)">`;
  });

  return html;
}

// ══════════════════════════════════════════════════════════════════════
// Fase 9.2 — Signature Element: Backdrop Marquee determinístico (Node).
// O LLM tem "medo" do fator UAU e entrega sites template-like. Forçamos,
// no pós-processamento, uma camada de "design de revista": o NOME do
// negócio em contorno vazado (text-stroke), gigante (30vw), girado -5deg,
// à opacidade 0.05, atrás do conteúdo da Hero. Não depende da criatividade
// da IA. Idempotente (guarda ELITE-SIGNATURE-APPLIED).
// ══════════════════════════════════════════════════════════════════════
function escapeSignatureText(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function applySignatureElement(html, prd) {
  if (/ELITE-SIGNATURE-APPLIED/.test(html)) return html;       // idempotente

  const businessName = (prd?.business_name || '').trim() || 'NEGOCIO';
  const name = escapeSignatureText(businessName);

  // Localiza a Hero: prefere <section class*="hero">, senão a 1ª <section>.
  const heroRe = /<section\b[^>]*class\s*=\s*["'][^"']*hero[^"']*["'][^>]*>/i;
  const anySectionRe = /<section\b[^>]*>/i;
  const m = html.match(heroRe) || html.match(anySectionRe);
  if (!m) return html;

  const marquee = `<div class="elite-signature" aria-hidden="true" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-5deg);font-size:30vw;line-height:1;font-weight:900;white-space:nowrap;pointer-events:none;z-index:-1;opacity:0.05;color:transparent;-webkit-text-stroke:2px #888;text-stroke:2px #888;user-select:none;letter-spacing:-0.02em;/* ELITE-SIGNATURE-APPLIED */">${name}</div>`;

  // Garante position:relative na Hero p/ o absolute ancorar nela (e z-index:-1
  // ficar acima do fundo da seção, abaixo do conteúdo).
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

// ══════════════════════════════════════════════════════════════════════
// Fase 9.1 — Injeção de Drama: Grain Cinematográfico (determinístico, Node).
// Quebra o "site chapado" com granulação sutil (feTurbulence SVG).
// HÍBRIDO: aplica SÓ em archetypes de impacto (industrial-bold,
// dark-futurist, editorial-asymmetric). Minimalistas (apple/zen/organic)
// ficam limpos. Idempotente (guarda CINEMATIC-GRAIN).
// ══════════════════════════════════════════════════════════════════════
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
  const archetype = (prd?.design_system?.archetype)
    || (prd?.design_tokens?.archetype)
    || 'editorial-asymmetric';
  if (!GRAIN_ARCHETYPES.has(archetype)) return html;       // minimalistas: limpos
  if (/ELITE-GRAIN-APPLIED/.test(html)) return html;         // idempotente

  const grainCss = buildGrainCss();

  // Injeta o CSS no <head>.
  if (html.includes('</head>')) {
    html = html.replace('</head>', grainCss + '</head>', 1);
  } else {
    html = grainCss + html;
  }

  // Anexa a classe .cinematic-grain ao <body> (ou cria <body> se não houver).
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

function injectHeroPatternBackground(html, prd) {
  const patternSvgKey = prd?.design_tokens?.pattern_svg;
  if (!patternSvgKey || patternSvgKey === 'none') {
    return html;
  }
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

  if (html.includes('</head>')) {
    return html.replace('</head>', css + '</head>', 1);
  }
  return css + html;
}
