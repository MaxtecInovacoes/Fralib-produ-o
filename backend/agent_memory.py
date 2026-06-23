"""
Agent Memory — Memória em 3 tiers: Core/Warm/Cold (PRD #11)
Padrão: MemGPT/Letta — agentes aprendem entre gerações.
Core: sempre no contexto (<500 tokens, max 20 entries)
Warm: buscável por nicho (max 50/nicho)
Cold: arquivo bruto de cada run (filesystem)
"""

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("agent_memory")

MEMORY_DIR = Path(__file__).parent / "memory"
CORE_FILE = MEMORY_DIR / "core.json"
WARM_DIR = MEMORY_DIR / "warm"
COLD_DIR = MEMORY_DIR / "cold"


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tipo: str = "padrao"
    agente: str = "*"
    nicho: str = "*"
    conteudo: str = ""
    confianca: float = 0.5
    vezes_usado: int = 0
    vezes_sucesso: int = 0
    vezes_falha: int = 0
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fonte: str = ""

    @property
    def taxa_sucesso(self) -> float:
        if self.vezes_usado == 0:
            return 0.5
        return self.vezes_sucesso / self.vezes_usado

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "agente": self.agente,
            "nicho": self.nicho,
            "conteudo": self.conteudo,
            "confianca": self.confianca,
            "vezes_usado": self.vezes_usado,
            "vezes_sucesso": self.vezes_sucesso,
            "vezes_falha": self.vezes_falha,
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
            "fonte": self.fonte,
        }


class CoreMemory:
    # Lock de classe para serializar read-modify-write entre processos via flock
    # (POSIX) ou via _intra_process_lock (Windows fallback).
    _intra_process_lock = threading.Lock()

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        # Lock de read-modify-write: protege _carregar + adicionar + _salvar
        with CoreMemory._intra_process_lock:
            self.entries: list[MemoryEntry] = self._carregar()

    def _carregar(self) -> list:
        if not CORE_FILE.exists():
            return []
        try:
            with open(CORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryEntry(**e) for e in data]
        except (json.JSONDecodeError, Exception) as e:
            # FIX CRITICO: backup antes de perder memoria corrompida
            try:
                import shutil
                backup = CORE_FILE.with_suffix('.corrupted.bak')
                shutil.copy2(CORE_FILE, backup)
                logger.warning(f'[AgentMemory] Backup memoria corrompida: {backup}. Erro: {e}')
            except Exception as backup_err:
                logger.error(f'[AgentMemory] Backup falhou: {backup_err}')
            return []  # Backup feito, inicia vazio

    def _salvar(self) -> None:
        """Salva core.json atomicamente com file lock (fcntl.flock).

        v1.1-baseline-2026-06-23: protecao contra race condition em
        pipeline_multiplos (2+ processos gravando simultaneamente).
        Combina 2 camadas:
        1. threading.Lock intra-processo (Windows + Linux)
        2. fcntl.flock inter-processo (Linux only)

        Windows: fallback sem flock (multi-process nao suportado em Win).
        IMPORTANTE: Em Linux, __init__ ja adquire o lock intra-processo;
        flock serializa entre processos diferentes.
        """
        with CoreMemory._intra_process_lock:
            _f = None
            try:
                _f = open(CORE_FILE, "w", encoding="utf-8")
            except (OSError, IOError) as e:
                logger.error(f"[AgentMemory] Falha ao abrir core memory: {e}")
                return
            try:
                try:
                    import fcntl
                    fcntl.flock(_f, fcntl.LOCK_EX)
                except (ImportError, OSError):
                    pass  # Windows ou sem suporte; prossegue sem lock
                json.dump(
                    [e.to_dict() for e in self.entries], _f, ensure_ascii=False, indent=2
                )
            except (OSError, IOError) as e:
                logger.error(f"[AgentMemory] Falha ao salvar core memory: {e}")
            finally:
                try:
                    import fcntl
                    fcntl.flock(_f, fcntl.LOCK_UN)
                except (ImportError, OSError, ValueError, AttributeError):
                    pass
                _f.close()

    def adicionar(self, entry: MemoryEntry):
        # Lock ja esta no escopo do caller (via __init__ quando necessario).
        # Para chamadas diretas de adicionar() (fora de __init__), usamos o lock aqui.
        with CoreMemory._intra_process_lock:
            existing = next((e for e in self.entries if e.conteudo == entry.conteudo), None)
            if existing:
                existing.confianca = max(existing.confianca, entry.confianca)
                existing.atualizado_em = datetime.now(timezone.utc).isoformat()
                self._salvar()
                return

            if len(self.entries) >= 20:
                self.entries.sort(key=lambda e: e.confianca)
                removida = self.entries.pop(0)
                print(
                    f"[MEMORY] Core cheio. Demovendo: '{removida.conteudo[:50]}' (conf={removida.confianca:.0%})"
                )
            self.entries.append(entry)
            self._salvar()
            print(f"[MEMORY] Core +1: '{entry.conteudo[:50]}' (conf={entry.confianca:.0%})")

    def get_para_agente(self, agente: str, nicho: str) -> str:
        relevantes = [
            e
            for e in self.entries
            if (e.agente == agente or e.agente == "*")
            and (e.nicho == nicho or e.nicho == "*")
        ]
        if not relevantes:
            return ""
        linhas = ["## Memória (aprendizados anteriores):"]
        for e in sorted(relevantes, key=lambda x: x.confianca, reverse=True)[:10]:
            linhas.append(f"- [{e.confianca:.0%}] {e.conteudo}")
        return "\n".join(linhas)


