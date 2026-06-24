"""Edge cases & production hardening utilities para FraLib (Sprint 9 - v1.12).

Conjunto de helpers defensivos para tornar o sistema resiliente em producao:
- Entradas None/vazias/whitespace/unicode nao quebram codigo
- JSONL corrompido e tolerado (warn + skip)
- DB operations sao retentadas com backoff exponencial
- Tenant access violations sao bloqueadas cedo
- Escrita em disco trata ENOSPC gracefully
- Operacoes longas respeitam timeout (fallback se exceder)

Todos os helpers sao stateless e side-effect free (com excecao de I/O explicito).

Uso:
    from backend.services.edge_cases import (
        safe_normalize_text, safe_jsonl_iter, db_retry,
        assert_tenant_access, safe_write_file, with_timeout,
    )
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import threading
import time
import unicodedata
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, TypeVar

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# TYPES
# ════════════════════════════════════════════════════════════════════

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# ════════════════════════════════════════════════════════════════════
# TEXT NORMALIZATION
# ════════════════════════════════════════════════════════════════════

def safe_normalize_text(s: Optional[str]) -> str:
    """Normaliza texto de forma defensiva (None/vazio/whitespace/unicode safe).

    - None -> string vazia
    - Whitespace only -> string vazia (apos strip)
    - Unicode e normalizado para NFC (compat canonical)
    - Caracteres de controle (< 0x20 exceto tab/newline) sao removidos
    - String sempre e strip()ada nas pontas

    Args:
        s: String de entrada (pode ser None).

    Returns:
        String normalizada (nunca None).

    Example:
        >>> safe_normalize_text(None)
        ''
        >>> safe_normalize_text('   \\n\\t  ')
        ''
        >>> safe_normalize_text('  Café  ')
        'Café'
        >>> safe_normalize_text('Cafe\\u0301')  # NFD decomposed
        'Café'
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        # Tenta converter (ex: bytes, int) sem quebrar
        try:
            s = str(s)
        except Exception:
            return ""
    # Unicode normalize (NFC canonical composition)
    try:
        s = unicodedata.normalize("NFC", s)
    except Exception:
        pass
    # Remove control chars (mantem tab/newline)
    try:
        s = "".join(ch for ch in s if (ch >= " " or ch in "\t\n"))
    except Exception:
        pass
    return s.strip()


# ════════════════════════════════════════════════════════════════════
# JSONL STREAMING
# ════════════════════════════════════════════════════════════════════

def safe_jsonl_iter(path: Any) -> Iterator[dict]:
    """Itera sobre um arquivo JSONL pulando linhas malformadas (com warning).

    - Arquivo inexistente -> nao yield nada (sem erro)
    - Linhas vazias -> puladas silenciosamente
    - Linhas malformadas (JSON invalido) -> warn + skip
    - Linhas que nao sao dict -> warn + skip
    - Encoding latin-1 fallback se UTF-8 falhar

    Args:
        path: caminho do arquivo (str ou Path).

    Yields:
        Dict parseado de cada linha valida.

    Example:
        >>> with open('/tmp/t.jsonl', 'w') as f:
        ...     f.write('{"a":1}\\n')
        ...     f.write('LINHA QUEBRADA\\n')
        ...     f.write('{"b":2}\\n')
        >>> list(safe_jsonl_iter('/tmp/t.jsonl'))
        [{'a': 1}, {'b': 2}]
    """
    p = Path(path)
    if not p.is_file():
        logger.debug(f"[safe_jsonl_iter] arquivo nao existe: {p}")
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        f"[safe_jsonl_iter] linha malformada em {p}:{lineno}: {e}"
                    )
                    continue
                if not isinstance(obj, dict):
                    logger.warning(
                        f"[safe_jsonl_iter] linha {lineno} nao e dict ({type(obj).__name__}), pulando"
                    )
                    continue
                yield obj
    except UnicodeDecodeError:
        # Fallback latin-1 (decodifica qualquer byte)
        logger.debug(f"[safe_jsonl_iter] UTF-8 falhou em {p}, tentando latin-1")
        try:
            with open(p, "r", encoding="latin-1") as f:
                for lineno, raw in enumerate(f, start=1):
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(
                            f"[safe_jsonl_iter] linha malformada {p}:{lineno}: {e}"
                        )
                        continue
                    if not isinstance(obj, dict):
                        continue
                    yield obj
        except Exception as e:
            logger.error(f"[safe_jsonl_iter] falha total em {p}: {e}")
    except Exception as e:
        logger.error(f"[safe_jsonl_iter] erro inesperado em {p}: {e}")


# ════════════════════════════════════════════════════════════════════
# DB RETRY DECORATOR
# ════════════════════════════════════════════════════════════════════

