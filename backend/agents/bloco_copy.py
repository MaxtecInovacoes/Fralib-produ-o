"""Bloco 2 — Copy por secao.
LLM call focada em escrever copy (h1, subtitulo, cta, body) para cada secao.
Retorno: Markdown parseado via markdown_prd_parser.
"""

import re as _re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_direct import call_claude
from markdown_prd_parser import parse_bloco2_with_fallback
from prompts_arquiteto import SYSTEM_COPY_SENIOR


def _formatar_reviews(top_3: list, reviews_insights: dict) -> tuple:
    """Retorna (reviews_fmt, reviews_intel_ctx)."""
    if top_3:
        reviews_fmt = "\n".join(
            [
                f'- "{r.get("text", r.get("texto", ""))}" — {r.get("author", r.get("autor", "Cliente"))}'
                for r in top_3
            ]
        )
    else:
        reviews_fmt = "NENHUM REVIEW DISPONIVEL"

    intel_ctx = ""
    if reviews_insights.get("total_reviews", 0) > 0:
        elogios = ", ".join(reviews_insights.get("elogios_resumo", [])[:3])
        reclamacoes = (
            ", ".join(reviews_insights.get("reclamacoes_resumo", [])[:2])
            or "nada relevante"
        )
        palavras = ", ".join(reviews_insights.get("palavras_frequentes", [])[:8])
        diferencial = reviews_insights.get("diferencial_detectado", "")
        intel_ctx = (
            f"\n=== INTELIGENCIA REVIEWS ({reviews_insights['total_reviews']} avaliacoes, nota {reviews_insights['nota_media']}/5) ===\n"
            f"Elogios: {elogios}\nReclamacoes: {reclamacoes}\n"
            f"Palavras citadas: {palavras}\nDiferencial: {diferencial}\n"
            f"REGRA: Use insights pra enriquecer hero, sobre e servicos. Evite mencionar reclamacoes.\n"
            f"=== FIM ===\n"
        )
    return reviews_fmt, intel_ctx


_SPECS_SECAO = {
    "hero": """## hero
h1: titulo com cidade (8+ palavras, headline de VENDA, nao o nome do negocio)
subtitulo: subtitulo persuasivo
cta: texto do botao
eyebrow: tag acima do h1""",
    "sobre": """## sobre
h2: titulo
body: texto curto e especifico
cta: texto do botao""",
    "servicos": """## servicos
h2: titulo
body: texto curto e especifico
items: servicos reais confirmados, separados por ; (vazio se nao houver)
cta: texto do botao""",
    "depoimentos": """## depoimentos
omitir: {omitir_val}
h2: titulo
body: texto com reviews reais""",
    "faq": """## faq
h2: titulo
body: perguntas e respostas curtas""",
    "localizacao": """## localizacao
h2: titulo
body: endereco real; se endereco estiver vazio, omitir:true
cta: texto do botao""",
    "contato": """## contato
h2: titulo
body: telefone real
cta: texto do botao""",
}

_GRUPOS_SECOES = [
    ["hero", "sobre"],
    ["servicos", "depoimentos"],
    ["faq", "localizacao"],
    ["contato"],
]


def _montar_contexto_shared(
    nome, cidade, segmento, telefone, endereco, rating, total_av,
    caio_tier, dark_mode, jina_insights, instrucao_criativa,
    reviews_fmt, reviews_intel_ctx, seo_ctx, faq_seo_fmt,
    keyword_research, reviews_has, craft_ctx, autocritica_ctx,
):
    """Monta o contexto compartilhado (mesmo para todas as chamadas parciais)."""
    endereco_rule = (
        "ADDRESS CAPTURED: use the complete address exactly as provided."
        if endereco
        else "ADDRESS NOT CAPTURED: do not invent street/neighborhood; mention only the city when needed and omit location section when there is no address."
    )
    return f"""BUSINESS: {nome} | CITY: {cidade} | SEGMENT: {segmento}
PHONE: {telefone} | ADDRESS: {endereco}
RATING: {rating}/5 ({total_av} avaliacoes) | TIER: {caio_tier}
MODE: {"DARK" if dark_mode else "LIGHT"}
{endereco_rule}

{jina_insights[:3000] if jina_insights else ""}

CREATIVE DIRECTION: {instrucao_criativa[:500]}
{reviews_intel_ctx}

COPY RULES:
- All customer-facing copy MUST be in Brazilian Portuguese (pt-BR).
- NEVER use: "atendimento personalizado", "qualidade e compromisso", "resultados reais", "pronto para comecar", "os melhores profissionais"
- NEVER use emoji.
- NEVER use "premium", "melhor", "top", "lider", "referencia", "moderna", "elite", "VIP" as public claims.
- Vary CTAs: Hero=urgency, Servicos=curiosity, Depoimentos=desire, Contato=scarcity.
- Geo-specific copy: if address exists, use street/neighborhood; if not, use only city.
- SOBRE: do not paste a review inside the text. Use only confirmed facts.
- SERVICOS: only confirmed Maps services. Reviews are NOT a service source.
- Never infer modality from words in reviews, keywords, or niche expectations.
- Numbers/metrics: use only rating and review count; do not invent average hours, modalities, students, years, or results.
- FAQ: use People Also Ask as questions when available.

REAL REVIEWS:
{reviews_fmt}

{seo_ctx}
{faq_seo_fmt}
{keyword_research}

CRAFT RULES:
{craft_ctx}

{autocritica_ctx}

Real phone: {telefone}
Specific copy for {nome}, never generic."""


