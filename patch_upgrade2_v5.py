"""Patch _inject_sections_into_shell: appends hermetic classes to existing <section> tags."""
import re
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

# Find function boundaries
start = src.find("def _inject_sections_into_shell(")
if start < 0:
    print("FUNCTION NOT FOUND")
    exit(1)
end = src.find("\ndef _google_fonts_href(", start)
if end < 0:
    end = len(src)

func = src[start:end]

# Identify the block to replace: lines containing the skip logic
# Use regex to find it within the function body
old_regex = re.compile(
    r"(frag = _sanitize_fragment\(frag\)\n\s*)"
    r"(# Se o fragmento ja inicia com <section>, usa ele direto.*?\n\s*)"
    r"(if re\.match\(r\"\(\?is\)<section\\\\b\", frag\):\n\s*)"
    r"(wrapped\.append\(frag\)\n\s*continue\n)",
    re.DOTALL,
)

if not old_regex.search(func):
    print("OLD PATTERN NOT FOUND — showing function head:")
    print(repr(func[:500]))
    exit(1)

replacement_first_line = "frag = _sanitize_fragment(frag)\n"
replacement_comment = (
    "        # Se o fragmento ja inicia com <section>, injeta as classes herméticas\n"
    "        # (evita <section><section>, preservando classes originais do fragmento)\n"
)
replacement_if = (
    '        if re.match(r"(?is)<section\\b", frag):\n'
)
replacement_body = (
    '            # Adiciona classes herméticas no primeiro atributo class do <section>\n'
    '            frag = re.sub(\n'
    '                r"(?is)(<section\\b[^>]*?\\sclass=)(["\'])([^"\']*?)\\2",\n'
    '                lambda m: (\n'
    '                    m.group(1) + m.group(2)\n'
    '                    + ((m.group(3).strip() + " w-full block clear-both relative overflow-hidden")).strip()\n'
    '                    + m.group(2)\n'
    '                ),\n'
    '                frag, count=1,\n'
    '            )\n'
    '            # fallback: se nao tem atributo class, injeta direto\n'
    '            if \' class="\' not in frag.lower():\n'
    '                frag = re.sub(\n'
    '                    r"(?is)(<section\\b)",\n'
    '                    r"\\1 class=\\"w-full block clear-both relative overflow-hidden\\"",\n'
    '                    frag, count=1,\n'
    '                )\n'
    '            wrapped.append(frag)\n'
    '            continue\n'
)

new_block = (
    replacement_first_line
    + replacement_comment
    + replacement_if
    + replacement_body
)

new_func = old_regex.sub(new_block, func, count=1)
if new_func == func:
    print("REPLACE FAILED — no change")
    exit(1)

new_src = src[:start] + new_func + src[end:]
with open(PATH, "w") as f:
    f.write(new_src)

try:
    py_compile.compile(PATH, doraise=True)
    print("PY_COMPILE: OK")
except Exception as e:
    print(f"PY_COMPILE FAIL: {e}")
    exit(1)

with open(PATH) as f:
    verify = f.read()
sec = verify.split("def _inject_sections_into_shell")[1].split("def _google_fonts")[0]
if "clear-both" in sec:
    print("PATCH VERIFIED: clear-both present")
else:
    print("PATCH WARNING: clear-both not found")
    print(repr(sec[:400]))
    exit(1)
print("PATCH COMPLETE")
