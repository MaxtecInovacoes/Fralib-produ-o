#!/bin/bash
# =============================================================================
# fix_imports.sh - Corrige imports quebrados automaticamente
# =============================================================================
# Uso: bash scripts/fix_imports.sh [--dry-run]
# =============================================================================

set +e

cd "$(dirname "$0")/.." || exit 1

DRY_RUN=false
[ "$1" == "--dry-run" ] && DRY_RUN=true

run_sed() {
    local pattern="$1"
    local files="$2"
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $pattern"
    else
        eval "sed -i '$pattern' $files"
        echo "✓ $pattern"
    fi
}

echo "==========================================="
echo "  Fix Imports - FraLib"
echo "  Mode: $([ "$DRY_RUN" = true ] && echo DRY-RUN || echo APPLY)"
echo "==========================================="

# 1. from core. → from backend.core.
echo ""
echo "[1/11] from core. → from backend.core."
for f in $(grep -rl "^from core\." backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from core\\./from backend.core./g" "$f"
done

# 2. from services. → from backend.services.
echo ""
echo "[2/11] from services. → from backend.services."
for f in $(grep -rl "^from services\." backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from services\\./from backend.services./g" "$f"
done

# 3. from agents. → from backend.agents.
echo ""
echo "[3/11] from agents. → from backend.agents."
for f in $(grep -rl "^from agents\." backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from agents\\./from backend.agents./g" "$f"
done

# 4. from endpoints. → from backend.endpoints.
echo ""
echo "[4/11] from endpoints. → from backend.endpoints."
for f in $(grep -rl "^from endpoints\." backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from endpoints\\./from backend.endpoints./g" "$f"
done

# 5. from utils. → from backend.utils.
echo ""
echo "[5/11] from utils. → from backend.utils."
for f in $(grep -rl "^from utils\." backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from utils\\./from backend.utils./g" "$f"
done

# 6. from database → from backend.core.database
echo ""
echo "[6/11] from database → from backend.core.database"
for f in $(grep -rl "^from database " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from database /from backend.core.database /g" "$f"
done

# 7. from auth → from backend.core.auth
echo ""
echo "[7/11] from auth → from backend.core.auth"
for f in $(grep -rl "^from auth " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from auth /from backend.core.auth /g" "$f"
done

# 8. from jwt_config → from backend.core.jwt_config
echo ""
echo "[8/11] from jwt_config → from backend.core.jwt_config"
for f in $(grep -rl "^from jwt_config " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from jwt_config /from backend.core.jwt_config /g" "$f"
done

# 9. from whatsapp_listener → from backend.whatsapp_listener
echo ""
echo "[9/11] from whatsapp_listener → from backend.whatsapp_listener"
for f in $(grep -rl "^from whatsapp_listener " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from whatsapp_listener /from backend.whatsapp_listener /g" "$f"
done

# 10. from sse_endpoints → from backend.endpoints.sse_endpoints
echo ""
echo "[10/11] from sse_endpoints → from backend.endpoints.sse_endpoints"
for f in $(grep -rl "^from sse_endpoints " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from sse_endpoints /from backend.endpoints.sse_endpoints /g" "$f"
done

# 11. from config → from backend.config
echo ""
echo "[11/11] from config → from backend.config"
for f in $(grep -rl "^from config " backend --include="*.py" 2>/dev/null); do
    run_sed "s/^from config /from backend.config /g" "$f"
done

echo ""
echo "==========================================="
REMAINING=$(grep -rE "^from (core|services|agents|endpoints|utils|database |auth |jwt_config |whatsapp_listener |sse_endpoints |config )" backend --include="*.py" 2>/dev/null | grep -v "backend\." | wc -l)
echo "  Imports quebrados restantes: $REMAINING"
echo "==========================================="
