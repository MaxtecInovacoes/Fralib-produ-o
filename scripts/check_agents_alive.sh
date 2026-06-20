#!/bin/bash
# =============================================================================
# check_agents_alive.sh v2 - Detecta código morto com lógica melhor
# =============================================================================
# Considera uso via string (não só import direto)
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

cd "$(dirname "$0")/.." || exit 1

echo "==========================================="
echo "  Agentes Vivos vs Mortos (v2)"
echo "==========================================="

MORTO=0
USADO=0
LISTA_MORTOS=""

for f in backend/agents/*.py; do
    [ -f "$f" ] || continue
    filename=$(basename "$f" .py)
    [ "$filename" == "__init__" ] && continue

    # Procura QUALQUER referência real (import, uso, string)
    # Excluindo o próprio arquivo
    REFS=$(grep -rE "(${filename}|backend\.agents\.${filename}|agents\.${filename})" backend --include="*.py" 2>/dev/null \
        | grep -v "^${f}:" \
        | grep -v "test_" \
        | wc -l)

    if [ "$REFS" -eq 0 ]; then
        LINES=$(wc -l < "$f")
        echo -e "${RED}☠️  MORTO${NC} $f ($LINES linhas)"
        LISTA_MORTOS="$LISTA_MORTOS $filename"
        MORTO=$((MORTO+1))
    else
        echo -e "${GREEN}✓${NC} $f ($REFS refs)"
        USADO=$((USADO+1))
    fi
done

echo ""
echo "==========================================="
echo -e "  ${RED}Mortos: $MORTO${NC} | ${GREEN}Vivos: $USADO${NC}"
echo "==========================================="

if [ "$MORTO" -gt 0 ]; then
    echo ""
    echo "Arquivos realmente mortos (não usados em lugar nenhum):"
    for m in $LISTA_MORTOS; do
        echo "  - backend/agents/$m.py"
    done
fi
