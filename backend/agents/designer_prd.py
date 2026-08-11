import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
DesignerPRD - modelo/gerador legado de PRD.
O pipeline ativo usa Arquiteto Mestre + Skill Renderer.
"""
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from typing import List, Dict, Any, Optional
from llm_direct import call_claude_structured
from agent_rag import format_rag_prompt, get_agent_temperature
from validation_enforcer import (
    require_rag,
    require_guidelines,
)  # ✅ Validação obrigatória

# # from prompt_templates import formatar_prompt_designer
from design_guidelines import ANIMATION_PRINCIPLES, ANIMATION_CSS


def clean_json_response(text: str) -> str:
    """Remove markdown code blocks e extrai JSON válido (versão blindada)"""

    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    # Regex robusto para extrair JSON (suporta nested objects)
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


# ===== MODELOS PYDANTIC =====


class AnimationSpec(BaseModel):
    name: str
    type: str
    target: str
    trigger: str
    duration: Optional[str] = "0.6s"
    easing: Optional[str] = "ease-out"

    @classmethod
    def from_any(cls, data) -> "AnimationSpec":
        """Normaliza qualquer formato de animacao para AnimationSpec."""
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            return cls(name=data, type="fade-in", target="section", trigger="scroll")
        if isinstance(data, dict):
            return cls(
                name=str(
                    data.get("name", data.get("id", data.get("animation", "fade-in")))
                ),
                type=str(
                    data.get(
                        "type",
                        data.get("animation_type", data.get("effect", "fade-in")),
                    )
                ),
                target=str(
                    data.get(
                        "target", data.get("element", data.get("selector", "section"))
                    )
                ),
                trigger=str(data.get("trigger", data.get("event", "scroll"))),
                duration=str(data.get("duration", data.get("timing", "0.6s"))),
                easing=str(data.get("easing", data.get("ease", "ease-out"))),
            )
        return cls(name="fade-in", type="fade-in", target="section", trigger="scroll")


class SectionSpec(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    required: bool = True
    layout_type: Optional[str] = None
    components: List[str] = Field(default_factory=list)
    copy_data: Dict[str, Any] = Field(default_factory=dict, alias="copy")
    items: List[Any] = Field(default_factory=list)
    cta: Optional[str] = None
    h1: Optional[str] = None
    h2: Optional[str] = None
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    objective: Optional[str] = None
    media_role: Optional[str] = None
    omitir: bool = False
    data_source: str = "Hunter V2"
    schema_org: Optional[str] = None

    @field_validator("schema_org", mode="before")
    @classmethod
    def normalize_schema_org_field(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return v[0] if v else None
        if isinstance(v, dict):
            return v.get("type", v.get("name", str(v)))
        return str(v)

    @field_validator("components", mode="before")
    @classmethod
    def normalize_components(cls, v):
        if not isinstance(v, list):
            return []
        return [str(c) if not isinstance(c, str) else c for c in v]

    @field_validator("copy_data", mode="before")
    @classmethod
    def normalize_copy(cls, v):
        return v if isinstance(v, dict) else {}

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [item.strip() for item in v.split(";") if item.strip()]
        return []

    @field_validator("required", mode="before")
    @classmethod
    def normalize_required(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "no")
        return True

    @field_validator("omitir", mode="before")
    @classmethod
    def normalize_omitir(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "sim")
        return False

    @field_validator("data_source", mode="before")
    @classmethod
    def normalize_data_source(cls, v):
        if not v or not isinstance(v, str):
            return "Hunter V2"
        return str(v)


class ColorPalette(BaseModel):
    primary: str = "#374151"
    secondary: str = "#f9fafb"
    accent: str = "#e85d04"
    background: str = "#ffffff"
    text: str = "#1f2937"
    surface: str = "#f9fafb"
    muted: str = "#6b7280"
    border: str = "#e5e7eb"
    tokens_oklch: dict = {}
    hero_style: dict = {}
    reasoning: str = "Paleta padrao"

    @field_validator(
        "primary", "secondary", "accent", "background", "text", mode="before"
    )
    @classmethod
    def normalize_color(cls, v):
        if not v or not isinstance(v, str):
            return "#374151"
        if isinstance(v, dict):
            return str(v.get("hex", v.get("value", v.get("color", "#374151"))))
        return str(v)

    @field_validator("reasoning", mode="before")
    @classmethod
    def normalize_reasoning(cls, v):
        if not v:
            return "Paleta baseada no segmento"
        if isinstance(v, dict):
            return str(v)
        return str(v)


class DesignerPRD(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sections: List[SectionSpec]

    @field_validator("sections", mode="before")
    @classmethod
    def normalize_sections(cls, v):
        if isinstance(v, dict):
            # Claude retornou {"hero": {...}, "sobre": {...}} em vez de lista
            result = []
            for key, val in v.items():
                if isinstance(val, dict):
                    val.setdefault("name", val.get("id", key).capitalize())
                    val.setdefault("required", True)
                    val.setdefault("components", ["cta"])
                    val.setdefault("data_source", "Claude")
                    result.append(val)
                elif isinstance(val, str):
                    result.append(
                        {
                            "name": key.capitalize(),
                            "required": True,
                            "components": ["cta"],
                            "data_source": val,
                        }
                    )
            return (
                result
                if result
                else [
                    {
                        "name": "Hero",
                        "required": True,
                        "components": ["hero-cta"],
                        "data_source": "Fallback",
                    }
                ]
            )
        if not isinstance(v, list):
            return [
                {
                    "name": "Hero",
                    "required": True,
                    "components": ["hero-cta"],
                    "data_source": "Fallback",
                }
            ]
        # Normalizar schema_org em cada item da lista
        for item in v:
            if isinstance(item, dict) and "schema_org" in item:
                so = item["schema_org"]
                if isinstance(so, dict):
                    item["schema_org"] = so.get("type", so.get("name", str(so)))
                elif isinstance(so, list):
                    item["schema_org"] = so[0] if so else None
        return v

    color_palette: ColorPalette
    typography: Dict[str, Any]
    design_system_slug: Optional[str] = None
    visual_dna: Dict[str, Any] = Field(default_factory=dict)
    layout_blueprint: List[Dict[str, Any]] = Field(default_factory=list)
    design_reference_pack: Dict[str, Any] = Field(default_factory=dict)
    dna_combo: Dict[str, Any] = Field(default_factory=dict)
    visual_seed: str = ""
    visual_direction: Dict[str, Any] = Field(default_factory=dict)
    minimum_required_media: Optional[int] = None
    requirements_contract: Dict[str, Any] = Field(default_factory=dict)
    visual_contract: Dict[str, Any] = Field(default_factory=dict)
    site_build_plan: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("typography", mode="before")
    @classmethod
    def normalize_typography(cls, v):
        """
        Normaliza estruturas de tipografia aninhadas para formato simples.

        Aceita:
        - Formato simples: {"heading": "Inter", "body": "Roboto"}
        - Formato aninhado: {"heading": {"family": "Inter", "weight": "700"}}

        Retorna sempre formato simples: {"heading": "Inter", "body": "Roboto"}
        """
        if not isinstance(v, dict):
            return {"heading": "Inter", "body": "Inter", "accent": "Inter"}

        normalized = {}
        for key, value in v.items():
            if isinstance(value, dict):
                # Extrair 'family' de estrutura aninhada
                normalized[key] = value.get("family", value.get("name", "Inter"))
            elif isinstance(value, str):
                # Já está no formato simples
                normalized[key] = value
            else:
                # Fallback
                normalized[key] = "Inter"

        # Garantir campos obrigatórios
        for required_key in ["heading", "body", "accent"]:
            if required_key not in normalized:
                normalized[required_key] = "Inter"

        return normalized

    animations: List[AnimationSpec]

    @field_validator("animations", mode="before")
    @classmethod
    def normalize_animations(cls, v):
        """Normaliza animacoes em qualquer formato para List[AnimationSpec]."""
        if not isinstance(v, list):
            return [
                {
                    "name": "fade-in",
                    "type": "fade-in",
                    "target": "section",
                    "trigger": "scroll",
                }
            ]
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(
                    {
                        "name": str(
                            item.get(
                                "name", item.get("id", item.get("animation", "fade-in"))
                            )
                        ),
                        "type": str(
                            item.get(
                                "type",
                                item.get(
                                    "animation_type",
                                    item.get("effect", item.get("kind", "fade-in")),
                                ),
                            )
                        ),
                        "target": str(
                            item.get(
                                "target",
                                item.get(
                                    "element",
                                    item.get(
                                        "selector", item.get("applies_to", "section")
                                    ),
                                ),
                            )
                        ),
                        "trigger": str(
                            item.get(
                                "trigger", item.get("event", item.get("on", "scroll"))
                            )
                        ),
                        "duration": str(
                            item.get("duration", item.get("timing", "0.6s"))
                        ),
                        "easing": str(item.get("easing", item.get("ease", "ease-out"))),
                    }
                )
            elif isinstance(item, str):
                result.append(
                    {
                        "name": item,
                        "type": "fade-in",
                        "target": "section",
                        "trigger": "scroll",
                    }
                )
        if not result:
            result = [
                {
                    "name": "fade-in",
                    "type": "fade-in",
                    "target": "section",
                    "trigger": "scroll",
                }
            ]
        return result

    business_name: str

    @field_validator("business_name", mode="before")
    @classmethod
    def normalize_business_name(cls, v):
        if not v or not str(v).strip():
            return "Negócio Local"
        return str(v).strip()

    reviews_count: int = Field(ge=0)

    @field_validator("reviews_count", mode="before")
    @classmethod
    def normalize_reviews_count(cls, v):
        if v is None:
            return 0
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    reviews_rating: float = Field(ge=0, le=5)

    @field_validator("reviews_rating", mode="before")
    @classmethod
    def normalize_reviews_rating(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    reviews_list: List[Dict[str, Any]]

    @field_validator("reviews_list", mode="before")
    @classmethod
    def normalize_reviews_list(cls, v):
        if not isinstance(v, list):
            return []
        return [r for r in v if isinstance(r, dict) and r]

    address: str

    @field_validator("address", mode="before")
    @classmethod
    def normalize_address(cls, v):
        if not v or not str(v).strip():
            return ""
        return str(v).strip()

    phone: str

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if not v or not str(v).strip():
            return ""
        return str(v).strip()

    hours: Optional[Dict[str, str]] = None
    photos: List[str] = Field(default_factory=list)
    videos: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("photos", mode="before")
    @classmethod
    def normalize_photos(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(str(item.get("url", item.get("src", ""))))
            else:
                result.append(str(item))
        return [x for x in result if x]

    logo_url: Optional[str] = None
    google_maps_embed: str

    @field_validator("google_maps_embed", mode="before")
    @classmethod
    def normalize_google_maps_embed(cls, v):
        if not v or not str(v).strip():
            return ""
        return str(v).strip()

    components_21dev: List[str]

    @field_validator("components_21dev", mode="before")
    @classmethod
    def normalize_components_21dev(cls, v):
        if not isinstance(v, list):
            return ["hero-cta"]
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    str(
                        item.get(
                            "id", item.get("name", item.get("component", str(item)))
                        )
                    )
                )
            else:
                result.append(str(item))
        return result if result else ["hero-cta"]

    cidade: str = ""
    segmento: str = ""
    instrucao_criativa_para_dev: str = (
        "Crie um layout moderno e responsivo com Tailwind."
    )
    jina_insights: str = ""
    # Dados reais do Hunter — passados intactos para o gerador HTML
    servicos: list = []
    atributos: list = []
    horarios: dict = {}
    faixa_preco: str = ""

    @field_validator("jina_insights", mode="before")
    @classmethod
    def normalize_jina_insights(cls, v):
        if not v:
            return ""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return v.get("summary", v.get("insights", v.get("content", str(v))))
        return str(v)

    competitor_analysis: str = ""

    @field_validator("competitor_analysis", mode="before")
    @classmethod
    def normalize_competitor_analysis(cls, v):
        if not v:
            return ""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return str(v.get("summary", str(v)))
        return str(v)

    anti_patterns: List[str]

    @field_validator("anti_patterns", mode="before")
    @classmethod
    def normalize_anti_patterns(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    str(
                        item.get(
                            "pattern",
                            item.get("name", item.get("description", str(item))),
                        )
                    )
                )
            else:
                result.append(str(item))
        return result

    schema_org_types: List[str]

    @field_validator("schema_org_types", mode="before")
    @classmethod
    def normalize_schema_org(cls, v):
        if not isinstance(v, list):
            return ["LocalBusiness"]
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(str(item.get("type", item.get("name", "LocalBusiness"))))
            else:
                result.append(str(item))
        return result if result else ["LocalBusiness"]

    seo_keywords: Optional[List[str]] = Field(default_factory=list)

    @field_validator("seo_keywords", mode="before")
    @classmethod
    def normalize_seo_keywords(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    str(
                        item.get(
                            "keyword",
                            item.get("term", item.get("text", str(item))),
                        )
                    )
                )
            else:
                result.append(str(item))
        return result

    faq_questions: Optional[List[str]] = Field(default_factory=list)

    @field_validator("faq_questions", mode="before")
    @classmethod
    def normalize_faq_questions(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    str(
                        item.get(
                            "question",
                            item.get("text", item.get("q", str(item))),
                        )
                    )
                )
            else:
                result.append(str(item))
        return result

    value_props: Optional[List[str]] = Field(default_factory=list)

    @field_validator("value_props", mode="before")
    @classmethod
    def normalize_value_props(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    str(
                        item.get(
                            "prop",
                            item.get("text", item.get("value", str(item))),
                        )
                    )
                )
            else:
                result.append(str(item))
        return result

    geo: Optional[Dict[str, float]] = None
    dark_mode: bool = False

    @model_validator(mode="after")
    def fill_missing_fields(self) -> "DesignerPRD":
        """Preenche campos obrigatórios faltantes com fallback"""
        # Fallback para sections
        if not self.sections:
            self.sections = [
                SectionSpec(
                    name="Hero",
                    required=True,
                    components=["hero-cta"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Sobre",
                    required=True,
                    components=["about-text", "about-image"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Servicos",
                    required=True,
                    components=["services-grid"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Depoimentos",
                    required=False,
                    components=["reviews-list"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Planos",
                    required=True,
                    components=["pricing-cards"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Localizacao",
                    required=True,
                    components=["map-embed", "address-info"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Contato",
                    required=True,
                    components=["contact-form", "whatsapp-cta"],
                    data_source="Hunter V2",
                ),
            ]

        # Fallback para animations
        if not self.animations:
            self.animations = [
                AnimationSpec(
                    name="hero-fade",
                    type="fade-in",
                    target="hero",
                    trigger="load",
                    duration="0.6s",
                    easing="ease-out",
                )
            ]

        # Fallback para components_21dev
        if not self.components_21dev:
            self.components_21dev = ["hero-cta"]

        # Fallback para schema_org_types
        if not self.schema_org_types:
            self.schema_org_types = ["LocalBusiness"]

        return self


# ===== INSTRUÇÕES DO AGENTE =====

DESIGNER_INSTRUCTIONS = """You are the PRD Designer, specialist in creating detailed PRDs for websites.

