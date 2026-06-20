#!/bin/bash
# =============================================================================
# check_uncommitted.sh - Bloqueia se houver modificações não commitadas
# =============================================================================
# Uso: ./scripts/check_uncommitted.sh [--force]
# Retorna 0 se working tree está limpo, 1 caso contrário.
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FORCE=false
if [ "$1" = "--force" ]; then
    FORCE=true
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

# Verificar se é repo git
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}ERRO: não está em um repositório Git${NC}"
    exit 2
fi

# Pegar modificações
MODIFIED=$(git status --short 2>/dev/null)
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)

TOTAL=0
if [ -n "$MODIFIED" ]; then
    TOTAL=$(echo "$MODIFIED" | wc -l)
fi
if [ -n "$UNTRACKED" ]; then
    TOTAL=$((TOTAL + $(echo "$UNTRACKED" | wc -l)))
fi

if [ "$TOTAL" = "0" ]; then
    echo -e "${GREEN}✅ Working tree limpo (0 modificações)${NC}"
    exit 0
fi

echo -e "${YELLOW}⚠️  ${TOTAL} arquivo(s) não commitado(s):${NC}"
echo ""
if [ -n "$MODIFIED" ]; then
    echo "  Modificados:"
    echo "$MODIFIED" | while read -r line; do
        echo "    $line"
    done
fi
if [ -n "$UNTRACKED" ]; then
    echo "  Untracked:"
    echo "$UNTRACKED" | while read -r line; do
        echo "    $line"
    done
fi
echo ""

if [ "$FORCE" = true ]; then
    echo -e "${YELLOW}--force: continuando apesar de modificações${NC}"
    exit 0
fi

echo -e "${RED}❌ BLOQUEADO: faça commit ou stash antes de continuar${NC}"
echo ""
echo "Comandos sugeridos:"
echo "  git add -A && git commit -m '...'    # commitar tudo"
echo "  git stash                              # guardar temporariamente"
echo "  ./scripts/check_uncommitted.sh --force # ignorar aviso"
echo ""

exit 1
