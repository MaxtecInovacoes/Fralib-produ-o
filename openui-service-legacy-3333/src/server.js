import http from 'http';

/**
 * FraLib OpenUI Service
 *
 * Recebe DesignerPRD como JSON, chama Claude (Anthropic), retorna HTML final.
 * Porta padrao: 3333
 *
 * Uso:
 *   POST /generate
 *   Body: { designerPRD: { business_name, cidade, segmento, hero, sections, ctas, faqs, paleta, seo_keywords, motion_directives } }
 *   Response: { html: string, model: string, success: boolean }
 */

import { generateHTML } from './generate.js';

const PORT = parseInt(process.env.PORT || '3333', 10);
const HOST = process.env.HOST || '0.0.0.0';

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try { resolve(JSON.parse(body)); }
      catch (e) { reject(new Error('Invalid JSON')); }
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
  // CORS preflight
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
      const { designerPRD, usar_llm = true } = body;

      if (!designerPRD) {
        return sendJSON(res, 400, { success: false, error: 'designerPRD is required' });
      }

      const result = await generateHTML(designerPRD, { usar_llm });
      return sendJSON(res, 200, result);

    } catch (err) {
      console.error('[/generate]', err.message);
      return sendJSON(res, 500, { success: false, error: err.message });
    }
  }

  if (req.method === 'GET' && url.pathname === '/health') {
    return sendJSON(res, 200, { status: 'ok', service: 'fralib-openui' });
  }

  sendJSON(res, 404, { error: 'Not found' });
});

server.listen(PORT, HOST, () => {
  console.log(`FraLib OpenUI Service running at http://${HOST}:${PORT}`);
  console.log(`  POST /generate  — gera HTML a partir do DesignerPRD`);
  console.log(`  GET  /health    — health check`);
});

process.on('SIGTERM', () => { server.close(); process.exit(0); });
process.on('SIGINT',  () => { server.close(); process.exit(0); });
