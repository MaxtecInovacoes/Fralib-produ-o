#!/bin/bash
# install_whatsmeow_bridge.sh
# Compila e instala o bridge Go do whatsmeow na VPS.
#
# Pre-requisitos:
#   - Go 1.21+ instalado
#   - Usuario 'fralib' existe
#   - /etc/fralib/fralib.env com MEOWHATS_DB_URL
#
# Uso:
#   sudo bash install_whatsmeow_bridge.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BRIDGE_SRC="$REPO_DIR/infra/whatsmeow_"
INSTALL_DIR="/opt/whatsmeow_"
BIN_PATH="/usr/local/bin/meowhats"
SERVICE_FILE="$REPO_DIR/infra/systemd/fralib-meowhats.service"
SYSTEMD_PATH="/etc/systemd/system/fralib-meowhats.service"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: precisa rodar como root (sudo)"
  exit 1
fi

if ! command -v go >/dev/null 2>&1; then
  echo "ERRO: Go nao instalado. Instale: apt install golang-go"
  exit 1
fi

if ! id fralib >/dev/null 2>&1; then
  echo "ERRO: usuario 'fralib' nao existe"
  exit 1
fi

if [ ! -f /etc/fralib/fralib.env ]; then
  echo "ERRO: /etc/fralib/fralib.env nao existe"
  exit 1
fi

echo "==> Criando $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
chown fralib:fralib "$INSTALL_DIR"

echo "==> Copiando codigo fonte..."
cp -r "$BRIDGE_SRC/"* "$INSTALL_DIR/"
chown -R fralib:fralib "$INSTALL_DIR"

echo "==> Compilando..."
cd "$INSTALL_DIR"
sudo -u fralib go mod tidy
sudo -u fralib go build -o "$BIN_PATH" .
chmod +x "$BIN_PATH"

echo "==> Instalando systemd unit..."
cp "$SERVICE_FILE" "$SYSTEMD_PATH"
chmod 644 "$SYSTEMD_PATH"
systemctl daemon-reload
systemctl enable fralib-meowhats.service
systemctl restart fralib-meowhats.service

echo "==> Aguardando 3s e verificando status..."
sleep 3
systemctl status fralib-meowhats.service --no-pager

echo ""
echo "==> Instalado!"
echo "    Binario:    $BIN_PATH"
echo "    InstallDir: $INSTALL_DIR"
echo "    Service:    systemctl status fralib-meowhats"
echo "    Health:     curl http://localhost:3001/health"
echo ""
echo "    Logs:       journalctl -u fralib-meowhats -f"