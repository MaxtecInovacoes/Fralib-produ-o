#!/bin/bash
# sync_vps.sh
# ===========
# Sincroniza o VPS com o estado do repositório Git:
#   1. git pull origin master
#   2. copia frontend/ para /var/www/fralib/ (sobrescrevendo)
#   3. reload nginx (force cache miss)
#   4. restart servicos Python (fralib-api, fralib-worker, etc)
#
# USO: ./scripts/sync_vps.sh
#
# Pre-requisitos:
#   - Acesso SSH ao VPS (chave)
#   - root@187.77.37.72 configurado em ~/.ssh/config
#
# Idempotente: pode rodar multiplas vezes sem efeito colateral.
set -euo pipefail

VPS_HOST="root@187.77.37.72"
FRALIB_DIR="/root/fralib"
WEB_DIR="/var/www/fralib"

echo "=== Sync VPS iniciado em $(date) ==="

ssh "$VPS_HOST" "bash -s" << EOF
set -e

echo "1. git pull origin master"
cd "$FRALIB_DIR"
git pull origin master

echo ""
echo "2. Copiar frontend/ para $WEB_DIR/"
# HTMLs canonicos
for html in admin.html landing.html login.html planos.html studio.html superadmin.html termos.html privacidade.html; do
    if [ -f "\$FRALIB_DIR/frontend/\$html" ]; then
        cp -a "\$FRALIB_DIR/frontend/\$html" "\$WEB_DIR/\$html"
        echo "  copiado: \$html"
    fi
done
rm -f "\$WEB_DIR/dashboard.html"

# Diretorios estaticos (sobrescreve se mudou)
for dir in blog docs css js static images; do
    if [ -d "\$FRALIB_DIR/frontend/\$dir" ]; then
        cp -a "\$FRALIB_DIR/frontend/\$dir" "\$WEB_DIR/" 2>/dev/null || true
        echo "  copiado dir: \$dir"
    fi
done

echo ""
echo "3. Reload nginx (forca bypass de cache)"
if nginx -t 2>&1 | tail -1; then
    nginx -s reload
    echo "  nginx recarregado"
fi

echo ""
echo "4. Restart servicos Python"
systemctl restart fralib-api 2>&1 | tail -1
systemctl restart fralib-worker 2>&1 | tail -1
systemctl restart fralib-franz 2>&1 | tail -1
systemctl restart fralib-hermes 2>&1 | tail -1
echo "  servicos reiniciados"

echo ""
echo "=== Sync VPS concluido em \$(date) ==="
EOF

echo ""
echo "=== Sync local concluido ==="
