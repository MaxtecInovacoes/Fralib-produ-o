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
from typing import Optional

import psycopg2

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

    Atomic LRU via DB: SELECT ... ORDER BY last_used_at ASC ... FOR UPDATE SKIP LOCKED
    garante que multiplos workers/processos nunca pegam a mesma key simultaneamente.
    """
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                # Atomic: pega a key menos usada recentemente, trava a row
                cur.execute(
                    """
                    UPDATE provider_keys
                    SET last_used_at = NOW()
                    WHERE id = (
                        SELECT id FROM provider_keys
                        WHERE provider = %s
                          AND enabled = TRUE
                          AND (cooldown_until IS NULL OR cooldown_until < NOW())
                        ORDER BY last_used_at ASC NULLS FIRST
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING id, encrypted_key, base_url
                    """,
                    (provider,),
                )
                row = cur.fetchone()
                conn.commit()
    except Exception as e:
        print(f'[ia_manager] erro pick_key atomic: {e}')
        row = None

    if not row:
        # Nenhuma key saudavel — fallback .env
        env = _ENV_FALLBACK.get(provider)
        if env and env[0]:
            return (env[0], env[1], None)
        return None

    key_id, enc, base_url = row
    plain = decriptar(enc)
    if not plain:
        # Key corrompida — marca falha e tenta proxima
        mark_failure(key_id, 'fernet_decrypt_failed', cooldown_seconds=300)
        return pick_key(provider)

    if not base_url:
        base_url = _default_base_url(provider)
    return (plain, base_url, int(key_id))


def _default_base_url(provider: str) -> str:
    return {
        'anthropic': os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud'),
        'openai':    'https://api.openai.com/v1',
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
        # Fallback .env — gravar cooldown global
        set_global_cooldown(cooldown_seconds)
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


def set_global_cooldown(seconds: int) -> None:
    """Grava cooldown global para quando usa key do .env (sem key_id)."""
    if seconds < 15:
        return
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO app_settings (key, value)
                    VALUES ('global_cooldown_until', (NOW() + (%s || ' seconds')::interval)::text)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, (str(int(seconds)),))
            conn.commit()
        print(f'[ia_manager] Global cooldown setado: {seconds}s')
    except Exception as e:
        # Tabela pode não existir — criar
        if 'app_settings' in str(e) or 'relation' in str(e):
            try:
                with _connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS app_settings (
                                key VARCHAR(100) PRIMARY KEY,
                                value TEXT NOT NULL,
                                updated_at TIMESTAMP DEFAULT NOW()
                            )
                        """)
                        cur.execute("""
                            INSERT INTO app_settings (key, value)
                            VALUES ('global_cooldown_until', (NOW() + (%s || ' seconds')::interval)::text)
                            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                        """, (str(int(seconds)),))
                    conn.commit()
                print(f'[ia_manager] Global cooldown setado (tabela criada): {seconds}s')
            except Exception as e2:
                print(f'[ia_manager] set_global_cooldown falhou: {e2}')
        else:
            print(f'[ia_manager] set_global_cooldown falhou: {e}')


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


# ===== ENV HELPERS (shared with config.py) =====
def _get_int(key: str, default: int) -> int:
    try:
        raw = os.getenv(key)
        return int(raw) if raw and raw.strip().isdigit() else default
    except (ValueError, TypeError):
        return default


# ===== Rate Limit Protection System =====

DAILY_TOKEN_BUDGET = _get_int("DAILY_TOKEN_BUDGET", 2_000_000)  # 2M tokens/dia default
GLOBAL_MAX_CALLS_PER_MIN = _get_int("GLOBAL_MAX_CALLS_PER_MIN", 30)

TENANT_DAILY_LIMITS = {
    'trial': 100_000,
    'starter': 300_000,
    'pro': 800_000,
    'beta': 800_000,
    'ilimitado': 999_999_999,
}


def is_globally_cooled_down() -> tuple:
    """Retorna (em_cooldown: bool, segundos_restantes: int).
    Checa se TODAS as keys estão em cooldown (circuit breaker global).
    Funciona tanto com keys na tabela quanto com fallback .env.
    """
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                # Primeiro: checar tabela provider_keys
                cur.execute("""
                    SELECT COUNT(*) FROM provider_keys
                    WHERE provider = 'anthropic' AND enabled = TRUE
                """)
                total_keys = cur.fetchone()[0] or 0

                if total_keys > 0:
                    # Tem keys na tabela — checar se alguma está saudável
                    cur.execute("""
                        SELECT COUNT(*) FROM provider_keys
                        WHERE provider = 'anthropic' AND enabled = TRUE
                          AND (cooldown_until IS NULL OR cooldown_until < NOW())
                    """)
                    healthy = cur.fetchone()[0] or 0
                    if healthy > 0:
                        return (False, 0)
                    # Todas em cooldown — pegar o maior cooldown
                    cur.execute("""
                        SELECT EXTRACT(EPOCH FROM (cooldown_until - NOW()))::int
                        FROM provider_keys
                        WHERE provider = 'anthropic' AND enabled = TRUE
                        ORDER BY cooldown_until DESC LIMIT 1
                    """)
                    row = cur.fetchone()
                    return (True, row[0]) if row and row[0] and row[0] > 0 else (False, 0)
                else:
                    # Sem keys na tabela — checar cooldown global via tabela auxiliar
                    cur.execute("""
                        SELECT EXTRACT(EPOCH FROM (value::timestamp - NOW()))::int
                        FROM app_settings
                        WHERE key = 'global_cooldown_until' AND value::timestamp > NOW()
                    """)
                    row = cur.fetchone()
                    if row and row[0] and row[0] > 0:
                        return (True, row[0])
                    return (False, 0)
    except Exception as e:
        # Tabela app_settings pode não existir — ignorar
        if 'app_settings' in str(e):
            return (False, 0)
        print(f'[ia_manager] is_globally_cooled_down erro: {e}')
        return (False, 0)


