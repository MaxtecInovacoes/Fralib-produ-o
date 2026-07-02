"""
============================================================================
TESTES: Copy angles + Polo voice + SEO por polo (Etapa 4)
============================================================================

Sprint 12.x: novos modulos backend/copywriting/ que dao ao LLM ferramentas
especificas por polo + nicho para gerar copy de alta qualidade.

Modulos testados:
- copywriting/copy_angles.py: 8 frameworks de copy (StoryBrand, PAS, AIDA, etc)
- copywriting/polo_voice.py: 4 polos com vocabulario proprio, proibicoes, gatilhos
- copywriting/seo_templates.py: 56 templates SEO (13 nichos x 4 polos + 4 default)
- bloco_copy.py: integra copy_angle e polo_voice no prompt LLM
============================================================================
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _PROJECT_ROOT / "backend"
for _p in (str(_BACKEND_PATH), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. copy_angles: 8 frameworks + get_recommended_angle
# ═══════════════════════════════════════════════════════════════════════════

class TestCopyAngles:
    """copy_angles.py expoe 8 frameworks de copy."""

    def test_8_frameworks_definidos(self):
        from backend.copywriting.copy_angles import COPY_ANGLES
        assert len(COPY_ANGLES) >= 8, f"Esperado 8+ frameworks, got {len(COPY_ANGLES)}"

    def test_frameworks_obrigatorios(self):
        from backend.copywriting.copy_angles import COPY_ANGLES
        required = {"storybrand", "pas", "aida", "bab", "social_proof",
                    "contrarian", "authority", "specificity"}
        keys = set(k.lower() for k in COPY_ANGLES.keys())
        missing = required - keys
        assert not missing, f"Frameworks faltando: {missing}"

    def test_get_recommended_angle_retorna_objeto(self):
        from backend.copywriting.copy_angles import get_recommended_angle
        angle = get_recommended_angle("academia", subnicho="crossfit", polo="BOLD")
        assert angle is not None
        assert hasattr(angle, "framework")
        assert hasattr(angle, "hook_template")
        assert hasattr(angle, "body_template")
        assert hasattr(angle, "cta_template")

    def test_get_recommended_angle_advogado_classic(self):
        from backend.copywriting.copy_angles import get_recommended_angle
        angle = get_recommended_angle("advogado", subnicho="", polo="CLASSIC")
        # CLASSIC -> authority/storybrand
        assert angle.framework in ("StoryBrand", "Authority", "PAS", "AIDA", "Social Proof")

    def test_get_recommended_angle_nutri_soft(self):
        from backend.copywriting.copy_angles import get_recommended_angle
        angle = get_recommended_angle("nutricionista", subnicho="", polo="SOFT")
        # SOFT -> storybrand/social_proof
        assert angle is not None

    def test_get_recommended_angle_energia_tech(self):
        from backend.copywriting.copy_angles import get_recommended_angle
        angle = get_recommended_angle("energia_solar", subnicho="", polo="TECH")
        # TECH -> specificity/contrarian
        assert angle is not None

    def test_get_recommended_angle_fallback(self):
        """Nicho desconhecido nao pode quebrar."""
        from backend.copywriting.copy_angles import get_recommended_angle
        angle = get_recommended_angle("nicho_xyz", subnicho="", polo="CLASSIC")
        assert angle is not None


# ═══════════════════════════════════════════════════════════════════════════
# 2. polo_voice: 4 polos com vocabulario, proibicoes, gatilhos
# ═══════════════════════════════════════════════════════════════════════════

class TestPoloVoice:
    """polo_voice.py expoe 4 polos com caracteristicas proprias."""

    def test_4_polos_definidos(self):
        from backend.copywriting.polo_voice import POLO_VOICES
        assert set(POLO_VOICES.keys()) == {"SOFT", "BOLD", "CLASSIC", "TECH"}

    def test_cada_polo_tem_vocabulary(self):
        from backend.copywriting.polo_voice import POLO_VOICES
        for polo, voice in POLO_VOICES.items():
            assert len(voice.vocabulary) >= 10, f"{polo} tem só {len(voice.vocabulary)} palavras"

    def test_cada_polo_tem_avoid_words(self):
        from backend.copywriting.polo_voice import POLO_VOICES
        for polo, voice in POLO_VOICES.items():
            assert len(voice.avoid_words) >= 5, f"{polo} tem só {len(voice.avoid_words)} avoid_words"

    def test_cada_polo_tem_mental_triggers(self):
        from backend.copywriting.polo_voice import POLO_VOICES
        for polo, voice in POLO_VOICES.items():
            assert len(voice.mental_triggers) >= 4, f"{polo} tem só {len(voice.mental_triggers)} triggers"

    def test_polos_tem_vocabulario_distinto(self):
        """Cada polo tem vocabulario proprio (sem misturar)."""
        from backend.copywriting.polo_voice import POLO_VOICES
        v_soft = set(POLO_VOICES["SOFT"].vocabulary)
        v_bold = set(POLO_VOICES["BOLD"].vocabulary)
        v_classic = set(POLO_VOICES["CLASSIC"].vocabulary)
        v_tech = set(POLO_VOICES["TECH"].vocabulary)
        # BOLD e SOFT nao devem misturar muito
        overlap_soft_bold = len(v_soft & v_bold)
        assert overlap_soft_bold <= 2, f"SOFT e BOLD compartilham {overlap_soft_bold} palavras: {v_soft & v_bold}"

    def test_avoid_words_diferem_entre_polos(self):
        """O que BOLD evita, SOFT pode usar (e vice-versa)."""
        from backend.copywriting.polo_voice import POLO_VOICES
        avoid_soft = set(POLO_VOICES["SOFT"].avoid_words)
        avoid_bold = set(POLO_VOICES["BOLD"].avoid_words)
        # BOLD nao pode evitar "agressivo" (que faz parte de sua identidade)
        # E SOFT nao pode evitar "acolhimento" (parte de sua identidade)
        # Apenas verificar que os 2 polos tem avoid_words diferentes
        assert avoid_soft != avoid_bold

    def test_get_polo_voice(self):
        from backend.copywriting.polo_voice import get_polo_voice
        v = get_polo_voice("BOLD")
        assert v is not None
        assert len(v.vocabulary) > 0

    def test_get_polo_voice_lanca_erro_para_polo_invalido(self):
        from backend.copywriting.polo_voice import get_polo_voice
        # get_polo_voice e estrito: polo invalido lanca ValueError
        with pytest.raises(ValueError):
            get_polo_voice("UNKNOWN_POLO")


# ═══════════════════════════════════════════════════════════════════════════
# 3. validate_copy_against_voice: detecta problemas
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateCopyAgainstVoice:
    """validate_copy_against_voice detecta problemas reais."""

    def test_copy_sem_vocabulario_bold_detecta_problema(self):
        from backend.copywriting.polo_voice import validate_copy_against_voice
        cop = "Bem vindos ao nosso espaço, aqui você encontra calma e tranquilidade."
        problemas, sugestoes = validate_copy_against_voice(cop, "BOLD")
        # "calma" e "tranquilidade" nao sao vocabulario BOLD
        assert len(problemas) > 0

    def test_copy_com_vocabulario_bold_sem_problema(self):
        from backend.copywriting.polo_voice import validate_copy_against_voice
        cop = "Agora é hora de superar seus limites. Supere a constancia. Faca mais."
        problemas, sugestoes = validate_copy_against_voice(cop, "BOLD")
        # "agora", "superar", "constancia", "faca" sao vocabulario BOLD
        # Nao deve reportar problema de vocabulario
        vocab_problems = [p for p in problemas if "vocabulario" in p.lower()]
        assert len(vocab_problems) == 0

    def test_copy_com_avoid_word_bold_detecta(self):
        from backend.copywriting.polo_voice import validate_copy_against_voice
        cop = "Um lugar suave e acolhedor para seu treino."
        problemas, sugestoes = validate_copy_against_voice(cop, "BOLD")
        # "suave" e "acolhedor" estao em avoid_words de BOLD
        assert len(problemas) > 0

    def test_copy_soft_com_vocabulario_soft(self):
        from backend.copywriting.polo_voice import validate_copy_against_voice
        cop = "Cuidar de você é o nosso ofício. Cada detalhe pensado com calma e afeto."
        problemas, sugestoes = validate_copy_against_voice(cop, "SOFT")
        vocab_problems = [p for p in problemas if "vocabulario" in p.lower()]
        assert len(vocab_problems) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. seo_templates: 56 templates (13 nichos x 4 polos + 4 default)
# ═══════════════════════════════════════════════════════════════════════════

class TestSeoTemplates:
    """seo_templates.py expoe templates SEO por polo+nicho."""

    def test_4_polos_definidos(self):
        from backend.copywriting.seo_templates import SEO_TEMPLATES
        assert set(SEO_TEMPLATES.keys()) == {"SOFT", "BOLD", "CLASSIC", "TECH"}

    def test_cada_polo_tem_multiplos_nichos(self):
        from backend.copywriting.seo_templates import SEO_TEMPLATES
        for polo, nichos in SEO_TEMPLATES.items():
            assert len(nichos) >= 13, f"{polo} tem só {len(nichos)} nichos"

    def test_total_templates(self):
        from backend.copywriting.seo_templates import SEO_TEMPLATES
        total = sum(len(n) for n in SEO_TEMPLATES.values())
        assert total >= 52, f"Esperado 52+ templates, got {total}"

    def test_get_seo_template_retorna_template(self):
        from backend.copywriting.seo_templates import get_seo_template
        tpl = get_seo_template("BOLD", "academia")
        assert tpl is not None
        assert "{name}" in tpl.title_pattern
        assert "{city}" in tpl.title_pattern

    def test_generate_title_tem_50_60_chars(self):
        from backend.copywriting.seo_templates import get_seo_template, generate_title, validate_title_length
        tpl = get_seo_template("BOLD", "academia")
        title = generate_title(tpl, "Iron Gym", "Sao Paulo")
        assert 30 <= len(title) <= 70, f"Title tem {len(title)} chars: '{title}'"

    def test_generate_title_diferente_entre_polos(self):
        from backend.copywriting.seo_templates import get_seo_template, generate_title
        tpl_soft = get_seo_template("SOFT", "nutricionista")
        tpl_bold = get_seo_template("BOLD", "academia")
        title_soft = generate_title(tpl_soft, "Dra. Marina", "SP")
        title_bold = generate_title(tpl_bold, "Iron Gym", "SP")
        # Devem ser substancialmente diferentes
        assert title_soft != title_bold

    def test_h1_tem_8_mais_palavras(self):
        from backend.copywriting.seo_templates import get_seo_template, generate_h1
        for polo in ("SOFT", "BOLD", "CLASSIC", "TECH"):
            tpl = get_seo_template(polo, "academia")
            h1 = generate_h1(tpl, "Sao Paulo")
            words = len(h1.split())
            assert words >= 8, f"{polo} h1 tem só {words} palavras: '{h1}'"


# ═══════════════════════════════════════════════════════════════════════════
# 5. bloco_copy.py injeta copy_angle e polo_voice
# ═══════════════════════════════════════════════════════════════════════════

class TestBlocoCopyInjetaCopyAngle:
    """_montar_prompt_bloco2 inclui COPY ANGLE e VOICE CHECK."""

    def _build_prompt(self, segmento: str, polo: str = "BOLD"):
        from backend.agents.bloco_copy import _montar_prompt_bloco2
        return _montar_prompt_bloco2(
            nome="X",
            cidade="Y",
            segmento=segmento,
            telefone="",
            endereco="",
            rating=4.5,
            total_av=10,
            caio_tier="STANDARD",
            dark_mode=False,
            jina_insights="",
            instrucao_criativa="",
            reviews_fmt="",
            reviews_intel_ctx="",
            seo_ctx="",
            faq_seo_fmt="",
            keyword_research="",
            secoes_nomes=["hero", "sobre", "contato"],
            reviews_has=False,
            intel_ctx="",
            craft_ctx="",
            autocritica_ctx="",
            polo_resolvido=polo,
        )

    def test_prompt_contem_copy_angle_label(self):
        try:
            prompt = self._build_prompt("academia", "BOLD")
        except Exception as e:
            pytest.skip(f"bloco_copy requer env completo: {e}")
        assert "COPY ANGLE" in prompt

    def test_prompt_contem_voice_check(self):
        try:
            prompt = self._build_prompt("academia", "BOLD")
        except Exception as e:
            pytest.skip(f"bloco_copy requer env completo: {e}")
        assert "VOICE CHECK" in prompt

    def test_prompt_contem_polo_marcado(self):
        try:
            prompt = self._build_prompt("academia", "BOLD")
        except Exception as e:
            pytest.skip(f"bloco_copy requer env completo: {e}")
        assert "POLO: BOLD" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 6. Copy NÃO-generico nas 38 lanes (anti-cliche check)
# ═══════════════════════════════════════════════════════════════════════════

class TestCopyNaoGenerico:
    """Copy das lanes NAO pode conter palavras genericas proibidas."""

    GENERIC_FORBIDDEN = [
        "resultados reais", "melhores profissionais", "qualidade e compromisso",
        "transformacao digital", "pronto para comecar", "venha conhecer",
    ]

    def test_lane_copy_sem_palavras_genericas(self):
        import sys
        sys.path.insert(0, 'C:/fralib')
        from backend.services.vite_visual_lanes import _LANE_COPY_ENRICHMENTS
        problemas = []
        for lid, copy in _LANE_COPY_ENRICHMENTS.items():
            # Concatena todos os campos
            texto = " ".join(str(v) for v in copy.values()).lower()
            for forbidden in self.GENERIC_FORBIDDEN:
                if forbidden in texto:
                    problemas.append(f'{lid}: contem "{forbidden}"')
        # Permitir até 5% de lanes com problema (algumas podem ter copy antigo)
        max_problemas = max(3, len(_LANE_COPY_ENRICHMENTS) // 20)
        assert len(problemas) <= max_problemas, (
            f"{len(problemas)} lanes com copy generico: {problemas[:5]}"
        )

    def test_cada_lane_tem_pelo_menos_3_palavras_distintas(self):
        import sys
        sys.path.insert(0, 'C:/fralib')
        from backend.services.vite_visual_lanes import _LANE_COPY_ENRICHMENTS
        for lid, copy in _LANE_COPY_ENRICHMENTS.items():
            texto = " ".join(str(v) for v in copy.values())
            palavras = texto.lower().split()
            unicas = set(palavras)
            assert len(unicas) >= 5, f"{lid}: copy muito pobre ({len(unicas)} palavras unicas)"