module.exports = {
  apps: [
    {
      name: 'fralib',
      script: 'server.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 5000,
      restart_delay: 1000,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        FRALIB_SKIP_HTML_QUALITY_GATE: '0'
      }
    },
    {
      name: 'fralib-worker',
      script: 'worker.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 8000,
      restart_delay: 2000,
      max_restarts: 20,
      env: {
        NODE_ENV: 'production',
        FRALIB_SKIP_HTML_QUALITY_GATE: '0',
        FRALIB_BUILDER_AUTO_APPROVE: '1',
        PYTHONUNBUFFERED: '1',
        WORKER_JOB_TYPES: 'pipeline_lead,pipeline_multiplos,lead_supply_hunter,lead_supply_caio,lead_production_tick',
        MAX_PIPELINES_GLOBAL: '1',
        WORKER_POLL_SECONDS: '3',
        WORKER_HEARTBEAT_SECS: '30',
        WORKER_REAP_SECS: '60'
      }
    },
    {
      name: 'fralib-franz-worker',
      script: 'worker.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 8000,
      restart_delay: 3000,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production',
        WORKER_JOB_TYPES: 'franz_outreach',
        MAX_PIPELINES_GLOBAL: '1',
        WORKER_POLL_SECONDS: '5',
        WORKER_HEARTBEAT_SECS: '30',
        WORKER_REAP_SECS: '60'
      }
    },
    {
      name: 'fralib-hermes-watchdog',
      script: 'scripts/hermes_daemon.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 5000,
      restart_delay: 5000,
      max_restarts: 20,
      env: {
        NODE_ENV: 'production',
        HERMES_WATCHDOG_INTERVAL_SECONDS: '300',
        HERMES_CANARY_EVERY_CYCLES: '12',
        HERMES_CANARY_TIMEOUT_SECONDS: '180',
        HERMES_AUTOREMEDIATE: '1',
        HERMES_AUTOREMEDIATE_PAYMENT_APPLY: '1',
        HERMES_REMEDIATION_COOLDOWN_SECONDS: '900',
        HERMES_REMEDIATION_TIMEOUT_SECONDS: '180'
      }
    },
    {
      name: 'fralib-wpp-listener',
      script: 'backend/whatsapp_listener.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 5000,
      restart_delay: 3000,
      max_restarts: 20,
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'fralib-dreamer',
      script: 'scripts/dreamer_daemon.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      kill_timeout: 5000,
      restart_delay: 5000,
      max_restarts: 5,
      cron_restart: '0 3 * * *',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        DREAMER_INTERVAL_SECONDS: '86400'
      }
    }
  ]
}
