from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.vite_renderer_models import cap_max_tokens_for_model, normalize_model_alias


def test_normalize_model_alias_groups_known_builder_models():
    assert normalize_model_alias("claude-sonnet-4-6") == "sonnet"
    assert normalize_model_alias("claude-3-5-sonnet-20241022") == "sonnet"
    assert normalize_model_alias("claude-haiku-4-5") == "haiku"
    assert normalize_model_alias("claude-opus-4-8") == "opus"
    assert normalize_model_alias("custom-model") == "custom-model"


def test_cap_max_tokens_uses_real_model_caps():
    assert cap_max_tokens_for_model("claude-sonnet-4-6", 50000) == 16384
    assert cap_max_tokens_for_model("claude-3-5-sonnet", 50000) == 8192
    assert cap_max_tokens_for_model("claude-haiku-4-5", 50000) == 8192


def test_cap_max_tokens_defaults_and_minimum():
    assert cap_max_tokens_for_model("some-sonnet-model", 50000) == 16384
    assert cap_max_tokens_for_model("some-haiku-model", 50000) == 8192
    assert cap_max_tokens_for_model("unknown", 0) == 8192
    assert cap_max_tokens_for_model("unknown", 200) == 1024
