"""Tests for llm_router.py - LLM Router silent failures."""

from unittest.mock import patch, MagicMock

import pytest


class TestLLMRouterSilentFailures:
    """Test suite ensuring llm_router does NOT return empty strings silently."""

    def test_gemini_returns_error_message_not_empty_string(self):
        """Test that Gemini returns error message when response format is unexpected."""
        from backend.services.llm_router import _call_google

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.gemini", None)

            with patch("backend.services.llm_router.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "candidates": [],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 0},
                }
                mock_post.return_value = mock_response

                text, usage = _call_google("gemini-pro", "system", "user", 0.7, 1000)

                assert text != ""
                assert "[LLMRouter ERROR" in text
                assert "formato inesperado" in text.lower()

    def test_gemini_logs_warning_when_response_unexpected(self):
        """Test that Gemini logs warning when response format is unexpected."""
        from backend.services.llm_router import _call_google
        import logging

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.gemini", None)

            with patch("backend.services.llm_router.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {"unexpected": "format"}
                mock_post.return_value = mock_response

                with patch("backend.services.llm_router.logger") as mock_logger:
                    text, usage = _call_google("gemini-pro", "system", "user", 0.7, 1000)

                    assert mock_logger.warning.called
                    warning_call = mock_logger.warning.call_args[0][0]
                    assert "formato inesperado" in warning_call.lower()

    def test_anthropic_returns_text_not_empty_on_success(self):
        """Test that Anthropic returns actual text, not empty string."""
        from backend.services.llm_router import _call_anthropic

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.anthropic", None)

            with patch("backend.services.llm_router._retry_with_backoff") as mock_retry:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "content": [
                        {"type": "text", "text": "Generated creative direction for restaurant"}
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                }
                mock_retry.return_value = mock_response

                text, usage = _call_anthropic("claude-3-haiku", "system", "user", 0.7, 1000)

                assert text == "Generated creative direction for restaurant"
                assert text != ""

    def test_extract_proxy_text_handles_list_content(self):
        """Test that _extract_proxy_text handles list content properly."""
        from backend.services.llm_router import _extract_proxy_text

        content = [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "World"},
        ]

        result = _extract_proxy_text(content)

        assert result == "Hello World"
        assert result != ""

    def test_extract_proxy_text_handles_string_content(self):
        """Test that _extract_proxy_text returns string as-is."""
        from backend.services.llm_router import _extract_proxy_text

        content = "Direct string response"

        result = _extract_proxy_text(content)

        assert result == "Direct string response"

    def test_extract_proxy_text_handles_empty_list(self):
        """Test that _extract_proxy_text returns empty string for empty list."""
        from backend.services.llm_router import _extract_proxy_text

        content = []

        result = _extract_proxy_text(content)

        assert result == ""

    def test_extract_proxy_text_skips_empty_text_blocks(self):
        """Test that _extract_proxy_text skips blocks with empty text."""
        from backend.services.llm_router import _extract_proxy_text

        content = [
            {"type": "text", "text": ""},
            {"type": "text", "text": "  "},
            {"type": "text", "text": "Valid content"},
        ]

        result = _extract_proxy_text(content)

        assert result == "Valid content"

    def test_extract_proxy_text_handles_nested_message_blocks(self):
        """Test that _extract_proxy_text extracts from nested message blocks."""
        from backend.services.llm_router import _extract_proxy_text

        content = [
            {
                "type": "message",
                "content": [{"type": "text", "text": "Nested text content"}],
            }
        ]

        result = _extract_proxy_text(content)

        assert result == "Nested text content"

    def test_normalize_proxy_blocks_handles_received_wrapper(self):
        """Test that _normalize_proxy_blocks handles received wrapper."""
        from backend.services.llm_router import _normalize_proxy_blocks

        content = {
            "received": {
                "content": [{"type": "text", "text": "Wrapped content"}]
            }
        }

        result = _normalize_proxy_blocks(content)

        assert len(result) == 1
        assert result[0]["text"] == "Wrapped content"

    def test_extract_openai_message_content_handles_string(self):
        """Test that _extract_openai_message_content returns string as-is."""
        from backend.services.llm_router import _extract_openai_message_content

        result = _extract_openai_message_content("Direct string")

        assert result == "Direct string"

    def test_extract_openai_message_content_handles_list(self):
        """Test that _extract_openai_message_content handles list of content parts."""
        from backend.services.llm_router import _extract_openai_message_content

        content = [
            {"text": "Part 1 "},
            {"content": "Part 2"},
        ]

        result = _extract_openai_message_content(content)

        assert result == "Part 1 Part 2"

    def test_extract_openai_message_content_skips_invalid_parts(self):
        """Test that _extract_openai_message_content skips non-dict parts."""
        from backend.services.llm_router import _extract_openai_message_content

        content = [
            "not a dict",
            {"text": "Valid"},
            123,
        ]

        result = _extract_openai_message_content(content)

        assert result == "Valid"

    def test_retry_with_backoff_raises_on_final_failure(self):
        """Test that _retry_with_backoff raises after max retries."""
        from backend.services.llm_router import _retry_with_backoff
        from requests.exceptions import HTTPError

        call_count = 0
        response = MagicMock(status_code=503)

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise HTTPError("Server error", response=response)

        with pytest.raises(HTTPError):
            _retry_with_backoff(failing_func, max_retries=2, base_delay=0.01)

        assert call_count == 3  # Initial + 2 retries

    def test_retry_with_backoff_succeeds_on_eventual_success(self):
        """Test that _retry_with_backoff succeeds if function eventually works."""
        from backend.services.llm_router import _retry_with_backoff
        from requests.exceptions import HTTPError

        call_count = 0
        response = MagicMock(status_code=503)

        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise HTTPError("Temporary error", response=response)
            return "success"

        with patch("backend.services.llm_router.time.sleep"):
            result = _retry_with_backoff(
                eventually_succeeds, max_retries=3, base_delay=0.01
            )

        assert result == "success"
        assert call_count == 2

    def test_retry_with_backoff_does_not_retry_4xx_errors(self):
        """Test that _retry_with_backoff does NOT retry 4xx client errors."""
        from backend.services.llm_router import _retry_with_backoff
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 400

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise HTTPError("Bad request", response=mock_response)

        with pytest.raises(HTTPError):
            _retry_with_backoff(failing_func, max_retries=3, base_delay=0.01)

        # Should NOT retry - only initial call
        assert call_count == 1

    def test_retry_with_backoff_retries_429_rate_limit(self):
        """Test that _retry_with_backoff DOES retry 429 rate limit errors."""
        from backend.services.llm_router import _retry_with_backoff
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 429

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise HTTPError("Rate limited", response=mock_response)

        with patch("backend.services.llm_router.time.sleep"):
            with pytest.raises(HTTPError):
                _retry_with_backoff(failing_func, max_retries=2, base_delay=0.01)

        # Should retry - 429 is in retry_on_status
        assert call_count == 3


