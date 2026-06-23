"""Tests para o sanitizer de HTML — fecha tags de bloco orfas (bug "Im Tema").

Cobre o bug classico onde o LLM gera `<h2>Im\nTema.</h2>` sem fechar,
e o parser de motion_runtime injetado depois quebra o layout.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.services.html_sanitizer import (
    close_unclosed_block_tags,
    close_unclosed_before_script_injection,
    BLOCK_TAGS,
)


class TestCloseUnclosedBlockTags:
    def test_no_change_when_html_is_valid(self):
        html = "<html><body><h2>Titulo</h2><p>texto</p></body></html>"
        assert close_unclosed_block_tags(html) == html

    def test_closes_unclosed_h2_before_body(self):
        html = "<html><body><h2>Im\nTema."
        result = close_unclosed_block_tags(html + "</body></html>")
        assert "</h2>" in result
        assert result.count("<h2>") == result.count("</h2>")

    def test_closes_unclosed_h2_in_middle(self):
        html = (
            "<html><body>"
            "<h2>Primeiro</h2>"
            "<p>texto</p>"
            "<h2>Segundo sem fechar"
            "</body></html>"
        )
        result = close_unclosed_block_tags(html)
        assert result.count("<h2>") == result.count("</h2>")

    def test_closes_unclosed_section(self):
        html = "<html><body><section><h2>Titulo</h2><section>"
        result = close_unclosed_block_tags(html + "</body></html>")
        assert result.count("<section>") == result.count("</section>")

    def test_idempotent(self):
        html = "<html><body><h2>Orfao</h2>"
        once = close_unclosed_block_tags(html + "</body></html>")
        twice = close_unclosed_block_tags(once)
        assert once == twice

    def test_empty_html(self):
        assert close_unclosed_block_tags("") == ""

    def test_no_body_tag_returns_unchanged(self):
        html = "<h2>sozinho</h2>"
        assert close_unclosed_block_tags(html) == html

    def test_preserves_void_tags_unclosed(self):
        # <br> e void — nao deve aparecer </br> injetado
        html = "<html><body><p>texto<br>mais texto</body></html>"
        result = close_unclosed_block_tags(html)
        assert "<br>" in result
        assert "</br>" not in result.lower()

    def test_multiple_unclosed_tags_lifo_order(self):
        # <section><h2> sem fechar ambos — deve fechar na ordem inversa
        html = "<html><body><section><h2>Sem fechar"
        result = close_unclosed_block_tags(html + "</body></html>")
        assert result.count("<section>") == result.count("</section>")
        assert result.count("<h2>") == result.count("</h2>")

    def test_real_karoline_bug(self):
        """Reproduz o bug exato do site Karoline: <h2>Im\nTema.</h2> sem fechar."""
        html = (
            "<html><body>"
            "<h2 id=\"galeria-title\">Im\nTema.</h2>\n"
            "<!-- motion_runtime_loader injeta <script> aqui DEPOIS -->"
            "<script id=\"fralib-motion-runtime-loader\">/* js */</script>"
            "</body></html>"
        )
        result = close_unclosed_before_script_injection(html)
        # Deve ter inserido </h2> antes do <script id="fralib-motion-runtime-loader">
        idx_script = result.find('<script id="fralib-motion-runtime-loader"')
        idx_close_h2 = result.rfind("</h2>", 0, idx_script)
        assert idx_close_h2 != -1, "expected </h2> before script injection"
        assert idx_close_h2 < idx_script


class TestCloseUnclosedBeforeScriptInjection:
    def test_closes_before_motion_runtime(self):
        html = (
            "<html><body>"
            "<h2>Orfao</h2>"
            "<script id=\"fralib-motion-runtime\">/* js */</script>"
            "</body></html>"
        )
        result = close_unclosed_before_script_injection(html)
        # HTML ja bem-formado nao deve ter nada inserido
        assert result.count("<h2>") == result.count("</h2>")

    def test_closes_before_lgpd_runtime(self):
        html = (
            "<html><body>"
            "<h2>Orfao</h2>"
            "<script id=\"fralib-lgpd-runtime\">/* js */</script>"
            "</body></html>"
        )
        result = close_unclosed_before_script_injection(html)
        assert result.count("<h2>") == result.count("</h2>")

    def test_falls_back_to_body_close(self):
        html = "<html><body><h2>Orfao</h2>"
        result = close_unclosed_before_script_injection(html + "</body></html>")
        assert "</h2>" in result


class TestBlockTagsConstant:
    def test_contains_essential_block_tags(self):
        assert "h1" in BLOCK_TAGS
        assert "h2" in BLOCK_TAGS
        assert "h3" in BLOCK_TAGS
        assert "section" in BLOCK_TAGS
        assert "div" in BLOCK_TAGS
        assert "p" in BLOCK_TAGS
        assert "footer" in BLOCK_TAGS


if __name__ == "__main__":
    test = TestCloseUnclosedBlockTags()
    methods = [m for m in dir(test) if m.startswith("test_")]
    passed = 0
    failed = 0
    for m in methods:
        try:
            getattr(test, m)()
            print(f"OK {m}")
            passed += 1
        except Exception as e:
            print(f"FAIL {m}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} passados")
    sys.exit(0 if failed == 0 else 1)
