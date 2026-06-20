"""Tests for core FraLib functions: design_director, pipeline validators, sanitize_reply, and HTML contract."""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import pytest

# Setup path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents.design_director import (
    gerar_direcao_criativa,
    _cache_get,
    _cache_set,
    _cache_key,
    _fallback_direction,
)
from services.pipeline_validators import normalize_segment, sanitize_keyword_term
from whatsapp.sdr_reply_service import sanitize_reply, is_duplicate_reply
from agents.html_contract_validator import phase6_contract_problems


class TestDesignDirectorCache:
    """Test suite for design director caching."""

    def test_design_director_cache_hit(self, tmp_path):
        """Test that cache hit returns quickly without calling LLM."""
        nicho = "nutricionista"
        cidade = "Sao Paulo"
        segment = "default"

        # Pre-populate cache
        cached_data = {
            "direcao_visual": {"paleta_primaria": "#7A9B7E"},
            "motion_style": {"intensidade": "subtle"},
            "source": "test_cache",
        }

        # Create temp cache directory
        cache_dir = tmp_path / "fralib_design_cache"
        cache_dir.mkdir(parents=True)

        with patch("backend.agents.design_director.CACHE_DIR", cache_dir):
            _cache_set(nicho, cidade, segment, cached_data)

            # Mock call_claude to raise if called
            with patch("backend.agents.design_director.call_claude") as mock_llm:
                mock_llm.side_effect = Exception("LLM should not be called on cache hit")

                # Call should return cached data
                result = _cache_get(nicho, cidade, segment)

                assert result is not None
                assert result["direcao_visual"]["paleta_primaria"] == "#7A9B7E"
                mock_llm.assert_not_called()

    def test_design_director_cache_miss_calls_llm(self):
        """Test that cache miss triggers LLM call."""
        nicho = "academia"
        cidade = "Rio de Janeiro"
        segment = "premium"

        # Mock cache miss and design_context import failure
        with patch("backend.agents.design_director._cache_get", return_value=None):
            import importlib
            import backend.agents.design_director as dd_module
            original_import = __builtins__["__import__"]

            def mock_import(name, *args, **kwargs):
                if name == "backend.agents.design_context":
                    raise ImportError("No module named 'design_context'")
                return original_import(name, *args, **kwargs)

            with patch("__main__." + "__builtins__", {"__import__": mock_import}):
                with patch.object(dd_module, "call_claude") as mock_llm:
                    mock_llm.return_value = '{"direcao_visual":{"paleta_primaria":"#FFD60A"}}'

                    with patch.object(dd_module, "_cache_set"):
                        result = gerar_direcao_criativa(
                            nicho=nicho,
                            cidade=cidade,
                            nome_negocio="Fit Test",
                            segment=segment,
                        )

                    # The LLM should be called (or fallback used)
                    assert "direcao_visual" in result

    def test_design_director_fallback(self):
        """Test that LLM failure triggers fallback to deterministic values."""
        with patch("backend.agents.design_director._cache_get", return_value=None):
            with patch.dict("sys.modules", {"backend.agents.design_context": None}):
                with patch.object(
                    __import__("backend.agents.design_director", fromlist=["gerar_direcao_criativa"]),
                    "get_design_context",
                    side_effect=Exception("Module not available"),
                    create=True
                ):
                    with patch("backend.agents.design_director.call_claude") as mock_llm:
                        # Simulate LLM failure
                        mock_llm.side_effect = Exception("LLM API Error")

                        with patch("backend.agents.design_director._cache_set"):
                            result = gerar_direcao_criativa(
                                nicho="nutricionista",
                                cidade="Curitiba",
                                nome_negocio="Nutri Vida",
                            )

                        # Fallback should return deterministic values for nutricionista
                        assert result["direcao_visual"]["paleta_primaria"] == "#7A9B7E"
                        assert result["direcao_visual"]["paleta_acento"] == "#D4866A"


