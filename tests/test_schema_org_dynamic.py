"""
============================================================================
TESTES: Schema.org dinâmico por nicho (Etapa 1.3)
============================================================================

Sprint 12.x: o JSON-LD injetado nos sites publicados deve usar o
schema_type correto por nicho, vindo de nicho_registry.get_schema_type().

Mapeamento esperado:
- advogado         -> "LegalService"
- restaurante      -> "Restaurant"
- clinica          -> "MedicalClinic"
- dentista         -> "Dentist"
- academia         -> "HealthClub"
- estetica         -> "BeautySalon"
- pet_shop         -> "PetStore"
- salao            -> "HairSalon"
- imobiliaria      -> "RealEstateAgent"
- nutricionista    -> "MedicalBusiness"
- energia_solar    -> "HomeAndConstructionBusiness"
- oficina          -> "AutoRepair"
- barbearia        -> "BarberShop"
- default / ???    -> "LocalBusiness"
============================================================================
"""

import json
import pytest
import sys
from pathlib import Path

# Adiciona o diretório backend ao sys.path para imports tipo `agents.*`
# (espelha o que conftest.py faz em modo padrão)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _PROJECT_ROOT / "backend"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════
# 1. REGISTRO: get_schema_type() funciona
# ═══════════════════════════════════════════════════════════════════════════

