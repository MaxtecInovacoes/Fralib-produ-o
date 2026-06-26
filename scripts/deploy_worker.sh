#!/bin/bash
# deploy_worker.sh — Deploy atômico do fralib-worker com 1 instância
# Uso: bash scripts/deploy_worker.sh
#
# O que faz:
#   1. Para TODOS os workers (evita polling durante deploy)
#   2. Faz git pull na VPS
#   3. Restart fralib-worker com ecosystem.config.js
#   4. Confirma que só 1 instância está rodando
#
set -e

VPS_USER="${VPS_USER:-root}"
VPS_HOST="${VPS_HOST:-100.101.18.1}"
VPS_REPO="${VPS_REPO:-/root/fralib}"

echo "=== Deploy Worker: 1 instância, código novo ==="
echo

# Passos local → remote via ssh
ssh "${VPS_USER}@${VPS_HOST}" bash << 'REMOTE_SCRIPT'
set -e
REPO="/root/fralib"
cd "$REPO"

echo "[1/5] Parando fralib-worker..."
pm2 stop fralib-worker 2>/dev/null || true

echo "[2/5] Aguardando poll corrente terminar (2s)..."
sleep 2

echo "[3/5] Git pull..."
git fetch origin
git checkout master
git pull origin master

echo "[4/5] Restartando fralib-worker..."
pm2 start ecosystem.config.js --only fralib-worker

echo "[5/5] Status PM2..."
pm2 status fralib-worker

# Confirma: instances deve ser 1
INSTANCES=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
apps = json.load(sys.stdin)
for a in apps:
    if a['name'] == 'fralib-worker':
        print(a.get('pm2_env',{}).get('instances','?'))
" 2>/dev/null || echo "?")
echo "fralib-worker instances: $INSTANCES"

if [ "$INSTANCES" != "1" ]; then
    echo "ERRO: fralib-worker deveria ter 1 instância, tem: $INSTANCES"
    exit 1
fi

echo ""
echo "Deploy OK — 1 worker rodando com código свежий"
REMOTE_SCRIPT

echo ""
echo "Feito."
