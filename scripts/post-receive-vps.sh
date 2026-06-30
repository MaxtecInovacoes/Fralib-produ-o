#!/bin/bash
# post-receive hook — deploy automatico do FraLib (v3 - PM2 completo)
# Reinicia TODOS os servicos PM2 para garantir que pegam codigo novo.
# Se nao reiniciar, servicos com codigo antigo continuam respondendo leads.

set -euo pipefail

FRALIB_DIR="/root/fralib"
WEB_DIR="/var/www/fralib"
LOG_FILE="/root/fralib-logs/deploy.log"
LEGACY_FRONTEND_CRON="/etc/cron.d/fralib-frontend-sync"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Deploy iniciado ==="

# Deploy only when master itself changes
DEPLOY_MASTER="false"
while read -r oldrev newrev refname; do
    log "Recebido: $refname $oldrev -> $newrev"
    if [ "$refname" = "refs/heads/master" ]; then
        DEPLOY_MASTER="true"
    fi
done

if [ "$DEPLOY_MASTER" != "true" ]; then
    log "Push sem alteracao em master; deploy ignorado"
    exit 0
fi

# 1. Atualizar working tree usando fetch + reset
log "Atualizando $FRALIB_DIR..."
cd "$FRALIB_DIR"

ENV_BACKUP=""
if [ -f .env ]; then
    ENV_BACKUP="$(mktemp /tmp/fralib-env.XXXXXX)"
    cp -p .env "$ENV_BACKUP"
fi

git fetch origin master 2>&1 | tee -a "$LOG_FILE" || log "ERRO: git fetch falhou"
git reset --hard origin/master 2>&1 | tee -a "$LOG_FILE" || {
    log "ERRO FATAL: git reset --hard falhou"
    exit 1
}

if [ -n "$ENV_BACKUP" ] && [ -f "$ENV_BACKUP" ]; then
    cp -p "$ENV_BACKUP" .env
    rm -f "$ENV_BACKUP"
fi

log "Codigo atualizado para: $(git rev-parse --short HEAD)"

if [ -f "$LEGACY_FRONTEND_CRON" ]; then
    rm -f "$LEGACY_FRONTEND_CRON"
    log "Removido cron legado de frontend: $LEGACY_FRONTEND_CRON"
fi

# 2. Clear pycache para forcar reload do codigo novo
log "Limpando __pycache__..."
find "$FRALIB_DIR/backend" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$FRALIB_DIR/scripts" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# 3. Instalar dependencias Python se mudou
log "Verificando dependencias Python..."
if [ -f backend/requirements.txt ]; then
    if ! "$FRALIB_DIR/venv/bin/pip" install -r backend/requirements.txt --quiet 2>&1 | tail -3 | tee -a "$LOG_FILE"; then
        log "ATENCAO: instalacao de dependencias pode ter falhar"
    fi
fi

# 4. Migrations alembic
log "Rodando migrations..."
cd "$FRALIB_DIR"
if [ -f alembic.ini ]; then
    "$FRALIB_DIR/venv/bin/alembic" upgrade head 2>&1 | tail -5 | tee -a "$LOG_FILE" || log "ATENCAO: migrations falharam"
fi

# 5. Publicar frontend estatico
log "Publicando frontend em $WEB_DIR..."
install -d "$WEB_DIR"
for html in admin.html landing.html login.html planos.html studio.html superadmin.html termos.html privacidade.html; do
    if [ -f "$FRALIB_DIR/frontend/$html" ]; then
        cp -a "$FRALIB_DIR/frontend/$html" "$WEB_DIR/$html"
    fi
done
for legacy_html in dashboard.html landing-b.html landing-c.html landing-new.html landing-backup-20260511.html landing2.html landing_backup.html; do
    if [ -f "$WEB_DIR/$legacy_html" ]; then
        rm -f "$WEB_DIR/$legacy_html"
        log "Removido HTML legado: $legacy_html"
    fi
    if [ -e "$WEB_DIR/$legacy_html" ]; then
        log "ERRO: HTML legado ainda publicado: $WEB_DIR/$legacy_html"
        exit 1
    fi
done

for dir in blog docs css js static images; do
    if [ -d "$FRALIB_DIR/frontend/$dir" ]; then
        cp -a "$FRALIB_DIR/frontend/$dir" "$WEB_DIR"/ 2>/dev/null || true
    fi
done

# 6. CRITICAL: Reiniciar TODOS os servicos PM2 (nao so 'fralib')
# Sem isso, fralib-franz-worker, fralib-wpp-listener, fralib-hermes-watchdog
# continuam com codigo antigo de horas/dias atras.
log "Reiniciando TODOS os servicos PM2 (reload + delete+start)..."
pm2 reload ecosystem.config.js 2>&1 | tail -10 | tee -a "$LOG_FILE" || {
    log "pm2 reload falhou - tentando kill+start"
    pm2 kill 2>&1
    sleep 2
    pm2 start ecosystem.config.js 2>&1 | tail -10 | tee -a "$LOG_FILE"
}

# 7. Salvar snapshot PM2 para reviver apos reboot
pm2 save 2>&1 | tail -2 | tee -a "$LOG_FILE" || true

log "=== Deploy concluido com sucesso ==="
log "Servicos online: $(pm2 list 2>/dev/null | grep -c online)"
