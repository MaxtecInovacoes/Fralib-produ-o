from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from backend.endpoints.pipeline_phase_helpers import (
    curate_lead_assets,
    ensure_keyword_research,
    ensure_jina_insights,
    build_prompt_phase_outputs,
)


def test_ensure_keyword_research_skips_when_present():
    state = SimpleNamespace(
        keyword_research={"cached": True},
        lead_obj=SimpleNamespace(lead=SimpleNamespace(segmento="fitness", cidade="sp")),
    )
    logs = []

    def _log(msg, tipo):
        logs.append((msg, tipo))

    ensure_keyword_research(state, _log)

    assert state.keyword_research == {"cached": True}
    assert logs == []


def test_curate_lead_assets_trims_reviews_and_maps_url():
    state = SimpleNamespace(
        lead_nome="Academia Nova",
        jina_insights="x" * 6001,
        lead_obj=SimpleNamespace(
            lead=SimpleNamespace(
                cidade="Sao Paulo",
                endereco="Rua A, 123",
                address="Rua A, 123",
            )
        ),
        lead_raw_data={
            "reviews": [
                {"texto": "curta"},
                {"texto": "uma avaliacao bem mais longa que a outra"},
                {"text": "média"},
                {"texto": "texto ainda maior do que a segunda avaliacao"},
                {"texto": "abc"},
                {"texto": "extra"},
            ],
            "google_maps_embed": "",
        },
    )
    logs = []

    def _log(msg, tipo):
        logs.append((msg, tipo))

    curate_lead_assets(state, _log)

    assert len(state.lead_raw_data["reviews"]) == 5
    assert len(state.jina_insights) == 5000
    assert "maps_url" in state.lead_raw_data
    assert logs[-1][0].startswith("  Mapa: sem embed confiavel")


class TestEnsureKeywordResearch:
    """Test suite for ensure_keyword_research function."""

    def test_skips_when_keyword_research_already_exists(self):
        """Test that function skips when keyword_research is already populated."""
        state = SimpleNamespace(
            keyword_research={"palavras": ["seo", "marketing"]},
            lead_obj=SimpleNamespace(lead=SimpleNamespace(segmento="restaurante", cidade="SP")),
        )
        logs = []

        def _log(msg, tipo):
            logs.append((msg, tipo))

        ensure_keyword_research(state, _log)

        assert state.keyword_research == {"palavras": ["seo", "marketing"]}
        assert logs == []

    @patch("backend.endpoints.pipeline_phase_helpers.pesquisar_keywords_nicho")
    def test_populates_when_missing(self, mock_pesquisar):
        """Test that function populates keyword_research when missing."""
        mock_pesquisar.return_value = {"keywords": ["restaurante sao paulo", "delivery"]}

        state = SimpleNamespace(
            keyword_research=None,
            lead_obj=SimpleNamespace(lead=SimpleNamespace(segmento="restaurante", cidade="Sao Paulo")),
        )
        logs = []

        def _log(msg, tipo):
            logs.append((msg, tipo))

        ensure_keyword_research(state, _log)

        assert state.keyword_research == {"keywords": ["restaurante sao paulo", "delivery"]}
        assert any("Keywords: OK" in log[0] for log in logs if log[1] == "success")

    @patch("backend.endpoints.pipeline_phase_helpers.pesquisar_keywords_nicho")
    def test_logs_warning_on_error(self, mock_pesquisar):
        """Test that function logs warning when research fails."""
        mock_pesquisar.side_effect = Exception("Network error")

        state = SimpleNamespace(
            keyword_research=None,
            lead_obj=SimpleNamespace(lead=SimpleNamespace(segmento="academia", cidade="SP")),
        )
        warnings = []

        def _log(msg, tipo):
            pass

        def _warn(msg):
            warnings.append(msg)

        ensure_keyword_research(state, _log, _warn)

        assert any("erro" in w.lower() for w in warnings)


