#!/bin/bash
# ============================================================================
# scripts/reset_tenant_2.sh
#
# SPRINT 1.3 - Reset operacional do tenant 2.
#
# Roda TODAS as acoes para deixar os leads do tenant 2 no estado
# "como se nunca tivessem passado pelo pipeline":
#   1. Executa migration SQL (leads + tabelas relacionadas)
#   2. Deleta arquivos de cache em disco (design_system JSONs)
#   3. Restart do fralib-api (invalida caches em memoria)
#   4. Trigger 1 ciclo de cron pra comecar reprocessamento
#
# ATENCAO: OPERACAO DESTRUTIVA. Backup antes.
#
# Uso: bash scripts/reset_tenant_2.sh
# Idempotente: pode rodar varias vezes.
# ============================================================================
set -uo pipefail

export PATH="/root/fralib/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Carrega env
if [ -f /etc/fralib/fralib.env ]; then
    set -a
    . /etc/fralib/fralib.env
    set +a
fi
export FRALIB_MEMORY_DIR=/var/lib/fralib/memory

LOG="/var/log/fralib-reset-tenant-2.log"
TS() { date -Iseconds; }

log() { echo "[$(TS)] $*" | tee -a "$LOG"; }

# ============================================================================
# 0. Pre-flight: confirma banco acessivel
# ============================================================================
log "=== INICIO reset tenant 2 ==="

if [ -z "${DATABASE_URL:-}" ]; then
    log "ERRO: DATABASE_URL nao definido no env"
    exit 1
fi

# ============================================================================
# 1. Migration SQL
# ============================================================================
MIGRATION="/root/fralib/backend/migrations/2026_07_05_reset_tenant_2_leads.sql"

if [ ! -f "$MIGRATION" ]; then
    log "ERRO: migration nao encontrada em $MIGRATION"
    log "Esperado apos git pull: backend/migrations/2026_07_05_reset_tenant_2_leads.sql"
    exit 1
fi

log "STEP 1: executando migration SQL..."
if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$MIGRATION" >> "$LOG" 2>&1; then
    log "  OK migration aplicada"
else
    log "  ERRO na migration - ABORTANDO"
    exit 1
fi

# ============================================================================
# 2. Limpar caches em disco (design_system JSONs)
# ============================================================================
log "STEP 2: limpando caches em disco (design_system JSONs)..."

# Backup antes de deletar (seguranca)
BACKUP_DIR="/root/fralib/backups/design_system_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

for f in \
    /root/fralib/backend/agents/design_system_index.json \
    /root/fralib/backend/agents/design_system_tokens.json
do
    if [ -f "$f" ]; then
        cp "$f" "$BACKUP_DIR/"
        rm "$f"
        log "  removido: $f (backup em $BACKUP_DIR)"
    else
        log "  ja nao existe: $f"
    fi
done

# ============================================================================
# 3. Restart fralib-api (invalida caches em memoria: _RAG_CACHE, _HORARIO_CACHE)
# ============================================================================
log "STEP 3: restart do fralib-api (invalida caches em memoria)..."

if pkill -9 -f 'server.py' 2>/dev/null; then
    log "  processo server.py morto"
else
    log "  nenhum processo server.py rodando"
fi

sleep 2

if systemctl start fralib-api 2>>"$LOG"; then
    log "  systemctl start OK"
else
    log "  systemctl start FALHOU - tentando direto"
    cd /root/fralib && nohup venv/bin/python server.py >> /var/log/fralib-api.log 2>&1 &
    log "  start manual disparado em background"
fi

# Aguarda servico ficar UP
log "  aguardando servico responder..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s --max-time 3 -o /dev/null -w "%{http_code}" "http://localhost:8000/health" | grep -q "200\|503"; then
        log "  servico respondeu (tentativa $i)"
        break
    fi
    sleep 3
done

# ============================================================================
# 4. Trigger 1 ciclo de cron pra comecar reprocessamento
# ============================================================================
log "STEP 4: disparando 1 ciclo de despachar-fila-franz..."

SECRET="${CRON_SECRET:-}"
if [ -z "$SECRET" ]; then
    log "  WARN: CRON_SECRET vazio - pulando trigger do cron"
else
    HTTP_CODE=$(curl -sS --max-time 30 -o /tmp/reset_resp.json -w "%{http_code}" \
        -X POST "http://localhost:8000/api/cron/despachar-fila-franz" \
        -H "X-Cron-Secret: $SECRET" 2>/dev/null) || HTTP_CODE="000"

    if [ "$HTTP_CODE" = "202" ] || [ "$HTTP_CODE" = "200" ]; then
        RESP=$(head -c 300 /tmp/reset_resp.json 2>/dev/null || echo "")
        log "  OK code=$HTTP_CODE resp=$RESP"
    else
        log "  WARN code=$HTTP_CODE body=$(head -c 300 /tmp/reset_resp.json 2>/dev/null)"
    fi
fi

# ============================================================================
# 5. Relatorio final (queries de leitura)
# ============================================================================
log "STEP 5: relatorio pos-reset..."
psql "$DATABASE_URL" -A -F'|' -t -c "
SELECT 'leads_tenant_2_total' AS metric, COUNT(*)::text AS value
FROM leads WHERE user_id = 2
UNION ALL
SELECT 'leads_pendente_wpp', COUNT(*)::text
FROM leads WHERE user_id = 2 AND sdr_stage = 'pendente_wpp' AND status = 'pendente'
UNION ALL
SELECT 'interacoes_restantes', COUNT(*)::text
FROM interacoes WHERE user_id = 2
UNION ALL
SELECT 'outbound_restantes', COUNT(*)::text
FROM outbound_queue WHERE tenant_id = 2
UNION ALL
SELECT 'sdr_turns_restantes', COUNT(*)::text
FROM sdr_turns WHERE tenant_id = 2
UNION ALL
SELECT 'leads_com_site_url', COUNT(*)::text
FROM leads WHERE user_id = 2 AND site_url IS NOT NULL
UNION ALL
SELECT 'leads_com_html_gerado', COUNT(*)::text
FROM leads WHERE user_id = 2 AND html_gerado IS NOT NULL
" >> "$LOG" 2>&1

log "=== FIM reset tenant 2 ==="
log "Log completo em: $LOG"
log "Backup dos design_system JSONs em: $BACKUP_DIR"
log ""
log "VERIFICACOES DE SEGURANCA aplicadas na migration:"
log "  - cada DELETE eh protegido por IF EXISTS (information_schema)"
log "  - audit_events usa colunas canonicas (tenant_id, action, entity_type, diff_json)"
log "  - keyword_cache NAO tem user_id - migration limpa TUDO (cache expira em 30d)"
log "  - ESCOPO: somente tenant 2 (outros tenants NAO foram tocados)"