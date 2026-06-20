#!/bin/bash
# ============================================
# FraLib - Otimizacao SEGURA da VPS
# ============================================
# Tudo tem fallback. Se falhar, sistema continua normal.
# Rodar como root: bash scripts/vps-safe-optimize.sh

set -euo pipefail

echo "============================================"
echo " FraLib - Otimizacao Segura da VPS"
echo "============================================"
echo ""

# ============================================
# 1. INSTALAR REDIS (cache distribuido)
# ============================================
echo "[1/4] Instalando Redis..."

if command -v redis-server &>/dev/null; then
    echo "  [SKIP] Redis ja esta instalado ($(redis-server --version))"
else
    apt-get update -qq
    apt-get install -y -qq redis-server

    # Configurar Redis para usar pouca memoria (safe para VPS pequena)
    cat > /etc/redis/redis.conf << 'EOF'
bind 127.0.0.1
port 6379
maxmemory 128mb
maxmemory-policy allkeys-lru
save ""
appendonly no
EOF

    systemctl enable redis-server
    systemctl restart redis-server

    if redis-cli ping | grep -q PONG; then
        echo "  [OK] Redis instalado e funcionando"
    else
        echo "  [WARN] Redis instalado mas nao respondeu ao ping"
    fi
fi

# Adicionar REDIS_URL no .env da VPS (se nao existir)
ENV_FILE="/root/fralib/.env"
if [ -f "$ENV_FILE" ]; then
    if ! grep -q "REDIS_URL" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# Redis (auto-configurado pelo optimize script)" >> "$ENV_FILE"
        echo "REDIS_URL=redis://localhost:6379" >> "$ENV_FILE"
        echo "  [OK] REDIS_URL adicionado ao .env"
    else
        echo "  [SKIP] REDIS_URL ja existe no .env"
    fi
else
    echo "  [SKIP] .env nao encontrado em $ENV_FILE"
fi

echo ""

# ============================================
# 2. CONFIGURAR SWAP (evita OOM no npm build)
# ============================================
echo "[2/4] Configurando swap..."

if swapon --show | grep -q "/swapfile"; then
    echo "  [SKIP] Swap ja configurado ($(free -h | grep Swap | awk '{print $2}'))"
else
    # Verificar se tem espaco em disco (precisa pelo menos 5GB livre)
    FREE_DISK=$(df / | tail -1 | awk '{print $4}')
    if [ "$FREE_DISK" -gt 5242880 ]; then
        fallocate -l 4G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile

        # Persistir reboot
        if ! grep -q "/swapfile" /etc/fstab; then
            echo "/swapfile none swap sw 0 0" >> /etc/fstab
        fi

        # Swappiness baixo = so usa swap quando RAM estiver acabando
        sysctl vm.swappiness=10
        if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
            echo "vm.swappiness=10" >> /etc/sysctl.conf
        fi

        echo "  [OK] Swap 4GB configurado (swappiness=10)"
    else
        echo "  [SKIP] Disco com menos de 5GB livre - nao configurar swap"
    fi
fi

echo ""

# ============================================
# 3. PM2 COM MEMORY LIMIT (auto-recovery)
# ============================================
echo "[3/4] Configurando PM2 com memory limit..."

if command -v pm2 &>/dev/null; then
    # Listar processos fralib atuais
    PM2_PROCS=$(pm2 jlist 2>/dev/null | python3 -c "
import json, sys
procs = json.load(sys.stdin)
for p in procs:
    name = p.get('name', '')
    if 'fralib' in name.lower():
        print(name)
" 2>/dev/null || echo "")

    if [ -n "$PM2_PROCS" ]; then
        for proc_name in $PM2_PROCS; do
            # Verificar se ja tem max_memory_restart
            HAS_LIMIT=$(pm2 show "$proc_name" 2>/dev/null | grep "max memory" || true)
            if echo "$HAS_LIMIT" | grep -q "0"; then
                # Nao tem limit - setar
                pm2 set "$proc_name:max_memory_restart" "512M" 2>/dev/null || true
                echo "  [OK] PM2 $proc_name: max_memory_restart=512M"
            else
                echo "  [SKIP] PM2 $proc_name ja tem memory limit"
            fi
        done
        pm2 save
    else
        echo "  [INFO] Nenhum processo fralib encontrado no PM2"
        echo "  [INFO] Ao iniciar, use: pm2 start server.py --name fralib --max-memory-restart 512M"
    fi
else
    echo "  [SKIP] PM2 nao instalado"
fi

echo ""

# ============================================
# 4. VERIFICAR SISTEMA
# ============================================
echo "[4/4] Verificando sistema..."

echo ""
echo "=== STATUS ==="
echo "RAM Total:     $(free -h | grep Mem | awk '{print $2}')"
echo "RAM Usada:     $(free -h | grep Mem | awk '{print $3}')"
echo "RAM Livre:     $(free -h | grep Mem | awk '{print $4}')"
echo "Swap Total:    $(free -h | grep Swap | awk '{print $2}')"
echo "Swap Usado:    $(free -h | grep Swap | awk '{print $3}')"
echo "Redis:         $(redis-cli ping 2>/dev/null || echo 'Nao respondendo')"
echo "PostgreSQL:    $(pg_isready -h localhost -p 5433 2>/dev/null || echo 'Nao respondendo')"
echo "Disco Livre:   $(df -h / | tail -1 | awk '{print $4}')"
echo "Uptime:        $(uptime -p)"
echo ""

echo "============================================"
echo " Otimizacao concluida com seguranca!"
echo "============================================"
echo ""
echo "Proximos passos:"
echo "  1. Reiniciar o fralib para ativar Redis:"
echo "     cd /root/fralib && pm2 restart all"
echo ""
echo "  2. Verificar se Redis esta sendo usado:"
echo "     tail -f /root/fralib/logs/fralib.log | grep -i redis"
echo ""
echo "  3. Monitorar metricas:"
echo "     curl http://localhost:8000/api/metrics/public"
