"""Canonical LLM pricing helpers.

All token ledgers and dashboards should use this module instead of keeping
separate model-price tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, TypedDict


class LlmUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    cache_creation: int
    cache_read: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input: Decimal
    output: Decimal
    cache_write: Decimal = Decimal("0")
    cache_read: Decimal = Decimal("0")


MODEL_PRICES: dict[str, ModelPrice] = {
    "claude-opus-4-8": ModelPrice(Decimal("5.0"), Decimal("25.0"), Decimal("6.25"), Decimal("0.50")),
    "claude-opus-4-20250514": ModelPrice(Decimal("5.0"), Decimal("25.0"), Decimal("6.25"), Decimal("0.50")),
    "claude-opus-4-7": ModelPrice(Decimal("15.0"), Decimal("75.0"), Decimal("18.75"), Decimal("1.50")),
    "claude-sonnet-4-6": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.75"), Decimal("0.30")),
    "claude-sonnet-4-20250514": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.75"), Decimal("0.30")),
    "claude-3-5-sonnet": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.75"), Decimal("0.30")),
    "claude-3-5-sonnet-20241022": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.75"), Decimal("0.30")),
    "claude-3-5-sonnet-20240620": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.75"), Decimal("0.30")),
    "claude-haiku-4-5": ModelPrice(Decimal("0.80"), Decimal("4.0"), Decimal("1.0"), Decimal("0.08")),
    "claude-haiku-4-20250514": ModelPrice(Decimal("0.80"), Decimal("4.0"), Decimal("1.0"), Decimal("0.08")),
    "fast": ModelPrice(Decimal("0.80"), Decimal("4.0"), Decimal("1.0"), Decimal("0.08")),
    "gpt-5.4-mini": ModelPrice(Decimal("0.80"), Decimal("4.0"), Decimal("1.0"), Decimal("0.08")),
    "deepseek-v4-flash": ModelPrice(Decimal("0.10"), Decimal("0.20"), Decimal("0.10"), Decimal("0.01")),
    "gemini-3.5-flash": ModelPrice(Decimal("1.5"), Decimal("9.0"), Decimal("1.5"), Decimal("0.15")),
    "gemini-2.5-flash": ModelPrice(Decimal("0.80"), Decimal("4.0"), Decimal("1.0"), Decimal("0.08")),
    "anthropic/claude-opus-4.8": ModelPrice(Decimal("5.0"), Decimal("25.0"), Decimal("5.0"), Decimal("0.50")),
    "anthropic/claude-opus-4.8-fast": ModelPrice(Decimal("10.0"), Decimal("50.0"), Decimal("10.0"), Decimal("1.0")),
    "anthropic/claude-sonnet-4.6": ModelPrice(Decimal("3.0"), Decimal("15.0"), Decimal("3.0"), Decimal("0.30")),
    "anthropic/claude-haiku-4.5": ModelPrice(Decimal("1.0"), Decimal("5.0"), Decimal("1.0"), Decimal("0.10")),
    "google/gemini-3.1-pro-preview": ModelPrice(Decimal("2.0"), Decimal("12.0"), Decimal("2.0"), Decimal("0.20")),
    "google/gemini-3.5-flash": ModelPrice(Decimal("1.5"), Decimal("9.0"), Decimal("1.5"), Decimal("0.15")),
    "deepseek/deepseek-v4-flash": ModelPrice(Decimal("0.10"), Decimal("0.20"), Decimal("0.10"), Decimal("0.01")),
    "deepseek/deepseek-v4-pro": ModelPrice(Decimal("0.43"), Decimal("0.87"), Decimal("0.43"), Decimal("0.04")),
    "qwen/qwen3-coder-plus": ModelPrice(Decimal("0.65"), Decimal("3.25"), Decimal("0.65"), Decimal("0.06")),
    "opus": ModelPrice(Decimal("15.0"), Decimal("75.0")),
    "sonnet": ModelPrice(Decimal("3.0"), Decimal("15.0")),
    "haiku": ModelPrice(Decimal("0.25"), Decimal("1.25")),
}

PRECOS_POR_MILHAO: dict[str, dict[str, float]] = {
    model: {
        "input": float(price.input),
        "output": float(price.output),
        "cache_write": float(price.cache_write),
        "cache_read": float(price.cache_read),
    }
    for model, price in MODEL_PRICES.items()
}


def resolve_model_price(model: str) -> ModelPrice:
    model_lower = (model or "").lower()
    if model_lower in MODEL_PRICES:
        return MODEL_PRICES[model_lower]
    for key in sorted(MODEL_PRICES, key=len, reverse=True):
        if key in model_lower:
            return MODEL_PRICES[key]
    return MODEL_PRICES["claude-sonnet-4-6"]


def estimate_llm_cost_usd(model: str, usage: Mapping[str, int | float]) -> float:
    price = resolve_model_price(model)
    million = Decimal("1000000")
    cache_write = usage.get("cache_creation", usage.get("cache_creation_input_tokens", 0))
    cache_read = usage.get("cache_read", usage.get("cache_read_input_tokens", 0))
    cost = (
        Decimal(str(usage.get("input_tokens", 0))) * price.input
        + Decimal(str(usage.get("output_tokens", 0))) * price.output
        + Decimal(str(cache_write)) * price.cache_write
        + Decimal(str(cache_read)) * price.cache_read
    ) / million
    return float(cost)
