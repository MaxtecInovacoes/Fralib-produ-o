from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
import asyncio
import json
import os
import select
import jwt
from datetime import datetime
from collections import deque, defaultdict

from backend.endpoints.auth_endpoints import get_current_user

router = APIRouter(prefix="/api/logs", tags=["logs"])

# Flag de shutdown para cancelar SSE streams
_shutting_down = False

def _shutdown_sse():
    """Chamado no shutdown do servidor para encerrar SSE streams."""
    global _shutting_down
    _shutting_down = True
    # Fechar conexão persistente do notify
    global _notify_conn
    if _notify_conn:
        try:
            _notify_conn.close()
        except Exception:
            pass
        _notify_conn = None
    print("[SSE] Shutdown: flag ativado, conexões SSE vão encerrar")

# Fallback em memória por user_id
# { user_id: deque(maxlen=500) }
_log_queues: dict = defaultdict(lambda: deque(maxlen=500))
# Canal global (admin / broadcast sem user_id)
log_queue = deque(maxlen=500)

# ===== CONFIGURAÇÃO POSTGRESQL =====

def _get_pg_dsn() -> str:
    """Retorna DSN psycopg2 a partir do DATABASE_URL do ambiente."""
    url = os.getenv("DATABASE_URL", "")
    return url

# Conexão persistente para pg_notify — evita abrir/fechar a cada log
_notify_conn = None
_notify_lock = None

def _get_notify_conn():
    """Retorna conexão persistente para pg_notify, reconectando se necessário."""
    global _notify_conn, _notify_lock
    import threading
    if _notify_lock is None:
        _notify_lock = threading.Lock()
    import psycopg2
    dsn = _get_pg_dsn()
    if not dsn:
        return None
    try:
        if _notify_conn is None or _notify_conn.closed:
            _notify_conn = psycopg2.connect(dsn)
            _notify_conn.autocommit = True
        # Testar se conexão ainda está viva
        _notify_conn.cursor().execute("SELECT 1")
        return _notify_conn
    except Exception:
        try:
            _notify_conn = psycopg2.connect(dsn)
            _notify_conn.autocommit = True
            return _notify_conn
        except Exception as e:
            print(f"[SSE] pg_notify reconexão falhou: {e}")
            return None


def _pg_notify(mensagem: str, tipo: str, user_id=None) -> bool:
    """
    Publica log via pg_notify no canal do usuário.
    Usa conexão persistente para evitar overhead de connect/close a cada chamada.
    Canal: fralib_logs_{user_id} se user_id, senão fralib_logs (broadcast).
    Retorna True se conseguiu, False se falhou.
    """
    global _notify_lock
    import threading
    if _notify_lock is None:
        _notify_lock = threading.Lock()
    try:
        evento = _TIPO_EVENTO.get(tipo.lower(), "INFO")
        log_entry = {
            "evento":   evento,
            "mensagem": mensagem,
            "ts":       datetime.now().strftime("%H:%M:%S"),
        }
        payload = json.dumps(log_entry, ensure_ascii=False)
        payload_safe = payload.replace("'", "''")[:7900]
        canal = f"fralib_logs_{user_id}" if user_id else "fralib_logs"
        with _notify_lock:
            conn = _get_notify_conn()
            if not conn:
                return False
            with conn.cursor() as cur:
                cur.execute('SELECT pg_notify(%s, %s)', (canal, payload_safe))
        return True
    except Exception as e:
        print(f"[SSE] pg_notify erro: {e}")
        global _notify_conn
        _notify_conn = None  # forçar reconexão na próxima chamada
        return False


# ===== VALIDAÇÃO JWT =====

