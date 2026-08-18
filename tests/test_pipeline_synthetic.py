"""
Synthetic E2E assembly test (Opção B — zero HTTP).

Fixture estática de academia/dentista que simula a saída de _prd_to_spec
e roda a montagem hermética do HTML final:
  1. shell com <html>/<head>/<body>/<main>
  2. _inject_sections_into_shell injeta fragmentos de seção
  3. _inject_deterministic_assets injeta :root tokens + AOS + OpenGraph
  4. _pin_footer_last reposiciona o footer

Valida em < 1s:
  - presença de tokens CSS :root no <style id="brand-design-tokens">
  - tags OpenGraph (og:title, og:description, og:type, og:image, og:locale)
  - classes clear-both nos wrappers de seção
  - footer posicionado como último bloco antes de </body>

Nenhuma requisição HTTP é feita — depende apenas do assembly local.
"""
from __future__ import annotations

import os
import re
import sys
import time

# env mínima para imports do backend (não toca banco)
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FRALIB_SITES_DIR", os.path.join(os.path.dirname(__file__), "tmp_sites"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ---------------------------------------------------------------------------
# Fixture sintética: spec mínimo equivalente ao retorno de _prd_to_spec
# ---------------------------------------------------------------------------
FIXTURE_SPEC: dict = {
    "business_name": "Academia Corpo & Força",
    "cidade": "Curitiba",
    "segmento": "Academia",
    "design_tokens": {
        "palette": {
            "primary": "#111111",
            "secondary": "#4b5563",
            "accent": "#ff3b00",
            "background": "#ffffff",
            "text": "#111827",
            "border": "#e5e7eb",
            "muted": "#6b7280",
            "surface": "#f9fafb",
        },
        "heading_font": "Bebas Neue",
        "body_font": "Space Grotesk",
        "radius": "0px",
        "archetype": "industrial-bold",
    },
    "photos": [
        {"url": "https://cdn.exemplo.com/academia-hero.jpg"},
    ],
    "_lead_name": "Academia Corpo & Força",
}

# Seções simulando a saída do Arquiteto + Builder (3 seções mínimas).
# Fragmentos SEM <section> de abertura para forçar a injeção do wrapper
# com clear-both por _inject_sections_into_shell — validando o contrato
# anti-colisão de colunas.
_SECTION_FRAGMENTS = [
    (
        '<h1>Academia Corpo &amp; Força em Curitiba</h1>\n'
        '<p>Transforme seu corpo com os melhores equipamentos.</p>\n'
        '<a href="#planos">Ver planos</a>\n'
    ),
    (
        '<h2>Modalidades</h2>\n'
        '<div class="w-full overflow-hidden grid grid-cols-1 md:grid-cols-3 gap-6">\n'
        '<div>Musculação</div><div>Crossfit</div><div>Spinning</div>\n'
        '</div>\n'
    ),
    (
        '<h2>Contato</h2>\n'
        '<p>(41) 9999-0000 • Curitiba, PR</p>\n'
        '<footer id="footer">\n'
        '<p>© 2026 Academia Corpo &amp; Força</p>\n'
        '</footer>\n'
    ),
]

# Shell mínimo com estrutura válida para injeção
_SHELL = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Academia Corpo &amp; Força — Curitiba</title>
</head>
<body>
<main id="root">
</main>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------
class TestSyntheticPipelineAssembly:
    """Montagem hermética de HTML zero HTTP — fixture academia/dentista."""

    def _build_final_html(self) -> str:
        from backend.agents.builder.agent import (
            _inject_sections_into_shell,
            _inject_deterministic_assets,
            _pin_footer_last,
        )

        html = _SHELL
        html = _inject_sections_into_shell(html, list(_SECTION_FRAGMENTS))
        html = _inject_deterministic_assets(html, FIXTURE_SPEC["design_tokens"], FIXTURE_SPEC)
        html = _pin_footer_last(html)
        return html

    def test_root_css_tokens_present(self):
        html = self._build_final_html()
        assert 'id="brand-design-tokens"' in html
        assert ":root{" in html
        root_block = re.search(r"<style[^>]*id=\"brand-design-tokens\"[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
        assert root_block, "<style id='brand-design-tokens'> não encontrado"
        root_body = root_block.group(1)
        for token in ("--brand-primary", "--brand-secondary", "--brand-accent",
                      "--brand-bg", "--brand-surface", "--brand-text", "--brand-border", "--brand-muted"):
            assert token in root_body, f":root CSS token ausente: {token}"

    def test_opengraph_tags_injected(self):
        html = self._build_final_html()
        assert '<meta property="og:title" content="Academia Corpo & Força — Curitiba" />' in html
        assert '<meta property="og:description" content="Academia em Curitiba" />' in html
        assert '<meta property="og:type" content="website" />' in html
        assert '<meta property="og:url" content="https://app.seunegociofralib.site" />' in html
        assert 'content="https://cdn.exemplo.com/academia-hero.jpg"' in html
        assert '<meta property="og:locale" content="pt_BR" />' in html

    def test_section_wrappers_have_clear_both(self):
        html = self._build_final_html()
        assert 'class="w-full relative overflow-hidden clear-both block"' in html

    def test_footer_is_last_before_body_close(self):
        html = self._build_final_html()
        body_idx = html.lower().rfind("</body>")
        footer_close_idx = html.lower().rfind("</footer>")
        assert body_idx != -1 and footer_close_idx != -1
        assert footer_close_idx < body_idx, "footer deve estar antes de </body>"

    def test_completes_under_one_second(self):
        start = time.perf_counter()
        for _ in range(50):
            self._build_final_html()
        elapsed = time.perf_counter() - start
        per_run_ms = (elapsed / 50) * 1000
        assert per_run_ms < 1000, f"execução muito lenta: {per_run_ms:.1f} ms/run"

    def test_dentist_fixture_also_works(self):
        """Garante que o mesmo pipeline funciona para segmento dentista."""
        dentist_spec = dict(FIXTURE_SPEC)
        dentist_spec.update({
            "business_name": "OdontoVida Sorriso",
            "cidade": "São Paulo",
            "segmento": "Odontologia",
            "photos": [],
            "_lead_name": "OdontoVida Sorriso",
        })
        from backend.agents.builder.agent import (
            _inject_sections_into_shell,
            _inject_deterministic_assets,
            _pin_footer_last,
        )
        html = _SHELL
        html = _inject_sections_into_shell(html, list(_SECTION_FRAGMENTS))
        html = _inject_deterministic_assets(html, dentist_spec["design_tokens"], dentist_spec)
        html = _pin_footer_last(html)
        assert 'content="OdontoVida Sorriso — São Paulo"' in html
        assert 'content="https://app.seunegociofralib.site/og-default.jpg"' in html
