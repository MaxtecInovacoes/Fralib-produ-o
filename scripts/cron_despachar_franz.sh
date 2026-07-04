#!/bin/bash
# Sprint 1.2 - Outreach do Franz + processador da fila outbound.
#
# Roda via cron a cada 2min. Faz 2 coisas:
#   1. Enfileira ate 2 leads pendentes_wpp (jitter 3-7min entre cada)
#   2. Processa 1 msg da fila outbound (rate limit: 1 msg/10min por tenant)
#
# Meta de cadencia: ~2 msgs a cada 10min com intervalos variados.
#
# Sai com exit code 0 mesmo se cron retornou 200 (curl cron retorna
# rapido se nao tem lead). Cron seguinte tenta de novo.
set -uo pipefail
export PATH="/root/fralib/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Carrega env (CRON_SECRET, DATABASE_URL, MEOWHATS_URL, etc)
if [ -f /etc/fralib/fralib.env ]; then
    set -a
    . /etc/fralib/fralib.env
    set +a
fi
export FRALIB_MEMORY_DIR=/var/lib/fralib/memory

FRANZ_URL="http://localhost:8000/api/cron/despachar-fila-franz"
QUEUE_URL="http://localhost:8000/api/cron/processar-fila-outbound"
SECRET="${CRON_SECRET:-}"

if [ -z "$SECRET" ]; then
    echo "[$(date -Iseconds)] CRON_SECRET nao definido no env - saindo" >> /var/log/fralib-franz-cron.log
    exit 0
fi

call_cron() {
    local url="$1"
    local label="$2"
    local attempt=1
    while [ $attempt -le 3 ]; do
        HTTP_CODE=$(curl -sS --max-time 110 -o /tmp/franz_out.json -w "%{http_code}" \
            -X POST "$url" \
            -H "X-Cron-Secret: $SECRET" 2>/dev/null) || HTTP_CODE="000"

        HTTP_CODE=$(echo "$HTTP_CODE" | head -c 3)
        [ -z "$HTTP_CODE" ] && HTTP_CODE="000"

        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "500" ]; then
            if [ -s /tmp/franz_out.json ]; then
                RESP=$(head -c 300 /tmp/franz_out.json)
                echo "[$(date -Iseconds)] [$label] OK code=$HTTP_CODE resp=$RESP" >> /var/log/fralib-franz-cron.log
            else
                echo "[$(date -Iseconds)] [$label] OK code=$HTTP_CODE (sem body)" >> /var/log/fralib-franz-cron.log
            fi
            return 0
        fi

        if [ "$HTTP_CODE" = "000" ]; then
            echo "[$(date -Iseconds)] [$label] WARN tentativa $attempt: servidor offline" >> /var/log/fralib-franz-cron.log
            sleep 5
            attempt=$((attempt + 1))
            continue
        fi

        echo "[$(date -Iseconds)] [$label] ERR code=$HTTP_CODE body=$(head -c 300 /tmp/franz_out.json 2>/dev/null)" >> /var/log/fralib-franz-cron.log
        return 0
    done
    return 0
}

# 1. Enfileira leads pendentes (gera ate 2 msgs com jitter 3-7min entre elas)
call_cron "$FRANZ_URL" "FRANZ"

# 2. Processa a fila outbound (1 msg por vez, rate limit 1/10min por tenant)
call_cron "$QUEUE_URL" "QUEUE"

exit 0
