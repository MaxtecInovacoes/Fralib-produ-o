"""Persistencia de interacoes e estado SDR de leads."""

from datetime import datetime

from sqlalchemy import text


def save_interaction(
    engine,
    lead_id: str,
    mensagem: str,
    direcao: str,
    user_id: int | None = None,
    now_factory=datetime.now,
) -> None:
    """Salva uma mensagem na tabela interacoes."""
    with engine.connect() as conn:
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
