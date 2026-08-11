import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
DesignerPRD - modelo/gerador legado de PRD.
O pipeline ativo usa Arquiteto Mestre + Skill Renderer.
"""
import re
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Dict, Any, Optional, Union
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
    name: str = "fade-in"
    type: str = "fade-in"
    target: str = "section"
    trigger: str = "scroll"
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

    name: Optional[str] = None
    id: Optional[str] = None
    required: bool = True
    layout_type: Optional[str] = None
    components: Optional[List[Union[str, Dict[str, Any]]]] = None
    copy_data: Optional[Dict[str, Any]] = Field(default=None, alias="copy")
    items: Optional[List[Any]] = None
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
    media_src: Optional[str] = None

    @model_validator(mode="after")
    def normalize_section(self) -> "SectionSpec":
        # Normaliza name: usa 'id' se name não vier
        if not self.name and self.id:
            self.name = str(self.id)
        if not self.name:
            self.name = "hero"

        # Normaliza components: aceita str, dict, ou lista mista
        if self.components is None:
            self.components = ["hero-cta"]
        else:
            cleaned = []
            for c in self.components:
                if isinstance(c, str):
                    cleaned.append(c)
                elif isinstance(c, dict):
                    cleaned.append(str(c.get("name", c.get("id", c.get("type", "component")))))
                else:
                    cleaned.append(str(c))
            self.components = cleaned

        # Normaliza copy_data
        if self.copy_data is None:
            self.copy_data = {}

        # Normaliza items
        if self.items is None:
            self.items = []

        # Normaliza schema_org
        if self.schema_org is not None and not isinstance(self.schema_org, str):
            if isinstance(self.schema_org, list):
                self.schema_org = self.schema_org[0] if self.schema_org else None
            elif isinstance(self.schema_org, dict):
                self.schema_org = self.schema_org.get("type", self.schema_org.get("name"))

        return self


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

    @model_validator(mode="after")
    def normalize_colors(self) -> "ColorPalette":
        color_fields = [
            ("primary", "#374151"),
            ("secondary", "#f9fafb"),
            ("accent", "#e85d04"),
            ("background", "#ffffff"),
            ("text", "#1f2937"),
            ("surface", "#f9fafb"),
            ("muted", "#6b7280"),
            ("border", "#e5e7eb"),
        ]
        for field_name, default in color_fields:
            val = getattr(self, field_name)
            if not val or not isinstance(val, str):
                setattr(self, field_name, default)
            elif isinstance(val, dict):
                setattr(self, field_name, str(val.get("hex", val.get("value", val.get("color", default)))))

        if not self.reasoning or not isinstance(self.reasoning, str):
            self.reasoning = "Paleta baseada no segmento"
        elif isinstance(self.reasoning, dict):
            self.reasoning = str(self.reasoning)

        return self


class DesignerPRD(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sections: List[SectionSpec] = Field(default_factory=list)
    color_palette: ColorPalette = Field(default_factory=ColorPalette)
    typography: Optional[Dict[str, Any]] = None
    design_system_slug: Optional[str] = None
    visual_dna: Dict[str, Any] = Field(default_factory=dict)
    layout_blueprint: List[Dict[str, Any]] = Field(default_factory=list)
    design_reference_pack: Dict[str, Any] = Field(default_factory=dict)
    dna_combo: Dict[str, Any] = Field(default_factory=dict)
    visual_seed: Optional[str] = None
    visual_direction: Dict[str, Any] = Field(default_factory=dict)
    minimum_required_media: Optional[int] = None
    visual_contract: Dict[str, Any] = Field(default_factory=dict)
    site_build_plan: Dict[str, Any] = Field(default_factory=dict)

    animations: List[AnimationSpec] = Field(default_factory=list)

    business_name: Optional[str] = None
    reviews_count: Optional[int] = None
    reviews_rating: Optional[float] = None
    reviews_list: Optional[List[Dict[str, Any]]] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[Dict[str, str]] = None
    photos: Optional[List[str]] = None
    videos: List[Dict[str, Any]] = Field(default_factory=list)
    logo_url: Optional[str] = None
    google_maps_embed: Optional[str] = None
    components_21dev: Optional[List[str]] = None
    cidade: Optional[str] = None
    segmento: Optional[str] = None
    instrucao_criativa_para_dev: Optional[str] = None
    jina_insights: Optional[str] = None
    servicos: Optional[list] = None
    atributos: Optional[list] = None
    horarios: Optional[dict] = None
    faixa_preco: Optional[str] = None
    competitor_analysis: Optional[str] = None
    anti_patterns: Optional[List[str]] = None
    schema_org_types: Optional[List[str]] = None
    seo_keywords: Optional[List[Union[str, Dict[str, Any]]]] = None
    faq_questions: Optional[List[Union[str, Dict[str, Any]]]] = None
    value_props: Optional[List[Union[str, Dict[str, Any]]]] = None
    geo: Optional[Dict[str, Any]] = None
    dark_mode: Optional[bool] = None

    @model_validator(mode="after")
    def fill_missing_fields(self) -> "DesignerPRD":
        """Normaliza dados sujos vindo da IA — aceita qualquer entrada."""
        # Sections: garantir que cada uma tem nome
        for i, sec in enumerate(self.sections):
            if not sec.name or not str(sec.name).strip():
                self.sections[i] = SectionSpec(
                    name=f"Secao {i+1}",
                    required=sec.required,
                    components=sec.components or [],
                    data_source=sec.data_source or "Hunter V2",
                    schema_org=sec.schema_org,
                )

        # Garantir arrays mínimos
        if not self.sections:
            self.sections = [
                SectionSpec(
                    name="Hero", required=True, components=["hero-cta"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Sobre", required=True, components=["about-text", "about-image"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Servicos", required=True, components=["services-grid"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Depoimentos", required=False, components=["reviews-list"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Planos", required=True, components=["pricing-cards"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Localizacao", required=True, components=["map-embed", "address-info"], data_source="Hunter V2",
                ),
                SectionSpec(
                    name="Contato", required=True, components=["contact-form", "whatsapp-cta"], data_source="Hunter V2",
                ),
            ]

        if not self.animations:
            self.animations = [
                AnimationSpec(
                    name="hero-fade", type="fade-in", target="hero", trigger="load",
                    duration="0.6s", easing="ease-out",
                )
            ]

        if not self.components_21dev:
            self.components_21dev = ["hero-cta"]
        if not self.schema_org_types:
            self.schema_org_types = ["LocalBusiness"]

        # Geo default
        if self.geo is None:
            self.geo = {"lat": 0.0, "lng": 0.0}
        elif isinstance(self.geo, dict):
            self.geo.setdefault("lat", self.geo.get("latitude", self.geo.get("lat", 0.0)))
            self.geo.setdefault("lng", self.geo.get("longitude", self.geo.get("lng", 0.0)))

        # Dark mode default
        if self.dark_mode is None:
            self.dark_mode = False

        # Normalize list fields: se veio dict em vez de str, extrair valor textual
        if self.faq_questions:
            cleaned = []
            for item in self.faq_questions:
                if isinstance(item, str):
                    cleaned.append(item)
                elif isinstance(item, dict):
                    cleaned.append(str(item.get("question", item.get("text", str(item)))))
            self.faq_questions = cleaned

        if self.value_props:
            cleaned = []
            for item in self.value_props:
                if isinstance(item, str):
                    cleaned.append(item)
                elif isinstance(item, dict):
                    cleaned.append(str(item.get("title", item.get("prop", item.get("text", str(item))))))
            self.value_props = cleaned

        if self.seo_keywords:
            cleaned = []
            for item in self.seo_keywords:
                if isinstance(item, str):
                    cleaned.append(item)
                elif isinstance(item, dict):
                    cleaned.append(str(item.get("keyword", item.get("term", item.get("text", str(item))))))
            self.seo_keywords = cleaned

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