def check_daily_budget() -> tuple:
    """Retorna (dentro_budget: bool, tokens_restantes: int)."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(input_tokens + output_tokens), 0)::bigint as total
                    FROM llm_usage
                    WHERE criado_em > NOW() - INTERVAL '24 hours'
                """)
                row = cur.fetchone()
                used = row[0] if row else 0
                remaining = DAILY_TOKEN_BUDGET - used
                return (remaining > 0, max(0, remaining))
    except Exception as e:
        print(f'[ia_manager] check_daily_budget erro: {e}')
        return (True, DAILY_TOKEN_BUDGET)  # Na dúvida, permite


def check_tenant_budget(tenant_id: int, plano: str = 'starter') -> tuple:
    """Retorna (dentro_budget: bool, tokens_restantes: int)."""
    limit = TENANT_DAILY_LIMITS.get(plano.lower(), 300_000)
    if limit >= 999_999_999:
        return (True, limit)
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(input_tokens + output_tokens), 0)::bigint
                    FROM llm_usage
                    WHERE user_id = %s AND criado_em > NOW() - INTERVAL '24 hours'
                """, (tenant_id,))
                row = cur.fetchone()
                used = row[0] if row else 0
                remaining = limit - used
                return (used < limit, max(0, remaining))
    except Exception as e:
        print(f'[ia_manager] check_tenant_budget erro: {e}')
        return (True, limit)


def check_global_call_rate() -> tuple:
    """Retorna (dentro_limite: bool, calls_no_ultimo_minuto: int).
    Coordenação cross-process via DB.
    """
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)::int FROM llm_usage
                    WHERE criado_em > NOW() - INTERVAL '1 minute'
                """)
                row = cur.fetchone()
                count = row[0] if row else 0
                return (count < GLOBAL_MAX_CALLS_PER_MIN, count)
    except Exception as e:
        print(f'[ia_manager] check_global_call_rate erro: {e}')
        return (True, 0)


def get_rate_limit_status() -> dict:
    """Retorna status completo para dashboard de monitoramento."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                # Budget diário
                cur.execute("""
                    SELECT COALESCE(SUM(input_tokens + output_tokens), 0)::bigint
                    FROM llm_usage WHERE criado_em > NOW() - INTERVAL '24 hours'
                """)
                daily_used = cur.fetchone()[0] or 0

                # Calls último minuto
                cur.execute("""
                    SELECT COUNT(*)::int FROM llm_usage
                    WHERE criado_em > NOW() - INTERVAL '1 minute'
                """)
                calls_last_min = cur.fetchone()[0] or 0

                # Status das keys
                cur.execute("""
                    SELECT id, enabled,
                           CASE WHEN cooldown_until > NOW() THEN 'cooldown'
                                WHEN enabled = FALSE THEN 'disabled'
                                ELSE 'healthy' END as status,
                           cooldown_until,
                           success_count, failure_count, last_error
                    FROM provider_keys WHERE provider = 'anthropic'
                """)
                keys = []
                for row in cur.fetchall():
                    success = row[4] or 0
                    failure = row[5] or 0
                    total = success + failure
                    keys.append({
                        "id": row[0],
                        "status": row[2],
                        "cooldown_until": row[3].isoformat() if row[3] else None,
                        "success_rate": round(success / total * 100, 1) if total > 0 else 100.0,
                        "last_error": row[6],
                    })

                # Top tenants
                cur.execute("""
                    SELECT user_id, SUM(input_tokens + output_tokens)::bigint as total
                    FROM llm_usage
                    WHERE criado_em > NOW() - INTERVAL '24 hours' AND user_id IS NOT NULL
                    GROUP BY user_id ORDER BY total DESC LIMIT 10
                """)
                top_tenants = [{"id": r[0], "tokens": r[1]} for r in cur.fetchall()]

                return {
                    "daily_budget": {
                        "limit": DAILY_TOKEN_BUDGET,
                        "used": daily_used,
                        "remaining": max(0, DAILY_TOKEN_BUDGET - daily_used),
                        "percent": round(daily_used / DAILY_TOKEN_BUDGET * 100, 1) if DAILY_TOKEN_BUDGET > 0 else 0,
                    },
                    "keys": keys,
                    "calls_last_minute": calls_last_min,
                    "max_calls_per_minute": GLOBAL_MAX_CALLS_PER_MIN,
                    "top_tenants_today": top_tenants,
                }
    except Exception as e:
        print(f'[ia_manager] get_rate_limit_status erro: {e}')
        return {"error": str(e)}
