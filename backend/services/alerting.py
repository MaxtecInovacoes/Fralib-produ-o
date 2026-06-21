"""
Alerting Service - Monitoramento proativo do sistema.

Verifica condições críticas e envia alertas quando necessário.
Pode ser chamado via cron ou endpoint.
"""
import os
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import text

logger = logging.getLogger("fralib.alerts")


class AlertLevel(str):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    def __init__(self, level: str, title: str, message: str, details: dict = None):
        self.level = level
        self.title = title
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def __str__(self):
        return f"[{self.level.upper()}] {self.title}: {self.message}"


def check_db_pool_health() -> Optional[Alert]:
    """Verifica se o connection pool está sobrecarregado."""
    try:
        from database import engine
        pool = engine.pool
        total = pool.size() + max(pool.overflow(), 1)
        utilization = pool.checkedout() / total

        if utilization > 0.9:
            return Alert(
                level=AlertLevel.CRITICAL,
                title="DB Pool sobrecarregado",
                message=f"Pool {utilization*100:.0f}% utilizado ({pool.checkedout()}/{total})",
                details={"checked_out": pool.checkedout(), "total": total, "utilization": utilization},
            )
        elif utilization > 0.75:
            return Alert(
                level=AlertLevel.WARNING,
                title="DB Pool em atenção",
                message=f"Pool {utilization*100:.0f}% utilizado",
                details={"checked_out": pool.checkedout(), "total": total},
            )
    except Exception as e:
        return Alert(
            level=AlertLevel.CRITICAL,
            title="Erro ao verificar DB pool",
            message=str(e),
        )
    return None


def check_llm_error_rate() -> Optional[Alert]:
    """Verifica taxa de erros LLM nas últimas horas."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            # Conta erros nas últimas 2 horas
            result = db.execute(text("""
                SELECT COUNT(*) FROM provider_alerts
                WHERE alert_type IN ('rate_limit', 'key_invalid', 'all_keys_failed', 'test_failed')
                AND created_at > NOW() - INTERVAL '2 hours'
            """)).fetchone()
            error_count = result[0] if result else 0

            if error_count > 50:
                return Alert(
                    level=AlertLevel.CRITICAL,
                    title="Alta taxa de erros LLM",
                    message=f"{error_count} erros nas últimas 2 horas",
                    details={"error_count": error_count},
                )
            elif error_count > 20:
                return Alert(
                    level=AlertLevel.WARNING,
                    title="Taxa elevada de erros LLM",
                    message=f"{error_count} erros nas últimas 2 horas",
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao verificar taxa de erros LLM: {e}")
    return None


def check_pipeline_jobs() -> Optional[Alert]:
    """Verifica se a fila canônica `jobs` está estagnada."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT COUNT(*) FROM jobs
                WHERE status = 'pending'
                  AND tipo IN ('pipeline_lead', 'pipeline_multiplos', 'pipeline_main')
                  AND criado_em < NOW() - INTERVAL '30 minutes'
            """)).fetchone()
            stuck_jobs = result[0] if result else 0

            if stuck_jobs > 10:
                return Alert(
                    level=AlertLevel.WARNING,
                    title="Jobs pendentes estagnados",
                    message=f"{stuck_jobs} jobs pendentes há mais de 30 minutos",
                    details={"stuck_jobs": stuck_jobs, "source": "jobs"},
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao verificar fila de pipeline: {e}")
    return None


def check_redis_health() -> Optional[Alert]:
    """Verifica se Redis está disponível."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None

    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
    except Exception as e:
        return Alert(
            level=AlertLevel.WARNING,
            title="Redis indisponível",
            message="Cache Redis não está respondendo. Sistema continuará com cache em memória.",
            details={"error": str(e)},
        )
    return None


