"""Patch _inject_sections_into_shell: injects hermetic classes into existing <section> tags.
Uses repr() from remote to build exact match, then replaces the OLD block with NEW behavior.
"""
import re
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

# Exact text block captured from remote repr()
OLD_BLOCK = (
    '        # Se o fragmento ja inicia com <section>, usa ele direto (evita <section><section>)\n'
    '        # Remove outer <section> do fragmento para evitar <section><section>\n'
    '        if re.match(r"(?is)<section\b", frag):\n'
    '            wrapped.append(frag)\n'
    '            continue\n'
)

NEW_BLOCK = (
    '        # Se o fragmento ja inicia com <section>, injeta as classes herméticas\n'
    '        # (evita <section><section>, preservando classes originais do fragmento)\n'
    '        if re.match(r"(?is)<section\b", frag):\n'
    '            frag = re.sub(\n'
    '                r"(?is)(<section\\b[^>]*?\\sclass=)([\"\'])([^\"\\\']*?)\\2",\n'
    "                lambda m: (\n"
    '                    m.group(1) + m.group(2)\n'
    '                    + ((m.group(3).strip() + " w-full block clear-both relative overflow-hidden")).strip()\n'
    '                    + m.group(2)\n'
    '                ),\n'
    '                frag,\n'
    '                count=1,\n'
    '            )\n'
    '            # fallback: se nao tem atributo class, injeta direto\n'
    '            if \' class="\' not in frag.lower() and " class=\'" not in frag.lower():\n'
    '                frag = re.sub(\n'
    '                    r"(?is)(<section\\b)",\n'
    '                    r"\\1 class=\\"w-full block clear-both relative overflow-hidden\\"",\n'
    '                    frag,\n'
    '                    count=1,\n'
    '                )\n'
    '            wrapped.append(frag)\n'
    '            continue\n'
)

if OLD_BLOCK not in src:
    print("PATCH FAILED: OLD_BLOCK not found in source")
    # Show what IS there
    idx = src.find("def _inject_sections_into_shell")
    if idx >= 0:
        chunk = src[idx:idx+700]
        print("Function snippet:")
        print(repr(chunk))
    exit(1)

src = src.replace(OLD_BLOCK, NEW_BLOCK, 1)
with open(PATH, "w") as f:
    f.write(src)

try:
    py_compile.compile(PATH, doraise=True)
    print("PY_COMPILE: OK")
except Exception as e:
    print(f"PY_COMPILE FAIL: {e}")
    exit(1)

# Verify patch landed
with open(PATH) as f:
    verify = f.read()
section = verify.split("def _inject_sections_into_shell")[1].split("def _google_fonts")[0]
if "clear-both" in section and "append(frag)" not in section:
    print("PATCH VERIFIED: clear-both present, old append(frag) removed")
else:
    print("PATCH WARNING: unexpected state")
    print(repr(section[:400]))
    exit(1)
print("PATCH COMPLETE")