class TestGetSchemaType:
    """get_schema_type() do nicho_registry retorna o @type correto."""

    def test_advogado_retorna_legal_service(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("advogado") == "LegalService"

    def test_restaurante_retorna_restaurant(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("restaurante") == "Restaurant"

    def test_clinica_retorna_medical_clinic(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("clinica") == "MedicalClinic"

    def test_dentista_retorna_dentist(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("dentista") == "Dentist"

    def test_academia_retorna_health_club(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("academia") == "HealthClub"

    def test_estetica_retorna_beauty_salon(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("estetica") == "BeautySalon"

    def test_pet_shop_retorna_pet_store(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("pet_shop") == "PetStore"

    def test_salao_retorna_hair_salon(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("salao") == "HairSalon"

    def test_imobiliaria_retorna_real_estate(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("imobiliaria") == "RealEstateAgent"

    def test_nutricionista_retorna_medical_business(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("nutricionista") == "MedicalBusiness"

    def test_energia_solar_retorna_home_construction(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("energia_solar") == "HomeAndConstructionBusiness"

    def test_oficina_retorna_auto_repair(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("oficina") == "AutoRepair"

    def test_barbearia_retorna_barber_shop(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("barbearia") == "BarberShop"

    def test_desconhecido_retorna_local_business(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("nicho_inexistente_xyz") == "LocalBusiness"

    def test_none_retorna_local_business(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type(None) == "LocalBusiness"

    def test_vazio_retorna_local_business(self):
        from backend.config.nicho_registry import get_schema_type
        assert get_schema_type("") == "LocalBusiness"


# ═══════════════════════════════════════════════════════════════════════════
# 2. INTEGRAÇÃO: vite_templates._facts_json_ld() injeta schema correto
# ═══════════════════════════════════════════════════════════════════════════

class TestViteTemplatesSchemaDinamico:
    """_facts_json_ld de vite_templates injeta @type correto por nicho."""

    def _extract_type(self, json_ld_str: str) -> str:
        data = json.loads(json_ld_str)
        return data.get("@type", "")

    def test_advogado_gera_legal_service(self):
        from backend.services.vite_templates import _facts_json_ld
        facts = {
            "business": {
                "name": "Silva & Associados",
                "segment": "advogado",
                "city": "Sao Paulo",
            }
        }
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "LegalService"

    def test_restaurante_gera_restaurant(self):
        from backend.services.vite_templates import _facts_json_ld
        facts = {
            "business": {
                "name": "Cantina Bella",
                "segment": "restaurante",
            }
        }
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "Restaurant"

    def test_clinica_gera_medical_clinic(self):
        from backend.services.vite_templates import _facts_json_ld
        facts = {
            "business": {
                "name": "Clinica Vida",
                "segment": "clinica",
            }
        }
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "MedicalClinic"

    def test_academia_gera_health_club(self):
        from backend.services.vite_templates import _facts_json_ld
        facts = {
            "business": {
                "name": "Iron Gym",
                "segment": "academia",
            }
        }
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "HealthClub"

    def test_energia_solar_gera_home_construction(self):
        from backend.services.vite_templates import _facts_json_ld
        facts = {
            "business": {
                "name": "Sun Power",
                "segment": "energia_solar",
            }
        }
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "HomeAndConstructionBusiness"

    def test_facts_vazio_gera_local_business(self):
        from backend.services.vite_templates import _facts_json_ld
        out = _facts_json_ld({})
        assert self._extract_type(out) == "LocalBusiness"

    def test_segment_no_top_level_facts(self):
        """Facts com segmento no top-level (nao dentro de business) funciona."""
        from backend.services.vite_templates import _facts_json_ld
        facts = {"segmento": "dentista", "business": {"name": "Odonto"}}
        out = _facts_json_ld(facts)
        assert self._extract_type(out) == "Dentist"


# ═══════════════════════════════════════════════════════════════════════════
# 3. INTEGRAÇÃO: vite_facts._facts_json_ld() também usa registry
# ═══════════════════════════════════════════════════════════════════════════

class TestViteFactsSchemaDinamico:
    """_facts_json_ld de vite_facts também injeta @type correto."""

    def test_advogado_em_vite_facts(self):
        from backend.services.vite_facts import _facts_json_ld
        facts = {
            "business": {"name": "Mendes Direito", "segment": "advogado"},
            "city": "Curitiba",
        }
        out = _facts_json_ld(facts)
        data = json.loads(out)
        assert data["@type"] == "LegalService"

    def test_restaurante_em_vite_facts(self):
        from backend.services.vite_facts import _facts_json_ld
        facts = {
            "business": {"name": "Bistro Sul", "segment": "restaurante"},
            "city": "Porto Alegre",
        }
        out = _facts_json_ld(facts)
        data = json.loads(out)
        assert data["@type"] == "Restaurant"

    def test_default_em_vite_facts(self):
        from backend.services.vite_facts import _facts_json_ld
        facts = {"business": {"name": "X"}}
        out = _facts_json_ld(facts)
        data = json.loads(out)
        assert data["@type"] == "LocalBusiness"


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTEGRAÇÃO: vite_prompts._build_lead_briefing_block()
# ═══════════════════════════════════════════════════════════════════════════

class TestVitePromptsBriefingSchemaDinamico:
    """_build_lead_briefing_block injeta JSON-LD com @type correto."""

    def _extract_json_ld_type(self, block: str) -> str | None:
        """Extrai o @type do JSON-LD dentro do bloco de briefing."""
        import re
        m = re.search(r'"@type"\s*:\s*"([^"]+)"', block)
        return m.group(1) if m else None

    def test_briefing_advogado_tem_legal_service(self):
        from backend.services.vite_prompts import _build_lead_briefing_block
        facts = {
            "business": {
                "name": "Silva Direito",
                "segment": "advogado",
                "city": "Sao Paulo",
            }
        }
        block = _build_lead_briefing_block(facts)
        schema_type = self._extract_json_ld_type(block)
        assert schema_type == "LegalService", \
            f"Briefing advogado deve usar LegalService, got {schema_type}"

    def test_briefing_restaurante_tem_restaurant(self):
        from backend.services.vite_prompts import _build_lead_briefing_block
        facts = {
            "business": {
                "name": "Cantina Top",
                "segment": "restaurante",
                "city": "Rio",
            }
        }
        block = _build_lead_briefing_block(facts)
        schema_type = self._extract_json_ld_type(block)
        assert schema_type == "Restaurant"

    def test_briefing_dentista_tem_dentist(self):
        from backend.services.vite_prompts import _build_lead_briefing_block
        facts = {
            "business": {
                "name": "Sorriso",
                "segment": "dentista",
            }
        }
        block = _build_lead_briefing_block(facts)
        schema_type = self._extract_json_ld_type(block)
        assert schema_type == "Dentist"

    def test_briefing_sem_segmento_tem_local_business(self):
        from backend.services.vite_prompts import _build_lead_briefing_block
        facts = {"business": {"name": "Negocio X"}}
        block = _build_lead_briefing_block(facts)
        schema_type = self._extract_json_ld_type(block)
        assert schema_type == "LocalBusiness"


# ═══════════════════════════════════════════════════════════════════════════
# 5. INTEGRAÇÃO: site_build_plan.build_site_build_plan()
# ═══════════════════════════════════════════════════════════════════════════

class TestSiteBuildPlanSchemaDinamico:
    """build_site_build_plan injeta schema_type correto no seo_plan."""

    def test_seo_plan_advogado(self):
        from backend.agents.site_build_plan import build_site_build_plan
        facts = {
            "segmento": "advogado",
            "cidade": "BH",
            "business_name": "Escritorio X",
        }
        plan = build_site_build_plan(facts)
        assert plan["seo_plan"]["schema_type"] == "LegalService"

    def test_seo_plan_restaurante(self):
        from backend.agents.site_build_plan import build_site_build_plan
        facts = {
            "segmento": "restaurante",
            "business_name": "Rest Y",
        }
        plan = build_site_build_plan(facts)
        assert plan["seo_plan"]["schema_type"] == "Restaurant"

    def test_seo_plan_academia(self):
        from backend.agents.site_build_plan import build_site_build_plan
        facts = {
            "segmento": "academia",
            "business_name": "Gym Z",
        }
        plan = build_site_build_plan(facts)
        assert plan["seo_plan"]["schema_type"] == "HealthClub"

    def test_seo_plan_default(self):
        from backend.agents.site_build_plan import build_site_build_plan
        facts = {"business_name": "Generico"}
        plan = build_site_build_plan(facts)
        assert plan["seo_plan"]["schema_type"] == "LocalBusiness"

    def test_seo_plan_com_business_aninhado(self):
        """Aceita tambem formato {business: {segment: ...}}."""
        from backend.agents.site_build_plan import build_site_build_plan
        facts = {
            "business_name": "Pet X",
            "business": {"segment": "pet_shop"},
        }
        plan = build_site_build_plan(facts)
        assert plan["seo_plan"]["schema_type"] == "PetStore"


# ═══════════════════════════════════════════════════════════════════════════
# 6. IMUTABILIDADE: schema_type nunca é "LocalBusiness" hardcoded
#    exceto no fallback de nicho desconhecido
# ═══════════════════════════════════════════════════════════════════════════

class TestSemLocalBusinessHardcodedEmCodigo:
    """Os arquivos modificados não devem mais ter @type LocalBusiness hardcoded
    no caminho dinâmico (apenas como fallback de nicho desconhecido)."""

    def test_vite_templates_nao_tem_localbusiness_em_linha_de_tipo(self):
        """A string "@type": "LocalBusiness" não pode mais aparecer em
        vite_templates.py — deve vir do registry."""
        from pathlib import Path
        p = Path("backend/services/vite_templates.py")
        if not p.exists():
            pytest.skip("arquivo nao encontrado")
        content = p.read_text(encoding="utf-8")
        # Não pode mais ter a string literal hardcoded no schema dinâmico
        assert '"@type": "LocalBusiness"' not in content, (
            "vite_templates.py ainda tem @type LocalBusiness hardcoded"
        )

    def test_vite_facts_nao_tem_localbusiness_em_linha_de_tipo(self):
        from pathlib import Path
        p = Path("backend/services/vite_facts.py")
        if not p.exists():
            pytest.skip("arquivo nao encontrado")
        content = p.read_text(encoding="utf-8")
        assert '"@type": "LocalBusiness"' not in content

    def test_vite_prompts_nao_tem_localbusiness_em_linha_de_tipo(self):
        from pathlib import Path
        p = Path("backend/services/vite_prompts.py")
        if not p.exists():
            pytest.skip("arquivo nao encontrado")
        content = p.read_text(encoding="utf-8")
        # No caminho dinâmico do briefing não pode ter
        # (pode haver menção em comentário — verificar só o dict)
        assert '"@type": "LocalBusiness"' not in content, (
            "vite_prompts.py ainda tem @type LocalBusiness hardcoded no briefing"
        )

    def test_site_build_plan_nao_tem_schema_type_localbusiness_literal(self):
        from pathlib import Path
        p = Path("backend/agents/site_build_plan.py")
        if not p.exists():
            pytest.skip("arquivo nao encontrado")
        content = p.read_text(encoding="utf-8")
        # O literal "LocalBusiness" só pode aparecer dentro do fallback _schema_type_for
        # Não pode estar no corpo principal do build_site_build_plan
        assert '"schema_type": "LocalBusiness"' not in content, (
            "site_build_plan.py ainda tem schema_type LocalBusiness hardcoded"
        )
