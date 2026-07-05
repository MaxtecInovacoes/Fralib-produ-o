"""
Lead Supply Watchdog - Monitoramento proativo do sistema de prospecção.

Executa checks periódicos para detectar:
1. Hunter parado (sem novas buscas há X horas)
2. Caio parado (sem qualificações há X horas)
3. Gap entre Hunter e Caio (leads "raw" sem progressão)
4. Scrapers indisponíveis (GOSOM + Playwright)

Uso:
    python -m backend.services.lead_supply_watchdog
    # ou via API:
    from backend.services.lead_supply_watchdog import run_lead_supply_health_check, diagnose_all_tenants
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from backend.utils.time import now_iso_utc  # noqa: E402  — M14 DRY

from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
logger = logging.getLogger("fralib.lead_supply_watchdog")

# ---- Config ----
GOSOM_BASE_URL = os.getenv("GOSOM_BASE_URL", "http://localhost:8085")
GOSOM_TIMEOUT = int(os.getenv("GOSOM_TIMEOUT", "5"))
STALE_HOURS_HUNTER = int(os.getenv("LEAD_SUPPLY_STALE_HOURS_HUNTER", "4"))
STALE_HOURS_CAIO = int(os.getenv("LEAD_SUPPLY_STALE_HOURS_CAIO", "2"))
STALE_HOURS_RAW_LEAD = int(os.getenv("LEAD_SUPPLY_STALE_HOURS_RAW_LEAD", "1"))


# ---- Tipos ----

class LeadSupplyAlert:
    """Alerta específico do Lead Supply."""

    def __init__(
        self,
        level: str,  # warning, critical
        title: str,
        message: str,
        check_name: str,
        details: dict | None = None,
    ):
        self.level = level
        self.title = title
        self.message = message
        self.check_name = check_name
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "check": self.check_name,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self):
        return f"[{self.level.upper()}] {self.title}: {self.message}"


# ---- Checks de Atividade ----

def check_hunter_activity(db: Session, horas: int | None = None) -> LeadSupplyAlert | None:
    """
    Verifica se o Hunter está ativo (gerando eventos recentes).

    Alerta se:
    - Não há eventos 'hunter' nos últimos X horas
    - E existem tenants com hunter_pausado=FALSE
    """
    horas = horas or STALE_HOURS_HUNTER

    # Conta eventos hunter recentes
    result = db.execute(
        text("""
            SELECT COUNT(*)
            FROM lead_supply_events
            WHERE source = 'hunter'
              AND criado_em > NOW() - INTERVAL ':horas hours'
        """),
        {"horas": horas},
    ).fetchone()
    eventos_hunter = result[0] if result else 0

    # Verifica se há tenants ativos (hunter não pausado)
    result_tenants = db.execute(
        text("""
            SELECT COUNT(*)
            FROM lead_supply_config
            WHERE ativo = TRUE
              AND hunter_pausado = FALSE
              AND (segmentos IS NOT NULL AND jsonb_array_length(segmentos) > 0)
        """)
    ).fetchone()
    tenants_ativos = result_tenants[0] if result_tenants else 0

    if tenants_ativos > 0 and eventos_hunter == 0:
        return LeadSupplyAlert(
            level="critical",
            title="Hunter Parado",
            message=f"Nenhum evento do Hunter nos últimos {horas}h. {tenants_ativos} tenant(s) ativo(s) mas sem prospecção.",
            check_name="hunter_activity",
            details={
                "eventos_hunter_ultimas_horas": eventos_hunter,
                "tenants_ativos": tenants_ativos,
                "horas_sem_eventos": horas,
            },
        )
    return None


def check_caio_activity(db: Session, horas: int | None = None) -> LeadSupplyAlert | None:
    """
    Verifica se o Caio está ativo (qualificando leads).

    Alerta se:
    - Não há eventos 'caio' nos últimos X horas
    - E há leads "raw" pendentes
    """
    horas = horas or STALE_HOURS_CAIO

    # Conta eventos caio recentes
    result = db.execute(
        text("""
            SELECT COUNT(*)
            FROM lead_supply_events
            WHERE source = 'caio'
              AND criado_em > NOW() - INTERVAL ':horas hours'
        """),
        {"horas": horas},
    ).fetchone()
    eventos_caio = result[0] if result else 0

    # Conta leads raw pendentes
    result_raw = db.execute(
        text("""
            SELECT COUNT(*)
            FROM lead_inventory
            WHERE status = 'raw'
              AND criado_em < NOW() - INTERVAL ':horas hours'
        """),
        {"horas": horas},
    ).fetchone()
    leads_raw_velhos = result_raw[0] if result_raw else 0

    if leads_raw_velhos > 0 and eventos_caio == 0:
        return LeadSupplyAlert(
            level="critical",
            title="Caio Parado",
            message=f"Caio sem atividade há {horas}h. {leads_raw_velhos} leads 'raw' pendentes sem qualificação.",
            check_name="caio_activity",
            details={
                "eventos_caio_ultimas_horas": eventos_caio,
                "leads_raw_pendentes": leads_raw_velhos,
                "horas_sem_eventos": horas,
            },
        )
    return None


def check_hunter_caio_gap(db: Session, horas: int | None = None) -> LeadSupplyAlert | None:
    """
    Verifica gap entre Hunter e Caio.

    Alerta se:
    - Há leads "raw" sem progressão há mais de X horas
    - Sugere que o Caio quebrou ou a fila está travada
    """
    horas = horas or STALE_HOURS_RAW_LEAD

    result = db.execute(
        text("""
            SELECT
                l.segmento,
                l.cidade,
                l.tenant_id,
                COUNT(*) as total
            FROM lead_inventory l
            JOIN lead_supply_config c ON l.tenant_id = c.tenant_id
            WHERE l.status = 'raw'
              AND l.atualizado_em < NOW() - INTERVAL ':horas hours'
              AND c.ativo = TRUE
              AND c.hunter_pausado = FALSE
            GROUP BY l.segmento, l.cidade, l.tenant_id
            ORDER BY total DESC
            LIMIT 10
        """),
        {"horas": horas},
    ).fetchall()

    if result:
        details = [
            {"segmento": r[0], "cidade": r[1], "tenant_id": r[2], "leads": r[3]}
            for r in result
        ]
        total_leads = sum(r[3] for r in result)
        return LeadSupplyAlert(
            level="warning",
            title="Gap Hunter → Caio",
            message=f"{total_leads} leads 'raw' sem progressão há {horas}h+. Caio pode estar travado.",
            check_name="hunter_caio_gap",
            details={"stuck_leads": details, "horas_estagnado": horas},
        )
    return None


# ---- Checks de Scrapers ----

async def check_gosom_availability() -> tuple[bool, str]:
    """
    Verifica se o GOSOM está disponível.

    Returns:
        (disponivel: bool, status: str)
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=GOSOM_TIMEOUT) as client:
            r = await client.get(f"{GOSOM_BASE_URL}/api/v1/jobs")
            if r.status_code == 200:
                return True, "available"
            return False, f"http_{r.status_code}"
    except httpx.ConnectError:
        return False, "connection_refused"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, f"error_{type(e).__name__}"


