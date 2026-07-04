from fastapi import APIRouter, Depends
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY

from backend.core.auth import get_current_user
from backend.core.database import get_db

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/ciclos")
async def get_ciclos(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id_c = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT
                id, numero, cidade, segmento,
                leads_buscados, sites_gerados, enviados, erros,
                iniciado_em, concluido_em, user_id
            FROM ciclos
            WHERE user_id = :uid
            ORDER BY id DESC
            LIMIT 100
        """),
            {"uid": tenant_id_c},
        ).fetchall()

        ciclos = []
        for r in result:
            d = dict(r._mapping)
            leads = d["leads_buscados"] or 0
            sites = d["sites_gerados"] or 0
            conv = round(sites / leads * 100, 1) if leads > 0 else 0
            ciclos.append(
                {
                    "id": d["id"],
                    "numero": d["numero"],
                    "nicho": d["segmento"] or "-",
                    "cidade": d["cidade"] or "-",
                    "leads_buscados": leads,
                    "sites_gerados": sites,
                    "enviados": d["enviados"] or 0,
                    "erros": d["erros"] or 0,
                    "conversao": conv,
                    "iniciado_em": str(d["iniciado_em"] or ""),
                    "concluido_em": str(d["concluido_em"] or ""),
                }
            )

        return {"ciclos": ciclos, "total": len(ciclos)}
    except Exception as e:
        print(f"[Ciclos] Erro: {e}")
        return {"ciclos": [], "total": 0}

