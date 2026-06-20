#!/bin/bash
# scan_secrets.sh - Fast secret detection for git commits
# Usage: Run as pre-commit hook or manually

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(git rev-parse --show-toplevel 2>/dev/null)"
[ $? -ne 0 ] && echo "Error: Not a git repository" && exit 1

which rg >/dev/null 2>&1
[ $? -ne 0 ] && echo "Error: ripgrep (rg) is required" && exit 1

echo -e "${YELLOW}Scanning for secrets...${NC}"

# Get staged files
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
if [ -n "$STAGED" ]; then
    echo "Scanning staged files..."
    SECRETS=$(echo "$STAGED" | rg -n \
        -w 'sk_live' \
        -w 'sk_test' \
        -w 'pk_live' \
        -w 'pk_test' \
        -e 'AKIA[A-Z0-9]{16}' \
        -e 'sk-[A-Za-z0-9]{30,}' \
        -e 'sk-ant-[A-Za-z0-9]{30,}' \
        -e 'AIza[A-Za-z0-9]{30,}' \
        -e 'ghp_[A-Za-z0-9]{36}' \
        -e 'gho_[A-Za-z0-9]{36}' \
        -e 'ghu_[A-Za-z0-9]{36}' \
        -e 'ghs_[A-Za-z0-9]{36}' \
        -e 'ghr_[A-Za-z0-9]{36}' \
        -e 'xox[baprs]-[A-Za-z0-9-]{30,}' \
        -e '-----BEGIN.*PRIVATE KEY-----' \
        2>/dev/null | head -30)

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
else
    echo "Scanning tracked files..."

    # Scan for API keys and tokens (exclude shell scripts and binary files)
    SECRETS=$(rg -n \
        -w 'sk_live' \
        -w 'sk_test' \
        -w 'pk_live' \
        -w 'pk_test' \
        -e 'AKIA[A-Z0-9]{16}' \
        -e 'sk-[A-Za-z0-9]{30,}' \
        -e 'sk-ant-[A-Za-z0-9]{30,}' \
        -e 'AIza[A-Za-z0-9]{30,}' \
        -e 'ghp_[A-Za-z0-9]{36}' \
        -e 'gho_[A-Za-z0-9]{36}' \
        -e 'ghu_[A-Za-z0-9]{36}' \
        -e 'ghs_[A-Za-z0-9]{36}' \
        -e 'ghr_[A-Za-z0-9]{36}' \
        -e 'xox[baprs]-[A-Za-z0-9-]{30,}' \
        --glob '!*.(png|jpg|jpeg|gif|webp|ico|svg|pdf|zip|tar|gz|tgz|mp4|mp3|woff|woff2|ttf|eot|lock|log|pyc|sh)' \
        --glob '!node_modules' \
        --glob '!venv' \
        --glob '!__pycache__' \
        --glob '!.git' \
        --glob '!backend/agents/jina_cache' \
        --glob '!backend/agents/unsplash_cache' \
        --glob '!backend/memory' \
        --glob '!backend/docs' \
        . 2>/dev/null | head -30)

    # Scan for private keys (exclude shell scripts that may contain the pattern as docs)
    PRIVATE_KEYS=$(rg -n \
        -e '-----BEGIN.*PRIVATE KEY-----' \
        --glob '!*.sh' \
        --glob '!*.bash' \
        --glob '!*.py' \
        --glob '!*.(png|jpg|jpeg|gif|webp|ico|svg|pdf|zip|tar|gz|tgz|mp4|mp3|woff|woff2|ttf|eot|lock|log)' \
        --glob '!node_modules' \
        --glob '!venv' \
        --glob '!__pycache__' \
        --glob '!.git' \
        . 2>/dev/null | head -30)

    if [ -n "$PRIVATE_KEYS" ]; then
        SECRETS="${SECRETS}${NL}${PRIVATE_KEYS}"
    fi

    BLOCKED=0
fi

# Report and exit
if [ -n "$SECRETS" ]; then
    echo -e "${RED}[SECRET] Patterns found:${NC}"
    echo "$SECRETS"
    echo ""
    echo -e "${RED}COMMIT BLOCKED - SECRETS DETECTED${NC}"
    exit 1
fi

if [ "$BLOCKED" -eq 1 ]; then
    echo ""
    echo -e "${RED}COMMIT BLOCKED - SECRET FILES${NC}"
    exit 1
fi

echo -e "${GREEN}No secrets detected. Safe to commit.${NC}"
exit 0
