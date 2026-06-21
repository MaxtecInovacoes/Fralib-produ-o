"""Testes da biblioteca de Design Systems."""
import pytest

from backend.agents.design_systems_library import (
    ALL_DESIGN_SYSTEMS,
    ACADEMIA,
    ADVOCACIA,
    BARBEARIA,
    CLINICA_DENTAL,
    ESTETICA,
    HAMBURGUERIA,
    IMOBILIARIA,
    OFICINA,
    PET_SHOP,
    PILATES,
    RESTAURANTE_BISTRO,
    SALAO_BELEZA,
    list_all_nichos,
    resolve_nicho,
)


class TestDesignSystems:
    def test_todos_tem_paleta(self):
        for ds in ALL_DESIGN_SYSTEMS.values():
            assert ds.paleta.primary.startswith("#")
            assert ds.paleta.bg.startswith("#")
            assert ds.paleta.fg.startswith("#")

    def test_todos_tem_typography(self):
        for ds in ALL_DESIGN_SYSTEMS.values():
            assert ds.typography.display != ""
            assert ds.typography.body != ""

    def test_todos_tem_motion(self):
        for ds in ALL_DESIGN_SYSTEMS.values():
            assert isinstance(ds.motion.parallax, bool)
            assert isinstance(ds.motion.reveal_on_scroll, bool)

    def test_todos_tem_hero_type(self):
        valid = {"video", "split", "fullscreen", "diagonal", "magazine"}
        for ds in ALL_DESIGN_SYSTEMS.values():
            assert ds.sections.hero_type in valid


class TestResolveNicho:
    def test_match_direto(self):
        ds = resolve_nicho("academia", "crossfit")
        assert ds == ACADEMIA

    def test_match_so_nicho(self):
        ds = resolve_nicho("academia")
        assert ds in (ACADEMIA, PILATES)

    def test_sinonimo_crossfit(self):
        ds = resolve_nicho("crossfit")
        assert ds == ACADEMIA

    def test_sinonimo_dentista(self):
        ds = resolve_nicho("dentista")
        assert ds == CLINICA_DENTAL

    def test_sinonimo_odontologia(self):
        ds = resolve_nicho("odontologia")
        assert ds == CLINICA_DENTAL

    def test_sinonimo_pilates(self):
        ds = resolve_nicho("pilates")
        assert ds == PILATES

    def test_sinonimo_hamburgueria(self):
        ds = resolve_nicho("hamburgueria")
        assert ds == HAMBURGUERIA

    def test_sinonimo_barbearia(self):
        ds = resolve_nicho("barbearia")
        assert ds == BARBEARIA

    def test_sinonimo_salao(self):
        ds = resolve_nicho("salao")
        assert ds == SALAO_BELEZA

    def test_sinonimo_imobiliaria(self):
        ds = resolve_nicho("corretor")
        assert ds == IMOBILIARIA

    def test_sinonimo_advocacia(self):
        ds = resolve_nicho("escritorio")
        assert ds == ADVOCACIA

    def test_nicho_inexistente_retorna_none(self):
        ds = resolve_nicho("banco_de_dados")
        assert ds is None

    def test_nicho_vazio_retorna_none(self):
        assert resolve_nicho("") is None


class TestListNichos:
    def test_tem_minimo_10_nichos(self):
        nichos = list_all_nichos()
        assert len(nichos) >= 10

    def test_cobre_nichos_principais(self):
        nichos = list_all_nichos()
        main_nichos = ["academia", "restaurante", "clinica", "barbearia", "salao", "oficina", "pet", "imobiliaria", "advocacia"]
        for n in main_nichos:
            assert any(n in x for x in nichos), f"Nicho {n} nao coberto"
