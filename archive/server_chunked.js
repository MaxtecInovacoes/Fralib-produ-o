// FraLib OpenUI — Geracao HTML em 4 chunks para evitar 529 do DeployFlow
// Cada chunk gera 1/4 do HTML e concatena no final.
import http from 'http';
import { generateHTML } from './generate.js';

const PORT = parseInt(process.env.PORT || '3333', 10);
const HOST = process.env.HOST || '0.0.0.0';

// Divide o PRD em 4 partes para gerar HTML em chunks
function splitPRDIntoChunks(prd) {
  const sections = prd.sections || [];
  const totalSections = sections.length;
  const chunkSize = Math.ceil(totalSections / 4);

  const chunks = [
    { ...prd, sections: sections.slice(0, chunkSize), chunkLabel: 'HERO+TOP' },
    { ...prd, sections: sections.slice(chunkSize, chunkSize * 2), chunkLabel: 'MIDDLE-1' },
    { ...prd, sections: sections.slice(chunkSize * 2, chunkSize * 3), chunkLabel: 'MIDDLE-2' },
    { ...prd, sections: sections.slice(chunkSize * 3), chunkLabel: 'BOTTOM+FAQ' },
  ];
  return chunks;
}

async function callLLMChunked(baseUrl, headers, model, maxTokens, systemPrompt, userPromptChunk, label) {
  const resp = await fetch(`${baseUrl}/messages`, {
    method: 'POST',
    headers: { ...headers, 'content-type': 'application/json' },
    body: JSON.stringify({
      model,
      max_tokens: Math.ceil(maxTokens / 4) + 2000, // margem
      temperature: 0.7,
      system: `${systemPrompt}\n\n# CHUNK ATUAL: ${label}\nGere APENAS o pedaco de HTML correspondente a este chunk. Nao feche </html>, deixe aberto para concatenacao.`,
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

  // Endpoint original /generate (mantido para compatibilidade)
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

  // Novo endpoint /generate-chunked — divide em 4 chamadas
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

      // Importa buildSystemPrompt e buildUserPrompt dinamicamente
      const gen = await import('./generate.js');
      const systemPrompt = gen.buildSystemPrompt(prd);

      const chunks = splitPRDIntoChunks(prd);
      const htmlParts = [];
      const totalUsage = { input_tokens: 0, output_tokens: 0 };

      // Primeiro chunk inclui o head + doctype
      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const chunkUserPrompt = `[CHUNK ${i + 1}/4: ${chunk.chunkLabel}]\n${gen.buildUserPrompt(chunk)}`;
        console.log(`[/generate-chunked] Calling chunk ${i + 1}/4: ${chunk.chunkLabel}`);
        const result = await callLLMChunked(
          baseUrl, authHeader, model, maxTokens,
          systemPrompt, chunkUserPrompt, chunk.chunkLabel
        );
        htmlParts.push(result.text);
        totalUsage.input_tokens += result.usage.input_tokens || 0;
        totalUsage.output_tokens += result.usage.output_tokens || 0;
        console.log(`[/generate-chunked] Chunk ${i + 1} OK, ${result.text.length} chars`);
      }

      // Concatenar partes do HTML (remove fechamentos duplicados)
      let combinedHTML = htmlParts.join('\n');
      // Garantir que </html></body> apareca so uma vez no final
      combinedHTML = combinedHTML.replace(/<\/html>/gi, '__HTML_CLOSE__');
      combinedHTML = combinedHTML.replace(/<\/body>/gi, '__BODY_CLOSE__');
      combinedHTML = combinedHTML.replace(/__HTML_CLOSE__|__BODY_CLOSE__/g, '');
      combinedHTML = combinedHTML + '\n</body>\n</html>';

      // Limpar <html> intermediario se houver
      combinedHTML = combinedHTML.replace(/<html[^>]*>/gi, (match, offset) => offset === 0 ? match : '');

      // Extrair e processar HTML
      const finalHTML = gen.extractHTML(combinedHTML);
      let html = finalHTML;
      html = gen.injectDesignTokensIntoHead(html, prd);
      html = gen.injectHeroPatternBackground(html, prd);
      html = gen.applyEliteRefinements(html, prd);
      html = gen.applyCinematicTexture(html, prd);
      html = gen.applySignatureElement(html, prd);
      html = gen.injectRequired(html, prd);

      return sendJSON(res, 200, {
        html,
        model,
        attempts: 4,
        success: true,
        usage: totalUsage,
        chunks: chunks.length,
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
  console.log(`FraLib OpenUI (CHUNKED) running at http://${HOST}:${PORT}`);
  console.log(`  POST /generate         — single-shot LLM call`);
  console.log(`  POST /generate-chunked — 4 chunked LLM calls + concat`);
  console.log(`  GET  /health           — health check`);
});

process.on('SIGTERM', () => { server.close(); process.exit(0); });
process.on('SIGINT', () => { server.close(); process.exit(0); });
