#!/bin/bash
# =========================================================================
# systemd_uninstall.sh - Remove serviços systemd e restaura PM2
# =========================================================================
# Rollback seguro: para systemd e religa PM2 via dump.pm2
# =========================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVICES=(
    "fralib-api.service"
    "fralib-worker.service"
    "fralib-franz.service"
    "fralib-wpp-listener.service"
    "fralib-hermes.service"
)

ok()    { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

echo "═══════════════════════════════════════"
echo "  FraLib systemd uninstaller (rollback)"
echo "═══════════════════════════════════════"

# [1/3] Parar e desabilitar serviços systemd
echo ""
echo "⏹️  [1/3] Parando serviços systemd..."
for svc in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc" && ok "Parado: $svc"
    else
        warn "$svc já estava parado"
    fi
    systemctl disable "$svc" 2>/dev/null || true
done

# [2/3] Remover .service files
echo ""
echo "🗑️  [2/3] Removendo .service files..."
for svc in "${SERVICES[@]}"; do
    if [ -f "/etc/systemd/system/$svc" ]; then
        rm -f "/etc/systemd/system/$svc" && ok "Removido: $svc"
    fi
done

systemctl daemon-reload && ok "systemd daemon recarregado"

# [3/3] Restaurar PM2
echo ""
echo "🔄 [3/3] Restaurando PM2..."
if [ -f /root/.pm2/dump.pm2 ]; then
    pm2 resurrect && ok "PM2 restaurado do dump.pm2"
    pm2 list
else
    warn "dump.pm2 não encontrado. Inicie PM2 manualmente."
fi

# Manter EnvironmentFile (é útil)
echo ""
ok "Rollback completo! PM2 assumiu novamente."