def _validar_token_sse(token: str) -> dict:
    """Valida JWT e retorna payload. Lança HTTPException se inválido."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY não configurado")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# ===== STREAM SSE =====

@router.get("/stream")
async def stream_logs(token: str = Query(..., description="JWT token para autenticação")):
    jwt_payload = _validar_token_sse(token)
    raw_sub = jwt_payload.get("sub", "")
    try:
        user_id = str(int(raw_sub)) if raw_sub != "" else ""
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido")

    async def event_generator():
        # Canal privado do usuário (user_id já validado como inteiro acima — seguro p/ LISTEN)
        canal = f"fralib_logs_{user_id}" if user_id else "fralib_logs"

        pg_conn = None
        use_pg = False
        try:
            import psycopg2
            dsn = os.getenv("DATABASE_URL", "")
            pg_conn = psycopg2.connect(dsn)
            pg_conn.autocommit = True
            with pg_conn.cursor() as cur:
                cur.execute(f"LISTEN {canal}")
            use_pg = True
            print(f"[SSE] LISTEN {canal} ativo (user_id={user_id})")
        except Exception as e:
            print(f"[SSE] PostgreSQL indisponível: {e} — usando fallback deque")
            use_pg = False

        try:
            while not _shutting_down:
                if use_pg and pg_conn:
                    loop = asyncio.get_running_loop()
                    try:
                        notif = await loop.run_in_executor(
                            None, _wait_notify, pg_conn, 0.5
                        )
                        if notif:
                            yield "data: " + notif + "\n\n"
                        else:
                            yield ": heartbeat\n\n"
                    except Exception as e:
                        print(f"[SSE] Erro no LISTEN: {e} — voltando para deque")
                        use_pg = False
                        try:
                            pg_conn.close()
                        except Exception:
                            pass
                        pg_conn = None
                else:
                    # Fallback: polling da deque do usuário
                    q = _log_queues[user_id] if user_id else log_queue
                    if q:
                        log = q.popleft()
                        payload = json.dumps(log, ensure_ascii=False)
                        yield "data: " + payload + "\n\n"
                    else:
                        yield ": heartbeat\n\n"
                    await asyncio.sleep(0.3)
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if pg_conn:
                try:
                    pg_conn.close()
                except Exception:
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


def _wait_notify(conn, timeout: float):
    """
    Aguarda notificação PostgreSQL usando select().
    Retorna o payload da notificação ou None se timeout.
    Executado em thread separada via run_in_executor.
    """
    if select.select([conn], [], [], timeout)[0]:
        conn.poll()
        if conn.notifies:
            notif = conn.notifies.pop(0)
            return notif.payload
    return None


# ===== MAPEAMENTO DE TIPOS =====

_TIPO_EVENTO = {
    "info":     "INFO",
    "success":  "SUCCESS",
    "warning":  "WARNING",
    "error":    "ERROR",
    "leads":    "LEADS",
    "caio":     "CAIO",
    "pipeline": "PIPELINE_STATUS",
    "rate_limit": "RATE_LIMIT",
}


# ===== ADICIONAR LOG =====

def adicionar_log(mensagem: str, tipo: str = "info", user_id=None):
    """
    Publica log via pg_notify no canal privado do usuário.
    user_id: int ou str do usuário dono do pipeline.
             Se None, publica no canal global (broadcast admin).
    Fallback automático para deque em memória se PostgreSQL falhar.
    Assinatura compatível com versão anterior (user_id é opcional).
    """
    evento = _TIPO_EVENTO.get(tipo.lower(), "INFO")
    log_entry = {
        "evento":   evento,
        "mensagem": mensagem,
        "ts":       datetime.now().strftime("%H:%M:%S"),
    }

    if not _pg_notify(mensagem, tipo, user_id):
        # Fallback: deque em memória por user_id
        if user_id:
            _log_queues[str(user_id)].append(log_entry)
        else:
            log_queue.append(log_entry)


# ===== ENDPOINTS AUXILIARES =====

@router.post("/test")
async def test_log(payload: dict, usuario: dict = Depends(get_current_user)):
    if usuario.get("role") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Acesso restrito")
    user_id = payload.get("user_id") or usuario["id"]
    adicionar_log(payload.get("mensagem", "teste"), payload.get("tipo", "info"), user_id)
    return {"ok": True}


@router.get("/debug")
async def debug_queue(usuario: dict = Depends(get_current_user)):
    if usuario.get("role") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Acesso restrito")
    import sys
    mods = {k: v.__file__ for k, v in sys.modules.items() if "sse_endpoint" in k}
    return {
        "queue_id":       id(log_queue),
        "queue_size":     len(log_queue),
        "queue_contents": list(log_queue)[:5],
        "modules":        mods,
        "pg_dsn_set":     bool(os.getenv("DATABASE_URL")),
        "user_queues":    {k: len(v) for k, v in _log_queues.items()},
    }
