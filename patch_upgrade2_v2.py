"""Patch _inject_sections_into_shell: append hermetic classes to existing <section> tags."""
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

OLD = (
    '        # Se o fragmento ja inicia com <section>, usa ele direto (evita <section><section>)\n'
    '        # Remove outer <section> do fragmento para evitar <section><section>\n'
    '        if re.match(r"(?is)<section\\\\b", frag):\n'
    '            wrapped.append(frag)\n'
    '            continue\n'
)

NEW = (
    '        # Se o fragmento ja inicia com <section>, injeta as classes herméticas\n'
    '        # (evita <section><section>, preservando classes originais do fragmento)\n'
    '        if re.match(r"(?is)<section\\\\b", frag):\n'
    '            frag = re.sub(\n'
    '                r\'\\1)(<section\\\\b[^>]*?\\\\sclass=)(["\\\'])([^"\\\']*)(\\3)\',\n'
    "                lambda m: (\n"
    '                    m.group(2) + m.group(3)\n'
    '                    + ((m.group(4).strip() + " w-full block clear-both relative overflow-hidden")).strip()\n'
    '                    + m.group(5)\n'
    '                ),\n'
    '                frag,\n'
    '                count=1,\n'
    '            )\n'
    '            if \'class="\' not in frag.lower() and "class=\'" not in frag.lower():\n'
    '                frag = re.sub(\n'
    '                    r\'(?is)(<section\\\\b)\',\n'
    '                    r\'\\\\1 class="w-full block clear-both relative overflow-hidden"\',\n'
    '                    frag,\n'
    '                    count=1,\n'
    '                )\n'
    '            wrapped.append(frag)\n'
    '            continue\n'
)

if OLD not in src:
    print("PATCH FAILED: OLD block not found in source")
    # Show what IS around line ~906
    idx = src.find("def _inject_sections_into_shell")
    print(repr(src[idx:idx+500]))
    exit(1)

src = src.replace(OLD, NEW, 1)
with open(PATH, "w") as f:
    f.write(src)

try:
    py_compile.compile(PATH, doraise=True)
    print("PY_COMPILE: OK")
except Exception as e:
    print(f"PY_COMPILE FAIL: {e}")
    exit(1)

# Verify
with open(PATH) as f:
    verify = f.read()
section = verify.split("def _inject_sections_into_shell")[1].split("def _google_fonts")[0]
if "clear-both" in section:
    print("PATCH VERIFIED: clear-both present in _inject_sections_into_shell")
else:
    print("PATCH WARNING: clear-both not found after patch")
    exit(1)
print("PATCH COMPLETE")
