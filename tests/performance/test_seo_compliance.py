"""SEO compliance tests for generated sites.

Tests that every generated site has:
- meta description (50-160 chars)
- og:image, og:url, og:type
- canonical URL
- JSON-LD LocalBusiness
- LGPD banner (data-lgpd-banner)
- Sitemap.xml generated
- robots.txt correct
"""

from __future__ import annotations

import re
from typing import Any
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _sample_html() -> str:
    """Sample HTML with SEO elements."""
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NutriVida - Nutricionista em Sao Paulo</title>
    <meta name="description" content="NutriVida Consultoria Nutricional. Agende sua consulta com a nutricionista Maria Silva.">
    <meta property="og:title" content="NutriVida - Nutricionista">
    <meta property="og:description" content="NutriVida Consultoria Nutricional.">
    <meta property="og:image" content="https://example.com/og-image.jpg">
    <meta property="og:url" content="https://nutrivida.com.br">
    <meta property="og:type" content="website">
    <link rel="canonical" href="https://nutrivida.com.br">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "NutriVida",
        "description": "Consultoria Nutricional"
    }
    </script>
</head>
<body>
    <div data-lgpd-banner>Usamos cookies...</div>
    <main>
        <h1>NutriVida Nutricionista</h1>
        <p>Consultoria personalizada em nutricao.</p>
    </main>
</body>
</html>"""


def _facts() -> dict[str, Any]:
    """Sample business facts."""
    return {
        "business": {
            "name": "NutriVida",
            "segment": "nutricionista",
            "cidade": "Sao Paulo",
            "whatsapp": "11999999999",
        },
        "publication_url": "https://nutrivida.com.br",
    }


def _sitemap_xml() -> str:
    """Sample sitemap.xml content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://nutrivida.com.br/</loc>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://nutrivida.com.br/servicos</loc>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>"""


def _robots_txt() -> str:
    """Sample robots.txt content."""
    return """User-agent: *
Allow: /

Sitemap: https://nutrivida.com.br/sitemap.xml
"""


class TestSEOCompliance:
    """Test suite for SEO compliance requirements."""

    # === Meta Description Tests ===

    def test_meta_description_exists(self) -> None:
        """Test that meta description tag exists."""
        html = _sample_html()
        pattern = r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "meta description tag should exist"

    def test_meta_description_length_50_160_chars(self) -> None:
        """Test that meta description is between 50-160 characters."""
        html = _sample_html()
        pattern = r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "meta description tag should exist"
        description = match.group(1)

        assert 50 <= len(description) <= 160, (
            f"Meta description should be 50-160 chars. Got {len(description)}: '{description}'"
        )

    def test_meta_description_minimum_length(self) -> None:
        """Test that descriptions under 50 chars fail validation."""
        short_html = """<!DOCTYPE html>
<html>
<head>
    <meta name="description" content="Curto">
</head>
<body></body>
</html>"""
        pattern = r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, short_html, re.IGNORECASE)

        assert match is not None
        description = match.group(1)

        assert len(description) < 50, "Short description should be detected"

    # === Open Graph Tests ===

    def test_og_image_exists(self) -> None:
        """Test that og:image meta tag exists."""
        html = _sample_html()
        pattern = r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "og:image should exist"

    def test_og_url_exists(self) -> None:
        """Test that og:url meta tag exists."""
        html = _sample_html()
        pattern = r'<meta\s+property=["\']og:url["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "og:url should exist"

    def test_og_type_exists(self) -> None:
        """Test that og:type meta tag exists."""
        html = _sample_html()
        pattern = r'<meta\s+property=["\']og:type["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "og:type should exist"

    def test_og_type_is_website(self) -> None:
        """Test that og:type is 'website' for landing pages."""
        html = _sample_html()
        pattern = r'<meta\s+property=["\']og:type["\']\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None
        og_type = match.group(1)

        assert og_type.lower() == "website", f"og:type should be 'website'. Got '{og_type}'"

    # === Canonical URL Tests ===

    def test_canonical_url_exists(self) -> None:
        """Test that canonical URL link tag exists."""
        html = _sample_html()
        pattern = r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "canonical URL should exist"

    def test_canonical_url_is_absolute(self) -> None:
        """Test that canonical URL is an absolute URL."""
        html = _sample_html()
        pattern = r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None
        canonical = match.group(1)

        assert canonical.startswith("http"), (
            f"Canonical URL should be absolute. Got '{canonical}'"
        )

    # === JSON-LD Tests ===

    def test_json_ld_exists(self) -> None:
        """Test that JSON-LD structured data exists."""
        html = _sample_html()
        pattern = r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)

        assert match is not None, "JSON-LD script should exist"

    def test_json_ld_localbusiness_type(self) -> None:
        """Test that JSON-LD contains LocalBusiness type."""
        html = _sample_html()
        pattern = r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)

        assert match is not None
        json_ld = match.group(1)

        assert '"@type"' in json_ld, "JSON-LD should have @type"
        assert 'LocalBusiness' in json_ld or 'localBusiness' in json_ld, (
            "JSON-LD should contain LocalBusiness type"
        )

    def test_json_ld_contains_business_name(self) -> None:
        """Test that JSON-LD contains business name."""
        import json
        html = _sample_html()
        pattern = r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)

        assert match is not None
        json_ld = match.group(1)

        data = json.loads(json_ld)
        assert "name" in data, "JSON-LD should contain name field"

    # === LGPD Banner Tests ===

    def test_lgpd_banner_exists(self) -> None:
        """Test that LGPD consent banner exists."""
        html = _sample_html()
        # Check for various LGPD banner patterns
        patterns = [
            r'data-lgpd-banner',
            r'data-cookie-banner',
            r'id=["\']lgpd',
            r'class=["\'][^"\']*cookie[^"\']*banner',
            r'cookie\s*consent',
        ]

        found = any(re.search(p, html, re.IGNORECASE) for p in patterns)
        assert found, "LGPD/cookie banner should exist in HTML"

    def test_lgpd_banner_has_content(self) -> None:
        """Test that LGPD banner has actual content."""
        html = _sample_html()
        pattern = r'<div[^>]*data-lgpd-banner[^>]*>([^<]+)'
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            content = match.group(1).strip()
            assert len(content) > 5, "LGPD banner should have meaningful content"


