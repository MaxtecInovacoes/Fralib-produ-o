#!/usr/bin/env bash
# Cron job para auto-post em TODOS os projetos de redes sociais (FraLib Multi-Tenant)
# Varre /root/fralib/projects/*/ e executa auto_post_social.py para cada projeto ativo.
#
# Sugestão de agendamento (horário de Brasília):
#   30 10 * * *  /bin/bash /root/fralib/scripts/cron_social_post.sh
#   -> roda todos os dias às 10:30, depois do cron do blog (08:00)

set -e

# Paths
FRALIB_DIR="/opt/fralib"
[ -d "/root/fralib" ] && FRALIB_DIR="/root/fralib"
PROJECTS_DIR="$FRALIB_DIR/projects"
SCRIPTS_DIR="$FRALIB_DIR/scripts"

LOG_DIR="/var/log/fralib"
LOG_FILE="$LOG_DIR/social_post_cron.log"
mkdir -p "$LOG_DIR"

cd "$FRALIB_DIR" || exit 1

# Venv
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

echo "=== Social-post cron started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# Contador de projetos
PROJECT_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0

# Varre todos os projetos com config.env
for project_dir in "$PROJECTS_DIR"/*/; do
    PROJECT_SLUG=$(basename "$project_dir")

    # Pula se não tem config.env
    if [ ! -f "$project_dir/config.env" ]; then
        continue
    fi

    # Pula se is_active=false (opcional, se definido)
    if grep -q "^IS_ACTIVE=false" "$project_dir/config.env" 2>/dev/null; then
        echo "  [-] Projeto inativo: $PROJECT_SLUG" >> "$LOG_FILE"
        continue
    fi

    echo "=== Processando projeto: $PROJECT_SLUG ===" >> "$LOG_FILE"

    PROJECT_COUNT=$((PROJECT_COUNT + 1))

    # Executa auto-post para este projeto específico
    if python3 "$SCRIPTS_DIR/auto_post_social.py" --project "$PROJECT_SLUG" >> "$project_dir/logs/social-post.log" 2>&1; then
        echo "  [OK] $PROJECT_SLUG" >> "$LOG_FILE"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  [FALHA] $PROJECT_SLUG" >> "$LOG_FILE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

# Resumo
echo "=== Social-post cron finished at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
echo "=== RESUMO: $PROJECT_COUNT projetos, $SUCCESS_COUNT OK, $FAIL_COUNT falhas ===" >> "$LOG_FILE"

# Log size guard (mantém últimos ~10 MB)
find "$LOG_DIR" -name "social-post.log" -size +10M -exec truncate -s 0 {} \; 2>/dev/null || true

exit 0