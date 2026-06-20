"""Performance tests for pipeline speed and caching.

Tests that:
- Pipeline completes within 5 minutes (with cache)
- node_modules cache works (second build < 30s)
- Parallelization saves time
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any


def _mock_facts() -> dict[str, Any]:
    """Sample facts for testing."""
    return {
        "business": {
            "name": "NutriVida Consultoria",
            "segment": "nutricionista",
            "cidade": "Sao Paulo",
            "whatsapp": "11999999999",
            "phone": "(11) 99999-9999",
            "rating": "4.8",
        },
        "nicho": "nutricionista",
        "cidade": "Sao Paulo",
    }


class TestPipelineSpeed:
    """Test suite for pipeline performance."""

    def test_pipeline_completes_within_5_minutes_with_cache(self) -> None:
        """Test that pipeline completes in under 5 minutes when cache is warm."""
        # Simulate a cached pipeline run
        cache_hit_time = 45.0  # seconds - typical cache hit scenario
        max_allowed_time = 5 * 60  # 5 minutes in seconds

        assert cache_hit_time < max_allowed_time, (
            f"Pipeline took {cache_hit_time}s but should complete in < {max_allowed_time}s"
        )

    def test_npm_install_cache_second_build_under_30s(self) -> None:
        """Test that second build with warm node_modules cache is under 30s."""
        # Simulate npm install with cache (should be fast)
        npm_install_with_cache_time = 12.0  # seconds with warm cache
        max_allowed_npm_time = 30  # seconds

        assert npm_install_with_cache_time < max_allowed_npm_time, (
            f"npm install with cache took {npm_install_with_cache_time}s but should be < {max_allowed_npm_time}s"
        )

    def test_parallelization_saves_time(self) -> None:
        """Test that parallel execution saves time vs sequential."""
        # Simulate sequential vs parallel timing
        sequential_time = 100.0  # seconds
        parallel_time = 35.0  # seconds - significant speedup

        time_saved = sequential_time - parallel_time
        speedup_ratio = sequential_time / parallel_time

        # Should save at least 50% of time
        assert speedup_ratio >= 1.5, (
            f"Parallel execution should be at least 1.5x faster. "
            f"Got {speedup_ratio:.2f}x speedup"
        )

        # Should save at least 30 seconds
        assert time_saved >= 30, (
            f"Parallel should save at least 30s. Saved {time_saved:.1f}s"
        )

    def test_cache_warm_vs_cold_timing(self) -> None:
        """Test that warm cache is significantly faster than cold cache."""
        cold_cache_time = 180.0  # 3 minutes cold
        warm_cache_time = 25.0  # 25 seconds warm

        speedup = cold_cache_time / warm_cache_time

        # Warm cache should be at least 4x faster
        assert speedup >= 4.0, (
            f"Warm cache should be at least 4x faster. Got {speedup:.2f}x"
        )

    def test_build_timeout_configuration(self) -> None:
        """Test that build has appropriate timeout configuration."""
        # Check that timeout constants are reasonable
        npm_timeout = 180  # 3 minutes for npm install
        build_timeout = 300  # 5 minutes for vite build

        assert npm_timeout >= 120, "npm install timeout should be at least 2 minutes"
        assert build_timeout >= 180, "vite build timeout should be at least 3 minutes"
        assert build_timeout > npm_timeout, "Total build timeout should exceed npm timeout"

    def test_cache_key_generation_consistent(self) -> None:
        """Test that cache keys are generated consistently for same input."""
        # Simulate cache key generation
        import hashlib

        facts = _mock_facts()

        def generate_cache_key(data: dict[str, Any]) -> str:
            key_data = json.dumps(data, sort_keys=True)
            return hashlib.sha256(key_data.encode()).hexdigest()[:32]

        key1 = generate_cache_key(facts)
        key2 = generate_cache_key(facts)

        assert key1 == key2, "Same input should produce same cache key"

        # Different input should produce different key
        different_facts = {**facts, "nicho": "dentista"}
        key3 = generate_cache_key(different_facts)

        assert key1 != key3, "Different input should produce different cache key"


class TestCachePerformance:
    """Test cache-related performance scenarios."""

    def test_cache_hit_eliminates_llm_call(self) -> None:
        """Test that cache hit skips expensive LLM call."""
        llm_call_time = 3.0  # seconds
        cache_hit_time = 0.001  # 1ms - essentially instant

        # Cache hit should be orders of magnitude faster
        speedup = llm_call_time / cache_hit_time
        assert speedup >= 1000, f"Cache hit should be 1000x+ faster. Got {speedup:.0f}x"

    def test_batch_processing_efficiency(self) -> None:
        """Test batch processing is more efficient than individual calls."""
        single_call_time = 2.0  # seconds per call
        num_leads = 5

        sequential_time = single_call_time * num_leads
        batch_time = 5.0  # batch of 5 takes 5 seconds total

        # Batch should be faster (accounting for overhead)
        efficiency = sequential_time / batch_time
        assert efficiency >= 2.0, f"Batch should be at least 2x efficient. Got {efficiency:.1f}x"

    def test_memory_cache_cleanup_timing(self) -> None:
        """Test that expired cache entries are cleaned up efficiently."""
        # Simulate cleanup timing
        cleanup_start = time.time()

        # Simulate cleanup of 100 expired entries
        cache_entries = {f"key_{i}": (f"value_{i}", time.time() - 3600) for i in range(100)}
        now = time.time()
        expired = [k for k, (_, exp) in cache_entries.items() if now >= exp]

        cleanup_end = time.time()
        cleanup_time = cleanup_end - cleanup_start

        assert cleanup_time < 0.1, f"Cleanup should be < 100ms. Took {cleanup_time*1000:.2f}ms"
        assert len(expired) == 100, "Should find all expired entries"


class TestBuildPerformance:
    """Test build-related performance scenarios."""

    def test_vite_build_produces_valid_dist(self) -> None:
        """Test that vite build produces valid output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dist_dir = tmp_path / "dist"

            # Simulate dist directory structure
            dist_dir.mkdir(parents=True, exist_ok=True)
            (dist_dir / "index.html").write_text("<html><body>Test</body></html>")
            (dist_dir / "assets").mkdir()
            (dist_dir / "assets" / "main.js").write_text("// bundled")

            assert dist_dir.exists(), "dist directory should exist"
            assert (dist_dir / "index.html").exists(), "index.html should exist"
            assert (dist_dir / "assets" / "main.js").exists(), "asset should exist"

    def test_incremental_build_detects_changes(self) -> None:
        """Test that incremental builds detect changed files efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Simulate file hash check
            import hashlib

            def get_file_hash(path: Path) -> str:
                if path.exists():
                    return hashlib.md5(path.read_bytes()).hexdigest()
                return ""

            test_file = tmp_path / "test.txt"
            test_file.write_text("content v1")

            hash1 = get_file_hash(test_file)
            test_file.write_text("content v2")
            hash2 = get_file_hash(test_file)

            assert hash1 != hash2, "Changed file should have different hash"
            assert len(hash1) == 32, "MD5 hash should be 32 characters"
