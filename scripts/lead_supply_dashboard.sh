#!/bin/bash
#
# Lead Supply Dashboard
# Mostra status em tempo real do sistema de prospeccao.
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e " ${GREEN}[OK]${NC} $1"; }
fail() { echo -e " ${RED}[FAIL]${NC} $1"; }
warn() { echo -e " ${YELLOW}[WARN]${NC} $1"; }

section() {
    echo ""
    echo -e "${BOLD}${CYAN}=== $1 ===${NC}"
}

# ============================================================
# 1. STATUS DOS SERVICOS
# ============================================================
section "STATUS DOS SERVICOS"

echo -n " GOSOM:  "
GOSOM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/api/v1/jobs 2>/dev/null || echo "000")
if [ "$GOSOM_STATUS" = "200" ]; then
    ok "Online (HTTP 200)"
else
    fail "Offline (HTTP $GOSOM_STATUS)"
fi

echo -n " Worker: "
if pm2 jlist 2>/dev/null | grep -q '"name":"worker"'; then
    WORKER_STATUS=$(pm2 jlist 2>/dev/null | python3 -c "import sys,json; [print(d.get('pm2_env',{}).get('status','unknown')) for d in json.load(sys.stdin) if d.get('name')=='worker']" 2>/dev/null || echo "unknown")
    if [ "$WORKER_STATUS" = "online" ]; then
        ok "Online (PM2)"
    else
        fail "Status: $WORKER_STATUS"
    fi
else
    warn "Nao encontrado no PM2"
fi

echo -n " Watchdog: "
if systemctl is-active --quiet lead-supply-watchdog 2>/dev/null; then
    ok "Ativo (systemd)"
elif pgrep -f "lead_supply_watchdog" > /dev/null 2>&1; then
    PID=$(pgrep -f "lead_supply_watchdog" | head -1)
    ok "Executando (PID $PID)"
else
    warn "Nao esta executando"
fi

# ============================================================
# 2. JOBS - ULTIMAS 24H
# ============================================================
section "JOBS - ULTIMAS 24H"
sudo -u postgres psql -d fralib_db -t -c "SELECT status, COUNT(*) FROM jobs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'running' THEN 2 WHEN 'failed' THEN 3 WHEN 'completed' THEN 4 ELSE 5 END" 2>/dev/null | sed 's/|/ /g; s/^/   /'

# ============================================================
# 3. LEADS INVENTORY
# ============================================================
section "LEADS INVENTORY"
sudo -u postgres psql -d fralib_db -t -c "SELECT status, COUNT(*) FROM lead_inventory GROUP BY status ORDER BY CASE status WHEN 'raw' THEN 1 WHEN 'qualifying' THEN 2 WHEN 'approved' THEN 3 WHEN 'discarded' THEN 4 ELSE 5 END" 2>/dev/null | sed 's/|/ /g; s/^/   /'

# ============================================================
# 4. TENANTS COM PROBLEMAS
# ============================================================
section "TENANTS COM PROBLEMAS"
sudo -u postgres psql -d fralib_db -t -c "SELECT c.tenant_id, CASE WHEN c.hunter_pausado THEN 'HUNTER PAUSADO' WHEN c.producao_pausada THEN 'PRODUCAO PAUSADA' WHEN c.segmentos IS NULL OR c.segmentos::text='[]' THEN 'SEM SEGMENTOS' WHEN (SELECT COUNT(*) FROM lead_inventory WHERE tenant_id=c.tenant_id)=0 THEN 'SEM LEADS' END as problema FROM lead_supply_config c WHERE c.ativo=TRUE AND (c.hunter_pausado OR c.producao_pausada OR c.segmentos IS NULL OR c.segmentos::text='[]' OR (SELECT COUNT(*) FROM lead_inventory WHERE tenant_id=c.tenant_id)=0) ORDER BY c.tenant_id LIMIT 10" 2>/dev/null | sed 's/|/ /g; s/^/   /'

# ============================================================
# 5. ULTIMOS 5 EVENTOS
# ============================================================
section "ULTIMOS 5 EVENTOS"
sudo -u postgres psql -d fralib_db -t -c "SELECT SUBSTRING(source,1,12), level, SUBSTRING(message,1,50) FROM lead_supply_events ORDER BY criado_em DESC LIMIT 5" 2>/dev/null | sed 's/|/ /g; s/^/   /'

echo ""
echo "=============================================================="
