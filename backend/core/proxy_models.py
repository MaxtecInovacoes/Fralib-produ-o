"""Canonical LiteLLM model policy for FraLib agents."""

from __future__ import annotations

import os


PROXY_PROVIDER = "anthropic"
PROXY_BASE_URL_DEFAULT = "https://llm.seunegociofralib.site"

PROXY_MODEL_OPTIONS = [
    {
        "id": "claude-haiku-4-5",
        "label": "Legacy light alias via llm.seunegociofralib.site",
        "tier": "light",
    },
    {
        "id": "claude-haiku-4-20250514",
        "label": "Legacy light dated alias via llm.seunegociofralib.site",
        "tier": "light",
    },
    {
        "id": "gemini-3.5-flash",
        "label": "Legacy Gemini Flash alias via LiteLLM",
        "tier": "light",
    },
    {
        "id": "gemini-2.5-flash",
        "label": "Legacy Gemini Flash alias via LiteLLM",
        "tier": "light",
    },
    {
        "id": "fast",
        "label": "Fast proxy alias via llm.seunegociofralib.site",
        "tier": "light",
    },
    {
        "id": "gpt-5.4-mini",
        "label": "Mini proxy alias via llm.seunegociofralib.site",
        "tier": "light",
    },
    {
        "id": "claude-sonnet-4-6",
        "label": "Sonnet alias via llm.seunegociofralib.site",
        "tier": "medium",
    },
    {
        "id": "claude-sonnet-4-20250514",
        "label": "Sonnet dated alias via llm.seunegociofralib.site",
        "tier": "medium",
    },
    {
        "id": "claude-3-5-sonnet",
        "label": "Claude 3.5 Sonnet alias via llm.seunegociofralib.site",
        "tier": "medium",
    },
    {
        "id": "claude-3-5-sonnet-20241022",
        "label": "Claude 3.5 Sonnet dated alias via llm.seunegociofralib.site",
        "tier": "medium",
    },
    {
        "id": "claude-3-5-sonnet-20240620",
        "label": "Claude 3.5 Sonnet dated alias via llm.seunegociofralib.site",
        "tier": "medium",
    },
    {
        "id": "claude-opus-4-7",
        "label": "Opus 4-7",
        "tier": "heavy",
    },
    {
        "id": "claude-opus-4-6",
        "label": "Opus 4-6",
        "tier": "heavy",
    },
    {
        "id": "claude-opus-4-8",
        "label": "Opus alias via llm.seunegociofralib.site",
        "tier": "heavy",
    },
    {
        "id": "claude-opus-4-20250514",
        "label": "Opus dated alias via llm.seunegociofralib.site",
        "tier": "heavy",
    },
    {
        "id": "deepseek-v4-flash",
        "label": "Legacy DeepSeek alias via LiteLLM",
        "tier": "medium",
    },
]

ALLOWED_PROXY_MODELS = frozenset(model["id"] for model in PROXY_MODEL_OPTIONS)
PROXY_LIGHT_MODEL = os.getenv("FRALIB_PROXY_LIGHT_MODEL", "claude-sonnet-4-6")
PROXY_DEFAULT_MODEL = os.getenv("FRALIB_PROXY_DEFAULT_MODEL", "claude-sonnet-4-6")
PROXY_BUILDER_MODEL = os.getenv("FRALIB_PROXY_BUILDER_MODEL", "claude-sonnet-4-6")


def is_proxy_model(model_id: str | None) -> bool:
    return (model_id or "").strip() in ALLOWED_PROXY_MODELS


def proxy_model_list_text() -> str:
    return ", ".join(sorted(ALLOWED_PROXY_MODELS))
