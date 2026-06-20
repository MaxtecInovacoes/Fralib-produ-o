"""Standalone test runner for performance tests - bypasses conftest.py."""

from __future__ import annotations

import sys
import os
import time
import traceback
from pathlib import Path

# Ensure no conftest interference
_test_dir = Path(__file__).parent
os.chdir(_test_dir.parent.parent)  # Go to project root

def run_pytest_style_tests(test_module_name: str, test_file_path: str) -> tuple[int, int, float]:
    """Run pytest-style tests from a file."""
    import importlib.util

    total_tests = 0
    failed_tests = 0
    errors = []

    # Load the test module
    spec = importlib.util.spec_from_file_location(test_module_name, test_file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[test_module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"  ERROR loading module: {e}")
            return 0, 1, 0.0

    # Find all test functions
    test_funcs = []
    for name in dir(module):
        if name.startswith('Test'):
            cls = getattr(module, name)
            if isinstance(cls, type):
                for method_name in dir(cls):
                    if method_name.startswith('test_'):
                        test_funcs.append((cls, method_name))

    total_tests = len(test_funcs)
    start_time = time.time()

    for cls, method_name in test_funcs:
        test_instance = cls()
        test_func = getattr(test_instance, method_name)

        # Get fixtures
        fixtures = {}
        for fixture_name in getattr(test_instance, '__dict__', {}):
            if fixture_name.startswith('_') or fixture_name.startswith('test_'):
                continue
            if callable(getattr(test_instance, fixture_name, None)):
                try:
                    fixtures[fixture_name] = getattr(test_instance, fixture_name)()
                except Exception:
                    pass

        try:
            # Try to call with fixtures
            try:
                test_func(**fixtures)
            except TypeError:
                # Try without fixtures
                test_func()

            print(f"  PASS {cls.__name__}.{method_name}")
        except Exception as e:
            print(f"  FAIL {cls.__name__}.{method_name}: {e}")
            failed_tests += 1
            errors.append((cls.__name__, method_name, str(e)))

    elapsed = time.time() - start_time
    return total_tests, failed_tests, elapsed


def main():
    """Run all performance tests."""
    # Get project root (parent of tests directory)
    project_root = Path(__file__).parent.parent.resolve()

    test_files = [
        ("TestPipelineSpeed", project_root / "tests/performance/test_pipeline_speed.py"),
        ("TestSEOCompliance", project_root / "tests/performance/test_seo_compliance.py"),
        ("TestPreRenderOutput", project_root / "tests/performance/test_pre_render.py"),
        ("TestDesignDirectorCache", project_root / "tests/unit/test_design_director_cache.py"),
        ("TestNodeModulesCache", project_root / "tests/unit/test_cache_node_modules.py"),
    ]

    all_results = []
    total_all = 0
    total_failed = 0

    print("="*70)
    print("PERFORMANCE AND CACHE TESTS")
    print("="*70)
    print()

    for module_name, test_file in test_files:
        print(f"Running {test_file.name}...")
        total, failed, elapsed = run_pytest_style_tests(module_name, test_file)
        all_results.append((test_file.name, total, failed, elapsed))
        total_all += total
        total_failed += failed
        print(f"  -> {total - failed}/{total} passed in {elapsed:.2f}s")
        print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"{'File':<45} {'Passed':>8} {'Failed':>8} {'Time':>10}")
    print("-"*70)
    for name, total, failed, elapsed in all_results:
        passed = total - failed
        print(f"{name:<45} {passed:>8} {failed:>8} {elapsed:>9.2f}s")
    print("-"*70)
    print(f"{'TOTAL':<45} {total_all - total_failed:>8} {total_failed:>8}")
    print()

    score = f"{(total_all - total_failed)}/{total_all}"
    print(f"SCORE: {score}")
    print()

    if total_failed == 0:
        print("ALL TESTS PASSING!")
        return 0
    else:
        print(f"WARNING: {total_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
