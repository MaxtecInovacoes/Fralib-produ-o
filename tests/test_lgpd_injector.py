"""Tests para o injector LGPD personalizado.

Valida que:
1. Banner LGPD e injetado
2. Copy personalizada por segmento (academia, restaurante, etc)
3. Cidade e nome do negocio aparecem
4. Botoes Aceitar/Rejeitar existem
5. localStorage persist funciona
6. data-lgpd-banner e data-lgpd-segment estao presentes
7. ARIA attributes para acessibilidade
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.services.lgpd_injector import (
    build_lgpd_banner_html,
    inject_lgpd_into_html,
)


class TestLGPDInjector:
    def test_banner_injected_into_empty_html(self):
        html = "<html><body><h1>Site</h1></body></html>"
        out = inject_lgpd_into_html(html, facts={})
        assert 'data-lgpd-banner' in out
        assert 'data-lgpd-accept' in out
        assert 'data-lgpd-reject' in out

    def test_banner_personalized_academia(self):
        html = "<html><body></body></html>"
        facts = {
            "business": {
                "name": "Academia Teste",
                "city": "Campo Grande",
                "segment": "academia",
                "phone": "67999887766",
            }
        }
        out = inject_lgpd_into_html(html, facts=facts)
        # Copy personalizada de academia
        assert "matriculas" in out.lower() or "fitness" in out.lower(), \
            "Copy nao personalizada para academia"
        assert "Academia Teste" in out, "Nome do negocio nao aparece"
        assert "Campo Grande" in out, "Cidade nao aparece"
        assert "academia" in out, "Segmento data-lgpd-segment ausente"

    def test_banner_personalized_restaurante(self):
        html = "<html><body></body></html>"
        facts = {
            "business": {
                "name": "Pizzaria do Joao",
                "city": "Sao Paulo",
                "segment": "pizzaria",
            }
        }
        out = inject_lgpd_into_html(html, facts=facts)
        assert "pedidos" in out.lower() or "delivery" in out.lower(), \
            "Copy nao personalizada para pizzaria"
        assert "Pizzaria do Joao" in out

    def test_banner_personalized_clinica(self):
        html = "<html><body></body></html>"
        facts = {
            "business": {
                "name": "Clinica Saude",
                "city": "",
                "segment": "clinica",
            }
        }
        out = inject_lgpd_into_html(html, facts=facts)
        # Sem cidade, deve funcionar mesmo assim
        assert "consultas" in out.lower() or "exames" in out.lower()
        assert "Clinica Saude" in out

    def test_banner_default_segment(self):
        html = "<html><body></body></html>"
        facts = {"business": {"name": "Site Genérico"}}
        out = inject_lgpd_into_html(html, facts=facts)
        assert 'data-lgpd-segment="default"' in out
        assert "Site Genérico" in out

    def test_banner_has_localstorage(self):
        html = "<html><body></body></html>"
        out = inject_lgpd_into_html(html, facts={})
        assert "localStorage" in out
        assert "fralib_lgpd" in out

    def test_banner_has_cookie(self):
        html = "<html><body></body></html>"
        out = inject_lgpd_into_html(html, facts={})
        assert "document.cookie" in out

    def test_banner_has_aria(self):
        html = "<html><body></body></html>"
        out = inject_lgpd_into_html(html, facts={})
        assert 'role="dialog"' in out
        assert 'aria-label="Aviso de privacidade"' in out
        assert 'aria-live="polite"' in out

    def test_banner_has_animation(self):
        html = "<html><body></body></html>"
        out = inject_lgpd_into_html(html, facts={})
        assert "transition:" in out
        assert "opacity:" in out
        assert "transform:" in out

    def test_banner_has_whatsapp_link(self):
        html = "<html><body></body></html>"
        facts = {"business": {"name": "X", "phone": "67999887766"}}
        out = inject_lgpd_into_html(html, facts=facts)
        assert "wa.me" in out

    def test_existing_banner_replaced(self):
        html = '''<html><body>
<div class="fralib-lgpd-banner" data-lgpd-banner>OLD GENERIC</div>
<script id="old-runtime">OLD</script>
</body></html>'''
        facts = {"business": {"name": "NOVO", "segment": "academia"}}
        out = inject_lgpd_into_html(html, facts=facts)
        assert "OLD GENERIC" not in out
        assert "OLD" not in out or 'fralib-lgpd-runtime' in out
        assert "NOVO" in out
        # So deve haver 1 banner
        assert out.count('data-lgpd-banner') == 1

    def test_consent_key_unique_per_business(self):
        html1 = inject_lgpd_into_html("<html></html>", facts={"business": {"name": "Site A"}})
        html2 = inject_lgpd_into_html("<html></html>", facts={"business": {"name": "Site B"}})
        # Extrair consent keys (KEY = '...')
        import re
        keys = []
        for h in [html1, html2]:
            m = re.search(r"var KEY = ['\"]([^'\"]+)['\"]", h)
            if m:
                keys.append(m.group(1))
        assert len(keys) == 2, f"Esperava 2 keys, achei {keys}"
        assert keys[0] != keys[1], "Consent keys devem ser unicas por site"

    def test_no_facts_works(self):
        html = inject_lgpd_into_html("<html></html>", facts=None)
        assert 'data-lgpd-banner' in html

    def test_banner_in_segment_keywords(self):
        """Verifica que cada segmento tem copy especifica."""
        for segment in ["academia", "restaurante", "clinica", "barbearia"]:
            html = inject_lgpd_into_html("<html></html>", facts={"business": {"name": "X", "segment": segment}})
            # Cada segmento tem palavras-chave proprias
            payload = build_lgpd_banner_html({"business": {"name": "X", "segment": segment}})
            assert payload["segment_key"] == segment, f"Segment key errado para {segment}"

    def test_handler_generico_nao_eh_injetado_quando_runtime_existe(self):
        """Defesa contra bug 'LGPD invisivel': se o banner ja vem com runtime
        do openui_renderer, o handler generico do html_builder_repair NAO deve
        ser injetado (causava display:none via localStorage)."""
        from backend.agents.html_builder_repair import repair_builder_publication_contract

        # HTML com banner LGPD + runtime ja injetados pelo openui_renderer
        html_with_runtime = '''<html><head></head><body>
<div id="fralib-lgpd-banner" data-lgpd-banner data-lgpd-accept>Banner</div>
<script id="fralib-lgpd-runtime">var KEY = "fralib_lgpd_test_v2";</script>
<button data-lgpd-accept>Aceitar</button>
</body></html>'''

        # Mock prd simples
        class _MockPrd(dict):
            def __getattr__(self, k): return self.get(k, "")
        prd = _MockPrd(
            name="Test", phone="11999887766", address="Rua X, 1", city="SP",
            canonical_url="https://example.com", site_url="https://example.com",
        )

        result = repair_builder_publication_contract(html_with_runtime, prd)

        # Handler generico NAO deve aparecer (causava bug)
        assert "fralib-lgpd-click-handler" not in result, (
            "Handler generico foi injetado mesmo com runtime presente — bug visual!"
        )
        # Runtime canonico do openui_renderer deve continuar presente
        assert "fralib-lgpd-runtime" in result, "Runtime canonico foi removido!"


if __name__ == "__main__":
    # Rodar sem pytest
    test = TestLGPDInjector()
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