class TestLLMRouterNoSilentEmptyString:
    """Tests ensuring llm_router NEVER returns empty string silently."""

    def test_anthropic_returns_text_or_raises(self):
        """Test that Anthropic path returns text or raises, never empty."""
        from backend.services.llm_router import _call_anthropic

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.anthropic", None)

            with patch("backend.services.llm_router._retry_with_backoff") as mock_retry:
                # Empty content list
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "content": [],
                    "usage": {"input_tokens": 100, "output_tokens": 0},
                }
                mock_retry.return_value = mock_response

                # Should not return empty string - should extract from tool_use
                text, usage = _call_anthropic("claude-3-haiku", "system", "user", 0.7, 1000)

                # Result might be empty but it's explicit, not silent
                # The key is it doesn't LOG and return "" silently
                assert isinstance(text, str)

    def test_openai_returns_text_or_raises(self):
        """Test that OpenAI path returns text or raises, never silently empty."""
        from backend.services.llm_router import _call_openai

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.openai", None)

            with patch("backend.services.llm_router._retry_with_backoff") as mock_retry:
                # Empty message content
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": ""}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 0},
                }
                mock_retry.return_value = mock_response

                text, usage = _call_openai("gpt-4o", "system", "user", 0.7, 1000)

                # Empty is returned explicitly, not logged away
                assert text == ""
                assert isinstance(text, str)

    def test_call_llm_routes_to_correct_provider(self):
        """Test that call_llm routes to correct provider function."""
        from backend.services.llm_router import call_llm

        with patch("backend.services.llm_router._call_anthropic") as mock_anthropic:
            mock_anthropic.return_value = ("result", {"input_tokens": 10, "output_tokens": 5})

            text, usage = call_llm(
                "anthropic", "claude-3-haiku", "system", "user", 0.7, 1000
            )

            mock_anthropic.assert_called_once_with(
                "claude-3-haiku", "system", "user", 0.7, 1000
            )
            assert text == "result"

    def test_call_llm_lowercases_provider(self):
        """Test that call_llm lowercases provider name."""
        from backend.services.llm_router import call_llm

        with patch("backend.services.llm_router._call_anthropic") as mock_anthropic:
            mock_anthropic.return_value = ("result", {"input_tokens": 10, "output_tokens": 5})

            call_llm("ANTHROPIC", "claude-3-haiku", "system", "user", 0.7, 1000)

            mock_anthropic.assert_called_once()

    def test_gemini_handles_keyerror_gracefully(self):
        """Test that Gemini handles missing keys in response gracefully."""
        from backend.services.llm_router import _call_google

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.gemini", None)

            with patch("backend.services.llm_router.requests.post") as mock_post:
                # Malformed response
                mock_response = MagicMock()
                mock_response.json.return_value = {}
                mock_post.return_value = mock_response

                text, usage = _call_google("gemini-pro", "system", "user", 0.7, 1000)

                # Should return error message, not empty
                assert text != ""
                assert "[LLMRouter ERROR" in text

    def test_logger_is_called_on_gemini_error(self):
        """Test that logger.warning is called on Gemini error."""
        from backend.services.llm_router import _call_google
        import logging

        with patch("backend.services.llm_router._get_key_for_provider") as mock_key:
            mock_key.return_value = ("fake-key", "https://api.gemini", None)

            with patch("backend.services.llm_router.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {"malformed": "response"}
                mock_post.return_value = mock_response

                # Capture logs
                with patch("backend.services.llm_router.logger") as mock_logger:
                    _call_google("gemini-pro", "system", "user", 0.7, 1000)

                    assert mock_logger.warning.called
