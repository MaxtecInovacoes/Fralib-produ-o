from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime
from collections import deque

router = APIRouter(prefix="/api/logs", tags=["sse"])

log_queue = deque(maxlen=500)

@router.get("/stream")
async def stream_logs():
    async def event_generator():
        try:
            while True:
                if log_queue:
                    log = log_queue.popleft()
                    payload = json.dumps(log, ensure_ascii=False)
                    yield 'data: ' + payload + '\n\n'
                else:
                    yield ': heartbeat\n\n'
                await asyncio.sleep(0.3)
        except (asyncio.CancelledError, GeneratorExit):
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

_TIPO_EVENTO = {
    "info":     "INFO",
    "success":  "SUCCESS",
    "warning":  "WARNING",
    "error":    "ERROR",
    "leads":    "LEADS",
    "caio":     "CAIO",
    "pipeline": "PIPELINE_STATUS",
}

def adicionar_log(mensagem: str, tipo: str = "info"):
    evento = _TIPO_EVENTO.get(tipo.lower(), "INFO")
    log_queue.append({
        "evento":   evento,
        "mensagem": mensagem,
        "ts":       datetime.now().strftime("%H:%M:%S"),
    })

@router.post('/test')
async def test_log(payload: dict):
    adicionar_log(payload.get('mensagem', 'teste'), payload.get('tipo', 'info'))
    return {'ok': True, 'queue_size': len(log_queue)}

@router.get('/debug')
async def debug_queue():
    import sys
    mods = {k: v.__file__ for k, v in sys.modules.items() if 'sse_endpoint' in k}
    return {
        'queue_id': id(log_queue),
        'queue_size': len(log_queue),
        'queue_contents': list(log_queue)[:5],
        'modules': mods
    }
