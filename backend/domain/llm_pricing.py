"""
LLM Pricing — Estimativa de custo por modelo.
Fonte: preços públicos Anthropic + OpenAI, em USD por 1M tokens.
"""


# (input_usd_per_1M, output_usd_per_1M)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic Claude
    "claude-opus-4-7":            (15.00, 75.00),
    "claude-opus-4-8":            (15.00, 75.00),
    "claude-opus-4-20250514":     (15.00, 75.00),
    "claude-sonnet-4-6":          (3.00,  15.00),
    "claude-sonnet-4-20250514":   (3.00,  15.00),
    "claude-haiku-4-5":           (0.25,  1.25),
    "claude-haiku-4-20250514":    (0.25,  1.25),
    "claude-haiku-4-5-20251001":  (0.25,  1.25),
    # Anthropic free-tier variants (cost = 0)
    "fast":                       (0.00,  0.00),
    "gpt-5.4-mini":               (0.00,  0.00),
    "deepseek-v4-flash":          (0.00,  0.00),
    # OpenAI
    "gpt-4o":                     (2.50,  10.00),
    "gpt-4o-mini":                (0.15,  0.60),
    "gpt-4-turbo":                (10.00, 30.00),
    "gpt-3.5-turbo":              (0.50,  1.50),
}


def _pricing_for(model: str) -> tuple[float, float]:
    """Retorna (input, output) USD por 1M tokens para o modelo."""
    if model in _MODEL_PRICING:
        return _MODEL_PRICING[model]

    # Fallback heurístico por prefixo
    lower = model.lower()
    if "opus" in lower or "gpt-4-turbo" in lower:
        return (15.00, 75.00)
    if "sonnet" in lower or "gpt-4o" in lower:
        return (3.00, 15.00)
    if "haiku" in lower or "mini" in lower or "flash" in lower:
        return (0.25, 1.25)
    if "gpt-3.5" in lower:
        return (0.50, 1.50)
    # Unknown model — assume cheap tier
    return (1.00, 5.00)


def estimate_llm_cost_usd(model: str, usage: dict) -> float:
    """Calcula custo estimado em USD para uma chamada LLM."""
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)

    input_price, output_price = _pricing_for(model)

    # Cached reads custam ~10% do input normal (prompt caching discount)
    cache_price = input_price * 0.10
    # Cache creation custa ~25% a mais que input normal (write penalty)
    cache_creation_price = input_price * 1.25

    cost = (
        cache_read * cache_price
        + cache_creation * cache_creation_price
        + max(input_tokens - cache_read - cache_creation, 0) * input_price
        + output_tokens * output_price
    )

    return cost / 1_000_000  # converter de USD por 1M para USD
