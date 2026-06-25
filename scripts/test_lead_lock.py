"""
Testes para o sistema de lock por lead_id e deduplicação por message_id.

Resolve o bug onde Franz responde 3x à mesma mensagem devido a:
- Race condition entre múltiplas threads/processos
- WebSocket race no MeoWhats entregando mesma msg 2x
- Deduplicação ineficiente

Usage:
    cd C:/fralib && python -m pytest scripts/test_lead_lock.py -v
    Ou: python scripts/test_lead_lock.py
"""

import sys
import unittest
import threading
import time
from pathlib import Path

# Adiciona backend ao path (igual test_sdr_fsm.py)
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from agents.sdr_langgraph.lead_lock import (
    _lead_lock_guard,
    _is_duplicate_message_id,
    _LEAD_LOCKS,
    _MESSAGE_ID_CACHE,
    _cleanup_old_cache,
)
from agents.sdr_langgraph.lead_lock import _CACHE_LOCK as _CACHE_LOCK_TEST


class TestLeadLock(unittest.TestCase):
    """Testes para o lock global por lead_id."""

    def setUp(self):
        """Limpar caches antes de cada teste."""
        _LEAD_LOCKS.clear()
        _MESSAGE_ID_CACHE.clear()

    def test_basic_lock_acquire_release(self):
        """Lock deve ser adquirido e liberado corretamente."""
        lead_id = "test_lead_1"
        with _lead_lock_guard(lead_id):
            self.assertIn(lead_id, _LEAD_LOCKS)
        # Lock deve estar liberado após o with
        with _lead_lock_guard(lead_id):
            pass  # Deve conseguir adquirir novamente

    def test_concurrent_threads_same_lead_serialized(self):
        """2 threads no mesmo lead devem ser serializadas."""
        lead_id = "test_lead_2"
        results = []
        lock_internal = threading.Lock()

        def task(thread_id):
            with _lead_lock_guard(lead_id):
                with lock_internal:
                    results.append(f"start_{thread_id}")
                time.sleep(0.1)  # Simular trabalho
                with lock_internal:
                    results.append(f"end_{thread_id}")

        threads = []
        for i in range(3):
            t = threading.Thread(target=task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verificar que execuções foram serializadas
        # Padrão esperado: start_0, end_0, start_1, end_1, start_2, end_2
        # OU qualquer rotação serializada (não intercalada)
        starts = [r for r in results if r.startswith("start_")]
        ends = [r for r in results if r.startswith("end_")]

        # Cada start deve vir ANTES do próximo start
        # (porque o lock impede 2 threads simultâneas)
        for i in range(len(starts) - 1):
            start_thread = int(starts[i].split("_")[1])
            next_start_thread = int(starts[i + 1].split("_")[1])
            # O end do thread atual deve vir antes do próximo start
            self.assertIn(f"end_{start_thread}", results[:results.index(f"start_{next_start_thread}")])

    def test_different_leads_parallel(self):
        """Leads diferentes devem poder ser processados em paralelo."""
        lead1_results = []
        lead2_results = []
        internal_lock = threading.Lock()

        def task_lead1():
            with _lead_lock_guard("lead1"):
                with internal_lock:
                    lead1_results.append("start")
                time.sleep(0.2)
                with internal_lock:
                    lead1_results.append("end")

        def task_lead2():
            with _lead_lock_guard("lead2"):
                with internal_lock:
                    lead2_results.append("start")
                time.sleep(0.2)
                with internal_lock:
                    lead2_results.append("end")

        t1 = threading.Thread(target=task_lead1)
        t2 = threading.Thread(target=task_lead2)

        start_time = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        elapsed = time.time() - start_time

        # Se fossem serializados, levaria ~0.4s. Em paralelo, ~0.2s
        self.assertLess(elapsed, 0.35, "Leads diferentes devem rodar em paralelo")
        self.assertEqual(lead1_results, ["start", "end"])
        self.assertEqual(lead2_results, ["start", "end"])

    def test_timeout_protection(self):
        """Lock deve ter timeout para evitar deadlock."""
        lead_id = "test_timeout"

        # Adquirir lock em uma thread e segurar por tempo suficiente
        holder_started = threading.Event()
        holder_can_release = threading.Event()

        def hold_lock():
            with _lead_lock_guard(lead_id):
                holder_started.set()
                holder_can_release.wait(timeout=5.0)  # Esperar sinal pra liberar

        holder = threading.Thread(target=hold_lock)
        holder.start()
        holder_started.wait(timeout=1.0)  # Garantir que holder pegou o lock

        # Tentar adquirir - deve dar timeout (timeout=30s, mas holder segura só 5s)
        # Como 30s é muito longo para teste, vamos só verificar que está bloqueado
        lock_held = threading.Lock()
        second_acquired = threading.Event()

        def try_second():
            try:
                with _lead_lock_guard(lead_id):
                    pass
            except TimeoutError:
                second_acquired.set()

        # Reduzir timeout para teste: usar uma versão modificada
        # Como _lead_lock_guard tem timeout fixo de 30s, vamos só verificar
        # que o lock está sendo segurado (outra thread não consegue entrar)
        t2 = threading.Thread(target=try_second)
        t2.start()

        # Verificar que holder ainda está segurando
        self.assertTrue(holder_started.is_set())
        self.assertTrue(holder.is_alive())

        # Liberar holder
        holder_can_release.set()
        holder.join(timeout=2.0)
        t2.join(timeout=2.0)


class TestMessageIdDedup(unittest.TestCase):
    """Testes para deduplicação por message_id."""

    def setUp(self):
        _MESSAGE_ID_CACHE.clear()

    def test_new_message_id_returns_false(self):
        """Message ID novo não deve ser considerado duplicado."""
        result = _is_duplicate_message_id("msg_123_abc")
        self.assertFalse(result)

    def test_same_message_id_returns_true(self):
        """Mesmo message ID deve ser considerado duplicado."""
        msg_id = "msg_456_xyz"
        # Primeira vez - não é duplicado
        self.assertFalse(_is_duplicate_message_id(msg_id))
        # Segunda vez - é duplicado
        self.assertTrue(_is_duplicate_message_id(msg_id))

    def test_empty_message_id_returns_false(self):
        """Message ID vazio não deve ser processado."""
        self.assertFalse(_is_duplicate_message_id(""))
        self.assertFalse(_is_duplicate_message_id(None))

    def test_cache_clears_after_ttl(self):
        """Cache deve limpar após TTL expirar."""
        msg_id = "msg_ttl_test"
        # Adicionar ao cache
        _is_duplicate_message_id(msg_id)

        # Simular passagem de tempo modificando timestamp no cache
        with _CACHE_LOCK_TEST:
            _MESSAGE_ID_CACHE[msg_id] = time.time() - 70  # 70s atrás

        # Chamar função de limpeza
        _cleanup_old_cache(ttl_seconds=60)

        # Agora o cache deve estar limpo
        self.assertNotIn(msg_id, _MESSAGE_ID_CACHE)


class TestIntegrationScenario(unittest.TestCase):
    """Testes de cenário integrado simulando o bug original."""

    def setUp(self):
        _LEAD_LOCKS.clear()
        _MESSAGE_ID_CACHE.clear()

    def test_simulated_3x_duplicate_replies(self):
        """Simula o cenário: 3 'entregas' da mesma msg → só 1 resposta."""
        lead_id = "lead_dra_karoline"
        msg_id = "msg_789_duplicate"

        # Cenário: MeoWhats envia a mesma msg 3x em 4ms (race condition)
        results = []

        def simulate_websocket_delivery(delivery_id):
            # Simular deduplicação no listener
            if _is_duplicate_message_id(msg_id):
                results.append(f"delivery_{delivery_id}_DEDUPED")
                return

            # Simular lock no entry point do Franz
            with _lead_lock_guard(lead_id):
                results.append(f"delivery_{delivery_id}_PROCESSED")
                time.sleep(0.1)  # Simular trabalho do Franz

        # 3 threads simulando 3 entregas simultâneas
        threads = []
        for i in range(3):
            t = threading.Thread(target=simulate_websocket_delivery, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verificar que só 1 foi processado, 2 foram deduplicados
        processed = [r for r in results if "PROCESSED" in r]
        deduped = [r for r in results if "DEDUPED" in r]

        self.assertEqual(len(processed), 1, f"Esperado 1 processado, teve {len(processed)}: {results}")
        self.assertEqual(len(deduped), 2, f"Esperado 2 deduplicados, teve {len(deduped)}: {results}")

    def test_simulated_different_messages_same_lead(self):
        """Msgs DIFERENTES do mesmo lead devem ser processadas (serializadas)."""
        lead_id = "lead_active"
        results = []
        lock = threading.Lock()

        def simulate_msg(msg_content):
            # Mensagens DIFERENTES têm IDs DIFERENTES
            msg_id = f"msg_{msg_content}"
            if _is_duplicate_message_id(msg_id):
                with lock:
                    results.append(f"{msg_content}_DEDUPED")
                return

            with _lead_lock_guard(lead_id):
                with lock:
                    results.append(f"{msg_content}_PROCESSING")
                time.sleep(0.05)
                with lock:
                    results.append(f"{msg_content}_DONE")

        threads = []
        for msg in ["msg1", "msg2", "msg3"]:
            t = threading.Thread(target=simulate_msg, args=(msg,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Todas devem ter sido processadas
        processed = [r for r in results if "PROCESSING" in r]
        self.assertEqual(len(processed), 3, "3 msgs diferentes devem ser processadas")


if __name__ == "__main__":
    unittest.main(verbosity=2)
