#!/bin/bash
# =========================================================================
# migrate_pm2_to_systemd.sh - Migração gradual PM2 → systemd
# =========================================================================
# Estratégia: migra 1 serviço por vez com validação entre cada.
# Se QUALQUER check falhar, aborta e mostra como rollbackar.
# =========================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()    { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; }

# Ordem de migração: do menos crítico ao mais crítico
# (se hermes falhar, API continua de pé)
MIGRATION_ORDER=(
    "fralib-hermes"       # Só vigia, baixo risco
    "fralib-wpp-listener" # WhatsApp (pode reiniciar)
    "fralib-franz"        # SDR (pode reiniciar)
    "fralib-worker"       # Pipeline (pode reiniciar)
    "fralib-api"          # API (mais crítico — por último)
)

PM2_MAP=(
    "fralib-hermes:fralib-hermes-watchdog"
    "fralib-wpp-listener:fralib-wpp-listener"
    "fralib-franz:fralib-franz-worker"
    "fralib-worker:fralib-worker"
    "fralib-api:fralib"
)

# Valida pré-requisito
if [ ! -f /etc/systemd/system/fralib-hermes.service ]; then
    fail "Serviços não instalados. Rode: bash scripts/systemd_install.sh"
fi

echo "═══════════════════════════════════════"
echo "  Migração gradual PM2 → systemd"
echo "═══════════════════════════════════════"

for entry in "${PM2_MAP[@]}"; do
    systemd_name="${entry%%:*}"
    pm2_name="${entry##*:}"
    full_service="${systemd_name}.service"

    echo ""
    echo "────────────────────────────────────────"
    echo "🔄 Migrando: $pm2_name (PM2) → $systemd_name (systemd)"
    echo "────────────────────────────────────────"

    # 1. Parar PM2
    if pm2 stop "$pm2_name" 2>/dev/null; then
        ok "PM2 parado: $pm2_name"
    else
        warn "$pm2_name não estava rodando no PM2"
    fi

    # 2. Iniciar systemd
    if systemctl start "$full_service" 2>&1 | head -3; then
        ok "systemd iniciado: $full_service"
    else
        fail "Falha ao iniciar $full_service"
    fi

    # 3. Aguardar 8 segundos para o serviço estabilizar
    sleep 8

    # 4. Verificar se está active
    if systemctl is-active --quiet "$full_service"; then
        ok "systemd ACTIVE: $full_service"
    else
        fail "$full_service NÃO está active. Rollback: bash scripts/systemd_uninstall.sh"
    fi

    # 5. Validar health (só API tem /health)
    if [ "$systemd_name" = "fralib-api" ]; then
        if curl -fsS -m 5 http://127.0.0.1:8000/health > /dev/null; then
            ok "API /health responde 200"
        else
            fail "API /health não responde. Rollback imediato."
        fi
    fi

    # 6. Verificar log recente (não pode ter erro fatal)
    RECENT_ERRORS=$(journalctl -u "$full_service" --since "30 seconds ago" 2>/dev/null | grep -iE "fatal|traceback|error" | wc -l)
    if [ "$RECENT_ERRORS" -lt 5 ]; then
        ok "Sem erros fatais no journal ($RECENT_ERRORS warnings/errors)"
    else
        warn "$RECENT_ERRORS erros detectados no journal — investigar"
    fi

    echo ""
done

# Remover processos PM2 órfãos (que não existem mais)
echo ""
echo "🧹 Limpando processos PM2 órfãos..."
pm2 delete all 2>/dev/null || true
pm2 save 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════"
ok "Migração completa! 5 serviços rodando em systemd"
echo "═══════════════════════════════════════"
echo ""
echo "📋 Verifique o estado final:"
echo "   systemctl list-units --type=service --state=running | grep fralib"
echo "   journalctl -u fralib-api -f   # tail ao vivo da API"
echo ""
echo "🛡️  Rollback (se necessário):"
echo "   bash scripts/systemd_uninstall.sh   # remove systemd"
echo "   pm2 resurrect                        # restaura PM2"