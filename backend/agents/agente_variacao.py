"""Agente de Variacao Estrutural - mapeia subnicho -> estrutura.

Em 2026-06-23 foi adicionado SUB_NICHO_TEMPLATES para evitar que sites
do mesmo nicho (ex: Nutricionista) fiquem identicos. Agora, quando
detect_subniche() identifica o subnicho canonico, a estrutura (template
+ ordem das secoes + angulo de comunicacao) vem do mapping canonico,
NAO do LLM. Isso garante variacao REAL entre subnichos.

Para subnichos nao mapeados, cai no fallback "default" que chama o
LLM (Sonnet) para gerar a variacao como antes.
"""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from handoff_types import NichoBriefing, VariacaoEstrutural
from llm_direct import call_claude


# ─── Subnicho detection (heuristica canonica) ──────────────────────────────


SUBNICHO_PATTERNS = {
    # Nutricionista
    "nutricionista_esportiva": ["esportiva", "esport", "atleta", "performance", "competicao"],
    "nutricionista_clinica": ["clinica", "clinico", "patologia", "emagrecimento", "reeducacao"],
    "nutricionista_infantil": ["infantil", "crianca", "pediatr", "familia"],
    # Saude
    "clinica_estetica": ["estetica", "estetic", "botox", "preenchimento", "harmonizacao"],
    "clinica_odontologica": ["odonto", "dentist", "dente", "implante", "ortodontia"],
    "clinica_medica": ["medico", "medicina", "consulta", "exame", "diagnostico"],
    # Beleza
    "barbearia_premium": ["barbearia", "barbeiro", "corte masculino", "barba"],
    "salao_beleza": ["salao", "cabeleireiro", "cabelo", "manicure", "pedicure"],
    "estetica_facial": ["facial", "limpeza de pele", "peeling", "skincare"],
    # Fitness
    "academia_crossfit": ["crossfit", "cross fit", "box"],
    "academia_musculacao": ["musculacao", "academia", "muscul", "hipertrofia"],
    "pilates_estudio": ["pilates", "studio"],
    "yoga_estudio": ["yoga", "meditacao"],
    # Alimentacao
    "restaurante_familiar": ["restaurante", "almoco", "jantar", "familia", "self service"],
    "pizzaria_tradicional": ["pizzaria", "pizza"],
    "hamburgueria_artesanal": ["hamburgueria", "hamburger", "artesanal"],
    "cafeteria_especial": ["cafeteria", "cafe", "especial", "gourmet"],
    # Servicos
    "advocacia_trabalhista": ["trabalhista", "trabalhador", "clt", "rescisao"],
    "advocacia_familia": ["familia", "divorcio", "inventario", "pensao"],
    "escritorio_contabil": ["contabilidade", "contador", "contabil", "imposto"],
    "imobiliaria_residencial": ["imobiliaria", "imovel", "aluguel", "venda"],
    "autoescola": ["autoescola", "cnh", "carteira de motorista", "habilitacao"],
}


def detect_subniche(segmento: str, servicos: list[str] | None = None, atributos: list[str] | None = None) -> str:
    """Detecta o subnicho canonico a partir de segmento + servicos + atributos.

    Retorna chave canonica (ex: "nutricionista_esportiva") ou "default".
    """
    segmento = (segmento or "").lower().strip()
    servicos = [str(s).lower() for s in (servicos or []) if s]
    atributos = [str(a).lower() for a in (atributos or []) if a]
    corpus = segmento + " " + " ".join(servicos) + " " + " ".join(atributos)

    # Match exato de segmento primeiro
    for subnicho, patterns in SUBNICHO_PATTERNS.items():
        segmento_base = subnicho.split("_", 1)[0]
        if segmento_base in segmento:
            # Verificar padroes mais especificos
            for p in patterns:
                if p in corpus:
                    return subnicho
            # Se nao achou padrao mais especifico, retorna o segmento_base mais comum
            if segmento_base == "nutricionista":
                return "nutricionista_clinica"  # fallback conservador
            if segmento_base == "clinica":
                return "clinica_medica"
            if segmento_base == "academia":
                return "academia_musculacao"
            if segmento_base == "advocacia":
                return "advocacia_familia"

    # Match fuzzy nos servicos/atributos
    for subnicho, patterns in SUBNICHO_PATTERNS.items():
        for p in patterns:
            if p in corpus:
                return subnicho

    return "default"


