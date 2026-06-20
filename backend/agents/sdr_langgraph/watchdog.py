"""
Watchdog do SDR LangGraph - Previne vícios do bryan antigo.

PROBLEMAS DO BRYAN ANTIGO QUE ESTE WATCHDOG EVITA:
1. Mandava follow-up de 1 em 1h (spam)
2. Não considerava reactions do WhatsApp (👀, etc) como "lead só visualizou"
3. Mandava 2-3 mensagens sem resposta sem controle
4. Não respeitava cooldown entre mensagens

O NOVO FRANZ:
1. Mínimo 24h entre mensagens sem resposta
2. Reactions do WhatsApp não contam como resposta
3. Máximo 2 mensagens sem resposta → marca lost
4. Cooldown sempre respeitado
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import text


def _get_engine():
    """Lazy load engine"""
    try:
        from core.database import engine
        return engine
    except ImportError:
        from database import engine
        return engine


def is_emoji_reaction_only(message: str) -> bool:
    """
    Detecta se a mensagem é APENAS emoji(s)/reaction sem texto real.

    O WhatsApp manda reactions (👀, ❤️, etc) separadamente, mas se vierem
    no campo de texto normal, devemos ignorar como resposta real.
    """
    if not message:
        return True

    # Remove espaços
    cleaned = message.strip()
    if not cleaned:
        return True

    # Caracteres não-textuais comuns
    emoji_pattern = (
        "[\U0001F300-\U0001F9FF"  # Misc symbols & pictographs
        "\U0001FA00-\U0001FA6F"  # Chess symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and pictographs extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U0000FE0F"              # Variation Selector
        "\U00002600-\U000027BF"  # Misc symbols
        "❤️"
        "]"
    )

    import re
    # Se só tem emoji(s), é uma reaction
    if re.fullmatch(f"{emoji_pattern}+", cleaned):
        return True

    return False


def can_send_next_outbound(
    telefone: str,
    user_id: int,
    sdr_stage: str,
    lead_responded: bool = False,
) -> tuple[bool, str]:
    """
    Watchdog principal: decide se pode enviar próxima mensagem outbound.

    Args:
        telefone: Número do lead
        user_id: ID do usuário (tenant)
        sdr_stage: Stage atual do SDR
        lead_responded: Se True, o lead respondeu recentemente → libera para responder

    Returns:
        (pode_enviar: bool, motivo_bloqueio: str)
    """
    # BUGFIX: Se o LEAD respondeu, libera para enviar (reseta watchdog)
    if lead_responded:
        return True, "lead_responded_can_reply"
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            # Buscar últimas 5 mensagens deste lead
            rows = conn.execute(
                text("""
                    SELECT i.mensagem, i.direcao, i.criado_em
                    FROM interacoes i
                    JOIN leads l ON l.id = i.lead_id
                    WHERE l.user_id = :uid
                      AND (
                        :tel IN (l.telefone, l.telefone_whatsapp, l.whatsapp)
                        OR regexp_replace(COALESCE(l.telefone_whatsapp, l.whatsapp, l.telefone, ''), '\\D', '', 'g')
                           = regexp_replace(:tel, '\\D', '', 'g')
                      )
                    ORDER BY i.criado_em DESC
                    LIMIT 5
                """),
                {"uid": user_id, "tel": telefone},
            ).fetchall()

            if not rows:
                return True, "no_history"

            # Contar mensagens de saída vs entrada desde o último contato
            outbound_count = 0
            last_outbound_time = None
            last_real_response_time = None

            for row in rows:
                mensagem, direcao, criado_em = row
                if direcao == "saida":
                    outbound_count += 1
                    if last_outbound_time is None:
                        last_outbound_time = criado_em
                elif direcao == "entrada":
                    # Verificar se é uma resposta real (não só emoji)
                    if not is_emoji_reaction_only(mensagem):
                        last_real_response_time = criado_em
                        break  # Resposta real encontrada, parar

            # REGRA 1: Já mandou 2 mensagens sem resposta → lost
            if outbound_count >= 2 and last_real_response_time is None:
                print(f"[Watchdog][DEBUG] BLOQUEADO tel={telefone}: max_2_messages_without_response (outbound_count={outbound_count})")
                return False, "max_2_messages_without_response"

            # REGRA 2: Cooldown mínimo de 24h entre mensagens
            if last_outbound_time:
                now = datetime.now(timezone.utc)
                if last_outbound_time.tzinfo is None:
                    last_outbound_time = last_outbound_time.replace(tzinfo=timezone.utc)
                time_since_last = now - last_outbound_time
                if time_since_last < timedelta(hours=24):
                    hours_remaining = 24 - time_since_last.total_seconds() / 3600
                    print(f"[Watchdog][DEBUG] BLOQUEADO tel={telefone}: cooldown {hours_remaining:.1f}h remaining")
                    return False, f"cooldown_active_{hours_remaining:.1f}h_remaining"

            # REGRA 3: Se já é followup_72h, não mandar mais
            if sdr_stage == "followup_72h":
                print(f"[Watchdog][DEBUG] BLOQUEADO tel={telefone}: already_in_final_followup_stage")
                return False, "already_in_final_followup_stage"

            return True, "ok"

    except Exception as e:
        print(f"[Watchdog] Erro: {e}")
        return True, "watchdog_error"


def get_outbound_count(telefone: str, user_id: int) -> int:
    """Conta quantas mensagens de saída o Franz já mandou sem resposta real"""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT i.mensagem, i.direcao, i.criado_em
                    FROM interacoes i
                    JOIN leads l ON l.id = i.lead_id
                    WHERE l.user_id = :uid
                      AND (
                        :tel IN (l.telefone, l.telefone_whatsapp, l.whatsapp)
                        OR regexp_replace(COALESCE(l.telefone_whatsapp, l.whatsapp, l.telefone, ''), '\\D', '', 'g')
                           = regexp_replace(:tel, '\\D', '', 'g')
                      )
                    ORDER BY i.criado_em DESC
                    LIMIT 10
                """),
                {"uid": user_id, "tel": telefone},
            ).fetchall()

            outbound = 0
            for row in rows:
                mensagem, direcao, criado_em = row
                if direcao == "entrada" and not is_emoji_reaction_only(mensagem):
                    # Resposta real encontrada
                    return outbound
                elif direcao == "saida":
                    outbound += 1
            return outbound
    except Exception:
        return 0
