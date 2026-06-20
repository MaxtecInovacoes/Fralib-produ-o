"""
Funções de persistência de leads no banco de dados.

Fornece funções para salvar, atualizar e gerenciar leads no banco de dados,
incluindo lógica de duplicatas, status e dados complementares.
"""
import json
import re
import uuid
import unicodedata
from datetime import datetime
from typing import Any, List, Optional, Tuple


def check_duplicate_lead(conn, nome: str, cidade: str, user_id: int) -> Optional[str]:
    """
    Verifica se um lead já existe no banco.

    Args:
        conn: Conexão SQLAlchemy
        nome: Nome do lead
        cidade: Cidade do lead
        user_id: ID do tenant

    Returns:
        Tupla (id, status) se existir, None caso contrário
    """
    from sqlalchemy import text

    result = conn.execute(
        text("""
            SELECT id, status FROM leads
            WHERE lower(trim(nome)) = lower(trim(:nome))
              AND lower(cidade) = lower(:cidade)
              AND user_id = :user_id
            LIMIT 1
        """),
        {"nome": nome, "cidade": cidade, "user_id": user_id},
    ).fetchone()
    if result:
        return (str(result[0]), result[1])
    return None


def build_lead_dados_completos(
    lead,
    website: str = "",
    total_avaliacoes: int = 0,
) -> dict:
    """
    Constrói o dict de dados_completos para um lead.

    Args:
        lead: Objeto lead com atributos
        website: URL do website
        total_avaliacoes: Total de avaliações

    Returns:
        Dict com dados completos do lead
    """
    return {
        "endereco": getattr(lead, "endereco", "")
        or getattr(lead, "address", "")
        or "",
        "horarios": getattr(lead, "horarios", []) or [],
        "maps_url": getattr(lead, "maps_url", None) or "",
        "atributos": getattr(lead, "atributos", []) or [],
        "servicos": getattr(lead, "servicos", []) or [],
        "faixa_preco": getattr(lead, "faixa_preco", None) or "",
        "website": website,
        "total_avaliacoes": total_avaliacoes,
        "google_maps_embed": getattr(lead, "google_maps_embed", "") or "",
        "fotos": getattr(lead, "fotos", []) or [],
        "reviews": [
            {"autor": r.get("autor", ""), "rating": r.get("rating", 5), "texto": r.get("texto", "")}
            for r in (getattr(lead, "reviews", []) or [])
        ],
    }


def save_lead_to_db(
    conn,
    lead_obj,
    lead_id: str,
    lead_nome: str,
    segmento: str,
    tenant_id: int,
    status: str = "capturado",
    score: float = 0.0,
    tier: str = "",
    dados_extras: dict = None,
    agora: str = None,
) -> None:
    """
    Salva ou atualiza um lead no banco de dados.

    Args:
        conn: Conexão SQLAlchemy
        lead_obj: Objeto lead
        lead_id: ID do lead (UUID)
        lead_nome: Nome do lead
        segmento: Segmento/nicho
        tenant_id: ID do tenant
        status: Status do lead (default: 'capturado')
        score: Score do lead
        tier: Tier do lead
        dados_extras: Dict com dados complementares
        agora: Timestamp ISO (default: agora)
    """
    from sqlalchemy import text

    if agora is None:
        agora = datetime.now().isoformat()

    if dados_extras is None:
        dados_extras = {}

    conn.execute(
        text("""
            INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
            VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
            ON CONFLICT DO NOTHING
        """),
        {
            "id": lead_id,
            "nome": lead_nome,
            "cidade": getattr(lead_obj, "cidade", ""),
            "segmento": getattr(lead_obj, "segmento", "") or segmento,
            "telefone": getattr(lead_obj, "telefone", "") or "",
            "whatsapp": getattr(lead_obj, "whatsapp", "") or "",
            "rating": getattr(lead_obj, "rating", 0.0) or 0.0,
            "score": score,
            "tier": tier,
            "status": status,
            "user_id": tenant_id,
            "dados_completos": json.dumps(dados_extras),
            "criado_em": agora,
            "atualizado_em": agora,
            "processado": False,
            "tentativas": 0,
        },
    )


def update_lead_reviews(
    conn,
    lead_id: str,
    tenant_id: int,
    reviews: List[dict],
) -> None:
    """
    Atualiza reviews de um lead existente.

    Args:
        conn: Conexão SQLAlchemy
        lead_id: ID do lead
        tenant_id: ID do tenant
        reviews: Lista de reviews para atualizar
    """
    from sqlalchemy import text

    if not reviews:
        return

    conn.execute(
        text("""
            UPDATE leads SET dados_completos = jsonb_set(
                COALESCE(CAST(dados_completos AS jsonb), CAST('{}' AS jsonb)),
                '{reviews}', CAST(:reviews AS jsonb)
            ) WHERE id = :id AND user_id = :uid AND (CAST(dados_completos AS jsonb)->'reviews' = CAST('[]' AS jsonb) OR CAST(dados_completos AS jsonb)->'reviews' IS NULL)
        """),
        {
            "id": lead_id,
            "uid": tenant_id,
            "reviews": json.dumps(reviews),
        },
    )
    conn.commit()