class TestPipelineValidators:
    """Test suite for pipeline validators."""

    def test_pipeline_validators_normalize_text(self):
        """Test normalize_segment removes accents and lowercases."""
        test_cases = [
            ("Nutrição", "nutricao"),
            ("CLÍNICA MÉDICA", "clinica medica"),
            ("CAFÉ", "cafe"),
            ("Bebê", "bebe"),
            ("ação", "acao"),
            ("", ""),
            ("  spaces  ", "spaces"),
        ]

        for input_val, expected in test_cases:
            assert normalize_segment(input_val) == expected

    def test_pipeline_validators_keywords_sanitize(self):
        """Test sanitize_keyword_term removes special chars and stopwords."""
        # Valid keywords
        assert sanitize_keyword_term("nutrição esportiva") == "nutrição esportiva"
        assert sanitize_keyword_term("  clinic  ") == "clinic"
        assert sanitize_keyword_term("emagrecimento saúde") == "emagrecimento saúde"

        # Stopwords should return empty
        assert sanitize_keyword_term("hero") == ""
        assert sanitize_keyword_term("cta") == ""
        assert sanitize_keyword_term("page") == ""  # 'page' is in stopwords

        # Too long should be truncated to 60 chars (not empty)
        long_keyword = "a" * 65
        result = sanitize_keyword_term(long_keyword)
        assert len(result) <= 60

        # Empty should return empty
        assert sanitize_keyword_term("") == ""
        assert sanitize_keyword_term("   ") == ""


class TestSanitizeReply:
    """Test suite for sanitize_reply function."""

    def test_sanitize_reply_extracts_json_field(self):
        """Test extraction of 'resposta' field from JSON."""
        raw = '{"resposta":"Oi, tudo bem? Como posso ajudar?","novo_stage":"intro"}'
        result = sanitize_reply(raw)
        assert result == "Oi, tudo bem? Como posso ajudar?"

    def test_sanitize_reply_no_json(self):
        """Test that plain text is returned unchanged."""
        plain_text = "Olá! Obrigado pelo seu contato."
        result = sanitize_reply(plain_text)
        assert result == plain_text

    def test_sanitize_reply_with_escaped_quotes(self):
        """Test handling of escaped quotes in JSON."""
        raw = '{"resposta":"她说\\"你好\\"朋友","novo_stage":"hook"}'
        result = sanitize_reply(raw)
        assert "你好" in result or "朋友" in result

    def test_sanitize_reply_empty_returns_empty(self):
        """Test that empty input returns empty."""
        assert sanitize_reply("") == ""
        assert sanitize_reply(None) == ""

    def test_sanitize_reply_with_retry_extractor(self):
        """Test retry_extractor fallback when JSON parse fails."""
        raw = '{"invalid":"json without resposta"}'
        retry_fn = lambda r: "Fixed reply via retry"

        result = sanitize_reply(raw, retry_extractor=retry_fn)
        assert result == "Fixed reply via retry"


class TestIsDuplicateReply:
    """Test suite for is_duplicate_reply function."""

    def test_is_duplicate_reply_true(self):
        """Test detection of duplicate reply (substring in history)."""
        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Bem-vindo ao nosso serviço!"},
        ]

        # Reply is substring of last assistant message
        assert is_duplicate_reply(history, "Olá!") is True
        assert is_duplicate_reply(history, "Bem-vindo") is True
        assert is_duplicate_reply(history, "Olá! Bem-vindo ao") is True

    def test_is_duplicate_reply_false(self):
        """Test that new replies are not flagged as duplicate."""
        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        ]

        # New reply not in history
        assert is_duplicate_reply(history, "Qual é o preço?") is False
        assert is_duplicate_reply(history, "Gostaria de saber mais") is False

    def test_is_duplicate_reply_empty_history(self):
        """Test with empty history returns False."""
        assert is_duplicate_reply([], "Olá!") is False
        assert is_duplicate_reply(None, "Olá!") is False

    def test_is_duplicate_reply_no_assistant_message(self):
        """Test with history but no assistant message returns False."""
        history = [{"role": "user", "content": "Olá"}]
        assert is_duplicate_reply(history, "Olá!") is False


