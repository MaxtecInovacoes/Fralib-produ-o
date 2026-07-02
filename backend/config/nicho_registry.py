"""
============================================================================
FRA LIB - NICHO REGISTRY (Fonte Única de Verdade)
============================================================================
Consolidação de configuração por nicho: schema_type, modal_config, faq,
hero_headlines, copy_defaults, polo_sugerido, lanes, design_logic,
sub_nicho_overrides.

OBJETIVO: eliminar fragmentação entre:
- backend/services/vite_prompts.py (NICHO_MODAL_CONFIG)
- backend/services/vite_visual_lanes.py (_LANES, _FAMILY_COPY_DEFAULTS)
- backend/agents/seo_context.py (SEO_NICHOS)
- backend/agents/arquiteto_mestre.py (fallbacks hardcoded)
- backend/services/vite_react_renderer.py (_ARCHETYPE_SEGMENTS)

CAMADAS:
  1. Tipo (schema.org)
  2. Polo sugerido (SOFT/BOLD/CLASSIC/TECH)
  3. Lanes disponíveis
  4. Modal de booking (title/cta/fields)
  5. FAQ por nicho
  6. Hero headlines por polo
  7. Copy defaults (tone/voice/cta)
  8. Design DNA (DesignLogic: radius/spacing/overlap/skew)
  9. SEO keywords
  10. Sub-nicho overrides (infantil→SOFT, atleta→BOLD, etc.)

Regras:
- Adicionar um nicho novo = 1 arquivo, 1 entry
- Tudo que é nicho-específico vive aqui
- Imutável (frozen=True) para evitar mutação acidental
- Type hints em todas as funções

============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# TYPES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ModalConfig:
    """Configuração do BookingModal por nicho."""
    title: str
    cta_button: str
    fields: tuple[str, ...]
    submit_action: str


@dataclass(frozen=True)
class HeroHeadlines:
    """Templates de headline do hero por polo."""
    SOFT: str = ""
    BOLD: str = ""
    CLASSIC: str = ""
    TECH: str = ""


@dataclass(frozen=True)
class CopyDefaults:
    """Defaults de tom de voz por nicho."""
    tone: str  # ex: "acolhedor", "agressivo", "sério"
    voice: str  # ex: "2a pessoa singular", "2a pessoa plural"
    cta_primary: str  # ex: "Falar no WhatsApp"


@dataclass(frozen=True)
class DesignLogic:
    """
    Regras geométricas do NichoConfig — DNA estrutural do nicho.

    Multiplicadores que sobrescrevem os tokens absolutos do POLO_TOKENS.
    Quando o Renderer aplica DesignLogic, faz:
        radius_final = POLO_TOKENS[polo]['radius'] * radius_multiplier
        spacing_final = POLO_TOKENS[polo]['spacing'] * spacing_multiplier

    Attributes:
        radius_multiplier: 0.0 (retinho, BOLD) a 2.0 (redondo demais, SOFT)
        spacing_multiplier: 0.5 (apertado, BOLD) a 2.0 (respiro total, SOFT)
        allow_overlap: Se permite blocos invadindo (true para BOLD)
        allow_skew: Se permite inclinação italic nos blocos (true para BOLD/TECH)
        allow_text_stroke: Se permite text-stroke em headlines (true para BOLD)
        image_treatment: 'clean' | 'grayscale' | 'grain' | 'warm' | 'glass'
        gallery_density: 'tight' | 'balanced' | 'editorial' | 'mosaic'
    """
    radius_multiplier: float = 1.0
    spacing_multiplier: float = 1.0
    allow_overlap: bool = False
    allow_skew: bool = False
    allow_text_stroke: bool = False
    image_treatment: str = "clean"
    gallery_density: str = "balanced"


@dataclass(frozen=True)
class NichoConfig:
    """Configuração completa de um nicho."""
    schema_type: str
    polo_sugerido: str  # SOFT | BOLD | CLASSIC | TECH
    lanes: tuple[str, ...]
    modal_config: ModalConfig
    faq: tuple[str, ...]
    hero_headlines: HeroHeadlines
    copy_defaults: CopyDefaults
    design_logic: DesignLogic = field(default_factory=DesignLogic)
    seo_keywords: tuple[str, ...] = field(default_factory=tuple)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════════════════

def _modal(
    title: str,
    cta: str,
    fields: tuple[str, ...],
    submit: str,
) -> ModalConfig:
    """Construtor auxiliar de ModalConfig."""
    return ModalConfig(
        title=title,
        cta_button=cta,
        fields=fields,
        submit_action=submit,
    )


def _hero(
    soft: str = "",
    bold: str = "",
    classic: str = "",
    tech: str = "",
) -> HeroHeadlines:
    """Construtor auxiliar de HeroHeadlines."""
    return HeroHeadlines(SOFT=soft, BOLD=bold, CLASSIC=classic, TECH=tech)


def _copy(tone: str, voice: str, cta: str) -> CopyDefaults:
    """Construtor auxiliar de CopyDefaults."""
    return CopyDefaults(tone=tone, voice=voice, cta_primary=cta)


def _design(
    radius: float = 1.0,
    spacing: float = 1.0,
    overlap: bool = False,
    skew: bool = False,
    text_stroke: bool = False,
    image_treatment: str = "clean",
    gallery_density: str = "balanced",
) -> DesignLogic:
    """Construtor auxiliar de DesignLogic."""
    return DesignLogic(
        radius_multiplier=radius,
        spacing_multiplier=spacing,
        allow_overlap=overlap,
        allow_skew=skew,
        allow_text_stroke=text_stroke,
        image_treatment=image_treatment,
        gallery_density=gallery_density,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DESIGN LOGIC PRESETS (por polo)
# ═══════════════════════════════════════════════════════════════════════════

_DESIGN_SOFT = _design(
    radius=2.0,        # bem redondo
    spacing=1.8,       # muito respiro
    overlap=False,
    skew=False,
    text_stroke=False,
    image_treatment="warm",
    gallery_density="editorial",
)

_DESIGN_BOLD = _design(
    radius=0.0,        # retinho
    spacing=0.7,       # apertado
    overlap=True,
    skew=True,
    text_stroke=True,
    image_treatment="grayscale",
    gallery_density="mosaic",
)

_DESIGN_CLASSIC = _design(
    radius=0.5,        # meio termo
    spacing=1.0,
    overlap=False,
    skew=False,
    text_stroke=False,
    image_treatment="clean",
    gallery_density="balanced",
)

_DESIGN_TECH = _design(
    radius=1.0,
    spacing=1.0,
    overlap=True,      # leve overlap
    skew=False,
    text_stroke=False,
    image_treatment="glass",
    gallery_density="tight",
)


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRO DE NICHOS
# ═══════════════════════════════════════════════════════════════════════════

NICHO_CONFIG: dict[str, NichoConfig] = {

    # ──────────────────────────────────────────────────────────────────
    # 1. ACADEMIA / FITNESS — BOLD (default)
    # ──────────────────────────────────────────────────────────────────
    "academia": NichoConfig(
        schema_type="HealthClub",
        polo_sugerido="BOLD",
        lanes=("academia-iron-pulse", "academia-neon-grid",
               "academia-sunset-track", "academia-graphite-core"),
        modal_config=_modal(
            title="Matricule-se Agora",
            cta="Falar com Consultor",
            fields=("Nome", "Email", "Telefone",
                    "Modalidade (Musculacao/Crossfit/Spinning/Yoga)",
                    "Horario Preferido"),
            submit="Enviar formulario + redirecionar para WhatsApp",
        ),
        faq=(
            "Quanto custa a matricula?",
            "Posso treinar sem experiencia?",
            "Qual o horario de funcionamento?",
            "Tem personal trainer incluso?",
            "Posso experimentar antes de matricular?",
        ),
        hero_headlines=_hero(
            soft="Movimento que cuida de voce",
            bold="Treine. Supere. Repita.",
            classic="Estrutura, metodo e resultados",
            tech="Performance medida, evolucao rastreada",
        ),
        copy_defaults=_copy(
            tone="motivacional, energetico, direto",
            voice="2a pessoa do plural",
            cta="Falar no WhatsApp",
        ),
        design_logic=_DESIGN_BOLD,
        seo_keywords=(
            "academia", "academia perto de mim", "musculacao",
            "crossfit", "personal trainer", "academia em {cidade}",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 2. ADVOGADO / ADVOCACIA — CLASSIC
    # ──────────────────────────────────────────────────────────────────
    "advogado": NichoConfig(
        schema_type="LegalService",
        polo_sugerido="CLASSIC",
        lanes=("advogado-statute-noir", "advogado-lex-meridian"),
        modal_config=_modal(
            title="Agendar Consulta Juridica",
            cta="Falar com Advogado",
            fields=("Nome", "Telefone", "Email",
                    "Area de Atuacao (Trabalhista/Civil/Familiar/Previdenciario/Criminal)",
                    "Descricao Resumida do Caso"),
            submit="Enviar para WhatsApp com contexto juridico",
        ),
        faq=(
            "Quanto custa uma consulta juridica?",
            "Atende qual area do direito?",
            "Preciso ir presencialmente ou pode ser online?",
            "Qual o prazo medio para um processo?",
            "Como funciona o pagamento de honorarios?",
        ),
        hero_headlines=_hero(
            soft="Direito com cuidado e estrategia",
            bold="Defendemos seus direitos com forca",
            classic="Estrategia juridica para resultados concretos",
            tech="Analise juridica baseada em dados e precedentes",
        ),
        copy_defaults=_copy(
            tone="serio, confiavel, tecnico",
            voice="3a pessoa do singular (o escritorio)",
            cta="Agendar Consulta",
        ),
        design_logic=_DESIGN_CLASSIC,
        seo_keywords=(
            "advogado", "advogado em {cidade}", "escritorio de advocacia",
            "advogado trabalhista", "consulta juridica",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 3. BARBEARIA — SOFT
    # ──────────────────────────────────────────────────────────────────
    "barbearia": NichoConfig(
        schema_type="BarberShop",
        polo_sugerido="SOFT",
        lanes=("barbearia-heritage-reserve", "barbearia-studio-mono",
               "barbearia-copper-smoke", "barbearia-midnight-club"),
        modal_config=_modal(
            title="Agendar Horario",
            cta="Agendar pelo WhatsApp",
            fields=("Nome", "Telefone",
                    "Servico (Corte/Barba/Sobrancelha)",
                    "Data", "Horario"),
            submit="Enviar para WhatsApp com mensagem pre-formatada",
        ),
        faq=(
            "Quanto custa um corte?",
            "Precisa agendar?",
            "Qual o horario de funcionamento?",
            "Fazem barba?",
            "Aceitam pagamento por pix?",
        ),
        hero_headlines=_hero(
            soft="Ritual de cuidado masculino",
            bold="Corte forte, visual marcante",
            classic="Barbearia tradicional, tecnica apurada",
            tech="Agendamento rapido, atendimento digital",
        ),
        copy_defaults=_copy(
            tone="acolhedor, masculino, artesanal",
            voice="2a pessoa do singular",
            cta="Reservar no WhatsApp",
        ),
        design_logic=_DESIGN_SOFT,
        seo_keywords=(
            "barbearia", "barbearia em {cidade}",
            "corte masculino", "barba", "barbearia perto de mim",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 4. CLINICA MEDICA — CLASSIC
    # ──────────────────────────────────────────────────────────────────
    "clinica": NichoConfig(
        schema_type="MedicalClinic",
        polo_sugerido="CLASSIC",
        lanes=("clinica-medical-trust", "clinica-care-plus"),
        modal_config=_modal(
            title="Agendar Consulta",
            cta="Marcar Consulta",
            fields=("Nome Completo", "Telefone", "Especialidade",
                    "Convenio (Particular/Unimed/Amil)",
                    "Periodo Preferido"),
            submit="Confirmar consulta por WhatsApp",
        ),
        faq=(
            "Quais convenios aceitam?",
            "Como agendo uma consulta?",
            "Atende emergencia?",
            "Qual o endereco da clinica?",
            "Tem estacionamento?",
        ),
        hero_headlines=_hero(
            soft="Cuidado integral da sua saude",
            bold="Saude de verdade, atendimento rapido",
            classic="Medicina de excelencia, ha anos",
            tech="Telemedicina + prontuario digital",
        ),
        copy_defaults=_copy(
            tone="cuidadoso, profissional, seguro",
            voice="3a pessoa do plural (a clinica)",
            cta="Agendar Consulta",
        ),
        design_logic=_DESIGN_CLASSIC,
        seo_keywords=(
            "clinica", "clinica medica", "consulta medica",
            "medico em {cidade}", "convenio medico",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 5. DENTISTA — CLASSIC
    # ──────────────────────────────────────────────────────────────────
    "dentista": NichoConfig(
        schema_type="Dentist",
        polo_sugerido="CLASSIC",
        lanes=("dentista-smile-care", "dentista-clinical-white"),
        modal_config=_modal(
            title="Agendar Consulta Odontologica",
            cta="Marcar Avaliacao",
            fields=("Nome", "Telefone",
                    "Tratamento (Limpeza/Implante/Ortodontia/Estetica)",
                    "Convenio", "Periodo Preferido"),
            submit="Confirmar consulta por WhatsApp",
        ),
        faq=(
            "Quanto custa um implante?",
            "Faz clareamento?",
            "Aceita convenio?",
            "Atende emergencia?",
            "Como funciona o parcelamento?",
        ),
        hero_headlines=_hero(
            soft="Sorriso saudavel com cuidado",
            bold="Sorriso forte, atendimento direto",
            classic="Odontologia de precisao ha anos",
            tech="Escaneamento digital + planejamento 3D",
        ),
        copy_defaults=_copy(
            tone="cuidadoso, tecnico, confiavel",
            voice="2a pessoa do singular",
            cta="Agendar Avaliacao",
        ),
        design_logic=_DESIGN_CLASSIC,
        seo_keywords=(
            "dentista", "dentista em {cidade}", "clinica odontologica",
            "implante dentario", "clareamento dental",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 6. ESTETICA — SOFT
    # ──────────────────────────────────────────────────────────────────
    "estetica": NichoConfig(
        schema_type="BeautySalon",
        polo_sugerido="SOFT",
        lanes=("estetica-clinic-ivory", "estetica-chrome-spa",
               "estetica-rose-clay", "estetica-noir-gold"),
        modal_config=_modal(
            title="Agendar Avaliacao Estetica",
            cta="Agendar pelo WhatsApp",
            fields=("Nome", "Telefone",
                    "Procedimento (Limpeza de Pele/Botox/Preenchimento/Harmonizacao)",
                    "Area do Corpo",
                    "Horario Preferido"),
            submit="Enviar para WhatsApp com procedimento escolhido",
        ),
        faq=(
            "Quanto custa o procedimento?",
            "Quantas sessoes sao necessarias?",
            "Tem contraindicacao?",
            "Qual o tempo de recuperacao?",
            "Posso parcelar?",
        ),
        hero_headlines=_hero(
            soft="Beleza que cuida de voce",
            bold="Transformacao visivel, resultado real",
            classic="Estetica refinada, ha anos no mercado",
            tech="Procedimentos com tecnologia de ponta",
        ),
        copy_defaults=_copy(
            tone="acolhedor, sensorial, feminino",
            voice="2a pessoa do singular",
            cta="Agendar Avaliacao",
        ),
        design_logic=_design(
            radius=2.0,
            spacing=1.8,
            overlap=False,
            skew=False,
            text_stroke=False,
            image_treatment="warm",
            gallery_density="editorial",
        ),
        seo_keywords=(
            "estetica", "clinica de estetica", "harmonizacao facial",
            "botox", "preenchimento", "estetica em {cidade}",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 7. NUTRICIONISTA — SOFT (default) / BOLD (atleta) / SOFT (infantil)
    # ──────────────────────────────────────────────────────────────────
    "nutricionista": NichoConfig(
        schema_type="MedicalBusiness",
        polo_sugerido="SOFT",
        lanes=("nutricionista-botanical-editorial", "nutricionista-clinical-soft",
               "nutricionista-performance-fuel", "nutricionista-coastal-light"),
        modal_config=_modal(
            title="Agendar Consulta Nutricional",
            cta="Agendar Consulta",
            fields=("Nome", "Telefone", "Email",
                    "Objetivo (Emagrecer/Ganho de Massa/Reeducacao)",
                    "Modalidade (Presencial/Online)"),
            submit="Enviar para WhatsApp com objetivo",
        ),
        faq=(
            "Como funciona a consulta?",
            "Atende online?",
            "Em quanto tempo vejo resultado?",
            "O plano alimentar e personalizado?",
            "Posso parcelar?",
        ),
        hero_headlines=_hero(
            soft="Alimentacao que cuida de voce",
            bold="Resultado real, sem dieta maluca",
            classic="Nutricao clinica baseada em evidencia",
            tech="App de acompanhamento + IA nutricao",
        ),
        copy_defaults=_copy(
            tone="acolhedor, educativo, cuidadoso",
            voice="2a pessoa do singular",
            cta="Agendar Consulta",
        ),
        design_logic=_DESIGN_SOFT,
        seo_keywords=(
            "nutricionista", "nutricionista em {cidade}",
            "dieta personalizada", "emagrecimento saudavel",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 8. RESTAURANTE — SOFT
    # ──────────────────────────────────────────────────────────────────
    "restaurante": NichoConfig(
        schema_type="Restaurant",
        polo_sugerido="SOFT",
        lanes=("restaurante-prato-certo", "restaurante-forno-livre"),
        modal_config=_modal(
            title="Reservar Mesa",
            cta="Reservar Mesa",
            fields=("Nome", "Telefone", "Data", "Horario",
                    "Numero de Pessoas", "Observacoes"),
            submit="Confirmar reserva via WhatsApp",
        ),
        faq=(
            "Precisa reservar?",
            "Tem opcao vegetariana?",
            "Aceita cartao?",
            "Tem delivery?",
            "Como chegar?",
        ),
        hero_headlines=_hero(
            soft="Sabor com calma e afeto",
            bold="Sabor que vira conversa",
            classic="Gastronomia classica, ingredientes selecionados",
            tech="Cardapio digital + pedido pelo app",
        ),
        copy_defaults=_copy(
            tone="apetitoso, acolhedor, sensorial",
            voice="2a pessoa do singular",
            cta="Reservar Mesa",
        ),
        design_logic=_DESIGN_SOFT,
        seo_keywords=(
            "restaurante", "restaurante em {cidade}",
            "almoco", "jantar", "gastronomia",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 9. PET SHOP — SOFT
    # ──────────────────────────────────────────────────────────────────
    "pet_shop": NichoConfig(
        schema_type="PetStore",
        polo_sugerido="SOFT",
        lanes=("pet-shop-patudo", "pet-shop-pet-care-pro"),
        modal_config=_modal(
            title="Agendar Atendimento",
            cta="Agendar pelo WhatsApp",
            fields=("Nome do Tutor", "Telefone",
                    "Nome do Pet", "Especie (Caixa/Gato/Outro)",
                    "Porte (Pequeno/Medio/Grande)",
                    "Servico (Banho/Tosa/Vacinacao/Consulta)"),
            submit="Enviar para WhatsApp com dados do pet",
        ),
        faq=(
            "Quanto custa o banho?",
            "Vacinam caes e gatos?",
            "Atendem emergencia?",
            "Tem hotel para pet?",
            "Como agendo o banho e tosa?",
        ),
        hero_headlines=_hero(
            soft="Cuidado que seu pet sente",
            bold="Banho, tosa e saude com agilidade",
            classic="Veterinaria tradicional, equipe especializada",
            tech="Prontuario digital do pet + lembretes de vacina",
        ),
        copy_defaults=_copy(
            tone="carinhoso, cuidadoso, acessivel",
            voice="2a pessoa do singular",
            cta="Agendar Atendimento",
        ),
        design_logic=_DESIGN_SOFT,
        seo_keywords=(
            "pet shop", "banho e tosa", "veterinaria",
            "pet shop em {cidade}", "vacinacao pet",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 10. SALAO DE BELEZA — SOFT
    # ──────────────────────────────────────────────────────────────────
    "salao": NichoConfig(
        schema_type="HairSalon",
        polo_sugerido="SOFT",
        lanes=("salao-glow-studio", "salao-mirror-room"),
        modal_config=_modal(
            title="Agendar Horario",
            cta="Reservar pelo WhatsApp",
            fields=("Nome", "Telefone",
                    "Servico (Corte/Coloracao/Escova/Manicure)",
                    "Data", "Horario"),
            submit="Enviar para WhatsApp com servico",
        ),
        faq=(
            "Quanto custa o corte?",
            "Faz coloracao?",
            "Precisa agendar?",
            "Atende em domicilio?",
            "Tem estacionamento?",
        ),
        hero_headlines=_hero(
            soft="Beleza com cuidado e calma",
            bold="Transformacao visual marcante",
            classic="Salao tradicional, profissionais experientes",
            tech="Agendamento digital + portfolio online",
        ),
        copy_defaults=_copy(
            tone="acolhedor, feminino, sensorial",
            voice="2a pessoa do singular",
            cta="Agendar Horario",
        ),
        design_logic=_DESIGN_SOFT,
        seo_keywords=(
            "salao de beleza", "cabeleireiro",
            "salao em {cidade}", "manicure", "coloracao",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 11. OFICINA MECANICA — BOLD
    # ──────────────────────────────────────────────────────────────────
    "oficina": NichoConfig(
        schema_type="AutoRepair",
        polo_sugerido="BOLD",
        lanes=("oficina-torque-box", "oficina-garage-iron"),
        modal_config=_modal(
            title="Solicitar Orcamento",
            cta="Pedir Orcamento",
            fields=("Nome", "Telefone",
                    "Modelo do Veiculo",
                    "Servico (Troca de Oleo/Alinhamento/Freios/Motor)",
                    "Descricao do Problema"),
            submit="Enviar para WhatsApp com modelo do carro",
        ),
        faq=(
            "Quanto custa a troca de oleo?",
            "Atendem qual marca?",
            "Faz alinhamento e balanceamento?",
            "Tem guincho?",
            "Qual o prazo para o servico?",
        ),
        hero_headlines=_hero(
            soft="Cuidado atencioso com seu carro",
            bold="Mecanica forte, servico rapido",
            classic="Oficina tradicional, mecanicos certificados",
            tech="Diagnostico computadorizado + orcamento digital",
        ),
        copy_defaults=_copy(
            tone="pratico, direto, masculino",
            voice="2a pessoa do singular",
            cta="Pedir Orcamento",
        ),
        design_logic=_DESIGN_BOLD,
        seo_keywords=(
            "oficina mecanica", "mecanico",
            "oficina em {cidade}", "troca de oleo", "alinhamento",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 12. ENERGIA SOLAR — TECH
    # ──────────────────────────────────────────────────────────────────
    "energia_solar": NichoConfig(
        schema_type="HomeAndConstructionBusiness",
        polo_sugerido="TECH",
        lanes=("energia-solar-sun-pure", "energia-solar-tech-grid"),
        modal_config=_modal(
            title="Solicitar Orcamento Solar",
            cta="Pedir Orcamento",
            fields=("Nome", "Telefone", "Email",
                    "Consumo Medio Mensal (kWh)",
                    "Tipo de Imovel (Residencial/Comercial/Rural)",
                    "Cidade/Estado"),
            submit="Enviar para WhatsApp com dados de consumo",
        ),
        faq=(
            "Quanto custa energia solar?",
            "Qual o payback medio?",
            "Funciona em dias nublados?",
            "Precisa de bateria?",
            "Qual a economia mensal esperada?",
        ),
        hero_headlines=_hero(
            soft="Energia limpa para o futuro",
            bold="Economia agressiva na conta de luz",
            classic="Energia solar com instalacao certificada",
            tech="Painel de monitoramento + ROI em tempo real",
        ),
        copy_defaults=_copy(
            tone="tecnico, confiavel, inovador",
            voice="2a pessoa do singular",
            cta="Solicitar Orcamento",
        ),
        design_logic=_DESIGN_TECH,
        seo_keywords=(
            "energia solar", "placa solar",
            "energia solar em {cidade}", "painel solar",
            "instalacao solar", "economia de energia",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # 13. IMOBILIARIA — CLASSIC
    # ──────────────────────────────────────────────────────────────────
    "imobiliaria": NichoConfig(
        schema_type="RealEstateAgent",
        polo_sugerido="CLASSIC",
        lanes=("imobiliaria-key-modern", "imobiliaria-loft-elegance"),
        modal_config=_modal(
            title="Tenho Interesse",
            cta="Quero Visitar",
            fields=("Nome", "Email", "Telefone",
                    "Tipo do Imovel (Apartamento/Casa/Sala/Terreno)",
                    "Faixa de Valor",
                    "Periodo para Mudar"),
            submit="Enviar para WhatsApp com imovel de interesse",
        ),
        faq=(
            "Tem imovel disponivel?",
            "Como agendo uma visita?",
            "Aceita financiamento?",
            "Tem garagem?",
            "Qual o valor do condominio?",
        ),
        hero_headlines=_hero(
            soft="Imovel com cuidado e atencao",
            bold="O imovel certo, na hora certa",
            classic="Imobiliaria tradicional, ha anos no mercado",
            tech="Busca digital + tour virtual 360",
        ),
        copy_defaults=_copy(
            tone="profissional, acessivel, consultivo",
            voice="3a pessoa do plural (a imobiliaria)",
            cta="Quero Visitar",
        ),
        design_logic=_DESIGN_CLASSIC,
        seo_keywords=(
            "imobiliaria", "imovel a venda",
            "imobiliaria em {cidade}", "aluguel", "compra de imovel",
        ),
    ),

    # ──────────────────────────────────────────────────────────────────
    # DEFAULT (fallback) — CLASSIC
    # ──────────────────────────────────────────────────────────────────
    "default": NichoConfig(
        schema_type="LocalBusiness",
        polo_sugerido="CLASSIC",
        lanes=("default-conversion-bold", "default-cinematic-soft",
               "default-health-trust", "default-local-craft"),
        modal_config=_modal(
            title="Fale Conosco",
            cta="Enviar Mensagem",
            fields=("Nome", "Email", "Telefone", "Mensagem"),
            submit="Enviar formulario via WhatsApp ou email",
        ),
        faq=(
            "Como entrar em contato?",
            "Qual o horario de atendimento?",
            "Onde voces estao localizados?",
        ),
        hero_headlines=_hero(
            soft="Cuidado e atencao para voce",
            bold="Atendimento direto e resolutivo",
            classic="Profissionalismo e experiencia",
            tech="Solucao moderna para sua necessidade",
        ),
        copy_defaults=_copy(
            tone="profissional, neutro",
            voice="3a pessoa do singular (o negocio)",
            cta="Falar no WhatsApp",
        ),
        design_logic=_DESIGN_CLASSIC,
        seo_keywords=(),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# SUB-NICHO OVERRIDES
#   Quando o subnicho sugere outro polo, sobrescreve o polo_sugerido.
#   Ex: nutricionista + infantil -> SOFT (default), mas nutricionista + atleta -> BOLD
# ═══════════════════════════════════════════════════════════════════════════

SUB_NICHO_POLO_OVERRIDES: dict[str, dict[str, str]] = {
    # Nutri: infantil e clinica = SOFT (padrão), atleta/performance = BOLD
    "nutricionista": {
        "atleta": "BOLD",
        "atletas": "BOLD",
        "performance": "BOLD",
        "esportivo": "BOLD",
        "esportistas": "BOLD",
        "infantil": "SOFT",
        "crianca": "SOFT",
        "criancas": "SOFT",
        "gestante": "SOFT",
        "gestantes": "SOFT",
        "emagrecimento": "CLASSIC",
        "clinica": "CLASSIC",
    },
    # Academia: yoga/pilates/alongamento = SOFT (em vez de BOLD)
    "academia": {
        "yoga": "SOFT",
        "pilates": "SOFT",
        "alongamento": "SOFT",
        "funcional": "BOLD",
        "crossfit": "BOLD",
        "musculacao": "BOLD",
        "boxe": "BOLD",
        "mma": "BOLD",
        "jiu_jitsu": "BOLD",
    },
    # Estética: clínica médica = CLASSIC, harmonização/spa = SOFT, procedimentos agressivos = BOLD
    "estetica": {
        "harmonizacao": "SOFT",
        "botox": "SOFT",
        "preenchimento": "SOFT",
        "limpeza_de_pele": "SOFT",
        "cirurgia": "CLASSIC",
        "clinica_medica": "CLASSIC",
        "dermatologia": "CLASSIC",
    },
    # Advogado: criminal/trabalhista = CLASSIC, empresarial = TECH
    "advogado": {
        "criminal": "CLASSIC",
        "trabalhista": "CLASSIC",
        "civil": "CLASSIC",
        "familia": "CLASSIC",
        "empresarial": "TECH",
        "tributario": "TECH",
        "compliance": "TECH",
    },
    # Restaurante: executivo = CLASSIC, pub/lounge = BOLD, vegetariano = SOFT
    "restaurante": {
        "vegetariano": "SOFT",
        "vegano": "SOFT",
        "natural": "SOFT",
        "fast_food": "BOLD",
        "hamburgueria": "BOLD",
        "pizzaria": "BOLD",
        "executivo": "CLASSIC",
        "fine_dining": "CLASSIC",
    },
}


def resolve_polo_for_lead(
    nicho: str | None,
    subnicho: str | None = None,
    inferido: str | None = None,
) -> str:
    """
    Resolve o polo final considerando nicho + subnicho + inferência prévia.

    Hierarquia (maior prioridade primeiro):
      1. SUB_NICHO_POLO_OVERRIDES[nicho][subnicho]  (override específico)
      2. NICHO_CONFIG[nicho].polo_sugerido           (default do nicho)
      3. inferido                                    (do LLM)
      4. "CLASSIC"                                   (fallback absoluto)

    Args:
        nicho: Nome do nicho canônico.
        subnicho: Subnicho opcional (ex: "atleta", "infantil", "yoga").
        inferido: Polo já inferido pelo agente_variacao (opcional).

    Returns:
        Polo canônico: SOFT | BOLD | CLASSIC | TECH.
    """
    if not nicho:
        return inferido or "CLASSIC"

    # 1) Override por subnicho (mais forte)
    if subnicho:
        overrides = SUB_NICHO_POLO_OVERRIDES.get(nicho.lower().strip(), {})
        polo_override = overrides.get(subnicho.lower().strip())
        if polo_override:
            return polo_override

    # 2) Polo do nicho canônico
    cfg = get_nicho_config(nicho)
    if cfg.polo_sugerido:
        return cfg.polo_sugerido

    # 3) Polo inferido pelo agente
    if inferido:
        return inferido.upper()

    # 4) Fallback absoluto
    return "CLASSIC"


# ═══════════════════════════════════════════════════════════════════════════
# LOOKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Mapeamento de aliases → chave canônica
ALIASES: dict[str, str] = {
    # academia
    "academia": "academia",
    "academias": "academia",
    "fitness": "academia",
    "crossfit": "academia",
    "musculacao": "academia",
    "musculação": "academia",
    "gym": "academia",
    "funcional": "academia",
    "personal_trainer": "academia",

    # advogado
    "advogado": "advogado",
    "advocacia": "advogado",
    "advogados": "advogado",
    "escritorio_advocacia": "advogado",
    "escritorio_de_advocacia": "advogado",
    "juridico": "advogado",
    "advogada": "advogado",

    # barbearia
    "barbearia": "barbearia",
    "barber": "barbearia",
    "barbeiro": "barbearia",
    "barbearias": "barbearia",

    # clinica
    "clinica": "clinica",
    "clínica": "clinica",
    "clinica_medica": "clinica",
    "medico": "clinica",
    "medica": "clinica",
    "consultorio": "clinica",

    # dentista
    "dentista": "dentista",
    "odontologia": "dentista",
    "odontologo": "dentista",
    "clinica_odontologica": "dentista",

    # estetica
    "estetica": "estetica",
    "estética": "estetica",
    "clinica_estetica": "estetica",
    "harmonizacao": "estetica",
    "harmonização": "estetica",
    "botox": "estetica",
    "preenchimento": "estetica",

    # nutricionista
    "nutricionista": "nutricionista",
    "nutricao": "nutricionista",
    "nutrição": "nutricionista",
    "nutri": "nutricionista",

    # restaurante
    "restaurante": "restaurante",
    "restaurantes": "restaurante",
    "gastronomia": "restaurante",
    "pizzaria": "restaurante",
    "hamburgueria": "restaurante",
    "lanchonete": "restaurante",
    "padaria": "restaurante",

    # pet shop
    "pet_shop": "pet_shop",
    "petshop": "pet_shop",
    "pet": "pet_shop",
    "veterinaria": "pet_shop",
    "veterinário": "pet_shop",
    "caes_e_gatos": "pet_shop",

    # salao
    "salao": "salao",
    "salão": "salao",
    "salao_de_beleza": "salao",
    "cabeleireiro": "salao",
    "cabelereira": "salao",
    "manicure": "salao",

    # oficina
    "oficina": "oficina",
    "oficina_mecanica": "oficina",
    "mecanico": "oficina",
    "mecânica": "oficina",
    "auto_pecas": "oficina",
    "autopeças": "oficina",

    # energia solar
    "energia_solar": "energia_solar",
    "solar": "energia_solar",
    "placa_solar": "energia_solar",
    "fotovoltaico": "energia_solar",

    # imobiliaria
    "imobiliaria": "imobiliaria",
    "imobiliária": "imobiliaria",
    "imoveis": "imobiliaria",
    "imóveis": "imobiliaria",
}


def get_nicho_config(nicho: str | None = None) -> NichoConfig:
    """
    Retorna a NichoConfig canônica de um nicho (com fallback).

    Args:
        nicho: Nome do nicho (segmento). Aceita aliases e variações.

    Returns:
        NichoConfig com toda configuração do nicho, ou default se não reconhecido.
    """
    if not nicho:
        return NICHO_CONFIG["default"]

    canonical = ALIASES.get(nicho.lower().strip(), nicho.lower().strip())
    return NICHO_CONFIG.get(canonical, NICHO_CONFIG["default"])


def get_modal_config(nicho: str | None = None) -> ModalConfig:
    """Atalho para get_nicho_config().modal_config."""
    return get_nicho_config(nicho).modal_config


def get_schema_type(nicho: str | None = None) -> str:
    """Atalho para get_nicho_config().schema_type."""
    return get_nicho_config(nicho).schema_type


def get_faq(nicho: str | None = None) -> tuple[str, ...]:
    """Atalho para get_nicho_config().faq."""
    return get_nicho_config(nicho).faq


def get_hero_headline(nicho: str | None = None, polo: str = "CLASSIC") -> str:
    """
    Retorna template de headline do hero para um (nicho, polo).

    Args:
        nicho: Nome do nicho.
        polo: Polo (SOFT | BOLD | CLASSIC | TECH).

    Returns:
        String da headline ou string vazia se não houver template.
    """
    headlines = get_nicho_config(nicho).hero_headlines
    return getattr(headlines, polo.upper(), "")


def get_cta_primary(nicho: str | None = None) -> str:
    """Atalho para get_nicho_config().copy_defaults.cta_primary."""
    return get_nicho_config(nicho).copy_defaults.cta_primary


def get_polo_sugerido(nicho: str | None = None) -> str:
    """Atalho para get_nicho_config().polo_sugerido."""
    return get_nicho_config(nicho).polo_sugerido


def get_design_logic(nicho: str | None = None) -> DesignLogic:
    """Atalho para get_nicho_config().design_logic."""
    return get_nicho_config(nicho).design_logic


def listar_nichos() -> tuple[str, ...]:
    """Lista todos os nichos canônicos (excluindo 'default')."""
    return tuple(k for k in NICHO_CONFIG.keys() if k != "default")


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "ModalConfig",
    "HeroHeadlines",
    "CopyDefaults",
    "DesignLogic",
    "NichoConfig",
    "NICHO_CONFIG",
    "ALIASES",
    "SUB_NICHO_POLO_OVERRIDES",
    "get_nicho_config",
    "get_modal_config",
    "get_schema_type",
    "get_faq",
    "get_hero_headline",
    "get_cta_primary",
    "get_polo_sugerido",
    "get_design_logic",
    "resolve_polo_for_lead",
    "listar_nichos",
]