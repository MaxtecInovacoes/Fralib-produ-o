#!/bin/bash
# scan_secrets.sh - Fast secret detection for git commits
# Uso: pre-commit hook ou manual (bash scripts/scan_secrets.sh)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1-5;33m'
NC='\033[0m'

cd "$(git rev-parse --show-toplevel 2>/dev/null)"
[ $? -ne 0 ] && echo "Error: Not a git repository" && exit 1

echo -e "${YELLOW}Scanning for secrets...${NC}"

# Patterns that indicate a real secret (not placeholder)
# Patterns that indicate a REAL secret (not a placeholder ending with ...)
# - Real tokens have at least 30+ alnum chars after the prefix
# - Placeholders usually end with '...' or are examples like 'sk-ant-api-key-aqui'
PATTERNS='(sk_live_[A-Za-z0-9]{30,}|sk_test_[A-Za-z0-9]{30,}|pk_live_[A-Za-z0-9]{30,}|pk_test_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9]{40,}|sk-ant-[A-Za-z0-9]{40,}|AIza[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|ghu_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|ghr_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{30,}|APP_USR-[A-Za-z0-9-]{40,}|TEST-[A-Za-z0-9-]{40,}|whsec_[A-Za-z0-9]{30,}|-----BEGIN.*PRIVATE KEY-----|MERCADOPAGO_ACCESS_TOKEN=APP_USR-[A-Za-z0-9]{30,}|MERCADOPAGO_WEBHOOK_SECRET=[^[:space:]\$\{\}]+|[^a-z_]sk_live_[a-zA-Z0-9]{30,}|[^a-z_]sk_test_[a-zA-Z0-9]{30,})'

STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
SECRETS=""

if [ -n "$STAGED" ]; then
    echo "Scanning staged files..."
    # Concat content of all staged files and search with grep
    for f in $STAGED; do
        [ -f "$f" ] || continue
        # Excluir o proprio scanner e o install hook (contem patterns como string)
        bn=$(basename "$f")
        case "$bn" in
            scan_secrets.sh|install_precommit_hook.sh) continue ;;
        esac
        hits=$(cat "$f" 2>/dev/null | grep -nE "$PATTERNS" 2>/dev/null)
        if [ -n "$hits" ]; then
            SECRETS="${SECRETS}${f}:${hits}\n"
        fi
    done
else
    echo "Scanning tracked files..."
    # Scan repo with grep (excluindo binarios e dotenv reais)
    hits=$(grep -rnE "$PATTERNS" \
        --include='*.py' --include='*.js' --include='*.ts' --include='*.tsx' \
        --include='*.jsx' --include='*.md' --include='*.txt' --include='*.json' \
        --include='*.yml' --include='*.yaml' --include='*.toml' --include='*.cfg' \
        --include='*.ini' --include='*.sh' --include='*.html' --include='*.css' \
        --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.venv \
        --exclude-dir=__pycache__ --exclude-dir=.git --exclude-dir=htmlcov \
        --exclude-dir=backend/agents/jina_cache --exclude-dir=backend/agents/unsplash_cache \
        --exclude-dir=backend/memory --exclude-dir=backend/docs \
        --exclude-dir=.claude --exclude-dir=worktrees \
        --exclude-dir=docs \
        --exclude='scan_secrets.sh' --exclude='install_precommit_hook.sh' \
        . 2>/dev/null | grep -vE '=$|=(\.\.\.|CHANGE_ME|KEY_HERE|API_KEY|sua_chave|aqui|exemplo|placeholder)' | head -50)
    [ -n "$hits" ] && SECRETS=$hits
fi

# Block .env files (sem .env.example)
BLOCKED=0
for f in $STAGED; do
    bn=$(basename "$f")
    case "$bn" in
        .env|.env.local|.env.production|.env.backup|.env.test|.env.production.local)
            echo -e "${RED}[BLOCKED] Secret file: $f${NC}"
            BLOCKED=1
            ;;
    esac
    case "$f" in
        *.pem|*.key|*.pkcs8)
            echo -e "${RED}[BLOCKED] Key file: $f${NC}"
            BLOCKED=1
            ;;
    esac
done

if [ -n "$SECRETS" ]; then
    echo -e "${RED}[SECRET] Patterns found:${NC}"
    echo -e "$SECRETS"
    echo ""
    echo -e "${RED}COMMIT BLOCKED - SECRETS DETECTED${NC}"
    echo "Para ignorar (apenas emergências): git commit --no-verify"
    exit 1
fi

if [ "$BLOCKED" -eq 1 ]; then
    echo ""
    echo -e "${RED}COMMIT BLOCKED - SECRET FILES${NC}"
    exit 1
fi

echo -e "${GREEN}No secrets detected. Safe to commit.${NC}"
exit 0