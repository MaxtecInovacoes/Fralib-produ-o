#!/usr/bin/env bash
# =============================================================================
# deploy_canary.sh - Canário pós-deploy (valida endpoints críticos)
# =============================================================================
# Uso: ./scripts/deploy_canary.sh [BASE_URL] [--verbose]
# Default BASE_URL: http://localhost:3000
# Retorna 0 se todos endpoints OK, 1 caso contrário.
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost:3000"
VERBOSE=false

for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=true ;;
        http*) BASE_URL="$arg" ;;
    esac
done

# Check curl
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${RED}ERRO: curl não encontrado${NC}"
    exit 2
fi

ENDPOINTS=(
    "/api/health"
    "/login"
    "/admin.html"
    "/plans"
    "/api/version"
)

CURL_OPTS="-s -o /dev/null -w %{http_code} --max-time 30"
if [ "$VERBOSE" = true ]; then
    CURL_OPTS="-s -w '\n%{http_code} (final URL: %{url_effective})' --max-time 30 -L"
fi

FAIL=0
PASS=0

echo "==========================================="
echo "  Canário pós-deploy"
echo "  Base: $BASE_URL"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

for ep in "${ENDPOINTS[@]}"; do
    URL="$BASE_URL$ep"
    CODE=$(eval "curl $CURL_OPTS '$URL'" 2>/dev/null | tail -1)

    if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
        echo -e "  ${GREEN}OK${NC}   [$CODE]  $ep"
        PASS=$((PASS+1))
    elif [ "$CODE" = "500" ]; then
        echo -e "  ${RED}FAIL${NC} [$CODE]  $ep  <-- ERRO INTERNO!"
        FAIL=$((FAIL+1))
    else
        echo -e "  ${YELLOW}WARN${NC} [$CODE]  $ep"
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "==========================================="
echo -e "  Resultado: ${GREEN}$PASS OK${NC} / ${RED}$FAIL FAIL${NC}"
echo "==========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