def _montar_prompt_bloco2(
    nome: str,
    cidade: str,
    segmento: str,
    telefone: str,
    endereco: str,
    rating: float,
    total_av: int,
    caio_tier: str,
    dark_mode: bool,
    jina_insights: str,
    instrucao_criativa: str,
    reviews_fmt: str,
    reviews_intel_ctx: str,
    seo_ctx: str,
    faq_seo_fmt: str,
    keyword_research: str,
    secoes_nomes: list,
    reviews_has: bool,
    intel_ctx: str,
    craft_ctx: str,
    autocritica_ctx: str,
) -> str:
    """Monta prompt para Bloco 2 — copy (todas secoes, legado single-call).

    DEPRECATED: Use _montar_contexto_shared + chamadas parciais instead.
    Mantido para compatibilidade.
    """
    shared = _montar_contexto_shared(
        nome, cidade, segmento, telefone, endereco, rating, total_av,
        caio_tier, dark_mode, jina_insights, instrucao_criativa,
        reviews_fmt, reviews_intel_ctx, seo_ctx, faq_seo_fmt,
        keyword_research, reviews_has, craft_ctx, autocritica_ctx,
    )
    secoes_set = set(s.lower() for s in secoes_nomes)
    blocks = []
    for grupo in _GRUPOS_SECOES:
        for sec in grupo:
            if sec in secoes_set:
                spec = _SPECS_SECAO[sec]
                if sec == "depoimentos":
                    spec = spec.format(omitir_val="false" if reviews_has else "true")
                blocks.append(spec)
    sections_block = "\n\n".join(blocks)
    return f"""{shared}

SECTIONS: {", ".join(secoes_nomes)}
{"REVIEWS REAIS DISPONIVEIS — use-os." if reviews_has else "REVIEWS INDISPONIVEIS — depoimentos deve ter omitir:true"}

Return MARKDOWN with EXACTLY this format:

{sections_block}

H1: 8+ words with benefit + city. Good example: "Treino funcional e nutricao integrada em Campina Grande do Sul". Bad example: "Nutrasport" (that is a name, NOT a headline).
MARKDOWN ONLY. No JSON. No code blocks."""


def _texto_curto(value) -> str:
    return str(value or "").strip()


def _primeira_linha_review(review: dict) -> str:
    texto = _texto_curto(review.get("text") or review.get("texto"))
    autor = _texto_curto(review.get("author") or review.get("autor")) or "Cliente"
    if not texto:
        return ""
    texto = " ".join(texto.split())
    if len(texto) > 180:
        texto = texto[:177].rstrip() + "..."
    return f'"{texto}" - {autor}'


