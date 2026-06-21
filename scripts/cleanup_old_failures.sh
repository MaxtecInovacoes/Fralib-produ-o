#!/bin/bash
# =========================================================================
# cleanup_old_failures.sh - Limpeza diaria de falhas e jobs antigos
# =========================================================================
# Roda todo dia 03:00 UTC (apos backup 02:00)
# Mantem ultimos 7 dias para debug
# =========================================================================
set -e

LOG_FILE="/var/log/fralib/cleanup.log"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "=== Iniciando limpeza (retencao: ${RETENTION_DAYS}d) ==="

# Query CTE para contar removidos (PostgreSQL < 14 nao tem ROW_COUNT)
count_query() {
    local sql="$1"
    sudo -u postgres psql -p 5433 -d fralib_db -t -A -c "$sql" 2>/dev/null | head -1
}

# 1. Falhas resolvidas antigas
RESOLVED=$(count_query "WITH d AS (DELETE FROM pipeline_failures WHERE resolvido = TRUE AND resolvido_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "Falhas resolvidas removidas: ${RESOLVED:-0}"

# 2. Falhas ABERTAS muito antigas (>30 dias, sem chance de retry)
OPEN_OLD=$(count_query "WITH d AS (DELETE FROM pipeline_failures WHERE resolvido = FALSE AND criado_em < NOW() - INTERVAL '30 days' AND tentativas_automaticas >= 5 RETURNING 1) SELECT COUNT(*) FROM d;")
log "Falhas abertas (>30d, >=5 tentativas) removidas: ${OPEN_OLD:-0}"

# 3. Jobs da fila concluidos/erro/interrompido antigos
JOBS_DONE=$(count_query "WITH d AS (DELETE FROM pipeline_queue WHERE status IN ('concluido', 'erro', 'interrompido') AND criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "Jobs antigos removidos: ${JOBS_DONE:-0}"

# 4. Vacuum para recuperar espaco
log "Rodando VACUUM ANALYZE..."
sudo -u postgres psql -p 5433 -d fralib_db -c "VACUUM ANALYZE pipeline_failures; VACUUM ANALYZE pipeline_queue;" >> "$LOG_FILE" 2>&1 || true

# 5. Estatisticas finais
log "=== Estado apos limpeza ==="
sudo -u postgres psql -p 5433 -d fralib_db -c "SELECT (SELECT COUNT(*) FROM pipeline_failures) AS total_failures, (SELECT COUNT(*) FROM pipeline_failures WHERE resolvido = FALSE) AS failures_abertas, (SELECT COUNT(*) FROM pipeline_queue WHERE status NOT IN ('concluido','erro','interrompido')) AS jobs_ativos;" >> "$LOG_FILE" 2>&1 || true

log "=== Limpeza concluida ==="