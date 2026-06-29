"""
Memory Management - Enhanced memory system for LangGraph agents
"""

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("agent_memory")

# Memory directories
MEMORY_DIR = Path(__file__).parent / "memory"
CORE_FILE = MEMORY_DIR / "core.json"
WARM_DIR = MEMORY_DIR / "warm"
COLD_DIR = MEMORY_DIR / "cold"


@dataclass
class MemoryEntry:
    """Enhanced memory entry with metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    agent_type: str = "*"
    nicho: str = "*"
    content: str = ""
    confidence: float = 0.5
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.usage_count == 0:
            return 0.5
        return self.success_count / self.usage_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "nicho": self.nicho,
            "content": self.content,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary"""
        return cls(**data)


class CoreMemory:
    """Core memory with thread safety and error handling"""

    _intra_process_lock = threading.Lock()

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        with CoreMemory._intra_process_lock:
            self.entries: List[MemoryEntry] = self._load()
            self._lock = threading.Lock()

    def _load(self) -> List[MemoryEntry]:
        """Load core memory from file"""
        if not CORE_FILE.exists():
            return []

        try:
            with open(CORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryEntry.from_dict(e) for e in data]
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"[CoreMemory] Failed to load: {e}")
            self._backup_corrupted_file()
            return []

    def _save(self) -> None:
        """Save core memory atomically"""
        with CoreMemory._intra_process_lock:
            try:
                # Create temporary file first
                temp_file = CORE_FILE.with_suffix(".tmp")

                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump([e.to_dict() for e in self.entries], f, ensure_ascii=False, indent=2)

                # Atomic rename
                temp_file.replace(CORE_FILE)

            except Exception as e:
                logger.error(f"[CoreMemory] Failed to save: {e}")
                if temp_file.exists():
                    temp_file.unlink()

    def _backup_corrupted_file(self) -> None:
        """Backup corrupted file"""
        try:
            if CORE_FILE.exists():
                backup = CORE_FILE.with_suffix(f".corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
                CORE_FILE.replace(backup)
                logger.info(f"[CoreMemory] Backed up corrupted file to: {backup}")
        except Exception as e:
            logger.error(f"[CoreMemory] Failed to backup: {e}")

    def add_entry(self, entry: MemoryEntry) -> None:
        """Add memory entry with deduplication"""
        with self._lock:
            # Check for duplicates
            existing = next((e for e in self.entries if e.content == entry.content), None)
            if existing:
                # Update existing entry
                existing.confidence = max(existing.confidence, entry.confidence)
                existing.usage_count += 1
                existing.updated_at = datetime.now(timezone.utc).isoformat()
                self._save()
                return

            # Add new entry
            if len(self.entries) >= 20:
                # Remove lowest confidence entry
                self.entries.sort(key=lambda e: e.confidence)
                removed = self.entries.pop(0)
                logger.info(f"[CoreMemory] Removed low-confidence entry: {removed.content[:50]}")

            self.entries.append(entry)
            self._save()
            logger.info(f"[CoreMemory] Added entry: {entry.content[:50]} (conf={entry.confidence:.0%})")

    def get_relevant_entries(self, agent_type: str, nicho: str, limit: int = 10) -> List[MemoryEntry]:
        """Get relevant memory entries"""
        relevant = [
            e for e in self.entries
            if (e.agent_type == agent_type or e.agent_type == "*")
            and (e.nicho == nicho or e.nicho == "*")
        ]

        # Sort by confidence and usage
        relevant.sort(key=lambda e: (e.confidence, e.usage_count), reverse=True)
        return relevant[:limit]


class WarmMemory:
    """Warm memory with per-nicho storage"""

    def __init__(self):
        WARM_DIR.mkdir(parents=True, exist_ok=True)

    def add_entry(self, entry: MemoryEntry) -> None:
        """Add entry to warm memory"""
        entries = self._load_nicho(entry.nicho)

        # Check for existing entry
        existing = next((e for e in entries if e.content == entry.content), None)
        if existing:
            # Update existing
            existing.confidence = min(1.0, existing.confidence + 0.05)
            existing.usage_count += 1
            existing.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            entries.append(entry)

        # Limit to 50 entries per nicho
        if len(entries) > 50:
            entries.sort(key=lambda e: e.confidence)
            entries = entries[-50:]

        self._save_nicho(entry.nicho, entries)

    def search_entries(
        self,
        nicho: str,
        agent_type: str = None,
        tags: List[str] = None,
        min_confidence: float = 0.3,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """Search warm memory entries"""
        entries = self._load_nicho(nicho)

        # Filter by criteria
        filtered = entries
        if agent_type:
            filtered = [e for e in filtered if e.agent_type in (agent_type, "*")]
        if tags:
            filtered = [e for e in filtered if any(tag in e.tags for tag in tags)]
        filtered = [e for e in filtered if e.confidence >= min_confidence]

        # Sort by confidence
        filtered.sort(key=lambda e: e.confidence, reverse=True)
        return filtered[:limit]

    def update_confidence(self, entry_id: str, nicho: str, success: bool) -> None:
        """Update entry confidence"""
        entries = self._load_nicho(nicho)

        for entry in entries:
            if entry.id == entry_id:
                delta = 0.05 if success else -0.1
                entry.confidence = max(0.0, min(1.0, entry.confidence + delta))
                entry.usage_count += 1
                if success:
                    entry.success_count += 1
                else:
                    entry.failure_count += 1
                entry.updated_at = datetime.now(timezone.utc).isoformat()
                break

        # Remove low confidence entries
        entries = [e for e in entries if e.confidence >= 0.3]
        self._save_nicho(nicho, entries)

    def _load_nicho(self, nicho: str) -> List[MemoryEntry]:
        """Load entries for specific nicho"""
        nicho_file = WARM_DIR / f"{nicho}.json"
        if not nicho_file.exists():
            return []

        try:
            with open(nicho_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryEntry.from_dict(e) for e in data]
        except Exception as e:
            logger.error(f"[WarmMemory] Failed to load nicho {nicho}: {e}")
            return []

    def _save_nicho(self, nicho: str, entries: List[MemoryEntry]) -> None:
        """Save entries for specific nicho"""
        nicho_file = WARM_DIR / f"{nicho}.json"

        try:
            with open(nicho_file, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in entries], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[WarmMemory] Failed to save nicho {nicho}: {e}")


class ColdMemory:
    """Cold memory for long-term storage"""

    def __init__(self):
        COLD_DIR.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Save complete session data"""
        session_file = COLD_DIR / f"{session_id}.json"

        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"[ColdMemory] Saved session: {session_id}")
        except Exception as e:
            logger.error(f"[ColdMemory] Failed to save session {session_id}: {e}")

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data"""
        session_file = COLD_DIR / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ColdMemory] Failed to load session {session_id}: {e}")
            return None

    def get_sessions_by_nicho(self, nicho: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for a nicho"""
        sessions = []

        for session_file in sorted(
            COLD_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("nicho") == nicho:
                    sessions.append(data)
                    if len(sessions) >= limit:
                        break
            except Exception:
                continue

        return sessions


class MemoryManager:
    """Unified memory manager for LangGraph agents"""

    def __init__(self):
        self.core = CoreMemory()
        self.warm = WarmMemory()
        self.cold = ColdMemory()

    def add_experience(
        self,
        session_id: str,
        agent_type: str,
        nicho: str,
        content: str,
        confidence: float = 0.5,
        tags: List[str] = None,
        source: str = ""
    ) -> MemoryEntry:
        """Add new experience to memory"""
        entry = MemoryEntry(
            session_id=session_id,
            agent_type=agent_type,
            nicho=nicho,
            content=content,
            confidence=confidence,
            tags=tags or [],
            source=source
        )

        # Add to all memory levels
        self.core.add_entry(entry)
        self.warm.add_entry(entry)

        return entry

    def get_memory_context(
        self,
        session_id: str,
        agent_type: str,
        nicho: str,
        limit_core: int = 10,
        limit_warm: int = 3
    ) -> Dict[str, str]:
        """Get memory context for agent"""
        # Get core memories
        core_entries = self.core.get_relevant_entries(agent_type, nicho, limit_core)
        core_text = "## Memória Principal (experiências passadas):\n"
        for entry in core_entries:
            core_text += f"- [{entry.confidence:.0%}] {entry.content}\n"

        # Get warm memories
        warm_entries = self.warm.search_entries(nicho, agent_type, limit=limit_warm)
        warm_text = ""
        if warm_entries:
            warm_text = "\n## Padrões Aprendidos (este nicho):\n"
            for entry in warm_entries:
                warm_text += f"- [{entry.confidence:.0%}] {entry.content}\n"

        # Calculate injected tokens
        total_text = core_text + warm_text
        tokens_est = len(total_text.split())

        context = {
            "core_memory": core_text,
            "warm_memory": warm_text,
            "total_tokens": tokens_est,
            "core_entries_count": len(core_entries),
            "warm_entries_count": len(warm_entries)
        }

        logger.info(f"[MemoryManager] Injected {tokens_est} tokens for {agent_type}/{nicho}")
        return context

    def record_interaction(
        self,
        session_id: str,
        agent_type: str,
        nicho: str,
        interaction: str,
        success: bool
    ) -> None:
        """Record interaction outcome"""
        # Find relevant warm entries
        entries = self.warm.search_entries(nicho, agent_type)

        for entry in entries:
            if entry.content in interaction or interaction in entry.content:
                self.warm.update_confidence(entry.id, nicho, success)
                break

        # Add new experience if interaction is valuable
        if success or len(interaction) > 50:  # Only add meaningful interactions
            confidence = 0.7 if success else 0.3
            tags = ["successful"] if success else ["failed"]

            self.add_experience(
                session_id=session_id,
                agent_type=agent_type,
                nicho=nicho,
                content=interaction,
                confidence=confidence,
                tags=tags,
                source="interaction"
            )

    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Save complete session state"""
        self.cold.save_session(session_id, state)

    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session state"""
        return self.cold.load_session(session_id)


# Global memory manager instance
memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Get global memory manager"""
    return memory_manager