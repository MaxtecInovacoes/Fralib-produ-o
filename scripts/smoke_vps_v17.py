"""Smoke test do sistema de variação na VPS - gera 6 sites, valida variação."""
import sys
import json
from pathlib import Path

ROOT = Path("/root/fralib")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.templates._system import variation
from backend.services import template_loader

print("=" * 70)
print("SPRINT 4 - SMOKE REAL VPS - 6 sites 1/estética")
print("=" * 70)

results = []
for lead_id in [2000, 2001, 2002, 2003, 2004, 2005]:
    v = variation.generate_variation(lead_id, "academia_crossfit")
    lead_context = {
        "business_name": f"Academia Lead {lead_id}",
        "tagline": "Performance real, sem enrolação",
        "city": "São Paulo",
        "phone": "11999990000",
    }
    template_html = template_loader.load_template(v["estetica"])
    final_html = template_loader.render_with_variation(
        template_html, lead_context, v
    )
    unresolved = template_loader.validate_template_output(final_html)
    chars = len(final_html)
    has_anim = "data-reveal" in final_html or "data-parallax" in final_html or "transform:" in final_html
    ok = len(unresolved) == 0 and chars > 5000
    results.append({
        "lead_id": lead_id,
        "estetica": v["estetica"],
        "theme": v["theme"],
        "typography": v["typography"],
        "layout": v["layout"],
        "motion": v["motion"],
        "chars": chars,
        "unresolved": unresolved,
        "ok": ok,
        "has_animation": has_anim,
    })
    print(
        f"  Lead {lead_id}: {v['estetica']:14s} | {v['theme']:18s} | "
        f"{v['typography']:18s} | {v['layout']:9s} | {v['motion']:10s} | "
        f"chars={chars:6d} | anim={has_anim} | ok={ok}"
    )

print()
print("=" * 70)
print("Determinismo (mesmo lead 3x)")
print("=" * 70)
v1 = variation.generate_variation(2000, "academia_crossfit")
v2 = variation.generate_variation(2000, "academia_crossfit")
v3 = variation.generate_variation(2000, "academia_crossfit")
print(f"  Run 1: {v1['estetica']}/{v1['theme']}/{v1['typography']}")
print(f"  Run 2: {v2['estetica']}/{v2['theme']}/{v2['typography']}")
print(f"  Run 3: {v3['estetica']}/{v3['theme']}/{v3['typography']}")
print(f"  Determinístico: {v1 == v2 == v3}")

# Salva report
report_path = Path("/root/fralib/tests/_smoke_vps_v1.7.json")
report_path.write_text(json.dumps({
    "vps": "100.101.18.1",
    "results": results,
    "all_ok": all(r["ok"] for r in results),
    "all_animation": all(r["has_animation"] for r in results),
    "deterministic": v1 == v2 == v3,
    "total_chars": sum(r["chars"] for r in results),
    "total_leads": len(results),
}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nReport salvo em {report_path}")
print(f"  All OK: {all(r['ok'] for r in results)}")
print(f"  Total chars: {sum(r['chars'] for r in results)}")
