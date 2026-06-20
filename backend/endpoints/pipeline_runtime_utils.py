from datetime import datetime as _dt, timedelta as _td, timezone as _tz
import time
from collections import defaultdict as _defaultdict
from fastapi import HTTPException
from sqlalchemy import text

_pipeline_calls = _defaultdict(list)
_PIPELINE_MAX_CALLS = 5
_PIPELINE_WINDOW = 60

_COOLDOWN_POR_PLANO = {
    "trial": 0,
    "starter": 3600,
    "pro": 1800,
    "agency": 0,
    "ilimitado": 0,
    "beta": 1800,
    "free": 0,
}


def check_rate_limit(user_id: str):
    now = time.time()
    calls = [t for t in _pipeline_calls[user_id] if now - t < _PIPELINE_WINDOW]
    _pipeline_calls[user_id] = calls
    if len(calls) >= _PIPELINE_MAX_CALLS:
        raise HTTPException(429, f"Rate limit: max {_PIPELINE_MAX_CALLS} pipelines/min.")
    calls.append(now)
    _pipeline_calls[user_id] = calls


def check_cooldown(db, tenant_id: int):
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    plano = (row[0] if row else "trial") or "trial"
    cooldown_secs = _COOLDOWN_POR_PLANO.get(plano, 3600)
    if cooldown_secs <= 0:
        return
    last_row = db.execute(
        text("SELECT finished_at FROM pipeline_executions WHERE user_id=:uid AND status='completed' ORDER BY finished_at DESC LIMIT 1"),
        {"uid": tenant_id},
    ).fetchone()
    if not last_row or not last_row[0]:
        last_row = db.execute(
            text("SELECT processado_em FROM leads WHERE user_id=:uid AND status='concluido' ORDER BY processado_em DESC LIMIT 1"),
            {"uid": tenant_id},
        ).fetchone()
    if not last_row or not last_row[0]:
        return
    try:
        last_ts = last_row[0]
        if isinstance(last_ts, str):
            last_ts = _dt.fromisoformat(last_ts)
        elapsed = (_dt.now(_tz.utc) - last_ts).total_seconds() if last_ts.tzinfo else (_dt.now() - last_ts).total_seconds()
    except Exception:
        return
    if elapsed < cooldown_secs:
        restante = int(cooldown_secs - elapsed)
        minutos = restante // 60
        segundos = restante % 60
        fila_count = db.execute(
            text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"),
            {"uid": tenant_id},
        ).scalar() or 0
        detail = {
            "mensagem": f"Aguarde {minutos}min {segundos}s antes de rodar outro pipeline.",
            "cooldown_restante_seg": restante,
            "cooldown_total_seg": cooldown_secs,
            "proximo_em": (_dt.now() + _td(seconds=restante)).isoformat(),
            "plano": plano,
            "leads_na_fila": fila_count,
            "auto_run": fila_count > 0,
            "upsell": f"Upgrade para {'Pro (30min + SDR)' if plano == 'starter' else 'Ilimitado (sem espera + SDR ilimitado)'} para rodar mais rapido."
            if plano in ("starter", "pro")
            else None,
        }
        raise HTTPException(status_code=429, detail=detail)


def emitir_erro_pipeline(adicionar_log_fn, tenant_id, error_code, message="", detalhes=None, **kwargs):
    import json as _json_err

    _TEMPLATES = {
        "RATE_LIMIT": {"severity": "wait", "title": "Servidor de IA ocupado"},
        "NO_LEADS": {"severity": "error", "title": "Nenhum lead qualificado"},
        "LLM_FAIL": {"severity": "error", "title": "Erro na geração do site"},
        "DEPLOY_FAIL": {"severity": "error", "title": "Erro ao publicar o site"},
        "SCRAPER_FAIL": {"severity": "error", "title": "Erro ao buscar negócios"},
        "TIMEOUT": {"severity": "wait", "title": "Geração demorou mais que o esperado"},
        "BRYAN_FAIL": {"severity": "warning", "title": "Site publicado, envio falhou"},
        "HEALTH_FAIL": {"severity": "error", "title": "Site gerado com problemas"},
    }
    tpl = _TEMPLATES.get(error_code, {"severity": "error", "title": "Erro no pipeline"})
    payload = {
        "type": "pipeline_error",
        "error_code": error_code,
        "severity": tpl["severity"],
        "title": tpl["title"],
        "message": message,
        "detalhes": detalhes or [],
        "credito_consumido": kwargs.get("credito_consumido", False),
        **{k: v for k, v in kwargs.items() if k != "credito_consumido"},
    }
    adicionar_log_fn(_json_err.dumps(payload), "PIPELINE_STATUS", user_id=tenant_id)

