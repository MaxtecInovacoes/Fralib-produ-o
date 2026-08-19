#!/usr/bin/env bash
# FraLib — Instant Rollback (1 comando)
# Uso: ./scripts/rollback.sh
set -euo pipefail

VPS="${FRALIB_VPS_HOST:-104.243.41.166}"
VPS_ROOT="${FRALIB_VPS_ROOT:-/opt/fralib}"
BACKUP_REF="rollback-backup-$(date +%Y%m%d-%H%M%S)"

echo "[rollback] salvando ref atual em $BACKUP_REF..."
git tag "$BACKUP_REF" || true

echo "[rollback] git reset --hard HEAD~1..."
git reset --hard HEAD~1

echo "[rollback] sync VPS ($VPS:$VPS_ROOT)..."
rsync -az --delete --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
    ./ "$VPS:$VPS_ROOT/"

echo "[rollback] restart containers..."
ssh "root@$VPS" "docker compose -f $VPS_ROOT/docker-compose.prod.yml up -d --force-recreate fralib-worker-1 fralib-api"

echo "[rollback] DONE — ref atual: $(git rev-parse --short HEAD) (backup: $BACKUP_REF)"
echo "[rollback] Para voltar ao estado anterior: git reset --hard $BACKUP_REF"