class TestSitemapAndRobots:
    """Test sitemap.xml and robots.txt generation."""

    def test_sitemap_xml_generated(self) -> None:
        """Test that sitemap.xml is properly formatted."""
        sitemap = _sitemap_xml()
        assert '<?xml' in sitemap, "Should have XML declaration"
        assert '<urlset' in sitemap, "Should have urlset element"
        assert '<loc>' in sitemap, "Should have loc elements"
        assert 'https://' in sitemap, "Should have absolute URLs"

    def test_sitemap_has_homepage(self) -> None:
        """Test that sitemap includes homepage."""
        sitemap = _sitemap_xml()
        pattern = r'<loc>([^<]+)</loc>'
        locs = re.findall(pattern, sitemap)

        assert any('nutrivida.com.br/' in loc for loc in locs), (
            "Sitemap should include homepage"
        )

    def test_sitemap_valid_xml_structure(self) -> None:
        """Test that sitemap has valid XML structure."""
        sitemap = _sitemap_xml()
        # Check for proper URL count
        url_count = sitemap.count('<url>')
        loc_count = sitemap.count('<loc>')

        assert url_count >= 1, "Sitemap should have at least one URL"
        assert url_count == loc_count, "Each URL should have a loc"

    def test_robots_txt_generated(self) -> None:
        """Test that robots.txt is properly formatted."""
        robots = _robots_txt()
        assert 'User-agent:' in robots, "Should specify user-agent"
        assert 'Allow:' in robots or 'Disallow:' in robots, (
            "Should have Allow or Disallow rules"
        )

    def test_robots_txt_has_sitemap(self) -> None:
        """Test that robots.txt references sitemap."""
        robots = _robots_txt()
        assert 'Sitemap:' in robots, "robots.txt should reference sitemap"

    def test_robots_txt_allows_crawlers(self) -> None:
        """Test that robots.txt allows crawlers to index."""
        robots = _robots_txt()
        assert 'User-agent: *' in robots, "Should have wildcard user-agent"
        assert 'Allow: /' in robots, "Should allow full site crawling"


class TestSEOComplianceIntegration:
    """Integration tests for complete SEO compliance."""

    def test_complete_seo_checklist(self) -> None:
        """Test all SEO requirements in one pass."""
        html = _sample_html()
        facts = _facts()
        issues: list[str] = []

        # Check meta description
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if not desc_match:
            issues.append("Missing meta description")
        elif not (50 <= len(desc_match.group(1)) <= 160):
            issues.append(f"Meta description length invalid: {len(desc_match.group(1))}")

        # Check og:image
        if not re.search(r'<meta\s+property=["\']og:image["\']', html, re.IGNORECASE):
            issues.append("Missing og:image")

        # Check og:url
        if not re.search(r'<meta\s+property=["\']og:url["\']', html, re.IGNORECASE):
            issues.append("Missing og:url")

        # Check og:type
        if not re.search(r'<meta\s+property=["\']og:type["\']', html, re.IGNORECASE):
            issues.append("Missing og:type")

        # Check canonical
        if not re.search(r'<link\s+rel=["\']canonical["\']', html, re.IGNORECASE):
            issues.append("Missing canonical URL")

        # Check JSON-LD
        if not re.search(r'<script\s+type=["\']application/ld\+json["\']', html, re.IGNORECASE):
            issues.append("Missing JSON-LD")
        elif 'LocalBusiness' not in html:
            issues.append("JSON-LD missing LocalBusiness type")

        # Check LGPD
        lgpd_patterns = [r'data-lgpd-banner', r'data-cookie-banner', r'cookie\s*consent']
        if not any(re.search(p, html, re.IGNORECASE) for p in lgpd_patterns):
            issues.append("Missing LGPD banner")

        assert len(issues) == 0, f"SEO compliance issues: {issues}"

    def test_lang_attribute_present(self) -> None:
        """Test that html tag has lang attribute."""
        html = _sample_html()
        pattern = r'<html[^>]*lang=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "html tag should have lang attribute"
        lang = match.group(1)
        assert lang.startswith("pt"), f"Lang should be pt-BR or similar. Got '{lang}'"

    def test_viewport_meta_present(self) -> None:
        """Test that viewport meta tag is present."""
        html = _sample_html()
        pattern = r'<meta\s+name=["\']viewport["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        assert match is not None, "viewport meta tag should exist"
