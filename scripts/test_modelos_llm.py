"""Testa quais modelos LLM respondem no proxy kpalabz.

User pediu: ver outros modelos em cascata fallback para nao dar problema
no kapslab. Antes veja quais modelos e nomes realmente respondem
antes de colocar qualquer nome.

Este script testa cada modelo e mostra o resultado.
"""

import os
import sys
sys.path.insert(0, '/root/fralib')

# Carregar env do VPS
env_file = '/root/fralib/.env'
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

import requests
import json
import time

API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://ia.namehost.com.br/v1")

# Lista de modelos para testar (kpalabz proxy)
MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-8",
    "claude-haiku-4-5",
    "claude-opus-4-7",
]


def test_model(model: str) -> dict:
    """Testa se um modelo responde."""
    print(f"\nTestando {model}...")
    start = time.time()

    try:
        r = requests.post(
            f"{BASE_URL}/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Diga 'ok'"}],
            },
            timeout=30,
        )

        elapsed = time.time() - start

        if r.status_code == 200:
            data = r.json()
            content = ""
            if "content" in data and len(data["content"]) > 0:
                content = data["content"][0].get("text", "")[:80]

            return {
                "model": model,
                "status": "OK",
                "status_code": r.status_code,
                "elapsed": f"{elapsed:.2f}s",
                "content": content,
            }
        else:
            return {
                "model": model,
                "status": "ERRO",
                "status_code": r.status_code,
                "elapsed": f"{elapsed:.2f}s",
                "error": r.text[:200],
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "model": model,
            "status": "EXCEPTION",
            "elapsed": f"{elapsed:.2f}s",
            "error": str(e)[:200],
        }


if __name__ == "__main__":
    print("=" * 80)
    print(f"Testando modelos no proxy: {BASE_URL}")
    print(f"API key: {API_KEY[:20]}...")
    print("=" * 80)

    results = []
    for m in MODELS:
        result = test_model(m)
        results.append(result)

        # Imprime resultado imediato
        if result["status"] == "OK":
            print(f"  OK ({result['elapsed']}) - resposta: '{result['content']}'")
        else:
            print(f"  {result['status']} ({result['elapsed']})")
            if "error" in result:
                err = result["error"][:200].replace("\n", " ")
                print(f"    {err}")

    print()
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    working = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] != "OK"]

    print(f"\nMODELOS QUE RESPONDEM ({len(working)}/{len(results)}):")
    for r in working:
        print(f"  {r['model']} ({r['elapsed']})")

    print(f"\nMODELOS QUE FALHARAM ({len(failed)}):")
    for r in failed:
        print(f"  {r['model']} - {r['status']} ({r.get('status_code', '')})")
