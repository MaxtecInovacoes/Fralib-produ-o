import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Cache control middleware for static frontend assets
app.use((req, res, next) => {
  const p = req.path;
  if (p.startsWith('/js/') || p.startsWith('/css/') || p.startsWith('/images/') || p.startsWith('/static/')) {
    res.setHeader('Cache-Control', 'public, max-age=86400');
  } else if (p.endsWith('.html') || p === '/admin' || p === '/dashboard') {
    res.setHeader('Cache-Control', 'public, max-age=60, stale-while-revalidate=60');
  }
  next();
});

// Health check endpoints
app.get('/health', (req, res) => {
  res.json({ status: 'ok', version: '2.0.0', service: 'FraLib OS' });
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', version: '2.0.0', service: 'FraLib OS' });
});

// System info endpoint
app.get('/api/info', (req, res) => {
  res.json({
    name: 'FraLib OS',
    version: '2.0.0',
    agents: [
      'hunter', 'caio', 'arquiteto', 'builder',
      'quality_gate', 'deploy', 'franz', 'manager'
    ],
    status: 'online'
  });
});

// CSRF Token route
app.get('/api/csrf-token', (req, res) => {
  res.json({ csrf_token: 'fralib-csrf-token-mock-2026' });
});

// Auth Routes
app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body || {};
  res.json({
    access_token: 'fralib-mock-jwt-token-superadmin',
    token_type: 'bearer',
    user: {
      id: 1,
      email: email || 'admin@fralib.site',
      nome: 'Admin FraLib',
      role: 'superadmin',
      credits: 1000
    }
  });
});

app.post('/api/auth/register', (req, res) => {
  const { email, nome } = req.body || {};
  res.json({
    access_token: 'fralib-mock-jwt-token-newuser',
    token_type: 'bearer',
    user: {
      id: Math.floor(Math.random() * 1000) + 2,
      email: email || 'usuario@fralib.site',
      nome: nome || 'Usuário FraLib',
      role: 'user',
      credits: 100
    }
  });
});

app.get('/api/auth/me', (req, res) => {
  res.json({
    id: 1,
    email: 'admin@fralib.site',
    nome: 'Admin FraLib',
    role: 'superadmin',
    credits: 1000
  });
});

app.post('/api/auth/logout', (req, res) => {
  res.json({ ok: true, message: 'Sessão encerrada com sucesso' });
});

// Dashboard & Analytics endpoints
app.get(['/api/dashboard/summary', '/api/dashboard/stats', '/api/dashboard'], (req, res) => {
  res.json({
    ok: true,
    stats: {
      total_leads: 142,
      active_pipelines: 18,
      sites_generated: 96,
      conversions: 38,
      revenue: 57000.00,
      conversion_rate: 26.7
    },
    metrics: {
      daily_leads: [12, 15, 18, 14, 22, 25, 36],
      conversions_by_day: [2, 4, 3, 5, 8, 7, 9]
    },
    recent_leads: [
      { id: 201, nome: 'OdontoSmile Clínica', cidade: 'São Paulo - SP', status: 'prospectado', site_url: '/sites/odontosmile' },
      { id: 202, nome: 'Barbearia Vanguarda', cidade: 'Rio de Janeiro - RJ', status: 'site_gerado', site_url: '/sites/barbearia-vanguarda' },
      { id: 203, nome: 'Restaurante Bella Italia', cidade: 'Curitiba - PR', status: 'fechado', site_url: '/sites/bella-italia' }
    ]
  });
});

app.get(['/api/leads', '/api/leads/list'], (req, res) => {
  res.json({
    ok: true,
    total: 3,
    leads: [
      { id: 201, nome: 'OdontoSmile Clínica', telefone: '+5511988887777', cidade: 'São Paulo', status: 'prospectado', data: '2026-08-07' },
      { id: 202, nome: 'Barbearia Vanguarda', telefone: '+5521977776666', cidade: 'Rio de Janeiro', status: 'site_gerado', data: '2026-08-07' },
      { id: 203, nome: 'Restaurante Bella Italia', telefone: '+5541966665555', cidade: 'Curitiba', status: 'fechado', data: '2026-08-06' }
    ]
  });
});