# ─── Subnicho templates (mapping canonico subnicho -> estrutura) ──────────


SUB_NICHO_TEMPLATES: dict[str, dict] = {
    "nutricionista_esportiva": {
        "template_estrutura": "organic",
        "template_hero": "hero-fullscreen",
        "template_prova_social": "stats-horizontal",
        "template_cta": "cta-floating",
        "template_faq": "faq-accordion",
        "ordem_das_secoes": [
            "hero", "numeros", "abordagem", "galeria", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Performance + resultados mensuraveis. "
            "Foco em ganho de massa, perda de gordura, performance em competicao. "
            "Tom direto, tecnico mas acessivel, com numeros e depoimentos de atletas."
        ),
    },
    "nutricionista_clinica": {
        "template_estrutura": "editorial",
        "template_hero": "hero-split",
        "template_prova_social": "reviews-spotlight",
        "template_cta": "cta-central",
        "template_faq": "faq-two-col",
        "ordem_das_secoes": [
            "hero", "sobre", "servicos", "processo", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Cuidado clinico + acompanhamento individualizado. "
            "Foco em reeducacao alimentar, patologias, emagrecimento saudavel. "
            "Tom acolhedor, cuidador, com linguagem tecnica mas acessivel."
        ),
    },
    "clinica_estetica": {
        "template_estrutura": "minimal",
        "template_hero": "hero-center",
        "template_prova_social": "reviews-grid",
        "template_cta": "cta-banner",
        "template_faq": "faq-accordion",
        "ordem_das_secoes": [
            "hero", "procedimentos", "antes-depois", "equipe", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Beleza + autoconfianca. Foco em procedimentos esteticos, antes/depois, "
            "resultados visiveis, equipe qualificada. Tom sofisticado, premium."
        ),
    },
    "barbearia_premium": {
        "template_estrutura": "brutalist",
        "template_hero": "hero-diagonal",
        "template_prova_social": "reviews-masonry",
        "template_cta": "cta-bottom",
        "template_faq": "faq-minimal",
        "ordem_das_secoes": [
            "hero", "servicos", "galeria", "equipe", "depoimentos", "localizacao", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Estilo + experiencia masculina. Foco em corte, barba, ambiente. "
            "Tom descontraido, masculino, com humor e atitude."
        ),
    },
    "academia_crossfit": {
        "template_estrutura": "brutalist",
        "template_hero": "hero-fullscreen",
        "template_prova_social": "stats-horizontal",
        "template_cta": "cta-floating",
        "template_faq": "faq-minimal",
        "ordem_das_secoes": [
            "hero", "numeros", "modalidades", "galeria", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Forca + comunidade. Foco em resultados transformadores, WODs, "
            "comunidade. Tom intenso, motivacional, com energia alta."
        ),
    },
    "restaurante_familiar": {
        "template_estrutura": "organic",
        "template_hero": "hero-split",
        "template_prova_social": "reviews-carousel",
        "template_cta": "cta-central",
        "template_faq": "faq-accordion",
        "ordem_das_secoes": [
            "hero", "cardapio", "sobre", "galeria", "depoimentos", "localizacao", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Sabor + acolhimento familiar. Foco em pratos caseiros, ingredientes "
            "frescos, ambiente acolhedor. Tom caloroso, tradicional."
        ),
    },
    "advocacia_trabalhista": {
        "template_estrutura": "corporate",
        "template_hero": "hero-split",
        "template_prova_social": "stats-cards",
        "template_cta": "cta-central",
        "template_faq": "faq-two-col",
        "ordem_das_secoes": [
            "hero", "sobre", "areas-atuacao", "processo", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": (
            "Confianca + expertise juridica. Foco em direitos trabalhistas, "
            "rescisoes, FGTS. Tom serio, profissional, com clareza juridica."
        ),
    },
    "default": {
        "template_estrutura": "corporate",
        "template_hero": "hero-split",
        "template_prova_social": "reviews-carousel",
        "template_cta": "cta-central",
        "template_faq": "faq-accordion",
        "ordem_das_secoes": [
            "hero", "sobre", "servicos", "depoimentos", "faq", "contato", "footer",
        ],
        "angulo_de_comunicacao": "Conversao + confianca. Tom profissional, foco em beneficios e CTA.",
    },
}