def update_lead_address(
    conn,
    lead_id: str,
    tenant_id: int,
    endereco: str,
) -> None:
    """
    Atualiza endereço de um lead existente.

    Args:
        conn: Conexão SQLAlchemy
        lead_id: ID do lead
        tenant_id: ID do tenant
        endereco: Endereço para atualizar
    """
    from sqlalchemy import text

    if not endereco:
        return

    conn.execute(
        text("""
            UPDATE leads SET dados_completos = jsonb_set(
                COALESCE(CAST(dados_completos AS jsonb), CAST('{}' AS jsonb)),
                '{endereco}', to_jsonb(CAST(:endereco AS text))
            ) WHERE id = :id AND user_id = :uid
              AND COALESCE(CAST(dados_completos AS jsonb)->>'endereco', '') = ''
        """),
        {
            "id": lead_id,
            "uid": tenant_id,
            "endereco": endereco,
        },
    )
    conn.commit()


def update_lead_status(
    conn,
    lead_id: str,
    tenant_id: int,
    status: str,
    agora: str = None,
) -> None:
    """
    Atualiza o status de um lead.

    Args:
        conn: Conexão SQLAlchemy
        lead_id: ID do lead
        tenant_id: ID do tenant
        status: Novo status
        agora: Timestamp ISO (default: agora)
    """
    from sqlalchemy import text

    if agora is None:
        agora = datetime.now().isoformat()

    conn.execute(
        text("UPDATE leads SET status=:status, atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
        {"status": status, "ts": agora, "id": lead_id, "uid": tenant_id},
    )
    conn.commit()


def save_rejected_lead(
    conn,
    lead_id: str,
    tenant_id: int,
    agora: str = None,
) -> None:
    """
    Salva um lead rejeitado como 'descartado'.

    Args:
        conn: Conexão SQLAlchemy
        lead_id: ID do lead
        tenant_id: ID do tenant
        agora: Timestamp ISO (default: agora)
    """
    update_lead_status(conn, lead_id, tenant_id, "descartado", agora)


def find_next_valid_lead(
    conn,
    leads: List,
    start_idx: int,
    tenant_id: int,
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Encontra o próximo lead válido da lista que não está duplicado.

    Args:
        conn: Conexão SQLAlchemy
        leads: Lista de leads
        start_idx: Índice para iniciar busca
        tenant_id: ID do tenant

    Returns:
        Tupla (lead_obj, lead_id) ou (None, None) se não encontrar
    """
    from sqlalchemy import text

    for lq in leads[start_idx:]:
        dup = conn.execute(
            text("""
                SELECT id FROM leads
                WHERE lower(trim(nome)) = lower(trim(:nome))
                  AND lower(cidade) = lower(:cidade)
                  AND user_id = :user_id
                  AND status IN ('concluido', 'processando')
                LIMIT 1
            """),
            {
                "nome": lq.lead.nome,
                "cidade": lq.lead.cidade,
                "user_id": tenant_id,
            },
        ).fetchone()
        if not dup:
            # Encontrou lead válido, buscar ID no banco
            existing = conn.execute(
                text("""
                    SELECT id FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                    LIMIT 1
                """),
                {
                    "nome": lq.lead.nome,
                    "cidade": lq.lead.cidade,
                    "user_id": tenant_id,
                },
            ).fetchone()
            return (lq, str(existing[0]) if existing else None)
    return (None, None)


def save_hunter_leads(
    engine,
    leads: List,
    tenant_id: int,
    segmento: str,
    cidade: str,
    max_salvar: int = 10,
) -> int:
    """
    Salva leads capturados pelo Hunter no banco.

    Args:
        engine: Engine SQLAlchemy
        leads: Lista de leads do Hunter
        tenant_id: ID do tenant
        segmento: Segmento/nicho
        cidade: Cidade
        max_salvar: Máximo de leads a salvar

    Returns:
        Número de leads salvos
    """
    from sqlalchemy import text

    agora = datetime.now().isoformat()
    salvos = 0

    with engine.connect() as conn:
        for lq in leads:
            if salvos >= max_salvar:
                break

            lead = lq.lead
            nome_norm = lead.nome.lower().strip() if lead.nome else ""
            if not nome_norm:
                continue

            # Checar duplicata
            dup = conn.execute(
                text("""
                    SELECT id FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                    LIMIT 1
                """),
                {
                    "nome": lead.nome,
                    "cidade": lead.cidade or cidade,
                    "user_id": tenant_id,
                },
            ).fetchone()
            if dup:
                continue

            lead_uuid = str(uuid.uuid4())
            dados = build_lead_dados_completos(
                lead,
                website=getattr(lead, "website", "") or "",
                total_avaliacoes=getattr(lead, "total_avaliacoes", 0) or 0,
            )

            try:
                conn.execute(
                    text("""
                        INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                        VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": lead_uuid,
                        "nome": lead.nome,
                        "cidade": lead.cidade or cidade,
                        "segmento": lead.segmento or segmento,
                        "telefone": getattr(lead, "telefone", "") or "",
                        "whatsapp": getattr(lead, "whatsapp", "") or "",
                        "rating": getattr(lead, "rating", 0.0) or 0.0,
                        "score": lq.score,
                        "tier": lq.tier,
                        "status": "capturado",
                        "user_id": tenant_id,
                        "criado_em": agora,
                        "atualizado_em": agora,
                        "processado": False,
                        "tentativas": 0,
                        "dados_completos": json.dumps(dados),
                    },
                )
                salvos += 1
            except Exception as e:
                print(f"[Hunter] Erro ao salvar lead pendente {lead.nome}: {e}")

        conn.commit()

    if salvos:
        print(f"[Hunter] {salvos} leads salvos como pendente no banco")

    return salvos


