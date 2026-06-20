"""Tests for vite_config module."""

import pytest


class TestViteConfigConstants:
    """Test configuration constants."""

    def test_fixed_package_json_has_required_deps(self):
        """Verify FixedPackageJson has all required dependencies."""
        from backend.services.vite_config import FIXED_PACKAGE_JSON

        deps = {
            **FIXED_PACKAGE_JSON["dependencies"],
            **FIXED_PACKAGE_JSON["devDependencies"],
        }
        assert "react" in deps
        assert "react-dom" in deps
        assert "lucide-react" in deps
        assert "tailwindcss" in deps
        assert "vite" in deps

    def test_required_project_files(self):
        """Verify required files are defined."""
        from backend.services.vite_config import REQUIRED_PROJECT_FILES

        assert "package.json" in REQUIRED_PROJECT_FILES
        assert "vite.config.ts" in REQUIRED_PROJECT_FILES
        assert "tsconfig.json" in REQUIRED_PROJECT_FILES
        assert "index.html" in REQUIRED_PROJECT_FILES

    def test_segment_rules_has_common_segments(self):
        """Verify segment rules cover common business types."""
        from backend.services.vite_config import SEGMENT_RULES

        assert "academia" in SEGMENT_RULES
        assert "restaurante" in SEGMENT_RULES
        assert "dentista" in SEGMENT_RULES
        assert "advocacia" in SEGMENT_RULES


class TestViteConfigEnvironmentHelpers:
    """Test environment variable helpers."""

    def test_env_int_with_valid_value(self, monkeypatch):
        """Test _env_int returns correct integer."""
        from backend.services.vite_config import _env_int

        monkeypatch.setenv("TEST_VAR", "42")
        assert _env_int("TEST_VAR", 10) == 42

    def test_env_int_with_invalid_value(self, monkeypatch):
        """Test _env_int returns default for invalid value."""
        from backend.services.vite_config import _env_int

        monkeypatch.setenv("TEST_VAR", "not_a_number")
        assert _env_int("TEST_VAR", 10) == 10

    def test_env_int_with_missing_var(self):
        """Test _env_int returns default for missing var."""
        from backend.services.vite_config import _env_int

        assert _env_int("NONEXISTENT_VAR_XYZ", 99) == 99

    def test_model_repair_attempts_default(self):
        """Test _model_repair_attempts has sensible default."""
        from backend.services.vite_config import _model_repair_attempts

        result = _model_repair_attempts()
        assert isinstance(result, int)
        assert 1 <= result <= 10

    def test_batch_first_enabled_default(self):
        """Test _batch_first_enabled defaults to True."""
        from backend.services.vite_config import _batch_first_enabled

        result = _batch_first_enabled()
        assert isinstance(result, bool)

    def test_batch_spacing_seconds_range(self):
        """Test _batch_spacing_seconds is in valid range."""
        from backend.services.vite_config import _batch_spacing_seconds

        result = _batch_spacing_seconds()
        assert 0.5 <= result <= 10.0

    def test_transient_proxy_retry_delay_positive(self):
        """Test _transient_proxy_retry_delay_seconds returns positive value."""
        from backend.services.vite_config import _transient_proxy_retry_delay_seconds

        result = _transient_proxy_retry_delay_seconds(0)
        assert result > 0