def _get_subnicho_template(subnicho: str) -> dict:
    """Retorna o template canonico do subnicho, ou o default."""
    return SUB_NICHO_TEMPLATES.get(subnicho, SUB_NICHO_TEMPLATES["default"])


# ─── System prompt (fallback para subnichos nao mapeados) ────────────────

SYSTEM_PROMPT = """You are the Structural Variation Agent.

Your role is to prevent pages in the same niche and region from looking the same.
You choose the best combination of structure, hero, section order, and communication angle for each lead.

INPUT:
- Niche Agent briefing
- Competitor data
- Segment and region

OUTPUT:
JSON only - no markdown, no extra explanation.

OBJECTIVE:
Select a website structure that is good for conversion and different from previous pages.

WHAT YOU DEFINE:
- template_estrutura: "brutalist" | "editorial" | "organic" | "corporate" | "minimal"
- template_hero: "hero-split" | "hero-center" | "hero-fullscreen" | "hero-diagonal" | "hero-video"
- template_prova_social: "reviews-masonry" | "reviews-carousel" | "reviews-grid" | "reviews-spotlight" | "stats-horizontal" | "stats-cards"
- template_cta: "cta-central" | "cta-banner" | "cta-floating" | "cta-bottom"
- template_faq: "faq-accordion" | "faq-two-col" | "faq-minimal"
- ordem_das_secoes: list (REQUIRED: hero, contato, footer + 2-5 optional)
- angulo_de_comunicacao: unique persuasive angle for the lead
- regra_antirrepeticao: what to avoid based on niche/region

OPTIONAL (choose 2-5): sobre, servicos, depoimentos, faq, localizacao, numeros, galeria, planos, equipe, cta-final

RULES:
- Do not repeat default structure automatically
- Vary hero, social proof, and section order when there is risk of clones
- Keep coherence with niche and user behavior
- Prioritize conversion over novelty
- Do not force "servicos" section; use it only if services are confirmed
- If niche has high repetition, increase structural variation
- If niche is very competitive, use a more differentiated structure
- If offer is simple, use a shorter and more objective structure

OUTPUT FORMAT (pure JSON, no markdown):
{
  "template_estrutura": "corporate",
  "template_hero": "hero-split",
  "template_prova_social": "reviews-carousel",
  "template_cta": "cta-central",
  "template_faq": "faq-accordion",
  "ordem_das_secoes": ["hero", "sobre", "depoimentos", "faq", "contato", "footer"],
  "angulo_de_comunicacao": "string",
  "regra_antirrepeticao": "string",
  "justificativa": "string"
}

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""


def gerar_variacao(
    nicho_briefing: NichoBriefing,
    concorrentes_raw: str = "",
    task_id: str = "",
    *,
    servicos: list[str] | None = None,
    atributos: list[str] | None = None,
) -> VariacaoEstrutural:
    """Gera variacao estrutural.

    Se o subnicho do briefing estiver em SUB_NICHO_TEMPLATES, USA O MAPPING
    CANONICO (sem chamar LLM). Caso contrario, chama Sonnet como antes.

    Args:
        nicho_briefing: Briefing do agente de nicho (com subnicho canonico)
        concorrentes_raw: Dados de concorrencia (Jina)
        task_id: ID da task
        servicos: Lista de servicos (opcional, para detectar subnicho se briefing nao tiver)
        atributos: Lista de atributos (opcional)
    """
    # 1) Detectar subnicho canonico
    subnicho = (nicho_briefing.subnicho or "").strip().lower()
    if not subnicho or subnicho == "default":
        subnicho = detect_subniche(
            nicho_briefing.nicho,
            servicos=servicos,
            atributos=atributos,
        )

    import time as _time

    _start = _time.time()

    # 2) Se subnicho mapeado, usa o template canonico (NAO chama LLM)
    if subnicho in SUB_NICHO_TEMPLATES and subnicho != "default":
        _template = _get_subnicho_template(subnicho)
        _elapsed = _time.time() - _start
        return VariacaoEstrutural(
            task_id=task_id,
            source_agent="agente_variacao",
            target_agent="arquiteto_mestre",
            status="ok",
            task_summary=f"Variacao canonica subnicho '{subnicho}' em {_elapsed:.3f}s (sem LLM)",
            subnicho=subnicho,
            template_estrutura=_template["template_estrutura"],
            template_hero=_template["template_hero"],
            template_prova_social=_template["template_prova_social"],
            template_cta=_template["template_cta"],
            template_faq=_template["template_faq"],
            ordem_das_secoes=_template["ordem_das_secoes"],
            angulo_de_comunicacao=_template["angulo_de_comunicacao"],
            regra_antirrepeticao=f"Estrutura fixa para subnicho {subnicho}; variacao vem de cor/copy.",
            justificativa=f"Subnicho {subnicho} mapeado em SUB_NICHO_TEMPLATES - sem chamada LLM.",
        )

    # 3) Fallback: chamar Sonnet para gerar variacao livre
    _briefing_md = nicho_briefing.to_markdown()
    user_prompt = f"""Escolha a variacao estrutural para este lead.

