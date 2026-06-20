#!/bin/bash
# =============================================================================
# auto_checkpoint.sh - Auto-commit/push quando Claude Code encerra
# =============================================================================
# Chamado pelo hook SessionEnd de Claude Code.
# Garante que NADA se perde ao fechar uma sessao.
#
# Comportamento:
#   1. Detecta modificacoes
#   2. Faz commit descritivo com timestamp
#   3. Push automatico para origin (VPS) E github (nuvem)
#   4. Reporta o que foi feito
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /c/fralib 2>/dev/null || cd "$(dirname "$0")/.."

echo "==========================================="
echo "  AUTO-CHECKPOINT (SessionEnd)"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="

# Verificar se eh um repo git
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}Nao eh um repo git. Saindo.${NC}"
    exit 0
fi

# Contar modificacoes
MODIFIED=$(git status --short 2>/dev/null | wc -l)
if [ "$MODIFIED" = "0" ]; then
    echo -e "${GREEN}Nada para commitar. Working tree limpo.${NC}"
    exit 0
fi

echo -e "${YELLOW}${MODIFIED} arquivo(s) modificado(s)${NC}"
git status --short 2>&1 | head -10
echo ""

# Stage tudo
git add -A 2>&1 >/dev/null

# Mensagem descritiva
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="checkpoint: auto-save ${TIMESTAMP}

Auto-commit disparado pelo hook SessionEnd de Claude Code.
Garante que modificacoes nao se percam entre sessoes.

Arquivos modificados: ${MODIFIED}
Working tree sera limpo apos este commit."

# Commit
echo "[1/3] Fazendo commit..."
git commit -m "$COMMIT_MSG" 2>&1 | tail -3
echo ""

# Push para VPS
echo "[2/3] Push para VPS (origin)..."
if git push origin master 2>&1 | tail -3; then
    echo -e "  ${GREEN}[OK] VPS atualizado${NC}"
else
    echo -e "  ${YELLOW}[WARN] VPS push falhou (sem rede?)${NC}"
fi
echo ""

# Push para GitHub
echo "[3/3] Push para GitHub (nuvem backup)..."
if git push github master 2>&1 | tail -3; then
    echo -e "  ${GREEN}[OK] GitHub atualizado${NC}"
else
    echo -e "  ${YELLOW}[WARN] GitHub push falhou${NC}"
fi

echo ""
echo "==========================================="
echo -e "${GREEN}CHECKPOINT COMPLETO${NC}"
echo "==========================================="