# Excecoes consideradas transientes (rede/lock/IO)
_TRANSIENT_DB_ERRORS: tuple = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def db_retry(max_attempts: int = 3, backoff: float = 1.5) -> Callable[[F], F]:
    """Decorator para retentar operacoes de banco com backoff exponencial.

    Retenta em caso de excecao transiente (ConnectionError/TimeoutError/OSError).
    Apos max_attempts falhas, propaga a ultima excecao.

    Args:
        max_attempts: numero maximo de tentativas (>=1).
        backoff: multiplicador de espera entre tentativas (1.0 = sem backoff).

    Example:
        >>> @db_retry(max_attempts=3, backoff=2.0)
        ... def fetch_user(user_id: int) -> dict:
        ...     return db.query("SELECT * FROM users WHERE id = %s", user_id)

        # Tentativa 1: ConnectionError -> espera 1.0s -> retry
        # Tentativa 2: ConnectionError -> espera 2.0s -> retry
        # Tentativa 3: ConnectionError -> propaga
    """
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser >= 1")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except _TRANSIENT_DB_ERRORS as e:
                    last_exc = e
                    if attempt >= max_attempts:
                        logger.error(
                            f"[db_retry] {func.__name__} falhou apos {max_attempts} tentativas: {e}"
                        )
                        raise
                    wait = (backoff ** (attempt - 1))
                    logger.warning(
                        f"[db_retry] {func.__name__} tentativa {attempt}/{max_attempts} "
                        f"falhou: {e}. Retry em {wait:.2f}s"
                    )
                    time.sleep(wait)
                except Exception as e:
                    # Excecao nao-transiente -> propaga imediatamente
                    logger.debug(f"[db_retry] {func.__name__} erro nao-transiente: {e}")
                    raise
            # Nunca alcancado (loop retorna ou raise), mas type-checker feliz
            if last_exc:
                raise last_exc
            return None
        return wrapper  # type: ignore[return-value]
    return decorator


# ════════════════════════════════════════════════════════════════════
# TENANT ACCESS
# ════════════════════════════════════════════════════════════════════

class TenantAccessError(PermissionError):
    """Excecao quando user tenta acessar recurso de outro tenant."""

    def __init__(self, user_id: Any, resource_user_id: Any, msg: str = "") -> None:
        self.user_id = user_id
        self.resource_user_id = resource_user_id
        default = (
            f"Cross-tenant access blocked: user={user_id} "
            f"tried to access resource owned by user={resource_user_id}"
        )
        super().__init__(msg or default)


def assert_tenant_access(user_id: Any, resource_user_id: Any) -> None:
    """Verifica acesso ao recurso no mesmo tenant (raise se mismatch).

    Use ANTES de qualquer operacao que toca recurso de usuario:
    - SELECT/UPDATE/DELETE em jobs/leads/sites de outro user
    - API endpoints que recebem user_id de outro tenant
    - Background jobs processando tasks de multi-tenant

    Args:
        user_id: ID do usuario autenticado/requesting.
        resource_user_id: ID do dono do recurso.

    Raises:
        TenantAccessError: se user_id != resource_user_id.

    Example:
        >>> def get_job(user_id: int, job_id: int) -> dict:
        ...     job = db.query("SELECT * FROM jobs WHERE id = %s", job_id)
        ...     assert_tenant_access(user_id, job["user_id"])
        ...     return job
    """
    if user_id is None or resource_user_id is None:
        raise TenantAccessError(user_id, resource_user_id, "user_id or resource_user_id is None")
    if str(user_id) != str(resource_user_id):
        raise TenantAccessError(user_id, resource_user_id)


# ════════════════════════════════════════════════════════════════════
# SAFE FILE WRITE
# ════════════════════════════════════════════════════════════════════

# Limite minimo livre em bytes (10MB) para considerar disk-full
_DISK_FULL_MIN_FREE_BYTES = 10 * 1024 * 1024


