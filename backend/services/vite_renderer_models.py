"""Selecao e limites de modelos usados pelo renderer Vite/React."""


MODEL_MAX_COMPLETION_TOKENS = {
    "claude-sonnet-4-6": 16384,
    "claude-sonnet-4-20250514": 16384,
    "claude-3-5-sonnet": 8192,
    "claude-3-5-sonnet-20241022": 8192,
    "claude-3-5-sonnet-20240620": 8192,
    "claude-haiku-4-5": 8192,
    "claude-haiku-4-20250514": 8192,
}


def normalize_model_alias(model: str) -> str:
    clean = str(model or "").strip().lower()
    if clean in {"haiku", "sonnet", "opus"}:
        return clean
    if clean in {
        "claude-haiku-4-5",
        "claude-haiku-4-20250514",
        "claude-haiku-4-5-20251001",
        "claude-haiku-4-5-thinking",
        "fast",
        "gpt-5.4-mini",
    }:
        return "haiku"
    if clean in {
        "claude-sonnet-4-6",
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "deepseek-v4-flash",
    }:
        return "sonnet"
    if clean in {
        "claude-opus-4-8",
        "claude-opus-4-6",
        "claude-opus-4-8-thinking",
        "claude-opus-4-20250514",
        "claude-opus-4-8-20250514",
        "claude-opus-4-6-thinking",
    }:
        return "opus"
    return clean


def cap_max_tokens_for_model(model_id: str, requested: int) -> int:
    raw = str(model_id or "").strip().lower()
    normalized = normalize_model_alias(model_id)
    hard_cap = MODEL_MAX_COMPLETION_TOKENS.get(raw)
    if hard_cap is None:
        if "sonnet" in normalized:
            hard_cap = 16384
        elif "haiku" in normalized:
            hard_cap = 8192
        else:
            hard_cap = requested or 8192
    if requested <= 0:
        return hard_cap
    return max(1024, min(requested, hard_cap))


# -----------------------------------------------------------------------------
# BATCH-LEVEL MODEL ROUTING
# -----------------------------------------------------------------------------
# Batches simples (estrutura, types, css) usam Haiku (10x mais barato).
# Batches complexos (hero, design tokens) usam Sonnet.
# Batches de refinamento/criativo usam Opus.

LIGHT_BATCH_NAMES = {
    "app", "main", "types", "css", "index_css", "tsconfig", "package_json",
    "vite_config", "index_html", "index", "app_tsx", "main_tsx",
}
SONNET_BATCH_NAMES = {
    "hero", "navbar", "footer", "about", "gallery", "location", "contact",
    "reviews", "cta", "services", "menu", "testimonials", "team",
}
OPUS_BATCH_NAMES = {
    "refactor", "custom_advanced", "architecture", "complex_interaction",
}


def batch_model_for_batch(batch_name: str) -> str:
    """Roteia modelo LLM pelo nome do batch.

    - Batches simples/estruturais: Haiku (~10x mais barato, ~3x mais rapido)
    - Batches visuais/copy: Sonnet (balanceado)
    - Batches complexos/criativos: Opus (top-tier)

    Custo LLM estimado cai ~50%, velocidade +30% em media.
    """
    name = (batch_name or "").strip().lower()
    name_clean = name.replace(".json", "").replace(".tsx", "").replace(".ts", "").replace(".css", "").replace(".html", "")
    if name_clean in LIGHT_BATCH_NAMES or any(p in name_clean for p in ("tsconfig", "package", "config")):
        return "haiku"
    if name_clean in OPUS_BATCH_NAMES or "custom" in name_clean:
        return "opus"
    return "sonnet"
