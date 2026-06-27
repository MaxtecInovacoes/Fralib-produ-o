#!/usr/bin/env bash
# Cron job diário do blog automatizado FraLib
# Roda todo dia às 8h (horário de Brasília)
# 0 8 * * * /bin/bash /opt/fralib/scripts/cron_diario.sh

set -e

# Paths
FRALIB_DIR="/opt/fralib"
SCRIPTS_DIR="$FRALIB_DIR/scripts"
LOG_FILE="/var/log/fralib/blog_cron.log"
mkdir -p $(dirname "$LOG_FILE")

# Navega para o diretório
cd "$FRALIB_DIR" || exit 1

# Ativa venv se existir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Carrega variáveis de ambiente
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

echo "=== Blog cron started at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# Step 1: Buscar tendências
echo "  [1/3] Buscando tendências..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/buscar_tendencias.py" >> "$LOG_FILE" 2>&1

# Step 2: Verificar se já postou (evitar duplicatas)
TENDENCIAS_FILE="$SCRIPTS_DIR/tendencias.json"
if [ ! -f "$TENDENCIAS_FILE" ]; then
    echo "  ✗ Arquivo de tendências não foi gerado" >> "$LOG_FILE"
    exit 1
fi

TOTAL_TRENDS=$(python3 -c "import json; d=json.load(open('$TENDENCIAS_FILE')); print(d.get('total', 0))")
echo "  $TOTAL_TRENDS tendências carregadas" >> "$LOG_FILE"

if [ "$TOTAL_TRENDS" -eq 0 ]; then
    echo "  ⚠ Nenhuma tendência nova, pulando" >> "$LOG_FILE"
    exit 0
fi

# Step 3: Gerar posts
echo "  [2/3] Gerando posts..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/gerar_post.py" >> "$LOG_FILE" 2>&1

# Step 4: Publicar (atualizar index, sitemap, RSS)
echo "  [3/3] Publicando..." >> "$LOG_FILE"
python3 "$SCRIPTS_DIR/publicar.py" >> "$LOG_FILE" 2>&1

# Step 5: Git commit + push (deploy automático)
cd "$FRALIB_DIR"
git add frontend/blog/ scripts/tendencias.json 2>/dev/null || true
git commit -m "blog: novos posts automáticos $(date '+%Y-%m-%d')" >> "$LOG_FILE" 2>&1 || echo "  (nada para commitar)" >> "$LOG_FILE"
git push origin main >> "$LOG_FILE" 2>&1 || echo "  ⚠ push falhou (deploy manual necessário)" >> "$LOG_FILE"

echo "=== Blog cron finished at $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
