#!/usr/bin/env bash
# =============================================================================
# check_public_pages.sh - Valida páginas públicas (llms.txt, termos, privacidade)
# =============================================================================
# Uso: ./scripts/check_public_pages.sh [BASE_URL]
# Default BASE_URL: http://localhost:8000
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

BASE_URL="${PUBLIC_PAGES_URL:-http://localhost:8000}"

PAGES=(
    "/llms.txt"
    "/termos"
    "/privacidade"
)

FAIL=0
PASS=0

echo "==========================================="
echo "  Páginas públicas"
echo "  Base: $BASE_URL"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

for page in "${PAGES[@]}"; do
    URL="$BASE_URL$page"
    RESP=$(curl -s -w "\n%{http_code}" --max-time 15 "$URL" 2>/dev/null)
    CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | sed '$d')
    SIZE=${#BODY}

    if [ "$CODE" = "200" ] && [ "$SIZE" -gt 100 ]; then
        echo -e "  ${GREEN}OK${NC}   [$CODE]  $page  ($SIZE chars)"
        PASS=$((PASS+1))
    else
        echo -e "  ${RED}FAIL${NC} [$CODE]  $page  ($SIZE chars)"
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