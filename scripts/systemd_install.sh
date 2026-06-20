#!/bin/bash
# =========================================================================
# systemd_install.sh - Instala serviços systemd do FraLib (idempotente)
# =========================================================================
# Pode rodar várias vezes sem efeito colateral.
# Preserva PM2 como fallback (não remove).
# =========================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Detectar projeto root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SYSTEMD_SRC="$PROJECT_ROOT/infra/systemd"
SYSTEMD_DST="/etc/systemd/system"
ENV_DIR="/etc/fralib"

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
echo "  FraLib systemd installer"
echo "═══════════════════════════════════════"

# [1/5] Validar sintaxe antes de instalar
echo ""
echo "📋 [1/5] Validando sintaxe dos .service..."
for svc in "${SERVICES[@]}"; do
    if ! systemd-analyze verify "$SYSTEMD_SRC/$svc" 2>&1 | head -5; then
        if [ $? -eq 0 ] || [ -z "$(systemd-analyze verify "$SYSTEMD_SRC/$svc" 2>&1)" ]; then
            ok "$svc - sintaxe OK"
        else
            warn "$svc - systemd-analyze reporta algo (mas pode ser warning)"
        fi
    fi
done

# [2/5] Copiar .service files
echo ""
echo "📦 [2/5] Instalando .service files..."
for svc in "${SERVICES[@]}"; do
    if [ ! -f "$SYSTEMD_SRC/$svc" ]; then
        fail "$SYSTEMD_SRC/$svc não encontrado"
    fi
    cp -v "$SYSTEMD_SRC/$svc" "$SYSTEMD_DST/$svc" >/dev/null
    ok "Instalado: $svc"
done

# [3/5] Gerar EnvironmentFile do .env
echo ""
echo "🔐 [3/5] Gerando EnvironmentFile do .env..."
mkdir -p "$ENV_DIR"
if python3 "$SYSTEMD_SRC/env-from-dotenv.py" "/root/fralib/.env" "$ENV_DIR/fralib.env"; then
    ok "EnvironmentFile criado: $ENV_DIR/fralib.env"
    chmod 600 "$ENV_DIR/fralib.env"
else
    fail "Falha ao gerar EnvironmentFile"
fi

# [4/5] Recarregar systemd
echo ""
echo "🔄 [4/5] Recarregando systemd daemon..."
systemctl daemon-reload && ok "systemd daemon recarregado"

# [5/5] NÃO inicia automaticamente (migração gradual via migrate_pm2_to_systemd.sh)
echo ""
echo "ℹ️  [5/5] Serviços instalados mas NÃO iniciados."
echo "   Para migrar gradualmente do PM2, rode:"
echo "   bash $PROJECT_ROOT/scripts/migrate_pm2_to_systemd.sh"
echo ""
ok "Instalação completa! PM2 continua rodando como fallback."