#!/usr/bin/env python3
"""
Lead Supply Diagnóstico e Recuperação
=====================================
Verifica o estado da esteira de prospecção e tenta recuperar tenants travados.

Uso:
    python scripts/lead_supply_diagnose.py [--fix]

Args:
    --fix   Tenta recuperar automaticamente tenants travados
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timezone

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from database import SessionLocal
from sqlalchemy import text


def banner(msg):
    print(f"\n{'='*60}")
    print(f" {msg}")
    print('='*60)


def check_gosom():
    """Verifica se GOSOM está disponível."""
    print("\n[1] Verificando GOSOM...")
    try:
        import httpx
        import asyncio
        async def _check():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get("http://localhost:8085/api/v1/jobs")
                    if r.status_code == 200:
                        return True, "online"
                    return False, f"http_{r.status_code}"
            except httpx.ConnectError:
                return False, "connection_refused"
            except httpx.TimeoutException:
                return False, "timeout"
            except Exception as e:
                return False, str(e)

        ok, status = asyncio.run(_check())
        if ok:
            print(f"    ✓ GOSOM está ONLINE")
        else:
            print(f"    ✗ GOSOM OFFLINE: {status}")
        return ok
    except ImportError:
        print("    ! httpx não disponível (instalando...)")
        return False


def check_scrapers():
    """Verifica todos os scrapers."""
    print("\n[2] Verificando Scrapers...")

    # GOSOM
    gosom_ok = check_gosom()

    # Playwright
    print("\n[3] Verificando Playwright...")
    playwright_ok = False
    try:
        from backend.utils.google_local_scraper import GoogleLocalScraper
        playwright_ok = True
        print("    ✓ Playwright disponível")
    except Exception as e:
        print(f"    ✗ Playwright falhou: {e}")

    return gosom_ok, playwright_ok


def check_tenants_status(db):
    """Verifica status de todos os tenants."""
    print("\n[4] Verificando Tenants...")

    rows = db.execute(text("""
        SELECT
            c.tenant_id,
            c.ativo,
            c.hunter_pausado,
            c.producao_pausada,
            c.segmentos,
            c.cidades,
            COUNT(CASE WHEN l.status = 'raw' THEN 1 END) as raw,
            Count(CASE WHEN l.status = 'qualifying' THEN 1 END) as qualifying,
            Count(CASE WHEN l.status = 'approved' THEN 1 END) as approved,
            Count(CASE WHEN l.status = 'discarded' THEN 1 END) as discarded
        FROM lead_supply_config c
        LEFT JOIN lead_inventory l ON c.tenant_id = l.tenant_id
        WHERE c.ativo = TRUE
        GROUP BY c.tenant_id, c.ativo, c.hunter_pausado, c.producao_pausada, c.segmentos, c.cidades
        ORDER BY c.tenant_id
    """)).fetchall()

    if not rows:
        print("    Nenhum tenant encontrado com configuração ativa.")
        return []

    tenants = []
    print(f"\n    {'ID':<6} {'Ativo':<7} {'Hunter':<8} {'Produção':<10} {'Raw':<6} {'Qual':<6} {'Aprov':<6} Status")
    print("    " + "-"*70)

    for r in rows:
        tenant_id = r[0]
        ativo = r[1]
        hunter_pausado = r[2]
        prod_pausada = r[3]
        segmentos = json.loads(r[4] or "[]") if isinstance(r[4], str) else r[4]
        cidades = json.loads(r[5] or "[]") if isinstance(r[5], str) else r[5]
        raw = r[6] or 0
        qualifying = r[7] or 0
        approved = r[8] or 0
        discarded = r[9] or 0

        # Determina status
        if not ativo:
            status = "⚠️ DESLIGADO"
        elif hunter_pausado:
            status = "⚠️ HUNTER PAUSADO"
        elif prod_pausada:
            status = "⚠️ PRODUÇÃO PAUSADA"
        elif raw == 0 and qualifying == 0 and approved == 0:
            status = "🔴 SEM LEADS"
        elif qualifying > 0:
            status = "🟡 QUALIFICANDO"
        elif raw > 0 and qualifying == 0:
            status = "🔴 HUNTER→CAIO TRAVADO"
        elif approved > 0:
            status = "🟢 APROVADOS"
        else:
            status = "🔵 AGUARDANDO"

        print(f"    {tenant_id:<6} {'✓' if ativo else '✗':<7} {'✓' if not hunter_pausado else '✗':<8} {'✓' if not prod_pausada else '✗':<10} {raw:<6} {qualifying:<6} {approved:<6} {status}")

        tenants.append({
            "tenant_id": tenant_id,
            "ativo": ativo,
            "hunter_pausado": hunter_pausado,
            "prod_pausada": prod_pausada,
            "segmentos": segmentos,
            "cidades": cidades,
            "raw": raw,
            "qualifying": qualifying,
            "approved": approved,
            "status": status,
        })

    return tenants


def check_recent_events(db, hours=24):
    """Verifica eventos recentes."""
    print(f"\n[5] Eventos nas últimas {hours}h...")

    rows = db.execute(text("""
        SELECT
            source,
            level,
            COUNT(*) as total
        FROM lead_supply_events
        WHERE criado_em > NOW() - INTERVAL ':hours hours'
        GROUP BY source, level
        ORDER BY total DESC
    """), {"hours": hours}).fetchall()

    if not rows:
        print("    Nenhum evento recente.")
        return

    print(f"\n    {'Source':<15} {'Level':<10} {'Total':<8}")
    print("    " + "-"*40)
    for r in rows:
        print(f"    {r[0]:<15} {r[1]:<10} {r[2]:<8}")


def fix_stuck_tenants(db, tenants):
    """Tenta corrigir tenants travados."""
    print("\n[6] Tentando corrigir tenants travados...")

    from backend.core import job_queue

    stuck_tenants = [t for t in tenants if "TRAVADO" in t["status"] or "SEM LEADS" in t["status"]]
    paused_hunter = [t for t in tenants if t["hunter_pausado"] and t["ativo"]]

    if not stuck_tenants and not paused_hunter:
        print("    ✓ Nenhum tenant para corrigir.")
        return

    if stuck_tenants:
        print(f"\n    Tentando corrigir {len(stuck_tenants)} tenant(s) travado(s):")
        for t in stuck_tenants:
            print(f"    - Tenant {t['tenant_id']}: {t['status']}")
            try:
                # Re-enqueue hunter job
                job_id = job_queue.enqueue_job(
                    db=db,
                    tipo="lead_supply_hunter",
                    tenant_id=t["tenant_id"],
                    payload={"reason": "diagnose_recovery", "force": True},
                )
                print(f"      ✓ Hunter job enfileirado (ID: {job_id})")
            except Exception as e:
                print(f"      ✗ Falha: {e}")

    if paused_hunter:
        print(f"\n    Hunters pausados ({len(paused_hunter)}):")
        for t in paused_hunter:
            print(f"    - Tenant {t['tenant_id']}: segments={t['segmentos']}, cities={t['cidades']}")


def force_requeue_all(db, tenants):
    """Força re-enqueue para todos tenants ativos."""
    print("\n[7] Re-enfileirando jobs para todos tenants ativos...")

    from backend.core import job_queue

    active = [t for t in tenants if t["ativo"] and not t["hunter_pausado"] and not t["prod_pausada"]]

    if not active:
        print("    Nenhum tenant ativo para re-enfileirar.")
        return

    print(f"    Re-enfileirando para {len(active)} tenant(s)...")

    for t in active:
        try:
            # Hunter job
            hunter_id = job_queue.enqueue_job(
                db=db,
                tipo="lead_supply_hunter",
                tenant_id=t["tenant_id"],
                payload={"reason": "diagnose_full_reset", "force": True},
            )

            # Caio jobs para leads raw
            raw_leads = db.execute(text("""
                SELECT id FROM lead_inventory
                WHERE tenant_id = :tid AND status = 'raw'
                LIMIT 10
            """), {"tid": t["tenant_id"]}).fetchall()

            caio_count = 0
            for lead in raw_leads:
                job_queue.enqueue_job(
                    db=db,
                    tipo="lead_supply_caio",
                    tenant_id=t["tenant_id"],
                    payload={"inventory_id": lead[0]},
                )
                caio_count += 1

            print(f"    Tenant {t['tenant_id']}: Hunter={hunter_id}, Caio jobs={caio_count}")

        except Exception as e:
            print(f"    Tenant {t['tenant_id']}: ✗ {e}")


def main():
    banner("Lead Supply - Diagnóstico e Recuperação")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    fix_mode = "--fix" in sys.argv or "-f" in sys.argv
    force_mode = "--force" in sys.argv

    # Checks
    gosom_ok, playwright_ok = check_scrapers()

    db = SessionLocal()
    try:
        tenants = check_tenants_status(db)
        check_recent_events(db, hours=24)

        # Count problems
        problemas = [t for t in tenants if "⚠️" in t["status"] or "🔴" in t["status"]]
        if problemas:
            print(f"\n{'='*60}")
            print(f" ⚠️  {len(problemas)} tenant(s) com problemas encontrados!")
            print('='*60)

        # Fix if requested
        if fix_mode:
            print("\n[MODO FIX ATIVADO]")
            fix_stuck_tenants(db, tenants)

        if force_mode:
            print("\n[MODO FORCE ATIVADO - Re-enfileirando tudo]")
            force_requeue_all(db, tenants)

        # Summary
        banner("Resumo")
        print(f"  GOSOM:         {'✓ Online' if gosom_ok else '✗ Offline'}")
        print(f"  Playwright:     {'✓ Disponível' if playwright_ok else '✗ Indisponível'}")
        print(f"  Total Tenants:  {len(tenants)}")

        if gosom_ok:
            print("\n  ✓ GOSOM está online. Hunter deve funcionar.")
        else:
            print("\n  ⚠️  GOSOM offline - usando Playwright (mais lento)")
            if not playwright_ok:
                print("  ✗ AVISO: Nenhum scraper disponível!")

        if problemas and not fix_mode and not force_mode:
            print(f"\n  Para corrigir: python scripts/lead_supply_diagnose.py --fix")
            print(f"  Para forçar:  python scripts/lead_supply_diagnose.py --force")

    finally:
        db.close()


if __name__ == "__main__":
    main()
