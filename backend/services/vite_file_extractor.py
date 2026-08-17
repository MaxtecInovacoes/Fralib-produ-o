"""Vite/React file extraction and normalization utilities."""


import json
import re


# ═══════════════════════════════════════════════════════════════════
# JSON EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_vite_project_files(raw: str) -> dict[str, str]:
    """Extract file contents from LLM JSON response."""
    # Try direct JSON parse first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "files" in parsed:
            return parsed["files"]
        if isinstance(parsed, dict):
            # Maybe the files are at the top level
            files = {k: v for k, v in parsed.items() if isinstance(v, str)}
            if files:
                return files
    except json.JSONDecodeError:
        pass

    # Markdown-wrapped strict JSON is still accepted as a compatibility fallback.
    cleaned = _clean_json_block(raw)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and isinstance(parsed.get("files"), dict):
            return parsed["files"]
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    files = _extract_tagged_file_blocks(raw)
    if files:
        return files

    # Try single file extraction
    return _extract_single_requested_file(raw, [])


def _extract_tagged_file_blocks(raw: str) -> dict[str, str]:
    """Extract files from markdown code blocks with paths."""
    files = {}

    # Match ```json or ```typescript blocks with file paths
    pattern = r'```(?:json|typescript)?\s*(?:file:\s*([^\n]+?))?\n([\s\S]*?)```'

    for match in re.finditer(pattern, raw):
        path = match.group(1)
        content = match.group(2).strip()

        if path:
            files[path.strip()] = content
        elif len(files) == 1:
            # If only one block without path, assign to first expected file
            pass

    # Alternative: parse as JSON with files key
    json_match = re.search(r'"files"\s*:\s*\{([^}]+)\}', raw, re.DOTALL)
    if json_match:
        try:
            files_dict = json.loads("{" + json_match.group(0) + "}")
            return files_dict
        except json.JSONDecodeError:
            pass

    return files


def _extract_single_requested_file(raw: str, paths: list[str]) -> dict[str, str]:
    """Extract a single requested file from response."""
    if not paths:
        return {}

    target = paths[0]
    content = _clean_json_block(raw)

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "files" in parsed:
            files = parsed["files"]
            if target in files:
                return {target: files[target]}
            # Return first file if target not found
            for k, v in files.items():
                if k.endswith((".tsx", ".ts", ".css", ".json", ".html")):
                    return {k: v}
    except json.JSONDecodeError:
        pass

    return {}


def _clean_json_block(raw: str) -> str:
    """Clean markdown JSON block wrapper."""
    # Remove markdown code fences
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last line (code fences)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    # Remove any leading/trailing non-JSON
    raw = raw.strip()

    # Try to find JSON boundaries
    json_start = raw.find('{"')
    if json_start > 0:
        raw = raw[json_start:]

    json_end = raw.rfind('"}')
    if json_end > 0:
        raw = raw[:json_end + 2]

    return raw


def _normalize_text(value: str) -> str:
    """Normalize text for comparison."""
    import unicodedata

    if not isinstance(value, str):
        value = str(value)

    # Normalize unicode
    value = unicodedata.normalize("NFKC", value)
    # Lowercase
    value = value.lower()
    # Remove extra whitespace
    value = re.sub(r"\s+", " ", value).strip()

    return value


def _normalize_model_alias(model: str) -> str:
    """Normalize model name to standard alias."""
    model = model.lower().strip()

    # Common aliases
    aliases = {
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4": "gpt-4",
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
    }

    return aliases.get(model, model)


def _normalize_component_export_contract(files: dict[str, str]) -> None:
    """Ensure components have proper export statements."""
    for path, content in files.items():
        if path.endswith(".tsx") or path.endswith(".ts"):
            # Check for export
            if "export" not in content:
                # Try to find the component name
                match = re.search(r"(?:function|const)\s+(\w+)", content)
                if match:
                    component_name = match.group(1)
                    files[path] = content + f"\nexport default {component_name};"


def _normalize_page_export_contract(files: dict[str, str]) -> None:
    """Ensure pages properly export and import components."""
    page_files = [f for f in files if "pages/" in f or f.endswith("Index.tsx")]

    for page_path in page_files:
        content = files[page_path]

        # Ensure imports from components
        if "import" not in content:
            # Add basic React import
            files[page_path] = "import React from 'react';\n" + content


def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:
    """Normalize imports across generated files."""
    # Build component list
    components = []
    for path in files:
        if "components/" in path and path.endswith(".tsx"):
            name = path.split("/")[-1].replace(".tsx", "")
            components.append(name)

    # Update imports in pages
    for path, content in files.items():
        if "pages/" in path or path.endswith("Index.tsx"):
            for comp in components:
                # Fix case mismatches
                if f"import {comp}" in content:
                    # Already imported
                    pass
