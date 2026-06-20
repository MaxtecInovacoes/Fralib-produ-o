#!/bin/bash
# =============================================================================
# audit_vps.sh - Audita VPS sem modificar nada (read-only)
# =============================================================================
# Compara VPS com LOCAL. Não executa comandos destrutivos.
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

VPS_HOST="root@187.77.37.72"
VPS_DIR="/root/fralib"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==========================================="
echo "  Auditoria VPS vs LOCAL"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

cd "$LOCAL_DIR"

# 1. Estado do git local
echo ""
echo -e "${YELLOW}[1/6] Estado LOCAL${NC}"
echo "  Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo "  Commit: $(git rev-parse --short HEAD 2>/dev/null)"
echo "  Msg:    $(git log -1 --format=%s 2>/dev/null)"
echo "  Modified: $(git status --short 2>/dev/null | wc -l) arquivos"

# 2. Estado do git VPS
echo ""
echo -e "${YELLOW}[2/6] Estado VPS${NC}"
ssh $VPS_HOST "cd $VPS_DIR && git log --oneline -3" 2>/dev/null | while read line; do
    echo "  $line"
done

# 3. Comparação de commits
echo ""
echo -e "${YELLOW}[3/6] Comparação de commits${NC}"
LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null)
VPS_HASH=$(ssh $VPS_HOST "cd $VPS_DIR && git rev-parse HEAD" 2>/dev/null)
echo "  Local: $LOCAL_HASH"
echo "  VPS:   $VPS_HASH"

if [ "$LOCAL_HASH" = "$VPS_HASH" ]; then
    echo -e "  ${GREEN}✓ Mesma versão${NC}"
else
    echo -e "  ${RED}⚠️  VERSÕES DIFERENTES${NC}"
    # Commits na VPS que não estão no local
    UNIQUE_VPS=$(ssh $VPS_HOST "cd $VPS_DIR && git log $LOCAL_HASH..HEAD --oneline 2>/dev/null" 2>/dev/null)
    if [ -n "$UNIQUE_VPS" ]; then
        echo ""
        echo "  Commits na VPS que não estão no LOCAL:"
        echo "$UNIQUE_VPS" | while read line; do
            echo "    $line"
        done
    fi
    # Commits no local que não estão na VPS
    UNIQUE_LOCAL=$(git log $VPS_HASH..HEAD --oneline 2>/dev/null)
    if [ -n "$UNIQUE_LOCAL" ]; then
        echo ""
        echo "  Commits no LOCAL que não estão na VPS:"
        echo "$UNIQUE_LOCAL" | while read line; do
            echo "    $line"
        done
    fi
fi

# 4. Arquivos modificados não commitados
echo ""
echo -e "${YELLOW}[4/6] Arquivos modificados LOCAL${NC}"
git status --short 2>/dev/null | head -10

echo ""
echo -e "${YELLOW}[4b/6] Arquivos modificados VPS${NC}"
ssh $VPS_HOST "cd $VPS_DIR && git status --short 2>/dev/null" | head -10

# 5. Comparar tamanhos de arquivos chave (imports/monolitos)
echo ""
echo -e "${YELLOW}[5/6] Comparação de arquivos críticos${NC}"
FILES=(
    "backend/agents/llm_direct.py"
    "backend/services/vite_react_renderer.py"
    "backend/agents/html_quality_gate.py"
    "backend/services/builder_worker.py"
    "backend/endpoints/pipeline_orchestrator_service.py"
    "backend/services/vite_prompts.py"
    "backend/services/pipeline_flow_config.py"
)
echo "  Arquivo                          | LOCAL    | VPS"
echo "  ---------------------------------|----------|----------"
for f in "${FILES[@]}"; do
    LOCAL_SIZE=$(wc -l < "$f" 2>/dev/null || echo "N/A")
    VPS_SIZE=$(ssh $VPS_HOST "wc -l < $VPS_DIR/$f" 2>/dev/null || echo "N/A")
    if [ "$LOCAL_SIZE" = "$VPS_SIZE" ]; then
        STATUS="${GREEN}✓${NC}"
    else
        STATUS="${RED}✗${NC}"
    fi
    printf "  %-32s | %-8s | %-8s %s\n" "$f" "$LOCAL_SIZE" "$VPS_SIZE" "$STATUS"
done

# 6. Verificar serviços VPS
echo ""
echo -e "${YELLOW}[6/6] Status serviços VPS${NC}"
ssh $VPS_HOST "pm2 jlist 2>/dev/null | python3 -c '
import sys, json
try:
    procs = json.load(sys.stdin)
    for p in procs:
        name = p.get(\"name\", \"?\")
        status = p.get(\"pm2_env\", {}).get(\"status\", \"?\")
        restarts = p.get(\"pm2_env\", {}).get(\"restart_count\", 0)
        uptime = p.get(\"pm2_env\", {}).get(\"pm2_uptime\", 0)
        print(f\"  {name:30} | {status:10} | restarts: {restarts:3} | uptime: {uptime}s\")
except: print(\"  Não conseguiu ler PM2\")
'" 2>/dev/null

echo ""
echo "==========================================="
echo "  FIM DA AUDITORIA"
echo "==========================================="
