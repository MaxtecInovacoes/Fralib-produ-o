#!/bin/bash
# install_precommit_hook.sh - Install scan_secrets.sh as pre-commit hook
# Run this script from the repo root to install the hook

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"

echo "Installing secret scanner pre-commit hook..."

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Create pre-commit hook
cat > "$HOOK_DIR/pre-commit" << 'HOOK_EOF'
#!/bin/bash
# Pre-commit hook - Block commits containing secrets

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Change to repo root
cd "$(git rev-parse --show-toplevel)"

# Detect if ripgrep is available
if command -v rg &>/dev/null; then
    GREP_CMD="rg"
else
    GREP_CMD="grep"
fi

# Files to always block
BLOCKED_FILES=(".env" ".env.local" ".env.production" ".env.backup" ".env.test")

# Blocked file extensions
BLOCKED_EXTENSIONS=(".pem" ".key" ".pkcs8")

# Secret patterns
SECRET_PATTERNS=(
    "sk_live_[A-Za-z0-9]{20,}"
    "sk_test_[A-Za-z0-9]{20,}"
    "pk_live_[A-Za-z0-9]{20,}"
    "pk_test_[A-Za-z0-9]{20,}"
    "AKIA[0-9A-Z]{16}"
    "sk-[A-Za-z0-9_-]{20,}"
    "sk-ant-[A-Za-z0-9_-]{20,}"
    "AIza[0-9A-Za-z_-]{20,}"
    "ghp_[0-9A-Za-z]{20,}"
    "gho_[0-9A-Za-z]{20,}"
    "ghu_[0-9A-Za-z]{20,}"
    "ghs_[0-9A-Za-z]{20,}"
    "ghr_[0-9A-Za-z]{20,}"
    "xox[baprs]-[0-9A-Za-z-]{10,}"
    "-----BEGIN.*PRIVATE KEY-----"
    "(postgres|mysql|mssql|mongodb)://[^:]+:[^@]+@"
    "JWT_SECRET_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{24,}"
    "SECRET_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{24,}"
)

# Skip patterns (allow in specific files)
ALLOWED_PATTERNS=(
    "sk_live_.*placeholder"
    "pk_live_.*placeholder"
    "ghp_.*placeholder"
    "AKIA.*EXAMPLE"
    "your_.*key"
    "test_.*key"
)

# Skip these extensions
SKIP_EXTENSIONS=(".png" ".jpg" ".jpeg" ".gif" ".webp" ".svg" ".pdf" ".zip" ".tar" ".gz" ".lock")

# Directories to skip
SKIP_DIRS=(".git" "node_modules" "venv" "__pycache__" ".pytest_cache" "htmlcov" ".ruff_cache")

FOUND_VIOLATIONS=0

should_skip() {
    local file="$1"
    local dir=$(dirname "$file")

    # Check extension
    for ext in "${SKIP_EXTENSIONS[@]}"; do
        [[ "$file" == *"$ext" ]] && return 0
    done

    # Check directory
    for skip_dir in "${SKIP_DIRS[@]}"; do
        [[ "$dir" == *"/$skip_dir"* ]] && return 0
    done

    return 1
}

is_allowed() {
    local line="$1"
    for pattern in "${ALLOWED_PATTERNS[@]}"; do
        [[ "$line" =~ $pattern ]] && return 0
    done
    return 1
}

echo -e "${YELLOW}Scanning staged files for secrets...${NC}"

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

BLOCKED_FOUND=0

# Check for blocked files
for blocked in "${BLOCKED_FILES[@]}"; do
    for file in $STAGED_FILES; do
        if [[ "$(basename "$file")" == "$blocked" ]]; then
            echo -e "${RED}[BLOCKED] Secret file detected: $file${NC}"
            BLOCKED_FOUND=1
        fi
    done
done

# Check for blocked extensions
for ext in "${BLOCKED_EXTENSIONS[@]}"; do
    for file in $STAGED_FILES; do
        if [[ "$file" == *"$ext" ]]; then
            echo -e "${RED}[BLOCKED] Secret file detected: $file${NC}"
            BLOCKED_FOUND=1
        fi
    done
done

# Scan for secret patterns
for file in $STAGED_FILES; do
    should_skip "$file" && continue
    [[ ! -f "$file" ]] && continue

    # Get staged content (works even if file is new)
    STAGED_CONTENT=$(git show ":$file" 2>/dev/null || cat "$file")

    for pattern in "${SECRET_PATTERNS[@]}"; do
        if [[ "$GREP_CMD" == "rg" ]]; then
            MATCHES=$(echo "$STAGED_CONTENT" | rg -n -i "$pattern" || true)
        else
            MATCHES=$(echo "$STAGED_CONTENT" | grep -n -i -E "$pattern" || true)
        fi

        if [[ -n "$MATCHES" ]]; then
            # Check if it's an allowed placeholder
            ALLOWED=0
            while IFS= read -r line; do
                is_allowed "$line" && ALLOWED=1
            done <<< "$MATCHES"

            if [[ $ALLOWED -eq 0 ]]; then
                echo -e "${RED}[SECRET] Pattern detected in $file:${NC}"
                echo "$MATCHES" | head -2
                echo ""
                FOUND_VIOLATIONS=1
            fi
        fi
    done
done

if [[ $BLOCKED_FOUND -eq 1 ]] || [[ $FOUND_VIOLATIONS -eq 1 ]]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}   COMMIT BLOCKED - SECRETS DETECTED   ${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Remove secrets or use placeholders before committing."
    echo "Rotate any exposed credentials immediately."
    exit 1
fi

echo -e "${GREEN}No secrets detected. Commit is safe.${NC}"
exit 0
HOOK_EOF

chmod +x "$HOOK_DIR/pre-commit"

echo ""
echo -e "${GREEN}Pre-commit hook installed successfully!${NC}"
echo ""
echo "The hook will now scan staged files for:"
echo "  - .env files and other secret files"
echo "  - Stripe keys (sk_live, pk_live)"
echo "  - AWS keys (AKIA)"
echo "  - OpenAI keys (sk-, sk-ant-)"
echo "  - GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_)"
echo "  - Slack tokens (xoxb-, xoxa-, etc.)"
echo "  - Private keys (.pem, .key)"
echo "  - Database connection strings with passwords"
echo ""
