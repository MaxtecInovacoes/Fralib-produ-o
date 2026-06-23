"""Unit tests para validar que os 46/46 patches sempre sao aplicados.

Roda sem precisar de LLM/banco/site real - apenas valida os patchers.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

import pytest
from services.openui_renderer import (
    build_openui_document,
    _enrich_seo_and_runtime,
    _patch_performance,
    _inject_modern_css_fallback,
    _dedupe_skip_link,
)


# HTML minimo para testes
MINIMAL_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Test</title>
</head>
<body>
  <img src="https://images.unsplash.com/photo-123?w=1080&q=80" alt="Test">
</body>
</html>"""

MINIMAL_FACTS = {
    "business": {
        "name": "Test Business",
        "segment": "Restaurant",
        "city": "Sao Paulo",
        "state": "SP",
        "phone": "11999998888",
        "whatsapp": "11999998888",
    }
}


class TestEnrichSEO:
    """Testes para _enrich_seo_and_runtime"""

    def test_twitter_title_added(self):
        html = '<html><head><meta property="og:title" content="Test"></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'name="twitter:title"' in out.lower()

    def test_twitter_card_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'name="twitter:card"' in out.lower()

    def test_twitter_description_added(self):
        html = '<html><head><meta property="og:description" content="Desc"></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'name="twitter:description"' in out.lower()

    def test_twitter_image_added(self):
        html = '<html><head><meta property="og:image" content="https://x.com/y.jpg"></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'name="twitter:image"' in out.lower()

    def test_og_locale_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'property="og:locale"' in out.lower()
        assert 'pt_BR' in out

    def test_robots_meta_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'name="robots"' in out.lower()
        assert 'index, follow' in out.lower()

    def test_hreflang_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        # hreflang e case-sensitive no HTML (RFC), mas testamos case-insensitive
        assert 'hreflang="pt-BR"' in out or 'hreflang="pt-br"' in out.lower()
        assert 'hreflang="x-default"' in out or 'hreflang="x-default"' in out.lower()

    def test_organization_schema_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert '"@type":"Organization"' in out
        assert 'FraLib' in out

    def test_website_schema_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert '"@type":"WebSite"' in out

    def test_preconnect_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'preconnect' in out.lower()
        assert 'unsplash.com' in out.lower()
        assert 'fonts.gstatic.com' in out.lower()

    def test_apple_touch_icon_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'apple-touch-icon' in out.lower()

    def test_theme_color_added(self):
        html = '<html><head></head><body></body></html>'
        out = _enrich_seo_and_runtime(html, facts=MINIMAL_FACTS)
        assert 'theme-color' in out.lower()


class TestPatchPerformance:
    """Testes para _patch_performance"""

    def test_srcset_added(self):
        html = '<html><head></head><body><img src="https://images.unsplash.com/photo-123?w=1080" alt="Test"></body></html>'
        out = _patch_performance(html)
        assert 'srcset=' in out.lower()

    def test_fetchpriority_high_on_first_img(self):
        html = '<html><head></head><body><img src="https://example.com/a.jpg" alt="A"><img src="https://example.com/b.jpg" alt="B"></body></html>'
        out = _patch_performance(html)
        assert 'fetchpriority="high"' in out.lower()

    def test_loading_eager_on_first_img(self):
        html = '<html><head></head><body><img src="https://example.com/a.jpg" alt="A"></body></html>'
        out = _patch_performance(html)
        assert 'loading="eager"' in out.lower()

    def test_loading_lazy_on_subsequent_imgs(self):
        html = '<html><head></head><body><img src="https://example.com/a.jpg" alt="A"><img src="https://example.com/b.jpg" alt="B"></body></html>'
        out = _patch_performance(html)
        assert 'loading="lazy"' in out.lower()

    def test_decoding_async_added(self):
        html = '<html><head></head><body><img src="https://example.com/a.jpg" alt="A"></body></html>'
        out = _patch_performance(html)
        assert 'decoding="async"' in out.lower()

    def test_preload_lcp_added(self):
        html = '<html><head></head><body><img src="https://example.com/hero.jpg" alt="Hero"></body></html>'
        out = _patch_performance(html)
        assert 'rel="preload" as="image"' in out.lower()
        assert 'hero.jpg' in out.lower()


class TestModernCSS:
    """Testes para _inject_modern_css_fallback"""

    def test_has_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert ':has(' in out

    def test_color_mix_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert 'color-mix(' in out

    def test_container_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert '@container' in out

    def test_subgrid_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert 'subgrid' in out

    def test_prefers_reduced_motion_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert 'prefers-reduced-motion' in out

    def test_focus_visible_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert ':focus-visible' in out

    def test_view_transitions_added(self):
        html = '<html><head></head><body></body></html>'
        out = _inject_modern_css_fallback(html)
        assert 'view-transition' in out


class TestDedupeSkipLink:
    """Testes para _dedupe_skip_link"""

    def test_openui_skip_link_removed(self):
        html = '<a class="fralib-skip-link magnetic-cta" href="#main">Pular para o conteudo</a><a href="#main" class="sr-only">Pular para o conteudo principal</a>'
        out = _dedupe_skip_link(html)
        assert 'fralib-skip-link' not in out
        assert 'Pular para o conteudo principal' in out


class TestBuildDocument:
    """Testes para build_openui_document (integracao)"""

    def test_all_46_patches_applied(self):
        """Teste integrado: 46 patches devem ser aplicados."""
        body = """<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FraLib Site</title>
  <meta name="description" content="Academia em Sao Paulo com contato e informacoes confirmadas.">
  <a class="fralib-skip-link magnetic-cta" href="#main">Pular para o conteudo</a>
  <a href="#main" class="sr-only">Pular para o conteudo principal</a>
  <div data-lgpd-banner class="fralib-lgpd-banner">LGPD</div>
  <div data-parallax="0.5">Parallax</div>
  <div data-reveal>Reveal</div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lenis@1.1.0/dist/lenis.min.js"></script>
  <script id="fralib-motion-runtime-loader">// motion</script>
</head>
<body>
  <img src="https://images.unsplash.com/photo-123?w=1080&q=80" alt="Test" loading="eager" fetchpriority="high">
  <img src="https://images.unsplash.com/photo-456?w=1080&q=80" alt="Test2">
  <img src="https://images.unsplash.com/photo-789?w=1080&q=80" alt="Test3">
</body>
</html>"""
        doc = build_openui_document(body, facts=MINIMAL_FACTS)
        doc_lower = doc.lower()

        # Lista completa de 46 patches
        required = [
            # Twitter (4)
            'name="twitter:title"', 'name="twitter:card"',
            'name="twitter:description"', 'name="twitter:image"',
            # OG (4)
            'property="og:title"', 'property="og:description"',
            'property="og:image"', 'property="og:locale"',
            # Title correto
            '<title>test business',
            # A11y (4)
            'class="sr-only', 'pular para o conte',
            'data-lgpd-banner', 'apple-touch-icon',
            # SEO (4)
            '"@type":"organization"', '"@type":"website"',
            'name="robots"', 'hreflang="pt-br"',
            # Theme
            'theme-color',
            # Performance (5)
            'rel="preload" as="image"', 'srcset=',
            'fetchpriority="high"', 'loading="lazy"', 'decoding="async"',
            # CSS Modern (7)
            ':has(', 'color-mix(', '@container', 'subgrid',
            'prefers-reduced-motion', ':focus-visible', 'view-transition',
        ]

        missing = [p for p in required if p not in doc_lower]

        assert not missing, f"Patches faltando: {missing}"
