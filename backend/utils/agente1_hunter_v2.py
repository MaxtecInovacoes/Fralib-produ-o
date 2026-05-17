"""
Agente 1 - Lead Hunter V2 (COM SCRAPING REAL)
Captura leads REAIS do Google Maps usando Playwright
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from utils.google_local_scraper import GoogleLocalScraper as GoogleMapsScraper
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
    maps_url: Optional[str] = None
    atributos: Optional[List[str]] = []
    servicos: Optional[List[str]] = []
    faixa_preco: Optional[str] = None
    logo_url: Optional[str] = None
    google_maps_embed: Optional[str] = None

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
    cached_leads = _buscar_cache_leads(segmento, cidade, _existentes, limite)
    if cached_leads and len(cached_leads) >= limite:
        print(f"[Hunter V2] ✅ CACHE HIT: {len(cached_leads)} leads do cache (sem Playwright)")
        return cached_leads[:limite]

    scraper = GoogleMapsScraper(headless=True)

    # Buscar leads COM detalhes (reviews, horários, fotos) em 1 sessão de browser
    # Buscar poucos a mais que o limite pra ter opção se o primeiro não tiver reviews
    _buscar = limite + 2
    cards_raw = await scraper.buscar(segmento, cidade, limite=_buscar)
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
            _seg_lower = segmento.lower()
            _tipo_lower = tipo_real.lower()
            # Verificar se há alguma relação semântica
            _match = (
                _seg_lower in _tipo_lower or
                _tipo_lower in _seg_lower or
                any(p in _tipo_lower for p in _seg_lower.split()) or
                any(p in _seg_lower for p in _tipo_lower.split())
            )
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
            )

            resultado = calcular_score(lead, cidade)
            dados_suficientes, erros = validar_dados_minimos(lead)

            # Preferir leads com reviews reais (mínimo 3 pra ter depoimentos no site)
            _has_reviews = lead.reviews and len(lead.reviews) >= 3
            if not _has_reviews and len(leads_encontrados) == 0:
                # Guardar como fallback mas continuar buscando um com reviews
                if not hasattr(buscar_leads_google_maps, '_fallback'):
                    buscar_leads_google_maps._fallback = []
                buscar_leads_google_maps._fallback.append(LeadQualificado(
                    lead=lead, score=resultado['score'], tier=resultado['tier'],
                    razoes=resultado['razoes'], sinais=resultado['sinais'],
                    presenca_digital=resultado['presenca_digital'], dados_suficientes=dados_suficientes
                ))
                print(f"[Hunter V2] SKIP sem reviews: {lead.nome} ({len(lead.reviews or [])} reviews) — guardado como fallback")
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

            leads_encontrados.append(lead_qualificado)
            print(f"[Hunter V2] APROVADO {lead.nome} | Score: {resultado['score']} | Tier: {resultado['tier']}")

        except Exception as e:
            print(f"[Hunter V2] ERRO ao processar {dados.get('nome', '?')}: {e}")
            continue

    print(f"[Hunter V2] Total: {len(leads_encontrados)} leads coletados (lazy, {len(cards_raw)} cards avaliados)")

    # Se nenhum lead com reviews foi encontrado, usar fallback
    if not leads_encontrados and hasattr(buscar_leads_google_maps, '_fallback') and buscar_leads_google_maps._fallback:
        leads_encontrados = buscar_leads_google_maps._fallback
        print(f"[Hunter V2] Usando {len(leads_encontrados)} leads fallback (sem reviews)")
    # Limpar fallback
    buscar_leads_google_maps._fallback = []

    # Ordenar por score (maior primeiro) — prioriza leads com reviews e dados completos
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
