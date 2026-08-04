"""
Agente 1 - Lead Hunter V2 (COM SCRAPING REAL)
Captura leads REAIS do Google Maps.
Primary: gosom/google-maps-scraper (REST API, open-source)
Fallback: Playwright (google_local_scraper.py)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from utils.google_local_scraper import GoogleLocalScraper as GoogleMapsScraper
from utils.google_maps_gosom import buscar_gosom, buscar_negocio_gosom
import asyncio
import re

# salvar_memoria: stub local (na VPS usa o módulo real)
try:
    from memory import salvar_memoria
except ImportError:
    def salvar_memoria(key, data): pass

# ===== MAPA DE SINÔNIMOS POR NICHO =====
# Termos que o Google Maps usa vs o que o usuário busca
SINONIMOS_NICHO = {
    "dentistas": ["odontológica", "odontologica", "odonto", "dentista", "dentário", "dentario", "oral", "ortodontia", "implantes", "endodontia", "periodontia"],
    "dentista": ["odontológica", "odontologica", "odonto", "dentista", "dentário", "dentario", "oral", "ortodontia", "implantes"],
    "nutricionistas": ["nutricionista", "nutrição", "nutricao", "nutri", "dietista", "alimentação"],
    "nutricionista": ["nutricionista", "nutrição", "nutricao", "nutri", "dietista", "alimentação"],
    "academias": ["academia", "fitness", "musculação", "musculacao", "crossfit", "gym", "ginástica", "ginastica"],
    "academia": ["academia", "fitness", "musculação", "musculacao", "crossfit", "gym", "ginástica", "ginastica"],
    "psicólogos": ["psicólogo", "psicologo", "psicologia", "psicoterapia", "terapeuta", "terapia"],
    "psicologo": ["psicólogo", "psicologo", "psicologia", "psicoterapia", "terapeuta", "terapia"],
    "advogados": ["advogado", "advocacia", "jurídico", "juridico", "escritório de advocacia", "direito"],
    "advogado": ["advogado", "advocacia", "jurídico", "juridico", "escritório de advocacia", "direito"],
    "salão de beleza": ["salão", "salao", "beleza", "cabeleireiro", "cabeleireira", "hair", "barbearia", "estética", "estetica"],
    "barbearia": ["barbearia", "barbeiro", "barber", "salão masculino", "salao masculino"],
    "restaurantes": ["restaurante", "hamburgueria", "pizzaria", "churrascaria", "lanchonete", "bistrô", "bistro", "gastro", "culinária"],
    "hamburgueria": ["hamburgueria", "hambúrguer", "hamburguer", "burger", "lanchonete", "fast food"],
    "pizzaria": ["pizzaria", "pizza", "pizzas"],
    "pet shop": ["pet shop", "pet", "veterinário", "veterinaria", "banho e tosa", "animal", "clínica veterinária"],
    "veterinário": ["veterinário", "veterinaria", "vet", "animal", "pet", "clínica veterinária"],
    "fisioterapia": ["fisioterapia", "fisioterapeuta", "fisio", "reabilitação", "reabilitacao", "pilates", "rpg"],
    "personal trainer": ["personal", "trainer", "treinador", "preparador físico", "preparador fisico", "fitness"],
    "encanador": ["encanador", "hidráulica", "hidraulica", "encanamento", "bombeiro hidráulico"],
    "eletricista": ["eletricista", "elétrica", "eletrica", "instalação elétrica", "instalacao eletrica"],
    "contabilidade": ["contabilidade", "contador", "contábil", "contabil", "escritório contábil"],
    "imobiliária": ["imobiliária", "imobiliaria", "imóveis", "imoveis", "corretor", "corretora"],
    "clínica médica": ["clínica", "clinica", "médica", "medica", "consultório", "consultorio", "saúde", "saude"],
    "dermatologista": ["dermatologista", "dermatologia", "derma", "pele", "estética", "estetica"],
    "oftalmologista": ["oftalmologista", "oftalmologia", "olhos", "óptica", "optica", "ótica", "otica"],
    "mecânica": ["mecânica", "mecanica", "mecânico", "mecanico", "oficina", "auto center", "autocenter", "funilaria"],
    "autoescola": ["autoescola", "auto escola", "cfc", "habilitação", "habilitacao", "carteira de motorista"],
    "escola": ["escola", "colégio", "colegio", "ensino", "educação", "educacao", "curso"],
    "farmácia": ["farmácia", "farmacia", "drogaria", "medicamento"],
    "padaria": ["padaria", "panificadora", "confeitaria", "pão", "pao", "bakery"],
    "floricultura": ["floricultura", "flores", "florista", "arranjos"],
    "lavanderia": ["lavanderia", "lavagem", "lava", "tinturaria", "passadoria"],
}

# ===== MODELOS PYDANTIC =====

class LeadRaw(BaseModel):
    """Lead capturado do Google Maps"""
    nome: str
    cidade: str
    segmento: str
    categoria: Optional[str] = None
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    rating: float = 0
    total_avaliacoes: int = 0
    reviews: Optional[List[Dict[str, Any]]] = []
    fotos: Optional[List[str]] = []
    horarios: Optional[List[str]] = []
    website: Optional[str] = None
    endereco: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    maps_url: Optional[str] = None
    atributos: Optional[List[str]] = []
    servicos: Optional[List[str]] = []
    faixa_preco: Optional[str] = None
    logo_url: Optional[str] = None
    google_maps_embed: Optional[str] = None
    place_id: Optional[str] = None

class LeadQualificado(BaseModel):
    """Lead qualificado com score e tier"""
    lead: LeadRaw
    score: int = Field(..., ge=0, le=100)
    tier: str  # PREMIUM, STANDARD, LOW, DADOS_INSUFICIENTES, REJEITAR
    razoes: List[str] = []
    sinais: List[str] = []
    presenca_digital: str  # SITE, SOCIAL_ONLY, ZERO_PRESENCA
    dados_suficientes: bool = True  # ✅ NOVO: flag de validação

# ===== CONSTANTES =====

TELEFONES_FAKE = [
    '555511999887766',
    '5511999887766',
    '11999887766',
    '11999999999',
    '11111111111',
    '99999999999',
    '12345678900',
    '554100000000',
    '5541998765432',
]

# Padrões de endereço FAKE — nunca permitem passar
ENDERECO_FAKE_PATTERNS = [
    r'\bexemplo\b', r'\bnao informado\b', r'\bnão informado\b',
    r'\bs/n\b', r'\bsem numero\b', r'\bs/numero\b',
    r'\bav\.?\s+principal\b', r'\brua principal\b',
    r'\bcentro\b.*\bs/n\b', r'\b123\b.*\b456\b',
    r'\bavenida\s+teste\b', r'\brua\s+teste\b',
    r'\bendereco\s+falso\b', r'\bendereço\s+falso\b',
    r'\bcasa\s+\d+\b', r'\blote\s+\d+\b',
]

# Padrões de URL FAKE — domínios que não são reais
URL_FAKE_PATTERNS = [
    'example.com', 'example.org', 'example.net',
    'test.com', 'test.org', 'localhost',
    'placeholder.com', 'placeholder.org',
    '127.0.0.1', '0.0.0.0',
    'your-site.com', 'yoursite.com',
    'seusite.com', 'seudominio.com',
    'www.example', 'http://test',
]

# Nomes genéricos que indicam dado fake
NOME_FAKE_PATTERNS = [
    r'\bnegócio\s+local\b', r'\bempresa\s+xyz\b', r'\btest\s+-\s+academia\b',
    r'\bacademia\s+test\b', r'\bloja\s+teste\b', r'\bteste\s+\w+\b',
    r'\bexemplo\b.*\bacademia\b', r'\bexemplo\b.*\bbarbearia\b',
    r'\bexemplo\b.*\brestaurante\b', r'\bfictic\w+\b',
]

DDDS_PERMITIDOS = [
    '11', '12', '13', '14', '15', '16', '17', '18', '19',  # SP
    '21', '22', '24',  # RJ
    '27', '28',  # ES
    '31', '32', '33', '34', '35', '37', '38',  # MG
    '41', '42', '43', '44', '45', '46',  # PR
    '47', '48', '49',  # SC
    '51', '53', '54', '55',  # RS
    # Nordeste
    '71', '73', '74', '75', '77',  # BA
    '85', '88',  # CE
    '98', '99',  # MA
    '83',  # PB
    '81', '87',  # PE
    '86', '89',  # PI
    '84',  # RN
    '79',  # SE
    '82',  # AL
    # Norte
    '91', '93', '94',  # PA
    '92', '97',  # AM
    '69',  # RO
    '68',  # AC
    '95',  # RR
    '96',  # AP
    '63',  # TO
    # Centro-Oeste
    '61',  # DF
    '62', '64',  # GO
    '65', '66',  # MT
    '67',  # MS
]

# ===== VALIDAÇÕES =====

def validar_telefone_real(telefone: str) -> bool:
    """Valida se telefone é real (não fake)"""
    if not telefone:
        return False

    # Limpar telefone
    digits = re.sub(r'\D', '', telefone)

    # Remover código do país se tiver
    if digits.startswith('55'):
        digits = digits[2:]

    # Verificar se é fake
    if digits in TELEFONES_FAKE:
        print(f"[Hunter] ❌ Telefone FAKE detectado: {digits}")
        return False

    # Validar formato (11 dígitos: DDD + 9 + 8 dígitos)
    if len(digits) != 11:
        return False

    ddd = digits[:2]
    if ddd not in DDDS_PERMITIDOS:
        return False

    # Primeiro dígito do celular deve ser 9
    if digits[2] != '9':
        return False

    return True

def _contem_padroes_fakes(texto: str, patterns: list) -> bool:
    """Verifica se texto contém algum padrão de dado fake."""
    if not texto:
        return False
    t = texto.lower()
    return any(re.search(p, t) for p in patterns)


def validar_dados_nao_sao_fakes(lead: LeadRaw) -> tuple[bool, List[str]]:
    """Valida que NENHUM campo do lead contém dados falsos/placeholder.
    Returns:
        (ok: bool, erros: List[str])
    """
    erros = []

    # Nome
    if _contem_padroes_fakes(lead.nome, NOME_FAKE_PATTERNS):
        erros.append(f"Nome genérico/fake: '{lead.nome}'")

    # Telefone já validado por validar_telefone_real, mas checar padrões extras
    if lead.telefone:
        digits = re.sub(r'\D', '', lead.telefone)
        if digits in ['12345678', '1234567890', '00000000', '11111111']:
            erros.append(f"Telefone com dígitos repetidos: '{lead.telefone}'")

    # Endereço
    if lead.endereco and _contem_padroes_fakes(lead.endereco, ENDERECO_FAKE_PATTERNS):
        erros.append(f"Endereço fake/placeholder: '{lead.endereco[:60]}'")

    # Website
    if lead.website and _contem_padroes_fakes(lead.website, URL_FAKE_PATTERNS):
        erros.append(f"URL fake: '{lead.website}'")

    # Fotos — verificar se são placeholder
    for foto in (lead.fotos or []):
        if any(p in foto.lower() for p in ['placeholder', 'example.com', 'test.com', 'via.placeholder']):
            erros.append("Fotos são placeholder (não reais)")
            break

    # Logo URL
    if lead.logo_url and _contem_padroes_fakes(lead.logo_url, URL_FAKE_PATTERNS):
        erros.append(f"Logo URL fake: '{lead.logo_url}'")

    return (len(erros) == 0, erros)


def validar_dados_minimos(lead: LeadRaw) -> tuple[bool, List[str]]:
    """
    Valida se lead tem dados mínimos para gerar site.
    Inclui validação de dados fake/placeholder.
    """
    erros = []

    # Nome
    if not lead.nome or len(lead.nome.strip()) < 3:
        erros.append("Nome ausente ou muito curto")
    else:
        _nome_ok, _nome_erros = validar_dados_nao_sao_fakes(LeadRaw(
            nome=lead.nome, telefone="", endereco="", fotos=[], website="", logo_url=""
        ))
        if not _nome_ok:
            erros.extend(_nome_erros)

    # Telefone
    if not lead.telefone or not validar_telefone_real(lead.telefone):
        erros.append("Telefone ausente ou inválido")

    # Endereço
    if not lead.endereco or len(lead.endereco) < 15:
        erros.append("Endereço ausente ou muito curto")
    else:
        _end_ok, _end_erros = validar_dados_nao_sao_fakes(LeadRaw(
            nome="", telefone="", endereco=lead.endereco, fotos=[], website="", logo_url=""
        ))
        if not _end_ok:
            erros.extend(_end_erros)

    # Endereço
    if not lead.endereco or len(lead.endereco) < 15:
        erros.append("Endereço ausente ou muito curto")

    # Reviews
    if not lead.reviews or len(lead.reviews) == 0:
        erros.append("Sem reviews")
    elif lead.reviews[0].get('texto') == 'Ótimo!':
        erros.append("Reviews genéricos (MOCK)")

    # Fotos
    if not lead.fotos or len(lead.fotos) == 0:
        erros.append("Sem fotos")
    else:
        _fotos_ok, _fotos_erros = validar_dados_nao_sao_fakes(LeadRaw(
            nome="", telefone="", endereco="", fotos=lead.fotos or [], website="", logo_url=""
        ))
        if not _fotos_ok:
            erros.extend(_fotos_erros)

    # Dados fake globais (nome + telefone + endereco + fotos)
    _all_ok, _all_erros = validar_dados_nao_sao_fakes(lead)
    if not _all_ok:
        erros.extend(_all_erros)

    # Se 2 ou mais problemas críticos, dados insuficientes
    dados_suficientes = len(erros) < 2

    return dados_suficientes, erros


def validar_dados_minimos(lead: LeadRaw) -> tuple[bool, List[str]]:
    """
    Valida se lead tem dados mínimos para gerar site

    Returns:
        (dados_suficientes: bool, erros: List[str])
    """
    erros = []

    # Nome
    if not lead.nome or len(lead.nome.strip()) < 3:
        erros.append("Nome ausente ou muito curto")
    elif _contem_padroes_fakes(lead.nome, NOME_FAKE_PATTERNS):
        erros.append(f"Nome genérico/fake: '{lead.nome}'")

    # Telefone
    if not lead.telefone or not validar_telefone_real(lead.telefone):
        erros.append("Telefone ausente ou inválido")
    elif re.sub(r'\D', '', lead.telefone) in ['12345678', '1234567890', '00000000', '11111111']:
        erros.append("Telefone com dígitos repetidos")

    # Endereço
    if not lead.endereco or len(lead.endereco) < 15:
        erros.append("Endereço ausente ou muito curto")
    elif _contem_padroes_fakes(lead.endereco, ENDERECO_FAKE_PATTERNS):
        erros.append(f"Endereço fake/placeholder: '{lead.endereco[:60]}'")

    # Website
    if lead.website and _contem_padroes_fakes(lead.website, URL_FAKE_PATTERNS):
        erros.append(f"URL fake: '{lead.website}'")

    # Reviews
    if not lead.reviews or len(lead.reviews) == 0:
        erros.append("Sem reviews")
    elif lead.reviews[0].get('texto') == 'Ótimo!':
        erros.append("Reviews genéricos (MOCK)")

    # Fotos
    if not lead.fotos or len(lead.fotos) == 0:
        erros.append("Sem fotos")
    else:
        for foto in lead.fotos:
            if any(p in foto.lower() for p in ['placeholder', 'example.com', 'test.com', 'via.placeholder']):
                erros.append("Fotos são placeholder (não reais)")
                break

    # Logo URL
    if lead.logo_url and _contem_padroes_fakes(lead.logo_url, URL_FAKE_PATTERNS):
        erros.append(f"Logo URL fake: '{lead.logo_url}'")

    # Se 2 ou mais problemas críticos, dados insuficientes
    dados_suficientes = len(erros) < 2

    return dados_suficientes, erros

def calcular_score(lead: LeadRaw, cidade: str) -> Dict[str, Any]:
    """Calcula score de qualificação do lead"""
    score = 0
    razoes = []
    sinais = []

    # Rating (0-20 pontos)
    if lead.rating >= 4.5:
        score += 20
        sinais.append("Rating excelente")
    elif lead.rating >= 4.0:
        score += 15
        sinais.append("Rating bom")
    elif lead.rating >= 3.5:
        score += 10

    # Reviews (0-20 pontos)
    if lead.total_avaliacoes >= 50:
        score += 20
        sinais.append("Muitas avaliações")
    elif lead.total_avaliacoes >= 20:
        score += 15
        sinais.append("Boas avaliações")
    elif lead.total_avaliacoes >= 10:
        score += 10

    # Telefone (0-15 pontos)
    if validar_telefone_real(lead.telefone):
        score += 15
        sinais.append("Telefone válido")

    # Fotos (0-10 pontos)
    if lead.fotos and len(lead.fotos) >= 5:
        score += 10
        sinais.append("Muitas fotos")
    elif lead.fotos and len(lead.fotos) >= 3:
        score += 7

    # Website (0-10 pontos)
    if lead.website:
        score += 10
        sinais.append("Tem website")
        presenca_digital = "SITE"
    else:
        presenca_digital = "ZERO_PRESENCA"

    # Endereço completo (0-10 pontos)
    if lead.endereco and len(lead.endereco) > 30:
        score += 10
        sinais.append("Endereço completo")

    # Horários (0-5 pontos)
    if lead.horarios and len(lead.horarios) > 0:
        score += 5

    # Reviews com texto (0-10 pontos)
    if lead.reviews and len(lead.reviews) >= 3:
        score += 10
        sinais.append("Reviews detalhados")

    # Determinar tier
    if score >= 80:
        tier = "PREMIUM"
        razoes.append("Score alto, lead qualificado")
    elif score >= 60:
        tier = "STANDARD"
        razoes.append("Score médio, lead aceitável")
    elif score >= 40:
        tier = "LOW"
        razoes.append("Score baixo, lead marginal")
    else:
        tier = "REJEITAR"
        razoes.append("Score muito baixo")

    return {
        'score': score,
        'tier': tier,
        'razoes': razoes,
        'sinais': sinais,
        'presenca_digital': presenca_digital
    }

# ===== FUNÇÃO PRINCIPAL =====

async def buscar_lead_google_maps(
    nome: str,
    cidade: str
) -> Optional[LeadQualificado]:
    """
    Busca lead REAL no Google Maps usando Playwright

    Args:
        nome: Nome do negócio (ex: "Barbearia Premium")
        cidade: Cidade (ex: "Curitiba")

    Returns:
        LeadQualificado ou None se não encontrado/dados insuficientes
    """
    print(f"\n[Hunter V2] Buscando: {nome} em {cidade}...")

    # PRIMARY: gosom REST API
    dados = await buscar_negocio_gosom(nome, cidade)

    # FALLBACK: Playwright
    if not dados:
        print(f"[Hunter V2] Gosom falhou — tentando Playwright...")
        async with GoogleMapsScraper(headless=True) as scraper:
            dados = await scraper.buscar_negocio(nome, cidade)

    if not dados:
        print(f"[Hunter V2] Negócio não encontrado no Google Maps")
        return None

    # Converter para LeadRaw
    _segmento_raw = dados.get('categoria') or segmento or 'Negócio Local'
    lead = LeadRaw(
        nome=dados['nome'],
        cidade=cidade,
        segmento=_segmento_raw,
        categoria=dados.get('categoria') or segmento,
        telefone=dados.get('telefone'),
        whatsapp=dados.get('telefone'),  # Assumir que telefone é WhatsApp
        rating=dados.get('rating', 0),
        total_avaliacoes=dados.get('total_avaliacoes', 0),
        reviews=dados.get('reviews', []),
        fotos=dados.get('fotos', []),
        horarios=dados.get('horarios', []),
        website=dados.get('website'),
        endereco=dados.get('endereco'),
        maps_url=dados.get('maps_url'),
        atributos=dados.get('atributos', []),
        servicos=dados.get('servicos', []),
        faixa_preco=dados.get('faixa_preco'),
        logo_url=dados.get('logo', '') or '',
        google_maps_embed=dados.get('google_maps_embed', '') or '',
        place_id=dados.get('place_id', '') or '',
    )

    # ✅ VALIDAR DADOS MÍNIMOS
    dados_suficientes, erros = validar_dados_minimos(lead)

    if not dados_suficientes:
        print(f"[Hunter V2] ⚠️ DADOS INSUFICIENTES:")
        for erro in erros:
            print(f"   - {erro}")

        # Retornar lead com tier "DADOS_INSUFICIENTES"
        return LeadQualificado(
            lead=lead,
            score=0,
            tier="DADOS_INSUFICIENTES",
            razoes=erros,
            sinais=[],
            presenca_digital="ZERO_PRESENCA",
            dados_suficientes=False
        )

    # Calcular score
    resultado = calcular_score(lead, cidade)

    # Criar LeadQualificado
    lead_qualificado = LeadQualificado(
        lead=lead,
        score=resultado['score'],
        tier=resultado['tier'],
        razoes=resultado['razoes'],
        sinais=resultado['sinais'],
        presenca_digital=resultado['presenca_digital'],
        dados_suficientes=True
    )

    print(f"[Hunter V2] ✅ Lead qualificado: {lead.nome}")
    print(f"   Score: {resultado['score']}/100")
    print(f"   Tier: {resultado['tier']}")
    print(f"   Sinais: {', '.join(resultado['sinais'][:3])}")
    print(f"   Dados suficientes: ✅")

    # Memória do hunter so e usada em testes locais (singular).
    # Em producao, buscar_leads_google_maps (plural) e chamado e nao precisa de memoria por lead.
    # Mantemos como no-op silencioso se user_id nao for fornecido.

    return lead_qualificado


# ═══════════════════════════════════════════════════════════════
# CACHE GLOBAL DE LEADS — evita Playwright se já buscou antes
# ═══════════════════════════════════════════════════════════════

def _buscar_cache_leads(segmento: str, cidade: str, existentes: set, limite: int) -> List['LeadQualificado']:
    """Busca leads no cache global (tabela leads_cache). Retorna lista de LeadQualificado ou []."""
    try:
        from database import engine
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = conn.execute(_text("""
                SELECT nome, cidade, segmento, telefone, rating, total_avaliacoes,
                       website, endereco, maps_url, fotos, servicos, horarios, logo_url,
                       atributos, faixa_preco, reviews_json
                FROM leads_cache
                WHERE lower(segmento) = lower(:seg) AND lower(cidade) = lower(:cid)
                  AND criado_em > NOW() - INTERVAL '7 days'
                ORDER BY rating DESC NULLS LAST
                LIMIT :lim
            """), {"seg": segmento, "cid": cidade, "lim": limite + len(existentes) + 5}).fetchall()

        if not rows:
            return []

        import json as _json_cache
        leads = []
        for r in rows:
            nome = r[0] or ''
            if nome.lower().strip() in existentes:
                continue
            if len(leads) >= limite:
                break
            # Pular leads sem reviews no cache (Caio vai rejeitar)
            _cached_reviews = []
            if r[15]:
                try:
                    _cached_reviews = _json_cache.loads(r[15])
                except:
                    _cached_reviews = []
            if not _cached_reviews:
                continue
            try:
                lead = LeadRaw(
                    nome=nome, cidade=r[1] or cidade, segmento=r[2] or segmento,
                    telefone=r[3], rating=r[4] or 0, total_avaliacoes=r[5] or 0,
                    website=r[6], endereco=r[7], maps_url=r[8],
                    fotos=_json_cache.loads(r[9]) if r[9] else [],
                    servicos=_json_cache.loads(r[10]) if r[10] else [],
                    horarios=_json_cache.loads(r[11]) if r[11] else [],
                    logo_url=r[12],
                    atributos=_json_cache.loads(r[13]) if r[13] else [],
                    faixa_preco=r[14],
                    reviews=_cached_reviews,
                )
                resultado = calcular_score(lead, cidade)
                dados_suficientes, _ = validar_dados_minimos(lead)
                leads.append(LeadQualificado(
                    lead=lead, score=resultado['score'], tier=resultado['tier'],
                    razoes=resultado['razoes'], sinais=resultado['sinais'],
                    presenca_digital=resultado['presenca_digital'],
                    dados_suficientes=dados_suficientes
                ))
            except Exception:
                continue
        return leads
    except Exception as e:
        print(f"[Hunter Cache] Erro ao buscar cache: {e}")
        return []


def _salvar_cache_leads(leads: List['LeadQualificado'], segmento: str, cidade: str):
    """Salva leads no cache global pra reutilização entre tenants."""
    try:
        from database import engine
        from sqlalchemy import text as _text
        import json as _json_cache
        with engine.connect() as conn:
            for lq in leads:
                l = lq.lead
                conn.execute(_text("""
                    INSERT INTO leads_cache (nome, cidade, segmento, telefone, rating, total_avaliacoes,
                        website, endereco, maps_url, fotos, servicos, horarios, logo_url,
                        atributos, faixa_preco, reviews_json, criado_em)
                    VALUES (:nome, :cidade, :seg, :tel, :rating, :aval, :web, :end, :maps,
                        :fotos, :servicos, :horarios, :logo, :atrib, :faixa, :reviews, NOW())
                    ON CONFLICT (lower(nome), lower(cidade)) DO UPDATE SET
                        rating = EXCLUDED.rating, telefone = COALESCE(EXCLUDED.telefone, leads_cache.telefone),
                        atualizado_em = NOW()
                """), {
                    "nome": l.nome, "cidade": l.cidade, "seg": segmento,
                    "tel": l.telefone, "rating": l.rating, "aval": l.total_avaliacoes,
                    "web": l.website, "end": l.endereco, "maps": l.maps_url,
                    "fotos": _json_cache.dumps(l.fotos or []),
                    "servicos": _json_cache.dumps(l.servicos or []),
                    "horarios": _json_cache.dumps(l.horarios or []),
                    "logo": getattr(l, 'logo_url', None),
                    "atrib": _json_cache.dumps(l.atributos or []),
                    "faixa": l.faixa_preco,
                    "reviews": _json_cache.dumps([{"autor": r.get("autor",""), "texto": r.get("texto",""), "rating": r.get("rating",5)} for r in (l.reviews or [])[:5]]),
                })
            conn.commit()
        print(f"[Hunter Cache] Salvou {len(leads)} leads no cache ({segmento}/{cidade})")
    except Exception as e:
        print(f"[Hunter Cache] Erro ao salvar cache: {e}")


async def buscar_leads_google_maps(
    cidade: str,
    segmento: str,
    limite: int = 5,
    score_type: str = 'STANDARD',
    leads_existentes: set = None,
    force_fresh: bool = False,
) -> List[LeadQualificado]:
    """
    Busca leads no Google Maps com estrategia LAZY:
    1. Captura cards basicos (leve)
    2. Para cada card: busca detalhes -> qualifica -> aceita/rejeita
    3. Para quando atingir limite de aprovados
    """
    _existentes = leads_existentes or set()
    print(f"[Hunter V2] Buscando {limite} leads LAZY: {segmento} em {cidade} ({len(_existentes)} ja existentes)...")

    # ── CACHE GLOBAL: verificar se já temos leads cacheados pra este segmento+cidade ──
    if force_fresh:
        print(f"[Hunter V2] FORCE FRESH: ignorando cache, buscando direto no Maps")
        cached_leads = []
    else:
        cached_leads = _buscar_cache_leads(segmento, cidade, _existentes, limite)
    if cached_leads and len(cached_leads) >= limite:
        print(f"[Hunter V2] ✅ CACHE HIT: {len(cached_leads)} leads do cache (sem scraping)")
        return cached_leads[:limite]

    # ── PRIMARY: gosom/google-maps-scraper (REST API, open-source) ──
    cards_raw = None
    _busca_limite = max(20, limite * 4)

    gosom_results = await buscar_gosom(segmento, cidade, limite=_busca_limite)
    if gosom_results and len(gosom_results) > 0:
        cards_raw = gosom_results
        print(f"[Hunter V2] ✅ GOSOM: {len(cards_raw)} leads capturados")
    else:
        # ── FALLBACK: Playwright (google_local_scraper.py) ──
        print(f"[Hunter V2] Gosom indisponível — usando Playwright...")
        scraper = GoogleMapsScraper(headless=True)
        cards_raw = await scraper.buscar(segmento, cidade, limite=_busca_limite, leads_existentes=_existentes)

    print(f"[Hunter V2] {len(cards_raw)} leads com detalhes capturados")

    leads_encontrados = []

    # Ordenar cards por reviews (mais reviews primeiro) — prioriza leads com depoimentos
    cards_raw.sort(key=lambda c: c.get('reviews', 0) if isinstance(c.get('reviews', 0), int) else 0, reverse=True)

    # FASE 2: Loop LAZY — detalhe de 1, qualifica, aceita/rejeita
    # Para no primeiro lead com score suficiente E reviews reais
    for dados in cards_raw:
        if len(leads_encontrados) >= limite:
            break

        nome = dados.get('nome', '').strip()
        if not nome or len(nome) < 3:
            continue

        # Validar que o lead pertence ao segmento buscado
        tipo_real = (dados.get('tipo') or '').strip()
        if tipo_real:
            # Se o tipo real do Google Maps não tem relação com o segmento buscado, pular
            _seg_lower = segmento.lower().strip()
            _tipo_lower = tipo_real.lower().strip()

            # 1. Match direto
            _match = (
                _seg_lower in _tipo_lower or
                _tipo_lower in _seg_lower or
                any(p in _tipo_lower for p in _seg_lower.split() if len(p) > 3) or
                any(p in _seg_lower for p in _tipo_lower.split() if len(p) > 3)
            )

            # 2. Match por sinônimos
            if not _match:
                _sinonimos = SINONIMOS_NICHO.get(_seg_lower, [])
                if _sinonimos:
                    _match = any(sin in _tipo_lower for sin in _sinonimos)

                # Fallback: buscar em todas as chaves que contenham o segmento
                if not _match:
                    for _chave, _sins in SINONIMOS_NICHO.items():
                        if _seg_lower in _chave or _chave in _seg_lower:
                            if any(sin in _tipo_lower for sin in _sins):
                                _match = True
                                break

            if not _match:
                print(f"[Hunter V2] SKIP nicho errado: {nome} (tipo={tipo_real}, buscado={segmento})")
                continue

        # Pular leads ja existentes no banco
        _nome_norm = nome.lower().strip()
        if _nome_norm and _nome_norm in _existentes:
            print(f"[Hunter V2] SKIP duplicata: {nome}")
            continue

        # Detalhes já vêm do scraper.buscar() — não precisa abrir browser separado

        try:
            lead = LeadRaw(
                nome=dados['nome'],
                cidade=cidade,
                segmento=tipo_real if tipo_real else segmento,
                categoria=dados.get('tipo'),
                telefone=dados.get('telefone'),
                whatsapp=dados.get('telefone'),
                rating=dados.get('rating', 0),
                total_avaliacoes=dados.get('reviews', 0) or len(dados.get('depoimentos', [])),
                reviews=[
                    {'autor': d.get('autor', ''), 'rating': d.get('rating', 5), 'texto': d.get('texto', ''), 'data': d.get('data', '')}
                    for d in dados.get('depoimentos', [])
                ],
                fotos=dados.get('fotos', []),
                website=dados.get('website', ''),
                endereco=dados.get('endereco', ''),
                latitude=dados.get('latitude') or dados.get('lat'),
                longitude=dados.get('longitude') or dados.get('lng'),
                horarios=dados.get('horarios') or dados.get('hours') or dados.get('opening_hours') or [],
                logo_url=dados.get('logo_url') or dados.get('logo'),
                maps_url=dados.get('maps_url'),
                atributos=dados.get('atributos', []),
                servicos=dados.get('servicos', []),
                faixa_preco=dados.get('faixa_preco'),
                google_maps_embed=dados.get('google_maps_embed', '') or '',
                place_id=dados.get('place_id', '') or '',
            )

            resultado = calcular_score(lead, cidade)
            dados_suficientes, erros = validar_dados_minimos(lead)

            lead_qualificado = LeadQualificado(
                lead=lead,
                score=resultado['score'],
                tier=resultado['tier'],
                razoes=resultado['razoes'],
                sinais=resultado['sinais'],
                presenca_digital=resultado['presenca_digital'],
                dados_suficientes=dados_suficientes
            )

            leads_encontrados.append(lead_qualificado)
            print(f"[Hunter V2] APROVADO {lead.nome} | Score: {resultado['score']} | Tier: {resultado['tier']}")

        except Exception as e:
            print(f"[Hunter V2] ERRO ao processar {dados.get('nome', '?')}: {e}")
            continue

    print(f"[Hunter V2] Total: {len(leads_encontrados)} leads coletados")

    # Ordenar por score (maior primeiro)
    leads_encontrados.sort(key=lambda lq: lq.score, reverse=True)

    # Salvar no cache global pra próximos tenants
    if leads_encontrados:
        _salvar_cache_leads(leads_encontrados, segmento, cidade)

    return leads_encontrados[:limite]

# ===== TESTE =====

if __name__ == "__main__":
    async def testar():
        # Testar com barbearia real
        lead = await buscar_lead_google_maps("Barbearia Seu Zé", "Curitiba")

        if lead:
            print(f"\n[Teste] ✅ Lead capturado!")
            print(f"   Nome: {lead.lead.nome}")
            print(f"   Score: {lead.score}/100")
            print(f"   Tier: {lead.tier}")
            print(f"   Telefone: {lead.lead.telefone}")
            print(f"   Rating: {lead.lead.rating}/5")
            print(f"   Reviews: {lead.lead.total_avaliacoes}")
            print(f"   Fotos: {len(lead.lead.fotos or [])}")
            print(f"   Dados suficientes: {'✅' if lead.dados_suficientes else '❌'}")
        else:
            print("\n[Teste] ❌ Nenhum lead capturado")

    asyncio.run(testar())
