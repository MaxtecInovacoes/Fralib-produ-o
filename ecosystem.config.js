module.exports = {
  apps: [
    {
      name: 'fralib',
      script: 'server.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 10000,
      restart_delay: 1000,
      max_restarts: 10,
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'fralib-worker',
      script: 'worker.py',
      interpreter: '/root/fralib/venv/bin/python3',
      cwd: '/root/fralib',
      instances: 1,
      autorestart: true,
      kill_timeout: 8000,
      restart_delay: 2000,
      max_restarts: 20,
      env: {
        NODE_ENV: 'production',
        WORKER_POLL_SECONDS: '3',
        WORKER_HEARTBEAT_SECS: '30',
        WORKER_REAP_SECS: '60'
      }
    }
  ]
}