TASK:
Generate a complete PRD in JSON with:

1. Textual wireframe (sections)
2. Unique color palette (anti-pattern from competitors)
3. 5 specific animations (parallax, fade-in, hover, scroll-reveal, pulse)
4. Validated data (exact reviews_count, not approximations like "2+")
5. Google Maps embed URL
6. Required 21dev components
7. Mandatory Schema.org

OUTPUT FORMAT JSON:
{
  "sections": [
    {"name": "Hero", "required": true, "components": ["hero-cta"], "data_source": "Hunter V2", "schema_org": "LocalBusiness"}
  ],
  "color_palette": {
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "text": "#hex",
    "reasoning": "Why this palette"
  },
  "typography": {"heading": "font-name", "body": "font-name", "accent": "font-name"},
  "animations": [
    {"name": "hero-fade", "type": "fade-in", "target": "hero", "trigger": "load", "duration": "0.6s", "easing": "ease-out"}
  ],
  "business_name": "Business name",
  "reviews_count": 120,
  "reviews_rating": 4.8,
  "reviews_list": [{"autor": "Name", "texto": "Review", "rating": 5}],
  "address": "Full address",
  "phone": "Phone"
}

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""


# ===== FUNÇÃO PRINCIPAL =====


@require_rag("Designer PRD")  # ✅ Validação obrigatória de RAG
@require_guidelines("Designer PRD")  # ✅ Validação obrigatória de Guidelines
def gerar_prd(
    briefing_theo: str, dados_hunter: Dict[str, Any], cidade: str, segmento: str
) -> DesignerPRD:
    """
    Gera PRD detalhado para o gerador HTML implementar
    """
    print(f"\n[Designer PRD] Gerando PRD para {dados_hunter.get('nome', 'negócio')}...")

    # Formatar reviews
    reviews_texto = "\n".join(
        [
            f'- {r.get("autor", "Anônimo")}: "{r.get("texto", "")}" ({r.get("rating", 5)}★)'
            for r in dados_hunter.get("reviews", [])[:5]
        ]
    )

    # Montar prompt
    user_prompt = f"""
# ⚡ ANIMATION PRINCIPLES (OBRIGATÓRIO - SEGUIR EXATAMENTE)

{ANIMATION_PRINCIPLES}

# 🎨 ANIMATION CSS (USAR ESTES PADRÕES)

{ANIMATION_CSS}

---

# 📋 SUA TAREFA

Gere um PRD completo para o site de: {dados_hunter.get("nome", "negócio")}

**BRIEFING ESTRATÉGICO:**
{briefing_theo}

**DADOS REAIS (Hunter V2):**
- Nome: {dados_hunter.get("nome")}
- Cidade: {cidade}
- Segmento: {segmento}
- Telefone: {dados_hunter.get("telefone")}
- Rating: {dados_hunter.get("rating")}/5
- Total de avaliações: {dados_hunter.get("total_avaliacoes")}
- Reviews: {len(dados_hunter.get("reviews", []))} capturadas
- Endereço: {dados_hunter.get("endereco")}
- Logo: {"Sim" if dados_hunter.get("logo_url") else "Não"}
- Website: {dados_hunter.get("website", "Não tem")}

**REVIEWS REAIS:**
{reviews_texto}

**GUARDRAILS CRITICOS:**
- NUNCA incluir precos, valores, mensalidades ou tabelas de preco
- Usar sempre: Consulte valores, Solicite orcamento, Fale conosco
- Respeitar MODO VISUAL do briefing (DARK ou LIGHT)
- Usar paleta de cores do briefing, nao inventar cores genericas

Retorne PRD estruturado em JSON.
"""

    # Log de confirmacao
    print("[Designer PRD] Design Guidelines injetadas:")
    print(f"  - ANIMATION_PRINCIPLES: {len(ANIMATION_PRINCIPLES)} chars")
    print(f"  - ANIMATION_CSS: {len(ANIMATION_CSS)} chars")

    PRD_SCHEMA = {
        "type": "object",
        "required": [
            "sections",
            "color_palette",
            "typography",
            "animations",
            "business_name",
            "reviews_count",
            "reviews_rating",
            "reviews_list",
            "address",
            "phone",
            "google_maps_embed",
            "components_21dev",
            "competitor_analysis",
            "anti_patterns",
            "schema_org_types",
        ],
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "required", "components", "data_source"],
                    "properties": {
                        "name": {"type": "string"},
                        "required": {"type": "boolean"},
                        "components": {"type": "array", "items": {"type": "string"}},
                        "data_source": {"type": "string"},
                        "schema_org": {"type": "string"},
                    },
                },
            },
            "color_palette": {
                "type": "object",
                "required": [
                    "primary",
                    "secondary",
                    "accent",
                    "background",
                    "text",
                    "reasoning",
                ],
                "properties": {
                    "primary": {"type": "string"},
                    "secondary": {"type": "string"},
                    "accent": {"type": "string"},
                    "background": {"type": "string"},
                    "text": {"type": "string"},
                    "reasoning": {"type": "string"},
                },
            },
            "typography": {
                "type": "object",
                "required": ["heading", "body", "accent"],
                "properties": {
                    "heading": {"type": "string"},
                    "body": {"type": "string"},
                    "accent": {"type": "string"},
                },
            },
            "animations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "type", "target", "trigger"],
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "target": {"type": "string"},
                        "trigger": {"type": "string"},
                        "duration": {"type": "string"},
                        "easing": {"type": "string"},
                    },
                },
            },
            "business_name": {"type": "string"},
            "reviews_count": {"type": "integer"},
            "reviews_rating": {"type": "number"},
            "reviews_list": {"type": "array", "items": {"type": "object"}},
            "address": {"type": "string"},
            "phone": {"type": "string"},
            "hours": {"type": "object"},
            "logo_url": {"type": "string"},
            "google_maps_embed": {"type": "string"},
            "components_21dev": {"type": "array", "items": {"type": "string"}},
            "competitor_analysis": {"type": "string"},
            "anti_patterns": {"type": "array", "items": {"type": "string"}},
            "schema_org_types": {"type": "array", "items": {"type": "string"}},
        },
    }

    try:
        full_prompt = format_rag_prompt("designer_prd", user_prompt)
        temperature = get_agent_temperature("designer_prd")
        print(f"[Designer PRD] Usando temperature={temperature} (Structured Outputs)")

        response_json = call_claude_structured(
            system=DESIGNER_INSTRUCTIONS,
            user=full_prompt,
            tool_name="gerar_prd",
            tool_description="Gera PRD completo e estruturado para site de negocio local",
            input_schema=PRD_SCHEMA,
            model="opus",
            max_tokens=8000,
            temperature=temperature,
            agent_name="designer_prd",
        )
        print(
            f"[Designer PRD] Structured Output recebido: {list(response_json.keys())[:5]}..."
        )

        prd = DesignerPRD(**response_json)
        prd.cidade = cidade
        prd.segmento = segmento
        print(
            f"[Designer PRD] PRD gerado: {len(prd.sections)} secoes, {len(prd.animations)} animacoes"
        )
        return prd

    except Exception as e:
        print(f"[Designer PRD] Erro ao gerar PRD: {e}")
        # Fallback
        return DesignerPRD(
            sections=[
                SectionSpec(
                    name="Hero",
                    required=True,
                    components=["hero-cta"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Sobre",
                    required=True,
                    components=["about-text", "about-image"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Servicos",
                    required=True,
                    components=["services-grid"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Depoimentos",
                    required=False,
                    components=["reviews-list"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Planos",
                    required=True,
                    components=["pricing-cards"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Localizacao",
                    required=True,
                    components=["map-embed", "address-info"],
                    data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Contato",
                    required=True,
                    components=["contact-form", "whatsapp-cta"],
                    data_source="Hunter V2",
                ),
            ],
            color_palette=ColorPalette(
                primary="#374151",
                secondary="#f9fafb",
                accent="#a855f7",
                background="#ffffff",
                text="#1f2937",
                reasoning="Paleta neutra fallback (erro ao gerar PRD)",
            ),
            typography={"heading": "Inter", "body": "Inter", "accent": "Inter"},
            animations=[
                AnimationSpec(
                    name="hero-fade",
                    type="fade-in",
                    target="hero",
                    trigger="load",
                    duration="0.6s",
                    easing="ease-out",
                )
            ],
            business_name=dados_hunter.get("nome", "Negócio"),
            reviews_count=dados_hunter.get("total_avaliacoes", 0),
            reviews_rating=dados_hunter.get("rating", 0),
            reviews_list=dados_hunter.get("reviews", [])[:5],
            address=dados_hunter.get("endereco", ""),
            phone=dados_hunter.get("telefone", ""),
            photos=[],
            videos=dados_hunter.get("videos", []),
            logo_url=dados_hunter.get("logo_url"),
            google_maps_embed="",
            components_21dev=["hero-cta"],
            competitor_analysis="Erro ao gerar análise",
            anti_patterns=[],
            schema_org_types=["LocalBusiness"],
        )
