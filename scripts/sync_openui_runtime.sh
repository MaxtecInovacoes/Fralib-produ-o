#!/bin/bash
set -euo pipefail

SOURCE="/opt/fralib/openui-service-wandb/backend/openui/generate.py"
TARGET="/opt/fralib/openui-wandb/backend/openui/generate.py"

if [[ ! -f "$SOURCE" ]]; then
    echo "OpenUI versionado ausente: $SOURCE" >&2
    exit 1
fi

if [[ ! -f "$TARGET" ]]; then
    echo "OpenUI runtime ausente: $TARGET" >&2
    exit 1
fi

install -m 0644 "$SOURCE" "$TARGET"
python3 -m py_compile "$TARGET"
echo "OpenUI runtime sincronizado: $(sha256sum "$TARGET" | cut -d' ' -f1)"
