#!/usr/bin/env bash
# Pipeline completo: BLOG + IMAGENS + SEO + PUBLICAÇÃO
# Roda todo dia às 8h (horário de Brasília)
# Cron: 0 8 * * * /bin/bash /root/fralib/scripts/pipeline_completo.sh

set -e

FRALIB_DIR="/root/fralib"
SCRIPTS_DIR="$FRALIB_DIR/scripts"
LOG_FILE="/var/log/fralib/pipeline.log"
mkdir -p $(dirname "$LOG_FILE")

cd "$FRALIB_DIR" || exit 1

# Ativa venv
[ -f ".venv/bin/activate" ] && source .venv/bin/activate

# Carrega .env
[ -f ".env" ] && set -a && source .env && set +a

echo "=== PIPELINE START $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# 1. Buscar tendências
echo "[1/5] Buscando tendências..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/buscar_tendencias.py" >> "$LOG_FILE" 2>&1

# 2. Gerar 3 posts com LLM
echo "[2/5] Gerando posts..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/gerar_post.py" >> "$LOG_FILE" 2>&1

# 3. Gerar 3 imagens (uma por post)
echo "[3/5] Gerando imagens..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/gerar_imagens.py" >> "$LOG_FILE" 2>&1

# 4. Aplicar SEO master
echo "[4/5] Aplicando SEO..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/seo_master.py" >> "$LOG_FILE" 2>&1

# 5. Publicar (index + sitemap + RSS)
echo "[5/5] Publicando..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/publicar.py" >> "$LOG_FILE" 2>&1

# 6. Git commit + push
cd "$FRALIB_DIR"
git add frontend/blog/ 2>/dev/null || true
git commit -m "blog: pipeline auto $(date '+%Y-%m-%d')" >> "$LOG_FILE" 2>&1 || echo "  (nada novo)" >> "$LOG_FILE"
git push origin main >> "$LOG_FILE" 2>&1 || true

# 7. Webhook de notificação
if [ -n "$WEBHOOK_URL" ]; then
    POSTS_TODAY=$(find "$FRALIB_DIR/frontend/blog/posts" -name "*.html" -mtime -1 | wc -l)
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"[FraLib Blog] ${POSTS_TODAY} posts gerados em $(date '+%Y-%m-%d')\"}" \
        >> "$LOG_FILE" 2>&1 || true
fi

echo "=== PIPELINE END $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
