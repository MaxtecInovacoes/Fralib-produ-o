#!/bin/bash
# =========================================================================
# cleanup_old_failures.sh - Limpeza diaria (retencao: 7 dias)
# =========================================================================
# Roda todo dia 03:00 UTC (apos backup 02:00)
# Mantem ultimos 7 dias para debug
# =========================================================================
set -e

LOG_FILE="/var/log/fralib/cleanup.log"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
RETENTION_LONG_DAYS="${RETENTION_LONG_DAYS:-30}"

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "=== Iniciando limpeza (retencao: ${RETENTION_DAYS}d / ${RETENTION_LONG_DAYS}d) ==="

count_query() {
    local sql="$1"
    sudo -u postgres psql -p 5433 -d fralib_db -t -A -c "$sql" 2>/dev/null | head -1
}

# =========================================================================
# LIMPEZA 7 DIAS (padrao)
# =========================================================================

# 1. Falhas resolvidas antigas
RESOLVED=$(count_query "WITH d AS (DELETE FROM pipeline_failures WHERE resolvido = TRUE AND resolvido_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "pipeline_failures (resolvidas >${RETENTION_DAYS}d): ${RESOLVED:-0}"

# 2. Jobs concluidos/erro/interrompido antigos
JOBS_DONE=$(count_query "WITH d AS (DELETE FROM pipeline_queue WHERE status IN ('concluido', 'erro', 'interrompido') AND criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "pipeline_queue (concluidos >${RETENTION_DAYS}d): ${JOBS_DONE:-0}"

# 3. Jobs antigos da tabela jobs (worker logs)
JOBS_OLD=$(count_query "WITH d AS (DELETE FROM jobs WHERE criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "jobs (>${RETENTION_DAYS}d): ${JOBS_OLD:-0}"

# 4. LLM usage logs antigos (custo/uso detalhado)
LLM_USAGE=$(count_query "WITH d AS (DELETE FROM llm_usage WHERE criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "llm_usage (>${RETENTION_DAYS}d): ${LLM_USAGE:-0}"

# 5. Pipeline traces/spans antigos
TRACES=$(count_query "WITH d AS (DELETE FROM pipeline_traces WHERE created_at < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "pipeline_traces (>${RETENTION_DAYS}d): ${TRACES:-0}"

SPANS=$(count_query "WITH d AS (DELETE FROM pipeline_run_spans WHERE started_at < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "pipeline_run_spans (>${RETENTION_DAYS}d): ${SPANS:-0}"

# 6. Audit log
AUDIT=$(count_query "WITH d AS (DELETE FROM audit_log WHERE criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "audit_log (>${RETENTION_DAYS}d): ${AUDIT:-0}"

# 7. Leads temp/rascunho antigos (sem html_gerado e antigos)
LEADS_DRAFT=$(count_query "WITH d AS (DELETE FROM leads WHERE (html_gerado IS NULL OR html_gerado = '') AND criado_em < NOW() - INTERVAL '${RETENTION_DAYS} days' AND status NOT IN ('processando', 'publicado') RETURNING 1) SELECT COUNT(*) FROM d;")
log "leads rascunho (>${RETENTION_DAYS}d): ${LEADS_DRAFT:-0}"

# =========================================================================
# LIMPEZA 30 DIAS (historico)
# =========================================================================

# 8. Falhas abertas muito antigas (sem chance de retry)
OPEN_OLD=$(count_query "WITH d AS (DELETE FROM pipeline_failures WHERE resolvido = FALSE AND criado_em < NOW() - INTERVAL '${RETENTION_LONG_DAYS} days' AND tentativas_automaticas >= 5 RETURNING 1) SELECT COUNT(*) FROM d;")
log "pipeline_failures (abertas >${RETENTION_LONG_DAYS}d): ${OPEN_OLD:-0}"

# 9. Hermes incidents resolvidos antigos
HERMES=$(count_query "WITH d AS (DELETE FROM hermes_incidents WHERE status = 'resolved' AND created_at < NOW() - INTERVAL '${RETENTION_LONG_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "hermes_incidents (resolved >${RETENTION_LONG_DAYS}d): ${HERMES:-0}"

# 10. LLM budget ledger antigo (sao snapshots diarios, 30d basta)
BUDGET=$(count_query "WITH d AS (DELETE FROM llm_budget_ledger WHERE created_at < NOW() - INTERVAL '${RETENTION_LONG_DAYS} days' RETURNING 1) SELECT COUNT(*) FROM d;")
log "llm_budget_ledger (>${RETENTION_LONG_DAYS}d): ${BUDGET:-0}"

# =========================================================================
# VACUUM para recuperar espaco em disco
# =========================================================================
log "Rodando VACUUM ANALYZE..."
sudo -u postgres psql -p 5433 -d fralib_db -c "
VACUUM ANALYZE pipeline_failures;
VACUUM ANALYZE pipeline_queue;
VACUUM ANALYZE jobs;
VACUUM ANALYZE llm_usage;
VACUUM ANALYZE llm_budget_ledger;
VACUUM ANALYZE pipeline_traces;
VACUUM ANALYZE pipeline_run_spans;
VACUUM ANALYZE audit_log;
VACUUM ANALYZE hermes_incidents;
" >> "$LOG_FILE" 2>&1 || true

# =========================================================================
# ESTATISTICAS FINAIS
# =========================================================================
log "=== Estado apos limpeza ==="
sudo -u postgres psql -p 5433 -d fralib_db -c "
SELECT
  (SELECT COUNT(*) FROM pipeline_failures) AS pipeline_failures,
  (SELECT COUNT(*) FROM pipeline_failures WHERE resolvido = FALSE) AS failures_abertas,
  (SELECT COUNT(*) FROM pipeline_queue WHERE status NOT IN ('concluido','erro','interrompido')) AS jobs_ativos,
  (SELECT COUNT(*) FROM jobs) AS jobs_total,
  (SELECT COUNT(*) FROM llm_usage) AS llm_usage,
  (SELECT COUNT(*) FROM llm_budget_ledger) AS llm_budget,
  (SELECT COUNT(*) FROM hermes_incidents) AS hermes_incidents;
" >> "$LOG_FILE" 2>&1 || true

log "=== Limpeza concluida ==="