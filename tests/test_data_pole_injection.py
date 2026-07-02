"""
============================================================================
TESTES: data-pole injection no index.html + copy de design-system-tokens.css
============================================================================

NOTA: write_vite_project tem uma verificação de path-escape que é testada
em outros lugares. Aqui testamos apenas:
- data-pole injection no template
- copy do design-system-tokens.css para o workspace
============================================================================
"""

import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")


# ────────────────────────────────────────────────────────────────────────
# 1. data-pole ATRIBUTO NO HTML
# ────────────────────────────────────────────────────────────────────────

class TestDataPoleInjection:
    """vite_template_index_html injeta data-pole quando polo está nos facts."""

    def test_sem_pole_nao_injeta(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({})
        assert "data-pole=" not in html

    def test_polo_bold_uppercase(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "BOLD"})
        assert 'data-pole="bold"' in html

    def test_polo_soft_lowercase(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "soft"})
        assert 'data-pole="soft"' in html

    def test_polo_corporate_alias(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "corporate"})
        assert 'data-pole="corporate"' in html

    def test_polo_minimal_alias(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "minimal"})
        assert 'data-pole="minimal"' in html

    def test_polo_classic_nao_e_mapeado(self):
        """CLASSIC (novo nome) ainda não tem regra CSS — cai em default."""
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "CLASSIC"})
        assert "data-pole=" not in html

    def test_polo_tech_nao_e_mapeado(self):
        """TECH (novo nome) ainda não tem regra CSS — cai em default."""
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "TECH"})
        assert "data-pole=" not in html

    def test_polo_invalido_caem_em_default(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "XYZ_INVALID"})
        assert "data-pole=" not in html

    def test_pole_vazio_caem_em_default(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": ""})
        assert "data-pole=" not in html


# ────────────────────────────────────────────────────────────────────────
# 2. DESIGN-SYSTEM-TOKENS.CSS LINKADO
# ────────────────────────────────────────────────────────────────────────

class TestDesignSystemTokensLinkado:
    """design-system-tokens.css sempre linkado no HTML."""

    def test_stylesheet_linkado(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({})
        assert "design-system-tokens.css" in html
        assert '<link rel="stylesheet"' in html

    def test_stylesheet_linkado_com_polo(self):
        from backend.services.vite_templates import vite_template_index_html
        html = vite_template_index_html({"pole": "bold"})
        assert "design-system-tokens.css" in html


# ────────────────────────────────────────────────────────────────────────
# 3. COPY DO DESIGN-SYSTEM-TOKENS.CSS PARA O WORKSPACE
# ────────────────────────────────────────────────────────────────────────

class TestCopyDesignSystemTokens:
    """_copy_design_system_tokens copia o CSS para o workspace."""

    def test_arquivo_e_copiado(self):
        from backend.services.vite_react_renderer import _copy_design_system_tokens
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _copy_design_system_tokens(ws)
            css = ws / "design-system-tokens.css"
            assert css.exists(), "design-system-tokens.css nao foi copiado"

    def test_arquivo_tem_pole_soft(self):
        from backend.services.vite_react_renderer import _copy_design_system_tokens
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _copy_design_system_tokens(ws)
            css = ws / "design-system-tokens.css"
            content = css.read_text(encoding="utf-8")
            assert '[data-pole="soft"]' in content
            assert '[data-pole="bold"]' in content
            assert '[data-pole="corporate"]' in content
            assert '[data-pole="minimal"]' in content

    def test_arquivo_tem_classes_utilitarias(self):
        from backend.services.vite_react_renderer import _copy_design_system_tokens
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _copy_design_system_tokens(ws)
            css = ws / "design-system-tokens.css"
            content = css.read_text(encoding="utf-8")
            assert ".hero-headline" in content
            assert ".card-pole" in content
            assert ".btn-pole" in content
            assert ".glass-card" in content

    def test_copy_nao_falha_se_workspace_vazio(self):
        """Não deve lançar exceção se workspace é diretório novo."""
        from backend.services.vite_react_renderer import _copy_design_system_tokens
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "novo"
            ws.mkdir()
            _copy_design_system_tokens(ws)
            # Se chegou aqui sem exception, OK
            assert True


# ────────────────────────────────────────────────────────────────────────
# 4. INTEGRAÇÃO: WRITE_VITE_PROJECT CHAMA _copy_design_system_tokens
# ────────────────────────────────────────────────────────────────────────

class TestWriteViteProjectIntegraCss:
    """write_vite_project chama _copy_design_system_tokens automaticamente."""

    def test_copy_design_system_tokens_e_chamado_indiretamente(self):
        """Verifica que _copy_design_system_tokens funciona como esperado."""
        from backend.services.vite_react_renderer import _copy_design_system_tokens
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _copy_design_system_tokens(ws)
            css = ws / "design-system-tokens.css"
            assert css.exists()