"""Patch _inject_sections_into_shell: injects hermetic classes into existing <section> tags.
Approach: regex-replace the body of the function without depending on exact old-string match.
"""
import re
import py_compile

PATH = "/app/backend/agents/builder/agent.py"

with open(PATH) as f:
    src = f.read()

# Find the function by name
func_start = src.find("def _inject_sections_into_shell(")
if func_start == -1:
    print("FUNCTION NOT FOUND")
    exit(1)

# Find next function def after this one (to know the bounds)
next_def = src.find("\ndef _google_fonts_href(", func_start)
if next_def == -1:
    next_def = len(src)

func_body = src[func_start:next_def]

# The problematic block (loose match, capture surrounding context)
OLD_PATTERN = re.compile(
    r'(frag = _sanitize_fragment\(frag\)\n\s*'
    r'# Se o fragmento ja inicia com <section>, usa ele direto[^\n]*\n'
    r'# Remove outer <section>[^\n]*\n'
    r'if re\.match\(r"\(\?is\)<section\\\\b", frag\):\n'
    r'wrapped\.append\(frag\)\n'
    r'continue)',
    re.MULTILINE,
)

NEW_BLOCK = '''frag = _sanitize_fragment(frag)
        # Se o fragmento ja inicia com <section>, injeta as classes herméticas
        # (evita <section><section>, preservando classes originais do fragmento)
        if re.match(r"(?is)<section\\b", frag):
            # Adiciona classes herméticas no primeiro atributo class do <section>
            frag = re.sub(
                r'(?is)(<section\\b[^>]*?\\sclass=)(["\\'])([^"\\']*?)\\2',
                lambda m: (
                    m.group(1) + m.group(2)
                    + ((m.group(3).strip() + " w-full block clear-both relative overflow-hidden")).strip()
                    + m.group(2)
                ),
                frag,
                count=1,
            )
            # fallback: se não tem atributo class, injeta direto
            if ' class="' not in frag.lower() and " class='" not in frag.lower():
                frag = re.sub(
                    r'(?is)(<section\\b)',
                    r'\\1 class="w-full block clear-both relative overflow-hidden"',
                    frag,
                    count=1,
                )
            wrapped.append(frag)
            continue'''

m = OLD_PATTERN.search(func_body)
if not m:
    print("OLD PATTERN NOT FOUND in function body")
    print("Function snippet:")
    print(func_body[:500])
    exit(1)

new_func_body = func_body[:m.start()] + NEW_BLOCK + func_body[m.end():]
new_src = src[:func_start] + new_func_body + src[next_def:]

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
section = verify.split("def _inject_sections_into_shell")[1].split("def _google_fonts")[0]
if "clear-both" in section:
    print("PATCH VERIFIED: clear-both present in _inject_sections_into_shell")
else:
    print("PATCH WARNING: clear-both not found after patch")
    exit(1)
print("PATCH COMPLETE")
