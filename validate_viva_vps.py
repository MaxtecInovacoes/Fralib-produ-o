"""Validate footer pin + palette diversity on Viva Academia HTML."""
import re

html_path = "/var/www/fralib/sites/2/legacy-centro-de-treinamento-87792a9c/index.html"
with open(html_path, encoding="utf-8") as f:
    html = f.read()

print(f"HTML size: {len(html)} bytes")

# 1. Section order
all_sections = re.findall(r'<section\b[^>]*id="([^"]+)"', html)
print(f"Section IDs: {all_sections}")
footer_idx = next((i for i, s in enumerate(all_sections) if s == "footer"), -1)
print(f"Footer position: {footer_idx} / {len(all_sections)}")
print(f"Footer is last: {footer_idx == len(all_sections) - 1}")
print(f"Sections after footer: {all_sections[footer_idx+1:]}")

# 2. Palette colors
palette_check = {
    "amarelo_neon": bool(re.search(r'FFD60A|oklch\(85%', html)),
    "azul_eletrico": bool(re.search(r'2563EB|oklch\(62%', html)),
    "verde_esmeralda": bool(re.search(r'10B981|oklch\(72%', html)),
    "laranja_vulcanico": bool(re.search(r'F97316|oklch\(68%', html)),
    "roxo_cyberpunk": bool(re.search(r'A855F7|oklch\(65%', html)),
    "branco_ciano": bool(re.search(r'06B6D4|oklch\(82%', html)),
}
print(f"Palette colors found: {palette_check}")
print(f"Any palette color active: {any(palette_check.values())}")

# 3. Footer tag check
footer_tags = re.findall(r'<footer\b', html)
footer_sections = re.findall(r'<section\b[^>]*id="footer"', html)
print(f"<footer> tags: {len(footer_tags)}")
print(f"<section id=\"footer\"> tags: {len(footer_sections)}")

# 4. Last 150 chars before </body>
last_body = html.lower().rfind('</body>')
print(f"Last 150 chars before </body>: {html[max(0, last_body-150):last_body]!r}")