class TestEnsureJinaInsights:
    """Test suite for ensure_jina_insights function."""

    @patch("backend.endpoints.pipeline_phase_helpers.buscar_inteligencia_jina")
    @patch("backend.endpoints.pipeline_phase_helpers.formatar_inteligencia_para_arquiteto")
    def test_populates_jina_intel_when_successful(
        self, mock_format, mock_buscar
    ):
        """Test that function populates jina_insights on success."""
        mock_buscar.return_value = {
            "palavras_poder": ["saudavel", "nutricao"],
            "analise": "texto de analise",
        }
        mock_format.return_value = "Insights formatados para o arquiteto"

        state = SimpleNamespace(
            lead_nome="Nutri Vida",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(segmento="nutricionista", cidade="Sao Paulo")
            ),
            _concorrentes_urls=["http://example.com"],
            jina_intel_dict=None,
            jina_insights=None,
        )

        success_logs = []
        warnings = []

        def _log(msg, tipo):
            success_logs.append((msg, tipo))

        def _warn(msg):
            warnings.append(msg)

        def _fallback(segmento, cidade):
            return "Fallback insights"

        ensure_jina_insights(state, _log, _fallback, _warn)

        assert state.jina_insights == "Insights formatados para o arquiteto"
        assert state.jina_intel_dict == {
            "palavras_poder": ["saudavel", "nutricao"],
            "analise": "texto de analise",
        }
        assert any("Jina Intel:" in log[0] for log in success_logs if log[1] == "success")

    @patch("backend.endpoints.pipeline_phase_helpers.buscar_inteligencia_jina")
    def test_uses_fallback_when_jina_fails(self, mock_buscar):
        """Test that function uses fallback researcher when Jina fails."""
        mock_buscar.side_effect = Exception("Jina API error")

        state = SimpleNamespace(
            lead_nome="Restaurante Gourmet",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(segmento="restaurante", cidade="Rio de Janeiro")
            ),
            _concorrentes_urls=None,
            jina_intel_dict=None,
            jina_insights=None,
        )

        success_logs = []
        warnings = []

        def _log(msg, tipo):
            success_logs.append((msg, tipo))

        def _warn(msg):
            warnings.append(msg)

        def _fallback(segmento, cidade):
            return f"Fallback para {segmento} em {cidade}"

        ensure_jina_insights(state, _log, _fallback, _warn)

        assert state.jina_insights == f"Fallback para restaurante em Rio de Janeiro"
        assert any("Jina fallback" in log[0] for log in success_logs if log[1] == "warning")

    @patch("backend.endpoints.pipeline_phase_helpers.buscar_inteligencia_jina")
    def test_logs_warning_when_jina_fails(self, mock_buscar):
        """Test that function logs warning when Jina fails."""
        mock_buscar.side_effect = Exception("Network timeout")

        state = SimpleNamespace(
            lead_nome="Clinica Sao Paulo",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(segmento="clinica", cidade="Sao Paulo")
            ),
            _concorrentes_urls=None,
            jina_intel_dict=None,
            jina_insights=None,
        )

        warnings = []

        def _log(msg, tipo):
            pass

        def _warn(msg):
            warnings.append(msg)

        def _fallback(segmento, cidade):
            raise Exception("Fallback also fails")
            return ""

        ensure_jina_insights(state, _log, _fallback, _warn)

        # Should have logged at least one warning
        assert len(warnings) > 0
        assert any("Jina Intel erro" in w or "Jina" in w for w in warnings)

    @patch("backend.endpoints.pipeline_phase_helpers.buscar_inteligencia_jina")
    def test_sets_empty_string_when_everything_fails(self, mock_buscar):
        """Test that function sets empty string when both Jina and fallback fail."""
        mock_buscar.side_effect = Exception("Jina down")
        state = SimpleNamespace(
            lead_nome="Farmacia Central",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(segmento="farmacia", cidade="Curitiba")
            ),
            _concorrentes_urls=None,
            jina_intel_dict=None,
            jina_insights=None,
        )

        def _log(msg, tipo):
            pass

        def _warn(msg):
            pass

        def _fallback(segmento, cidade):
            raise Exception("Fallback down")

        ensure_jina_insights(state, _log, _fallback, _warn)

        assert state.jina_insights == ""
        assert state.jina_intel_dict == {}


