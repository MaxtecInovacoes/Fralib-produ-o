"""Validate and register a provider API key without leaking the secret.

Usage:
    set FRALIB_PROVIDER_API_KEY=...
    python scripts/repair_provider_key.py --provider anthropic --label aibee-main --apply

Without --apply the script only validates the key and prints a safe summary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for item in (str(BACKEND), str(BACKEND / "utils")):
    if item not in sys.path:
        sys.path.insert(0, item)

from utils.secrets_crypto import encriptar  # noqa: E402
from core.proxy_models import PROXY_LIGHT_MODEL  # noqa: E402


DEFAULT_BASE_URLS = {
    "anthropic": "https://llm.seunegociofralib.site",
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

DEFAULT_TEST_MODELS = {
    "anthropic": PROXY_LIGHT_MODEL,
    "openai": "gpt-4o-mini",
    "google": "gemini-2.0-flash",
    "groq": "llama-3.1-8b-instant",
    "openrouter": "anthropic/claude-haiku-4.5",
}


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="anthropic", choices=sorted(DEFAULT_BASE_URLS))
    parser.add_argument("--label", default="aibee-main")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--key-env", default="FRALIB_PROVIDER_API_KEY")
    parser.add_argument("--created-by", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--mark-alerts-read", action="store_true")
    args = parser.parse_args()

    api_key = (os.getenv(args.key_env) or "").strip()
    if not api_key:
        _print(
            ok=False,
            applied=False,
            provider=args.provider,
            error=f"env {args.key_env} vazia; nao passe chave por argumento",
        )
        return 2

    base_url = (args.base_url or DEFAULT_BASE_URLS[args.provider]).rstrip("/")
    model = args.model or DEFAULT_TEST_MODELS[args.provider]
    test = validate_provider_key(args.provider, api_key, base_url, model)
    if not test["ok"]:
        _print(
            ok=False,
            applied=False,
            provider=args.provider,
            label=args.label,
            base_url=base_url,
            key_masked=mask_key(api_key),
            test=test,
        )
        return 3

    result: dict[str, Any] = {
        "ok": True,
        "applied": False,
        "provider": args.provider,
        "label": args.label,
        "base_url": base_url,
        "key_masked": mask_key(api_key),
        "test": test,
    }
    if args.apply:
        engine = _engine()
        key_id = upsert_provider_key(
            engine,
            provider=args.provider,
            label=args.label,
            api_key=api_key,
            base_url=base_url,
            created_by=args.created_by,
        )
        clear_global_cooldown(engine)
        if args.mark_alerts_read:
            mark_key_alerts_read(engine)
        result.update({"applied": True, "key_id": key_id})
    _print(**result)
    return 0


def validate_provider_key(provider: str, api_key: str, base_url: str, model: str) -> dict[str, Any]:
    started = time.time()
    try:
        if provider == "anthropic":
            response = requests.post(
                f"{base_url.rstrip('/')}/v1/messages",
                timeout=20,
                json={
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )
        elif provider in {"openai", "groq", "openrouter"}:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            if provider == "openrouter":
                headers.update({"HTTP-Referer": "https://seunegociofralib.site", "X-Title": "FraLib"})
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                timeout=20,
                json={
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                headers=headers,
            )
        elif provider == "google":
            response = requests.post(
                f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}",
                timeout=20,
                json={
                    "contents": [{"parts": [{"text": "hi"}]}],
                    "generationConfig": {"maxOutputTokens": 1},
                },
                headers={"Content-Type": "application/json"},
            )
        else:
            return {"ok": False, "error": "provider invalido"}
    except requests.Timeout:
        return {"ok": False, "error": "timeout"}
    except requests.ConnectionError:
        return {"ok": False, "error": "network"}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}

    status = int(response.status_code)
    latency_ms = int((time.time() - started) * 1000)
    if 200 <= status < 300:
        return {"ok": True, "status": status, "latency_ms": latency_ms, "model": model}
    return {
        "ok": False,
        "status": status,
        "latency_ms": latency_ms,
        "error": _safe_http_error(status),
    }


def upsert_provider_key(
    engine,
    *,
    provider: str,
    label: str,
    api_key: str,
    base_url: str,
    created_by: int | None,
) -> int:
    encrypted = encriptar(api_key)
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM provider_keys WHERE provider=:provider AND label=:label ORDER BY id LIMIT 1"),
            {"provider": provider, "label": label},
        ).fetchone()
        if row:
            key_id = int(row[0])
            conn.execute(
                text(
                    """
                    UPDATE provider_keys
                    SET encrypted_key=:encrypted, base_url=:base_url, enabled=TRUE,
                        cooldown_until=NULL, last_error=NULL, atualizado_em=NOW()
                    WHERE id=:id
                    """
                ),
                {"id": key_id, "encrypted": encrypted, "base_url": base_url},
            )
            return key_id
        inserted = conn.execute(
            text(
                """
                INSERT INTO provider_keys (provider, label, encrypted_key, base_url, enabled, criado_por)
                VALUES (:provider, :label, :encrypted, :base_url, TRUE, :created_by)
                RETURNING id
                """
            ),
            {
                "provider": provider,
                "label": label,
                "encrypted": encrypted,
                "base_url": base_url,
                "created_by": created_by,
            },
        ).fetchone()
        return int(inserted[0])


def clear_global_cooldown(engine) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM app_settings WHERE key='global_cooldown_until'"))
    except Exception:
        pass


def mark_key_alerts_read(engine) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE provider_alerts
                    SET lido=TRUE, lido_em=NOW()
                    WHERE tipo='key_invalid' AND lido=FALSE
                    """
                )
            )
    except Exception:
        pass


def mask_key(api_key: str) -> str:
    """Compat shim — fonte em backend.utils.pii_masker.mask_key (M8 DRY)."""
    from backend.utils.pii_masker import mask_key as _mk  # noqa: E402  — M8 DRY shim
    return _mk(api_key)


def _engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL ausente")
    connect_args = (
        {"options": "-csearch_path=public"}
        if database_url.startswith(("postgresql://", "postgresql+psycopg2://"))
        else {}
    )
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def _safe_http_error(status: int) -> str:
    return {
        400: "400 requisicao invalida ou modelo indisponivel",
        401: "401 key invalida",
        403: "403 key sem permissao",
        404: "404 base_url/modelo incorreto",
        429: "429 rate limit",
    }.get(status, f"{status} erro do provider")


def _print(**payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
