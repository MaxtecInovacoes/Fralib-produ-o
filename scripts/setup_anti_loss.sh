#!/bin/bash
# =============================================================================
# setup_anti_loss.sh - Configura sistema anti-perda completo (one-time)
# =============================================================================
# Roda uma vez apos clonar o repo. Configura:
#   - Hook post-commit (auto-push VPS + GitHub)
#   - Pre-commit secret scanning
#   - Aliases git uteis
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(cd "$(dirname "$0")/.." && pwd)"

echo "==========================================="
echo "  SETUP ANTI-PERDA - FraLib"
echo "==========================================="
echo ""

# 1. Verificar se esta em um repo git
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}ERRO: nao esta em um repo git${NC}"
    exit 1
fi

# 2. Instalar hook post-commit
echo "[1/4] Instalando hook post-commit (auto-push)..."
if [ -f "scripts/auto_checkpoint.sh" ]; then
    cp scripts/auto_checkpoint.sh .git/hooks/post-commit
    chmod +x .git/hooks/post-commit
    echo -e "  ${GREEN}[OK]${NC}"
else
    echo -e "  ${YELLOW}[SKIP] scripts/auto_checkpoint.sh nao encontrado${NC}"
fi

# 3. Instalar pre-commit (secret scanning)
echo "[2/4] Instalando pre-commit (secret scan)..."
if [ -f "scripts/scan_secrets.sh" ]; then
    HOOK_PATH=".git/hooks/pre-commit"
    cat > "$HOOK_PATH" <<'EOF'
#!/bin/bash
bash "$(git rev-parse --show-toplevel)/scripts/scan_secrets.sh" || {
    echo "BLOQUEADO: secrets detectados - corrija antes de commitar"
    exit 1
}
EOF
    chmod +x "$HOOK_PATH"
    echo -e "  ${GREEN}[OK]${NC}"
else
    echo -e "  ${YELLOW}[SKIP] scripts/scan_secrets.sh nao encontrado${NC}"
fi

# 4. Aliases git uteis
echo "[3/4] Configurando aliases git..."
git config alias.s "status --short"
git config alias.c "checkout"
git config alias.lg "log --oneline --graph -20"
git config alias.unstage "reset HEAD --"
git config alias.last "log -1 --stat"
git config alias.amend "commit --amend --no-edit"
git config alias.wip "commit -am 'wip: work in progress'"
git config alias.save "!bash scripts/auto_checkpoint.sh"
echo -e "  ${GREEN}[OK]${NC}"
echo "  Aliases disponiveis: git s, git c, git lg, git save, etc"

# 5. Verificar remotes
echo "[4/4] Verificando remotes..."
REMOTES=$(git remote -v | wc -l)
if [ "$REMOTES" -ge "2" ]; then
    echo -e "  ${GREEN}[OK] $REMOTES remotes configurados${NC}"
    git remote -v
else
    echo -e "  ${YELLOW}[WARN] Apenas $REMOTES remote(s)${NC}"
    echo "  Recomendado ter: origin (VPS) + github (backup)"
fi

echo ""
echo "==========================================="
echo -e "${GREEN}SETUP COMPLETO!${NC}"
echo "==========================================="
echo ""
echo "Comandos uteis:"
echo "  git save          # checkpoint manual"
echo "  git s             # status curto"
echo "  git lg            # log visual"
echo ""
echo "A partir de agora, todo commit vai para:"
echo "  - VPS (origin)"
echo "  - GitHub (github)"