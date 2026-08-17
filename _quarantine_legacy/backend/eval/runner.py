import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .schemas import EvalCase, EvalReport, EvalResult

logger = logging.getLogger("eval_runner")


def load_eval_suite(path: str) -> list[EvalCase]:
    """Load eval cases from a JSON file."""
    suite_path = Path(path)
    if not suite_path.exists():
        raise FileNotFoundError(f"Eval suite not found: {path}")

    with open(suite_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cases: list[EvalCase] = []
    for item in raw:
        try:
            cases.append(EvalCase.model_validate(item))
        except Exception as exc:
            logger.warning("Skipping invalid eval case: %s — %s", item.get("name"), exc)

    logger.info("Loaded %d eval cases from %s", len(cases), path)
    return cases


def _check_expected(output: dict, expected: dict) -> bool:
    """Compare agent output against expected assertions.

    Supported operators in expected values:
    - plain value: exact match (==)
    - string starting with ">": numeric greater-than (e.g., ">0", ">50")
    - string starting with "<": numeric less-than
    - string starting with "~": approximate match (assertIn for strings)
    """
    for key, expected_value in expected.items():
        if expected_value is None:
            continue

        actual = output.get(key)

        if isinstance(expected_value, str) and expected_value.startswith(">"):
            try:
                threshold = float(expected_value[1:])
                if not isinstance(actual, (int, float)) or actual <= threshold:
                    logger.debug("Key '%s': %s !> %s", key, actual, threshold)
                    return False
            except (ValueError, TypeError):
                return False
        elif isinstance(expected_value, str) and expected_value.startswith("<"):
            try:
                threshold = float(expected_value[1:])
                if not isinstance(actual, (int, float)) or actual >= threshold:
                    logger.debug("Key '%s': %s !< %s", key, actual, threshold)
                    return False
            except (ValueError, TypeError):
                return False
        elif isinstance(expected_value, str) and expected_value.startswith("~"):
            if actual is None or expected_value[1:] not in str(actual):
                logger.debug("Key '%s': '%s' not in '%s'", key, expected_value[1:], actual)
                return False
        else:
            if actual != expected_value:
                logger.debug("Key '%s': %s != %s", key, actual, expected_value)
                return False

    return True


def run_eval(agent_fn: Callable[[dict], Any], eval_cases: list[EvalCase]) -> EvalReport:
    """Execute eval cases against an agent function.

    Args:
        agent_fn: callable that receives the case.input dict and returns the result.
        eval_cases: list of EvalCase to run.

    Returns:
        EvalReport with aggregated results.
    """
    results: list[EvalResult] = []
    suite_name = "unnamed"

    for case in eval_cases:
        suite_name = case.agent
        start = time.perf_counter()
        passed = False
        output: dict = {}
        error: Optional[str] = None

        try:
            raw_output = agent_fn(case.input)

            if isinstance(raw_output, dict):
                output = raw_output
            elif hasattr(raw_output, "model_dump"):
                output = raw_output.model_dump()
            elif hasattr(raw_output, "dict"):
                output = raw_output.dict()
            else:
                output = {"_raw": str(raw_output)}

            max_latency = case.tolerance.get("max_latency_ms", 0)
            latency_ms = (time.perf_counter() - start) * 1000

            if max_latency and latency_ms > max_latency:
                passed = False
                error = f"Latency {latency_ms:.0f}ms exceeded max {max_latency}ms"
            else:
                passed = _check_expected(output, case.expected)

        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("Eval case '%s' errored: %s", case.name, error)

        results.append(
            EvalResult(
                case_name=case.name,
                passed=passed,
                latency_ms=round(latency_ms, 2),
                output=output,
                error=error,
            )
        )

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    avg_latency = (
        sum(r.latency_ms for r in results) / total if total > 0 else 0.0
    )

    report = EvalReport(
        suite_name=suite_name,
        total_cases=total,
        passed=passed_count,
        failed=total - passed_count,
        avg_latency_ms=round(avg_latency, 2),
        results=results,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        "Eval complete: %d/%d passed (%.1f%%), avg %.0fms",
        passed_count,
        total,
        (passed_count / total * 100) if total else 0,
        avg_latency,
    )
    return report


def run_pipeline_eval(pipeline_fn: Callable[[dict], Any], suite_path: str) -> EvalReport:
    """Load a suite and evaluate against the full pipeline function."""
    cases = load_eval_suite(suite_path)
    return run_eval(pipeline_fn, cases)


def save_report(report: EvalReport, path: str) -> None:
    """Save the eval report as JSON to the given path."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    payload = report.model_dump(mode="json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Report saved to %s", path)
