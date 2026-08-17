#!/usr/bin/env python3
"""
Mechanical fixer for low-risk cleanup only.

Targets:
1. Duplicate imports in the same file.
2. Unused import statements when they are simple and safe to remove.
3. Obvious missing f-prefix on string literals that interpolate in-scope names.

This script is intentionally conservative: it skips complex cases instead of
trying to be clever.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
SKIP_PARTS = {
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
    "tests",
    "test",
    "backend/_arquivo",
}

PLACEHOLDER_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")


@dataclass
class ImportRemoval:
    start: int
    end: int


def should_skip(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return any(part in SKIP_PARTS for part in path.parts) or any(
        skip in normalized for skip in ("/tests/", "/test/", "/__pycache__/", "/.git/", "/.venv/", "/venv/", "/backend/_arquivo/")
    )


def iter_py_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if path == Path(__file__).resolve():
            continue
        if should_skip(path):
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def normalize_import(node: ast.AST) -> tuple[str, tuple[str, ...]]:
    if isinstance(node, ast.Import):
        names = tuple(alias.name + (f" as {alias.asname}" if alias.asname else "") for alias in node.names)
        return ("import", names)
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        names = tuple(alias.name + (f" as {alias.asname}" if alias.asname else "") for alias in node.names)
        return (f"from {module}", names)
    raise TypeError(node)


def collect_import_lines(tree: ast.AST) -> dict[int, ast.AST]:
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            result[getattr(node, "lineno", 0)] = node
    return result


def collect_used_names(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
    return used


def import_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            names.append(alias.asname or alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            names.append(alias.asname or alias.name)
    return names


def duplicate_import_removals(tree: ast.AST) -> list[ImportRemoval]:
    seen: dict[tuple[str, tuple[str, ...]], int] = {}
    removals: list[ImportRemoval] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        key = normalize_import(node)
        line = getattr(node, "lineno", 0)
        if key in seen:
            removals.append(ImportRemoval(start=line, end=getattr(node, "end_lineno", line)))
        else:
            seen[key] = line
    return removals


def unused_import_removals(tree: ast.AST) -> list[ImportRemoval]:
    used = collect_used_names(tree)
    removals: list[ImportRemoval] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        names = import_names(node)
        if not names:
            continue
        if all(name not in used for name in names):
            removals.append(ImportRemoval(start=getattr(node, "lineno", 0), end=getattr(node, "end_lineno", getattr(node, "lineno", 0))))
    return removals


def has_safe_f_string_candidate(token_text: str, names_in_scope: set[str]) -> bool:
    if token_text.lstrip().startswith(("f'", 'f"', "F'", 'F"')):
        return False
    if "{" not in token_text or "}" not in token_text:
        return False
    matches = PLACEHOLDER_RE.findall(token_text)
    if not matches:
        return False
    return any(name in names_in_scope for name in matches)


def build_scopes(tree: ast.AST) -> dict[tuple[int, int], set[str]]:
    scopes: dict[tuple[int, int], set[str]] = {}

    class ScopeVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[set[str]] = [set()]

        def _record(self, node: ast.AST, extra_names: set[str] | None = None) -> None:
            scope = set(self.stack[-1])
            if extra_names:
                scope.update(extra_names)
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            scopes[(start, end)] = scope
            self.stack.append(scope)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Module(self, node: ast.Module) -> None:  # type: ignore[override]
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
            args = {arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
            if node.args.vararg:
                args.add(node.args.vararg.arg)
            if node.args.kwarg:
                args.add(node.args.kwarg.arg)
            self._record(node, args)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override]
            args = {arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
            if node.args.vararg:
                args.add(node.args.vararg.arg)
            if node.args.kwarg:
                args.add(node.args.kwarg.arg)
            self._record(node, args)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # type: ignore[override]
            self._record(node)

        def visit_Assign(self, node: ast.Assign) -> None:  # type: ignore[override]
            targets: set[str] = set()
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        targets.add(sub.id)
            self.stack[-1].update(targets)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # type: ignore[override]
            if isinstance(node.target, ast.Name):
                self.stack[-1].add(node.target.id)
            self.generic_visit(node)

    ScopeVisitor().visit(tree)
    return scopes


def scope_for_line(scopes: dict[tuple[int, int], set[str]], line: int) -> set[str]:
    best: set[str] = set()
    best_span = None
    for (start, end), names in scopes.items():
        if start <= line <= end:
            span = end - start
            if best_span is None or span <= best_span:
                best = names
                best_span = span
    return best


def apply_import_removals(source: str, removals: list[ImportRemoval]) -> str:
    if not removals:
        return source
    lines = source.splitlines()
    removal_lines = set()
    for removal in removals:
        for line in range(removal.start, removal.end + 1):
            removal_lines.add(line)
    kept = [line for idx, line in enumerate(lines, start=1) if idx not in removal_lines]
    return "\n".join(kept) + ("\n" if source.endswith("\n") else "")


def apply_f_prefixes(source: str, scopes: dict[tuple[int, int], set[str]]) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return source

    updated: list[tokenize.TokenInfo] = []
    changed = False
    for tok in tokens:
        if tok.type == tokenize.STRING and has_safe_f_string_candidate(tok.string, scope_for_line(scopes, tok.start[0])):
            prefix_match = re.match(r"^([urbfURBF]*)(['\"]{1,3})(.*)$", tok.string, re.DOTALL)
            if prefix_match:
                prefixes, quote, rest = prefix_match.groups()
                lower_prefix = prefixes.lower()
                if "f" not in lower_prefix:
                    new_prefix = prefixes + ("f" if prefixes.islower() else "F")
                    tok = tokenize.TokenInfo(tok.type, new_prefix + quote + rest, tok.start, tok.end, tok.line)
                    changed = True
        updated.append(tok)

    if not changed:
        return source
    return tokenize.untokenize(updated)


def process_file(path: Path) -> tuple[bool, dict[str, int]]:
    source = read_text(path)
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return False, Counter()

    counts = Counter()
    duplicate_removals = duplicate_import_removals(tree)
    if duplicate_removals:
        candidate = apply_import_removals(source, duplicate_removals)
        try:
            tree = ast.parse(candidate, filename=str(path))
        except SyntaxError:
            pass
        else:
            source = candidate
            counts["duplicate_import"] += len(duplicate_removals)

    unused_removals = unused_import_removals(tree)
    if unused_removals:
        candidate = apply_import_removals(source, unused_removals)
        try:
            tree = ast.parse(candidate, filename=str(path))
        except SyntaxError:
            pass
        else:
            source = candidate
            counts["unused_import"] += len(unused_removals)

    scopes = build_scopes(tree)
    new_source = apply_f_prefixes(source, scopes)
    if new_source != source:
        try:
            ast.parse(new_source, filename=str(path))
        except SyntaxError:
            pass
        else:
            source = new_source
            counts["f_string_prefix"] += 1

    if counts:
        write_text(path, source)
        return True, dict(counts)
    return False, dict(counts)


def main() -> int:
    changed_files = 0
    totals: Counter[str] = Counter()
    for path in iter_py_files(ROOT):
        changed, counts = process_file(path)
        if changed:
            changed_files += 1
        totals.update(counts)

    print(f"Changed files: {changed_files}")
    print(f"Fix counts: {dict(totals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
