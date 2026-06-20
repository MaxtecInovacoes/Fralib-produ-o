#!/usr/bin/env python3
"""Apply FraLib production runtime variables without storing secrets in Git.

Run this script on the VPS from the deployed repo. It prompts for Mercado Pago
secrets in the terminal, writes only the local .env, and can restart PM2.
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
BACKUP_DIR = Path("/root/fralib-env-backups")
DEFAULT_REDIS_URL = "redis://localhost:6379"
NAMEHOST_BASE_URL = "https://ia.namehost.com.br/v1"
NAMEHOST_LIGHT_MODEL = "claude-sonnet-4-6"
NAMEHOST_DEFAULT_MODEL = "claude-sonnet-4-6"
NAMEHOST_BUILDER_MODEL = "claude-sonnet-4-6"
LOCAL_PROXY_BASE_URL = "http://127.0.0.1:4000/v1"
LOCAL_PROXY_LIGHT_MODEL = "fralib-fast-cheap"
LOCAL_PROXY_DEFAULT_MODEL = "fralib-agent-balanced"
LOCAL_PROXY_BUILDER_MODEL = "fralib-builder-strong"


def _fail(message: str, code: int = 1) -> None:
    print(f"erro: {message}", file=sys.stderr)
    raise SystemExit(code)


def _read_env_lines() -> list[str]:
    if not ENV_PATH.exists():
        _fail(f"{ENV_PATH} nao existe")
    return ENV_PATH.read_text(encoding="utf-8").splitlines()


def _parse_env(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _set_env(lines: list[str], key: str, value: str) -> list[str]:
    replacement = f"{key}={value}"
    out: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.lstrip()
        if not stripped.startswith("#") and stripped.startswith(f"{key}="):
            if not replaced:
                out.append(replacement)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(replacement)
    return out


def _clean_secret(value: str, *, name: str) -> str:
    value = (value or "").strip()
    if not value:
        _fail(f"{name} vazio")
    if "\n" in value or "\r" in value:
        _fail(f"{name} contem quebra de linha")
    if any(ch.isspace() for ch in value):
        _fail(f"{name} contem espaco")
    return value


def _prompt_secret(label: str, current_is_set: bool) -> str:
    suffix = " [enter para manter]" if current_is_set else ""
    value = getpass.getpass(f"{label}{suffix}: ").strip()
    return value


def _backup_env() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(BACKUP_DIR, stat.S_IRWXU)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_DIR / f".env.{stamp}"
    shutil.copy2(ENV_PATH, backup)
    os.chmod(backup, stat.S_IRUSR | stat.S_IWUSR)
    print(f"backup: {backup}")


def _write_env(lines: list[str]) -> None:
    tmp = ENV_PATH.parent / ".env.tmp"
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, ENV_PATH)
    os.chmod(ENV_PATH, stat.S_IRUSR | stat.S_IWUSR)


def _run(cmd: list[str], check: bool = True) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=check)


def _redis_ok() -> bool:
    try:
        out = subprocess.check_output(["redis-cli", "ping"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return False
    return out.strip() == "PONG"


def _restart_pm2() -> None:
    _run(["pm2", "restart", "fralib", "--update-env"])
    _run(["pm2", "startOrReload", "ecosystem.config.js", "--only", "fralib-worker", "--update-env"])
    _run(["pm2", "delete", "fralib-bryan-worker"], check=False)
    _run(["pm2", "startOrReload", "ecosystem.config.js", "--only", "fralib-franz-worker", "--update-env"])


def _apply_local_proxy_llm(lines: list[str], current: dict[str, str]) -> list[str]:
    api_key = _clean_secret(
        os.getenv("LOCAL_PROXY_API_KEY") or os.getenv("LITELLM_API_KEY") or current.get("LITELLM_API_KEY", ""),
        name="LOCAL_PROXY_API_KEY",
    )
    updates = {
        "LITELLM_API_KEY": api_key,
        "LITELLM_BASE_URL": LOCAL_PROXY_BASE_URL,
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_BASE_URL": LOCAL_PROXY_BASE_URL.removesuffix("/v1"),
        "FRALIB_PROXY_LIGHT_MODEL": LOCAL_PROXY_LIGHT_MODEL,
        "FRALIB_PROXY_DEFAULT_MODEL": LOCAL_PROXY_DEFAULT_MODEL,
        "FRALIB_PROXY_BUILDER_MODEL": LOCAL_PROXY_BUILDER_MODEL,
        "FRALIB_BUILDER_AIBEE_MODEL_ID": LOCAL_PROXY_BUILDER_MODEL,
        "FRALIB_LITELLM_OPENAI_CHAT": "1",
    }
    for key, value in updates.items():
        lines = _set_env(lines, key, value)
    print("env: runtime LLM proxy local aplicado")
    return lines

def _apply_namehost_llm(lines: list[str], current: dict[str, str]) -> list[str]:
    api_key = _clean_secret(
        os.getenv("NAMEHOST_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or current.get("ANTHROPIC_API_KEY", ""),
        name="NAMEHOST_API_KEY",
    )
    updates = {
        "NAMEHOST_API_KEY": api_key,
        "LITELLM_API_KEY": "",
        "LITELLM_BASE_URL": "",
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_BASE_URL": NAMEHOST_BASE_URL.removesuffix("/v1"),
        "FRALIB_PROXY_LIGHT_MODEL": NAMEHOST_LIGHT_MODEL,
        "FRALIB_PROXY_DEFAULT_MODEL": NAMEHOST_DEFAULT_MODEL,
        "FRALIB_PROXY_BUILDER_MODEL": NAMEHOST_BUILDER_MODEL,
        "FRALIB_BUILDER_AIBEE_MODEL_ID": NAMEHOST_BUILDER_MODEL,
        "FRALIB_LITELLM_OPENAI_CHAT": "0",
        "FRALIB_BUILDER_USE_PROVIDER_KEYS": "0",
        "FRALIB_SINGLE_MODEL_ONLY": "1",
        "FRALIB_DISABLE_PROXY_FAILOVER": "1",
    }
    for key, value in updates.items():
        lines = _set_env(lines, key, value)
    print("env: runtime LLM Namehost aplicado")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply FraLib production runtime on the VPS")
    parser.add_argument("--app-url", help="Public HTTPS URL, e.g. https://seudominio.com")
    parser.add_argument("--restart", action="store_true", help="Restart PM2 after writing .env")
    parser.add_argument("--allow-test-mercadopago-token", action="store_true", help="Allow TEST-* token for sandbox tests")
    parser.add_argument("--llm-namehost", action="store_true", help="Route LLM runtime to ia.namehost.com.br using NAMEHOST_API_KEY")
    parser.add_argument("--llm-local-proxy", action="store_true", help="Route LLM runtime to the local LiteLLM proxy on 127.0.0.1:4000")
    args = parser.parse_args()

    if not (ROOT / ".git").exists():
        _fail("execute dentro do repo implantado por Git")
    if args.llm_namehost or args.llm_local_proxy:
        lines = _read_env_lines()
        current = _parse_env(lines)
        _backup_env()
        if args.llm_namehost:
            lines = _apply_namehost_llm(lines, current)
        else:
            lines = _apply_local_proxy_llm(lines, current)
        _write_env(lines)
        if args.restart:
            _restart_pm2()
        else:
            print("proximo passo: pm2 restart fralib --update-env")
        return 0

    if not sys.stdin.isatty():
        _fail("execute em terminal interativo para nao expor segredos no historico")

    lines = _read_env_lines()
    current = _parse_env(lines)
    app_url = (args.app_url or current.get("APP_URL") or "").strip()
    if not app_url.startswith("https://"):
        _fail("APP_URL precisa ser HTTPS antes de habilitar cobranca real")

    current_token_set = bool(current.get("MERCADOPAGO_ACCESS_TOKEN"))
    token = _prompt_secret("MERCADOPAGO_ACCESS_TOKEN", current_token_set) or current.get("MERCADOPAGO_ACCESS_TOKEN", "")
    token = _clean_secret(token, name="MERCADOPAGO_ACCESS_TOKEN")
    if not (token.startswith("APP_USR") or (args.allow_test_mercadopago_token and token.startswith("TEST-"))):
        _fail("use token Mercado Pago de producao APP_USR... para venda real")

    current_secret_set = bool(current.get("MERCADOPAGO_WEBHOOK_SECRET"))
    webhook_secret = _prompt_secret("MERCADOPAGO_WEBHOOK_SECRET", current_secret_set)
    if not webhook_secret and current_secret_set:
        webhook_secret = current.get("MERCADOPAGO_WEBHOOK_SECRET", "")
    if not webhook_secret:
        webhook_secret = secrets.token_urlsafe(48)
        print("webhook_secret: gerado automaticamente; copie do .env da VPS para o painel Mercado Pago")
    webhook_secret = _clean_secret(webhook_secret, name="MERCADOPAGO_WEBHOOK_SECRET")
    if len(webhook_secret) < 32:
        _fail("MERCADOPAGO_WEBHOOK_SECRET deve ter pelo menos 32 caracteres")

    _backup_env()
    updates = {
        "APP_URL": app_url,
        "FRALIB_ENV": "prod",
        "FRALIB_COOKIE_SECURE": "1",
        "REDIS_URL": current.get("REDIS_URL") or DEFAULT_REDIS_URL,
        "FRALIB_RATE_LIMIT_STORAGE_URI": current.get("FRALIB_RATE_LIMIT_STORAGE_URI") or DEFAULT_REDIS_URL,
        "MERCADOPAGO_ACCESS_TOKEN": token,
        "MERCADOPAGO_WEBHOOK_SECRET": webhook_secret,
        "MERCADOPAGO_PLAN_STARTER_AMOUNT": current.get("MERCADOPAGO_PLAN_STARTER_AMOUNT") or "97",
        "MERCADOPAGO_PLAN_PRO_AMOUNT": current.get("MERCADOPAGO_PLAN_PRO_AMOUNT") or "197",
        "MERCADOPAGO_PLAN_AGENCY_AMOUNT": current.get("MERCADOPAGO_PLAN_AGENCY_AMOUNT") or "497",
        "MERCADOPAGO_RECHARGE_MAX_AMOUNT": current.get("MERCADOPAGO_RECHARGE_MAX_AMOUNT") or "5000",
    }
    for key, value in updates.items():
        lines = _set_env(lines, key, value)
    _write_env(lines)
    print("env: producao aplicada sem gravar segredo no Git")

    if not _redis_ok():
        print("aviso: Redis ainda nao respondeu. Rode scripts/vps_prepare_redis.sh antes da validacao final.")

    if args.restart:
        _restart_pm2()
    else:
        print("proximo passo: pm2 restart fralib --update-env")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

