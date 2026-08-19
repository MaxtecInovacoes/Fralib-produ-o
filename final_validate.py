"""Final validation of footer pin + palette diversity on published Viva Academia."""
import re, subprocess

# Pull fresh HTML
r = subprocess.run(
    ["scp", "-i", r"C:\Users\JESUS TE AMA\.ssh\id_ed25519",
     "root@104.243.41.166:/var/www/fralib/sites/2/viva-academia-09f19869/index.html",
     r"C:\fralib\viva_final.html"],
    capture_output=True, text=True
)
print(f"scp: rc={r.returncode}")

with open(r"C:\fralib\viva_final.html", encoding="utf-8") as f:
    html = f.read()

print(f"HTML size: {len(html)} bytes")

# --- 1. Section order ---
all_sections = re.findall(r'<section\b[^>]*id="([^"]+)"', html)
print(f"Section IDs: {all_sections}")
footer_idx = next((i for i, s in enumerate(all_sections) if s == "footer"), -1)
print(f"Footer position: {footer_idx} / {len(all_sections)}")
print(f"Footer is last: {footer_idx == len(all_sections) - 1}")
print(f"Sections after footer: {all_sections[footer_idx+1:]}")

# --- 2. Palette colors ---
# Look for oklch accent values in the design-tokens style block
m = re.search(r'<style id="design-tokens">(.*?)</style>', html, re.DOTALL)
if m:
    tokens = m.group(1)
    print(f"Design tokens block: {tokens[:600]}")

# Look for accent color in inline styles (var(--accent, ...) fallbacks)
inline_accents = re.findall(r'var\(--accent,\s*([^)]+)\)', html)
print(f"Inline accent fallbacks (first 10): {inline_accents[:10]}")

# Check for the 6 palette colors (HEX or oklch approximations)
palette_check = {
    "amarelo_neon":    bool(re.search(r'FFD60A|oklch\(85%', html)),
    "azul_eletrico":   bool(re.search(r'2563EB|oklch\(62%.*250\)', html)),
    "verde_esmeralda": bool(re.search(r'10B981|oklch\(72%.*145\)', html)),
    "laranja_vulcanico": bool(re.search(r'F97316|oklch\(68%.*28\)', html)),
    "roxo_cyberpunk":  bool(re.search(r'A855F7|oklch\(65%.*285\)', html)),
    "branco_ciano":    bool(re.search(r'06B6D4|oklch\(82%.*195\)', html)),
}
print(f"Palette colors found: {palette_check}")
print(f"Any palette color active: {any(palette_check.values())}")

# Check if old standard orange is gone
old_orange = bool(re.search(r'#E8430A|#ff3b00|oklch\(.*25\).*0\.22', html))
print(f"Old standard orange still present: {old_orange}")

# --- 3. Footer tag check ---
footer_tags = re.findall(r'<footer\b', html)
footer_sections = re.findall(r'<section\b[^>]*id=["\']footer["\']', html)
print(f"<footer> tags: {len(footer_tags)}")
print(f"<section id=\"footer\"> tags: {len(footer_sections)}")

# --- 4. Last 300 chars before </body> ---
last_body = html.lower().rfind('</body>')
print(f"Last 300 chars before </body>: {html[max(0, last_body-300):last_body]!r}")
