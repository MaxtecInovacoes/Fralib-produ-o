#!/usr/bin/env python3
"""Fix corrupted _normalize_generated_imports_and_hooks function."""
import re

filepath = '/root/fralib/backend/services/vite_react_renderer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the corrupted function
marker = 'def _normalize_generated_imports_and_hooks'
idx = content.find(marker)
if idx == -1:
    print('ERROR: function not found')
    exit(1)

# Read until next def
rest = content[idx:]
next_def = rest.find('\ndef _')
if next_def == -1:
    print('ERROR: next function not found')
    exit(1)

corrupted = content[idx:idx+next_def]
print(f'Corrupted len: {len(corrupted)}')

# Build clean replacement
new_func = '''def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:
    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines
    # e.g. "import { Index } from './pages/Index'\\n " becomes valid single line
    for path in list(files.keys()):
        if path.endswith((".tsx", ".ts")):
            files[path] = files[path].replace("\\\\n", "\\n")

    card_stub_needed = False
    for path, content in list(files.items()):
        if not path.endswith((".tsx", ".ts")):
            continue
        updated = str(content or "")
        if path.startswith("src/components/") and '"@/components/ui/card"' in updated:
            updated = updated.replace('"@/components/ui/card"', '"./ui/card"')
            updated = updated.replace("'@/components/ui/card'", "'./ui/card'")
            card_stub_needed = True
        updated = re.sub(
            r"useState<([^>]+)>\((null)\)",
            lambda match: f"useState({match.group(2)} as {match.group(1).strip()})",
            updated,
        )
        updated = re.sub(
            r"useRef\(\s*null\s+as\s+([^)]+)\)",
            lambda match: f"useRef<{match.group(1).strip()} | null>(null)",
            updated,
        )
        updated = re.sub(
            r"useRef<([^>]+)>\((null)\)",
            lambda match: f"useRef<{match.group(1).strip()} | null>({match.group(2)})",
            updated,
        )
        updated = re.sub(r"\\bReact\\.FC\\s*<", "FC<", updated)
        updated = re.sub(r"\\bReact\\.FC\\b", "FC", updated)
        updated = re.sub(r"\\bReact\\.ReactNode\\b", "ReactNode", updated)
        updated = re.sub(r"\\bReact\\.(MouseEvent|ChangeEvent|FormEvent|FocusEvent|KeyboardEvent)\\b", r"\\1", updated)
        if path.endswith(".tsx") and re.search(r"\\b(?:FC|ReactNode|MouseEvent|ChangeEvent|FormEvent|FocusEvent|KeyboardEvent)\\b", updated):
            if "from 'react'" in updated and "import type {" not in updated:
                updated = re.sub(
                    r"import\s*\{([^}]*)\}\s*from\s*['\"]react['\"]\\s*;?",
                    lambda match: (
                        f"import {{{match.group(1)}}} from 'react';\\n"
                        "import type { FC, ReactNode, MouseEvent, ChangeEvent, FormEvent, FocusEvent, KeyboardEvent } from 'react';"
                    ),
                    updated,
                    count=1,
                )
            elif "from 'react'" not in updated:
                updated = (
                    "import type { FC, ReactNode, MouseEvent, ChangeEvent, FormEvent, FocusEvent, KeyboardEvent } from 'react';\\n"
                    + updated
                )
        files[path] = updated
    if card_stub_needed and "src/components/ui/card.tsx" not in files:
        files["src/components/ui/card.tsx"] = vite_template_card_ui()


'''

new_content = content[:idx] + new_func + content[idx+next_def:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f'OK: replaced {len(corrupted)} chars with {len(new_func)} chars')
print(f'New file size: {len(new_content)}')