def safe_write_file(path: Any, content: str, encoding: str = "utf-8") -> bool:
    """Escreve arquivo tratando disk-full e erros de IO (retorna bool).

    - Diretorios pai sao criados automaticamente
    - Verifica espaco livre antes de escrever (min 10MB)
    - Escreve em arquivo temporario e renomeia (atomic write)
    - Em caso de erro, tenta cleanup do temp e retorna False

    Args:
        path: caminho destino (str ou Path).
        content: conteudo string a escrever.
        encoding: encoding (default utf-8).

    Returns:
        True se escreveu com sucesso, False caso contrario.

    Example:
        >>> safe_write_file('/tmp/foo.txt', 'hello')
        True
        >>> safe_write_file('/readonly/bar.txt', 'x')
        False
    """
    p = Path(path)
    try:
        # Garante parent
        p.parent.mkdir(parents=True, exist_ok=True)
        # Checa espaco livre (best-effort)
        try:
            usage = shutil.disk_usage(str(p.parent))
            if usage.free < _DISK_FULL_MIN_FREE_BYTES:
                logger.error(
                    f"[safe_write_file] disk full: {usage.free} bytes livres em {p.parent}"
                )
                return False
        except Exception:
            pass  # Se nao conseguir checar, segue (best-effort)
        # Atomic write (temp + rename)
        tmp = p.with_suffix(p.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)
            return True
        except OSError as e:
            # Cleanup temp se sobrou
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if e.errno == 28 or "No space left" in str(e):  # ENOSPC
                logger.error(f"[safe_write_file] ENOSPC ao escrever {p}")
            else:
                logger.error(f"[safe_write_file] OSError ao escrever {p}: {e}")
            return False
    except PermissionError as e:
        logger.error(f"[safe_write_file] PermissionError em {p}: {e}")
        return False
    except Exception as e:
        logger.error(f"[safe_write_file] erro inesperado em {p}: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
# TIMEOUT DECORATOR
# ════════════════════════════════════════════════════════════════════

class TimeoutError_(Exception):  # noqa: N801 (compat com built-in)
    """Excecao levantada quando timeout e excedido."""

    def __init__(self, seconds: float, func_name: str) -> None:
        self.seconds = seconds
        self.func_name = func_name
        super().__init__(f"Timeout: {func_name} excedeu {seconds}s")


def with_timeout(seconds: float = 30.0, fallback: Any = None) -> Callable[[F], F]:
    """Decorator que aborta funcao apos `seconds` (retorna fallback se exceder).

    Implementacao: roda em thread daemon + join(timeout).
    - Se completar a tempo -> retorna resultado
    - Se exceder -> retorna fallback (NAO tenta matar thread; Python nao permite)
    - NOTA: para CPU-bound work, timeout nao e 100% garantido (thread continua rodando)

    Args:
        seconds: tempo maximo em segundos.
        fallback: valor retornado em caso de timeout.

    Example:
        >>> @with_timeout(seconds=2.0, fallback={"status": "slow"})
        ... def slow_op() -> dict:
        ...     time.sleep(5)
        ...     return {"status": "ok"}
        >>> slow_op()
        {'status': 'slow'}
    """
    if seconds <= 0:
        raise ValueError("seconds deve ser > 0")

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result_box: dict = {"value": None, "exc": None, "done": False}

            def runner() -> None:
                try:
                    result_box["value"] = func(*args, **kwargs)
                except BaseException as e:  # noqa: BLE001 (captura tudo do runner)
                    result_box["exc"] = e
                finally:
                    result_box["done"] = True

            t = threading.Thread(target=runner, daemon=True, name=f"timeout-{func.__name__}")
            t.start()
            t.join(timeout=seconds)
            if not result_box["done"]:
                logger.warning(
                    f"[with_timeout] {func.__name__} excedeu {seconds}s, retornando fallback"
                )
                return fallback
            if result_box["exc"] is not None:
                raise result_box["exc"]
            return result_box["value"]
        return wrapper  # type: ignore[return-value]
    return decorator


# ════════════════════════════════════════════════════════════════════
# HELPERS AUXILIARES (idempotencia basica)
# ════════════════════════════════════════════════════════════════════

def is_idempotent_action(action_key: str, ttl_seconds: int = 300) -> bool:
    """Verifica se action_key foi executada nos ultimos ttl_seconds (idempotencia basica).

    Armazena em arquivo de lock local (thread-safe via arquivo + mtime).
    NAO e distribuido (para multi-instance, use Redis/DB).

    Args:
        action_key: chave unica da acao (ex: 'job:123:render:openui').
        ttl_seconds: tempo de retencao do lock.

    Returns:
        True se JA foi executada (action deve ser pulada),
        False se pode executar (action sera registrada).

    Example:
        >>> if is_idempotent_action(f'job:{job_id}:build'):
        ...     return  # ja foi feito
        ... do_build()
        ... register_action(f'job:{job_id}:build')  # registra
    """
    lock_dir = Path(os.getenv("FRALIB_IDEMPOTENCY_DIR", "/tmp/fralib_idempotency"))
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{action_key.replace('/', '_').replace(':', '_')}.lock"
    try:
        if lock_path.exists():
            age = time.time() - lock_path.stat().st_mtime
            if age < ttl_seconds:
                return True  # ja executado, ainda dentro do TTL
        return False
    except Exception:
        return False


def register_action(action_key: str) -> bool:
    """Registra action_key como executada (com idempotency TTL).

    Args:
        action_key: mesma chave usada em is_idempotent_action.

    Returns:
        True se registrou, False se falhou.

    Example:
        >>> if is_idempotent_action('job:1:build'):
        ...     return
        >>> do_build()
        >>> register_action('job:1:build')
        True
    """
    lock_dir = Path(os.getenv("FRALIB_IDEMPOTENCY_DIR", "/tmp/fralib_idempotency"))
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{action_key.replace('/', '_').replace(':', '_')}.lock"
    try:
        lock_path.touch()
        return True
    except Exception as e:
        logger.warning(f"[register_action] falha ao registrar {action_key}: {e}")
        return False