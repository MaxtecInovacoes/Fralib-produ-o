#!/usr/bin/env bash
# Prepare Redis for FraLib production rate limiting on the VPS.
# Run on the VPS as root from /root/fralib after the script is deployed by Git.

set -euo pipefail

if [ "$(id -u)" != "0" ]; then
  echo "erro: execute como root na VPS" >&2
  exit 2
fi

if command -v redis-cli >/dev/null 2>&1; then
  if [ "$(redis-cli ping 2>/dev/null || true)" = "PONG" ]; then
    echo "redis: ok"
    exit 0
  fi
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "erro: apt-get nao encontrado; instale redis-server manualmente" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y redis-server

if command -v systemctl >/dev/null 2>&1; then
  systemctl enable redis-server
  systemctl restart redis-server
else
  service redis-server restart || service redis-server start
fi

if [ "$(redis-cli ping 2>/dev/null || true)" != "PONG" ]; then
  echo "erro: Redis instalado, mas ping nao retornou PONG" >&2
  exit 1
fi

echo "redis: ok"
