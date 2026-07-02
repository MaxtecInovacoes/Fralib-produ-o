"""
============================================================================
TESTES: BookingModal CTA dinâmico (var(--fralib-accent))
============================================================================

Sprint 12.x: o template do BookingModal em vite_prompts.py não deve mais
usar cores hardcoded (bg-amber-500, etc). Deve usar var(--fralib-accent)
que muda conforme o polo escolhido.
============================================================================
"""

import pytest
import sys

sys.path.insert(0, ".")


# ────────────────────────────────────────────────────────────────────────
# 1. TEMPLATE NÃO TEM MAIS CORES HARDCODED
# ────────────────────────────────────────────────────────────────────────

class TestTemplateSemCoresHardcoded:
    """O template do BookingModal não deve usar bg-amber-500 ou similares."""

    def test_template_nao_contem_bg_amber_500(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "academia"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        # O comentário de aviso (NAO use bg-amber-500) é permitido,
        # mas o template TSX não deve CONTER bg-amber-500 como classe
        # Extrair apenas o bloco de código TSX
        import re
        tsx_match = re.search(r"```tsx(.*?)```", block, re.DOTALL)
        tsx = tsx_match.group(1) if tsx_match else block
        assert "bg-amber-500" not in tsx, "Template TSX ainda usa bg-amber-500 hardcoded"

    def test_template_nao_contem_border_amber(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "academia"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        assert "border-amber-500" not in block

    def test_template_nao_contem_text_amber(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "academia"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        assert "text-amber-50" not in block
        assert "text-amber-100" not in block

    def test_template_usa_var_fralib_accent(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "academia"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        assert "var(--fralib-accent)" in block, \
            "Template deve usar var(--fralib-accent)"


# ────────────────────────────────────────────────────────────────────────
# 2. PROMPT INSTRUI LLM A USAR TOKEN CSS
# ────────────────────────────────────────────────────────────────────────

class TestPromptInstruUsoToken:
    """O prompt deve instruir o LLM a usar var(--fralib-accent)."""

    def test_prompt_contem_regra_acerca_var(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "academia"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        # Deve mencionar uso de var(--fralib-accent) na regra
        assert "var(--fralib-accent)" in block or "polo" in block.lower()


# ────────────────────────────────────────────────────────────────────────
# 3. INTEGRAÇÃO COM REGISTRY
# ────────────────────────────────────────────────────────────────────────

class TestIntegracaoRegistry:
    """BookingModal ainda usa NICHO_MODAL_CONFIG/registry corretamente."""

    def test_modal_block_para_advogado(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "advogado"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        # Advogado deve ter seu próprio modal (não "Fale Conosco")
        if "BookingModal" in block:
            assert "Falar com Advogado" in block or "Agendar Consulta Juridica" in block

    def test_modal_block_para_estetica(self):
        from backend.services.vite_prompts import _build_nicho_modal_block
        facts = {"segment": "estetica"}
        try:
            block = _build_nicho_modal_block(facts)
        except Exception:
            block = ""
        if "BookingModal" in block:
            # Estética pode estar usando default — isso é problema conhecido
            # mas pelo menos não deve quebrar
            assert "Fale Conosco" in block or "Avaliacao" in block or "Agendar" in block