app.get(['/api/agentes', '/api/agentes/status'], (req, res) => {
  res.json({
    ok: true,
    agents: [
      { name: 'Hunter', role: 'Prospecção Google Maps', status: 'ativo', total_processed: 350 },
      { name: 'Caio', role: 'Enriquecimento & Qualificação', status: 'ativo', total_processed: 310 },
      { name: 'Arquiteto', role: 'Estruturação & UX/UI', status: 'ativo', total_processed: 280 },
      { name: 'Builder', role: 'Geração do Site', status: 'ativo', total_processed: 250 },
      { name: 'Franz', role: 'Atendimento & Fechamento WhatsApp', status: 'ativo', total_processed: 190 }
    ]
  });
});

app.get(['/api/whatsapp/status', '/api/whatsapp'], (req, res) => {
  res.json({
    ok: true,
    connected: true,
    phone: '+5511999998888',
    status: 'online',
    disparos_hoje: 45
  });
});

// Generic catch-all for any unhandled /api/* route to prevent 404 errors
app.use('/api', (req, res) => {
  res.json({
    ok: true,
    path: req.path,
    message: 'FraLib API Mock Response',
    data: []
  });
});

// HTML Route Mappings (Clean URLs without .html extension)
app.get('/admin', (req, res) => res.sendFile(path.join(__dirname, 'frontend/admin.html')));
app.get('/dashboard', (req, res) => res.sendFile(path.join(__dirname, 'frontend/dashboard.html')));
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, 'frontend/login.html')));
app.get('/onboarding', (req, res) => res.sendFile(path.join(__dirname, 'frontend/onboarding.html')));
app.get('/planos', (req, res) => res.sendFile(path.join(__dirname, 'frontend/planos.html')));
app.get('/oferta', (req, res) => res.sendFile(path.join(__dirname, 'frontend/oferta.html')));
app.get('/studio', (req, res) => res.sendFile(path.join(__dirname, 'frontend/studio.html')));
app.get('/superadmin', (req, res) => res.sendFile(path.join(__dirname, 'frontend/superadmin.html')));
app.get('/docs', (req, res) => res.sendFile(path.join(__dirname, 'frontend/docs/index.html')));
app.get('/blog', (req, res) => res.sendFile(path.join(__dirname, 'frontend/blog/index.html')));

// Static asset compatibility aliases
app.get('/design-system.css', (req, res) => res.sendFile(path.join(__dirname, 'frontend/static/design-system-tokens.css')));
app.get('/js/chart.min.js', (req, res) => res.sendFile(path.join(__dirname, 'frontend/static/js/chart.min.js')));
app.get('/js/socket.io.min.js', (req, res) => res.sendFile(path.join(__dirname, 'frontend/static/js/socket.io.min.js')));
app.get(['/assets/logo-fralib.png', '/images/logo.png'], (req, res) => {
  res.setHeader('Content-Type', 'image/svg+xml');
  res.send(`<svg xmlns="http://www.w3.org/2000/svg" width="140" height="36" viewBox="0 0 140 36">
    <rect width="100%" height="100%" rx="6" fill="#12121a"/>
    <text x="10" y="23" font-family="system-ui, sans-serif" font-weight="bold" font-size="16" fill="#c084fc">FraLib OS</text>
  </svg>`);
});

// Static file serving from frontend directory and subdirectories
app.use('/static', express.static(path.join(__dirname, 'frontend/static')));
app.use(express.static(path.join(__dirname, 'frontend')));

// Handle missing static JS/CSS assets gracefully to prevent SyntaxError: Unexpected token '<'
app.use((req, res, next) => {
  const url = req.path;
  if (url.endsWith('.js') || url.startsWith('/js/')) {
    res.setHeader('Content-Type', 'application/javascript');
    return res.status(404).send('/* Asset not found: ' + url + ' */');
  }
  if (url.endsWith('.css') || url.startsWith('/css/')) {
    res.setHeader('Content-Type', 'text/css');
    return res.status(404).send('/* Asset not found: ' + url + ' */');
  }
  next();
});

// Serve landing page for root or SPA fallback
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'frontend/landing.html'));
});

app.use((req, res) => {
  res.sendFile(path.join(__dirname, 'frontend/landing.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`FraLib OS server running on http://0.0.0.0:${PORT}`);
});
