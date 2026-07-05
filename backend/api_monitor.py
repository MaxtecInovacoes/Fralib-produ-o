#!/usr/bin/env python3
"""
FraLib API Usage Monitor
Monitora uso da API Anthropic em tempo real
Salva historico no banco e exibe dashboard
"""

import os, sys, requests, psycopg2, re, json, logging

from backend.utils.time import now_iso_utc  # noqa: E402  — M14 DRY
from datetime import datetime, timezone
from dotenv import load_dotenv

# FIX CRÍTICO: logging para monitoramento de API
# print() nao e confiavel em producao (stdout pode nao ser capturado)
# logger captura corretamente em arquivos de log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("api_monitor")

from backend.config import FRALIB_ROOT as _FR_ROOT

load_dotenv(str(_FR_ROOT / ".env"))

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://ia.namehost.com.br/v1")
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5433/fralib_db")


def get_db():
    m = re.match(r"postgresql://([^:@]+)(?::([^@]*))?@([^:/]+):(\d+)/(.+)", DB_URL)
    user, pwd, host, port, dbname = m.groups()
    return psycopg2.connect(
        host=host, port=int(port), user=user, password=pwd or "", dbname=dbname
    )


def check_limits():
    """Faz chamada minima e retorna headers de rate limit"""
    url = f"{BASE_URL}/v1/messages"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "x"}],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    h = resp.headers
    return {
        "timestamp": now_iso_utc(),
        "status": resp.status_code,
        "input_limit": int(h.get("Anthropic-Ratelimit-Input-Tokens-Limit", 0)),
        "input_remaining": int(h.get("Anthropic-Ratelimit-Input-Tokens-Remaining", 0)),
        "input_reset": h.get("Anthropic-Ratelimit-Input-Tokens-Reset", ""),
        "output_limit": int(h.get("Anthropic-Ratelimit-Output-Tokens-Limit", 0)),
        "output_remaining": int(
            h.get("Anthropic-Ratelimit-Output-Tokens-Remaining", 0)
        ),
        "output_reset": h.get("Anthropic-Ratelimit-Output-Tokens-Reset", ""),
        "req_limit": int(h.get("Anthropic-Ratelimit-Requests-Limit", 0)),
        "req_remaining": int(h.get("Anthropic-Ratelimit-Requests-Remaining", 0)),
        "req_reset": h.get("Anthropic-Ratelimit-Requests-Reset", ""),
    }


def save_to_db(data):
    """Salva snapshot no banco"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_usage_snapshots (
                id SERIAL PRIMARY KEY,
                captured_at TIMESTAMPTZ DEFAULT NOW(),
                input_limit INT, input_remaining INT, input_reset TEXT,
                output_limit INT, output_remaining INT, output_reset TEXT,
                req_limit INT, req_remaining INT, req_reset TEXT
            )
        """)
        cur.execute(
            """
            INSERT INTO api_usage_snapshots
            (input_limit, input_remaining, input_reset,
             output_limit, output_remaining, output_reset,
             req_limit, req_remaining, req_reset)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
            (
                data["input_limit"],
                data["input_remaining"],
                data["input_reset"],
                data["output_limit"],
                data["output_remaining"],
                data["output_reset"],
                data["req_limit"],
                data["req_remaining"],
                data["req_reset"],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # FIX CRÍTICO: print() nao e confiavel em ambiente de producao
        # logging captura corretamente em arquivos de log
        logger.error(f"[DB] Erro ao salvar snapshot de uso da API: {e}")


def bar(used_pct, width=20):
    filled = int(width * used_pct / 100)
    color = "\033[92m" if used_pct < 50 else "\033[93m" if used_pct < 80 else "\033[91m"
    reset = "\033[0m"
    return color + "█" * filled + "░" * (width - filled) + reset


def dashboard(data):
    inp_used = (
        round((1 - data["input_remaining"] / data["input_limit"]) * 100, 1)
        if data["input_limit"]
        else 0
    )
    out_used = (
        round((1 - data["output_remaining"] / data["output_limit"]) * 100, 1)
        if data["output_limit"]
        else 0
    )
    req_used = (
        round((1 - data["req_remaining"] / data["req_limit"]) * 100, 1)
        if data["req_limit"]
        else 0
    )

    # Calcular pipelines restantes (estimativa: 15k input + 5k output por pipeline)
    pipelines_by_input = data["input_remaining"] // 15000
    pipelines_by_output = data["output_remaining"] // 5000
    pipelines_ok = min(pipelines_by_input, pipelines_by_output)

    now = datetime.now().strftime("%H:%M:%S")
    reset_time = (
        data["input_reset"][:19].replace("T", " ") if data["input_reset"] else "?"
    )

    print()
    print("\033[1m╔══════════════════════════════════════════════╗\033[0m")
    print("\033[1m║       FRALIB — API USAGE MONITOR             ║\033[0m")
    print("\033[1m╚══════════════════════════════════════════════╝\033[0m")
    print(f"  Horario: {now}   Reset janela: {reset_time} UTC")
    print()
    print(f"  INPUT TOKENS   {bar(inp_used)} {inp_used:5.1f}%")
    print(f"  {data['input_remaining']:,} restando de {data['input_limit']:,}/min")
    print()
    print(f"  OUTPUT TOKENS  {bar(out_used)} {out_used:5.1f}%")
    print(f"  {data['output_remaining']:,} restando de {data['output_limit']:,}/min")
    print()
    print(f"  REQUESTS       {bar(req_used)} {req_used:5.1f}%")
    print(f"  {data['req_remaining']:,} restando de {data['req_limit']:,}/min")
    print()
    print(f"  PIPELINES POSSIVEIS AGORA: ~{pipelines_ok} simultaneos")
    print("  (estimativa: 15k input + 5k output por pipeline)")
    print()

    if inp_used > 80 or out_used > 80:
        print("  \033[91m⚠  ALERTA: Limite quase esgotado! Aguarde o reset.\033[0m")
    elif inp_used > 50 or out_used > 50:
        print("  \033[93m⚡ AVISO: Mais de 50% consumido nesta janela.\033[0m")
    else:
        print("  \033[92m✓  Limite saudavel.\033[0m")
    print()


if __name__ == "__main__":
    save_flag = "--save" in sys.argv
    data = check_limits()
    dashboard(data)
    if save_flag:
        save_to_db(data)
        print("  [DB] Snapshot salvo no banco.")
    # Salvar JSON para o painel web
    with open("/tmp/api_usage_latest.json", "w") as f:
        json.dump(data, f)
