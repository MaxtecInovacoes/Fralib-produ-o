"""
Agente 1 - Lead Hunter V2 (COM SCRAPING REAL)
Captura leads REAIS do Google Maps.
Ordem: leads prontos/cache -> GoSom best-effort -> Playwright.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from backend.utils.google_local_scraper import GoogleLocalScraper as GoogleMapsScraper
from backend.utils.google_maps_gosom import buscar_gosom, buscar_negocio_gosom
import asyncio
import os
import re
import time

# salvar_memoria: stub local (na VPS usa o módulo real)
try:
    from memory import salvar_memoria
except ImportError:
    def salvar_memoria(key, data): pass


def _env_int(name: str, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(value, max_value))

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
    """Envelope legado de candidato. Somente Caio decide score e tier comercial."""
    lead: LeadRaw
    score: int = Field(..., ge=0, le=100)
    tier: str  # CAPTURADO ou DADOS_INSUFICIENTES; Caio define o tier comercial
    razoes: List[str] = []
    sinais: List[str] = []
    presenca_digital: str  # SITE, SOCIAL_ONLY, ZERO_PRESENCA
    dados_suficientes: bool = True  # ✅ NOVO: flag de validação
    caio_resultado: Optional[Dict[str, Any]] = None

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

    # Fotos do Google Maps sao enriquecimento, nao criterio de validade.
    # O scraper de Maps nao coleta fotos por padrao; a etapa multimidia usa
    # midia editorial externa quando necessario.
    if lead.fotos and 'placeholder.com' in lead.fotos[0]:
        erros.append("Fotos são PLACEHOLDER (MOCK)")

    # Endereço
    if not lead.endereco or len(lead.endereco) < 20:
        erros.append("Endereço incompleto")

    # Se 2 ou mais problemas críticos, dados insuficientes
    dados_suficientes = len(erros) < 2

    return dados_suficientes, erros

def calcular_score(lead: LeadRaw, cidade: str) -> Dict[str, Any]:
    """Compatibilidade: Hunter captura; Caio e a unica autoridade comercial."""
    return {
        'score': 0,
        'tier': "CAPTURADO",
        'razoes': ["Candidato capturado; qualificacao comercial pendente no Caio"],
        'sinais': [],
        'presenca_digital': "SITE" if lead.website else "ZERO_PRESENCA",
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
    _segmento_raw = dados.get('categoria') or 'Negócio Local'
    lead = LeadRaw(
        nome=dados['nome'],
        cidade=cidade,
        segmento=_segmento_raw,
        categoria=dados.get('categoria') or _segmento_raw,
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
            if not _cache_lead_matches_segment(nome, segmento):
                print(f"[Hunter Cache] SKIP nicho errado: {nome} (buscado={segmento})")
                continue
            if len(leads) >= limite:
                break
            _cached_reviews = []
            if r[15]:
                try:
                    _cached_reviews = _json_cache.loads(r[15])
                except _json_cache.JSONDecodeError:
                    _cached_reviews = []
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
                if not dados_suficientes:
                    continue
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


def _cache_lead_matches_segment(nome: str, segmento: str) -> bool:
    """Avoid reusing stale cache entries that were saved under the wrong query."""
    try:
        from agents.caio import _verificar_relevancia_segmento
    except Exception:
        try:
            from caio import _verificar_relevancia_segmento
        except Exception:
            return True
    return bool(_verificar_relevancia_segmento(nome or "", segmento or ""))


def _lead_from_db_row(row, segmento_default: str, cidade_default: str) -> Optional['LeadQualificado']:
    """Normaliza linha de leads/leads_cache para LeadQualificado."""
    import json as _json_cache

    try:
        dados = {}
        if row.get("dados_completos"):
            raw = row.get("dados_completos")
            dados = raw if isinstance(raw, dict) else _json_cache.loads(raw)
        reviews = dados.get("reviews") or dados.get("depoimentos") or []
        lead = LeadRaw(
            nome=row.get("nome") or "",
            cidade=row.get("cidade") or cidade_default,
            segmento=row.get("segmento") or segmento_default,
            telefone=row.get("telefone") or "",
            whatsapp=row.get("whatsapp") or row.get("telefone") or "",
            rating=row.get("rating") or 0,
            total_avaliacoes=dados.get("total_avaliacoes") or row.get("total_avaliacoes") or len(reviews),
            website=dados.get("website") or row.get("website") or "",
            endereco=dados.get("endereco") or row.get("endereco") or "",
            maps_url=dados.get("maps_url") or row.get("maps_url") or "",
            fotos=dados.get("fotos") or [],
            servicos=dados.get("servicos") or [],
            horarios=dados.get("horarios") or [],
            atributos=dados.get("atributos") or [],
            reviews=reviews,
            google_maps_embed=dados.get("google_maps_embed") or "",
            place_id=dados.get("place_id") or "",
        )
        resultado = calcular_score(lead, cidade_default)
        dados_suficientes, _ = validar_dados_minimos(lead)
        return LeadQualificado(
            lead=lead,
            score=resultado["score"],
            tier=resultado["tier"],
            razoes=resultado["razoes"],
            sinais=resultado["sinais"],
            presenca_digital=resultado["presenca_digital"],
            dados_suficientes=dados_suficientes,
        )
    except Exception:
        return None


def _buscar_leads_prontos_usuario(user_id: Optional[int], segmento: str, cidade: str, limite: int) -> List['LeadQualificado']:
    """Reaproveita leads capturados/pendentes antes de abrir scraping novo."""
    if not user_id:
        return []
    try:
        from database import engine
        from sqlalchemy import text as _text

        with engine.connect() as conn:
            rows = conn.execute(_text("""
                SELECT id, nome, cidade, segmento, telefone, whatsapp, rating, score,
                       tier, status, dados_completos
                FROM leads
                WHERE user_id = :uid
                  AND lower(cidade) = lower(:cid)
                  AND COALESCE(processado, false) = false
                  AND lower(COALESCE(status, '')) IN ('capturado', 'pendente', 'erro')
                ORDER BY COALESCE(score, 0) DESC, criado_em ASC
                LIMIT :lim
            """), {"uid": user_id, "cid": cidade, "seg": segmento, "lim": limite + 5}).mappings().fetchall()
        leads = []
        for row in rows:
            row_data = dict(row)
            nome = row_data.get("nome") or ""
            row_segmento = row_data.get("segmento") or ""
            if row_segmento and segmento.lower().strip() not in row_segmento.lower().strip():
                if not _cache_lead_matches_segment(nome, segmento):
                    continue
            lq = _lead_from_db_row(dict(row), segmento, cidade)
            if lq:
                leads.append(lq)
            if len(leads) >= limite:
                break
        return leads
    except Exception as e:
        print(f"[Hunter Pool] Erro ao buscar leads prontos: {e}")
        return []


def _merge_leads(*listas: List['LeadQualificado'], limite: int) -> List['LeadQualificado']:
    """Une candidatos por nome+cidade sem antecipar a decisao comercial do Caio."""
    por_chave = {}
    for lista in listas:
        for item in lista or []:
            nome = (item.lead.nome or "").lower().strip()
            cidade = (item.lead.cidade or "").lower().strip()
            if not nome:
                continue
            chave = (nome, cidade)
            atual = por_chave.get(chave)
            if not atual or _prioridade_captura(item) > _prioridade_captura(atual):
                por_chave[chave] = item
    merged = list(por_chave.values())
    merged.sort(key=_prioridade_captura, reverse=True)
    return merged[:limite]


def _prioridade_captura(item: 'LeadQualificado') -> tuple:
    """Ordena dados mais completos primeiro; nao aprova nem rejeita oportunidades."""
    lead = item.lead
    return (
        bool(item.dados_suficientes),
        bool(lead.telefone or lead.whatsapp),
        bool(lead.endereco),
        int(lead.total_avaliacoes or 0),
        float(lead.rating or 0),
    )


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


def _filtrar_aprovados_caio(
    candidatos: List['LeadQualificado'],
    segmento: str,
    score_minimo: int,
    aprovados_necessarios: int,
) -> List['LeadQualificado']:
    """Executa a unica qualificacao comercial, candidato a candidato."""
    from agents.caio import CaioOutput, LeadInput as CaioInput, qualificar_lead

    aprovados = []
    for candidato in candidatos:
        lead = candidato.lead
        resultado = (
            CaioOutput(**candidato.caio_resultado)
            if candidato.caio_resultado
            else qualificar_lead(
                CaioInput(
                    nome=lead.nome,
                    cidade=lead.cidade,
                    segmento=segmento,
                    telefone=lead.telefone or "",
                    whatsapp=lead.whatsapp or "",
                    rating=lead.rating or 0.0,
                    reviews_count=lead.total_avaliacoes or len(lead.reviews or []),
                    fotos=lead.fotos or [],
                    website=lead.website or "",
                    logo_url=lead.logo_url or "",
                )
            )
        )
        if not resultado.qualificado or resultado.tier == "REJEITADO":
            print(f"[Hunter V2] DESCARTADO {lead.nome} | Caio: {resultado.motivo}")
            continue
        if int(resultado.score or 0) < int(score_minimo or 45):
            print(
                f"[Hunter V2] DESCARTADO {lead.nome} | "
                f"Caio score {resultado.score} abaixo do minimo {score_minimo}"
            )
            continue
        candidato.score = resultado.score
        candidato.tier = resultado.tier or "STANDARD"
        candidato.razoes = [resultado.motivo]
        candidato.caio_resultado = resultado.model_dump()
        aprovados.append(candidato)
        print(
            f"[Hunter V2] ENCAMINHADO {lead.nome} | "
            f"Caio: {resultado.qualificacao} score={resultado.score}"
        )
        if len(aprovados) >= max(1, int(aprovados_necessarios or 1)):
            break
    return aprovados


def _aceitar_lote_caio(
    cards: List[Dict[str, Any]],
    segmento: str,
    cidade: str,
    score_minimo: int,
) -> bool:
    """Marca o primeiro card aprovado para o scraper encerrar detalhes cedo."""
    from agents.caio import LeadInput as CaioInput, qualificar_lead

    for card in cards:
        resultado = qualificar_lead(
            CaioInput(
                nome=(card.get("nome") or "").strip(),
                cidade=(card.get("cidade") or cidade).strip(),
                segmento=segmento,
                telefone=card.get("telefone") or "",
                whatsapp=card.get("telefone") or "",
                rating=card.get("rating") or 0.0,
                reviews_count=card.get("reviews") or len(card.get("depoimentos") or []),
                fotos=card.get("fotos") or [],
                website=card.get("website") or "",
                logo_url=card.get("logo") or "",
            )
        )
        if (
            resultado.qualificado
            and resultado.tier != "REJEITADO"
            and int(resultado.score or 0) >= int(score_minimo or 45)
        ):
            card["_caio_resultado"] = resultado.model_dump()
            return True
    return False


async def buscar_leads_google_maps(
    cidade: str,
    segmento: str,
    limite: int = 5,
    score_type: str = 'STANDARD',
    leads_existentes: set = None,
    force_fresh: bool = False,
    user_id: Optional[int] = None,
    score_minimo: int = 45,
    aprovados_necessarios: int = 1,
) -> List[LeadQualificado]:
    """
    Busca leads no Google Maps com estrategia LAZY:
    1. Captura cards basicos (leve)
    2. Para cada card: busca detalhes -> qualifica -> aceita/rejeita
    3. Para quando atingir limite de aprovados
    """
    _existentes = leads_existentes or set()
    _target = max(1, int(aprovados_necessarios or 1))
    _single_lead_limit = _env_int("FRALIB_HUNTER_SINGLE_LEAD_CANDIDATES", 8, 3, 15)
    _candidate_limit_base = max(limite, 10 if limite <= 3 else limite + 5)
    if _target == 1:
        _candidate_limit_base = min(_candidate_limit_base, _single_lead_limit)
    _candidate_limit = min(30, _candidate_limit_base)
    _capture_timeout = _env_int("FRALIB_HUNTER_CAPTURE_TIMEOUT_SECS", 150, 30, 180)
    _deadline = time.monotonic() + _capture_timeout

    def _remaining_secs() -> float:
        return max(0.0, _deadline - time.monotonic())

    print(
        f"[Hunter V2] Buscando {limite} lead(s) LAZY + buffer {_candidate_limit}: "
        f"{segmento} em {cidade} ({len(_existentes)} ja existentes)..."
    )

    _min_buffer = min(_candidate_limit, max(limite + 3, 5))
    leads_prontos = [] if force_fresh else _buscar_leads_prontos_usuario(user_id, segmento, cidade, _candidate_limit)
    if leads_prontos:
        print(f"[Hunter V2] Pool pronto: {len(leads_prontos)} lead(s) capturados/pendentes")

    # ── CACHE GLOBAL: verificar se já temos leads cacheados pra este segmento+cidade ──
    if force_fresh:
        print(f"[Hunter V2] FORCE FRESH: ignorando cache, buscando direto no Maps")
        cached_leads = []
    else:
        cached_leads = _buscar_cache_leads(segmento, cidade, _existentes, _candidate_limit)
    pool_inicial = _merge_leads(leads_prontos, cached_leads, limite=_candidate_limit)
    if pool_inicial and len(pool_inicial) >= _min_buffer:
        print(
            f"[Hunter V2] ✅ POOL HIT: {len(pool_inicial)} candidatos prontos/cache "
            f"(sem scraping)"
        )
        _aprovados_pool = _filtrar_aprovados_caio(
            pool_inicial, segmento, score_minimo, aprovados_necessarios
        )
        if _aprovados_pool:
            return _aprovados_pool
        print("[Hunter V2] Pool/cache sem aprovado Caio; buscando complemento")
    if pool_inicial:
        print(f"[Hunter V2] Pool parcial: {len(pool_inicial)}/{_min_buffer}; buscando complemento")

    # ── PRIMARY: gosom/google-maps-scraper (REST API, open-source) ──
    cards_raw = None
    _maps_search_limit = _env_int("FRALIB_HUNTER_MAPS_SEARCH_LIMIT", 24, 10, 60)
    _busca_limite = max(10, min(_maps_search_limit, _candidate_limit * 3))

    try:
        _gosom_timeout = max(3.0, min(30.0, _remaining_secs() - 5))
        gosom_results = await asyncio.wait_for(
            buscar_gosom(segmento, cidade, limite=_busca_limite),
            timeout=_gosom_timeout,
        )
    except asyncio.TimeoutError:
        gosom_results = []
        print("[Hunter V2] Gosom excedeu budget; usando Playwright")
    if gosom_results and len(gosom_results) > 0:
        cards_raw = gosom_results
        print(f"[Hunter V2] ✅ GOSOM: {len(cards_raw)} leads capturados")
    else:
        # ── FALLBACK: Playwright (google_local_scraper.py) ──
        _remaining = _remaining_secs()
        if _remaining <= 15:
            print("[Hunter V2] Budget de captura esgotado antes do Playwright")
            return _filtrar_aprovados_caio(
                pool_inicial, segmento, score_minimo, aprovados_necessarios
            )
        print(f"[Hunter V2] Gosom indisponível — usando Playwright...")
        scraper = GoogleMapsScraper(headless=True)
        cards_raw = await scraper.buscar(
            segmento,
            cidade,
            limite=_busca_limite,
            leads_existentes=_existentes,
            candidate_acceptor=lambda cards: _aceitar_lote_caio(
                cards, segmento, cidade, score_minimo
            ),
            max_duration_secs=max(10.0, _remaining - 5.0),
        )

    cards_raw = cards_raw or []

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
                dados_suficientes=dados_suficientes,
                caio_resultado=dados.get("_caio_resultado"),
            )

            leads_encontrados.append(lead_qualificado)
            _obs = f" | observacoes: {', '.join(erros)}" if erros else ""
            print(f"[Hunter V2] CAPTURADO {lead.nome}{_obs}")

        except Exception as e:
            print(f"[Hunter V2] ERRO ao processar {dados.get('nome', '?')}: {e}")
            continue

    print(f"[Hunter V2] Total: {len(leads_encontrados)} leads coletados")

    # Deduplicar e ordenar por completude observavel. Caio decide score e tier.
    leads_encontrados = _merge_leads(pool_inicial, leads_encontrados, limite=_candidate_limit)

    aprovados = _filtrar_aprovados_caio(
        leads_encontrados[:_candidate_limit],
        segmento,
        score_minimo,
        aprovados_necessarios,
    )
    if aprovados:
        _salvar_cache_leads(aprovados, segmento, cidade)
    return aprovados

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
