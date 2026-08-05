// FraLib OpenUI — Geracao HTML com retry em chunks para evitar 529
import http from 'http';
import {
  generateHTML, buildSystemPrompt, buildUserPrompt, extractHTML,
  injectDesignTokensIntoHead, injectHeroPatternBackground,
  applyEliteRefinements, applyCinematicTexture, applySignatureElement,
  injectRequired
} from './generate.js';

const PORT = parseInt(process.env.PORT || '3333', 10);
const HOST = process.env.HOST || '0.0.0.0';

function splitPRDIntoChunks(prd) {
  const sections = prd.sections || [];
  const totalSections = sections.length;
  const chunkSize = Math.ceil(totalSections / 4) || 1;
  return [
    { ...prd, sections: sections.slice(0, chunkSize), chunkLabel: 'HERO+TOP' },
    { ...prd, sections: sections.slice(chunkSize, chunkSize * 2), chunkLabel: 'MIDDLE-1' },
    { ...prd, sections: sections.slice(chunkSize * 2, chunkSize * 3), chunkLabel: 'MIDDLE-2' },
    { ...prd, sections: sections.slice(chunkSize * 3), chunkLabel: 'BOTTOM+FAQ' },
  ];
}

async function callLLMSingle(baseUrl, headers, model, maxTokens, systemPrompt, userPromptChunk, label) {
  const resp = await fetch(`${baseUrl}/messages`, {
    method: 'POST',
    headers: { ...headers, 'content-type': 'application/json' },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      temperature: 0.7,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPromptChunk }],
      tools: [],
      thinking: { type: 'disabled' },
      stream: false,
    }),
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Chunk ${label} failed: ${resp.status} ${errText}`);
  }
  const data = await resp.json();
  const rawText = data.content?.find(b => b.type === 'text')?.text || '';
  if (!rawText) throw new Error(`Chunk ${label} returned empty`);
  return { text: rawText, usage: data.usage || {} };
}

async function callLLMChunked(baseUrl, headers, model, maxTokens, systemPrompt, userPromptChunk, label) {
  const maxAttempts = 3;
  let lastErr = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await callLLMSingle(baseUrl, headers, model, maxTokens, systemPrompt, userPromptChunk, label);
    } catch (err) {
      lastErr = err;
      const is529 = err.message.includes("529") || err.message.includes("overloaded");
      if (is529 && attempt < maxAttempts) {
        const waitSec = 30 * attempt;
        console.log(`[/generate-chunked] Chunk ${label} attempt ${attempt} failed (529), waiting ${waitSec}s...`);
        await new Promise(r => setTimeout(r, waitSec * 1000));
      } else if (!is529) {
        throw err;
      }
    }
  }
  throw lastErr;
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(body)); } catch (e) { reject(new Error('Invalid JSON')); }
    });
    req.on('error', reject);
  });
}

function sendJSON(res, status, data) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || HOST}`);

  if (req.method === 'POST' && url.pathname === '/generate') {
    try {
      const body = await parseBody(req);
      const result = await generateHTML(body.designerPRD, body);
      return sendJSON(res, 200, result);
    } catch (err) {
      console.error('[/generate]', err.message);
      return sendJSON(res, 500, { success: false, error: err.message });
    }
  }

  if (req.method === 'POST' && url.pathname === '/generate-chunked') {
    try {
      const body = await parseBody(req);
      const prd = body.designerPRD;
      const apiKey = process.env.ANTHROPIC_API_KEY;
      const baseUrl = process.env.ANTHROPIC_BASE_URL || 'https://deployflow.com.br/api/public/v1';
      const model = process.env.MODEL || 'claude-sonnet-4-6';
      const maxTokens = parseInt(process.env.MAX_TOKENS || '64000', 10);

      const useXApiKey = baseUrl.includes('deployflow.com.br');
      const authHeader = useXApiKey ? { 'x-api-key': apiKey } : { 'Authorization': `Bearer ${apiKey}` };

      const systemPrompt = buildSystemPrompt(prd);
      const chunks = splitPRDIntoChunks(prd);
      const htmlParts = [];
      const totalUsage = { input_tokens: 0, output_tokens: 0 };

      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const chunkUserPrompt = `[CHUNK ${i + 1}/4: ${chunk.chunkLabel}]\n${buildUserPrompt(chunk)}`;
        console.log(`[/generate-chunked] Calling chunk ${i + 1}/4: ${chunk.chunkLabel}`);
        const result = await callLLMChunked(
          baseUrl, authHeader, model, Math.ceil(maxTokens / 4) + 2000,
          `${systemPrompt}\n\n# CHUNK ATUAL: ${chunk.chunkLabel}\nGere APENAS o pedaco de HTML correspondente a este chunk. Nao feche </html>, deixe aberto para concatenacao.`,
          chunkUserPrompt, chunk.chunkLabel
        );
        htmlParts.push(result.text);
        totalUsage.input_tokens += result.usage.input_tokens || 0;
        totalUsage.output_tokens += result.usage.output_tokens || 0;
        console.log(`[/generate-chunked] Chunk ${i + 1} OK, ${result.text.length} chars`);
      }

      // Concatenar partes do HTML
      let combinedHTML = htmlParts.join('\n');
      // Remover tags duplicadas de fechamento
      combinedHTML = combinedHTML.replace(/<\/html>/gi, '__HTML_CLOSE__');
      combinedHTML = combinedHTML.replace(/<\/body>/gi, '__BODY_CLOSE__');
      combinedHTML = combinedHTML.replace(/__HTML_CLOSE__|__BODY_CLOSE__/g, '');
      combinedHTML = combinedHTML + '\n</body>\n</html>';
      // Limpar <html> intermediario
      combinedHTML = combinedHTML.replace(/<html[^>]*>/gi, (match, offset) => offset === 0 ? match : '');

      let html = extractHTML(combinedHTML);
      html = injectDesignTokensIntoHead(html, prd);
      html = injectHeroPatternBackground(html, prd);
      html = applyEliteRefinements(html, prd);
      html = applyCinematicTexture(html, prd);
      html = applySignatureElement(html, prd);
      html = injectRequired(html, prd);

      return sendJSON(res, 200, {
        html, model, attempts: 4, success: true, usage: totalUsage, chunks: chunks.length,
      });
    } catch (err) {
      console.error('[/generate-chunked]', err.message);
      return sendJSON(res, 500, { success: false, error: err.message });
    }
  }

  if (req.method === 'GET' && url.pathname === '/health') {
    return sendJSON(res, 200, { status: 'ok', service: 'fralib-openui-chunked' });
  }

  sendJSON(res, 404, { error: 'Not found' });
});

server.listen(PORT, HOST, () => {
  console.log(`FraLib OpenUI (CHUNKED + RETRY) running at http://${HOST}:${PORT}`);
  console.log(`  POST /generate         — single-shot LLM call`);
  console.log(`  POST /generate-chunked — 4 chunked calls + retry on 529`);
  console.log(`  GET  /health           — health check`);
});

process.on('SIGTERM', () => { server.close(); process.exit(0); });
process.on('SIGINT', () => { server.close(); process.exit(0); });
