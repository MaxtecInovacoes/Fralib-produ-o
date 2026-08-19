"""Patch _inject_sections_into_shell: append hermetic classes to existing <section> tags."""
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

# Find function
func_start = src.find("def _inject_sections_into_shell(")
if func_start < 0:
    print("FUNCTION NOT FOUND"); exit(1)
func_end = src.find("\ndef _google_fonts_href(", func_start)
if func_end < 0:
    func_end = len(src)
func = src[func_start:func_end]

# Target: the 5-line block that does "wrapped.append(frag); continue" when fragment starts with <section>
# We'll find it by matching the key strings
needle1 = "wrapped.append(frag)\n            continue"
if needle1 not in func:
    print("TARGET NOT FOUND in function")
    print(repr(func[:400]))
    exit(1)

# Split func into before/after at the needle
pos = func.index(needle1)
# Need to also remove the 4 lines before this that form the "skip" block
before_skip = func[:pos]
after_skip = func[pos + len(needle1):]

# Remove the 4 lines immediately before needle1 (they form the skip block)
# Trace back to find the start of the block
lines_before = before_skip.rsplit("\n", 6)
print("LINES BEFORE TARGET:")
for i, l in enumerate(lines_before):
    print(f"  {i}: {repr(l)}")

# The block is:
#   (line -4): frag = _sanitize_fragment(frag)
#   (line -3): comment line 1
#   (line -2): comment line 2
#   (line -1): if re.match(...):
#   (line 0):  wrapped.append(frag); continue  <-- needle1

# We need to remove lines -4 through -1 (inclusive) and replace with new code
# Find the start of the sanitize line
sanitize_line = "        frag = _sanitize_fragment(frag)"
if sanitize_line not in before_skip:
    print("sanitize line not found"); exit(1)

sanitize_pos = before_skip.rfind(sanitize_line)
new_func = (
    before_skip[:sanitize_pos]
    + '        # Se o fragmento ja inicia com <section>, injeta as classes herméticas\n'
    + '        # (evita <section><section>, preservando classes originais do fragmento)\n'
    + '        if re.match(r"(?is)<section\\\\b", frag):\n'
    + '            # Adiciona classes herméticas no primeiro atributo class do <section>\n'
    + '            frag = re.sub(\n'
    + '                r"(?is)(<section\\\\b[^>]*?\\\\sclass=)(["\'])([^"\']*?)\\2",\n'
    + '                lambda m: m.group(1) + m.group(2)\n'
    + '                    + ((m.group(3).strip() + " w-full block clear-both relative overflow-hidden")).strip()\n'
    + '                    + m.group(2),\n'
    + '                frag, count=1,\n'
    + '            )\n'
    + '            # fallback: se nao tem atributo class, injeta direto\n'
    + "            if ' class=\"' not in frag.lower():\n"
    + '                frag = re.sub(\n'
    + '                    r"(?is)(<section\\\\b)",\n'
    + '                    r"\\1 class=\\"w-full block clear-both relative overflow-hidden\\"",\n'
    + '                    frag, count=1,\n'
    + '                )\n'
    + '            wrapped.append(frag)\n'
    + '            continue\n'
    + after_skip
)

new_src = src[:func_start] + new_func + src[func_end:]
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
print("CLEAR-BOTH IN SECTION:", "clear-both" in sec)
print("PATCH COMPLETE")
