#!/bin/bash
# Cron job para blog automatizado FraLib
# Executa 2x/dia: 9h e 18h (horario de Brasilia)
#
# Para configurar o cron do usuario:
#   TZ=America/Sao_Paulo
#   0 9 * * * /usr/bin/bash /root/fralib/scripts/cron_blog_setup.sh
#   0 18 * * * /usr/bin/bash /root/fralib/scripts/cron_blog_setup.sh
#
# Adicionar com: crontab -e

# Navega para o diretorio do fralib (tenta varios paths comuns)
cd /root/fralib || cd /opt/fralib || cd /home/$(whoami)/fralib || exit 1

# Ativa venv se existir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Carrega variaveis de ambiente (.env tem ANTHROPIC_API_KEY, MERCADOPAGO_*, etc)
if [ -f ".env" ]; then
    set -a  # exporta automaticamente todas as variaveis
    source .env
    set +a
fi

# Log do job
LOG_FILE="/var/log/fralib/blog_cron.log"
LOG_DIR=$(dirname $LOG_FILE)
if [ ! -d "$LOG_DIR" ]; then
    LOG_FILE="/root/fralib/logs/blog_cron.log"
    LOG_DIR=$(dirname $LOG_FILE)
    mkdir -p "$LOG_DIR"
fi

echo "=== Blog cron started at $(date) ===" >> $LOG_FILE

# Executa o script Python com o venv do FraLib (que tem bleach, lxml, etc)
VENV_PY="/root/fralib/venv/bin/python3"
if [ -f "$VENV_PY" ]; then
    PYTHON_BIN="$VENV_PY"
else
    PYTHON_BIN="python3"
fi

# Executa o script Python que gera 2 posts/dia (POSTS_PER_DAY=2)
$PYTHON_BIN scripts/cron_blog_automation.py >> $LOG_FILE 2>&1

echo "=== Blog cron finished at $(date) ===" >> $LOG_FILE