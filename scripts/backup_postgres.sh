#!/bin/bash
# =========================================================================
# backup_postgres.sh - Backup automático do PostgreSQL do FraLib
# =========================================================================
# Estratégia:
#   - Diário (02:00) - mantém últimos 7
#   - Semanal (domingo 03:00) - mantém últimos 4
#   - Teste de integridade automático
#   - Log em /var/log/fralib/backup.log
# =========================================================================
set -e

# Configuração
BACKUP_ROOT="/var/backups/fralib/postgres"
DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
LOG_FILE="/var/log/fralib/backup.log"
KEEP_DAILY=7
KEEP_WEEKLY=4
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=segunda, 7=domingo
DAY_OF_MONTH=$(date +%d)

# Carrega credenciais do .env
ENV_FILE="/root/fralib/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[$TIMESTAMP] ❌ .env não encontrado em $ENV_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Extrai DATABASE_URL
DATABASE_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
if [ -z "$DATABASE_URL" ]; then
    echo "[$TIMESTAMP] ❌ DATABASE_URL vazio no .env" | tee -a "$LOG_FILE"
    exit 1
fi

# Parse URL: postgresql://user:pass@host:port/db
DB_USER=$(echo "$DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')
DB_PASS=$(echo "$DATABASE_URL" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$DATABASE_URL" | sed -E 's|.*/([^?]+)(\?.*)?$|\1|')

# Cria diretórios
mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" 2>/dev/null || {
    echo "[$TIMESTAMP] ❌ Sem permissão para criar $BACKUP_ROOT" | tee -a "$LOG_FILE"
    exit 1
}

# Log início
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "═══════════════════════════════════════"
log "🔄 Iniciando backup do PostgreSQL"
log "DB: $DB_NAME @ $DB_HOST:$DB_PORT (user: $DB_USER)"

# Backup com pg_dump (formato custom, comprimível)
BACKUP_FILE="$DAILY_DIR/${DB_NAME}_${TIMESTAMP}.dump"

export PGPASSWORD="$DB_PASS"
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -Fc -Z 9 --no-owner --no-acl \
    -f "$BACKUP_FILE" 2>> "$LOG_FILE"; then

    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✅ Backup criado: $(basename $BACKUP_FILE) ($SIZE)"

    # Teste de integridade (readable + table count)
    if pg_restore -l "$BACKUP_FILE" > /dev/null 2>&1; then
        TABLES=$(pg_restore -l "$BACKUP_FILE" 2>/dev/null | grep -c "TABLE" || echo "?")
        log "✅ Integridade OK ($TABLES tabelas)"
    else
        log "❌ Arquivo de backup CORROMPIDO!"
        rm -f "$BACKUP_FILE"
        exit 2
    fi
else
    log "❌ pg_dump FALHOU"
    exit 3
fi

# Promove para semanal se for domingo
if [ "$DAY_OF_WEEK" = "7" ]; then
    WEEKLY_FILE="$WEEKLY_DIR/${DB_NAME}_weekly_${TIMESTAMP}.dump"
    cp "$BACKUP_FILE" "$WEEKLY_FILE"
    log "📅 Backup semanal arquivado"
fi

# Retenção: remove daily antigos
DELETED_DAILY=$(find "$DAILY_DIR" -name "*.dump" -mtime +$KEEP_DAILY -delete -print | wc -l)
[ "$DELETED_DAILY" -gt 0 ] && log "🗑️  Removidos $DELETED_DAILY backups daily (>${KEEP_DAILY}d)"

# Retenção: remove weekly antigos
DELETED_WEEKLY=$(find "$WEEKLY_DIR" -name "*.dump" -mtime +$((KEEP_WEEKLY * 7)) -delete -print | wc -l)
[ "$DELETED_WEEKLY" -gt 0 ] && log "🗑️  Removidos $DELETED_WEEKLY backups weekly (>${KEEP_WEEKLY}w)"

# Estatísticas
TOTAL_DAILY=$(ls -1 "$DAILY_DIR"/*.dump 2>/dev/null | wc -l)
TOTAL_WEEKLY=$(ls -1 "$WEEKLY_DIR"/*.dump 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_ROOT" 2>/dev/null | cut -f1)

log "📊 Estado: $TOTAL_DAILY daily + $TOTAL_WEEKLY weekly = $TOTAL_SIZE"
log "═══════════════════════════════════════"

exit 0