def reuse_hunter_lead(
    conn,
    lead_nome: str,
    lead_id: str,
    tenant_id: int,
    lead_obj,
) -> bool:
    """
    Reutiliza um lead pendente/capturado pelo Hunter.

    Atualiza reviews e endereço do lead existente se necessário.

    Args:
        conn: Conexão SQLAlchemy
        lead_nome: Nome do lead
        lead_id: ID do lead existente
        tenant_id: ID do tenant
        lead_obj: Objeto lead com dados novos

    Returns:
        True se reutilizado com sucesso
    """
    print(f"[Pipeline] Lead pendente reutilizado: {lead_nome} (id: {lead_id})")

    # Atualizar reviews se o lead antigo não tinha
    reviews = [
        {"autor": r.get("autor", ""), "rating": r.get("rating", 5), "texto": r.get("texto", "")}
        for r in (getattr(lead_obj, "reviews", []) or [])
    ]
    if reviews:
        update_lead_reviews(conn, lead_id, tenant_id, reviews)

    # Atualizar endereço se o lead antigo não tinha
    endereco = getattr(lead_obj, "endereco", "") or ""
    if endereco:
        update_lead_address(conn, lead_id, tenant_id, endereco)

    return True


def slugify(text: str, max_len: int = 50) -> str:
    """
    Converte texto para slug URL-friendly.

    Args:
        text: Texto a converter
        max_len: Comprimento máximo do slug

    Returns:
        Slug gerado
    """
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:max_len]


def save_fallback_lead(
    conn,
    lead_obj,
    lead_nome: str,
    segmento: str,
    tenant_id: int,
    score: float,
    tier: str,
    cidade: str = "",
    website: str = "",
    total_avaliacoes: int = 0,
) -> str:
    """
    Salva um lead após fallback do Caio.

    Args:
        conn: Conexão SQLAlchemy
        lead_obj: Objeto lead
        lead_nome: Nome do lead
        segmento: Segmento/nicho
        tenant_id: ID do tenant
        score: Score do lead
        tier: Tier do lead
        cidade: Cidade (opcional)
        website: Website (opcional)
        total_avaliacoes: Total de avaliações (opcional)

    Returns:
        ID do lead salvo
    """
    from sqlalchemy import text

    lead_id = str(uuid.uuid4())
    agora = datetime.now().isoformat()

    # Verificar se já existe
    existing = conn.execute(
        text("""
            SELECT id FROM leads
            WHERE lower(trim(nome)) = lower(trim(:nome))
              AND lower(cidade) = lower(:cidade)
              AND user_id = :user_id
            LIMIT 1
        """),
        {
            "nome": lead_nome,
            "cidade": getattr(lead_obj, "cidade", "") or cidade,
            "user_id": tenant_id,
        },
    ).fetchone()

    if existing:
        lead_id = str(existing[0])
    else:
        dados = build_lead_dados_completos(
            lead_obj,
            website=website,
            total_avaliacoes=total_avaliacoes,
        )
        conn.execute(
            text("""
                INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                ON CONFLICT DO NOTHING
            """),
            {
                "id": lead_id,
                "nome": lead_nome,
                "cidade": getattr(lead_obj, "cidade", "") or cidade,
                "segmento": segmento,
                "telefone": getattr(lead_obj, "telefone", "") or "",
                "whatsapp": getattr(lead_obj, "whatsapp", "") or "",
                "rating": getattr(lead_obj, "rating", 0.0) or 0.0,
                "score": score,
                "tier": tier,
                "status": "capturado",
                "user_id": tenant_id,
                "dados_completos": json.dumps(dados),
                "criado_em": agora,
                "atualizado_em": agora,
                "processado": False,
                "tentativas": 0,
            },
        )

    return lead_id
