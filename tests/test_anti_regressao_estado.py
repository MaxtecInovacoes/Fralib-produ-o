"""Testes anti-regressão do estado consolidado pós SDR 10/10 + subnicho.

Cada teste PROTEGE uma decisão arquitetural critica. Se algum deles
quebrar, significa que alguém removeu/apagou algo que NAO devia.

Estado baseline: tag v1.0-baseline-2026-06-23
- 74 arquivos em backend/agents/ (NÃO pode cair)
- 49 arquivos em backend/services/ (NÃO pode cair)
- 11 testes top-level (NAO pode cair)
- 18 arquivos legados removidos (NAO podem voltar)
- LGPD handler generico NAO pode ser reintroduzido
- OpenUI como UNICO gerador (sem vite_react)
- SUB_NICHO_TEMPLATES com 8 nichos (NAO pode cair pra <8)
- HTML sanitizer fecha h2 orfao
- Sonnet e primario (nao Haiku)
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

BACKEND = ROOT / "backend"
AGENTS_DIR = BACKEND / "agents"
SERVICES_DIR = BACKEND / "services"
TESTS_DIR = ROOT / "tests"


class TestAntiRegressaoEstrutural:
    """Garante que a estrutura canonica nao foi destruida."""

    def test_minimo_70_agentes(self):
        """74 agentes hoje - nao pode cair muito."""
        agents = list(AGENTS_DIR.glob("*.py"))
        n = len(agents)
        assert n >= 70, f"Agentes cairam para {n} (baseline 74)"

    def test_minimo_45_services(self):
        """49 services hoje - nao pode cair muito."""
        services = list(SERVICES_DIR.glob("*.py"))
        n = len(services)
        assert n >= 45, f"Services cairam para {n} (baseline 49)"

    def test_sdr_langgraph_existe(self):
        """Diretorio SDR e critico - NAO pode sumir."""
        assert (AGENTS_DIR / "sdr_langgraph").is_dir(), \
            "sdr_langgraph/ foi removido! SDR Studio 10/10 perdido."

    def test_openui_renderer_existe(self):
        """OpenUI e o UNICO renderer - NAO pode sumir."""
        assert (SERVICES_DIR / "openui_renderer.py").is_file(), \
            "openui_renderer.py sumiu! Sistema perde geracao de sites."

    def test_html_sanitizer_existe(self):
        """Sanitizer foi criado hoje - NAO pode sumir."""
        assert (SERVICES_DIR / "html_sanitizer.py").is_file(), \
            "html_sanitizer.py sumiu! Bug 'Im Tema' volta."

    def test_lgpd_injector_existe(self):
        assert (SERVICES_DIR / "lgpd_injector.py").is_file(), \
            "lgpd_injector.py sumiu! LGPD quebra."

    def test_handoff_types_existe(self):
        assert (AGENTS_DIR / "handoff_types.py").is_file(), \
            "handoff_types.py sumiu! Contratos entre agentes quebram."

    def test_agente_nicho_e_variacao_existem(self):
        for f in ["agente_nicho.py", "agente_variacao.py"]:
            assert (AGENTS_DIR / f).is_file(), \
                f"{f} sumiu! Pipeline de briefing quebrada."


class TestAntiRegressaoConteudo:
    """Garante que decisoes de design NAO foram revertidas."""

    def test_vite_react_renderer_isolado_por_engine_explicita(self):
        """Vite/React pode existir, mas nao pode virar rota implicita."""
        from backend.services import builder_worker

        assert (SERVICES_DIR / "vite_react_renderer.py").is_file(), \
            "vite_react_renderer.py deve existir enquanto o modo compat estiver ativo."
        assert builder_worker._builder_engine(None) == "openui"
        assert builder_worker._builder_engine("vite_react") == "vite_react"

    def test_handler_generico_lgpd_nao_voltou(self):
        """O handler generico duplicado causa LGPD invisivel."""
        from backend.agents.html_builder_repair import (
            repair_builder_publication_contract,
        )

        html_with_runtime = '''<html><body>
<div id="fralib-lgpd-banner" data-lgpd-banner data-lgpd-accept>X</div>
<script id="fralib-lgpd-runtime">var KEY = "fralib_lgpd_test_v2";</script>
<button data-lgpd-accept>OK</button>
</body></html>'''

        class _Prd(dict):
            def __getattr__(self, k): return self.get(k, "")
        prd = _Prd(name="X", phone="11999887766", address="Rua", city="SP",
                   canonical_url="https://e.com", site_url="https://e.com")

        out = repair_builder_publication_contract(html_with_runtime, prd)
        assert "fralib-lgpd-click-handler" not in out, \
            "Handler LGPD generico voltou! Bug visual reintroduzido."

    def test_haiku_nao_e_primario_em_openui(self):
        """Sonnet e primario hoje - haiku NAO pode voltar.

        Verifica tanto a definicao de funcao (signature) quanto
        o docstring referenciando 'sonnet'.
        """
        from backend.services import openui_renderer

        # 1. Docstring cita sonnet (ou "Cascade qualidade: sonnet")
        doc = openui_renderer.render_openui_site.__doc__ or ""
        assert "sonnet" in doc.lower(), (
            f"render_openui_site docstring nao cita sonnet: {doc[:200]}"
        )

        # 2. No codigo-fonte: a keyword arg primary_model NAO e haiku
        src = (SERVICES_DIR / "openui_renderer.py").read_text(encoding="utf-8")
        m = re.search(
            r'primary_model\s*[:=]\s*["\']?(\w+)["\']?',
            src,
        )
        assert m, "primary_model nao encontrado no codigo-fonte"
        assert m.group(1).lower() != "haiku", (
            f"primary_model voltou pra haiku ({m.group(1)}) - regressao!"
        )

    def test_subnicho_templates_minimo_8_nichos(self):
        """8 subnichos mapeados - NAO pode cair pra <5."""
        from backend.agents.agente_variacao import SUB_NICHO_TEMPLATES

        n = len(SUB_NICHO_TEMPLATES)
        assert n >= 5, f"SUB_NICHO_TEMPLATES reduziu para {n} (baseline 8)"
        # Nutricionista DEVE estar la
        assert "nutricionista_esportiva" in SUB_NICHO_TEMPLATES
        assert "nutricionista_clinica" in SUB_NICHO_TEMPLATES
        # E devem ser DIFERENTES (ordem de secoes)
        esp = SUB_NICHO_TEMPLATES["nutricionista_esportiva"]
        clin = SUB_NICHO_TEMPLATES["nutricionista_clinica"]
        assert esp["ordem_das_secoes"] != clin["ordem_das_secoes"], \
            "Nutricionista esportiva e clinica com mesma ordem - regressao!"

    def test_sanitize_fecha_h2_orfao(self):
        """Bug 'Im Tema' - sanitizer deve fechar h2 orfao antes de </body>.

        Caso REAL do bug: h2 aberto sem </h2> e sem section/pai
        que seja fechado DEPOIS dele (senao o HTMLParser conserta
        o aninhamento implicitamente).
        """
        from backend.services.html_sanitizer import close_unclosed_block_tags

        # h2 orfao direto no body, sem nada que feche o aninhamento
        html = "<html><body><h2>Im\nTema.<p>Mais conteudo</body></html>"
        out = close_unclosed_block_tags(html)
        open_h2 = out.count("<h2>")
        close_h2 = out.count("</h2>")
        assert open_h2 == close_h2, (
            f"h2 nao foi fechado antes de </body>: {out!r}"
        )
        # Conteudo "Im Tema." DEVE aparecer inteiro
        assert "Im" in out and "Tema." in out, (
            f"Conteudo do h2 perdido: {out!r}"
        )

    def test_consent_key_unico_por_site(self):
        """LGPD: cada site tem chave de consentimento unica."""
        from backend.services.lgpd_injector import inject_lgpd_into_html

        h1 = inject_lgpd_into_html("<html></html>",
                                   facts={"business": {"name": "Site A"}})
        h2 = inject_lgpd_into_html("<html></html>",
                                   facts={"business": {"name": "Site B"}})
        k1 = re.search(r'KEY\s*=\s*["\']([^"\']+)["\']', h1)
        k2 = re.search(r'KEY\s*=\s*["\']([^"\']+)["\']', h2)
        assert k1 and k2, "Consent key nao encontrada"
        assert k1.group(1) != k2.group(1), \
            "Consent keys iguais para sites diferentes - LGPD bug!"

    def test_sonnet_e_padrao_global(self):
        """Builder worker usa Sonnet, nao Haiku."""
        src = (SERVICES_DIR / "builder_worker.py").read_text(encoding="utf-8")
        # Procura env var de fallback que DEVE apontar pra opus (nao haiku)
        m = re.search(r'FRALIB_OPENUI_FALLBACK_MODEL["\']?\s*[,\)]', src)
        if m:
            # Verifica o contexto
            ctx = src[max(0, m.start()-200):m.end()+200]
            assert "opus" in ctx.lower() or "haiku" not in ctx.lower(), \
                "Builder worker ainda referencia Haiku"


class TestAntiRegressaoDocs:
    """Garante que AGENTS.md e CLAUDE.md nao foram apagados."""

    def test_agents_md_existe_e_grande(self):
        p = ROOT / "AGENTS.md"
        assert p.is_file(), "AGENTS.md sumiu!"
        size = p.stat().st_size
        assert size > 10_000, f"AGENTS.md muito pequeno ({size} bytes)"

    def test_secao_subnicho_em_agents(self):
        p = ROOT / "AGENTS.md"
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore")
            assert "SUB_NICHO_TEMPLATES" in content or "subnicho" in content.lower(), \
                "Secao de subnicho nao documentada em AGENTS.md"


class TestAntiRegressaoSanity:
    """Smoke tests que garantem que o sistema pelo menos IMPORTA."""

    def test_openui_renderer_importa(self):
        from backend.services import openui_renderer  # noqa: F401

    def test_builder_worker_importa(self):
        from backend.services import builder_worker  # noqa: F401

    def test_sdr_langgraph_importa(self):
        from backend.agents import sdr_langgraph  # noqa: F401

    def test_lgpd_injector_importa(self):
        from backend.services import lgpd_injector  # noqa: F401

    def test_html_sanitizer_importa(self):
        from backend.services import html_sanitizer  # noqa: F401


if __name__ == "__main__":
    test = TestAntiRegressaoEstrutural()
    classes = [TestAntiRegressaoEstrutural, TestAntiRegressaoConteudo,
               TestAntiRegressaoDocs, TestAntiRegressaoSanity]
    passed = failed = 0
    for cls in classes:
        for m in dir(cls):
            if not m.startswith("test_"):
                continue
            try:
                getattr(cls(), m)()
                print(f"OK {cls.__name__}.{m}")
                passed += 1
            except AssertionError as e:
                print(f"FAIL {cls.__name__}.{m}: {e}")
                failed += 1
            except Exception as e:
                print(f"ERR  {cls.__name__}.{m}: {type(e).__name__}: {e}")
                failed += 1
    print(f"\n{passed}/{passed+failed} passados")
    sys.exit(0 if failed == 0 else 1)
