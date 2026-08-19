#!/usr/bin/env bash
# FraLib — Atomic Deploy
# Uso: ./scripts/deploy.sh [mensagem opcional do commit]
set -euo pipefail

MSG="${1:-chore: deploy $(date +%Y-%m-%d\ %H:%M)}"
BRANCH="${FRALIB_DEPLOY_BRANCH:-master}"

echo "[deploy] branch=$BRANCH msg='$MSG'"

# 1) Valida py_compile local
echo "[deploy] py_compile..."
find backend -name '*.py' -print0 | xargs -0 python -m py_compile
echo "[deploy] py_compile OK"

# 2) Git push
echo "[deploy] git push..."
git add -A
git commit -m "$MSG" || true
git push origin "$BRANCH"

# 3) Sync working tree no VPS
VPS="${FRALIB_VPS_HOST:-104.243.41.166}"
VPS_ROOT="${FRALIB_VPS_ROOT:-/opt/fralib}"
echo "[deploy] sync VPS ($VPS:$VPS_ROOT)..."
rsync -az --delete --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
    ./ "$VPS:$VPS_ROOT/"

# 4) Restart containers
echo "[deploy] restart containers..."
ssh "root@$VPS" "docker compose -f $VPS_ROOT/docker-compose.prod.yml up -d --force-recreate fralib-worker-1 fralib-api"

# 5) Preflight
echo "[deploy] preflight..."
sleep 5
ssh "root@$VPS" "docker exec fralib-worker-1 python3 -m backend.core.preflight"

echo "[deploy] DONE ($(date +%H:%M:%S))"
