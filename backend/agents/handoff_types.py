from pydantic import BaseModel, Field


class HandoffBase(BaseModel):
    task_id: str = ""
    source_agent: str = ""
    target_agent: str = ""
    status: str = "ok"
    task_summary: str = ""


class NichoBriefing(HandoffBase):
    nicho: str = ""
    subnichos: list[str] = Field(default_factory=list)
    cidade: str = ""
    publico_alvo: list[str] = Field(default_factory=list)
    usp: list[str] = Field(default_factory=list)
    diferenciais: list[str] = Field(default_factory=list)
    objeções: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    tom_de_voz: str = ""
    notas: str = ""
    confianca: str = "media"
    dados_ausentes: list[str] = Field(default_factory=list)
    competidores: list[str] = Field(default_factory=list)
    regras: list[str] = Field(default_factory=list)
    nao_fazer: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["## Briefing de Nicho", f"**Nicho:** {self.nicho}"]
        if self.subnichos:
            lines.append(f"**Subnichos:** {', '.join(self.subnichos)}")
        if self.cidade:
            lines.append(f"**Cidade:** {self.cidade}")
        if self.publico_alvo:
            lines.append(f"**Público-alvo:** {', '.join(self.publico_alvo)}")
        if self.usp:
            lines.append(f"**USP:** {', '.join(self.usp)}")
        if self.diferenciais:
            lines.append(f"**Diferenciais:** {', '.join(self.diferenciais)}")
        if self.objeções:
            lines.append(f"**Objeções:** {', '.join(self.objeções)}")
        if self.keywords:
            lines.append(f"**Keywords:** {', '.join(self.keywords)}")
        if self.tom_de_voz:
            lines.append(f"**Tom de voz:** {self.tom_de_voz}")
        if self.notas:
            lines.append(f"**Notas:** {self.notas}")
        if self.dados_ausentes:
            lines.append(f"**Dados ausentes:** {', '.join(self.dados_ausentes)}")
        if self.competidores:
            lines.append(f"**Competidores analisados:** {', '.join(self.competidores)}")
        return "\n".join(lines)


class VariacaoEstrutural(HandoffBase):
    template_estrutura: str = ""
    template_hero: str = ""
    template_prova_social: str = ""
    template_cta: str = ""
    template_faq: str = ""
    ordem_das_secoes: list[str] = Field(default_factory=list)
    angulo_de_comunicacao: str = ""
    regra_antirrepeticao: str = ""
    justificativa: str = ""
    layout_variants: dict = Field(default_factory=dict)
    rhythm: str = ""
    signature_composition: str = ""
    avoid: list[str] = Field(default_factory=list)


class CreativeDirectionContract(HandoffBase):
    brand_concept: str = ""
    audience: str = ""
    positioning: str = ""
    commercial_thesis: str = ""
    visual_concept: str = ""
    visual_keywords: list[str] = Field(default_factory=list)
    physical_scene: str = ""
    color_strategy: dict = Field(default_factory=dict)
    typography_strategy: dict = Field(default_factory=dict)
    photography_strategy: dict = Field(default_factory=dict)
    composition_strategy: str = ""
    density_strategy: str = ""
    rhythm_strategy: str = ""
    hero_strategy: str = ""
    cta_strategy: str = ""
    signature_section: str = ""
    anti_patterns: list[str] = Field(default_factory=list)
    required_visual_differences: list[str] = Field(default_factory=list)
    hard_constraints: dict = Field(default_factory=dict)
    soft_constraints: dict = Field(default_factory=dict)


class MediaPlanItem(BaseModel):
    url: str = ""
    role: str = ""
    section: str = ""
    required: bool = False
    source: str = ""
    alt: str = ""


class VisualCustodyRecord(BaseModel):
    stage: str
    received_decisions: dict = Field(default_factory=dict)
    preserved_decisions: dict = Field(default_factory=dict)
    changed_decisions: dict = Field(default_factory=dict)
    lost_decisions: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ValidacaoResultado(HandoffBase):
    aprovado: bool = False
    problemas: list[str] = Field(default_factory=list)
    prioridade: list[str] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)
    correcoes_sugeridas: list[str] = Field(default_factory=list)
