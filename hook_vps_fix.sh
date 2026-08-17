#!/bin/bash
set -euo pipefail
TARGET="/opt/fralib"
BRANCH="master"

while read oldrev newrev ref; do
    if [[ $ref = refs/heads/$BRANCH ]]; then
        echo "[hook] === Deploy: branch $BRANCH recebida ==="
        echo "[hook] === Git checkout forcado em $TARGET ==="
        git --work-tree="$TARGET" --git-dir=/root/repos/fralib.git checkout -f "$BRANCH"
        echo "[hook] === Limpeza de arquivos mortos ==="
        git --work-tree="$TARGET" --git-dir=/root/repos/fralib.git clean -fd
        echo "[hook] === Docker Compose restart worker ==="
        cd "$TARGET" && docker compose -f docker-compose.prod.yml up -d worker
        echo "[hook] === Restart fralib-api ==="
        systemctl restart fralib-api.service
        echo "[hook] === Restart fralib-openui ==="
        systemctl restart fralib-openui.service
        echo "[hook] === Deploy concluido ==="
    fi
done
