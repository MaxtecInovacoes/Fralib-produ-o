"""
Gerenciador de heartbeat para o pipeline.

Fornece um daemon que atualiza periodicamente o worker_heartbeat na tabela jobs
e o last_heartbeat do span atual.
"""
import threading
from typing import Optional, Callable


class HeartbeatManager:
    """
    Gerencia o heartbeat do pipeline.

    Atualiza worker_heartbeat na tabela jobs e span heartbeat periodicamente
    enquanto o pipeline está em execução.
    """

    def __init__(
        self,
        run_id: str,
        tenant_id: int,
        engine,
        fase_counter: list,
        atualizar_heartbeat_span: Optional[Callable] = None,
        interval: float = 15.0,
    ):
        """
        Inicializa o HeartbeatManager.

        Args:
            run_id: ID da execução do pipeline
            tenant_id: ID do tenant
            engine: Engine SQLAlchemy para conexões DB
            fase_counter: Lista com contador de fase [int]
            atualizar_heartbeat_span: Função para atualizar heartbeat do span (opcional)
            interval: Intervalo entre heartbeats em segundos (default: 15)
        """
        self.run_id = run_id
        self.tenant_id = tenant_id
        self.engine = engine
        self.fase_counter = fase_counter
        self.atualizar_heartbeat_span = atualizar_heartbeat_span
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _heartbeat_loop(self):
        """Loop interno do heartbeat - atualiza worker_heartbeat e span heartbeat."""
        from sqlalchemy import text

        while not self._stop_event.is_set():
            try:
                with self.engine.connect() as conn:
                    # Atualizar worker_heartbeat na tabela jobs
                    conn.execute(
                        text("""
                            UPDATE jobs
                            SET worker_heartbeat = NOW()
                            WHERE run_id = :run_id AND tenant_id = :tenant_id
                        """),
                        {"run_id": self.run_id, "tenant_id": self.tenant_id},
                    )
                    # Atualizar last_heartbeat no span atual
                    if self.fase_counter[0] > 0 and self.atualizar_heartbeat_span:
                        self.atualizar_heartbeat_span(self.run_id, self.fase_counter[0])
                    conn.commit()
            except Exception:
                pass
            self._stop_event.wait(self.interval)

    def start(self):
        """Inicia o daemon de heartbeat."""
        if self._thread is not None:
            return  # Já está rodando
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0):
        """
        Para o daemon de heartbeat.

        Args:
            timeout: Tempo máximo de espera pelo fim da thread em segundos
        """
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None


# Funções stand-alone para backward compatibility
def heartbeat_loop(
    run_id: str,
    tenant_id: int,
    engine,
    fase_counter: list,
    atualizar_heartbeat_span: Optional[Callable] = None,
    stop_event: Optional[threading.Event] = None,
    interval: float = 15.0,
):
    """
    Atualiza worker_heartbeat e span heartbeat a cada 15s.

    Esta função é um gerador que usa um Event para sinalizar parada.
    Para usar, passe um threading.Event como stop_event e chame stop_event.set()
    para terminar o loop.

    Args:
        run_id: ID da execução do pipeline
        tenant_id: ID do tenant
        engine: Engine SQLAlchemy para conexões DB
        fase_counter: Lista com contador de fase [int]
        atualizar_heartbeat_span: Função para atualizar heartbeat do span (opcional)
        stop_event: Evento de parada (criado se não fornecido)
        interval: Intervalo entre heartbeats em segundos
    """
    from sqlalchemy import text

    if stop_event is None:
        stop_event = threading.Event()

    while not stop_event.is_set():
        try:
            with engine.connect() as conn:
                # Atualizar worker_heartbeat na tabela jobs
                conn.execute(
                    text("""
                        UPDATE jobs
                        SET worker_heartbeat = NOW()
                        WHERE run_id = :run_id AND tenant_id = :tenant_id
                    """),
                    {"run_id": run_id, "tenant_id": tenant_id},
                )
                # Atualizar last_heartbeat no span atual
                if fase_counter[0] > 0 and atualizar_heartbeat_span:
                    atualizar_heartbeat_span(run_id, fase_counter[0])
                conn.commit()
        except Exception:
            pass
        stop_event.wait(interval)


def parar_heartbeat(
    thread: threading.Thread,
    stop_event: threading.Event,
    timeout: float = 3.0,
):
    """
    Para o daemon de heartbeat.

    Args:
        thread: Thread do heartbeat
        stop_event: Evento de parada
        timeout: Tempo máximo de espera pelo fim da thread em segundos
    """
    stop_event.set()
    if thread is not None:
        thread.join(timeout=timeout)
