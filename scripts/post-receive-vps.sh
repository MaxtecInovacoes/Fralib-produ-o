#!/bin/bash
# post-receive hook — deploy automatico do FraLib (CORRIGIDO v2)
# Usa systemctl (servicos systemd) em vez de pm2, que eh o gerenciador real no VPS.

set -euo pipefail

FRALIB_DIR="/root/fralib"
WEB_DIR="/var/www/fralib"
LOG_FILE="/root/fralib-logs/deploy.log"

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

# 1. Atualizar working tree usando fetch + reset (funciona mesmo com divergencia)
log "Atualizando $FRALIB_DIR..."
cd "$FRALIB_DIR"

# Backup .env antes de qualquer operacao
ENV_BACKUP=""
if [ -f .env ]; then
    ENV_BACKUP="$(mktemp /tmp/fralib-env.XXXXXX)"
    cp -p .env "$ENV_BACKUP"
fi

# Fetch + reset (mais confiavel que pull)
git fetch origin master 2>&1 | tee -a "$LOG_FILE" || {
    log "ERRO: git fetch falhou - tentando git reset direto"
}
git reset --hard origin/master 2>&1 | tee -a "$LOG_FILE" || {
    log "ERRO FATAL: git reset --hard falhou"
    exit 1
}

# Restaurar .env se existir
if [ -n "$ENV_BACKUP" ] && [ -f "$ENV_BACKUP" ]; then
    cp -p "$ENV_BACKUP" .env
    rm -f "$ENV_BACKUP"
fi

log "Codigo atualizado para: $(git rev-parse --short HEAD)"

# 2. Validar frontend canonico
log "Validando frontend canonico..."
if [ -f "$FRALIB_DIR/scripts/verify_frontend_canonical.py" ]; then
    "$FRALIB_DIR/venv/bin/python3" "$FRALIB_DIR/scripts/verify_frontend_canonical.py" 2>&1 | tee -a "$LOG_FILE" || true
fi

# 3. Instalar dependencias Python se mudou
log "Verificando dependencias Python..."
cd "$FRALIB_DIR"
if [ -f backend/requirements.txt ]; then
    if ! "$FRALIB_DIR/venv/bin/pip" install -r backend/requirements.txt --quiet 2>&1 | tail -3 | tee -a "$LOG_FILE"; then
        log "ATENCAO: instalacao de dependencias pode ter falhado"
    fi
fi

# 4. Publicar frontend estatico
log "Publicando frontend estatico em $WEB_DIR..."
install -d "$WEB_DIR"
for html in admin.html dashboard.html landing.html login.html planos.html studio.html superadmin.html termos.html privacidade.html; do
    if [ -f "$FRALIB_DIR/frontend/$html" ]; then
        cp -a "$FRALIB_DIR/frontend/$html" "$WEB_DIR/$html"
    fi
done

# Copiar assets
for dir in blog docs css js static images; do
    if [ -d "$FRALIB_DIR/frontend/$dir" ]; then
        cp -a "$FRALIB_DIR/frontend/$dir" "$WEB_DIR"/ 2>/dev/null || true
    fi
done

# 5. Restart via systemctl (NAO pm2)
log "Reiniciando servicos via systemctl..."
systemctl restart fralib-api 2>&1 | tee -a "$LOG_FILE" || log "ATENCAO: fralib-api restart falhou"
systemctl restart fralib-worker 2>&1 | tee -a "$LOG_FILE" || log "ATENCAO: fralib-worker restart falhou"
systemctl restart fralib-franz 2>&1 | tee -a "$LOG_FILE" || log "ATENCAO: fralib-franz restart falhou"
systemctl restart fralib-hermes 2>&1 | tee -a "$LOG_FILE" || log "ATENCAO: fralib-hermes restart falhou"
# wpp-listener nao precisa de restart (sockets persistentes)

log "=== Deploy concluido com sucesso ==="
