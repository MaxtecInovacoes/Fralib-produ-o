"""
Configurações centralizadas do FraLib.
Substitui variáveis hardcoded dispersas pelo codebase.
"""
import os
from pathlib import Path
from typing import Set

# ===== COMPATIBILIDADE COM backend/config.py =====
BACKEND_DIR = Path(__file__).resolve().parents[1]
FRALIB_ROOT = BACKEND_DIR.parent.resolve()
CHECKPOINT_DIR = os.getenv("FRALIB_CHECKPOINT_DIR", str(FRALIB_ROOT / "checkpoints"))
SITES_DIR = os.getenv("FRALIB_SITES_DIR", "/var/www/fralib/sites")
SITE_DOMAIN = os.getenv("FRALIB_SITE_DOMAIN", "https://seunegociofralib.site")
FRALIB_DOMAIN = os.getenv("FRALIB_DOMAIN", "https://fralib.com.br")
DS_DIR = os.getenv("FRALIB_DS_DIR", "/root/open-design/design-systems")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5433/fralib_db")
WA_PHONE_PREFIX = os.getenv("WA_PHONE_PREFIX", "55")

# ===== SUPERADMIN =====
def _get_superadmin_emails() -> Set[str]:
    """Retorna emails de superadmin do .env (suporta múltiplos separados por vírgula)."""
    raw = os.getenv("SUPERADMIN_EMAIL", "").strip()
    if not raw:
        return set()  # No superadmin configured — safe default
    return set(email.strip() for email in raw.split(",") if email.strip())

SUPERADMIN_EMAILS = _get_superadmin_emails()

def is_superadmin(email: str) -> bool:
    """Verifica se o email é de um superadmin."""
    return email in SUPERADMIN_EMAILS

# ===== ENVIRONMENT =====
FRALIB_ENV = os.getenv("FRALIB_ENV", "dev").lower()
IS_PRODUCTION = FRALIB_ENV == "prod"
IS_DEVELOPMENT = FRALIB_ENV == "dev"

# ===== REDIS =====
REDIS_URL = os.getenv("REDIS_URL")
HAS_REDIS = REDIS_URL is not None and REDIS_URL.strip() != ""

# ===== RATE LIMITING =====
GLOBAL_MAX_CALLS_PER_MIN = int(os.getenv("GLOBAL_MAX_CALLS_PER_MIN", "60"))
GLOBAL_DAILY_TOKEN_BUDGET = int(os.getenv("GLOBAL_DAILY_TOKEN_BUDGET", "2000000"))

# ===== FILE PATHS =====
FRALIB_SITES_ROOT = os.getenv("FRALIB_SITES_ROOT", "/var/www/fralib/sites")
FRALIB_BUILDER_SANDBOX_ROOT = os.getenv("FRALIB_BUILDER_SANDBOX_ROOT", "/tmp/fralib_builder")
FRALIB_BUILDER_MANIFEST_DIR = os.getenv("FRALIB_BUILDER_MANIFEST_DIR", "logs/builder_manifests")

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/fralib.log")

# ===== ALLOWED BASE URLs (SSRF Protection) =====
ALLOWED_LLM_BASE_URLS = {
    # Anthropic
    "api.anthropic.com",
    "api.claude.ai",
    "api.aibee.cloud",
    "caludeilimi.up.railway.app",
    # OpenAI
    "api.openai.com",
    "openai.azure.com",
    # Google
    "generativelanguage.googleapis.com",
    # Groq
    "api.groq.com",
    # OpenRouter
    "openrouter.ai",
    "ws-yl9g28gtt9a4owrv.ap-southeast-1.maas.aliyuncs.com",
    # DeepSeek
    "api.deepseek.com",
    # Qwen
    "dashscope.aliyuncs.com",
    # Moonshot
    "api.moonshot.cn",
}

def is_allowed_llm_url(url: str) -> bool:
    """Verifica se uma URL de provider LLM é permitida (SSRF protection)."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc in ALLOWED_LLM_BASE_URLS
    except Exception:
        return False
