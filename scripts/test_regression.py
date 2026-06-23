"""Regression test: 46/46 patches must pass on generated sites.

Este test garante que a pipeline canonica sempre gera sites com:
- 45 patches verdes + 1 title correto (46/46 total)
- Sem regressao nos sites gerados

Uso:
    python3 test_regression.py --tenant-id 2 --lead-id test-tenant2-academia-20260622193321
    # OU
    python3 test_regression.py --tenant-id 31 --lead-id real-lead-id
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

# 46 patches que devem estar presentes
PATCHES = [
    # Twitter Cards
    ("Twitter title", 'name="twitter:title"'),
    ("Twitter card", 'name="twitter:card"'),
    ("Twitter description", 'name="twitter:description"'),
    ("Twitter image", 'name="twitter:image"'),
    # Open Graph
    ("OG title", 'property="og:title"'),
    ("OG description", 'property="og:description"'),
    ("OG image", 'property="og:image"'),
    ("OG locale", 'property="og:locale"'),
    # Title correto (nao FraLib Site)
    ("Title correct", '<title>Academia Pipeline Teste | Academia em Curitiba</title>'),
    # Acessibilidade
    ("Skip link OpenUI", 'class="fralib-skip-link'),
    ("Skip link A11Y", 'Pular para o conte'),
    ("LGPD banner", 'data-lgpd-banner'),
    ("Preconnect Unsplash", 'preconnect" href="https://images.unsplash.com"'),
    ("Preload LCP", 'rel="preload" as="image"'),
    ("Apple touch icon", 'apple-touch-icon'),
    ("Organization schema", '"@type":"Organization"'),
    ("WebSite schema", '"@type":"WebSite"'),
    ("Robots meta", 'name="robots"'),
    ("Hreflang", 'hreflang="pt-BR"'),
    ("Theme color", 'theme-color'),
    # Motion Awwwards (12)
    ("Data parallax", 'data-parallax'),
    ("Data reveal", 'data-reveal'),
    ("Data marquee", 'data-marquee'),
    ("Data magnetic", 'data-magnetic'),
    ("Data 3d-tilt", 'data-3d-tilt'),
    ("Data counter", 'data-counter'),
    ("Data stagger", 'data-stagger'),
    ("GSAP", 'gsap'),
    ("ScrollTrigger", 'ScrollTrigger'),
    ("Lenis", 'lenis'),
    ("Motion runtime", 'fralib-motion-runtime'),
    # CSS Moderno
    ("CSS :has()", ':has('),
    ("CSS color-mix()", 'color-mix('),
    ("CSS @container", '@container'),
    ("CSS subgrid", 'subgrid'),
    ("prefers-reduced-motion", 'prefers-reduced-motion'),
    (":focus-visible", ':focus-visible'),
    ("view-transitions", 'view-transition'),
    # Performance
    ("srcset (Unsplash)", 'srcset="'),
    ("fetchpriority=\"high\"", 'fetchpriority="high"'),
    ("loading=\"lazy\"", 'loading="lazy"'),
    ("loading=\"eager\"", 'loading="eager"'),
    ("decoding=\"async\"", 'decoding="async"'),
    ("WebP/AVIF URL", 'fm=webp'),
    ("alt= em imgs", 'alt='),
    ("canonical link", 'rel="canonical"'),
]

def run_pipeline(tenant_id, lead_id):
    """Roda pipeline para o lead."""
    print(f"\n🚀 Rodando pipeline para tenant {tenant_id}, lead {lead_id}...")

    # Reset lead status
    subprocess.run([
        "ssh", "root@100.101.18.1",
        f"sudo -u postgres psql -d fralib_db -c "
        f"'UPDATE leads SET status = \"novo\", pipeline_stage = \"novo\" WHERE id = \"{lead_id}\";'"
    ], check=True, capture_output=True)

    # Roda controlled pipeline
    cmd = [
        "ssh", "root@100.101.18.1",
        f"cd /root/fralib && venv/bin/python3 scripts/controlled_pipeline_run.py "
        f"--tenant-id {tenant_id} --lead-id {lead_id} --confirm RUN_CONTROLLED_PIPELINE --wait"
    ]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
    print("✅ Pipeline completado!")

    # Extrair URL do site
    url = extract_site_url(lead_id)
    return url

def extract_site_url(lead_id):
    """Extrai URL do site do banco."""
    result = subprocess.run([
        "ssh", "root@100.101.18.1",
        f"sudo -u postgres psql -d fralib_db -c "
        f"SELECT url_site FROM leads WHERE id = '{lead_id}';"
    ], check=True, capture_output=True, text=True)

    # Extrair URL da saída
    lines = result.stdout.split('\n')
    for line in lines:
        if 'seunegociofralib.site' in line:
            return line.strip()
    raise ValueError("URL não encontrada")

def validate_site(url):
    """Valida todos os 46 patches no site."""
    print(f"\n🔍 Validando site: {url}")

    # Baixa HTML
    with urlopen(url, timeout=30) as response:
        html = response.read().decode('utf-8')

    results = []
    passed = 0
    failed = 0

    for name, needle in PATCHES:
        found = needle.lower() in html.lower()
        status = "✅" if found else "❌"
        if found:
            passed += 1
        else:
            failed += 1
        results.append((name, found))
        print(f"{status} {name}")

    print(f"\n📊 Resultado: {passed}/{len(PATCHES)} passados ({passed/len(PATCHES)*100:.1f}%)")

    if failed > 0:
        print(f"\n❌ {failed} patches falharam:")
        for name, found in results:
            if not found:
                print(f"   - {name}")
        return False

    return True

def main():
    parser = argparse.ArgumentParser(description="Regression test for 46/46 patches")
    parser.add_argument("--tenant-id", type=int, required=True, help="Tenant ID")
    parser.add_argument("--lead-id", type=str, required=True, help="Lead ID")
    parser.add_argument("--skip-pipeline", action="store_true", help="Pular pipeline, só validar")

    args = parser.parse_args()

    print("🧪 Regression Test: 46/46 Patches")
    print("=" * 50)

    if not args.skip_pipeline:
        url = run_pipeline(args.tenant_id, args.lead_id)
    else:
        url = extract_site_url(args.lead_id)

    # Valida
    if validate_site(url):
        print("\n🎉 SUCCESS: 46/46 patches verdes!")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Regressão detectada!")
        sys.exit(1)

if __name__ == "__main__":
    main()