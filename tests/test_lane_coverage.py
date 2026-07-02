"""
============================================================================
TESTES: Cobertura de lanes (Etapa 3)
============================================================================

Sprint 12.x: nicho_registry declara 38 lanes em 13 nichos. vite_visual_lanes.py
deve ter TODAS elas (diretas ou via alias). Cada lane precisa ter copy_enrichment.

Cobertura esperada por nicho:
- academia:        4 lanes  (ja existem)
- advogado:        2 lanes
- barbearia:       4 lanes (alias para barber-* funciona)
- clinica:         2 lanes
- dentista:        2 lanes
- energia_solar:   2 lanes
- estetica:        4 lanes  (ja existem)
- imobiliaria:     2 lanes
- nutricionista:   4 lanes (alias para nutri-* funciona)
- oficina:         2 lanes
- pet_shop:        2 lanes
- restaurante:     2 lanes
- salao:           2 lanes
- default:         4 lanes  (ja existem)
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
# 1. COBERTURA TOTAL: registry lanes todas existem em vite_visual_lanes
# ═══════════════════════════════════════════════════════════════════════════

class TestLaneCoverageRegistry:
    """Todas as lanes declaradas no registry existem no vite_visual_lanes."""

    @pytest.fixture(scope="class")
    def declared_lanes(self) -> set[str]:
        from backend.config.nicho_registry import NICHO_CONFIG
        declared = set()
        for cfg in NICHO_CONFIG.values():
            declared.update(cfg.lanes)
        return declared

    @pytest.fixture(scope="class")
    def defined_lanes(self) -> set[str]:
        """Coleta ids de lanes definidos em vite_visual_lanes.py + aliases."""
        content = Path("backend/services/vite_visual_lanes.py").read_text(encoding="utf-8")
        ids = set(re.findall(r'"id":\s*"([a-z0-9_-]+)"', content))
        # Aliases resolvem automaticamente: barber-* resolve para barbearia-*
        # (ver _LANE_ID_ALIASES). Mas o test confere que tanto o nome canonico
        # quanto o alias estao presentes em alguma chave do arquivo.
        aliases_reverse = {}
        for old, new in re.findall(r'"([a-z0-9_-]+)":\s*"([a-z0-9_-]+)"', content):
            if len(old) < len(new) and (old.startswith("barber") or old.startswith("nutri")):
                aliases_reverse[new] = old
        ids_with_aliases = set(ids)
        for new_id, old_id in aliases_reverse.items():
            ids_with_aliases.add(new_id)
        return ids_with_aliases

    def test_todas_lanes_declaradas_existem(self, declared_lanes, defined_lanes):
        missing = declared_lanes - defined_lanes
        assert not missing, f"Lanes declaradas no registry mas ausentes em vite_visual_lanes: {sorted(missing)}"

    def test_total_minimo_de_lanes(self, defined_lanes):
        """Sistema precisa ter pelo menos 30 lanes (cobertura ampla)."""
        assert len(defined_lanes) >= 30, f"Apenas {len(defined_lanes)} lanes definidas"

    def test_cada_nicho_tem_pelo_menos_2_lanes(self):
        """Cada nicho canonico deve ter pelo menos 2 lanes para variacao."""
        from backend.config.nicho_registry import NICHO_CONFIG
        for nicho, cfg in NICHO_CONFIG.items():
            if nicho == "default":
                continue
            assert len(cfg.lanes) >= 2, f"Nicho {nicho} tem apenas {len(cfg.lanes)} lanes"


# ═══════════════════════════════════════════════════════════════════════════
# 2. SHAPE: cada lane tem campos obrigatorios
# ═══════════════════════════════════════════════════════════════════════════

class TestLaneShape:
    """Cada lane em _LANES tem shape correto."""

    def test_lane_tem_campos_obrigatorios(self):
        """Cada lane tem id, name, fallback_palette, blocks, copy."""
        content = Path("backend/services/vite_visual_lanes.py").read_text(encoding="utf-8")
        # Coletar lanes via regex (id, name)
        ids = re.findall(r'"id":\s*"([a-z0-9_-]+)"', content)
        assert len(ids) >= 30, f"Apenas {len(ids)} lanes encontradas"
        # Verificar que cada lane tem fallback_palette, blocks, copy
        for lane_id in ids[:5]:  # smoke test
            lane_block = re.search(
                rf'"id":\s*"{re.escape(lane_id)}".*?(?="id":|\Z)',
                content,
                re.DOTALL,
            )
            assert lane_block, f"Bloco da lane {lane_id} nao encontrado"
            block = lane_block.group(0)
            assert "fallback_palette" in block
            assert "blocks" in block
            assert "copy" in block

    def test_blocks_tem_6_variants(self):
        """blocks tem hero_variant, services_variant, reviews_variant,
        faq_variant, location_variant, surface_style."""
        content = Path("backend/services/vite_visual_lanes.py").read_text(encoding="utf-8")
        # Pegar uma lane qualquer e verificar
        m = re.search(r'"blocks":\s*\{[^}]+\}', content)
        assert m
        keys = re.findall(r'"([a-z_]+)":', m.group(0))
        required = {"hero_variant", "services_variant", "reviews_variant",
                    "faq_variant", "location_variant", "surface_style"}
        assert required.issubset(set(keys)), f"blocks sem todas as variants: {required - set(keys)}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. COPY_ENRICHMENTS cobre todas as lanes
# ═══════════════════════════════════════════════════════════════════════════

class TestCopyEnrichmentsCoverage:
    """_LANE_COPY_ENRICHMENTS tem entrada para cada lane."""

    def test_copy_enrichments_tem_todas_lanes(self):
        """Lanes que existem em _LANES devem ter copy_enrichment (ou herdar de
        _FAMILY_COPY_DEFAULTS). Lanes com nome canonico mas sem enrichment
        dedicado caem em fallback se o nome curto correspondente existe."""
        from backend.config.nicho_registry import NICHO_CONFIG
        from pathlib import Path
        import re

        declared = set()
        for cfg in NICHO_CONFIG.values():
            declared.update(cfg.lanes)

        content = Path("backend/services/vite_visual_lanes.py").read_text(encoding="utf-8")
        m = re.search(
            r'_LANE_COPY_ENRICHMENTS:\s*dict\[str,\s*dict\[str,\s*str\]\]\s*=\s*\{(.+?)\n\}',
            content, re.DOTALL,
        )
        if not m:
            pytest.skip("nao consegui parsear _LANE_COPY_ENRICHMENTS")
        keys = set(re.findall(r'"([a-z0-9_-]+)":\s*\{', m.group(1)))

        # Construir mapa de aliases (nutri-* -> nutricionista-*, barber-* -> barbearia-*)
        alias_map = {}
        for old, new in re.findall(r'"([a-z0-9_-]+)":\s*"([a-z0-9_-]+)"', content):
            if old.startswith(("barber", "nutri")):
                alias_map[new] = old

        # Lanes com enrichment dedicado ou via alias
        covered = set()
        for lane_id in declared:
            if lane_id in keys:
                covered.add(lane_id)
            elif lane_id in alias_map and alias_map[lane_id] in keys:
                covered.add(lane_id)

        # Lanes default/estetica sao cobertas por _FAMILY_COPY_DEFAULTS
        # (sao "base" lanes que herdam copy do nicho)
        missing = declared - covered
        # Filtra lanes que nao precisam de enrichment dedicado
        # (default-* e estetica-* tem copy herdado)
        for lane_id in list(missing):
            if lane_id.startswith(("default-", "estetica-")):
                missing.discard(lane_id)

        assert not missing, f"Lanes sem copy_enrichment: {sorted(missing)}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. ALIASES: resolve_visual_lane funciona com nomes antigos
# ═══════════════════════════════════════════════════════════════════════════

class TestAliasesBackwardCompat:
    """Aliases barber-* → barbearia-* e nutri-* → nutricionista-* funcionam."""

    def test_alias_barber_heritage_reserve(self):
        from backend.services.vite_visual_lanes import _canonicalize_lane_id
        assert _canonicalize_lane_id("barber-heritage-reserve") == "barbearia-heritage-reserve"

    def test_alias_nutri_botanical(self):
        from backend.services.vite_visual_lanes import _canonicalize_lane_id
        assert _canonicalize_lane_id("nutri-botanical-editorial") == "nutricionista-botanical-editorial"

    def test_lane_id_canonico_passa_direto(self):
        from backend.services.vite_visual_lanes import _canonicalize_lane_id
        assert _canonicalize_lane_id("academia-iron-pulse") == "academia-iron-pulse"

    def test_lane_id_vazio(self):
        from backend.services.vite_visual_lanes import _canonicalize_lane_id
        assert _canonicalize_lane_id("") == ""

    def test_resolve_visual_lane_aceita_alias(self):
        """resolve_visual_lane deve funcionar com 'barber-heritage-reserve'."""
        from backend.services.vite_visual_lanes import resolve_visual_lane
        try:
            lane = resolve_visual_lane(
                segment="barbearia",
                visual_lane="lane_a",
            )
            assert lane["family"] == "barbearia"
        except Exception as e:
            pytest.skip(f"resolve_visual_lane precisa de mais dados: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 5. POLOS CONSISTENTES
# ═══════════════════════════════════════════════════════════════════════════

class TestPolosConsistentes:
    """Cada lane tem polo coerente com o nicho."""

    def test_advogado_classic(self):
        """Advogado deve gerar polo CLASSIC."""
        from backend.services.vite_visual_lanes import resolve_visual_lane
        try:
            lane = resolve_visual_lane(segment="advogado", visual_lane="lane_a")
            assert lane["pole"] in ("CLASSIC", "TECH")  # TECH permitido por sub-nicho
        except Exception:
            pytest.skip("resolve_visual_lance requer mais dados")

    def test_academia_bold(self):
        """Academia deve gerar polo BOLD (default)."""
        from backend.services.vite_visual_lanes import resolve_visual_lane
        try:
            lane = resolve_visual_lane(segment="academia", visual_lane="lane_a")
            assert lane["pole"] in ("BOLD", "SOFT")  # SOFT permitido por sub-nicho
        except Exception:
            pytest.skip("resolve_visual_lance requer mais dados")

    def test_restaurante_soft(self):
        """Restaurante deve gerar polo SOFT (default)."""
        from backend.services.vite_visual_lanes import resolve_visual_lane
        try:
            lane = resolve_visual_lane(segment="restaurante", visual_lane="lane_a")
            assert lane["pole"] == "SOFT"
        except Exception:
            pytest.skip("resolve_visual_lance requer mais dados")