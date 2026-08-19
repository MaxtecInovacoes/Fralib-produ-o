"""Inspect final HTML of Curitiba Fitness for section classes and design-tokens."""
import sys, os
sys.path.insert(0, '/app/backend')
os.environ['DATABASE_URL'] = 'postgresql://fralib_user:fralib_dev_password@postgres:5432/fralib_db'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])

LEAD_DIR = "/var/www/fralib/sites/2/curitiba-fitness-b5db65cd"
html_path = os.path.join(LEAD_DIR, "index.html")
with open(html_path) as f:
    html = f.read()

print(f"HTML size: {len(html)} bytes")

# 1. design-tokens block
idx = html.find('id="design-tokens"')
print(f"\ndesign-tokens block:\n{html[max(0,idx-5):idx+400]!r}\n")

# 2. section tags — count and sample classes
import re
sections = re.findall(r'<section\b[^>]*>', html, re.IGNORECASE)
print(f"Total <section> tags: {len(sections)}")
for sec in sections[:8]:
    print(f"  {sec}")
if len(sections) > 8:
    print(f"  ... ({len(sections)-8} more)")

# 3. clear-both anywhere
print(f"\nclear-both occurrences: {html.lower().count('clear-both')}")
for m in re.finditer(r'.{0,40}clear-both.{0,60}', html, re.IGNORECASE):
    print(f"  ctx: {m.group()!r}")

# 4. Check for <section class="...">
print("\n<section class=...> samples:")
for sec in sections[:5]:
    print(f"  {sec}")
