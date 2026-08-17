"""
key_healthcheck.py
==================
Healthcheck automatico da chave Anthropic.

Detecta:
  - Chave morta (403 "plano venceu") -> auto-marca alerta como lido
  - Chave voltou a funcionar -> auto-reprocessa jobs que falharam por auth

Vantagem: evita loop de erro 403 infinito e libera pipeline
quando a chave for renovada.

Como ativa:
  - Importado pelo hermes (heartbeat a cada 5min)
  - Ou executado direto: python -m backend.services.key_healthcheck
"""

import logging
import os

import requests

logger = logging.getLogger("uvicorn.key_healthcheck")


def check_key_health() -> dict:
    """Testa a chave Anthropic com ping leve.

    Returns:
        {
          "ok": bool,            # True se chave funciona
          "status_code": int,
          "error_type": str,     # "permission_error" | "rate_limit" | "auth" | None
          "model_tested": str,
          "elapsed_ms": int,
          "message": str
        }
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    if not api_key or not base_url:
        return {
            "ok": False,
            "status_code": 0,
            "error_type": "config_missing",
            "message": "ANTHROPIC_API_KEY ou ANTHROPIC_BASE_URL nao configurado",
        }

    # Limpa /v1 duplicado
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]

    # Tenta com haiku (mais barato) e 5 tokens
    try:
        import time
        started = time.time()
        resp = requests.post(
            f"{base}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "ping"}],
            },
            timeout=15,
        )
        elapsed = int((time.time() - started) * 1000)

        if resp.status_code == 200:
            return {
                "ok": True,
                "status_code": 200,
                "error_type": None,
                "model_tested": "claude-haiku-4-5",
                "elapsed_ms": elapsed,
                "message": "Chave funcional",
            }

        # Detalhe do erro
        try:
            err = resp.json().get("error", {})
            err_type = err.get("type", "unknown")
        except Exception:
            err_type = "unknown"

        return {
            "ok": False,
            "status_code": resp.status_code,
            "error_type": err_type,
            "model_tested": "claude-haiku-4-5",
            "elapsed_ms": elapsed,
            "message": resp.text[:200],
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": 0,
            "error_type": "exception",
            "message": str(e)[:200],
        }


def auto_cleanup_auth_alerts() -> int:
    """Marca como lidos os alertas de auth que sao resultados de chave morta.

    Retorna numero de alertas limpos.
    """
    try:
        from backend.core.database import engine
        from sqlalchemy import text

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE provider_alerts
                    SET lido = TRUE, lido_em = NOW()
                    WHERE NOT lido
                      AND (
                          mensagem LIKE '%plano venceu%'
                          OR mensagem LIKE '%permission_error%'
                          OR (mensagem LIKE '%HTTP 403%' AND tipo = 'key_invalid')
                          OR (mensagem LIKE '%HTTP 401%' AND tipo = 'key_invalid')
                      )
                      AND criado_em < NOW() - INTERVAL '60 seconds'
                """)
            )
            count = result.rowcount
            if count:
                logger.info(f"[key_healthcheck] Marcados {count} alertas auth como lidos")
            return count
    except Exception as e:
        logger.error(f"[key_healthcheck] Erro limpando alertas: {e}")
        return 0


def auto_reprocess_recent_auth_failures() -> int:
    """Quando a chave voltou a funcionar, reprocessa jobs que falharam por auth.

    Retorna numero de jobs reenfileirados.
    """
    try:

        with engine.begin() as conn:
            # Marca pipeline_failures com auth_error como reprocessaveis
            # (seta resolvido=false se foi auto-fix ja tentou, mas tenta 1x mais)
            result = conn.execute(
                text("""
                    UPDATE pipeline_failures pf
                    SET resolvido = FALSE
                    WHERE pf.resolvido = TRUE
                      AND (
                          pf.erro_tecnico LIKE '%plano venceu%'
                          OR pf.erro_tecnico LIKE '%permission_error%'
                          OR (pf.erro_tecnico LIKE '%HTTP 403%' AND pf.erro_tecnico LIKE '%Anthropic%')
                          OR (pf.erro_tecnico LIKE '%HTTP 401%' AND pf.erro_tecnico LIKE '%Anthropic%')
                      )
                      AND pf.criado_em > NOW() - INTERVAL '1 hour'
                """)
            )
            count = result.rowcount
            if count:
                logger.info(f"[key_healthcheck] Reabertos {count} jobs para reprocessamento")
            return count
    except Exception as e:
        logger.error(f"[key_healthcheck] Erro reabrindo jobs: {e}")
        return 0


def run_healthcheck_cycle() -> dict:
    """Executa 1 ciclo completo: healthcheck + auto-cleanup + (se OK) reprocess.

    Returns:
        dict com resumo do ciclo
    """
    health = check_key_health()
    result = {
        "key_ok": health["ok"],
        "status_code": health["status_code"],
        "error_type": health.get("error_type"),
        "alerts_cleaned": 0,
        "jobs_reopened": 0,
    }

    if not health["ok"]:
        # Chave morta: limpa alerta para nao poluir admin
        result["alerts_cleaned"] = auto_cleanup_auth_alerts()
        result["action"] = "key_dead_cleaned_alerts"
    else:
        # Chave voltou: reprocessa jobs recentes
        result["jobs_reopened"] = auto_reprocess_recent_auth_failures()
        result["action"] = "key_alive_reprocessed_jobs"

    return result


# ── Funcao para ser chamada pelo hermes (heartbeat) ─────────────
def should_notify_admin(health: dict) -> bool:
    """Decide se deve notificar o admin (so quando chave RECEM voltou a falhar).

    Evita spam: notifica so na transicao alive->dead.
    """
    # Implementacao simples: o proprio auto_cleanup ja lida
    # com limpeza. Notificacao fica por conta do alerting.py.
    return False


# ── CLI: roda 1 ciclo sob demanda ────────────────────────────────
if __name__ == "__main__":
    import json
    print(json.dumps(run_healthcheck_cycle(), indent=2))