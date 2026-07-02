"""
============================================================================
TESTES: nicho_config.py — Fonte única de verdade para nichos
============================================================================
Cobertura: 13 nichos canônicos + aliases + fallback default
============================================================================
"""

import pytest
import sys

sys.path.insert(0, ".")


# ────────────────────────────────────────────────────────────────────────
# 1. ESTRUTURA
# ────────────────────────────────────────────────────────────────────────

class TestEstruturaNichoConfig:
    """Estrutura do módulo nicho_config."""

    def test_modulo_importa(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        assert isinstance(NICHO_CONFIG, dict)

    def test_13_nichos_canonicos(self):
        from backend.config.nicho_registry import listar_nichos
        nichos = listar_nichos()
        assert len(nichos) == 13
        for n in ("academia", "advogado", "barbearia", "clinica",
                  "dentista", "estetica", "nutricionista", "restaurante",
                  "pet_shop", "salao", "oficina", "energia_solar", "imobiliaria"):
            assert n in nichos, f"Nicho {n} faltando"

    def test_default_existe(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        assert "default" in NICHO_CONFIG

    def test_todos_nichos_tem_campos_obrigatorios(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        for key, cfg in NICHO_CONFIG.items():
            assert cfg.schema_type, f"{key} sem schema_type"
            assert cfg.polo_sugerido in {"SOFT", "BOLD", "CLASSIC", "TECH"}, \
                f"{key} polo invalido: {cfg.polo_sugerido}"
            assert len(cfg.lanes) >= 1, f"{key} sem lanes"
            assert cfg.modal_config.title, f"{key} sem modal title"
            assert cfg.modal_config.cta_button, f"{key} sem modal cta"
            assert len(cfg.faq) >= 3, f"{key} FAQ insuficiente ({len(cfg.faq)})"
            assert cfg.copy_defaults.cta_primary, f"{key} sem cta_primary"


# ────────────────────────────────────────────────────────────────────────
# 2. LOOKUP DIRETO
# ────────────────────────────────────────────────────────────────────────

class TestLookupDireto:
    """get_nicho_config() resolve nomes canônicos."""

    @pytest.mark.parametrize("nicho,polo_esperado,schema_esperado", [
        ("academia", "BOLD", "HealthClub"),
        ("advogado", "CLASSIC", "LegalService"),
        ("barbearia", "SOFT", "BarberShop"),
        ("clinica", "CLASSIC", "MedicalClinic"),
        ("dentista", "CLASSIC", "Dentist"),
        ("estetica", "SOFT", "BeautySalon"),
        ("nutricionista", "SOFT", "MedicalBusiness"),
        ("restaurante", "SOFT", "Restaurant"),
        ("pet_shop", "SOFT", "PetStore"),
        ("salao", "SOFT", "HairSalon"),
        ("oficina", "BOLD", "AutoRepair"),
        ("energia_solar", "TECH", "HomeAndConstructionBusiness"),
        ("imobiliaria", "CLASSIC", "RealEstateAgent"),
        ("default", "CLASSIC", "LocalBusiness"),
    ])
    def test_lookup_direto(self, nicho, polo_esperado, schema_esperado):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(nicho)
        assert cfg.polo_sugerido == polo_esperado
        assert cfg.schema_type == schema_esperado


# ────────────────────────────────────────────────────────────────────────
# 3. ALIASES
# ────────────────────────────────────────────────────────────────────────

class TestAliases:
    """Aliases normalizam para chave canônica."""

    @pytest.mark.parametrize("alias,canonico,polo", [
        # academia
        ("crossfit", "academia", "BOLD"),
        ("musculacao", "academia", "BOLD"),
        ("gym", "academia", "BOLD"),
        ("fitness", "academia", "BOLD"),
        # advogado
        ("advocacia", "advogado", "CLASSIC"),
        ("juridico", "advogado", "CLASSIC"),
        # estetica
        ("harmonizacao", "estetica", "SOFT"),
        ("clinica_estetica", "estetica", "SOFT"),
        # restaurante
        ("pizzaria", "restaurante", "SOFT"),
        ("hamburgueria", "restaurante", "SOFT"),
        # pet
        ("veterinaria", "pet_shop", "SOFT"),
        # oficina
        ("mecanico", "oficina", "BOLD"),
        # energia solar
        ("solar", "energia_solar", "TECH"),
        ("placa_solar", "energia_solar", "TECH"),
    ])
    def test_alias_resolve_canonico(self, alias, canonico, polo):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(alias)
        assert cfg.polo_sugerido == polo
        assert cfg.schema_type == get_schema_for(canonico)


def get_schema_for(canonico: str) -> str:
    """Helper: retorna schema_type canonico."""
    from backend.config.nicho_registry import get_nicho_config
    return get_nicho_config(canonico).schema_type


# ────────────────────────────────────────────────────────────────────────
# 4. FALLBACK
# ────────────────────────────────────────────────────────────────────────

class TestFallback:
    """Nicho desconhecido cai em default."""

    def test_nicho_inexistente_caem_default(self):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config("nao_existe_xyz")
        assert cfg.schema_type == "LocalBusiness"
        assert cfg.polo_sugerido == "CLASSIC"

    def test_nicho_none_caem_default(self):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(None)
        assert cfg.schema_type == "LocalBusiness"

    def test_nicho_vazio_caem_default(self):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config("")
        assert cfg.schema_type == "LocalBusiness"


# ────────────────────────────────────────────────────────────────────────
# 5. ATALHOS
# ────────────────────────────────────────────────────────────────────────

class TestAtalhos:
    """Atalhos retornam a parte certa da config."""

    def test_get_modal_config(self):
        from backend.config.nicho_registry import get_modal_config
        modal = get_modal_config("academia")
        assert "Matricule-se" in modal.title
        assert modal.cta_button == "Falar com Consultor"
        assert len(modal.fields) >= 3

    def test_get_schema_type(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("advogado") == "LegalService"
        assert get_schema_type("restaurante") == "Restaurant"
        assert get_schema_type("clinica") == "MedicalClinic"

    def test_get_faq(self):
        from backend.config.nicho_registry import get_faq
        faq = get_faq("advogado")
        assert len(faq) >= 5
        assert all(isinstance(q, str) for q in faq)
        assert any("consulta" in q.lower() or "honorario" in q.lower() for q in faq)

    def test_get_cta_primary(self):
        from backend.config.nicho_registry import get_cta_primary
        assert get_cta_primary("academia") == "Falar no WhatsApp"
        assert get_cta_primary("advogado") == "Agendar Consulta"

    def test_get_polo_sugerido(self):
        from backend.config.nicho_registry import get_polo_sugerido
        assert get_polo_sugerido("academia") == "BOLD"
        assert get_polo_sugerido("estetica") == "SOFT"
        assert get_polo_sugerido("energia_solar") == "TECH"
        assert get_polo_sugerido("advogado") == "CLASSIC"

    def test_get_polo_sugerido_default(self):
        from backend.config.nicho_registry import get_polo_sugerido
        assert get_polo_sugerido("qualquer_coisa") == "CLASSIC"


# ────────────────────────────────────────────────────────────────────────
# 6. HERO HEADLINES
# ────────────────────────────────────────────────────────────────────────

class TestHeroHeadlines:
    """Templates de headline por (nicho, polo)."""

    def test_get_hero_headline_advogado_classic(self):
        from backend.config.nicho_registry import get_hero_headline
        headline = get_hero_headline("advogado", "CLASSIC")
        assert headline != ""
        assert isinstance(headline, str)
        assert "Estrategia" in headline or "juridica" in headline.lower()

    def test_get_hero_headline_todos_polos(self):
        from backend.config.nicho_registry import get_hero_headline
        for polo in ("SOFT", "BOLD", "CLASSIC", "TECH"):
            h = get_hero_headline("academia", polo)
            assert h != "", f"academia + {polo} sem headline"

    def test_get_hero_headline_default_retorna_vazio(self):
        from backend.config.nicho_registry import get_hero_headline
        # Polo inexistente → string vazia
        assert get_hero_headline("academia", "POLO_INEXISTENTE") == ""


# ────────────────────────────────────────────────────────────────────────
# 7. IMUTABILIDADE
# ────────────────────────────────────────────────────────────────────────

class TestImutabilidade:
    """Dataclasses são frozen=True."""

    def test_nicho_config_imutavel(self):
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config("academia")
        with pytest.raises(Exception):  # FrozenInstanceError ou AttributeError
            cfg.polo_sugerido = "BOLD"  # type: ignore

    def test_modal_config_imutavel(self):
        from backend.config.nicho_registry import get_modal_config
        modal = get_modal_config("academia")
        with pytest.raises(Exception):
            modal.title = "Outro"  # type: ignore

    def test_nicho_config_dict_nao_mutavel_direto(self):
        from backend.config.nicho_registry import NICHO_CONFIG
        # NICHO_CONFIG é dict (mutável por design), mas os valores são imutáveis
        assert isinstance(NICHO_CONFIG, dict)
        cfg = NICHO_CONFIG["academia"]
        with pytest.raises(Exception):
            cfg.polo_sugerido = "BOLD"  # type: ignore


# ────────────────────────────────────────────────────────────────────────
# 8. COBERTURA DE NICHO_MODAL_CONFIG
# ────────────────────────────────────────────────────────────────────────

class TestCoberturaModal:
    """Todos os nichos cobrem o booking modal."""

    @pytest.mark.parametrize("nicho", [
        "academia", "advogado", "barbearia", "clinica", "dentista",
        "estetica", "nutricionista", "restaurante", "pet_shop",
        "salao", "oficina", "energia_solar", "imobiliaria",
    ])
    def test_modal_nao_e_default(self, nicho):
        """Cada nicho (não default) deve ter modal próprio, não genérico."""
        from backend.config.nicho_registry import get_modal_config, get_modal_config as gmc
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(nicho)
        modal = gmc(nicho)
        # Não pode ser o título default
        assert modal.title != "Fale Conosco", f"{nicho} caindo no default"
        # Deve ter polo coerente com o nicho
        assert cfg.polo_sugerido in {"SOFT", "BOLD", "CLASSIC", "TECH"}


# ────────────────────────────────────────────────────────────────────────
# 9. LISTAR_NICHOS
# ────────────────────────────────────────────────────────────────────────

class TestListarNichos:
    """listar_nichos() exclui 'default'."""

    def test_listar_exclui_default(self):
        from backend.config.nicho_registry import listar_nichos
        nichos = listar_nichos()
        assert "default" not in nichos

    def test_listar_retorna_tupla(self):
        from backend.config.nicho_registry import listar_nichos
        nichos = listar_nichos()
        assert isinstance(nichos, tuple)

    def test_listar_tem_13_nichos(self):
        from backend.config.nicho_registry import listar_nichos
        assert len(listar_nichos()) == 13