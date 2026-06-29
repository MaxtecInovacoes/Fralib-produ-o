// Servidor MaxTec Solar - COM endpoints de dashboard e funil
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const sqlite3 = require('better-sqlite3');

const PORT = process.env.PORT || 9000;
const ROOT = '/var/www/maxtec-solar';
const DB_PATH = '/root/maxtec-app/maxtec.db';

const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2'
};

let db = null;
try {
    db = new sqlite3(DB_PATH, { readonly: false, fileMustExist: true });
    console.log('DB connected:', DB_PATH);
} catch (e) {
    console.error('DB error:', e.message);
}

const server = http.createServer((req, res) => {
    const parsed = url.parse(req.url, true);
    const pathname = parsed.pathname;

    // ============== API ROUTES ==============
    res.setHeader('Access-Control-Allow-Origin', '*');

    // /api/lead POST
    if (pathname === '/api/lead' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                const data = JSON.parse(body);
                // Salvar lead
                const stmt = db.prepare(`INSERT INTO leads (nome, whatsapp, email, cidade, conta_luz, proprietario, prazo, orcamento, pagamento, score, prioridade, source_url, utm_source, utm_medium, utm_campaign, utm_content, utm_term, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
                const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
                const ua = req.headers['user-agent'] || '';

                // Calcular prioridade
                let score = 0;
                let prioridade = 'cold';
                const contaMap = {'Até R$350': 350, 'R$350–600': 500, 'R$600–1000': 800, 'R$1000–2500': 1500, 'Acima de R$2500': 3000};
                const contaNum = contaMap[data.conta_luz] || 0;
                if (data.prazo === 'Imediatamente') score += 30;
                else if (data.prazo && data.prazo.includes('30 dias')) score += 20;
                else if (data.prazo === 'Só pesquisando') score -= 50;
                if (contaNum >= 800) score += 40;
                else if (contaNum >= 600) score += 25;
                if (contaNum < 350) { score = 0; prioridade = 'disqualified'; }
                else if (contaNum >= 800 && score >= 60) prioridade = 'premium';
                else if (contaNum >= 800) prioridade = 'hot';
                else if (score >= 70) prioridade = 'hot';
                else if (score >= 40) prioridade = 'warm';
                else if (score >= 0) prioridade = 'cold';

                const result = stmt.run(
                    data.nome || null, data.whatsapp || null, data.email || null,
                    data.cidade || null, data.conta_luz || null, data.proprietario || null,
                    data.prazo || null, data.orcamento || null, data.pagamento || null,
                    score, prioridade, data.source_url || req.headers.referer || null,
                    data.utm_source || 'direct', data.utm_medium || 'none',
                    data.utm_campaign || 'none', data.utm_content || 'none',
                    data.utm_term || null, ip, ua, new Date().toISOString()
                );

                res.writeHead(200, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({success: true, id: result.lastInsertRowid, score, prioridade}));
            } catch (e) {
                res.writeHead(500, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({error: e.message}));
            }
        });
        return;
    }

    // /api/event POST
    if (pathname === '/api/event' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                const data = JSON.parse(body);
                const stmt = db.prepare(`INSERT INTO events (event_type, session_id, data, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?)`);
                stmt.run(
                    data.event || 'unknown',
                    data.session_id || null,
                    JSON.stringify(data),
                    req.headers['x-forwarded-for'] || req.socket.remoteAddress,
                    req.headers['user-agent'] || '',
                    new Date().toISOString()
                );
                res.writeHead(200, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({success: true}));
            } catch (e) {
                res.writeHead(500, {'Content-Type': 'application/json'});
                res.end(JSON.stringify({error: e.message}));
            }
        });
        return;
    }

    // /api/leads-public GET
    if (pathname === '/api/leads-public' && req.method === 'GET') {
        try {
            const limit = parseInt(parsed.query.limit) || 10;
            const rows = db.prepare('SELECT id, created_at, nome, whatsapp, conta_luz, proprietario, prazo, prioridade, utm_source, utm_campaign FROM leads ORDER BY created_at DESC LIMIT ?').all(limit);
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({leads: rows}));
        } catch (e) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({error: e.message}));
        }
        return;
    }

    // /api/funnel-stats GET
    if (pathname === '/api/funnel-stats' && req.method === 'GET') {
        try {
            const rows = db.prepare("SELECT event_type, COUNT(DISTINCT session_id) as count FROM events WHERE created_at >= datetime('now', '-3 days') AND event_type LIKE 'step%' GROUP BY event_type").all();
            const steps = [];
            const labels = {1: 'Step 1: Conta de Luz', 2: 'Step 2: Proprietario', 3: 'Step 3: Telhado', 4: 'Step 4: Prazo', 5: 'Step 5: Formulario'};
            for (const r of rows) {
                const m = r.event_type.match(/\d+/);
                const stepNum = m ? parseInt(m[0]) : 0;
                steps.push({label: labels[stepNum] || ('Step ' + stepNum), count: r.count, step: stepNum});
            }
            steps.sort((a, b) => a.step - b.step);
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({steps: steps}));
        } catch (e) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({error: e.message}));
        }
        return;
    }

    // /api/recent-events GET
    if (pathname === '/api/recent-events' && req.method === 'GET') {
        try {
            const rows = db.prepare("SELECT created_at, event_type, data, session_id FROM events ORDER BY created_at DESC LIMIT 50").all();
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({events: rows}));
        } catch (e) {
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({events: []}));
        }
        return;
    }

    // /api/event-stats GET
    if (pathname === '/api/event-stats' && req.method === 'GET') {
        try {
            const row = db.prepare("SELECT SUM(CASE WHEN event_type='dropoff' THEN 1 ELSE 0 END) as dropoffs, SUM(CASE WHEN event_type='form_complete' THEN 1 ELSE 0 END) as completions FROM events WHERE created_at >= datetime('now', '-3 days')").get();
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({
                dropoffs: (row && row.dropoffs) || 0,
                completions: (row && row.completions) || 0
            }));
        } catch (e) {
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({dropoffs: 0, completions: 0}));
        }
        return;
    }

    // /api/campaign-stats GET
    if (pathname === '/api/campaign-stats' && req.method === 'GET') {
        try {
            const rows = db.prepare("SELECT utm_campaign, utm_source, utm_medium, COUNT(*) as total, SUM(CASE WHEN prioridade IN ('hot', 'warm', 'premium') THEN 1 ELSE 0 END) as qualificados, SUM(CASE WHEN prioridade = 'disqualified' THEN 1 ELSE 0 END) as descartados FROM leads WHERE utm_campaign IS NOT NULL AND utm_campaign != 'direct' AND utm_campaign != 'none' GROUP BY utm_campaign, utm_source, utm_medium ORDER BY total DESC").all();
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({campaigns: rows}));
        } catch (e) {
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({campaigns: []}));
        }
        return;
    }

    // /api/stats GET
    if (pathname === '/api/stats' && req.method === 'GET') {
        try {
            const today = new Date().toISOString().split('T')[0];
            const total = db.prepare('SELECT COUNT(*) as c FROM leads').get();
            const qualified = db.prepare("SELECT COUNT(*) as c FROM leads WHERE prioridade IN ('hot', 'warm', 'premium')").get();
            res.writeHead(200, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({
                total_leads: total.c,
                total_qualified: qualified.c,
                leads_today: db.prepare("SELECT COUNT(*) as c FROM leads WHERE DATE(created_at) = ?").get(today).c
            }));
        } catch (e) {
            res.writeHead(500, {'Content-Type': 'application/json'});
            res.end(JSON.stringify({error: e.message}));
        }
        return;
    }

    // /api/health
    if (pathname === '/api/health' && req.method === 'GET') {
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify({status: 'ok', db: db ? 'connected' : 'disconnected'}));
        return;
    }

    // ============== STATIC FILES ==============
    let filePath = path.join(ROOT, pathname === '/' ? '/index.html' : pathname);
    if (!path.extname(filePath) && !filePath.includes('.')) {
        filePath = path.join(ROOT, 'index.html');
    }

    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404);
            res.end('Not Found');
            return;
        }
        const ext = path.extname(filePath);
        const isHTML = ext === '.html';
        res.writeHead(200, {
            'Content-Type': MIME[ext] || 'application/octet-stream',
            'Cache-Control': isHTML ? 'no-cache, no-store, must-revalidate' : 'public, max-age=31536000, immutable'
        });
        res.end(data);
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`MaxTec Solar API+Static rodando em http://0.0.0.0:${PORT}`);
});