def _copy_deterministica_fallback(
    nome: str,
    cidade: str,
    segmento: str,
    telefone: str,
    endereco: str,
    rating: float,
    total_av: int,
    secoes_nomes: list,
    reviews_raw: list,
) -> dict:
    """Gera copy factual minima quando LLM fica indisponivel.

    Mantem o pipeline vivo sem inventar servicos, endereco, metricas ou claims.
    """
    nome = _texto_curto(nome)
    cidade = _texto_curto(cidade)
    segmento = _texto_curto(segmento).lower() or "negocio local"
    telefone = _texto_curto(telefone)
    endereco = _texto_curto(endereco)
    reviews_raw = reviews_raw or []
    total_label = f"{total_av} avaliacoes" if total_av else "avaliacoes no perfil"
    rating_label = f"Nota {rating}/5" if rating else "Perfil local verificado"
    contato_body = telefone or "Entre em contato para confirmar atendimento."

    copy_por_secao = {
        "hero": {
            "h1": f"{segmento.capitalize()} em {cidade} para treinar com mais clareza",
            "subtitulo": f"Conheca a {nome} com informacoes reais do perfil local, contato direto e detalhes para decidir sua proxima visita.",
            "cta": "Chamar no WhatsApp" if telefone else "Falar com a equipe",
            "eyebrow": f"{segmento.capitalize()} em {cidade}",
        },
        "sobre": {
            "h2": f"Sobre a {nome}",
            "body": f"A {nome} atende em {cidade}. {rating_label} com {total_label}. Consulte a equipe para confirmar atividades, planos e disponibilidade.",
            "cta": "Ver informacoes",
        },
        "servicos": {
            "omitir": True,
            "h2": "Confirme o atendimento pelo contato",
            "body": "A lista de atividades nao foi confirmada por fonte estruturada nesta coleta. Fale com a equipe antes de visitar.",
            "items": "",
            "cta": "Falar com a equipe",
        },
        "depoimentos": {
            "omitir": not bool(reviews_raw),
            "h2": "O que aparece nas avaliacoes",
            "body": "\n".join(
                line for line in (_primeira_linha_review(r) for r in reviews_raw[:3]) if line
            )
            or "Depoimentos indisponiveis nesta coleta.",
        },
        "faq": {
            "h2": "Perguntas frequentes",
            "body": f"Como falar com a {nome}? Use o telefone informado no site.\nOnde fica? {endereco or cidade}.\nQuais atividades oferece? Confirme diretamente com a equipe.",
        },
        "localizacao": {
            "omitir": not bool(endereco),
            "h2": "Localizacao",
            "body": endereco or cidade,
            "cta": "Ver rota",
        },
        "contato": {
            "h2": f"Contato da {nome}",
            "body": contato_body,
            "cta": "Enviar mensagem",
        },
    }

    sections = []
    nomes = secoes_nomes or list(copy_por_secao.keys())
    for secao in nomes:
        nome_secao = _texto_curto(secao).lower()
        copy = copy_por_secao.get(
            nome_secao,
            {
                "h2": nome_secao.capitalize() or "Informacoes",
                "body": f"Informacoes da {nome} em {cidade}.",
                "cta": "Falar com a equipe",
            },
        )
        sections.append(
            {
                "name": nome_secao,
                "copy": {k: v for k, v in copy.items() if k != "omitir"},
                "omitir": bool(copy.get("omitir", False)),
            }
        )
    return {"sections": sections, "_fallback": "deterministic_copy"}


def _callar_bloco_parcial(
    shared_context: str,
    grupo_secoes: list,
    reviews_has: bool,
) -> list | None:
    """Faz uma chamada LLM para um subconjunto de secoes.

    Returns lista de {name, copy, omitir} ou None se todas as tentativas falharem.
    """
    # Montar spec das secoes do grupo
    blocks = []
    for sec in grupo_secoes:
        spec = _SPECS_SECAO[sec]
        if sec == "depoimentos":
            spec = spec.format(omitir_val="false" if reviews_has else "true")
        blocks.append(spec)
    sections_block = "\n\n".join(blocks)
    labels = ", ".join(grupo_secoes)

    prompt = (
        f"{shared_context}\n\n"
        f"Generate copy ONLY for: {labels}\n\n"
        f"Return MARKDOWN with EXACTLY this format:\n\n"
        f"{sections_block}\n\n"
        f"MARKDOWN ONLY. No JSON. No code blocks."
    )

    # Tentativa 1: sonnet
    try:
        resp = call_claude(
            system=SYSTEM_COPY_SENIOR,
            user=prompt,
            model="sonnet",
            max_tokens=1200,
            temperature=0.4,
            agent_name="arquiteto_mestre",
        )
    except Exception as e:
        print(f"[BlocoCopy] Grupo [{labels}] sonnet falhou, haiku: {e}")
        try:
            resp = call_claude(
                system=SYSTEM_COPY_SENIOR,
                user=prompt,
                model="haiku",
                max_tokens=1000,
                temperature=0.3,
                agent_name="arquiteto_mestre",
                respect_agent_config=False,
            )
        except Exception as e2:
            print(f"[BlocoCopy] Grupo [{labels}] haiku tambem falhou: {e2}")
            return None

    resp = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", resp)
    dados = parse_bloco2_with_fallback(resp)

    if dados and dados.get("sections"):
        grupo_set = set(s.lower() for s in grupo_secoes)
        filtered = [s for s in dados["sections"] if s.get("name", "").lower() in grupo_set]
        if filtered:
            return filtered

    return None


