// FraLib OpenUI Native - KPA Lab/DeployFlow + NVIDIA Fallback
// Cascata: DeployFlow (x-api-key) -> NVIDIA (OpenAI-compatible)

import http from 'http';

const PORT = parseInt(process.env.PORT || '7878', 10);
const HOST = process.env.HOST || '0.0.0.0';

// KPA Lab / DeployFlow (PRIMARY)
const ANTHROPIC_BASE_URL = process.env.ANTHROPIC_BASE_URL || 'https://deployflow.com.br/api/public/v1';
const MODEL = process.env.MODEL || 'claude-sonnet-4-6';
const MAX_TOKENS = parseInt(process.env.MAX_TOKENS || '64000', 10);
const API_KEY = process.env.ANTHROPIC_API_KEY;

// NVIDIA NIM (FALLBACK)
const NVIDIA_BASE_URL = process.env.NVIDIA_BASE_URL || 'https://integrate.api.nvidia.com/v1';
const NVIDIA_API_KEY = process.env.NVIDIA_API_KEY;

// NVIDIA Models cascade (free models) - TODOS SERÃO TENTADOS
const NVIDIA_MODELS = [
  'meta/llama-3.3-70b-instruct',
  'meta/llama-3.1-70b-instruct',
  'mistralai/mistral-large-2-instruct',
  'meta/llama-3.1-8b-instruct',
  '01-ai/yi-large',
  'deepseek-ai/deepseek-v4-pro',
  'nvidia/nemotron-3-ultra-550b-a55b',
];

function buildSystemPrompt(prd) {
  const archetype = prd?.design_tokens?.archetype || 'editorial-asymmetric';
  const layoutFam = prd?.layout_dna?.layout_family || 'asymmetric-magazine';
  const tokens = prd?.design_tokens || {};
  const palette = tokens.palette || {};
  const typo = tokens.typography || {};

  return `Voce faz parte do orquestrador SEO/GEO 2026 do FraLib.
Gere HTML completo a partir do DesignerPRD.

REGRAS OBRIGATORIAS:
- CTAs, provas, secoes obrigatorios
- Copy: numeros OU nomes proprios (nao generico)
- CTA: imperativo direto ('Agendar aula gratis')
- Max 2 paragrafos por secao
- Mobile-first (375px, 768px, 1440px)
- Lazy loading imagens
- JSON-LD LocalBusiness
- Open Graph + Twitter Cards
- Sem emojis como icone de UI
- Sem 'Bem-vindo' em lugar nenhum

DRAMA VISUAL (OBRIGATORIO):
- MONUMENTAL TYPE: h1 clamp(3rem, 13vw, 15rem), peso 800-900
- OVERLAP E ASSIMETRIA: margin-top negativo, colunas 70/30
- NEGATIVE SPACE: py-32/py-48 intencional
- SIGNATURE ELEMENT: linha decorativa / gradiente radial / tipografia vazada / forma geometrica
- PROFUNDIDADE: sombras com OFFSET direcional

ARCHETYPE: ${archetype}
LAYOUT: ${layoutFam}
PALETA: ${JSON.stringify(palette)}
TIPOGRAFIA: ${JSON.stringify(typo)}

Responda APENAS com HTML completo: <!DOCTYPE html> ate </html>.
NAO use markdown, fences, comentarios.`;
}

function buildUserPrompt(prd) {
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

Gere o HTML completo.`;
}

function extractHTML(text) {
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
  return text;
}

async function callKPA(systemPrompt, userPrompt) {
  const payload = {
    model: MODEL,
    max_tokens: MAX_TOKENS,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
    stream: false,
  };

  return new Promise((resolve, reject) => {
    const url = new URL(ANTHROPIC_BASE_URL + '/messages');
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01',
      },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            const parsed = JSON.parse(data);
            const html = extractHTML(parsed.content?.[0]?.text || '');
            resolve({ html, model: 'kpa-' + MODEL, usage: parsed.usage });
          } catch (e) {
            reject(new Error('KPA parse error: ' + e.message));
          }
        } else {
          reject(new Error(`KPA HTTP ${res.statusCode}: ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(JSON.stringify(payload));
    req.end();
  });
}

async function callNVIDIA(systemPrompt, userPrompt) {
  // TENTA TODOS OS MODELOS NVIDIA EM CASCATA
  for (let i = 0; i < NVIDIA_MODELS.length; i++) {
    const model = NVIDIA_MODELS[i];
    console.log(`[NVIDIA] Trying model ${i+1}/${NVIDIA_MODELS.length}: ${model}`);
    
    const payload = {
      model,
      max_tokens: MAX_TOKENS,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      stream: false,
      temperature: 0.3,
    };

    try {
      const result = await new Promise((resolve, reject) => {
        const url = new URL(NVIDIA_BASE_URL + '/chat/completions');
        const options = {
          hostname: url.hostname,
          port: url.port || 443,
          path: url.pathname,
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${NVIDIA_API_KEY}`,
          },
        };

        const req = http.request(options, (res) => {
          let data = '';
          res.on('data', (chunk) => data += chunk);
          res.on('end', () => {
            if (res.statusCode === 200) {
              try {
                const parsed = JSON.parse(data);
                const content = parsed.choices?.[0]?.message?.content || '';
                const html = extractHTML(content);
                resolve({ html, model: 'nvidia-' + model, usage: parsed.usage });
              } catch (e) {
                reject(new Error('NVIDIA parse error: ' + e.message));
              }
            } else {
              reject(new Error(`NVIDIA HTTP ${res.statusCode}: ${data}`));
            }
          });
        });

        req.on('error', reject);
        req.setTimeout(180000, () => reject(new Error('NVIDIA timeout')));
        req.write(JSON.stringify(payload));
        req.end();
      });
      
      if (result.html && result.html.length > 500) {
        console.log(`[NVIDIA] ✅ Success with model: ${model}`);
        return result;
      }
      throw new Error('Empty HTML from NVIDIA');
    } catch (e) {
      console.log(`[NVIDIA] ❌ Model ${model} failed: ${e.message}`);
      continue;
    }
  }
  throw new Error('All NVIDIA models failed');
}

async function generateHTML(prd) {
  const systemPrompt = buildSystemPrompt(prd);
  const userPrompt = buildUserPrompt(prd);

  // 1. Try KPA first (3 attempts with backoff for 529/rate limit)
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      console.log(`[KPA] Attempt ${attempt}/3`);
      return await callKPA(systemPrompt, userPrompt);
    } catch (e) {
      const msg = e.message;
      const isRateLimit = msg.includes('529') || msg.includes('overloaded') || 
                          msg.includes('sobrecarregado') || msg.includes('
