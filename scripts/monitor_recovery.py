"""Monitor do sistema de recovery de WhatsApp.

Apos reconectar o whatsmeow, este script:
1. Verifica status da sessao
2. Tenta processar fila outbound
3. Reporta metricas

Uso:
    python3 monitor_recovery.py
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta

# Adicionar path do backend
sys.path.insert(0, '/root/fralib')

# Carregar .env
from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')

MEOWHATS_URL = os.getenv('MEOWHATS_URL', 'http://localhost:3001')
MEOWHATS_KEY_RAW = os.getenv('MEOWHATS_KEY', '')
MEOWHATS_KEY = MEOWHATS_KEY_RAW if '@' in MEOWHATS_KEY_RAW else f'{MEOWHATS_KEY_RAW}@'
CRON_SECRET = os.getenv('CRON_SECRET', '')
FRALIB_API = 'http://localhost:8000'


def check_session() -> dict:
    """Verifica status da sessao whatsmeow."""
    try:
        r = requests.get(
            f"{MEOWHATS_URL}/health",
            headers={'X-API-Key': MEOWHATS_KEY},
            timeout=5,
        )
        return {
            'connected': r.status_code == 200,
            'http_status': r.status_code,
            'response': r.text[:200] if r.status_code != 200 else 'OK',
        }
    except Exception as e:
        return {'connected': False, 'error': str(e)}


def process_queue() -> dict:
    """Processa fila outbound."""
    try:
        r = requests.post(
            f"{FRALIB_API}/api/cron/processar-fila-outbound",
            headers={'X-Cron-Secret': CRON_SECRET},
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
        return {'error': f'HTTP {r.status_code}: {r.text[:200]}'}
    except Exception as e:
        return {'error': str(e)}


def get_health() -> dict:
    """Verifica health do sistema."""
    try:
        r = requests.get(
            f"{FRALIB_API}/api/cron/sdr_health_outbound",
            headers={'X-Cron-Secret': CRON_SECRET},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return {}
    except Exception:
        return {}


def main():
    print("=" * 60)
    print(f"WhatsApp Recovery Monitor - {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. Status sessao
    print("\n[1] SESSAO WHATSMEOWS:")
    session = check_session()
    print(f"   Conectado: {session.get('connected', False)}")
    if not session.get('connected'):
        print(f"   Resposta: {session.get('response', 'N/A')[:100]}")
        print(f"   Erro: {session.get('error', 'N/A')[:100]}")

    # 2. Fila outbound
    print("\n[2] FILA OUTBOUND:")
    health = get_health()
    if health:
        pending = health.get('pending_count', 'N/A')
        sent_1h = health.get('sent_last_hour', 'N/A')
        print(f"   Pendentes: {pending}")
        print(f"   Enviadas (ultima hora): {sent_1h}")
        if 'redis_ok' in health:
            print(f"   Redis OK: {health['redis_ok']}")
    else:
        print("   N/A (endpoint pode nao existir)")

    # 3. Processar fila
    if session.get('connected'):
        print("\n[3] PROCESSANDO FILA:")
        result = process_queue()
        print(f"   Resultado: {result}")
    else:
        print("\n[3] FILA NAO PROCESSADA (sessao nao conectada)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
