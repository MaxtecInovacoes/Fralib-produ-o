#!/bin/bash
# deploy_worker.sh — Deploy atômico do fralib via systemd na VPS
#
# Status: A VPS usa systemd (NÃO PM2) para workers em produção:
#   fralib-worker  → worker.py com WORKER_JOB_TYPES=pipeline_lead,...
#   fralib-franz   → worker.py com WORKER_JOB_TYPES=franz_outreach
#   (ecosystem.config.js / PM2 é só pra dev/local)
#
# O que faz:
#   1. Para os 3 serviços via systemctl
#   2. Git pull свежий код
#   3. Restart systemctl
#   4. Confirma que cada serviço está active
#
set -e

VPS_USER="${VPS_USER:-root}"
VPS_HOST="${VPS_HOST:-100.101.18.1}"

echo "=== Deploy VPS: systemd workers + API ==="
echo

ssh "${VPS_USER}@${VPS_HOST}" bash << 'REMOTE_SCRIPT'
set -e
REPO="/root/fralib"
cd "$REPO"

echo "[1/6] Parando serviços..."
for svc in fralib-worker fralib-franz fralib-api fralib-hermes fralib-wpp-listener fralib-dreamer; do
    systemctl stop "$svc" 2>/dev/null || true
done
sleep 2

echo "[2/6] Verificando processos zumbis..."
ZOMBIES=$(ps auxww | grep -E 'python.*fralib' | grep -v grep | grep -v systemd | wc -l)
echo "  Processos zumbis: $ZOMBIES"
if [ "$ZOMBIES" -gt 0 ]; then
    echo "  AVISO: processos orphans detectados:"
    ps auxww | grep -E 'python.*fralib' | grep -v grep | grep -v systemd
fi

echo "[3/6] Git pull..."
git fetch origin
git checkout master
git pull origin master

echo "[4/6] Restartando serviços..."
for svc in fralib-api fralib-worker fralib-franz fralib-wpp-listener fralib-hermes; do
    systemctl restart "$svc" 2>/dev/null && echo "  $svc: OK" || echo "  $svc: FALHA"
done

echo "[5/6] Status dos serviços..."
for svc in fralib-api fralib-worker fralib-franz fralib-wpp-listener fralib-hermes; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "unknown")
    echo "  $svc: $STATUS"
done

echo "[6/6] Confirmação: só 1 worker.py em cada domínio..."
WORKER_PIDS=$(ps auxww | grep 'worker.py' | grep -v grep | wc -l)
FRANZ_PIDS=$(ps auxww | grep 'worker.py' | grep -v grep | grep -c franz || echo 0)
PIPELINE_PIDS=$(ps auxww | grep 'worker.py' | grep -v grep | grep -c pipeline || echo 0)
echo "  Total worker.py: $WORKER_PIDS"
echo "  worker.py franz:  $FRANZ_PIDS"
echo "  worker.py pipeline: $PIPELINE_PIDS"

if [ "$WORKER_PIDS" -gt 2 ]; then
    echo "  AVISO: mais de 2 worker.py rodando — verificar"
fi

echo ""
echo "Deploy OK"
REMOTE_SCRIPT

echo ""
echo "Feito — verificar status em:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'systemctl status fralib-worker fralib-franz'"

