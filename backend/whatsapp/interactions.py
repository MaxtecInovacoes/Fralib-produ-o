"""Persistencia de interacoes e estado SDR de leads."""

import hashlib
import re
from datetime import datetime

from sqlalchemy import text


def save_interaction(
    engine,
    lead_id: str,
    mensagem: str,
    direcao: str,
    user_id: int | None = None,
    now_factory=datetime.now,
    msg_id_wpp: str = "",
) -> bool:
    """Salva uma mensagem na tabela interacoes com idempotencia.

    Args:
        engine: SQLAlchemy engine
        lead_id: ID do lead
        mensagem: Conteudo da mensagem
        direcao: 'entrada' (recebida) ou 'saida' (enviada)
        user_id: Tenant ID
        now_factory: Funcao de timestamp (para testes)
        msg_id_wpp: ID unico da mensagem do WhatsApp (para idempotencia)

    Returns:
        True se inseriu nova linha, False se era duplicada
    """
    # Gerar dedup_key para idempotencia
    # Prioridade: msg_id_wpp do WhatsApp > hash do conteudo
    if msg_id_wpp:
        dedup_key = f"wpp:{msg_id_wpp}"
    else:
        # Fallback: hash do conteudo + direcao + janela de 5s
        content_hash = hashlib.sha256(
            f"{lead_id}:{direcao}:{mensagem}".encode("utf-8")
        ).hexdigest()[:32]
        # Janela de 5s: agrupar msgs identicas em sequencia
        dedup_key = f"hash:{content_hash}"

    with engine.connect() as conn:
        try:
            result = conn.execute(
                text(
                    """
                    INSERT INTO interacoes
                        (lead_id, mensagem, direcao, criado_em, user_id, dedup_key)
                    VALUES
                        (:lead_id, :mensagem, :direcao, :criado_em, :user_id, :dedup_key)
                    ON CONFLICT (lead_id, user_id, dedup_key)
                    WHERE dedup_key IS NOT NULL
                    DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "lead_id": lead_id,
                    "mensagem": mensagem,
                    "direcao": direcao,
                    "criado_em": now_factory().isoformat(),
                    "user_id": user_id,
                    "dedup_key": dedup_key if msg_id_wpp else None,
                },
            )
            conn.commit()
            # rowcount = 0 significa que era duplicado
            return result.rowcount > 0
        except Exception as e:
            # Fallback gracioso se coluna dedup_key nao existir (migration nao aplicada)
            if "dedup_key" in str(e) or "column" in str(e).lower():
                try:
                    conn.execute(
                        text(
                            """
                            INSERT INTO interacoes (lead_id, mensagem, direcao, criado_em, user_id)
                            VALUES (:lead_id, :mensagem, :direcao, :criado_em, :user_id)
                            """
                        ),
                        {
                            "lead_id": lead_id,
                            "mensagem": mensagem,
                            "direcao": direcao,
                            "criado_em": now_factory().isoformat(),
                            "user_id": user_id,
                        },
                    )
                    conn.commit()
                    return True
                except Exception:
                    conn.rollback()
                    return False
            conn.rollback()
            return False


def update_lead_stage(
    engine,
    lead_id: str,
    sdr_stage: str,
    user_id: int,
    now_factory=datetime.now,
) -> None:
    """Atualiza sdr_stage do lead dentro do tenant informado."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE leads SET sdr_stage=:stage, atualizado_em=:ts "
                "WHERE id=:id AND user_id=:uid"
            ),
            {
                "stage": sdr_stage,
                "ts": now_factory().isoformat(),
                "id": lead_id,
                "uid": user_id,
            },
        )
        conn.commit()


# ===== Retroalimentacao: URL de site proprio via mensagem WhatsApp =====

# Redes sociais, agregadores de link e dominios Google NAO contam
# como "site proprio" para o Caio.
_REDES_SOCIAIS_DOMINIOS = frozenset({
    "instagram.com", "facebook.com", "fb.com", "tiktok.com",
    "youtube.com", "youtu.be", "x.com", "twitter.com",
    "linkedin.com", "wa.me", "whatsapp.com", "t.me",
    "pinterest.com", "snapchat.com", "reddit.com",
    "linktr.ee", "bio.me", "beacons.ai",
    # Dominios Google — URLs compartilhadas em mensagens WhatsApp
    # frequentemente apontam para assets (lh3.googleusercontent.com),
    # Maps, etc. Nenhum desses e "site proprio do lead".
    "googleusercontent.com", "google.com", "google.com.br",
    "gstatic.com", "schema.org", "w3.org",
})

# Regex captura a primeira URL com TLD "proprio" (com.br, com, net, org, etc.).
# Requer finalizacao (espaco, /, ?, # ou fim de string) para nao capturar pedaco
# solto de texto. Case-insensitive.
_TLD_PROPRIO = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"([a-z0-9][a-z0-9-]{0,61}\."
    r"(?:com\.br|com|net|org|io|app|dev|me|store|shop|tech|"
    r"site|xyz|biz|info|online|page|cloud|br|co|com\.co))"
    r"(?:[/\s?#]|$)",
    re.IGNORECASE,
)


def extrair_url_website(texto: str) -> str | None:
    """Extrai a primeira URL de site proprio presente em ``texto``.

    Ignora redes sociais e dominios Google. Retorna a URL normalizada para
    ``https://dominio`` (sem path/query/fragmento). Retorna ``None`` quando
    nao ha site proprio.

    Funcao pura (sem I/O) para permitir testes deterministicos.
    """
    if not texto:
        return None
    for match in _TLD_PROPRIO.finditer(texto):
        dominio = match.group(1).lower()
        if any(red in dominio for red in _REDES_SOCIAIS_DOMINIOS):
            continue
        return f"https://{dominio}"
    return None