def check_llm_budget() -> Optional[Alert]:
    """Verifica se o budget LLM está acabando."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            # Verifica budget usado hoje
            result = db.execute(text("""
                SELECT COALESCE(SUM(cost_usd), 0) as total_cost
                FROM llm_budget_ledger
                WHERE DATE(created_at) = CURRENT_DATE
            """)).fetchone()
            daily_cost = float(result[0] if result else 0)

            # Limite diário default
            daily_limit = float(os.getenv("GLOBAL_DAILY_TOKEN_BUDGET", "2000000"))
            # Aproximação: $1 por100k tokens
            cost_limit = daily_limit / 100000

            if daily_cost > cost_limit * 0.9:
                return Alert(
                    level=AlertLevel.CRITICAL,
                    title="Budget LLM quase esgotado",
                    message=f"${daily_cost:.2f} gastos hoje (limite: ${cost_limit:.2f})",
                    details={"daily_cost": daily_cost, "cost_limit": cost_limit},
                )
            elif daily_cost > cost_limit * 0.75:
                return Alert(
                    level=AlertLevel.WARNING,
                    title="Budget LLM em atenção",
                    message=f"${daily_cost:.2f} gastos hoje de ${cost_limit:.2f}",
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao verificar budget LLM: {e}")
    return None


def run_health_checks() -> list[Alert]:
    """Executa todos os checks de saúde."""
    checks = [
        check_db_pool_health,
        check_llm_error_rate,
        check_pipeline_jobs,
        check_redis_health,
        check_llm_budget,
    ]

    alerts = []
    for check in checks:
        try:
            alert = check()
            if alert:
                alerts.append(alert)
                logger.warning(str(alert))
        except Exception as e:
            logger.error(f"Erro no check {check.__name__}: {e}")

    return alerts


def send_alert(alert: Alert):
    """Envia alerta via email (Resend) e log."""
    logger.warning(f"ALERT [{alert.level.upper()}]: {alert.title} - {alert.message}")

    # Email via Resend
    try:
        import resend
        resend.api_key = os.getenv("RESEND_API_KEY", "")
        from_email = os.getenv("FROM_EMAIL", "noreply@seunegociofralib.site")
        admin_email = os.getenv("SUPERADMIN_EMAIL", "")

        if not resend.api_key:
            logger.debug("RESEND_API_KEY not configured - email skipped")
            return
        if not admin_email:
            logger.debug("SUPERADMIN_EMAIL not configured - email skipped")
            return

        import json as _json
        subject = f"[FraLib {alert.level.upper()}] {alert.title}"
        body_html = f"""
        <h2>{alert.title}</h2>
        <p><strong>Nivel:</strong> {alert.level}</p>
        <p><strong>Mensagem:</strong> {alert.message}</p>
        <p><strong>Timestamp:</strong> {alert.timestamp}</p>
        <pre style="background:#f5f5f5;padding:12px;border-radius:6px;font-size:12px">{_json.dumps(alert.details, indent=2, default=str)[:1000]}</pre>
        <p><em>Enviado automaticamente pelo watchdog do FraLib</em></p>
        """
        resend.Emails.send({
            "from": from_email,
            "to": [admin_email],
            "subject": subject,
            "html": body_html,
        })
        logger.info(f"Alert email sent: {subject}")
    except ImportError:
        logger.debug("resend not installed - pip install resend")
    except Exception as e:
        logger.warning(f"Failed to send alert email: {e}")


def hook_pos_falha(erro_tecnico: str, fase: str | None = None, tenant_id: int = None) -> dict:
    """Hook chamado apos cada falha registrada.

    Args:
        erro_tecnico: mensagem do erro
        fase: fase do pipeline (opcional)
        tenant_id: ID do tenant (opcional)

    Returns:
        dict com decisao de auto-fix + alerta (se aplicavel)
    """
    resultado = {"auto_fix": None, "alerta": None}

    # 1. Tentar auto-fix
    try:
        from backend.services.auto_fix import tentar_auto_fix
        fix = tentar_auto_fix(erro_tecnico, tentativas_anteriores=0, max_tentativas_total=3)
        resultado["auto_fix"] = fix.to_dict()
    except Exception as e:
        logger.warning(f"erro no auto_fix: {e}")

    # 2. Criar alerta se necessario
    if not resultado["auto_fix"] or not resultado["auto_fix"].get("sucesso"):
        try:
            alerta = Alert(
                level="warning",
                title="Falha no pipeline",
                message=f"Erro na fase '{fase or 'desconhecida'}'",
                details={
                    "erro": erro_tecnico[:200],
                    "fase": fase,
                    "tenant_id": tenant_id,
                }
            )
            send_alert(alerta)
            resultado["alerta"] = str(alerta)
        except Exception as e:
            logger.warning(f"erro ao criar alerta: {e}")

    return resultado


def check_and_alert():
    """Executa checks e envia alertas automaticamente."""
    alerts = run_health_checks()
    for alert in alerts:
        send_alert(alert)
    return alerts
