module.exports = {
  apps: [{
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
  }]
}
