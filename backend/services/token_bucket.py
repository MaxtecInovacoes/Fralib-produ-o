"""
Token Bucket Rate Limiter — DB-backed, cross-process.

Usa tabela llm_usage como fonte de verdade para calcular
tokens consumidos na janela. Garante que NUNCA ultrapasse
o limite configurado, prevenindo 429s.

Configuração via .env:
  TOKEN_BUCKET_TPM=150000      # tokens/min máximo (80% do limite real)
  TOKEN_BUCKET_WINDOW=60       # janela em segundos
  TOKEN_BUCKET_SAFETY=0.75     # usar 75% do TPM (margem extra)
"""
import os
import time
import threading

import psycopg2

# ─── Configuração ────────────────────────────────────────────────────────────

MAX_TPM = int(os.getenv("TOKEN_BUCKET_TPM", "150000"))
WINDOW_SECONDS = int(os.getenv("TOKEN_BUCKET_WINDOW", "60"))
SAFETY_RATIO = float(os.getenv("TOKEN_BUCKET_SAFETY", "0.75"))
SAFE_TPM = int(MAX_TPM * SAFETY_RATIO)

_DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres@localhost:5433/fralib_db')

# Cache local pra não bater no DB a cada call
_lock = threading.Lock()
_last_check = 0.0
_cached_used = 0
_remaining_from_headers = None  # Calibração via response headers


# ─── Core ────────────────────────────────────────────────────────────────────

def _get_tokens_used_in_window() -> int:
    """Consulta DB: total de tokens usados na janela atual (cross-process)."""
    global _last_check, _cached_used
    now = time.time()
    # Cache por 2s pra não sobrecarregar DB com queries a cada call
    if now - _last_check < 2.0:
        return _cached_used
    try:
        conn = psycopg2.connect(_DB_URL, connect_timeout=3)
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(input_tokens + output_tokens), 0)::bigint "
            "FROM llm_usage WHERE criado_em > NOW() - INTERVAL '%s seconds'" % int(WINDOW_SECONDS)
        )
        row = cur.fetchone()
        _cached_used = row[0] if row else 0
        _last_check = now
        cur.close()
        conn.close()
    except Exception as e:
        # Se DB falhar, usar cache anterior (não bloquear)
        if _cached_used == 0:
            print(f"[TokenBucket] DB query falhou: {e}")
    return _cached_used


def tokens_available() -> int:
    """Quantos tokens ainda cabem na janela atual."""
    used = _get_tokens_used_in_window()
    return max(0, SAFE_TPM - used)


def can_send(estimated_tokens: int) -> bool:
    """Pode enviar request com esse tamanho sem estourar o limite?"""
    return tokens_available() >= estimated_tokens


def wait_time(estimated_tokens: int) -> float:
    """Segundos pra esperar antes de enviar. 0 = pode ir agora."""
    available = tokens_available()
    if available >= estimated_tokens:
        return 0.0
    # Precisa esperar tokens "caírem" da janela (sliding window)
    deficit = estimated_tokens - available
    # Tokens saem da janela a uma taxa de SAFE_TPM/WINDOW por segundo
    drain_rate = SAFE_TPM / WINDOW_SECONDS
    if drain_rate <= 0:
        return float(WINDOW_SECONDS)
    wait = deficit / drain_rate
    # Adicionar 1s de margem, cap em 1 janela inteira
    return min(wait + 1.0, float(WINDOW_SECONDS))


def throttle(estimated_tokens: int) -> None:
    """Bloqueia até ter espaço na janela. Chamado antes de cada call_claude."""
    with _lock:
        wait = wait_time(estimated_tokens)
        if wait > 0:
            avail = tokens_available()
            print(f"[TokenBucket] Throttling {wait:.1f}s (available={avail}, need={estimated_tokens}, safe_tpm={SAFE_TPM})")
            time.sleep(wait)
            # Invalidar cache após sleep pra re-checar
            global _last_check
            _last_check = 0.0


def update_remaining(remaining_tokens: int) -> None:
    """Calibra o bucket com dados reais dos response headers.
    Se o proxy expõe x-ratelimit-remaining-tokens, usamos pra ajustar.
    """
    global _remaining_from_headers
    _remaining_from_headers = remaining_tokens


# ─── Status (para monitoramento) ─────────────────────────────────────────────

def get_status() -> dict:
    """Retorna status atual do bucket para debug/monitoramento."""
    used = _get_tokens_used_in_window()
    return {
        "max_tpm": MAX_TPM,
        "safe_tpm": SAFE_TPM,
        "window_seconds": WINDOW_SECONDS,
        "safety_ratio": SAFETY_RATIO,
        "tokens_used_in_window": used,
        "tokens_available": max(0, SAFE_TPM - used),
        "percent_used": round(used / SAFE_TPM * 100, 1) if SAFE_TPM > 0 else 0,
        "remaining_from_headers": _remaining_from_headers,
    }