class TestBuildPromptPhaseOutputs:
    """Test suite for build_prompt_phase_outputs function."""

    def test_sets_nicho_briefing_for_fast_path(self):
        """Test that fast path sets default NichoBriefing."""
        state = SimpleNamespace(
            pipeline_id="test-pipeline-123",
            nicho_briefing=None,
            variacao_estrutural=None,
            prd_arquiteto=None,
        )

        def _log(msg, tipo):
            pass

        def _warn(msg):
            pass

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="restaurante",
            cid="Sao Paulo",
            dark_mode=False,
            builder_fast_path=True,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=None,
            gerar_briefing=None,
            gerar_variacao=None,
            log_fn=_log,
            warning_fn=_warn,
        )

        assert state.nicho_briefing is not None
        assert state.nicho_briefing.source_agent == "pipeline"
        assert state.nicho_briefing.target_agent == "builder_renderer"

    def test_sets_variacao_estrutural_for_fast_path(self):
        """Test that fast path sets default VariacaoEstrutural."""
        state = SimpleNamespace(
            pipeline_id="test-pipeline-456",
            nicho_briefing=None,
            variacao_estrutural=None,
            prd_arquiteto=None,
        )

        def _log(msg, tipo):
            pass

        def _warn(msg):
            pass

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="nutricionista",
            cid="Rio de Janeiro",
            dark_mode=False,
            builder_fast_path=True,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=None,
            gerar_briefing=None,
            gerar_variacao=None,
            log_fn=_log,
            warning_fn=_warn,
        )

        assert state.variacao_estrutural is not None
        assert state.variacao_estrutural.template_estrutura == "skill-fast"

    @patch("backend.endpoints.pipeline_phase_helpers.gerar_briefing")
    def test_calls_gerar_briefing_when_missing(self, mock_gerar_briefing):
        """Test that function calls gerar_briefing when niche_briefing is missing."""
        mock_briefing = MagicMock()
        mock_briefing.nicho = "restaurante"
        mock_gerar_briefing.return_value = mock_briefing

        state = SimpleNamespace(
            pipeline_id="test-pipeline-789",
            lead_raw_data={"nome": "Restaurante Teste"},
            segmento="restaurante",
            nicho_briefing=None,
            variacao_estrutural=None,
            prd_arquiteto=None,
            jina_insights="Some insights",
        )

        def _log(msg, tipo):
            pass

        def _warn(msg):
            pass

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="restaurante",
            cid="Sao Paulo",
            dark_mode=False,
            builder_fast_path=False,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=MagicMock(return_value={"prompt": "master prd"}),
            gerar_briefing=mock_gerar_briefing,
            gerar_variacao=None,
            log_fn=_log,
            warning_fn=_warn,
        )

        mock_gerar_briefing.assert_called_once()
        assert state.nicho_briefing == mock_briefing

    @patch("backend.endpoints.pipeline_phase_helpers.gerar_variacao")
    def test_calls_gerar_variacao_when_missing(self, mock_gerar_var):
        """Test that function calls gerar_variacao when variacao_estrutural is missing."""
        mock_variacao = MagicMock()
        mock_variacao.template_estrutura = "corporate"
        mock_gerar_var.return_value = mock_variacao

        state = SimpleNamespace(
            pipeline_id="test-pipeline-abc",
            lead_raw_data={"nome": "Restaurante Teste"},
            nicho_briefing=MagicMock(),
            variacao_estrutural=None,
            prd_arquiteto=None,
            jina_insights="Insights",
        )

        def _log(msg, tipo):
            pass

        def _warn(msg):
            pass

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="restaurante",
            cid="Sao Paulo",
            dark_mode=False,
            builder_fast_path=False,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=MagicMock(return_value={"prompt": "master prd"}),
            gerar_briefing=MagicMock(),
            gerar_variacao=mock_gerar_var,
            log_fn=_log,
            warning_fn=_warn,
        )

        mock_gerar_var.assert_called_once()
        assert state.variacao_estrutural == mock_variacao

    def test_logs_warning_on_gerar_briefing_error(self):
        """Test that function logs warning when gerar_briefing fails."""
        state = SimpleNamespace(
            pipeline_id="test-pipeline-def",
            lead_raw_data={"nome": "Restaurante Teste"},
            nicho_briefing=None,
            variacao_estrutural=None,
            prd_arquiteto=None,
            jina_insights="Insights",
        )

        def _log(msg, tipo):
            pass

        warnings = []

        def _warn(msg):
            warnings.append(msg)

        def mock_failing_briefing(**kwargs):
            raise Exception("Briefing generation failed")

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="restaurante",
            cid="Sao Paulo",
            dark_mode=False,
            builder_fast_path=False,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=MagicMock(return_value={"prompt": "master prd"}),
            gerar_briefing=mock_failing_briefing,
            gerar_variacao=MagicMock(),
            log_fn=_log,
            warning_fn=_warn,
        )

        assert any("agente_nicho erro" in w for w in warnings)
        # Should have created fallback briefing
        assert state.nicho_briefing is not None

    def test_logs_warning_on_gerar_variacao_error(self):
        """Test that function logs warning when gerar_variacao fails."""
        state = SimpleNamespace(
            pipeline_id="test-pipeline-ghi",
            lead_raw_data={"nome": "Restaurante Teste"},
            nicho_briefing=MagicMock(),
            variacao_estrutural=None,
            prd_arquiteto=None,
            jina_insights="Insights",
        )

        def _log(msg, tipo):
            pass

        warnings = []

        def _warn(msg):
            warnings.append(msg)

        def mock_failing_variacao(**kwargs):
            raise Exception("Variacao generation failed")

        build_prompt_phase_outputs(
            state=state,
            tenant_id=1,
            seg="restaurante",
            cid="Sao Paulo",
            dark_mode=False,
            builder_fast_path=False,
            prompt_agent_flow=False,
            build_prompt_prd=None,
            build_skill_prd=None,
            build_master_prd=MagicMock(return_value={"prompt": "master prd"}),
            gerar_briefing=MagicMock(),
            gerar_variacao=mock_failing_variacao,
            log_fn=_log,
            warning_fn=_warn,
        )

        assert any("agente_variacao erro" in w for w in warnings)
        # Should have created fallback variacao
        assert state.variacao_estrutural is not None