async def check_scraper_availability() -> LeadSupplyAlert | None:
    """
    Verifica se pelo menos um scraper está disponível.

    Alerta crítico se ambos (GOSOM + Playwright) estão offline.
    """
    gosom_ok, gosom_status = await check_gosom_availability()

    # Tenta Playwright como fallback
    playwright_ok = False
    try:
        from backend.utils.google_local_scraper import GoogleLocalScraper
        # Testa apenas instanciando (sem fazer scraping)
        playwright_ok = True  # Se importou, está disponível
    except Exception:
        pass

    if not gosom_ok and not playwright_ok:
        return LeadSupplyAlert(
            level="critical",
            title="Scrapers Indisponíveis",
            message="GOSOM e Playwright offline. Prospecção completamente parada.",
            check_name="scraper_availability",
            details={
                "gosom": {"available": gosom_ok, "status": gosom_status},
                "playwright": {"available": playwright_ok, "status": "unknown"},
            },
        )
    elif not gosom_ok:
        return LeadSupplyAlert(
            level="warning",
            title="GOSOM Indisponível",
            message="GOSOM offline. Sistema usando apenas Playwright (mais lento).",
            check_name="scraper_availability",
            details={
                "gosom": {"available": gosom_ok, "status": gosom_status},
                "playwright": {"available": playwright_ok, "status": "active"},
            },
        )
    return None


# ---- Diagnóstico Completo ----

