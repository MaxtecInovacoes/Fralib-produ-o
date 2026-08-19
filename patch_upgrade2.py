"""Patch _inject_sections_into_shell: appends hermetic classes to existing <section> tags."""
import re
import os
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

OLD = '''        frag = _sanitize_fragment(frag)
        # Se o fragmento ja inicia com <section>, usa ele direto (evita <section><section>)
        if re.match(r"(?is)<section\b", frag):
            wrapped.append(frag)
            continue'''

NEW = '''        frag = _sanitize_fragment(frag)
        # Se o fragmento ja inicia com <section>, injeta as classes herméticas
        # (evita <section><section>, preservando classes originais do fragmento)
        if re.match(r"(?is)<section\\b", frag):
            frag = re.sub(
                r'(?is)(<section\\b[^>]*?\\sclass=)(["\\'])([^"\\']*)(\\2)',
                lambda m: (
                    m.group(1) + m.group(2)
                    + (m.group(3).strip() + " w-full block clear-both relative overflow-hidden").strip()
                    + m.group(4)
                ),
                frag,
                count=1,
            )
            # fallback: se não tem atributo class, injeta direto
            if 'class="' not in frag.lower() and "class='" not in frag.lower():
                frag = re.sub(
                    r'(?is)(<section\\b)',
                    r'\\1 class="w-full block clear-both relative overflow-hidden"',
                    frag,
                    count=1,
                )
            wrapped.append(frag)
            continue'''

if OLD not in src:
    print("PATCH FAILED: OLD block not found in source")
    print("Looking for _inject_sections_into_shell...")
    idx = src.find("def _inject_sections_into_shell")
    print(f"Function at index: {idx}")
    print(repr(src[idx:idx+500]))
    exit(1)

src = src.replace(OLD, NEW, 1)

# Write back
with open(PATH, "w") as f:
    f.write(src)

# Verify py_compile
try:
    py_compile.compile(PATH, doraise=True)
    print("PY_COMPILE: OK")
except Exception as e:
    print(f"PY_COMPILE FAIL: {e}")
    exit(1)

# Verify the patch landed
with open(PATH) as f:
    verify = f.read()
if "clear-both" in verify.split("def _inject_sections_into_shell")[1].split("def _google_fonts")[0]:
    print("PATCH VERIFIED: clear-both present in _inject_sections_into_shell")
else:
    print("PATCH WARNING: clear-both not found after patch")
    exit(1)

print("PATCH COMPLETE")
