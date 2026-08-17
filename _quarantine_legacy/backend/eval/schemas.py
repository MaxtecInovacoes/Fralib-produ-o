from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """Single evaluation test case."""
    name: str = Field(..., description="Unique test case identifier")
    agent: str = Field(..., description="Target agent name (hunter, caio, franz, pipeline)")
    input: dict = Field(default_factory=dict, description="Input payload for the agent")
    expected: dict = Field(..., description="Expected output assertions")
    tolerance: dict = Field(default_factory=dict, description="Tolerance constraints (max_latency_ms, etc)")


class EvalResult(BaseModel):
    """Result of a single eval case execution."""
    case_name: str
    passed: bool
    latency_ms: float
    output: dict = Field(default_factory=dict)
    error: str | None = None


class EvalReport(BaseModel):
    """Aggregated report for an eval suite run."""
    suite_name: str
    total_cases: int
    passed: int
    failed: int
    avg_latency_ms: float
    results: list[EvalResult] = Field(default_factory=list)
    created_at: str = Field(..., description="ISO 8601 timestamp")
