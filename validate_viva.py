"""Validate footer position + palette in published Viva Academia site."""
import re, subprocess

# Pull the HTML from container
r = subprocess.run(
    ["scp", "-i", r"C:\Users\JESUS TE AMA\.ssh\id_ed25519",
     "root@104.243.41.166:/var/www/fralib/sites/2/viva-academia-09f19869/index.html",
     r"C:\fralib\viva_check.html"],
    capture_output=True, text=True
)
print(f"scp: rc={r.returncode} {r.stderr[:200]}")

with open(r"C:\fralib\viva_check.html", encoding="utf-8") as f:
    html = f.read()

print(f"Size: {len(html)} bytes")

# Footer analysis
footer_matches = list(re.finditer(r'(?is)<footer\b[^>]*>', html))
print(f"Footer tags found: {len(footer_matches)}")
for i, m in enumerate(footer_matches):
    start = m.start()
    end = html.lower().find('</footer>', start)
    footer_block = html[start:end+10] if end > start else html[start:start+200]
    # What comes AFTER this footer?
    after = html[end+10:end+500] if end > start else ""
    print(f"  Footer {i+1}: starts at {start}, ends at {end}")
    print(f"  Content after footer (first 300 chars): {after[:300]!r}")
    print(f"  </body> after footer: {'</body>' in after.lower()}")

# Last </body> position
last_body_close = html.lower().rfind('</body>')
print(f"Last </body> at: {last_body_close}")
print(f"Last 400 chars before </body>: {html[max(0, last_body_close-400):last_body_close]!r}")

# Accent analysis
accent_matches = re.findall(r'(?:--accent|accent)\s*[:=]\s*([^;}\s]+)', html[:3000])  # design-tokens block
print(f"Accent tokens: {accent_matches}")

# Also look in style blocks
style_accent = re.findall(r'--brand-accent\s*:\s*([^;}\s]+)', html)
print(f"Brand accent inline: {style_accent[:5]}")

# Search for hardcoded orange fitness
is_orange_standard = '#E8430A' in html or '#FF3B00' in html or '#ff3b00' in html
print(f"Is standard orange (#E8430A/ff3b00): {is_orange_standard}")

# Check if palette rotation produced one of 6
palette_hex = set(re.findall(r'#(?:FFD60A|2563EB|10B981|F97316|A855F7|FFFFFF|06B6D4)', html, re.I))
print(f"Palette diversity colors found: {palette_hex}")

# Section order check — list all section ids in order
all_sections = re.findall(r'<section[^>]+id="([^"]+)"', html)
print(f"Section IDs in order: {all_sections}")
footer_idx = next((i for i,s in enumerate(all_sections) if s == 'footer'), -1)
print(f"Footer position: {footer_idx} of {len(all_sections)} sections")
if footer_idx >= 0:
    print(f"Sections after footer: {all_sections[footer_idx+1:]}")
    print(f"Footer is last: {footer_idx == len(all_sections)-1}")
