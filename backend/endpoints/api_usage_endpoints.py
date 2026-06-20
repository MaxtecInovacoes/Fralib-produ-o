from fastapi import APIRouter, Depends
from backend.core.auth import get_current_user
import os, requests
from datetime import datetime, timezone
from backend.core.database import engine
from sqlalchemy import text

router = APIRouter(prefix='/api/usage', tags=['usage'])

API_KEY  = os.getenv('ANTHROPIC_API_KEY', '')
BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud')


_usage_cache = {'data': None, 'ts': 0}

def _fetch_limits():
    """Faz chamada minima ao proxy e retorna headers de rate limit. Cache de 60s."""
    import time as _time
    # Retornar cache se < 60 segundos
    if _usage_cache['data'] and (_time.time() - _usage_cache['ts']) < 60:
        return _usage_cache['data']

    url = f'{BASE_URL}/v1/messages'
    headers = {
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'claude-haiku-4-5',
        'max_tokens': 1,
        'messages': [{'role': 'user', 'content': 'x'}],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    h = resp.headers

    # Se a API retornou 429, extrair info de reset e retornar como limite esgotado
    if resp.status_code == 429:
        reset_at = h.get('Anthropic-Ratelimit-Input-Tokens-Reset', '')
        reset_secs = 60
        if reset_at:
            try:
                from datetime import timezone
                _reset_dt = datetime.fromisoformat(reset_at.replace('Z', '+00:00'))
                reset_secs = max(0, int((_reset_dt - datetime.now(timezone.utc)).total_seconds()))
            except Exception:
                reset_secs = 60
        reset_min = max(1, reset_secs // 60)
        result_429 = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reset_at': reset_at,
            'input':    {'limit': int(h.get('Anthropic-Ratelimit-Input-Tokens-Limit', 200000)), 'remaining': 0, 'used_pct': 100},
            'output':   {'limit': int(h.get('Anthropic-Ratelimit-Output-Tokens-Limit', 128000)), 'remaining': 0, 'used_pct': 100},
            'requests': {'limit': int(h.get('Anthropic-Ratelimit-Requests-Limit', 4000)), 'remaining': 0, 'used_pct': 100},
            'pipelines_available': 0,
            'alert': {'level': 'rate_limit', 'msg': f'Limite atingido! Volte daqui {reset_min} minuto(s).'},
        }
        import time as _time
        _usage_cache['data'] = result_429
        _usage_cache['ts'] = _time.time()
        return result_429

    def _int(key): return int(h.get(key, 0))

    input_limit      = _int('Anthropic-Ratelimit-Input-Tokens-Limit')
    input_remaining  = _int('Anthropic-Ratelimit-Input-Tokens-Remaining')
    output_limit     = _int('Anthropic-Ratelimit-Output-Tokens-Limit')
    output_remaining = _int('Anthropic-Ratelimit-Output-Tokens-Remaining')
    req_limit        = _int('Anthropic-Ratelimit-Requests-Limit')
    req_remaining    = _int('Anthropic-Ratelimit-Requests-Remaining')
    reset_at         = h.get('Anthropic-Ratelimit-Input-Tokens-Reset', '')

    inp_pct = max(0, min(100, round((1 - input_remaining  / input_limit)  * 100, 1))) if input_limit  else 0
    out_pct = max(0, min(100, round((1 - output_remaining / output_limit) * 100, 1))) if output_limit else 0
    req_pct = max(0, min(100, round((1 - req_remaining    / req_limit)    * 100, 1))) if req_limit    else 0

    # Clamp remaining para não ser negativo (proxy pode retornar > limit no reset)
    input_remaining  = max(0, input_remaining)
    output_remaining = max(0, output_remaining)
    req_remaining    = max(0, req_remaining)
    pipelines = max(0, min(input_remaining // 15000, output_remaining // 5000))

    max_pct = max(inp_pct, out_pct)
    if max_pct >= 80:
        alert = {'level': 'danger',  'msg': 'Limite quase esgotado! Aguarde o reset.'}
    elif max_pct >= 50:
        alert = {'level': 'warning', 'msg': 'Mais de 50% consumido nesta janela.'}
    else:
        alert = {'level': 'ok',      'msg': 'Limite saudavel.'}

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'reset_at': reset_at,
        'input':    {'limit': input_limit,  'remaining': input_remaining,  'used_pct': inp_pct},
        'output':   {'limit': output_limit, 'remaining': output_remaining, 'used_pct': out_pct},
        'requests': {'limit': req_limit,    'remaining': req_remaining,    'used_pct': req_pct},
        'pipelines_available': pipelines,
        'alert': alert,
    }
    import time as _time
    _usage_cache['data'] = result
    _usage_cache['ts'] = _time.time()
    return result


@router.get('/status')
async def api_usage_status(usuario: dict = Depends(get_current_user)):
    """Retorna status atual de uso da API Anthropic em tempo real."""
    if usuario.get('role') not in ('admin', 'superadmin'):
        from fastapi import HTTPException
        raise HTTPException(403, 'Apenas admins podem ver uso da API')
    data = _fetch_limits()
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO api_usage_snapshots
                (input_limit, input_remaining, input_reset,
                 output_limit, output_remaining, output_reset,
                 req_limit, req_remaining, req_reset)
                VALUES (:il,:ir,:irst,:ol,:or_,:orst,:rl,:rr,:rrst)
            """), {
                'il': data['input']['limit'],    'ir': data['input']['remaining'],    'irst': data['reset_at'],
                'ol': data['output']['limit'],   'or_': data['output']['remaining'],  'orst': data['reset_at'],
                'rl': data['requests']['limit'], 'rr': data['requests']['remaining'], 'rrst': data['reset_at'],
            })
            conn.commit()
    except Exception:
        pass
    return data


@router.get('/history')
async def api_usage_history(usuario: dict = Depends(get_current_user)):
    """Retorna historico de snapshots das ultimas 24h."""
    if usuario.get('role') not in ('admin', 'superadmin'):
        from fastapi import HTTPException
        raise HTTPException(403, 'Apenas admins')
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT captured_at, input_limit, input_remaining,
                       output_limit, output_remaining, req_limit, req_remaining
                FROM api_usage_snapshots
                WHERE captured_at > NOW() - INTERVAL '24 hours'
                ORDER BY captured_at DESC
                LIMIT 100
            """)).fetchall()
        return [{
            'time':       str(r[0]),
            'input_pct':  round((1 - r[2]/r[1])*100, 1) if r[1] else 0,
            'output_pct': round((1 - r[4]/r[3])*100, 1) if r[3] else 0,
            'req_pct':    round((1 - r[6]/r[5])*100, 1) if r[5] else 0,
        } for r in rows]
    except Exception as e:
        return {'error': str(e)}
