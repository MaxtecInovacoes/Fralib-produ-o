"""Tests para SUB_NICHO_TEMPLATES e detect_subniche.

Garante que subnichos mapeados retornam templates canonicos diferentes
(ex: nutricionista_esportiva != nutricionista_clinica) e que o
agente_variacao usa o mapping quando o subnicho esta presente.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.agents.agente_variacao import (
    SUB_NICHO_TEMPLATES,
    detect_subniche,
    _get_subnicho_template,
)
from backend.agents.handoff_types import NichoBriefing, VariacaoEstrutural


class TestDetectSubniche:
    def test_nutricionista_esportiva_detected(self):
        assert detect_subniche("nutricionista", ["nutricao esportiva"]) == "nutricionista_esportiva"
        assert detect_subniche("Nutricionista Esportiva") == "nutricionista_esportiva"
        assert detect_subniche("nutricionista", ["atendimento para atletas"]) == "nutricionista_esportiva"

    def test_nutricionista_clinica_detected(self):
        assert detect_subniche("nutricionista", ["reeducacao alimentar"]) == "nutricionista_clinica"
        assert detect_subniche("nutricionista", ["emagrecimento saudavel"]) == "nutricionista_clinica"
        assert detect_subniche("nutricionista clinica") == "nutricionista_clinica"

    def test_clinica_estetica_detected(self):
        assert detect_subniche("clinica", ["botox", "preenchimento"]) == "clinica_estetica"
        assert detect_subniche("clinica estetica") == "clinica_estetica"

    def test_barbearia_premium_detected(self):
        assert detect_subniche("barbearia", ["corte masculino"]) == "barbearia_premium"
        assert detect_subniche("barbearia premium") == "barbearia_premium"

    def test_academia_crossfit_detected(self):
        assert detect_subniche("academia", ["crossfit", "box"]) == "academia_crossfit"

    def test_default_for_unknown(self):
        assert detect_subniche("pet_shop_legal") == "default"
        assert detect_subniche("") == "default"

    def test_attributes_used_as_fallback(self):
        assert detect_subniche("loja", atributos=["vende crossfit box"]) == "academia_crossfit"


class TestSubNichoTemplates:
    def test_nutricionista_esportiva_uses_organic(self):
        t = SUB_NICHO_TEMPLATES["nutricionista_esportiva"]
        assert t["template_estrutura"] == "organic"
        assert "numeros" in t["ordem_das_secoes"]
        assert "abordagem" in t["ordem_das_secoes"]

    def test_nutricionista_clinica_uses_editorial(self):
        t = SUB_NICHO_TEMPLATES["nutricionista_clinica"]
        assert t["template_estrutura"] == "editorial"
        assert "sobre" in t["ordem_das_secoes"]
        assert "processo" in t["ordem_das_secoes"]

    def test_nutricionista_esportiva_diferente_de_clinica(self):
        esport = SUB_NICHO_TEMPLATES["nutricionista_esportiva"]
        clin = SUB_NICHO_TEMPLATES["nutricionista_clinica"]
        # Devem ter ordens DIFERENTES (chave do anti-clone)
        assert esport["ordem_das_secoes"] != clin["ordem_das_secoes"]
        assert esport["template_estrutura"] != clin["template_estrutura"]
        assert esport["template_hero"] != clin["template_hero"]

    def test_todos_subnichos_terminam_em_footer(self):
        for subnicho, t in SUB_NICHO_TEMPLATES.items():
            assert "footer" in t["ordem_das_secoes"], f"{subnicho} sem footer"
            assert t["ordem_das_secoes"][0] == "hero", f"{subnicho} deve comecar com hero"
            assert "contato" in t["ordem_das_secoes"], f"{subnicho} sem contato"

    def test_todos_subnichos_minimo_5_secoes(self):
        for subnicho, t in SUB_NICHO_TEMPLATES.items():
            assert len(t["ordem_das_secoes"]) >= 5, f"{subnicho} tem menos de 5 secoes"

    def test_todos_subnichos_tem_angulo(self):
        for subnicho, t in SUB_NICHO_TEMPLATES.items():
            assert t.get("angulo_de_comunicacao"), f"{subnicho} sem angulo"


class TestGerarVariacaoUsesTemplate:
    def test_uses_canonical_template_without_llm_when_mapped(self):
        from backend.agents.agente_variacao import gerar_variacao

        briefing = NichoBriefing(
            task_id="t1",
            source_agent="agente_nicho",
            target_agent="agente_variacao",
            status="ok",
            task_summary="",
            nicho="nutricionista",
            subnichos=["esportiva"],
            subnicho="nutricionista_esportiva",
            cidade="Sao Paulo",
        )
        # Nao chama LLM — usa o template canonico
        result = gerar_variacao(briefing)
        assert result.subnicho == "nutricionista_esportiva"
        assert result.template_estrutura == "organic"
        assert "numeros" in result.ordem_das_secoes
        # Nao deve ter saido do default
        assert result.angulo_de_comunicacao != SUB_NICHO_TEMPLATES["default"]["angulo_de_comunicacao"]

    def test_falls_back_to_default_when_unknown(self):
        from backend.agents.agente_variacao import gerar_variacao

        briefing = NichoBriefing(
            task_id="t2",
            source_agent="agente_nicho",
            target_agent="agente_variacao",
            status="ok",
            task_summary="",
            nicho="pet_shop_exotico",
            subnicho="",  # nao mapeado
            cidade="Curitiba",
        )
        # Cai no fallback LLM (Sonnet) — so testamos que nao quebra
        # Se nao houver LLM configurado, ainda retorna o default
        try:
            result = gerar_variacao(briefing)
        except Exception as e:
            # Aceitavel: pode falhar se LLM nao disponivel em ambiente de teste
            assert "llm" in str(e).lower() or "api" in str(e).lower() or "anthropic" in str(e).lower()
            return
        # Se chegou aqui, o LLM respondeu
        assert result.subnicho != ""
        assert len(result.ordem_das_secoes) >= 5


class TestVariacaoEstruturalSubnichoField:
    def test_variacao_has_subnicho_field(self):
        v = VariacaoEstrutural(
            task_id="t",
            source_agent="agente_variacao",
            target_agent="arquiteto_mestre",
            status="ok",
            task_summary="",
        )
        assert hasattr(v, "subnicho")
        assert v.subnicho == ""

    def test_nicho_briefing_has_subnicho_field(self):
        b = NichoBriefing(
            task_id="t",
            source_agent="agente_nicho",
            target_agent="agente_variacao",
            status="ok",
            task_summary="",
        )
        assert hasattr(b, "subnicho")
        assert hasattr(b, "subnichos")
        assert b.subnicho == ""


class TestGetSubnichoTemplate:
    def test_returns_mapped_template(self):
        t = _get_subnicho_template("clinica_estetica")
        assert t["template_estrutura"] == "minimal"
        assert "procedimentos" in t["ordem_das_secoes"]

    def test_returns_default_for_unknown(self):
        t = _get_subnicho_template("subnicho_inexistente")
        default = SUB_NICHO_TEMPLATES["default"]
        assert t == default


if __name__ == "__main__":
    test = TestDetectSubniche()
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
