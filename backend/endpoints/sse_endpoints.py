from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime

router = APIRouter(prefix="/api/logs", tags=["sse"])

# Fila global de logs
log_queue = []

@router.get("/stream")
async def stream_logs():
    async def event_generator():
        try:
            while True:
                if log_queue:
                    log = log_queue.pop(0)
                    yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
                else:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
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

# Mapa tipo -> evento (formato que o frontend espera)
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
    if len(log_queue) > 200:
        log_queue.pop(0)
