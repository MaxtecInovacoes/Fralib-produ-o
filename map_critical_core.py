"""FraLib Critical Core Dependency-Graph Audit.
Traces AST imports recursively from real entrypoints, classifies by architectural
layer, audits health, and emits critical_core_report.json + .md.
NO code mutation. Read-only inspection.
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {"__pycache__", "_arquivo"}
OUTPUT_JSON = ROOT / "critical_core_report.json"
OUTPUT_MD = ROOT / "critical_core_report.md"

# ── Layer classifiers (match against POSIX-style relative path) ─────────────
LAYER_1_DB = re.compile(
    r"(database|auth|session|model|tenant|db_import|jwt|schema_init|proxy_model)", re.I
)
LAYER_2_PIPELINE = re.compile(
    r"(pipeline|job_queue|state_machine|ledger|queue_manager|watchdog|checkpoint|pipeline_)",
    re.I,
)
LAYER_3_AGENTS = re.compile(
    r"(agents?|hunter|caio|arquiteto|builder|design_director|deploy|seo|franz|"
    r"sdr_|quality_gate|openui|html_|visual_|cinematic|validation_enforcer)",
    re.I,
)
LAYER_4_LEAD_SUPPLY = re.compile(
    r"(lead_supply|credits|quota|cooldown|lead_provider|manual_provider|maps_provider|"
    r"cakto|webhook|checkout|provider_key|provider_alert)",
    re.I,
)
LAYER_5_ROUTES = re.compile(r"(endpoint|router_setup)", re.I)
LAYER_6_SCHEMAS = re.compile(r"(schema|contract)", re.I)

RE_JSON_TRUNCATION = re.compile(r"json\.dumps?\s*\(.*\)\s*\[", re.S)
RE_HTML_REGEX = re.compile(r"re\.(compile|sub|search|match)\s*\(.*<[^>]*>", re.S)
RE_BAK = re.compile(r"\.(bak|tmp|old)(\.|$)", re.I)


# ── Module-level registry (flat, no closures) ───────────────────────────────
_registry: dict[str, Path] = {}          # rel_posix -> abs
_registry_tree: dict[str, Optional[ast.AST]] = {}
_registry_imports: dict[str, set[str]] = {}  # top-level module names


def _safe_parse(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def _top_imports(tree: ast.AST) -> set[str]:
    tops: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            tops.add(node.module.split(".")[0])
    return tops


def _is_router_inst(tree: Optional[ast.AST]) -> bool:
    if tree is None:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in {"APIRouter", "FastAPI"}:
                return True
    return False


def register(abs_p: Path, rel: str) -> None:
    if rel in _registry:
        return
    _registry[rel] = abs_p
    tree = _safe_parse(abs_p)
    _registry_tree[rel] = tree
    _registry_imports[rel] = _top_imports(tree) if tree else set()


def classify_layer(rel: str) -> str:
    if LAYER_6_SCHEMAS.search(rel):
        return "LAYER_6_SCHEMAS_CONTRACTS"
    if LAYER_1_DB.search(rel):
        return "LAYER_1_CORE_DATABASE"
    if LAYER_4_LEAD_SUPPLY.search(rel):
        return "LAYER_4_LEAD_SUPPLY"
    if LAYER_3_AGENTS.search(rel):
        return "LAYER_3_AI_AGENTS"
    if LAYER_2_PIPELINE.search(rel):
        return "LAYER_2_PIPELINE_ENGINE"
    if LAYER_5_ROUTES.search(rel):
        return "LAYER_5_ACTIVE_ROUTES"
    return "LAYER_UNCLASSIFIED"


def audit_health(path: Path, tree: Optional[ast.AST], src: str) -> list[dict]:
    issues: list[dict] = []
    if not tree:
        return issues

    # 1. async def touching session/DB
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                body = ast.unparse(node)
                # Strip FastAPI request.session dict access and URL path strings
                # before scanning — both trigger false positives on the heuristic.
                clean = re.sub(r'request\.session\b', '', body)
                clean = re.sub(r'["\'][^"\']*session[^"\']*["\']', '', clean)
                if re.search(
                    r"\bsession(\.|\(|query|execute|commit|rollback|close)", clean
                ):
                    issues.append(
                        {
                            "rule": "ASYNC_DB_SYNC_MISMATCH",
                            "severity": "critical",
                            "detail": f"async def '{node.name}' accesses session/DB synchronously",
                        }
                    )
                    break
    except Exception:
        pass

    # 2. SessionLocal duplication
    sessionlocal_count = len(re.findall(r"SessionLocal\s*=|sessionmaker\s*\(", src))
    if sessionlocal_count > 1:
        issues.append(
            {
                "rule": "SESSIONLOCAL_DUPLICATED",
                "severity": "critical",
                "detail": f"{sessionlocal_count} SessionLocal instantiations in file",
            }
        )

    # 3. JSON blind truncation
    if RE_JSON_TRUNCATION.search(src):
        issues.append(
            {
                "rule": "JSON_BLIND_TRUNCATION",
                "severity": "warning",
                "detail": "json.dumps(...) slice truncation detected",
            }
        )

    # 4. HTML parsing via regex
    if RE_HTML_REGEX.search(src):
        issues.append(
            {
                "rule": "HTML_FRAGILE_REGEX",
                "severity": "warning",
                "detail": "HTML parsing via regex detected",
            }
        )

    # 5. Duplicated top-level imports
    tops = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            tops.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            tops.append(node.module.split(".")[0])
    dupes = sorted({m for m in set(tops) if tops.count(m) > 1})
    if dupes:
        issues.append(
            {
                "rule": "IMPORT_DUPLICATED",
                "severity": "warning",
                "detail": f"duplicated top-level imports: {dupes}",
            }
        )

    # 6. Missing f-string prefix (3+ lines with {} placeholder, no f prefix)
    suspects = 0
    for line in src.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        has_f = re.match(r"^f['\"ru]", s) is not None
        has_placeholder = re.search(r"(?<!{){[A-Za-z_][\w]*(?![^}]*?})", s) is not None
        if not has_f and has_placeholder and len(s) < 200:
            suspects += 1
    if suspects >= 3:
        issues.append(
            {
                "rule": "MISSING_FSTRING_PREFIX",
                "severity": "info",
                "detail": f"~{suspects} lines with {{}} placeholders without f-prefix",
            }
        )

    return issues


# ── Discovery ───────────────────────────────────────────────────────────────
def discover_python_files(root: Path) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith(".py") and not fname.startswith(".") and not RE_BAK.search(fname):
                p = Path(dirpath) / fname
                out.append((p, p.relative_to(root).as_posix()))
    return out


# ── Entrypoints ─────────────────────────────────────────────────────────────
_BASE_ENTRYPOINTS = [
    "server.py",
    "backend/agent_router.py",
    "backend/pipeline_queue_manager.py",
    "backend/pipeline_ledger.py",
    "backend/dreaming_job.py",
    "backend/whatsapp_listener.py",
    "backend/agents/manager/agent.py",
    "backend/services/lead_supply_engine.py",
    "openui-service-wandb/backend/openui/server.py",
]

_BASE_ENDPOINT_DIRS = [
    ROOT / "backend" / "endpoints",
    ROOT / "endpoints",
]


def _resolve_entrypoints() -> list[str]:
    eps = list(_BASE_ENTRYPOINTS)
    for d in _BASE_ENDPOINT_DIRS:
        if d.is_dir():
            for p in sorted(d.glob("*.py")):
                if not RE_BAK.search(p.name):
                    rel = p.relative_to(ROOT).as_posix()
                    if rel not in eps:
                        eps.append(rel)
    return eps


DISCOVERED_ENTRYPOINTS = _resolve_entrypoints()


# ── Graph walk (flat, no closures) ─────────────────────────────────────────
def trace_graph(entrypoints: list[str]) -> tuple[set[str], dict[str, set[str]]]:
    active: set[str] = set()
    reverse_deps: dict[str, set[str]] = {}

    queue = list(entrypoints)
    while queue:
        rel = queue.pop(0)
        if rel in active:
            continue
        if rel not in _registry:
            print(f"[WARN] entrypoint missing from registry: {rel}")
            continue
        active.add(rel)
        for top in _registry_imports.get(rel, set()):
            # candidates: top.py, top/__init__.py, backend/top/__init__.py
            for cand in (
                [f"{top}.py", f"{top}/__init__.py", f"backend/{top}/__init__.py"]
                + ([f"{top.replace('.', '/')}.py"] if "." in top else [])
            ):
                if cand in _registry and cand not in active:
                    queue.append(cand)
                    reverse_deps.setdefault(cand, set()).add(rel)
    return active, reverse_deps


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    print("[*] Discovery: scanning .py files ...")
    discovered = discover_python_files(ROOT)
    total_scanned = len(discovered)
    print(f"    {total_scanned} .py files scanned under {ROOT}")

    for abs_p, rel in discovered:
        register(abs_p, rel)

    print("[*] Tracing dependency graph from entrypoints ...")
    active_rel, reverse_deps = trace_graph(DISCOVERED_ENTRYPOINTS)
    print(f"    Active files: {len(active_rel)}")

    # classify + audit
    LAYERS = [
        "LAYER_1_CORE_DATABASE",
        "LAYER_2_PIPELINE_ENGINE",
        "LAYER_3_AI_AGENTS",
        "LAYER_4_LEAD_SUPPLY",
        "LAYER_5_ACTIVE_ROUTES",
        "LAYER_6_SCHEMAS_CONTRACTS",
    ]
    layer_buckets: dict[str, list[str]] = {k: [] for k in LAYERS}
    per_file: dict[str, dict] = {}
    clean = warning = critical = 0

    for rel in sorted(active_rel):
        abs_p = _registry[rel]
        tree = _registry_tree[rel]
        src = (
            abs_p.read_text(encoding="utf-8", errors="replace") if abs_p.exists() else ""
        )
        layer = classify_layer(rel)
        layer_buckets.setdefault(layer, []).append(rel)
        issues = audit_health(abs_p, tree, src)
        sevs = {i["severity"] for i in issues}
        if "critical" in sevs:
            critical += 1
        elif "warning" in sevs:
            warning += 1
        else:
            clean += 1
        per_file[rel] = {
            "layer": layer,
            "size_bytes": abs_p.stat().st_size if abs_p.exists() else 0,
            "has_fastapi_router": _is_router_inst(tree),
            "issues": issues,
            "issue_count": len(issues),
            "incoming": sorted(reverse_deps.get(rel, set())),
        }

    orphaned = sorted(set(r for _, r in discovered) - active_rel)

    top_priority = sorted(
        [
            {
                "file_path": rel,
                "layer": per_file[rel]["layer"],
                "critical_issues_count": sum(
                    1 for i in per_file[rel]["issues"] if i["severity"] == "critical"
                ),
                "warning_issues_count": sum(
                    1 for i in per_file[rel]["issues"] if i["severity"] == "warning"
                ),
                "issue_types": sorted({i["rule"] for i in per_file[rel]["issues"]}),
            }
            for rel in per_file
            if per_file[rel]["issues"]
        ],
        key=lambda x: (-x["critical_issues_count"], -x["warning_issues_count"], x["file_path"]),
    )

    report = {
        "meta": {
            "directive": "FRA-LIB_AUDIT_DIRECTIVE",
            "version": "2026.08.16",
            "halt_condition": "Report-only. No code mutated. Halt condition satisfied.",
        },
        "discovered_entrypoints": [
            ep for ep in DISCOVERED_ENTRYPOINTS if (ROOT / ep).exists()
        ],
        "missing_entrypoints": [
            ep for ep in DISCOVERED_ENTRYPOINTS if not (ROOT / ep).exists()
        ],
        "total_scanned_files": total_scanned,
        "active_core_files_count": len(active_rel),
        "orphaned_files_count": len(orphaned),
        "active_files_by_layer": layer_buckets,
        "health_summary": {
            "clean_files_count": clean,
            "warning_files_count": warning,
            "critical_files_count": critical,
        },
        "top_priority_files_to_fix": top_priority[:20],
        "per_file_detail": per_file,
        "orphaned_files": orphaned,
    }

    OUTPUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md: list[str] = [
        "# FraLib Critical Core Audit",
        "> Read-only. No files modified.",
        "",
        f"- **Scanned**: {total_scanned} .py files",
        f"- **Active**: {len(active_rel)}",
        f"- **Orphaned**: {len(orphaned)}",
        f"- **Clean**: {clean} · **Warning**: {warning} · **Critical**: {critical}",
        "",
        "## Discovered Entrypoints",
        "",
    ]
    for ep in DISCOVERED_ENTRYPOINTS:
        md.append(f"- `{ep}` — {'✅' if (ROOT / ep).exists() else '❌ MISSING'}")

    md += ["", "## Active Files by Layer", ""]
    for layer, paths in layer_buckets.items():
        md.append(f"### {layer} ({len(paths)})")
        for p in paths:
            flag = " 🚩" if any(i["severity"] == "critical" for i in per_file[p]["issues"]) else ""
            md.append(f"- `{p}`{flag}")
        md.append("")

    md += ["", "## Top Priority Fixes", ""]
    for item in top_priority[:20]:
        md.append(
            f"### {item['file_path']}\n"
            f"- Layer: {item['layer']}\n"
            f"- Critical: {item['critical_issues_count']} · Warning: {item['warning_issues_count']}\n"
            f"- Issues: {', '.join(item['issue_types']) or 'none'}\n"
        )

    if orphaned:
        md += ["", "## Orphaned Files (first 100)", ""]
        for p in orphaned[:100]:
            md.append(f"- `{p}`")
        if len(orphaned) > 100:
            md.append(f"- … and {len(orphaned) - 100} more (see JSON)")

    md += ["", "---", f"Generated: {OUTPUT_JSON.name} + {OUTPUT_MD.name}"]
    OUTPUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(
        {
            "discovered_entrypoints": [ep for ep in DISCOVERED_ENTRYPOINTS if (ROOT / ep).exists()],
            "missing_entrypoints": [ep for ep in DISCOVERED_ENTRYPOINTS if not (ROOT / ep).exists()],
            "total_scanned_files": total_scanned,
            "total_active_core_files": len(active_rel),
            "total_orphaned_files": len(orphaned),
            "active_files_by_layer": layer_buckets,
            "health_summary": {
                "clean_files_count": clean,
                "warning_files_count": warning,
                "critical_files_count": critical,
            },
            "top_priority_files_to_fix": top_priority[:20],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
