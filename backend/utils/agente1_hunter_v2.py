"""
Agente 1 - Lead Hunter V2 (COM SCRAPING REAL)
Captura leads REAIS do Google Maps usando Playwright
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from google_local_scraper import GoogleLocalScraper as GoogleMapsScraper
import asyncio
import re

# salvar_memoria: stub local (na VPS usa o módulo real)
try:
    from memory import salvar_memoria
except ImportError:
    def salvar_memoria(key, data): pass

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
    horarios: Optional[List[str]] = []
    maps_url: Optional[str] = None
    atributos: Optional[List[str]] = []
    servicos: Optional[List[str]] = []
    faixa_preco: Optional[str] = None

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
]

DDDS_PERMITIDOS = [
    '11', '12', '13', '14', '15', '16', '17', '18', '19',  # SP
    '21', '22', '24',  # RJ
    '27', '28',  # ES
    '31', '32', '33', '34', '35', '37', '38',  # MG
    '41', '42', '43', '44', '45', '46',  # PR
    '47', '48', '49',  # SC
    '51', '53', '54', '55',  # RS
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

def validar_dados_minimos(lead: LeadRaw) -> tuple[bool, List[str]]:
    """
    Valida se lead tem dados mínimos para gerar site

    Returns:
        (dados_suficientes: bool, erros: List[str])
    """
    erros = []

    # Telefone
    if not lead.telefone or not validar_telefone_real(lead.telefone):
        erros.append("Telefone ausente ou inválido")

    # Reviews
    if not lead.reviews or len(lead.reviews) == 0:
        erros.append("Sem reviews")
    elif lead.reviews[0].get('texto') == 'Ótimo!':
        erros.append("Reviews genéricos (MOCK)")

    # Fotos
    if not lead.fotos or len(lead.fotos) == 0:
        erros.append("Sem fotos")
    elif 'placeholder.com' in lead.fotos[0]:
        erros.append("Fotos são PLACEHOLDER (MOCK)")

    # Endereço
    if not lead.endereco or len(lead.endereco) < 20:
        erros.append("Endereço incompleto")

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

    # Scraping do Google Maps
    async with GoogleMapsScraper(headless=True) as scraper:
        dados = await scraper.buscar_negocio(nome, cidade)

    if not dados:
        print(f"[Hunter V2] ❌ Negócio não encontrado no Google Maps")
        return None

    # Converter para LeadRaw
    lead = LeadRaw(
        nome=dados['nome'],
        cidade=cidade,
        segmento=dados.get('categoria', 'Negócio Local'),
        categoria=dados.get('categoria'),
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

    # Salvar memória
    salvar_memoria(f"hunter_v2_{lead.nome}", {
        "lead": lead.model_dump(),
        "score": resultado['score'],
        "tier": resultado['tier'],
        "dados_suficientes": True
    })

    return lead_qualificado

async def buscar_leads_google_maps(
    cidade: str,
    segmento: str,
    limite: int = 5,
    score_type: str = 'STANDARD',
    leads_existentes: set = None,
) -> List[LeadQualificado]:
    """
    Busca múltiplos leads no Google Search para um segmento/cidade.
    Usada pelo pipeline_endpoints_hunter.py

    Args:
        cidade: Cidade alvo (ex: "Curitiba")
        segmento: Nicho (ex: "academia", "barbearia")
        limite: Quantidade máxima de leads
        score_type: Tier mínimo aceito (PREMIUM, STANDARD, LOW)
        leads_existentes: set de nomes normalizados já no banco (lower+strip) — pula duplicatas

    Returns:
        Lista de LeadQualificado
    """
    _existentes = leads_existentes or set()
    print(f"\n[Hunter V2] Buscando {limite} leads: {segmento} em {cidade} ({len(_existentes)} ja existentes no banco)...")

    scraper = GoogleMapsScraper(headless=True)
    # Busca o dobro para compensar os que já existem no banco
    _buscar = max(limite * 2, limite + len(_existentes) + 5)
    resultados_raw = await scraper.buscar(segmento, cidade, limite=_buscar)

    leads_qualificados = []
    tiers_aceitos = {'PREMIUM', 'STANDARD', 'LOW'}
    if score_type == 'PREMIUM':
        tiers_aceitos = {'PREMIUM'}
    elif score_type == 'STANDARD':
        tiers_aceitos = {'PREMIUM', 'STANDARD'}

    for dados in resultados_raw:
        if len(leads_qualificados) >= limite:
            break

        # Pular leads já existentes no banco
        _nome_norm = dados.get('nome', '').lower().strip()
        if _nome_norm and _nome_norm in _existentes:
            print(f"[Hunter V2] SKIP duplicata: {dados.get('nome')}")
            continue

        try:
            lead = LeadRaw(
                nome=dados['nome'],
                cidade=cidade,
                segmento=dados.get('tipo', segmento),
                categoria=dados.get('tipo'),
                telefone=dados.get('telefone'),
                whatsapp=dados.get('telefone'),
                rating=dados.get('rating', 0),
                total_avaliacoes=dados.get('reviews', 0),
                reviews=[
                    {'autor': d.get('autor', ''), 'rating': d.get('rating', 5), 'texto': d.get('texto', ''), 'data': d.get('data', '')}
                    for d in dados.get('depoimentos', [])
                ],
                fotos=dados.get('fotos', []),
                website=dados.get('website', ''),
                endereco=dados.get('endereco', ''),
                maps_url=dados.get('maps_url'),
                atributos=dados.get('atributos', []),
                servicos=dados.get('servicos', []),
                faixa_preco=dados.get('faixa_preco'),
            )

            dados_suficientes, erros = validar_dados_minimos(lead)
            resultado = calcular_score(lead, cidade)

            if resultado['tier'] not in tiers_aceitos:
                print(f"[Hunter V2] SKIP {lead.nome} - tier {resultado['tier']} abaixo do mínimo")
                continue

            lead_qualificado = LeadQualificado(
                lead=lead,
                score=resultado['score'],
                tier=resultado['tier'],
                razoes=resultado['razoes'],
                sinais=resultado['sinais'],
                presenca_digital=resultado['presenca_digital'],
                dados_suficientes=dados_suficientes
            )

            leads_qualificados.append(lead_qualificado)
            print(f"[Hunter V2] OK {lead.nome} | Score: {resultado['score']} | Tier: {resultado['tier']}")

        except Exception as e:
            print(f"[Hunter V2] ERRO ao processar {dados.get('nome', '?')}: {e}")
            continue

    print(f"[Hunter V2] Total: {len(leads_qualificados)} leads qualificados")
    return leads_qualificados


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