def _secoes_faltando(todas: list, todas_nomes: list) -> list:
    """Retorna secoes deterministicas para secoes que nao foram preenchidas."""
    nomes_existentes = {s["name"] for s in todas}
    faltando = [n for n in todas_nomes if n.lower() not in nomes_existentes]
    return faltando


def executar_bloco_copy(
    nome: str,
    cidade: str,
    segmento: str,
    telefone: str,
    endereco: str,
    rating: float,
    total_av: int,
    caio_tier: str,
    dark_mode: bool,
    jina_insights: str,
    instrucao_criativa: str,
    reviews_raw: list,
    seo_ctx: str,
    faq_seo_fmt: str,
    keyword_research: str,
    secoes_nomes: list,
    intel_ctx: str,
    craft_ctx: str,
    autocritica_ctx: str,
) -> dict:
    """Executa Bloco 2 (copy) com 4 chamadas LLM parciais.

    Cada chamada gera copy para 1-2 secoes, mantendo o prompt pequeno
    o suficiente para o proxy nao retornar 529 (Service Overloaded).

    Fallback: se um grupo falha, apenas suas secoes sao afetadas.
    Se todos os grupos falharem, retorna fallback deterministico completo.
    """
    from prompts_arquiteto import selecionar_top_reviews

    _reviews_sep = selecionar_top_reviews(reviews_raw)
    reviews_fmt, reviews_intel_ctx = _formatar_reviews(
        _reviews_sep["top_3"], _reviews_sep["insights"]
    )
    reviews_has = bool(reviews_raw)

    # Contexto compartilhado (montado uma vez)
    shared = _montar_contexto_shared(
        nome, cidade, segmento, telefone, endereco, rating, total_av,
        caio_tier, dark_mode, jina_insights, instrucao_criativa,
        reviews_fmt, reviews_intel_ctx, seo_ctx, faq_seo_fmt,
        keyword_research, reviews_has, craft_ctx, autocritica_ctx,
    )

    # Filtrar grupos para incluir apenas secoes solicitadas
    secoes_set = set(s.lower() for s in secoes_nomes)
    grupos_ativos = []
    for grupo in _GRUPOS_SECOES:
        relevantes = [s for s in grupo if s in secoes_set]
        if relevantes:
            grupos_ativos.append(relevantes)

    # 4 chamadas sequenciais
    todas_secoes: list = []
    falhas = 0

    for grupo in grupos_ativos:
        labels = ", ".join(grupo)
        print(f"[BlocoCopy] LLM grupo: [{labels}]")
        resultado = _callar_bloco_parcial(shared, grupo, reviews_has)
        if resultado:
            todas_secoes.extend(resultado)
        else:
            falhas += 1
            print(f"[BlocoCopy] Grupo [{labels}]: falhou — sera preenchido deterministicamente")

    # Todos falharam → fallback completo
    if falhas == len(grupos_ativos) or not todas_secoes:
        print("[BlocoCopy] Todos grupos falharam — fallback deterministico completo")
        return _copy_deterministica_fallback(
            nome=nome, cidade=cidade, segmento=segmento,
            telefone=telefone, endereco=endereco, rating=rating,
            total_av=total_av, secoes_nomes=secoes_nomes,
            reviews_raw=reviews_raw,
        )

    # Preencher secoes que nao foram geradas
    faltando = _secoes_faltando(todas_secoes, secoes_nomes)
    if faltando:
        fb = _copy_deterministica_fallback(
            nome=nome, cidade=cidade, segmento=segmento,
            telefone=telefone, endereco=endereco, rating=rating,
            total_av=total_av, secoes_nomes=faltando,
            reviews_raw=reviews_raw,
        )
        for sec in fb.get("sections", []):
            if sec["name"] not in {s["name"] for s in todas_secoes}:
                todas_secoes.append(sec)

    print(f"[BlocoCopy] OK: {len(todas_secoes)} secoes ({falhas} grupos falharam)")
    return {"sections": todas_secoes}
