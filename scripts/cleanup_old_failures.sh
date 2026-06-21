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
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="fralib_db"
DB_USER="postgres"

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "=== Iniciando limpeza (retencao: ${RETENTION_DAYS}d) ==="

# 1. Falhas resolvidas antigas
RESOLVED=$(sudo -u postgres psql -p "$DB_PORT" -d "$DB_NAME" -t -c "
WITH deleted AS (
  DELETE FROM pipeline_failures
  WHERE resolvido = TRUE
    AND resolvido_em < NOW() - INTERVAL '${RETENTION_DAYS} days'
  RETURNING 1
)
SELECT COUNT(*) FROM deleted;
" 2>&1 | tail -1 | tr -d ' ')
log "Falhas resolvidas removidas: $RESOLVED"

# 2. Falhas ABERTAS muito antigas (>30 dias, sem chance de retry)
OPEN_OLD=$(sudo -u postgres psql -p "$DB_PORT" -d "$DB_NAME" -t -c "
WITH deleted AS (
  DELETE FROM pipeline_failures
  WHERE resolvido = FALSE
    AND criado_em < NOW() - INTERVAL '30 days'
    AND tentativas_automaticas >= 5
  RETURNING 1
)
SELECT COUNT(*) FROM deleted;
" 2>&1 | tail -1 | tr -d ' ')
log "Falhas abertas (>30d, >=5 tentativas) removidas: $OPEN_OLD"

# 3. Jobs da fila concluidos/erro/interrompido antigos
JOBS_DONE=$(sudo -u postgres psql -p "$DB_PORT" -d "$DB_NAME" -t -c "
WITH deleted AS (
  DELETE FROM pipeline_queue
  WHERE status IN ('concluido', 'erro', 'interrompido')
    AND criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days'
  RETURNING 1
)
SELECT COUNT(*) FROM deleted;
" 2>&1 | tail -1 | tr -d ' ')
log "Jobs antigos removidos: $JOBS_DONE"

# 4. Vacuum para recuperar espaco
log "Rodando VACUUM ANALYZE..."
sudo -u postgres psql -p "$DB_PORT" -d "$DB_NAME" -c "VACUUM ANALYZE pipeline_failures; VACUUM ANALYZE pipeline_queue;" >> "$LOG_FILE" 2>&1

# 5. Estatisticas finais
log "=== Estado apos limpeza ==="
sudo -u postgres psql -p "$DB_PORT" -d "$DB_NAME" -c "
SELECT
  (SELECT COUNT(*) FROM pipeline_failures) AS total_failures,
  (SELECT COUNT(*) FROM pipeline_failures WHERE resolvido = FALSE) AS failures_abertas,
  (SELECT COUNT(*) FROM pipeline_queue WHERE status NOT IN ('concluido','erro','interrompido')) AS jobs_ativos;
" >> "$LOG_FILE" 2>&1

log "=== Limpeza concluida ==="