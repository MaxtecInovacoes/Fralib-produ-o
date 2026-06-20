"""Tests for vite_file_extractor module."""

import pytest
import json


class TestExtractViteProjectFiles:
    """Test file extraction from LLM responses."""

    def test_extract_direct_json(self):
        """Test extraction from direct JSON response."""
        from backend.services.vite_file_extractor import extract_vite_project_files

        raw = json.dumps({
            "files": {
                "package.json": '{"name": "test"}',
                "index.html": "<html></html>",
            }
        })

        result = extract_vite_project_files(raw)
        assert "package.json" in result
        assert "index.html" in result

    def test_extract_from_markdown(self):
        """Test extraction from markdown code block."""
        from backend.services.vite_file_extractor import extract_vite_project_files

        raw = '''
```json
{
  "files": {
    "vite.config.ts": "export default {}"
  }
}
```
'''
        result = extract_vite_project_files(raw)
        assert "vite.config.ts" in result


class TestCleanJsonBlock:
    """Test JSON block cleaning."""

    def test_remove_markdown_fences(self):
        """Test removal of markdown code fences."""
        from backend.services.vite_file_extractor import _clean_json_block

        raw = '''
```json
{"key": "value"}
```
'''
        result = _clean_json_block(raw)
        assert not result.startswith("```")
        assert not result.endswith("```")

    def test_find_json_start(self):
        """Test finding JSON start in mixed content."""
        from backend.services.vite_file_extractor import _clean_json_block

        raw = "Some text before\n{\"files\": {}}\nmore text"
        result = _clean_json_block(raw)
        assert result.startswith('{"')


class TestNormalizeModelAlias:
    """Test model alias normalization."""

    def test_known_alias(self):
        """Test normalization of known aliases."""
        from backend.services.vite_file_extractor import _normalize_model_alias

        assert _normalize_model_alias("gpt-4o") == "gpt-4o"
        assert _normalize_model_alias("GPT-4O") == "gpt-4o"

    def test_unknown_alias_passthrough(self):
        """Test unknown aliases pass through unchanged."""
        from backend.services.vite_file_extractor import _normalize_model_alias

        result = _normalize_model_alias("unknown-model-v1")
        assert result == "unknown-model-v1"


class TestNormalizeText:
    """Test text normalization."""

    def test_lowercase(self):
        """Test text is lowercased."""
        from backend.services.vite_file_extractor import _normalize_text

        result = _normalize_text("Hello WORLD")
        assert result == "hello world"

    def test_whitespace_normalized(self):
        """Test whitespace is normalized."""
        from backend.services.vite_file_extractor import _normalize_text

        result = _normalize_text("hello   world\n\ttab")
        assert "  " not in result
        assert "\n" not in result
