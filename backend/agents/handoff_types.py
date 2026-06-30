from pydantic import BaseModel, Field
from typing import Dict


class HandoffBase(BaseModel):
    task_id: str = ""
    source_agent: str = ""
    target_agent: str = ""
    status: str = "ok"
    task_summary: str = ""


class NichoBriefing(HandoffBase):
    nicho: str = ""
    subnichos: list[str] = Field(default_factory=list)
    subnicho: str = ""  # canonico (ex: "nutricionista_esportiva") usado por agente_variacao
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
    # Sprint 14.x: cores extraídas do briefing livre
    paleta_cores: Dict[str, str] = Field(default_factory=dict)
    # Sprint 14.x: referências visuais do usuário (ex: "Quero um site como Nubank")
    refs_visuais: str = ""
    # Sprint 14.x: preferência de fonte (sans-serif, serif, display, monospace)
    font_preferencia: str = ""

    def to_markdown(self) -> str:
        lines = ["## Briefing de Nicho", f"**Nicho:** {self.nicho}"]
        if self.subnicho:
            lines.append(f"**Subnicho canonico:** {self.subnicho}")
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
        if self.refs_visuais:
            lines.append(f"**Referências visuais:** {self.refs_visuais}")
        if self.font_preferencia:
            lines.append(f"**Preferência de fonte:** {self.font_preferencia}")
        if self.dados_ausentes:
            lines.append(f"**Dados ausentes:** {', '.join(self.dados_ausentes)}")
        if self.competidores:
            lines.append(f"**Competidores analisados:** {', '.join(self.competidores)}")
        return "\n".join(lines)


class VariacaoEstrutural(HandoffBase):
    subnicho: str = ""
    template_estrutura: str = ""
    template_hero: str = ""
    template_prova_social: str = ""
    template_cta: str = ""
    template_faq: str = ""
    ordem_das_secoes: list[str] = Field(default_factory=list)
    angulo_de_comunicacao: str = ""
    regra_antirrepeticao: str = ""
    justificativa: str = ""
    # Sprint 16: variation seed completo (hero_layout, motion_style, copy_voice, etc)
    # Usado pelo vite_react_renderer para gerar CSS único por lead
    variation: Dict = Field(default_factory=dict)


class ValidacaoResultado(HandoffBase):
    aprovado: bool = False
    score: float = 0.0  # 0-10 LLM-as-judge (>=7 = aprovado)
    problemas: list[str] = Field(default_factory=list)
    prioridade: list[str] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)
    correcoes_sugeridas: list[str] = Field(default_factory=list)
