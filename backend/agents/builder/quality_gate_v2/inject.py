"""
inject.py — Partial HTML injection for FraLib landing pages.

Sprint 4+5: injects missing sections (FAQ, depoimentos, selos, footer, nav)
using idempotent HTML markers. Reads partials from the landing partials directory.

Usage:
    from inject import inject_partials
    result = inject_partials(html, prd, partials_dir=None)
    # result["html"] → enriched HTML
    # result["injected"] → list of partials that were injected
"""


import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Idempotent markers
# ============================================================================
MARKERS: Dict[str, str] = {
    "faq":         "<!-- PARTIAL-FAQ -->",
    "depoimentos": "<!-- PARTIAL-DEPOIMENTOS -->",
    "selos":       "<!-- PARTIAL-SELOS -->",
    "footer":      "<!-- PARTIAL-FOOTER -->",
    "nav":         "<!-- PARTIAL-NAV -->",
}

PARTIAL_FILES: Dict[str, str] = {
    "faq":         "_faq.html",
    "depoimentos": "_depoimentos.html",
    "selos":       "_selos.html",
    "footer":      "_footer.html",
    "nav":         "_nav.html",
}

INJECTION_ORDER = ["nav", "footer", "faq", "depoimentos", "selos"]

# Pattern to find a marker anywhere in the HTML
_MARKER_RE = re.compile(
    r"<!--\s*PARTIAL-({})\s*-->".format("|".join(MARKERS.keys())),
    re.IGNORECASE,
)


def _partials_dir() -> Path:
    """Return the landing partials directory (relative to this file)."""
    return Path(__file__).resolve().parent / "partials" / "landing"


def _read_partial(partials_dir: Path, name: str) -> str:
    """Read a partial HTML file from disk. Returns empty string on error."""
    path = partials_dir / PARTIAL_FILES[name]
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return ""


def _replace_placeholders(html: str, prd: Dict[str, Any]) -> str:
    """Replace {placeholder} tokens in partial HTML with PRD values.

    Falls back to sensible defaults when the PRD doesn't provide a value.
    """
    context: Dict[str, str] = {
        # Core brand info
        "marca":   _safe(prd, "marca", _safe(prd, "brand_name", "")),
        "cidade":  _safe(prd, "cidade", _safe(prd, "city", "")),
        "sub_nicho": _safe(prd, "sub_nicho", _safe(prd, "sub_niche", "")),
        "telefone": _safe(prd, "telefone", _safe(prd, "phone", "")),
        "cnpj":    _safe(prd, "cnpj", _safe(prd, "cnpj", "00.000.000/0000-00")),
    }

    for key, value in context.items():
        html = html.replace("{" + key + "}", value)

    return html


def _safe(data: Dict[str, Any], key: str, default: str = "") -> str:
    """Safely extract a string value from a dict, with a default fallback."""
    val = data.get(key, default)
    if val is None:
        return default
    return str(val)


def _has_marker(html: str, name: str) -> bool:
    """Check if a specific marker comment exists in the HTML."""
    return bool(re.search(
        r"<!--\s*PARTIAL-{}\s*-->".format(re.escape(name)),
        html,
        re.IGNORECASE,
    ))


def _inject_after_marker(html: str, content: str, marker: str) -> str:
    """Inject content right after the first occurrence of a marker."""
    escaped = re.escape(marker)
    pattern = re.compile(r"(<!--\s*PARTIAL-{}\s*-->)".format(
        marker.replace("<!-- PARTIAL-", "").replace(" -->", "")
    ), re.IGNORECASE)
    return pattern.sub(r"\1\n" + content, html, count=1)


# ============================================================================
# Public API
# ============================================================================

