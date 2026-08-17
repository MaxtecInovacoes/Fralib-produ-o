from __future__ import annotations

import json
import time
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.secrets_crypto import decriptar, encriptar, mascarar_key


ALLOWED_PROVIDERS = {"anthropic", "openai", "groq", "custom"}


def list_provider_keys(db: Session) -> list[tuple]:
    return db.execute(text("""
        SELECT id, provider, label, encrypted_key, base_url, enabled,
               cooldown_until, last_error, last_used_at,
               success_count, failure_count, criado_em
        FROM provider_keys
        ORDER BY provider, id
    """)).fetchall()


def create_provider_key(db: Session, provider: str, label: str, apikey: str, base_url: str | None, created_by: int | None) -> int:
    row = db.execute(text("""
        INSERT INTO provider_keys (provider, label, encrypted_key, base_url, criado_por)
        VALUES (:p, :l, :e, :b, :u)
        RETURNING id
    """), {"p": provider, "l": label, "e": encriptar(apikey), "b": base_url, "u": created_by}).fetchone()
    db.commit()
    return int(row[0])


def get_provider_key(db: Session, key_id: int) -> tuple | None:
    return db.execute(text("SELECT id, provider FROM provider_keys WHERE id = :id"), {"id": key_id}).fetchone()


def update_provider_key(db: Session, key_id: int, updates: dict[str, Any]) -> None:
    db.execute(text(f"UPDATE provider_keys SET {', '.join(updates['sql'])} WHERE id = :id"), updates["params"])
    db.commit()


def delete_provider_key(db: Session, key_id: int) -> tuple | None:
    row = db.execute(text("SELECT provider, label FROM provider_keys WHERE id = :id"), {"id": key_id}).fetchone()
    if not row:
        return None
    db.execute(text("DELETE FROM provider_keys WHERE id = :id"), {"id": key_id})
    db.commit()
    return row


def toggle_provider_key(db: Session, key_id: int) -> bool:
    row = db.execute(text("SELECT enabled FROM provider_keys WHERE id = :id"), {"id": key_id}).fetchone()
    if not row:
        raise LookupError("Key nao encontrada")
    new_state = not bool(row[0])
    db.execute(text("UPDATE provider_keys SET enabled = :en, atualizado_em = NOW() WHERE id = :id"), {"en": new_state, "id": key_id})
    db.commit()
    return new_state


def reset_provider_cooldown(db: Session, key_id: int) -> None:
    db.execute(text("""
        UPDATE provider_keys SET cooldown_until = NULL, last_error = NULL, atualizado_em = NOW()
        WHERE id = :id
    """), {"id": key_id})
    db.commit()


def row_to_dict(row: tuple) -> dict[str, Any]:
    plain = decriptar(row[3])
    return {
        "id": row[0],
        "provider": row[1],
        "label": row[2],
        "apikey_masked": mascarar_key(plain),
        "base_url": row[4] or "",
        "enabled": bool(row[5]),
        "cooldown_until": row[6].isoformat() if row[6] else None,
        "in_cooldown": bool(row[6]) and row[6].timestamp() > time.time() if row[6] else False,
        "last_error": row[7] or "",
        "last_used_at": row[8].isoformat() if row[8] else None,
        "success_count": row[9] or 0,
        "failure_count": row[10] or 0,
        "criado_em": row[11].isoformat() if row[11] else None,
    }


def test_provider(provider: str, apikey: str, base_url: str | None) -> dict:
    t0 = time.time()
    try:
        if provider == "anthropic":
            url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
            r = requests.post(url, timeout=10, json={
                "model": "claude-haiku-4-5",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }, headers={
                "x-api-key": apikey,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            })
        elif provider == "openai":
            url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
            r = requests.post(url, timeout=10, json={
                "model": "gpt-4o-mini",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }, headers={
                "Authorization": f"Bearer {apikey}",
                "Content-Type": "application/json",
            })
        elif provider == "custom":
            if not base_url:
                return {"ok": False, "error": "base_url obrigatorio para custom"}
            url = base_url.rstrip("/") + "/chat/completions"
            r = requests.post(url, timeout=10, json={
                "model": "gpt-3.5-turbo",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }, headers={
                "Authorization": f"Bearer {apikey}",
                "Content-Type": "application/json",
            })
        elif provider == "groq":
            url = (base_url or "https://api.groq.com/openai/v1").rstrip("/") + "/chat/completions"
            r = requests.post(url, timeout=10, json={
                "model": "llama-3.1-8b-instant",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }, headers={
                "Authorization": f"Bearer {apikey}",
                "Content-Type": "application/json",
            })
        else:
            return {"ok": False, "error": "provider invalido"}
        return {"ok": False, "error": "timeout (10s)"}
    except requests.ConnectionError:
        return {"ok": False, "error": "network (host inacessivel)"}
    except Exception as e:
        return {"ok": False, "error": f"erro: {type(e).__name__}"}

    latency_ms = int((time.time() - t0) * 1000)
    if 200 <= r.status_code < 300:
        return {"ok": True, "latency_ms": latency_ms, "status": r.status_code}
    msg = {
        400: "400 requisicao invalida (modelo/payload nao aceito)",
        401: "401 nao autorizado (key invalida)",
        403: "403 proibido (key sem permissao)",
        404: "404 endpoint nao encontrado (base_url errada?)",
        429: "429 rate limit",
    }.get(r.status_code, f"{r.status_code} erro")
    return {"ok": False, "error": msg, "latency_ms": latency_ms, "status": r.status_code}
