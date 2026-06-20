import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "tenant_scope_audit.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("tenant_scope_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_py(path: Path, sql: str) -> Path:
    path.write_text(f"from sqlalchemy import text\nquery = text({sql!r})\n", encoding="utf-8")
    return path


def test_audit_flags_unscoped_pipeline_failures(tmp_path):
    audit = _load_audit_module()
    path = _write_py(
        tmp_path / "bad.py",
        "SELECT id, fase FROM pipeline_failures WHERE resolvido = FALSE",
    )

    findings = audit.audit_file(path)

    assert findings
    assert findings[0][1] == "pipeline_failures"


def test_audit_allows_tenant_scoped_jobs_query(tmp_path):
    audit = _load_audit_module()
    path = _write_py(
        tmp_path / "good.py",
        "SELECT id FROM jobs WHERE tenant_id = :tenant_id AND status = 'pending'",
    )

    assert audit.audit_file(path) == []


def test_audit_allows_user_scoped_leads_insert(tmp_path):
    audit = _load_audit_module()
    path = _write_py(
        tmp_path / "good_insert.py",
        "INSERT INTO leads (id, user_id, nome) VALUES (:id, :uid, :nome)",
    )

    assert audit.audit_file(path) == []


def test_audit_documents_metrics_and_alerting_as_global_exceptions():
    audit = _load_audit_module()

    assert "backend/endpoints/metrics_endpoints.py" in audit.SKIP_FILES
    assert "backend/services/alerting.py" in audit.SKIP_FILES
