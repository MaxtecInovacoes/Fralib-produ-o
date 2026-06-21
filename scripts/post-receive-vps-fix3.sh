#!/bin/bash
# post-receive hook — deploy automatico do FraLib (CORRIGIDO v3)
# Usa systemctl (servicos systemd) em vez de pm2, que eh o gerenciador real no VPS.
# v3: unset GIT_DIR/GIT_WORK_TREE no inicio para resolver
#     "fatal: not a git repository: '.'" quando rodando via git-receive-pack.

set -euo pipefail

FRALIB_DIR="/root/fralib"
WEB_DIR="/var/www/fralib"
LOG_FILE="/root/fralib-logs/deploy.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# FIX v3: Quando este hook e executado via git-receive-pack, o ambiente vem com
# GIT_DIR=/root/repos/fralib (o bare repo). O `cd /root/fralib` nao basta, pois
# o GIT_DIR exportado sobrescreve. Resetamos essas variaveis para o hook poder
# manipular o repo em /root/fralib normalmente.
unset GIT_DIR
unset GIT_WORK_TREE
unset GIT_INDEX_FILE

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

# 1. Atualizar working tree
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

# 2. Sincronizar frontend/ com o web dir (nginx serve de /var/www/fralib/)
log "Sincronizando $FRALIB_DIR/frontend/ -> $WEB_DIR/..."
if [ -d "$FRALIB_DIR/frontend" ] && [ -d "$WEB_DIR" ]; then
    # Copia o conteudo de frontend/ pra raiz do web dir (mantem imagens/, css/, js/, *.html)
    cp -ru "$FRALIB_DIR/frontend/." "$WEB_DIR/" 2>&1 | tee -a "$LOG_FILE" || {
        log "ERRO: cp frontend/ -> $WEB_DIR/ falhou"
    }
    log "Frontend sincronizado em $WEB_DIR"
else
    log "AVISO: $FRALIB_DIR/frontend ou $WEB_DIR nao existem - pulando sync"
fi

# 3. Reload nginx (se existir)
if command -v nginx >/dev/null 2>&1; then
    log "Recarregando nginx..."
    nginx -s reload 2>&1 | tee -a "$LOG_FILE" || {
        log "ERRO: nginx reload falhou - tentando systemctl"
        systemctl reload nginx 2>&1 | tee -a "$LOG_FILE" || true
    }
elif command -v systemctl >/dev/null 2>&1; then
    log "Recarregando nginx via systemctl..."
    systemctl reload nginx 2>&1 | tee -a "$LOG_FILE" || true
else
    log "AVISO: nginx nem systemctl encontrados - reload manual necessario"
fi

log "=== Deploy concluido ==="