def inject_partials(
    html: str,
    prd: Optional[Dict[str, Any]] = None,
    partials_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Inject missing partial sections into an HTML document.

    For each partial marker:
    - If the marker exists in HTML → leave it alone (idempotent).
    - If the marker is missing → read the partial file and inject it
      at the best location in the HTML.

    Args:
        html:      Full HTML document string.
        prd:       Designer PRD dict (provides brand/city placeholders).
        partials_dir: Override for the partials directory path.

    Returns:
        Dict with:
            "html"       → enriched HTML string
            "injected"   → list of partial names that were injected
            "skipped"    → list of partial names already present
            "errors"     → list of partial names that failed to load
    """
    prd = prd or {}
    pd = partials_dir or _partials_dir()

    injected: List[str] = []
    skipped:  List[str] = []
    errors:   List[str] = []
    result_html = html

    for name in INJECTION_ORDER:
        if _has_marker(result_html, name):
            skipped.append(name)
            continue

        raw = _read_partial(pd, name)
        if not raw:
            errors.append(name)
            continue

        processed = _replace_placeholders(raw, prd)

        # Choose injection point based on partial type
        if name == "nav":
            # Inject right after <body> tag
            body_match = re.search(r"<body[^>]*>", result_html, re.IGNORECASE)
            if body_match:
                insert_pos = body_match.end()
                result_html = result_html[:insert_pos] + "\n" + processed + result_html[insert_pos:]
            else:
                result_html = processed + "\n" + result_html

        elif name == "footer":
            # Inject right before </body>
            body_close = result_html.rfind("</body>")
            if body_close != -1:
                result_html = result_html[:body_close] + processed + "\n" + result_html[body_close:]
            else:
                result_html = result_html + "\n" + processed

        elif name == "faq":
            # Inject before </main> if present, otherwise before </body>
            main_close = result_html.rfind("</main>")
            if main_close != -1:
                result_html = result_html[:main_close] + processed + result_html[main_close:]
            else:
                body_close = result_html.rfind("</body>")
                if body_close != -1:
                    result_html = result_html[:body_close] + processed + "\n" + result_html[body_close:]
                else:
                    result_html = result_html + "\n" + processed

        elif name == "depoimentos":
            # Inject before FAQ if FAQ marker exists, else before </main>
            if _has_marker(result_html, "faq"):
                faq_marker = re.search(r"<!--\s*PARTIAL-FAQ\s*-->", result_html, re.IGNORECASE)
                if faq_marker:
                    result_html = result_html[:faq_marker.start()] + processed + "\n" + result_html[faq_marker.start():]
                    injected.append(name)
                    continue
            main_close = result_html.rfind("</main>")
            if main_close != -1:
                result_html = result_html[:main_close] + processed + result_html[main_close:]
            else:
                body_close = result_html.rfind("</body>")
                if body_close != -1:
                    result_html = result_html[:body_close] + processed + "\n" + result_html[body_close:]
                else:
                    result_html = result_html + "\n" + processed

        elif name == "selos":
            # Inject before closing </section> of the last section, or before </main>
            last_section = result_html.rfind("</section>")
            if last_section != -1:
                result_html = result_html[:last_section] + processed + "\n" + result_html[last_section:]
            else:
                main_close = result_html.rfind("</main>")
                if main_close != -1:
                    result_html = result_html[:main_close] + processed + result_html[main_close:]
                else:
                    body_close = result_html.rfind("</body>")
                    if body_close != -1:
                        result_html = result_html[:body_close] + processed + "\n" + result_html[body_close:]
                    else:
                        result_html = result_html + "\n" + processed

        injected.append(name)

    return {
        "html": result_html,
        "injected": injected,
        "skipped": skipped,
        "errors": errors,
    }


# ============================================================================
# All-in-one: inject + SEO enrich
# ============================================================================

def enrich_and_inject(
    html: str,
    prd: Optional[Dict[str, Any]] = None,
    partials_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Convenience function: inject partials then enrich SEO in one call.

    Returns dict with:
        "html"       → final enriched HTML
        "injected"   → partials injected
        "skipped"    → partials already present
        "seo"        → SEO enrichment report dict
    """
    # Step 1: inject partials
    injection = inject_partials(html, prd, partials_dir)
    enriched = injection["html"]

    # Step 2: enrich SEO
    seo_report = enrich_seo(enriched, prd)

    return {
        "html": seo_report["html"],
        "injected": injection["injected"],
        "skipped": injection["skipped"],
        "seo": seo_report,
    }
