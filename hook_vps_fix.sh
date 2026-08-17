#!/bin/bash
set -euo pipefail

GIT_DIR="/root/repos/fralib.git"
TARGET="/root/fralib"
BRANCH="master"

while read oldrev newrev ref; do
    if [[ $ref = refs/heads/$BRANCH ]]; then
        echo "[deploy] === Deploy $BRANCH -> $TARGET ==="

        echo "[deploy] git checkout -f"
        git --work-tree="$TARGET" --git-dir="$GIT_DIR" checkout -f "$BRANCH"

        echo "[deploy] git clean -fd"
        git --work-tree="$TARGET" --git-dir="$GIT_DIR" clean -fd

        echo "[deploy] Restart fralib-api.service"
        systemctl restart fralib-api.service || true

        echo "[deploy] Restart fralib-openui.service"
        systemctl restart fralib-openui.service || true

        echo "[deploy] Worker gerenciado externamente (pulando restart automatico)"

        echo "[deploy] === Deploy concluido ==="
    fi
done
