// PM2 ecosystem file - loads .env vars and starts fralib stack
const fs = require('fs');
const path = require('path');

// Load .env file
function loadEnv(envPath) {
  const env = {};
  if (!fs.existsSync(envPath)) return env;
  const content = fs.readFileSync(envPath, 'utf-8');
  content.split('\n').forEach(line => {
    line = line.trim();
    if (!line || line.startsWith('#')) return;
    const idx = line.indexOf('=');
    if (idx === -1) return;
    const key = line.slice(0, idx).trim();
    let val = line.slice(idx + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    env[key] = val;
  });
  return env;
}

const env = loadEnv('/root/fralib/.env');

module.exports = {
  apps: [
    {
      name: 'fralib',
      cwd: '/root/fralib',
      script: 'server.py',
      interpreter: 'venv/bin/python3',
      args: '--host 0.0.0.0 --port 8000',
      env: env,
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: 'fralib-wpp-listener',
      cwd: '/root/fralib',
      script: 'backend/whatsapp_listener.py',
      interpreter: 'venv/bin/python3',
      args: '--env production',
      env: env,
      max_restarts: 10,
    },
  ],
};