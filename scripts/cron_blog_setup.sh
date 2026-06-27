#!/usr/bin/env bash
# Cron job para blog automatizado
# Executa todo dia às 8h (horário de Brasília)
# 0 8 * * * /usr/bin/bash /opt/fralib/scripts/cron_blog_setup.sh

# Navega para o diretório do fralib
cd /opt/fralib || cd /home/$(whoami)/fralib || exit 1

# Ativa venv se existir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Carrega variáveis de ambiente
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Log do job
LOG_FILE="/var/log/fralib/blog_cron.log"
mkdir -p $(dirname $LOG_FILE)

echo "=== Blog cron started at $(date) ===" >> $LOG_FILE

# Executa o script
python3 scripts/cron_blog_automation.py >> $LOG_FILE 2>&1

echo "=== Blog cron finished at $(date) ===" >> $LOG_FILE
