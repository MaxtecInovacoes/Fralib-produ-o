"""
Endpoints disparados por cron externo (crontab/PM2).

Autenticacao por header X-Cron-Secret == CRON_SECRET do .env.
Nunca expor sem secret - estes endpoints podem mandar emails em massa.
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from database import engine
from services.email_service import enviar_email_resumo_diario

router = APIRouter(prefix='/api/cron', tags=['cron'])

CRON_SECRET = os.getenv('CRON_SECRET', '')


def _autorizar(x_cron_secret: str):
    if not CRON_SECRET:
        raise HTTPException(500, 'CRON_SECRET nao configurado no .env')
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(403, 'Cron secret invalido')


@router.post('/email-resumo-diario')
async def email_resumo_diario(x_cron_secret: str = Header(None, alias='X-Cron-Secret')):
    """Agrupa leads concluidos nas ultimas 24h por usuario e envia 1 email.
    Idempotencia simples: nao reenvia se a coluna ultimo_resumo_em foi atualizada hoje.
    """
    _autorizar(x_cron_secret)

    janela_inicio = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    hoje = datetime.utcnow().date().isoformat()
    enviados = 0
    pulados = 0
    erros = 0

    with engine.connect() as conn:
        # Garante a coluna de idempotencia (idempotente)
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS ultimo_resumo_em TIMESTAMP"
        ))
        conn.commit()

        # Usuarios com pelo menos 1 lead concluido nas ultimas 24h
        rows = conn.execute(text("""
            SELECT u.id, u.email, u.nome, u.ultimo_resumo_em
            FROM users u
            WHERE EXISTS (
                SELECT 1 FROM leads l
                WHERE l.user_id = u.id
                  AND l.status = 'concluido'
                  AND l.processado_em >= :inicio
            )
        """), {'inicio': janela_inicio}).fetchall()

        for u in rows:
            uid, email, nome, ultimo = int(u[0]), u[1], u[2] or 'Cliente', u[3]
            # Pulou se ja enviou hoje
            if ultimo and str(ultimo)[:10] == hoje:
                pulados += 1
                continue
            leads_rows = conn.execute(text("""
                SELECT nome, COALESCE(site_url, url_site) AS site_url, cidade
                FROM leads
                WHERE user_id = :uid
                  AND status = 'concluido'
                  AND processado_em >= :inicio
                ORDER BY processado_em DESC
                LIMIT 50
            """), {'uid': uid, 'inicio': janela_inicio}).fetchall()
            leads = [{'nome': r[0], 'site_url': r[1], 'cidade': r[2]} for r in leads_rows]
            if not leads:
                continue
            try:
                ok = await enviar_email_resumo_diario(email, nome, leads)
                if ok:
                    enviados += 1
                    conn.execute(text(
                        "UPDATE users SET ultimo_resumo_em = NOW() WHERE id = :uid"
                    ), {'uid': uid})
                    conn.commit()
                else:
                    erros += 1
            except Exception as e:
                print(f'[Cron resumo] erro user {uid}: {e}')
                erros += 1

    return {'status': 'ok', 'enviados': enviados, 'pulados': pulados, 'erros': erros}
