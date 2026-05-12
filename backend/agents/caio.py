import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Caio - Qualificador de Leads (Python puro, zero LLM)
Regras determinísticas de if/else.
"""
import requests
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class LeadInput(BaseModel):
    nome: str
    cidade: str
    segmento: str
    telefone: str
    whatsapp: Optional[str] = None
    rating: float = 0.0
    reviews_count: int = 0
    fotos: Optional[List[str]] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    social: Optional[str] = None
    reprocessamento: bool = False  # Pula verificacao de segmento

class CaioOutput(BaseModel):
    qualificacao: str = Field(description="QUENTE/MORNO/FRIO/REJEITADO")
    score: int = Field(description="Score 0-100")
    motivo: str = Field(description="Justificativa")
    colors: Optional[dict] = Field(default=None)
    tier: Optional[str] = Field(default=None)
    qualificado: bool = Field(default=True)
    nome: str = ""
    cidade: str = ""
    segmento: str = ""
    reviews: List[Dict] = []
    nicho: str = ""
    telefone: str = ""
    whatsapp: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    fotos: List[str] = []
    website: str = ""
    logo_url: str = ""
    concorrentes: List[Dict] = []
    paleta_cores: Dict[str, str] = {}


REDES_CONHECIDAS = [
    "smart fit", "smartfit", "bio ritmo", "bioritmo", "bluefit", "blue fit",
    "bodytech", "body tech", "competition", "formula academia",
    "selfit", "sel fit", "velocity", "runner", "cia athletica", "companhia athletica",
    "phd sports", "ph.d sports", "pratique fitness", "just fit", "curves",
    "unidade", "filial", "matriz",
    "coco bambu", "mcdonald", "starbucks", "burger king", "subway", "outback",
    "giraffas", "habib", "spoleto", "domino", "pizza hut", "kfc", "popeyes",
    "carrefour", "extra", "walmart", "casas bahia",
    "magazine luiza", "americanas", "submarino",
]

REDES_SOCIAIS = [
    "instagram.com", "facebook.com", "fb.com", "linkedin.com",
    "twitter.com", "tiktok.com", "youtube.com", "whatsapp.com",
]

SITE_BUILDERS = [
    "wix.com", "wordpress.com", "blogspot.com", "weebly.com",
    "squarespace.com", "webnode.com", "site123.com", "jimdo.com", "strikingly.com",
]


# Mapa de palavras-chave por segmento para filtro de relevancia
_SEGMENTO_KEYWORDS = {
    "nutricionista": ["nutri", "nutricao", "nutricionist", "dieta", "alimenta", "emagre", "performance"],
    "academia": ["academi", "gym", "fitness", "muscula", "treino", "crossfit", "pilates", "personal"],
    "barbearia": ["barbe", "barber", "cabelo", "corte", "navalha"],
    "salao": ["salao", "salon", "cabele", "beleza", "estetica", "unhas", "manicure"],
    "clinica": ["clinic", "medic", "saude", "hospital", "consulto", "terapia", "fisio"],
    "dentista": ["dent", "odonto", "sorriso", "ortodon", "implant"],
    "restaurante": ["restaur", "comida", "culinaria", "gastrono", "bistr", "churrasco", "pizz"],
    "lanchonete": ["lanch", "burger", "hamburguer", "sanduiche", "fast"],
    "padaria": ["padaria", "padao", "paes", "confeit", "doce", "bolo"],
    "estetica": ["estet", "beleza", "spa", "massagem", "depila", "skin", "facial"],
    "advocacia": ["advog", "juridic", "direito", "law", "escritorio"],
    "psicologia": ["psicol", "terapia", "mental", "emocional"],
    "pet": ["pet", "animal", "veterin", "caes", "gatos", "dog", "cat"],
    "imobiliaria": ["imobil", "imoveis", "corretor", "aluguel", "venda"],
    "farmacia": ["farmac", "drogaria", "medicamento", "remedio"],
    "auto": ["auto", "mecanica", "carro", "veiculo", "oficina", "funilaria"],
}

def _verificar_relevancia_segmento(nome, segmento_pedido):
    seg = segmento_pedido.lower().strip()
    nome_lower = nome.lower()
    keywords = None
    for key, kws in _SEGMENTO_KEYWORDS.items():
        if key in seg:
            keywords = kws
            break
    if not keywords:
        return True
    for kw in keywords:
        if kw in nome_lower:
            return True
    return False


def verificar_se_e_rede(nome: str, website: str = "") -> bool:
    nome_lower = nome.lower()
    website_lower = website.lower() if website else ""
    for rede in REDES_CONHECIDAS:
        if rede in nome_lower or rede in website_lower:
            return True
    return False


def validar_site(website: str) -> tuple:
    if not website or not website.strip():
        return False, "Sem site"
    website_lower = website.lower()
    for rede in REDES_SOCIAIS:
        if rede in website_lower:
            return False, "Site e rede social"
    for builder in SITE_BUILDERS:
        if builder in website_lower:
            return False, "Site em builder de baixa qualidade"
    try:
        url = website if website.startswith(("http://", "https://")) else "https://" + website
        response = requests.head(url, timeout=3, allow_redirects=True)
        if response.status_code >= 400:
            return False, "Site offline (HTTP {})".format(response.status_code)
        final_url = response.url.lower()
        for rede in REDES_SOCIAIS:
            if rede in final_url:
                return False, "Site redireciona para rede social"
        return True, "Site valido"
    except requests.exceptions.Timeout:
        return False, "Site muito lento (timeout)"
    except requests.exceptions.ConnectionError:
        return False, "Site offline"
    except Exception as e:
        return False, "Erro ao verificar site: {}".format(e)


def _calcular_score(lead: LeadInput) -> tuple:
    score = 0
    motivos = []

    if lead.rating >= 4.8:
        score += 40; motivos.append("rating excelente (>=4.8)")
    elif lead.rating >= 4.5:
        score += 30; motivos.append("rating muito bom (>=4.5)")
    elif lead.rating >= 4.0:
        score += 20; motivos.append("rating bom (>=4.0)")
    elif lead.rating >= 3.5:
        score += 10; motivos.append("rating regular (>=3.5)")
    else:
        motivos.append("rating baixo (<3.5)")

    if lead.reviews_count >= 200:
        score += 30; motivos.append("muitas avaliacoes (>=200)")
    elif lead.reviews_count >= 100:
        score += 25; motivos.append("boas avaliacoes (>=100)")
    elif lead.reviews_count >= 50:
        score += 20; motivos.append("avaliacoes razoaveis (>=50)")
    elif lead.reviews_count >= 20:
        score += 10; motivos.append("poucas avaliacoes (>=20)")
    else:
        motivos.append("avaliacoes insuficientes (<20)")

    if not lead.website or not lead.website.strip():
        score += 20; motivos.append("sem site (oportunidade)")
    else:
        site_valido, _ = validar_site(lead.website)
        if not site_valido:
            score += 15; motivos.append("site invalido/rede social (oportunidade)")

    n_fotos = len(lead.fotos) if lead.fotos else 0
    if n_fotos >= 5:
        score += 10; motivos.append("{} fotos disponiveis".format(n_fotos))
    elif n_fotos >= 2:
        score += 5; motivos.append("{} fotos disponiveis".format(n_fotos))

    return min(score, 100), motivos


def qualificar_lead(lead: LeadInput) -> CaioOutput:
    """Qualifica lead via regras Python puras. Zero LLM."""

    if not lead.reprocessamento and not _verificar_relevancia_segmento(lead.nome, lead.segmento):
        print("[Caio] REJEITADO: {} - nao relevante para segmento {}".format(lead.nome, lead.segmento))
        return CaioOutput(
            qualificacao="REJEITADO", score=0, tier="REJEITADO",
            motivo="Lead nao relevante para o segmento pedido", qualificado=False,
            nome=lead.nome, cidade=lead.cidade, segmento=lead.segmento,
            telefone=lead.telefone, whatsapp=lead.whatsapp or "",
            rating=lead.rating, reviews_count=lead.reviews_count,
            fotos=lead.fotos or [], website=lead.website or "",
            logo_url=lead.logo_url or "", concorrentes=[],
            paleta_cores={"primaria": "#374151", "secundaria": "#f9fafb", "acento": "#6366f1"},
        )

    if verificar_se_e_rede(lead.nome, lead.website or ""):
        print("[Caio] REJEITADO: {} - rede/franquia".format(lead.nome))
        return CaioOutput(
            qualificacao="REJEITADO", score=0, tier="REJEITADO",
            motivo="Rede/franquia - nao atendemos", qualificado=False,
            nome=lead.nome, cidade=lead.cidade, segmento=lead.segmento,
            telefone=lead.telefone, whatsapp=lead.whatsapp or "",
            rating=lead.rating, reviews_count=lead.reviews_count,
            fotos=lead.fotos or [], website=lead.website or "",
            logo_url=lead.logo_url or "", concorrentes=[],
            paleta_cores={"primaria": "#374151", "secundaria": "#f9fafb", "acento": "#6366f1"},
        )

    if lead.website and lead.website.strip():
        site_valido, motivo_site = validar_site(lead.website)
        if site_valido:
            print("[Caio] REJEITADO: {} - {}".format(lead.nome, motivo_site))
            return CaioOutput(
                qualificacao="REJEITADO", score=0, tier="REJEITADO",
                motivo="Lead ja possui site proprio valido", qualificado=False,
                nome=lead.nome, cidade=lead.cidade, segmento=lead.segmento,
                telefone=lead.telefone, whatsapp=lead.whatsapp or "",
                rating=lead.rating, reviews_count=lead.reviews_count,
                fotos=lead.fotos or [], website=lead.website or "",
                logo_url=lead.logo_url or "", concorrentes=[],
                paleta_cores={"primaria": "#374151", "secundaria": "#f9fafb", "acento": "#6366f1"},
            )

    score, motivos = _calcular_score(lead)

    if score >= 70:
        qualificacao, tier = "QUENTE", "PREMIUM"
    elif score >= 45:
        qualificacao, tier = "MORNO", "STANDARD"
    elif score >= 20:
        qualificacao, tier = "FRIO", "BASIC"
    else:
        qualificacao, tier = "REJEITADO", "REJEITADO"

    motivo = " | ".join(motivos) if motivos else "Score calculado por regras"

    paleta = {}

    print("[Caio] {} -> {} (score={}, tier={})".format(lead.nome, qualificacao, score, tier))

    return CaioOutput(
        qualificacao=qualificacao, score=score, tier=tier,
        motivo=motivo, qualificado=qualificacao != "REJEITADO",
        nome=lead.nome, cidade=lead.cidade, segmento=lead.segmento,
        telefone=lead.telefone, whatsapp=lead.whatsapp or "",
        rating=lead.rating, reviews_count=lead.reviews_count,
        fotos=lead.fotos or [], website=lead.website or "",
        logo_url=lead.logo_url or "", concorrentes=[],
        paleta_cores=paleta,
    )


if __name__ == "__main__":
    lead = LeadInput(
        nome="Academia Forca Total",
        cidade="Curitiba",
        segmento="Academia",
        telefone="41985143249",
        whatsapp="5541985143249",
        rating=4.7,
        reviews_count=120,
        fotos=[],
        website="",
        logo_url=None,
    )
    out = qualificar_lead(lead)
    print("Resultado: {} | score={} | tier={}".format(out.qualificacao, out.score, out.tier))
    print("Motivo: {}".format(out.motivo))