{_briefing_md}

== DADOS DE CONCORRENCIA ==
{concorrentes_raw[:2000] if concorrentes_raw else "nao disponivel"}

Regiao: {nicho_briefing.cidade}
Nicho: {nicho_briefing.nicho}

Retorne APENAS o JSON - sem markdown, sem explicacao extra."""

    resposta = call_claude(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="sonnet",  # Era haiku; agora sonnet para evitar variacoes ruins
        max_tokens=1500,
        temperature=0.4,
        agent_name="agente_variacao",
    )

    _elapsed = _time.time() - _start

    # Extrair JSON da resposta
    import json as _json, re as _re

    _json_match = _re.search(r"\{.*\}", resposta, _re.DOTALL)
    _dados = {}
    if _json_match:
        try:
            _dados = _json.loads(_json_match.group(0))
        except _json.JSONDecodeError:
            pass

    # Fallback seguro
    _estrutura = _dados.get("template_estrutura", "corporate")
    _hero = _dados.get("template_hero", "hero-split")
    _ordem = _dados.get(
        "ordem_das_secoes", ["hero", "sobre", "localizacao", "contato", "footer"]
    )

    return VariacaoEstrutural(
        task_id=task_id,
        source_agent="agente_variacao",
        target_agent="arquiteto_mestre",
        status="ok",
        task_summary=f"Variacao Sonnet para subnicho '{subnicho}' em {_elapsed:.1f}s",
        subnicho=subnicho,
        template_estrutura=_estrutura,
        template_hero=_hero,
        template_prova_social=_dados.get("template_prova_social", "reviews-carousel"),
        template_cta=_dados.get("template_cta", "cta-central"),
        template_faq=_dados.get("template_faq", "faq-accordion"),
        ordem_das_secoes=_ordem,
        angulo_de_comunicacao=_dados.get("angulo_de_comunicacao", ""),
        regra_antirrepeticao=_dados.get("regra_antirrepeticao", ""),
        justificativa=_dados.get("justificativa", ""),
    )