class TestCurateLeadAssets:
    """Expanded test suite for curate_lead_assets function."""

    def test_trims_reviews_to_max_5(self):
        """Test that reviews are trimmed to maximum of 5."""
        state = SimpleNamespace(
            lead_nome="Teste",
            jina_insights="short",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(cidade="SP", endereco="", address="")
            ),
            lead_raw_data={
                "reviews": [{"texto": f"Review {i}"} for i in range(10)],
                "google_maps_embed": "",
            },
        )

        def _log(msg, tipo):
            pass

        curate_lead_assets(state, _log)

        assert len(state.lead_raw_data["reviews"]) == 5

    def test_trims_jina_insights_to_5000_chars(self):
        """Test that jina_insights is trimmed to 5000 characters."""
        state = SimpleNamespace(
            lead_nome="Teste",
            jina_insights="x" * 10000,
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(cidade="SP", endereco="", address="")
            ),
            lead_raw_data={"reviews": [], "google_maps_embed": ""},
        )

        def _log(msg, tipo):
            pass

        curate_lead_assets(state, _log)

        assert len(state.jina_insights) == 5000

    def test_keeps_reliable_embed(self):
        """Test that reliable embed (>50 chars) is kept."""
        state = SimpleNamespace(
            lead_nome="Teste",
            jina_insights="short",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(cidade="SP", endereco="", address="")
            ),
            lead_raw_data={
                "reviews": [],
                "google_maps_embed": "https://www.google.com/maps/embed?pb=longreliableembedcode",
            },
        )

        logs = []

        def _log(msg, tipo):
            logs.append((msg, tipo))

        curate_lead_assets(state, _log)

        assert "Mapa: embed confiavel mantido" in logs[-1][0]

    def test_generates_maps_url_when_no_embed(self):
        """Test that maps_url is generated when no reliable embed exists."""
        state = SimpleNamespace(
            lead_nome="Restaurante Central",
            jina_insights="short",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(
                    cidade="Sao Paulo",
                    endereco="Rua das Flores, 100",
                    address="",
                )
            ),
            lead_raw_data={"reviews": [], "google_maps_embed": ""},
        )

        def _log(msg, tipo):
            pass

        curate_lead_assets(state, _log)

        assert "maps_url" in state.lead_raw_data
        assert "Restaurante+Central" in state.lead_raw_data["maps_url"]
        assert "Sao+Paulo" in state.lead_raw_data["maps_url"]

    def test_prioritizes_endereco_over_address(self):
        """Test that endereco is used over address field."""
        state = SimpleNamespace(
            lead_nome="Farmacia Sao Jose",
            jina_insights="short",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(
                    cidade="Belo Horizonte",
                    endereco="Av. Principal, 500",
                    address="Rua Secundaria, 200",
                )
            ),
            lead_raw_data={"reviews": [], "google_maps_embed": ""},
        )

        def _log(msg, tipo):
            pass

        curate_lead_assets(state, _log)

        assert "Av.+Principal" in state.lead_raw_data["maps_url"]

    def test_handles_missing_address_fields(self):
        """Test that function handles missing address fields gracefully."""
        state = SimpleNamespace(
            lead_nome="Clinica",
            jina_insights="short",
            lead_obj=SimpleNamespace(
                lead=SimpleNamespace(cidade="Curitiba", endereco=None, address=None)
            ),
            lead_raw_data={"reviews": [], "google_maps_embed": ""},
        )

        def _log(msg, tipo):
            pass

        curate_lead_assets(state, _log)

        # Should still work, just without address
        assert "maps_url" in state.lead_raw_data
        assert "Clinica" in state.lead_raw_data["maps_url"]
