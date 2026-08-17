"""closer_queue: handoff real do SDR para o closer humano.

Quando o lead chega no stage 'won' ou pede explicitamente fechamento humano,
o sistema cria uma entrada nesta fila. O closer recebe contexto completo e
assume a conversa via WhatsApp.
"""

from typing import Any, Dict, Optional

from sqlalchemy import text


# Schema versionado — toda migration nova DEVE incrementar SCHEMA_VERSION
SCHEMA_VERSION = 1


CREATE_CLOSER_QUEUE = """
CREATE TABLE IF NOT EXISTS closer_queue (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    lead_id BIGINT NOT NULL,
    lead_telefone VARCHAR(30) NOT NULL,
    lead_nome VARCHAR(255),
    stage_at_handoff VARCHAR(50) NOT NULL,
    context_json TEXT NOT NULL,
    bant_score INTEGER DEFAULT 0,
    meddic_score INTEGER DEFAULT 0,
    main_objection TEXT,
    pain_identified TEXT,
    temperature VARCHAR(20) DEFAULT 'morno',
    status VARCHAR(20) DEFAULT 'pending',
    claimed_by VARCHAR(100),
    claimed_at TIMESTAMP,
    completed_at TIMESTAMP,
    closer_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_closer_queue_user_status ON closer_queue (user_id, status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_closer_queue_lead ON closer_queue (lead_id)",
]


def ensure_closer_queue_schema(engine) -> None:
    """Cria tabela closer_queue se não existir (idempotente)."""
    with engine.connect() as conn:
        conn.execute(text(CREATE_CLOSER_QUEUE))
        for idx in CREATE_INDEXES:
            conn.execute(text(idx))
        conn.commit()


def enqueue_closer(
    engine,
    *,
    user_id: int,
    lead_id: int,
    lead_telefone: str,
    lead_nome: str,
    stage_at_handoff: str,
    context: Dict[str, Any],
    bant_score: int = 0,
    meddic_score: int = 0,
    main_objection: str = "",
    pain_identified: str = "",
    temperature: str = "morno",
) -> int:
    """Enfileira lead para closer humano. Retorna id da fila."""
    import json
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                INSERT INTO closer_queue
                    (user_id, lead_id, lead_telefone, lead_nome, stage_at_handoff,
                     context_json, bant_score, meddic_score, main_objection,
                     pain_identified, temperature)
                VALUES
                    (:uid, :lid, :tel, :nome, :stage, :ctx, :bant, :meddic,
                     :obj, :pain, :temp)
                RETURNING id
            """),
            {
                "uid": user_id,
                "lid": lead_id,
                "tel": lead_telefone,
                "nome": lead_nome,
                "stage": stage_at_handoff,
                "ctx": json.dumps(context, ensure_ascii=False),
                "bant": bant_score,
                "meddic": meddic_score,
                "obj": main_objection,
                "pain": pain_identified,
                "temp": temperature,
            },
        ).fetchone()
        conn.commit()
        return int(row[0])


def list_pending(
    engine,
    *,
    user_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lista leads pendentes na fila do closer (status='pending')."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, lead_id, lead_telefone, lead_nome, stage_at_handoff,
                       bant_score, meddic_score, main_objection, pain_identified,
                       temperature, created_at, context_json
                FROM closer_queue
                WHERE user_id = :uid AND status = 'pending'
                ORDER BY
                    CASE temperature WHEN 'quente' THEN 0 WHEN 'morno' THEN 1 ELSE 2 END,
                    bant_score + meddic_score DESC,
                    created_at ASC
                LIMIT :lim
            """),
            {"uid": user_id, "lim": limit},
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "lead_id": r[1],
            "lead_telefone": r[2],
            "lead_nome": r[3],
            "stage_at_handoff": r[4],
            "bant_score": r[5],
            "meddic_score": r[6],
            "main_objection": r[7],
            "pain_identified": r[8],
            "temperature": r[9],
            "created_at": r[10].isoformat() if r[10] else None,
            "context": json.loads(r[11]) if r[11] else {},
        })
    return out


def claim(
    engine,
    *,
    queue_id: int,
    claimed_by: str,
    user_id: int,
) -> bool:
    """Closer reivindica lead. Retorna True se conseguiu."""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                UPDATE closer_queue
                SET status = 'claimed', claimed_by = :who, claimed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :qid AND user_id = :uid AND status = 'pending'
            """),
            {"qid": queue_id, "who": claimed_by, "uid": user_id},
        )
        conn.commit()
        return result.rowcount > 0


def complete(
    engine,
    *,
    queue_id: int,
    user_id: int,
    closer_notes: str = "",
    won: bool = False,
) -> bool:
    """Closer marca como done."""
    final_status = "won" if won else "lost"
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                UPDATE closer_queue
                SET status = :st, completed_at = NOW(),
                    closer_notes = :notes, updated_at = NOW()
                WHERE id = :qid AND user_id = :uid
            """),
            {"qid": queue_id, "uid": user_id, "st": final_status, "notes": closer_notes},
        )
        conn.commit()
        return result.rowcount > 0


def get_stats(engine, *, user_id: int, days: int = 30) -> dict[str, Any]:
    """Estatísticas da fila para o tenant."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    COUNT(*) FILTER (WHERE status = 'claimed') AS claimed,
                    COUNT(*) FILTER (WHERE status = 'won') AS won,
                    COUNT(*) FILTER (WHERE status = 'lost') AS lost,
                    COUNT(*) AS total,
                    AVG(bant_score + meddic_score) FILTER (WHERE status IN ('won','lost')) AS avg_score
                FROM closer_queue
                WHERE user_id = :uid AND created_at > NOW() - (:d || ' days')::interval
            """),
            {"uid": user_id, "d": str(days)},
        ).fetchone()
    return {
        "pending": int(row[0] or 0),
        "claimed": int(row[1] or 0),
        "won": int(row[2] or 0),
        "lost": int(row[3] or 0),
        "total": int(row[4] or 0),
        "avg_score": float(row[5] or 0),
        "conversion_rate": (int(row[2] or 0) / max(int(row[4] or 0), 1)) * 100,
        "window_days": days,
    }
