#!/usr/bin/env python3
"""Tenta fazer build do output ja gerado pelo LLM (sem chamar LLM de novo)."""

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except: pass

# Carrega raw output
raw_path = ROOT / ".tmp" / "test-builder-llm-only" / "llm_raw_output.txt"
if not raw_path.exists():
    print(f"ERRO: {raw_path} nao existe. Rode primeiro: python scripts/test_builder_llm_only.py")
    sys.exit(1)

raw = raw_path.read_text(encoding="utf-8")
print(f"carreguei {len(raw)} chars de LLM raw output")

# Parse os arquivos
data = json.loads(raw)
files_in = data["files"]
print(f"LLM retornou {len(files_in)} arquivos")

# Prepara e builda
from services.vite_react_renderer import (
    prepare_vite_project_files,
    write_vite_project,
    build_vite_project,
    extract_vite_project_files,
    validate_vite_project_files,
    validate_vite_dist,
)

facts = {
    "business": {"name": "Crossfit Campo Grande", "whatsapp": "67999887766", "phone": "67999887766", "city": "Campo Grande", "segment": "academia", "rating": "4.8"},
    "cidade": "Campo Grande", "segmento": "academia", "design_system": "crossfit-box",
}

workspace = ROOT / ".tmp" / "test-build-only"
workspace.mkdir(parents=True, exist_ok=True)
for stale in ("dist", "src", "node_modules", "package.json", "vite.config.ts", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json"):
    target = workspace / stale
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()

files = prepare_vite_project_files(extract_vite_project_files(raw), facts=facts)
print(f"prepare_vite_project_files: {len(files)} arquivos")

# Valida ANTES do build
print()
print("=== validate_vite_project_files ===")
try:
    validate_vite_project_files(files, facts)
    print("OK: passou")
except Exception as e:
    print(f"FALHOU: {e}")

# Escreve e builda mesmo se validador falhar (pra ver se npm compila)
print()
print("=== write_vite_project + build ===")
started = time.time()
try:
    write_vite_project(workspace, files)
    build_vite_project(workspace)
    index_path = workspace / "dist" / "index.html"
    html = index_path.read_text(encoding="utf-8")
    print(f"OK: build em {time.time()-started:.1f}s, {len(html)} chars HTML")

    # Valida dist
    validate_vite_dist(workspace / "dist")
    print("OK: dist valido")

    # Lista arquivos no dist
    dist = workspace / "dist"
    print(f"dist files:")
    for p in sorted(dist.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(workspace)} ({p.stat().st_size} bytes)")
except Exception as e:
    print(f"BUILD FAIL: {e}")
    import traceback
    traceback.print_exc()
