"""Vite/React configuration constants and environment helpers."""

from __future__ import annotations

import os
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# FIXED DEPENDENCIES (pinned, verified-compatible)
# ═══════════════════════════════════════════════════════════════════

FIXED_PACKAGE_JSON = {
    "dependencies": {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
        "lucide-react": "^0.468.0",
        "@tailwindcss/vite": "^4.0.0",
        "tailwindcss": "^4.0.0",
        "motion": "^11.11.0",
    },
    "devDependencies": {
        "@types/react": "^18.3.12",
        "@types/react-dom": "^18.3.1",
        "@vitejs/plugin-react": "^4.3.3",
        "typescript": "^5.7.2",
        "vite": "^6.0.0",
        "vite-plugin-prerender-spa": "^1.2.3",
    },
}

REQUIRED_PROJECT_FILES = frozenset([
    "package.json",
    "vite.config.ts",
    "tsconfig.json",
    "index.html",
    "src/main.tsx",
    "src/App.tsx",
    "src/index.css",
    "src/types.ts",
])

# Files that must be present (generated or provided)
CORE_FILES = frozenset([
    "package.json",
    "vite.config.ts",
    "tsconfig.json",
    "index.html",
    "src/main.tsx",
])

# ═══════════════════════════════════════════════════════════════════
# SOURCE GUARDS — block unwanted code patterns in generated output
# ═══════════════════════════════════════════════════════════════════

BLOCKED_SOURCE_PATTERNS = [
    r"import\s+.*from\s+['\"]supabase",
    r"import\s+.*from\s+['\"]@supabase/",
    r"import\s+.*from\s+['\"]firebase",
    r"import\s+.*from\s+['\"]firebase/",
    r"createClient\(\)",
    r"initializeApp\(",
    r"Next\.js",
    r"next/",
    r"Router\s*\(",
    r"getServerSideProps",
    r"getStaticProps",
    r"useRouter\(\).push",
]

# ═══════════════════════════════════════════════════════════════════
# SEGMENT-SPECIFIC RULES
# ═══════════════════════════════════════════════════════════════════

SEGMENT_RULES: dict[str, dict] = {
    "academia": {
        "exclude_sections": ["menu", "reservation"],
        "include_sections": ["hero", "services", "plans", "testimonials", "location"],
    },
    "restaurante": {
        "exclude_sections": ["pricing", "faq"],
        "include_sections": ["hero", "menu", "gallery", "reviews", "location"],
    },
    "hamburgueria": {
        "exclude_sections": ["pricing", "faq"],
        "include_sections": ["hero", "menu", "gallery", "reviews", "location"],
    },
    "pizzaria": {
        "exclude_sections": ["pricing", "faq"],
        "include_sections": ["hero", "menu", "gallery", "reviews", "location"],
    },
    "dentista": {
        "exclude_sections": ["menu", "reservation"],
        "include_sections": ["hero", "services", "testimonials", "location"],
    },
    "clinica": {
        "exclude_sections": ["menu", "reservation"],
        "include_sections": ["hero", "services", "testimonials", "location"],
    },
    "advocacia": {
        "exclude_sections": ["menu", "reservation", "plans"],
        "include_sections": ["hero", "services", "about", "testimonials"],
    },
}

# ═══════════════════════════════════════════════════════════════════
# BATCH CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

VITE_REACT_FILE_BATCHES = [
    {
        "name": "core",
        "files": [
            "package.json",
            "vite.config.ts",
            "tsconfig.json",
            "index.html",
            "src/main.tsx",
        ],
    },
    {
        "name": "foundation",
        "files": [
            "src/App.tsx",
            "src/index.css",
            "src/types.ts",
        ],
    },
    {
        "name": "components",
        "files": [
            "src/components/Navbar.tsx",
            "src/components/HeroSection.tsx",
            "src/components/ContactCTA.tsx",
            "src/components/Footer.tsx",
        ],
    },
    {
        "name": "page",
        "files": [
            "src/pages/Index.tsx",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════
# ENVIRONMENT HELPERS
# ═══════════════════════════════════════════════════════════════════

def _env_int(name: str, default: int) -> int:
    """Parse integer from environment variable, return default if missing/invalid."""
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def _model_repair_attempts() -> int:
    """Number of repair attempts when JSON parsing fails."""
    return _env_int("VITE_MODEL_REPAIR_ATTEMPTS", 2)


def _single_model_mode_enabled() -> bool:
    """Use single model without fallback chain."""
    return os.getenv("VITE_SINGLE_MODEL_MODE", "0") == "1"


def _preview_fast_enabled() -> bool:
    """Enable fast preview mode with minimal generation."""
    return os.getenv("VITE_PREVIEW_FAST", "0") == "1"


def _batch_first_enabled() -> bool:
    """Generate core files first, then components in batches."""
    return os.getenv("VITE_BATCH_FIRST", "1") == "1"


def _batch_first_project_attempts() -> int:
    """Max attempts for full project generation (batch-first mode)."""
    return _env_int("VITE_BATCH_FIRST_ATTEMPTS", 1)


def _batch_spacing_seconds() -> float:
    """Delay between batches to avoid rate limits."""
    val = float(os.getenv("VITE_BATCH_SPACING_SECONDS", "1.0"))
    return max(0.5, min(val, 10.0))


def _batch_max_tokens(max_tokens: int) -> int:
    """Scale tokens based on environment config."""
    multiplier = float(os.getenv("VITE_BATCH_TOKEN_MULTIPLIER", "1.0"))
    return int(max_tokens * multiplier)


def _batch_token_budget(batch_name: str, max_tokens: int) -> int:
    """Calculate token budget per batch based on name."""
    budgets = {
        "core": int(max_tokens * 0.25),
        "foundation": int(max_tokens * 0.20),
        "components": int(max_tokens * 0.40),
        "page": int(max_tokens * 0.15),
    }
    return budgets.get(batch_name, int(max_tokens * 0.20))


def _batch_format_repair_budget() -> int:
    """Tokens for format-repair attempts."""
    return _env_int("VITE_FORMAT_REPAIR_TOKENS", 2048)


def _studio_min_source_chars() -> int:
    """Minimum total source characters for valid project."""
    return _env_int("VITE_MIN_SOURCE_CHARS", 8000)


def _studio_min_classnames() -> int:
    """Minimum unique Tailwind classnames."""
    return _env_int("VITE_MIN_CLASSNAMES", 30)


def _studio_min_images() -> int:
    """Minimum external image URLs."""
    return _env_int("VITE_MIN_IMAGES", 2)


def _studio_min_components() -> int:
    """Minimum React component files."""
    return _env_int("VITE_MIN_COMPONENTS", 4)


def _transient_proxy_retry_delay_seconds(attempt: int) -> float:
    """Exponential backoff delay between retries."""
    base = float(os.getenv("VITE_RETRY_DELAY_BASE", "2.0"))
    max_delay = float(os.getenv("VITE_RETRY_DELAY_MAX", "30.0"))
    delay = base * (2 ** min(attempt, 5))
    return min(delay, max_delay)
