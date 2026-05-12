from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/llm", tags=["llm"])

# Limites do plano Anthropic 20x (tokens por minuto por modelo)
LIMITES = {
    "claude-opus-4-7":    {"rpm": 2000,  "tpm": 320000,  "tpd": 10000000},
    "claude-sonnet-4-6":  {"rpm": 2000,  "tpm": 320000,  "tpd": 40000000},
    "claude-haiku-4-5":   {"rpm": 2000,  "tpm": 320000,  "tpd": 100000000},
}

@router.get("/usage")
async def llm_usage(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    if usuario.get("plano") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    # Uso hoje
    hoje = db.execute(text("""
        SELECT modelo,
               SUM(input_tokens) as input,
               SUM(output_tokens) as output,
               COUNT(*) as chamadas
        FROM llm_usage
        WHERE criado_em >= NOW() - INTERVAL '24 hours'
        GROUP BY modelo
        ORDER BY modelo
    """)).fetchall()

    # Uso mes
    mes = db.execute(text("""
        SELECT modelo,
               SUM(input_tokens) as input,
               SUM(output_tokens) as output,
               COUNT(*) as chamadas
        FROM llm_usage
        WHERE criado_em >= DATE_TRUNC('month', NOW())
        GROUP BY modelo
        ORDER BY modelo
    """)).fetchall()

    # Total geral
    total = db.execute(text("""
        SELECT SUM(input_tokens + output_tokens) as total,
               COUNT(*) as chamadas
        FROM llm_usage
        WHERE criado_em >= NOW() - INTERVAL '24 hours'
    """)).fetchone()

    modelos_hoje = {}
    for row in hoje:
        modelo = row[0]
        total_tokens = (row[1] or 0) + (row[2] or 0)
        limite = LIMITES.get(modelo, {"tpd": 10000000})
        pct = round((total_tokens / limite["tpd"]) * 100, 1) if limite["tpd"] else 0
        modelos_hoje[modelo] = {
            "input": row[1] or 0,
            "output": row[2] or 0,
            "total": total_tokens,
            "chamadas": row[3] or 0,
            "limite_dia": limite["tpd"],
            "percentual": pct,
        }

    modelos_mes = {}
    for row in mes:
        modelo = row[0]
        total_tokens = (row[1] or 0) + (row[2] or 0)
        modelos_mes[modelo] = {
            "input": row[1] or 0,
            "output": row[2] or 0,
            "total": total_tokens,
            "chamadas": row[3] or 0,
        }

    return {
        "hoje": modelos_hoje,
        "mes": modelos_mes,
        "total_tokens_hoje": total[0] or 0 if total else 0,
        "total_chamadas_hoje": total[1] or 0 if total else 0,
    }
