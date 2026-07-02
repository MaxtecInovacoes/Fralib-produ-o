"""Fail release when secrets are tracked in git."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_TRACKED = {".env", ".env.local", ".env.production", ".env.backup"}
BLOCKED_TRACKED_SUFFIXES = (".db", ".sqlite", ".sqlite3")
SENSITIVE_BACKUP_GLOBS = ("**/.env.backup*", "**/*.env.backup*")
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-or-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-kpa-[A-Za-z0-9_-]{20,}\b"),  # KPLabs / kie.ai
    re.compile(r"\bsk-proj-[A-Za-z0-9_-]{20,}\b"),  # OpenAI project keys
    re.compile(r"\bgsk_[A-Za-z0-9_-]{20,}\b"),  # Groq
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS Access Key
    re.compile(r"\bghp_[0-9A-Za-z]{20,}\b"),
    re.compile(r"\bgho_[0-9A-Za-z]{20,}\b"),  # GitHub OAuth
    re.compile(r"\bghu_[0-9A-Za-z]{20,}\b"),  # GitHub User
    re.compile(r"\bghs_[0-9A-Za-z]{20,}\b"),  # GitHub Server
    re.compile(r"\bghr_[0-9A-Za-z]{20,}\b"),  # GitHub Refresh
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b"),
    re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b"),
    re.compile(r"\bpk_(?:live|test)_[0-9A-Za-z]{16,}\b"),  # Stripe publishable
    re.compile(r"\bAPP_USR-[0-9]+-[0-9]+-[A-Za-z0-9-]+"),  # MercadoPago
    re.compile(r"\bwhsec_[0-9A-Za-z]{16,}\b"),
    re.compile(r"postgres(?:ql)?://[^\s'\":/]+:[^@\s'\"]+@", re.IGNORECASE),
    re.compile(r"mysql://[^\s'\":/]+:[^@\s'\"]+@", re.IGNORECASE),
    re.compile(r"mongodb(?:\+srv)?://[^\s'\":/]+:[^@\s'\"]+@", re.IGNORECASE),
    re.compile(r"\bJWT_SECRET_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{24,}", re.IGNORECASE),
    re.compile(r"\bFERNET_KEY\s*=\s*['\"]?[A-Za-z0-9_=-]{30,}", re.IGNORECASE),
    re.compile(
        r"\b(?:POSTGRES_PASSWORD|DB_PASSWORD|DATABASE_PASSWORD)\s*=\s*['\"]?[^'\"\s#]+",
        re.IGNORECASE,
    ),
]
PLACEHOLDER_FILES = {".env.example"}
DEV_COMPOSE_FILES = {"docker-compose.yml"}
PLACEHOLDER_MARKERS = (
    "aqui",
    "placeholder",
    "usuario:senha",
    "sua_",
    "seudominio",
    "cole_",
)
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".lock",
}
SKIP_DIRS = {".git", "venv", "node_modules", "htmlcov", "__pycache__"}


def _should_skip(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    if parts & SKIP_DIRS:
        return True
    return any(part.startswith("pytest-cache-files-") for part in parts)


def _git_lines(*args: str) -> list[str]:
    out = subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _line_for_match(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def _allowed_placeholder(rel: str, text: str, match: re.Match[str]) -> bool:
    line = _line_for_match(text, match.start()).lower()
    rel = rel.replace("\\", "/")
    if rel in PLACEHOLDER_FILES:
        return any(marker in line for marker in PLACEHOLDER_MARKERS)
    if rel in DEV_COMPOSE_FILES and "fralib_dev_password" in line:
        return True
    return False


def main() -> int:
    tracked = _git_lines("ls-files")
    failures: list[str] = []
    tracked_set = {p.replace("\\", "/") for p in tracked}
    for item in sorted(BLOCKED_TRACKED):
        if item in tracked_set:
            failures.append(f"tracked secret file: {item}")
    for rel in sorted(tracked_set):
        if rel.lower().endswith(BLOCKED_TRACKED_SUFFIXES):
            failures.append(f"tracked database file: {rel}")

    local_backups: set[str] = set()
    for pattern in SENSITIVE_BACKUP_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file() and not _should_skip(path):
                local_backups.add(path.relative_to(ROOT).as_posix())
    for rel in sorted(local_backups):
        failures.append(f"local env backup file present: {rel}")

    for rel in tracked:
        path = ROOT / rel
        if path.suffix.lower() in SKIP_SUFFIXES or not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match and not _allowed_placeholder(rel, text, match):
                failures.append(f"secret-like pattern in tracked file: {rel}")
                break

    if failures:
        print("secret hygiene failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("secret hygiene ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