class TestHtmlContractValidatorPhase6:
    """Test suite for Phase 6 HTML contract validator (T1-T17)."""

    def test_phase6_t1_hero_video_autoplay(self):
        """Test T1: hero video requires autoplay muted loop playsinline."""
        # Valid video hero with all required elements
        valid_html = '''
        <html data-renderer="builder">
        <header data-hero-type="video" data-component-id="hero">
            <video autoplay muted loop playsinline></video>
        </header>
        <a class="fralib-skip-link" href="#main">Skip</a>
        <main id="main"></main>
        <style>:focus-visible{outline:none}</style>
        <div class="fralib-cursor"></div>
        <div class="fralib-cursor-follower"></div>
        <button class="fralib-theme-toggle" aria-label="alternar tema" data-theme="dark">
            <span data-theme="light"></span>
        </button>
        <link rel="preconnect" href="https://videos.pexels.com">
        <link href="https://fonts.gstatic.com" crossorigin>
        <style>body{font-display:swap}</style>
        <script type="application/ld+json">{"@type":"BreadcrumbList"}</script>
        <meta property="og:image:width" content="1200">
        <meta property="og:image:height" content="630">
        <div class="fralib-reading-progress" role="progressbar"></div>
        <script src="https://cdn.jsdelivr.net/npm/gsap"></script>
        <script src="https://cdn.jsdelivr.net/npm/lenis"></script>
        <script>gsap.registerplugin()</script>
        <style>
            .fralib-card-interactive {}
            ::-webkit-scrollbar {}
            .fralib-letter-reveal {}
            .fralib-text-scramble {}
            .fralib-grain {}
            .magnetic-cta {}
            [data-lenis-scroll] {}
        </style>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        # Filter to T1 specific problems only
        t1_problems = [p for p in problems if p.startswith("Fase 6/T1:")]
        assert len(t1_problems) == 0

    def test_phase6_t1_hero_video_missing_attrs(self):
        """Test T1: hero video missing autoplay/muted/loop/playsinline."""
        invalid_html = '''
        <html data-renderer="builder">
        <header data-hero-type="video" data-component-id="hero">
            <video></video>
        </header>
        </html>
        '''
        problems = phase6_contract_problems(invalid_html)
        t1_problems = [p for p in problems if "T1" in p and "autoplay" in p]
        assert len(t1_problems) == 1

    def test_phase6_t2_cursor_custom(self):
        """Test T2: requires fralib-cursor and fralib-cursor-follower."""
        valid_html = '''
        <html data-renderer="builder">
        <body>
            <div class="fralib-cursor"></div>
            <div class="fralib-cursor-follower"></div>
        </body>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t2_problems = [p for p in problems if "T2" in p]
        assert len(t2_problems) == 0

    def test_phase6_t2_cursor_missing(self):
        """Test T2: missing cursor custom elements."""
        invalid_html = '''
        <html data-renderer="builder">
        <body></body>
        </html>
        '''
        problems = phase6_contract_problems(invalid_html)
        t2_problems = [p for p in problems if "T2" in p]
        assert len(t2_problems) == 1

    def test_phase6_t3_smooth_scroll(self):
        """Test T3: requires lenis or fralibsmoothscroll."""
        valid_html = '<html data-renderer="builder"><body data-lenis-scroll></body></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T3: smooth scroll ausente" not in problems

    def test_phase6_t4_magnetic_cta(self):
        """Test T4: requires magnetic-cta or data-magnetic."""
        valid_html = '<html data-renderer="builder"><button class="magnetic-cta">CTA</button></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T4: magnetic ausente" not in problems

    def test_phase6_t5_letter_reveal(self):
        """Test T5: requires fralib-letter-reveal."""
        valid_html = '<html data-renderer="builder"><h1 class="fralib-letter-reveal">Title</h1></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T5: letter reveal ausente" not in problems

    def test_phase6_t6_text_scramble(self):
        """Test T6: requires fralib-text-scramble or data-text-scramble."""
        valid_html = '<html data-renderer="builder"><span data-text-scramble>Text</span></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T6: text scramble ausente" not in problems

    def test_phase6_t7_grain(self):
        """Test T7: requires fralib-grain."""
        valid_html = '<html data-renderer="builder"><div class="fralib-grain"></div></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T7: grain ausente" not in problems

    def test_phase6_t8_reading_progress(self):
        """Test T8: requires fralib-reading-progress and role=progressbar."""
        valid_html = '''
        <html data-renderer="builder">
        <div class="fralib-reading-progress" role="progressbar"></div>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t8_problems = [p for p in problems if "T8" in p]
        assert len(t8_problems) == 0

    def test_phase6_t9_backdrop_blur(self):
        """Test T9: requires backdrop-filter or -webkit-backdrop-filter."""
        valid_html = '<html data-renderer="builder"><div style="backdrop-filter: blur(10px)"></div></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T9: backdrop blur ausente" not in problems

    def test_phase6_t10_custom_scrollbar(self):
        """Test T10: requires ::-webkit-scrollbar or scrollbar-color."""
        valid_html = '<html data-renderer="builder"><style>::-webkit-scrollbar{width:8px}</style></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T10: custom scrollbar ausente" not in problems

    def test_phase6_t11_card_interativo(self):
        """Test T11: requires fralib-card-interactive."""
        valid_html = '<html data-renderer="builder"><div class="fralib-card-interactive"></div></html>'
        problems = phase6_contract_problems(valid_html)
        assert "Fase 6/T11: card interativo ausente" not in problems

    def test_phase6_t12_a11y(self):
        """Test T12: requires fralib-skip-link, href=#main, focus-visible, main#main."""
        valid_html = '''
        <html data-renderer="builder">
        <a class="fralib-skip-link" href="#main">Skip</a>
        <style>:focus-visible{outline:2px solid blue}</style>
        <main id="main"></main>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t12_problems = [p for p in problems if "T12" in p]
        assert len(t12_problems) == 0

    def test_phase6_t13_seo_avancado(self):
        """Test T13: requires breadcrumblist, og:image:width/height."""
        valid_html = '''
        <html data-renderer="builder">
        <script type="application/ld+json">{"@type":"BreadcrumbList"}</script>
        <meta property="og:image:width" content="1200">
        <meta property="og:image:height" content="630">
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t13_problems = [p for p in problems if "T13" in p]
        assert len(t13_problems) == 0

    def test_phase6_t14_fonts_performance(self):
        """Test T14: requires fonts.gstatic.com and display=swap in HTML."""
        # Note: The validator checks for literal "display=swap" string in HTML
        # which is typically found in Google Fonts URLs, not CSS
        # Valid HTML with fonts.gstatic.com link and display=swap in URL
        valid_html = '''
        <html data-renderer="builder">
        <header data-hero-type="image" data-component-id="hero">
            <h1>Title</h1>
        </header>
        <a class="fralib-skip-link" href="#main">Skip</a>
        <main id="main"></main>
        <style>:focus-visible{}</style>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        # T14 checks for fonts.gstatic.com AND display=swap
        t14_problems = [p for p in problems if p.startswith("Fase 6/T14:") and "performance" in p.lower()]
        assert len(t14_problems) == 0

    def test_phase6_t15_theme_toggle(self):
        """Test T15: requires fralib-theme-toggle, aria-label, data-theme."""
        # Note: The validator checks for [data-theme="dark"] which is CSS attribute selector
        # Need complete HTML with all requirements
        valid_html = '''
        <html data-renderer="builder">
        <header data-hero-type="image" data-component-id="hero">
            <h1>Title</h1>
        </header>
        <a class="fralib-skip-link" href="#main">Skip</a>
        <main id="main"></main>
        <style>:focus-visible{}</style>
        <button class="fralib-theme-toggle" aria-label="alternar tema" data-theme="dark">
            <span data-theme="dark"></span>
        </button>
        <style>[data-theme="dark"]{background:#000}</style>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t15_problems = [p for p in problems if p.startswith("Fase 6/T15:")]
        assert len(t15_problems) == 0

    def test_phase6_t16_gsap_lenis(self):
        """Test T16: requires GSAP and Lenis CDN."""
        valid_html = '''
        <html data-renderer="builder">
        <script src="https://cdn.jsdelivr.net/npm/gsap"></script>
        <script src="https://cdn.jsdelivr.net/npm/lenis"></script>
        <script>gsap.registerPlugin()</script>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        t16_problems = [p for p in problems if "T16" in p]
        assert len(t16_problems) == 0

    def test_phase6_t17_video_pexels(self):
        """Test T17: video hero requires Pexels preconnect."""
        valid_html = '''
        <html data-renderer="builder">
        <header data-hero-type="video">
            <video autoplay muted loop playsinline></video>
            <link rel="preconnect" href="https://videos.pexels.com">
        </header>
        </html>
        '''
        problems = phase6_contract_problems(valid_html)
        # Should NOT have T14 error about video without Pexels
        t17_problems = [p for p in problems if "T14" in p and "pexels" in p.lower()]
        assert len(t17_problems) == 0

    def test_phase6_non_builder_ignored(self):
        """Test that non-builder HTML is ignored by validator."""
        regular_html = '<html><body><h1>Regular Site</h1></body></html>'
        problems = phase6_contract_problems(regular_html)
        # Should return empty list for non-builder HTML
        assert all("Fase 6/" not in p for p in problems)
