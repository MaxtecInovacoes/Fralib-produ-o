#!/bin/bash
# Cron job para blog automatizado FraLib
# Executa 2x/dia: 9h e 18h (horario de Brasilia)
#
# Para configurar o cron do usuario:
#   TZ=America/Sao_Paulo
#   0 9 * * * /usr/bin/bash /opt/fralib/scripts/cron_blog_setup.sh
#   0 18 * * * /usr/bin/bash /opt/fralib/scripts/cron_blog_setup.sh
#
# Adicionar com: crontab -e (depois de mover o script para /opt/fralib/scripts/)

# Navega para o diretorio do fralib
cd /opt/fralib || cd /home/$(whoami)/fralib || cd /root/fralib || exit 1

# Ativa venv se existir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Carrega variaveis de ambiente (.env tem ANTHROPIC_API_KEY, MERCADOPAGO_*, etc)
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Log do job
LOG_FILE="/var/log/fralib/blog_cron.log"
mkdir -p $(dirname $LOG_FILE)

echo "=== Blog cron started at $(date) ===" >> $LOG_FILE

# Executa o script Python que gera 2 posts/dia (POSTS_PER_DAY=2)
python3 scripts/cron_blog_automation.py >> $LOG_FILE 2>&1

echo "=== Blog cron finished at $(date) ===" >> $LOG_FILE