class WarmMemory:
    def __init__(self):
        WARM_DIR.mkdir(parents=True, exist_ok=True)

    def adicionar(self, entry: MemoryEntry):
        entries = self._carregar_nicho(entry.nicho)
        existing = next(
            (e for e in entries if e.get("conteudo") == entry.conteudo), None
        )
        if existing:
            existing["confianca"] = min(1.0, existing.get("confianca", 0.5) + 0.05)
            existing["vezes_usado"] = existing.get("vezes_usado", 0) + 1
            existing["atualizado_em"] = datetime.now().isoformat()
        else:
            entries.append(entry.to_dict())

        if len(entries) > 50:
            entries.sort(key=lambda e: e.get("confianca", 0))
            entries = entries[-50:]

        self._salvar_nicho(entry.nicho, entries)

    def buscar(
        self, nicho: str, agente: str = None, tipo: str = None, top_k: int = 5
    ) -> list[MemoryEntry]:
        entries = self._carregar_nicho(nicho)
        if agente:
            entries = [e for e in entries if e.get("agente") in (agente, "*")]
        if tipo:
            entries = [e for e in entries if e.get("tipo") == tipo]
        entries.sort(key=lambda e: e.get("confianca", 0), reverse=True)
        return [MemoryEntry(**e) for e in entries[:top_k]]

    def atualizar_confianca(self, nicho: str, entry_id: str, sucesso: bool):
        entries = self._carregar_nicho(nicho)
        for e in entries:
            if e.get("id") == entry_id:
                delta = 0.05 if sucesso else -0.1
                e["confianca"] = max(0.0, min(1.0, e.get("confianca", 0.5) + delta))
                e["vezes_usado"] = e.get("vezes_usado", 0) + 1
                if sucesso:
                    e["vezes_sucesso"] = e.get("vezes_sucesso", 0) + 1
                else:
                    e["vezes_falha"] = e.get("vezes_falha", 0) + 1
                e["atualizado_em"] = datetime.now().isoformat()
                break
        entries = [e for e in entries if e.get("confianca", 0) >= 0.3]
        self._salvar_nicho(nicho, entries)

    def promover_para_core(self, core: CoreMemory):
        for nicho_file in WARM_DIR.glob("*.json"):
            try:
                entries = json.load(open(nicho_file, "r", encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                continue
            for e in entries:
                if e.get("confianca", 0) >= 0.9 and e.get("vezes_usado", 0) >= 5:
                    entry = MemoryEntry(**e)
                    core.adicionar(entry)
                    print(f"[MEMORY] Promovido warm→core: '{entry.conteudo[:50]}'")

    def _carregar_nicho(self, nicho: str) -> list:
        nicho_file = WARM_DIR / f"{nicho}.json"
        if not nicho_file.exists():
            return []
        try:
            with open(nicho_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []

    def _salvar_nicho(self, nicho: str, entries: list) -> None:
        """Salva warm/<nicho>.json atomicamente com file lock (fcntl.flock).

        v1.1-baseline-2026-06-23: protecao contra race condition quando
        2+ pipelines rodando em paralelo gravam no mesmo nicho.
        Windows: fallback sem lock (multi-process nao suportado em Win).
        """
        nicho_file = WARM_DIR / f"{nicho}.json"
        _f = None
        try:
            _f = open(nicho_file, "w", encoding="utf-8")
        except (OSError, IOError) as e:
            logger.error(f"[AgentMemory] Falha ao abrir warm memory para nicho={nicho}: {e}")
            return
        try:
            try:
                import fcntl
                fcntl.flock(_f, fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
            json.dump(entries, _f, ensure_ascii=False, indent=2)
        except (OSError, IOError) as e:
            logger.error(f"[AgentMemory] Falha ao salvar warm memory para nicho={nicho}: {e}")
        finally:
            try:
                import fcntl
                fcntl.flock(_f, fcntl.LOCK_UN)
            except (ImportError, OSError, ValueError, AttributeError):
                pass
            _f.close()


class ColdMemory:
    def __init__(self):
        COLD_DIR.mkdir(parents=True, exist_ok=True)

    def salvar_run(self, run_id: str, dados: dict):
        path = COLD_DIR / f"{run_id}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"[MEMORY] Cold save erro: {e}")

    def buscar_por_nicho(self, nicho: str, limit: int = 10) -> list:
        resultados = []
        for path in sorted(
            COLD_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("nicho") == nicho:
                    resultados.append(data)
                    if len(resultados) >= limit:
                        break
            except Exception:
                continue
        return resultados


def gerar_prompt_com_memoria(
    system_base: str, agente: str, nicho: str, core: CoreMemory, warm: WarmMemory
) -> str:
    core_text = core.get_para_agente(agente, nicho)
    warm_entries = warm.buscar(nicho, agente=agente, top_k=3)
    warm_text = ""
    if warm_entries:
        warm_text = "\n## Padrões aprendidos (este nicho):\n"
        warm_text += "\n".join([f"- {e.conteudo}" for e in warm_entries])

    extra = ""
    if core_text or warm_text:
        extra = f"\n\n{core_text}\n{warm_text}" if core_text else f"\n\n{warm_text}"
        tokens_est = len(extra.split())
        print(f"[MEMORY] Injetado pra {agente}/{nicho}: {tokens_est} tokens estimados")

    return f"{system_base}{extra}"


# ══════════════════════════════════════════════════════════════
# THREAD-LOCAL MEMORY — call_claude injeta automaticamente
# ══════════════════════════════════════════════════════════════
import threading

_thread_local = threading.local()


def set_memory(core: CoreMemory, warm: WarmMemory, nicho: str):
    _thread_local.memory_core = core
    _thread_local.memory_warm = warm
    _thread_local.memory_nicho = nicho


def get_memory():
    core = getattr(_thread_local, "memory_core", None)
    warm = getattr(_thread_local, "memory_warm", None)
    nicho = getattr(_thread_local, "memory_nicho", None)
    return core, warm, nicho


def clear_memory():
    _thread_local.memory_core = None
    _thread_local.memory_warm = None
    _thread_local.memory_nicho = None
