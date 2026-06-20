"""Audit published site HTML files for the minimum FraLib delivery contract.

This script is read-only. It is meant to run on the VPS against
`/var/www/fralib/sites` before calling a production state healthy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECKS = {
    "builder_renderer": 'data-renderer="builder"',
    "canonical": '<link rel="canonical"',
    "og_url": 'property="og:url"',
    "twitter_card": 'name="twitter:card"',
    "schema_jsonld": 'application/ld+json',
    "lgpd_storage_key": "fralib_lgpd_consent_v1",
    "lgpd_banner": "data-lgpd-banner",
}


def _site_label(root: Path, index_file: Path) -> str:
    try:
        return str(index_file.parent.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(index_file.parent)


def audit_site(index_file: Path) -> dict[str, object]:
    html = index_file.read_text(encoding="utf-8", errors="ignore")
    missing = [name for name, token in CHECKS.items() if token not in html]
    return {
        "path": str(index_file),
        "ok": not missing,
        "missing": missing,
        "size_bytes": len(html.encode("utf-8")),
    }


def collect_sites(root: Path, max_sites: int | None) -> list[Path]:
    indexes = sorted(root.rglob("index.html"))
    if max_sites is not None:
        return indexes[:max_sites]
    return indexes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="/var/www/fralib/sites", help="Published sites root")
    parser.add_argument("--max-sites", type=int, default=None, help="Limit number of index.html files")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--warn-only", action="store_true", help="Always exit 0")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        payload = {"ok": False, "root": str(root), "error": "sites root not found", "sites": []}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"FAIL published-site-audit: sites root not found: {root}")
        return 0 if args.warn_only else 1

    sites = collect_sites(root, args.max_sites)
    results = []
    for index_file in sites:
        result = audit_site(index_file)
        result["site"] = _site_label(root, index_file)
        results.append(result)

    failed = [item for item in results if not item["ok"]]
    payload = {
        "ok": not failed,
        "root": str(root),
        "total": len(results),
        "failed": len(failed),
        "checks": sorted(CHECKS),
        "sites": results,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if payload["ok"] else "FAIL"
        print(f"{status} published-site-audit: {len(results)} sites checked, {len(failed)} failed")
        for item in failed[:20]:
            print(f"- {item['site']}: missing {', '.join(item['missing'])}")
        if len(failed) > 20:
            print(f"... {len(failed) - 20} more failed sites omitted")

    return 0 if payload["ok"] or args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