def diagnose_all_tenants(db: Session) -> dict:
    """
    Retorna diagnóstico completo do Lead Supply para todos os tenants.

    Útil para o painel admin.
    """
    # Totais por status
    result_totals = db.execute(
        text("""
            SELECT status, COUNT(*) as total
            FROM lead_inventory
            GROUP BY status
        """)
    ).fetchall()
    totals = {r[0]: r[1] for r in result_totals}

    # Eventos por hora (últimas 24h)
    result_events = db.execute(
        text("""
            SELECT source, COUNT(*) as total
            FROM lead_supply_events
            WHERE criado_em > NOW() - INTERVAL '24 hours'
            GROUP BY source
        """)
    ).fetchall()
    events_24h = {r[0]: r[1] for r in result_events}

    # Tenants com problemas
    result_problemas = db.execute(
        text("""
            SELECT
                c.tenant_id,
                c.segmentos,
                c.cidades,
                c.ativo,
                c.hunter_pausado,
                c.producao_pausada,
                COUNT(CASE WHEN l.status = 'approved' THEN 1 END) as approved,
                COUNT(CASE WHEN l.status = 'raw' THEN 1 END) as raw,
                COUNT(CASE WHEN l.status = 'discarded' THEN 1 END) as discarded
            FROM lead_supply_config c
            LEFT JOIN lead_inventory l ON c.tenant_id = l.tenant_id
            WHERE c.ativo = TRUE
            GROUP BY c.tenant_id, c.segmentos, c.cidades, c.ativo, c.hunter_pausado, c.producao_pausada
            ORDER BY raw DESC
        """)
    ).fetchall()

    tenants = []
    for r in result_problemas:
        segmentos = r[1] if isinstance(r[1], list) else json.loads(r[1] or "[]")
        cidades = r[2] if isinstance(r[2], list) else json.loads(r[2] or "[]")
        tenants.append({
            "tenant_id": r[0],
            "segmentos": segmentos,
            "cidades": cidades,
            "ativo": r[3],
            "hunter_pausado": r[4],
            "producao_pausada": r[5],
            "leads_approved": r[6] or 0,
            "leads_raw": r[7] or 0,
            "leads_discarded": r[8] or 0,
        })

    return {
        "totals": totals,
        "events_24h": events_24h,
        "tenants": tenants,
        "timestamp": now_iso_utc(),
    }


# ---- Run All Checks ----

async def run_lead_supply_health_check() -> list[LeadSupplyAlert]:
    """
    Executa todos os checks de saúde do Lead Supply.

    Returns:
        Lista de alertas (vazia se tudo ok)
    """
    from database import SessionLocal

    alerts: list[LeadSupplyAlert] = []
    db = SessionLocal()

    try:
        # Check 1: Hunter activity
        try:
            alert = check_hunter_activity(db)
            if alert:
                alerts.append(alert)
                logger.warning(str(alert))
        except Exception as e:
            logger.error(f"Erro no check_hunter_activity: {e}")

        # Check 2: Caio activity
        try:
            alert = check_caio_activity(db)
            if alert:
                alerts.append(alert)
                logger.warning(str(alert))
        except Exception as e:
            logger.error(f"Erro no check_caio_activity: {e}")

        # Check 3: Hunter-Caio gap
        try:
            alert = check_hunter_caio_gap(db)
            if alert:
                alerts.append(alert)
                logger.warning(str(alert))
        except Exception as e:
            logger.error(f"Erro no check_hunter_caio_gap: {e}")

        # Check 4: Scraper availability (async)
        try:
            alert = await check_scraper_availability()
            if alert:
                alerts.append(alert)
                logger.warning(str(alert))
        except Exception as e:
            logger.error(f"Erro no check_scraper_availability: {e}")

    finally:
        db.close()

    return alerts


def send_lead_supply_alerts(alerts: list[LeadSupplyAlert]) -> None:
    """
    Envia alertas via email usando o sistema de alerting existente.
    """
    if not alerts:
        return

    try:
        from backend.services.alerting import send_alert as send_generic_alert, Alert as GenericAlert

        for alert in alerts:
            generic_alert = GenericAlert(
                level=alert.level,
                title=f"[Lead Supply] {alert.title}",
                message=alert.message,
                details=alert.details,
            )
            send_generic_alert(generic_alert)
            logger.info(f"Alert sent: {alert.title}")

    except ImportError:
        logger.warning("Alerting module not available - logging only")
        for alert in alerts:
            logger.warning(str(alert))


# ---- Auto-Recovery ----

