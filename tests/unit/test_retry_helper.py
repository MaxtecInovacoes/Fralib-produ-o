"""Testes para retry_helper — retry 3x com backoff, sem fallback silencioso."""

from __future__ import annotations

import time

import pytest

from backend.services.retry_helper import (
    retry_with_backoff,
    async_retry_with_backoff,
    DEFAULT_MAX_RETRIES,
)


class TestSyncRetry:
    def test_success_first_try_no_retry(self) -> None:
        calls = []

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def func() -> str:
            calls.append(1)
            return "ok"

        assert func() == "ok"
        assert len(calls) == 1

    def test_success_second_try(self) -> None:
        calls = []

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def func() -> str:
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("transient")
            return "ok"

        assert func() == "ok"
        assert len(calls) == 2

    def test_success_third_try(self) -> None:
        calls = []

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def func() -> str:
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("transient")
            return "ok"

        assert func() == "ok"
        assert len(calls) == 3

    def test_fail_after_max_retries_raises(self) -> None:
        calls = []

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def func() -> str:
            calls.append(1)
            raise RuntimeError("persistent failure")

        with pytest.raises(RuntimeError, match="persistent failure"):
            func()
        assert len(calls) == 3

    def test_default_max_retries_is_3(self) -> None:
        assert DEFAULT_MAX_RETRIES == 3

    def test_no_fallback_value_returned(self) -> None:
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def func() -> str:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            func()


class TestAsyncRetry:
    @pytest.mark.asyncio
    async def test_async_success(self) -> None:
        calls = []

        @async_retry_with_backoff(max_retries=3, base_delay=0.01)
        async def func() -> str:
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("transient")
            return "ok"

        result = await func()
        assert result == "ok"
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_async_fail_propagates(self) -> None:
        @async_retry_with_backoff(max_retries=3, base_delay=0.01)
        async def func() -> str:
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            await func()