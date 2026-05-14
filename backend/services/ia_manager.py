"""
ia_manager — round-robin entre keys saudaveis de um provider, com circuit-breaker.

Fonte: tabela provider_keys. Round-robin distribui carga entre keys com
enabled=true e cooldown_until expirado/nulo. Quando uma key da 429 ou 5xx,
o manager seta cooldown e tenta a proxima.

Fallback: se a tabela esta vazia pro provider 'anthropic', retorna a key
do .env (ANTHROPIC_API_KEY) pra nao quebrar o pipeline antes do cadastro.

Uso tipico:
    from services import ia_manager
    key, base_url, key_id = ia_manager.pick_key('anthropic')
    # ...faz a request...
    if ok:
        ia_manager.mark_success(key_id)
    else:
        ia_manager.mark_failure(key_id, error_msg, cooldown_seconds=15)

O manager nao faz a request — quem chama tem essa logica. Isso mantem o
acoplamento minimo com call_claude/call_openai/etc.
"""
import os
import threading
from collections import defaultdict
from typing import Optional

import psycopg2
from psycopg2.extras import DictCursor

from utils.secrets_crypto import decriptar


_DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:fralib2024@localhost:5433/fralib_db')

# Defaults usados quando a tabela esta vazia (fallback pro .env). So pro Anthropic
# porque hoje so ele tem variavel global no codigo.
_ENV_FALLBACK = {
    'anthropic': (
        os.getenv('ANTHROPIC_API_KEY', ''),
        os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud'),
    ),
}

# Counters de round-robin por provider, em memoria. Thread-safe.
_rr_counters: dict[str, int] = defaultdict(int)
_rr_lock = threading.Lock()


def _connect():
    return psycopg2.connect(_DB_URL)


def _list_healthy(provider: str):
    """Retorna [(id, encrypted_key, base_url), ...] das keys saudaveis."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, encrypted_key, base_url
                    FROM provider_keys
                    WHERE provider = %s
                      AND enabled = TRUE
                      AND (cooldown_until IS NULL OR cooldown_until < NOW())
                    ORDER BY id
                    """,
                    (provider,),
                )
                return cur.fetchall()
    except Exception as e:
        print(f'[ia_manager] erro consultando provider_keys: {e}')
        return []


def pick_key(provider: str) -> Optional[tuple[str, str, Optional[int]]]:
    """Retorna (api_key_plaintext, base_url, key_id) ou None se nao houver opcao.

    Round-robin sobre o snapshot atual de keys saudaveis. Se nao houver key
    cadastrada, usa fallback do .env (so pra anthropic).
    """
    rows = _list_healthy(provider)
    if not rows:
        env = _ENV_FALLBACK.get(provider)
        if env and env[0]:
            return (env[0], env[1], None)
        return None

    with _rr_lock:
        idx = _rr_counters[provider] % len(rows)
        _rr_counters[provider] = idx + 1

    key_id, enc, base_url = rows[idx]
    plain = decriptar(enc)
    if not plain:
        # Key corrompida (FERNET_KEY mudou). Marca falha e tenta proxima.
        mark_failure(key_id, 'fernet_decrypt_failed', cooldown_seconds=300)
        # Tail-recurse pra pegar a proxima — limita por seguranca a len(rows).
        # Simples: chama de novo; se ainda vier essa, vai cair em outra iteracao
        # do round-robin. No pior caso, todas falham e retornamos None.
        return pick_key(provider)

    # base_url null = default por provider.
    if not base_url:
        base_url = _default_base_url(provider)
    return (plain, base_url, int(key_id))


def _default_base_url(provider: str) -> str:
    return {
        'anthropic': os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud'),
        'openai':    'https://api.openai.com/v1',
        'google':    'https://generativelanguage.googleapis.com/v1beta',
        'custom':    '',
    }.get(provider, '')


def mark_success(key_id: Optional[int]) -> None:
    if not key_id:
        return  # fallback .env nao tem id
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE provider_keys
                    SET success_count = success_count + 1,
                        last_used_at = NOW(),
                        last_error = NULL,
                        atualizado_em = NOW()
                    WHERE id = %s
                    """,
                    (key_id,),
                )
            conn.commit()
    except Exception as e:
        print(f'[ia_manager] mark_success falhou key_id={key_id}: {e}')


def mark_failure(key_id: Optional[int], error: str, cooldown_seconds: int = 15) -> None:
    if not key_id:
        return
    error_short = (error or '')[:500]
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE provider_keys
                    SET failure_count = failure_count + 1,
                        last_error = %s,
                        cooldown_until = NOW() + (%s || ' seconds')::interval,
                        atualizado_em = NOW()
                    WHERE id = %s
                    """,
                    (error_short, str(int(cooldown_seconds)), key_id),
                )
            conn.commit()
    except Exception as e:
        print(f'[ia_manager] mark_failure falhou key_id={key_id}: {e}')


def raise_alert(tipo: str, key_id: Optional[int], mensagem: str,
                lead_id: Optional[int] = None, user_id: Optional[int] = None) -> None:
    """Grava alerta na tabela provider_alerts. Falha silenciosa.

    Deduplica: se ja existe alerta nao-lido do mesmo (tipo, key_id) nos ultimos
    5 minutos, nao insere de novo (evita spam quando todas as keys estouram).
    """
    if tipo not in ('rate_limit', 'all_keys_failed', 'key_invalid', 'test_failed'):
        print(f'[ia_manager] tipo de alerta invalido: {tipo}')
        return
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM provider_alerts
                    WHERE tipo = %s
                      AND COALESCE(key_id, -1) = COALESCE(%s, -1)
                      AND lido = FALSE
                      AND criado_em > NOW() - INTERVAL '5 minutes'
                    LIMIT 1
                """, (tipo, key_id))
                if cur.fetchone():
                    return
                cur.execute("""
                    INSERT INTO provider_alerts (tipo, key_id, mensagem, lead_id, user_id_afetado)
                    VALUES (%s, %s, %s, %s, %s)
                """, (tipo, key_id, (mensagem or '')[:1000], lead_id, user_id))
            conn.commit()
    except Exception as e:
        print(f'[ia_manager] raise_alert falhou: {e}')


def parse_cooldown_from_response(status_code: int, headers: dict) -> int:
    """Sugere quantos segundos pausar a key, baseado em status + headers."""
    if status_code == 429:
        # Anthropic: header Anthropic-Ratelimit-Input-Tokens-Reset (ISO datetime)
        reset = (headers or {}).get('Anthropic-Ratelimit-Input-Tokens-Reset', '')
        if reset:
            try:
                from datetime import datetime, timezone
                reset_dt = datetime.fromisoformat(reset.replace('Z', '+00:00'))
                return max(15, int((reset_dt - datetime.now(timezone.utc)).total_seconds()))
            except Exception:
                pass
        # OpenAI: header retry-after (segundos)
        retry_after = (headers or {}).get('retry-after') or (headers or {}).get('Retry-After')
        if retry_after:
            try:
                return max(15, int(float(retry_after)))
            except Exception:
                pass
        return 60
    if status_code in (502, 503, 529):
        return 30
    if status_code >= 500:
        return 15
    return 15
