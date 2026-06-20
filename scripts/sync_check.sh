#!/bin/bash
# =============================================================================
# sync_check.sh — Verifica sincronia entre repo interno e VPS
# Adicionar ao crontab: */5 * * * * /root/fralib/scripts/sync_check.sh
# =============================================================================

set -euo pipefail

LOG_FILE="/root/fralib-logs/sync_check.log"
ALERT_EMAIL="${SYNC_ALERT_EMAIL:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Verificando sincronia ==="

# Commit no repo interno ( fonte da verdade )
INTERNAL_COMMIT=$(cd /root/repos/fralib && git rev-parse --short HEAD 2>/dev/null || echo "ERROR")
# Commit na VPS
VPS_COMMIT=$(cd /root/fralib && git rev-parse --short origin/master 2>/dev/null || echo "ERROR")

log "Repo interno: $INTERNAL_COMMIT"
log "VPS (origin/master): $VPS_COMMIT"

# Atualizar refs da VPS para garantir que estamos comparando com a verdade
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@187.77.37.72 "cd /root/fralib && git fetch origin 2>/dev/null" 2>/dev/null || true

if [ "$INTERNAL_COMMIT" != "$VPS_COMMIT" ]; then
    log "⚠️  DIVERGÊNCIA DETECTADA!"
    log "   Repo interno está à frente"

    # Forçar sincronização
    log "Sincronizando VPS..."
    ssh root@187.77.37.72 "cd /root/fralib && git fetch origin && git reset --hard origin/master && pm2 restart fralib fralib-worker fralib-franz-worker fralib-hermes-watchdog --update-env" 2>&1 | while read line; do
        log "   VPS: $line"
    done

    # Verificar se sincronizou
    VPS_AFTER=$(ssh root@187.77.37.72 "cd /root/fralib && git rev-parse --short HEAD" 2>/dev/null)
    if [ "$INTERNAL_COMMIT" == "$VPS_AFTER" ]; then
        log "✅ Sincronização corrigida: $VPS_AFTER"
    else
        log "❌ FALHA na sincronização! Repo: $INTERNAL_COMMIT, VPS: $VPS_AFTER"

        # Enviar alerta se email configurado
        if [ -n "$ALERT_EMAIL" ]; then
            echo "ALERTA: FraLib VPS dessincronizada!

Repo interno: $INTERNAL_COMMIT
VPS: $VPS_AFTER

Último deploy pode ter falhado. Verifique manualmente:
ssh root@187.77.37.72
cd /root/fralib
git fetch origin && git reset --hard origin/master
pm2 restart all" | mail -s "[ALERTA] FraLib VPS dessincronizada" "$ALERT_EMAIL" 2>/dev/null || true
        fi
    fi
else
    log "✅ Repo interno e VPS sincronizados: $INTERNAL_COMMIT"
fi

log "=== Verificação concluída ==="
