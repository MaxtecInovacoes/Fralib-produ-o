#!/usr/bin/env python3
"""
Standalone codebase auditor for FraLib.

Scans Python files with AST + regex/token heuristics and emits:
- audit_report.json
- audit_report.md

Findings include:
1. Router functions without decorator
2. FastAPI async endpoints using sync DB methods
3. String literals with interpolation placeholders but missing f-prefix
4. Blind JSON truncation patterns
5. Duplicate imports in same file
6. Direct db.execute(text(...)) usage inside router files
7. await request.json() endpoints that could use Pydantic models
"""


import ast
import json
import re
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parent
JSON_OUT = ROOT / "audit_report.json"
MD_OUT = ROOT / "audit_report.md"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    "tests",
    "test",
    "docs",
    "archive",
    "archive_",
    "legacy",
    "legacy_",
    "_arquivo",
    "backend/_arquivo",
}

PRIORITY_DIRS = (
    "backend/endpoints",
    "backend/routers",
    "backend/agents/manager",
    "backend/services",
)

SEVERITY_ORDER = {
    "CRÍTICO": 0,
    "MÉDIO": 1,
    "BAIXO": 2,
}

ROUTER_NAME_HINTS = (
    "router",
    "routers",
    "endpoints",
)

DB_SYNC_METHODS = {
    "execute",
    "commit",
    "rollback",
    "flush",
    "refresh",
    "scalar",
    "scalars",
    "fetchone",
    "fetchall",
    "close",
}

STRING_PLACEHOLDER_RE = re.compile(r"(?<!\{)\{[A-Za-z_][A-Za-z0-9_\.]*(?:\[[^\]]+\])?\}(?!\})")
JSON_TRUNCATION_RE = re.compile(r"\b(?:json\.)?dumps\s*\([^)]*\)\s*\[\s*:\s*\w+\s*\]")
TEXT_EXEC_RE = re.compile(r"\bdb\.execute\s*\(\s*text\s*\(", re.IGNORECASE)


@dataclass
class Finding:
    file: str
    line: int
    problem: str
    detail: str = ""
    severity: str = "BAIXO"


def iter_py_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*.py"):
        normalized = path.as_posix().lower()
        if any(part.lower() in EXCLUDE_DIRS for part in path.parts):
            continue
        if any(excluded in normalized for excluded in ("/tests/", "/test/", "/__pycache__/", "/.git/", "/.venv/", "/venv/", "/backend/_arquivo/")):
            continue
        if path == Path(__file__).resolve():
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_router_file(path: Path, source: str) -> bool:
    if any(hint in str(path).lower() for hint in ROUTER_NAME_HINTS):
        return True
    if "APIRouter" in source or "router = APIRouter" in source or "@router." in source:
        return True
    return False


def is_priority_path(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return any(priority in normalized for priority in PRIORITY_DIRS)


def severity_for(problem: str) -> str:
    if problem in {
        "router_function_without_decorator",
        "async_endpoint_uses_sync_db_method",
        "string_missing_f_prefix",
        "blind_json_truncation",
    }:
        return "CRÍTICO"
    if problem in {
        "endpoint_uses_request_json_instead_of_pydantic",
        "direct_db_execute_in_router",
    }:
        return "MÉDIO"
    if problem in {
        "duplicate_import",
        "syntax_error",
    }:
        return "BAIXO"
    return "BAIXO"


def is_fastapi_endpoint(func: ast.AST) -> bool:
    decorators = getattr(func, "decorator_list", []) or []
    for dec in decorators:
        text = ast.unparse(dec) if hasattr(ast, "unparse") else ""
        if "router." in text or "app." in text or "api_router." in text:
            return True
    return False


def get_full_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = get_full_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Call):
        return get_full_name(node.func)
    return ""


def is_depends_get_db(default: ast.AST) -> bool:
    if not isinstance(default, ast.Call):
        return False
    func_name = get_full_name(default.func)
    if func_name.endswith("Depends"):
        if default.args:
            arg_name = get_full_name(default.args[0])
            return arg_name.endswith("get_db")
        for kw in default.keywords or []:
            if kw.arg == "dependency":
                arg_name = get_full_name(kw.value)
                return arg_name.endswith("get_db")
    return False