def attempt_recovery(alert: LeadSupplyAlert) -> dict:
    """
    Tenta auto-recuperar o sistema baseado no tipo de alerta.

    Args:
        alert: O alerta que disparou a necessidade de recuperação

    Returns:
        dict com resultado da tentativa
    """
    from backend.core import job_queue

    result = {
        "alert": alert.check_name,
        "attempted": False,
        "success": False,
        "message": "",
    }

    try:
        from database import SessionLocal
        db = SessionLocal()

        try:
            if alert.check_name == "hunter_activity":
                result["attempted"] = True
                # Re-enqueue hunter jobs para tenants ativos
                requeued = job_queue.enqueue_job(
                    db=db,
                    tipo="lead_supply_hunter",
                    tenant_id=None,  # null = todos
                    payload={"reason": "watchdog_recovery", "force": True},
                )
                result["success"] = True
                result["message"] = f"Hunter jobs re-enfileirados: {requeued}"

            elif alert.check_name == "caio_activity":
                result["attempted"] = True
                # Encontrar leads raw e re-enqueue para Caio
                rows = db.execute(
                    text("""
                        SELECT id, tenant_id
                        FROM lead_inventory
                        WHERE status = 'raw'
                        LIMIT 50
                    """)
                ).fetchall()
                enqueued = 0
                for row in rows:
                    job_queue.enqueue_job(
                        db=db,
                        tipo="lead_supply_caio",
                        tenant_id=row[1],
                        payload={"inventory_id": row[0]},
                    )
                    enqueued += 1
                result["success"] = True
                result["message"] = f"Caio jobs enfileirados: {enqueued} leads"

            elif alert.check_name == "scraper_availability":
                result["attempted"] = True
                # Tentar restart do GOSOM via systemctl
                import subprocess
                try:
                    r = subprocess.run(
                        ["systemctl", "restart", "gosom-scraper"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if r.returncode == 0:
                        result["success"] = True
                        result["message"] = "GOSOM reiniciado via systemctl"
                    else:
                        result["message"] = f"Falha ao reiniciar GOSOM: {r.stderr}"
                except FileNotFoundError:
                    # systemctl não disponível, tenta pm2
                    try:
                        r = subprocess.run(
                            ["pm2", "restart", "gosom-scraper"],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if r.returncode == 0:
                            result["success"] = True
                            result["message"] = "GOSOM reiniciado via pm2"
                        else:
                            result["message"] = f"Falha ao reiniciar GOSOM: {r.stderr}"
                    except Exception as e:
                        result["message"] = f"Não foi possível reiniciar GOSOM: {e}"

            else:
                result["message"] = f"Recovery não implementado para: {alert.check_name}"

        finally:
            db.close()

    except Exception as e:
        result["message"] = f"Erro durante recovery: {e}"
        logger.error(f"Recovery error: {e}")

    logger.info(f"[Recovery] {alert.check_name}: {result['message']}")
    return result


def run_with_recovery() -> list[dict]:
    """
    Executa checks e tenta recovery automático se necessário.

    Returns:
        Lista de resultados (check + recovery se aplicável)
    """
    alerts = asyncio.run(run_lead_supply_health_check())

    results = []
    for alert in alerts:
        results.append({
            "alert": alert.to_dict(),
        })
        # Tenta auto-recovery para alertas críticos
        if alert.level == "critical":
            recovery_result = attempt_recovery(alert)
            results[-1]["recovery"] = recovery_result

    return results


# ---- CLI / Cron ----

def run_once(with_recovery: bool = False) -> int:
    """
    Executa checks uma vez (para cron/CLI).

    Args:
        with_recovery: se True, tenta auto-recuperar problemas

    Returns:
        0 se tudo ok, 1 se houve alertas
    """
    print(f"[LeadSupplyWatchdog] Running health check at {now_iso_utc()}")

    if with_recovery:
        results = run_with_recovery()
        alerts = [r["alert"] for r in results]

        if alerts:
            print(f"[LeadSupplyWatchdog] ⚠️  {len(alerts)} alert(s):")
            for r in results:
                alert = r["alert"]
                print(f"  - [{alert['level']}] {alert['title']}: {alert['message']}")
                if "recovery" in r:
                    recovery = r["recovery"]
                    print(f"    Recovery: {recovery['message']}")
            send_lead_supply_alerts([LeadSupplyAlert(**a) for a in alerts])
            return 1
        else:
            print("[LeadSupplyWatchdog] ✓ All checks passed")
            return 0
    else:
        alerts = asyncio.run(run_lead_supply_health_check())

        if alerts:
            print(f"[LeadSupplyWatchdog] ⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                print(f"  - {alert}")
            send_lead_supply_alerts(alerts)
            return 1
        else:
            print("[LeadSupplyWatchdog] ✓ All checks passed")
            return 0


if __name__ == "__main__":
    import sys
    with_recovery = "--recovery" in sys.argv
    exit(run_once(with_recovery=with_recovery))
