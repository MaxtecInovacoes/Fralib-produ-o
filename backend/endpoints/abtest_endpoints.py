"""A/B Test Reporting endpoints (Fase 5).

Tabela franz_ab_events criada em database.py.
Endpoints:
  POST /api/abtest/register  — agent.py chama ao enviar variante
  POST /api/abtest/convert/{lead_id} — marca conversão
  GET  /api/abtest/report    — agrega impressões, conversões, taxa, significância
"""

from fastapi import APIRouter, Depends
from backend.core.db_imports import Session, text  # noqa: F401
import math

from backend.core.database import get_db
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/abtest", tags=["abtest"])


def _tid(usuario: dict) -> int:
    return int(usuario.get("tenant_id", usuario["id"]))


@router.post("/register")
async def register_ab_event(
    variant_name: str,
    axis: str,
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Registra que lead recebeu variante X."""
    try:
        uid = _tid(usuario)
        db.execute(
            text("""
                INSERT INTO franz_ab_events (tenant_id, variant_name, axis, lead_id)
                VALUES (:uid, :vn, :ax, :lid)
            """),
            {"uid": uid, "vn": variant_name, "ax": axis, "lid": lead_id},
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        print(f"[ABTest] Erro register: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/convert/{lead_id}")
async def convert_ab_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Marca todas as variantes deste lead como converted."""
    try:
        uid = _tid(usuario)
        db.execute(
            text("""
                UPDATE franz_ab_events
                SET converted = TRUE, converted_at = NOW()
                WHERE lead_id = :lid AND tenant_id = :uid AND converted = FALSE
            """),
            {"lid": lead_id, "uid": uid},
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        print(f"[ABTest] Erro convert: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/report")
async def get_ab_report(
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Agrega: variante, eixo, impressões, conversões, taxa, significância."""
    try:
        uid = _tid(usuario)
        rows = db.execute(
            text("""
                SELECT
                    variant_name,
                    axis,
                    COUNT(*) as impressions,
                    SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions
                FROM franz_ab_events
                WHERE tenant_id = :uid
                GROUP BY variant_name, axis
                ORDER BY axis, impressions DESC
            """),
            {"uid": uid},
        ).fetchall()

        report = []
        for r in rows:
            rate = round(r.conversions / r.impressions * 100, 2) if r.impressions else 0.0
            report.append({
                "variant_name": r.variant_name,
                "axis": r.axis,
                "impressions": r.impressions,
                "conversions": r.conversions,
                "conversion_rate": rate,
            })

        # Agrupar por axis para calcular significância (chi-squared-like)
        grouped = {}
        for item in report:
            ax = item["axis"]
            grouped.setdefault(ax, []).append(item)

        # Adicionar significance score para cada eixo
        for ax, items in grouped.items():
            if len(items) < 2:
                for it in items:
                    it["significance"] = None
                continue
            total_imp = sum(it["impressions"] for it in items)
            total_conv = sum(it["conversions"] for it in items)
            if total_imp == 0:
                continue
            overall_rate = total_conv / total_imp
            chi2 = 0.0
            for it in items:
                if it["impressions"] == 0:
                    continue
                expected = overall_rate * it["impressions"]
                if expected > 0:
                    chi2 += (it["conversions"] - expected) ** 2 / expected
            # Convert chi2 to approximate significance (1 degree of freedom)
            # Very rough: chi2 > 3.84 ~ p < 0.05
            if chi2 > 10.83:
                sig = "high"
            elif chi2 > 5.02:
                sig = "medium"
            elif chi2 > 3.84:
                sig = "low"
            else:
                sig = "none"
            for it in items:
                it["significance"] = sig
                it["chi2"] = round(chi2, 2)

        return {"report": report, "total": len(report)}
    except Exception as e:
        print(f"[ABTest] Erro report: {e}")
        import traceback
        traceback.print_exc()
        return {"report": [], "total": 0}