def iter_function_defs(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def top_level_functions(tree: ast.AST) -> list[ast.AST]:
    items = []
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            items.append(node)
    return items


def collect_imports(tree: ast.AST) -> list[tuple[str, int, str]]:
    imports: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, getattr(node, "lineno", 0), f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full = f"{module}.{alias.name}" if module else alias.name
                imports.append((full, getattr(node, "lineno", 0), f"from {module} import {alias.name}".strip()))
    return imports


def find_router_functions_without_decorator(path: Path, tree: ast.AST) -> list[Finding]:
    source = read_text(path)
    if not is_router_file(path, source):
        return []
    findings: list[Finding] = []
    for node in top_level_functions(tree):
        decorators = getattr(node, "decorator_list", []) or []
        if decorators:
            continue
        if node.name.startswith("_"):
            continue
        if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
            findings.append(
                Finding(
                    file=str(path),
                    line=int(getattr(node, "lineno", 1)),
                    problem="router_function_without_decorator",
                    detail=f"Função de topo `{node.name}` em arquivo de router sem decorator",
                    severity=severity_for("router_function_without_decorator"),
                )
            )
    return findings


def find_async_db_sync_calls(path: Path, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    for node in iter_function_defs(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        dep_db_params = set()
        for arg, default in zip(
            list(getattr(node.args, "args", []))[-len(getattr(node.args, "defaults", []) or []):],
            getattr(node.args, "defaults", []) or [],
        ):
            if is_depends_get_db(default):
                dep_db_params.add(arg.arg)
        for kwarg, default in zip(getattr(node.args, "kwonlyargs", []), getattr(node.args, "kw_defaults", []) or []):
            if default is not None and is_depends_get_db(default):
                dep_db_params.add(kwarg.arg)
        if not dep_db_params:
            continue
        sync_hits: list[tuple[int, str]] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id in dep_db_params and func.attr in DB_SYNC_METHODS:
                        sync_hits.append((getattr(sub, "lineno", getattr(node, "lineno", 1)), f"{func.value.id}.{func.attr}()"))
        if sync_hits:
            for line, hit in sync_hits:
                findings.append(
                Finding(
                    file=str(path),
                    line=int(line),
                    problem="async_endpoint_uses_sync_db_method",
                    detail=f"Endpoint async `{node.name}` usa chamada síncrona `{hit}` em parâmetro Depends(get_db)",
                    severity=severity_for("async_endpoint_uses_sync_db_method"),
                )
            )
    return findings


def scan_string_literals(path: Path, source: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tokens = list(tokenize.generate_tokens(iter(source.splitlines(True)).__next__))
    except Exception:
        return findings

    for idx, tok in enumerate(tokens):
        if tok.type != tokenize.STRING:
            continue
        tok_text = tok.string
        prefix = tok_text[:5].lower()
        if "f" in prefix or "r" in prefix or "b" in prefix:
            # f-strings are parsed differently; raw/bytes often shouldn't be checked
            pass
        if not STRING_PLACEHOLDER_RE.search(tok_text):
            continue
        if tok_text.lstrip().startswith(("f'", 'f"', "F'", 'F"')):
            continue
        prev = tokens[idx - 1] if idx > 0 else None
        if prev and prev.type == tokenize.OP and prev.string == ".":
            # likely .format or attribute chain; keep only if literal itself is suspicious
            pass
        findings.append(
            Finding(
                file=str(path),
                line=int(tok.start[0]),
                problem="string_missing_f_prefix",
                detail=f"String literal contém placeholder de interpolação sem prefixo f: {tok_text[:120]}",
                severity=severity_for("string_missing_f_prefix"),
            )
        )
    return findings


def find_json_truncation(path: Path, source: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if "dumps(" not in line:
            continue
        if re.search(r"\.dumps\s*\([^)]*\)\s*\[\s*:\s*\w+\s*\]", line):
            findings.append(
                Finding(
                    file=str(path),
                    line=lineno,
                    problem="blind_json_truncation",
                    detail=line.strip(),
                    severity=severity_for("blind_json_truncation"),
                )
            )
    return findings


def find_duplicate_imports(path: Path, tree: ast.AST) -> list[Finding]:
    imports = collect_imports(tree)
    seen: dict[str, int] = {}
    findings: list[Finding] = []
    for name, line, _ in imports:
        if name in seen:
            findings.append(
                Finding(
                    file=str(path),
                    line=line,
                    problem="duplicate_import",
                    detail=f"Import duplicado de `{name}`; primeira ocorrência na linha {seen[name]}",
                    severity=severity_for("duplicate_import"),
                )
            )
        else:
            seen[name] = line
    return findings


def find_router_db_execute(path: Path, tree: ast.AST, source: str) -> list[Finding]:
    if not is_router_file(path, source):
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = get_full_name(node.func)
            if func_name == "db.execute":
                first_arg = node.args[0] if node.args else None
                if first_arg and isinstance(first_arg, ast.Call) and get_full_name(first_arg.func).endswith("text"):
                    findings.append(
                    Finding(
                        file=str(path),
                        line=int(getattr(node, "lineno", 1)),
                        problem="direct_db_execute_in_router",
                        detail="Uso direto de db.execute(text(...)) em arquivo de router",
                        severity=severity_for("direct_db_execute_in_router"),
                    )
                )
    return findings


def find_request_json_endpoints(path: Path, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    for node in iter_function_defs(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        decorators = getattr(node, "decorator_list", []) or []
        is_endpoint = any("router." in (ast.unparse(dec) if hasattr(ast, "unparse") else "") for dec in decorators)
        if not is_endpoint:
            continue
        uses_request_json = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Await) and isinstance(sub.value, ast.Call):
                func_name = get_full_name(sub.value.func)
                if func_name.endswith("request.json"):
                    uses_request_json = True
                    break
        if uses_request_json:
            has_pydantic_param = any(
                getattr(arg, "annotation", None) is not None and getattr(arg.annotation, "id", "") not in {"Request"}
                for arg in getattr(node.args, "args", [])
            )
            if not has_pydantic_param:
                findings.append(
                Finding(
                    file=str(path),
                    line=int(getattr(node, "lineno", 1)),
                    problem="endpoint_uses_request_json_instead_of_pydantic",
                    detail=f"Endpoint async `{node.name}` usa await request.json() sem modelo Pydantic explícito",
                    severity=severity_for("endpoint_uses_request_json_instead_of_pydantic"),
                )
            )
    return findings


def scan_file(path: Path) -> list[Finding]:
    source = read_text(path)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            Finding(
                file=str(path),
                line=int(getattr(exc, "lineno", 1) or 1),
                problem="syntax_error",
                detail=exc.msg,
                severity=severity_for("syntax_error"),
            )
        ]

    findings: list[Finding] = []
    findings.extend(find_router_functions_without_decorator(path, tree))
    findings.extend(find_async_db_sync_calls(path, tree))
    findings.extend(scan_string_literals(path, source))
    findings.extend(find_json_truncation(path, source))
    findings.extend(find_duplicate_imports(path, tree))
    findings.extend(find_router_db_execute(path, tree, source))
    findings.extend(find_request_json_endpoints(path, tree))
    return findings


def render_markdown(findings: list[Finding]) -> str:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[f"{finding.severity}::{finding.problem}"].append(finding)

    lines = ["# Audit de Codebase", ""]
    lines.append(f"Total de achados: {len(findings)}")
    lines.append("")
    severity_counts = Counter(f.severity for f in findings)
    lines.append("## Resumo por severidade")
    lines.append("")
    for severity in ("CRÍTICO", "MÉDIO", "BAIXO"):
        lines.append(f"- {severity}: {severity_counts.get(severity, 0)}")
    lines.append("")
    for problem, items in sorted(grouped.items()):
        severity, issue = problem.split("::", 1)
        lines.append(f"## {severity} — {issue}")
        lines.append("")
        for item in items:
            detail = f" - {item.detail}" if item.detail else ""
            lines.append(f"- [{item.file}]({item.file}) -> linha {item.line} -> {item.problem}{detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sort_key(finding: Finding) -> tuple[int, int, str, str]:
    return (
        0 if is_priority_path(Path(finding.file)) else 1,
        SEVERITY_ORDER.get(finding.severity, 99),
        finding.file.lower(),
        f"{finding.line:06d}:{finding.problem}",
    )


def main() -> int:
    files = list(iter_py_files(ROOT))
    findings: list[Finding] = []
    for file in files:
        findings.extend(scan_file(file))

    findings.sort(key=sort_key)
    data = {
        "root": str(ROOT),
        "total_files_scanned": len(files),
        "total_findings": len(findings),
        "severity_counts": dict(Counter(f.severity for f in findings)),
        "findings": [asdict(f) for f in findings],
    }

    JSON_OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_OUT.write_text(render_markdown(findings), encoding="utf-8")

    print(f"Scanned {len(files)} files")
    print(f"Findings: {len(findings)}")
    print(f"JSON: {JSON_OUT}")
    print(f"Markdown: {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
