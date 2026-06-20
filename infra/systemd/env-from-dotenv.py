#!/usr/bin/env python3
"""
env-from-dotenv.py
==================
Converte .env do FraLib em EnvironmentFile válido para systemd.

systemd NÃO suporta:
- export VAR=value
- comments com # no meio da linha
- aspas escapadas

Uso:
    python3 env-from-dotenv.py /root/fralib/.env /etc/fralib/fralib.env
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def parse_dotenv(env_path: Path) -> dict[str, str]:
    """Parse .env file (formato key=value) -> dict."""
    if not env_path.exists():
        raise FileNotFoundError(f".env nao encontrado: {env_path}")

    env: dict[str, str] = {}
    with env_path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Match: KEY=VALUE (sem export)
            match = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", line, re.IGNORECASE)
            if not match:
                print(f"[WARN] Linha {line_num} ignorada: {line[:50]}", file=sys.stderr)
                continue

            key = match.group(1)
            value = match.group(2).strip()

            # Remove aspas externas
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            env[key] = value

    return env


def write_systemd_env(env: dict[str, str], output_path: Path) -> None:
    """Escreve dict no formato EnvironmentFile do systemd."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Gerado por env-from-dotenv.py\n")
        f.write("# NÃO EDITAR — regenerado automaticamente\n\n")

        for key, value in env.items():
            # Escape para systemd (sem $, sem ", sem \)
            # systemd EnvironmentFile usa $ para expandir, então escapamos com $$
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
            f.write(f'{key}="{escaped}"\n')

    output_path.chmod(0o600)  # Apenas root lê (contém secrets)
    # Use ASCII-safe output for Windows compatibility
    print(f"[OK] {len(env)} variaveis escritas em {output_path}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Uso: env-from-dotenv.py <input.env> <output.env>")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    try:
        env = parse_dotenv(input_path)
        write_systemd_env(env, output_path)
    except Exception as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())