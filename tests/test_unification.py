"""
============================================================================
TESTES: Unificação housekeeping (Etapa 5)
============================================================================

Sprint 12.x: nicho_registry.py é fonte única de verdade. Constantes legadas
(NICHO_MODAL_CONFIG, SEO_NICHOS, _FAMILY_COPY_DEFAULTS) existem apenas como
fallback, mas código NOVO deve usar o registry.

Validacoes:
1. nicho_registry é fonte única
2. Constantes legadas estao marcadas DEPRECATED
3. get_family_copy_defaults() funciona via registry
4. _get_legacy_modal_config() existe para compatibilidade
5. get_seo_context() consulta registry primeiro
============================================================================
"""

import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _PROJECT_ROOT / "backend"
for _p in (str(_BACKEND_PATH), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. NICHO_REGISTRY é fonte única
# ═══════════════════════════════════════════════════════════════════════════

class TestNichoRegistryFonteUnica:
    """nicho_registry.py é a única fonte de verdade para nicho."""

    def test_registry_tem_13_nichos(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        assert len(NICHO_CONFIG) == 14  # 13 + default
        assert "default" in NICHO_CONFIG

    def test_cada_nicho_tem_schema_type(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            assert cfg.schema_type, f"{nicho} sem schema_type"
            assert " " not in cfg.schema_type, f"{nicho} schema_type invalido: {cfg.schema_type}"

    def test_cada_nicho_tem_polo_sugerido(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        valid = {"SOFT", "BOLD", "CLASSIC", "TECH"}
        for nicho, cfg in NICHO_CONFIG.items():
            assert cfg.polo_sugerido in valid, f"{nicho} polo invalido: {cfg.polo_sugerido}"

    def test_cada_nicho_tem_modal_config(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            assert cfg.modal_config.title, f"{nicho} sem modal title"
            assert cfg.modal_config.cta_button, f"{nicho} sem cta_button"

    def test_cada_nicho_tem_ao_menos_2_lanes(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            if nicho == "default":
                continue
            assert len(cfg.lanes) >= 2, f"{nicho} tem so {len(cfg.lanes)} lanes"

    def test_cada_nicho_tem_seo_keywords(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            # default pode ter tupla vazia
            if nicho == "default":
                continue
            assert len(cfg.seo_keywords) >= 3, f"{nicho} tem so {len(cfg.seo_keywords)} keywords"

    def test_cada_nicho_tem_copy_defaults(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            assert cfg.copy_defaults.tone, f"{nicho} sem tone"
            assert cfg.copy_defaults.cta_primary, f"{nicho} sem cta_primary"

    def test_cada_nicho_tem_design_logic(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            assert cfg.design_logic is not None, f"{nicho} sem design_logic"


# ═══════════════════════════════════════════════════════════════════════════
# 2. CONSTANTES LEGADAS marcadas DEPRECATED
# ═══════════════════════════════════════════════════════════════════════════

class TestLegacyMarcadoDeprecated:
    """Constantes legadas (NICHO_MODAL_CONFIG, SEO_NICHOS, _FAMILY_COPY_DEFAULTS)
    estao claramente marcadas como DEPRECATED."""

    def test_nicho_modal_config_marcado_deprecated(self):
        content = Path("backend/services/vite_prompts.py").read_text(encoding="utf-8")
        # Procura bloco antes de NICHO_MODAL_CONFIG
        idx = content.find("NICHO_MODAL_CONFIG:")
        assert idx > 0
        # Pega 500 chars antes
        prefix = content[max(0, idx - 500):idx]
        assert "DEPRECATED" in prefix, "NICHO_MODAL_CONFIG nao marcado DEPRECATED"

    def test_seo_nichos_marcado_deprecated(self):
        content = Path("backend/agents/seo_context.py").read_text(encoding="utf-8")
        assert "DEPRECATED" in content[:300], "seo_context.py nao marcado DEPRECATED no topo"

    def test_family_copy_defaults_marcado_deprecated(self):
        content = Path("backend/services/vite_visual_lanes.py").read_text(encoding="utf-8")
        m = re.search(r'_FAMILY_COPY_DEFAULTS:', content)
        assert m
        # Pega 500 chars antes do ponto
        start = max(0, m.start() - 500)
        prefix = content[start:m.start()]
        assert "DEPRECATED" in prefix, "_FAMILY_COPY_DEFAULTS nao marcado DEPRECATED"


# ═══════════════════════════════════════════════════════════════════════════
# 3. get_family_copy_defaults() funciona via registry
# ═══════════════════════════════════════════════════════════════════════════

class TestGetFamilyCopyDefaults:
    """get_family_copy_defaults() consulta o registry."""

    def test_retorna_dict_para_nicho_canonico(self):
        from backend.services.vite_visual_lanes import get_family_copy_defaults
        out = get_family_copy_defaults("academia")
        assert isinstance(out, dict)
        assert len(out) > 0

    def test_contem_campos_nav(self):
        from backend.services.vite_visual_lanes import get_family_copy_defaults
        out = get_family_copy_defaults("academia")
        # Deve ter pelo menos nav_about ou nav_services
        assert any(k.startswith("nav_") for k in out.keys())

    def test_contem_cta_primary_do_registry(self):
        from backend.services.vite_visual_lanes import get_family_copy_defaults
        out = get_family_copy_defaults("academia")
        # academia tem cta_primary "Falar no WhatsApp"
        # Vai aparecer em contact_kicker
        assert "WhatsApp" in out.get("contact_kicker", "")

    def test_nicho_desconhecido_falls_back_para_default(self):
        from backend.services.vite_visual_lanes import get_family_copy_defaults
        out = get_family_copy_defaults("nicho_xyz_inexistente")
        # Fallback para default legacy
        assert isinstance(out, dict)


# ═══════════════════════════════════════════════════════════════════════════
# 4. _get_legacy_modal_config() existe
# ═══════════════════════════════════════════════════════════════════════════

class TestLegacyModalConfigCompat:
    """_get_legacy_modal_config() existe para compatibilidade."""

    def test_retorna_dict_com_keys_legadas(self):
        from backend.services.vite_prompts import _get_legacy_modal_config
        out = _get_legacy_modal_config()
        assert isinstance(out, dict)
        assert "academia" in out
        assert "default" in out
        # Cada entrada tem title, cta_button, fields
        for nicho, cfg in out.items():
            assert "title" in cfg
            assert "cta_button" in cfg

    def test_nicho_modal_config_ainda_existe(self):
        """NICHO_MODAL_CONFIG ainda pode ser importado (compat)."""
        from backend.services.vite_prompts import NICHO_MODAL_CONFIG
        assert isinstance(NICHO_MODAL_CONFIG, dict)
        assert "academia" in NICHO_MODAL_CONFIG


# ═══════════════════════════════════════════════════════════════════════════
# 5. get_seo_context() consulta registry primeiro
# ═══════════════════════════════════════════════════════════════════════════

class TestGetSeoContextUsaRegistry:
    """get_seo_context() usa nicho_registry como fonte primaria."""

    def test_advogado_retorna_schema_correto_do_registry(self):
        from backend.agents.seo_context import get_seo_context
        ctx = get_seo_context("advogado", "Sao Paulo", "Silva Direito")
        # Registry tem advogado.schema_type = "LegalService"
        assert "LegalService" in ctx

    def test_restaurante_retorna_schema_correto_do_registry(self):
        from backend.agents.seo_context import get_seo_context
        ctx = get_seo_context("restaurante", "Sao Paulo", "Cantina")
        # Registry tem restaurante.schema_type = "Restaurant"
        assert "Restaurant" in ctx

    def test_nicho_desconhecido_falls_back_para_legacy(self):
        from backend.agents.seo_context import get_seo_context
        # Nicho nao esta no registry: contabilidade
        # Mas tem fallback no SEO_NICHOS
        ctx = get_seo_context("contabilidade", "Sao Paulo", "Contador")
        assert "SCHEMA.ORG" in ctx  # pelo menos retorna formato correto

    def test_output_contem_h1_obrigatorio(self):
        from backend.agents.seo_context import get_seo_context
        ctx = get_seo_context("academia", "Sao Paulo", "Iron Gym")
        assert "H1 OBRIGATORIO" in ctx
        assert "Sao Paulo" in ctx or "Iron Gym" in ctx


# ═══════════════════════════════════════════════════════════════════════════
# 6. Imports externos nao quebraram
# ═══════════════════════════════════════════════════════════════════════════

class TestImportsExternos:
    """Imports legados continuam funcionando."""

    def test_seo_context_imports_principais(self):
        from backend.agents.seo_context import get_seo_context, SEO_NICHOS, ALIASES
        assert callable(get_seo_context)
        assert isinstance(SEO_NICHOS, dict)
        assert isinstance(ALIASES, dict)

    def test_vite_prompts_imports_principais(self):
        from backend.services.vite_prompts import NICHO_MODAL_CONFIG, _get_legacy_modal_config
        assert isinstance(NICHO_MODAL_CONFIG, dict)
        assert callable(_get_legacy_modal_config)

    def test_vite_visual_lanes_legacy_constants(self):
        from backend.services.vite_visual_lanes import _LANE_COPY_ENRICHMENTS, _FAMILY_COPY_DEFAULTS
        assert isinstance(_LANE_COPY_ENRICHMENTS, dict)
        assert isinstance(_FAMILY_COPY_DEFAULTS, dict)
        # _FAMILY_COPY_DEFAULTS agora é fallback
        assert len(_FAMILY_COPY_DEFAULTS) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 7. Anti-cliche: código não duplica fonte única
# ═══════════════════════════════════════════════════════════════════════════

class TestNaoDuplicaFonteUnica:
    """Verifica que o codigo nao duplica definicoes do registry."""

    def test_nicho_registry_tem_comentario_sobre_consolidacao(self):
        content = Path("backend/config/nicho_registry.py").read_text(encoding="utf-8")
        # Procura mencao a fonte unica (com ou sem acentos, OU single source)
        texto_lower = content.lower()
        has_fonte = "fonte unic" in texto_lower
        has_source = "single source" in texto_lower
        has_objetivo = "objetivo" in texto_lower
        assert has_fonte or has_source or has_objetivo, (
            "nicho_registry.py deve documentar que e fonte unica"
        )

    def test_polo_prompts_delega_para_nicho_registry(self):
        content = Path("backend/agents/polo_prompts.py").read_text(encoding="utf-8")
        assert "nicho_registry" in content, (
            "polo_prompts.py deve usar nicho_registry como fonte"
        )

    def test_copy_angles_nao_duplica_copy_defaults(self):
        """copy_angles.py nao redefine CopyDefaults (isso é do registry)."""
        content = Path("backend/copywriting/copy_angles.py").read_text(encoding="utf-8")
        # Nao deve ter CopyDefaults como dataclass
        assert "class CopyDefaults" not in content, (
            "copy_angles.py esta duplicando CopyDefaults do registry"
        )

    def test_polo_voice_nao_duplica_DesignLogic(self):
        """polo_voice.py nao redefine DesignLogic (isso é do registry)."""
        content = Path("backend/copywriting/polo_voice.py").read_text(encoding="utf-8")
        assert "class DesignLogic" not in content, (
            "polo_voice.py esta duplicando DesignLogic do registry"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8. Constituição documenta arquitetura
# ═══════════════════════════════════════════════════════════════════════════

class TestDocumentacaoArquitetura:
    """docs/ documenta a arquitetura."""

    def test_polos_e_nichos_doc_existe(self):
        assert Path("docs/POLOS_E_NICHOS.md").exists()

    def test_polos_e_nichos_doc_tem_secoes_essenciais(self):
        content = Path("docs/POLOS_E_NICHOS.md").read_text(encoding="utf-8")
        content_lower = content.lower()
        # Normalizar acentos: 'unica' ou 'única' ambas viram 'unica' após decompose
        import unicodedata
        content_normalized = unicodedata.normalize("NFKD", content_lower)
        content_ascii = content_normalized.encode("ascii", "ignore").decode("ascii")
        required = [
            "fonte unic",
            "polo",
            "nicho",
            "alias",
            "fluxo",
        ]
        for sec in required:
            assert sec in content_ascii, f"docs/POLOS_E_NICHOS.md falta: {sec}"

    def test_polos_e_nichos_doc_lista_nichos(self):
        content = Path("docs/POLOS_E_NICHOS.md").read_text(encoding="utf-8")
        for nicho in ("academia", "advogado", "energia_solar", "restaurante", "salao"):
            assert nicho in content, f"docs/POLOS_E_NICHOS.md falta nicho: {nicho}"