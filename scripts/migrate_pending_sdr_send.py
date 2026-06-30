#!/usr/bin/env python3
"""
Migração: Corrige leads com sdr_stage='pending_sdr_send' -> 'pendente_wpp'
=========================================================================
Executa a correção do bug SDR stage mismatch.

Uso:
    python scripts/migrate_pending_sdr_send.py [--dry-run] [--tenant <id>]

Args:
    --dry-run   Apenas mostra o que seria feito, sem executar
    --tenant    Corrige apenas um tenant específico
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=False)

from backend.core.database import SessionLocal
from sqlalchemy import text


def banner(msg):
    print(f"\n{'='*60}")
    print(f" {msg}")
    print('='*60)


def count_leads_by_stage(db, tenant_id=None):
    """Conta leads por estágio SDR."""
    query = """
        SELECT
            sdr_stage,
            COUNT(*) as total
        FROM leads
        WHERE status = 'concluido'
    """
    params = {}
    if tenant_id:
        query += " AND user_id = :tid"
        params['tid'] = tenant_id
    query += " GROUP BY sdr_stage ORDER BY sdr_stage"

    return db.execute(text(query), params).fetchall()


def migrate_leads(db, dry_run=True, tenant_id=None):
    """Migra leads de pending_sdr_send para pendente_wpp."""

    # Query para leads a migrar
    query = """
        SELECT id, nome, user_id, processado_em
        FROM leads
        WHERE status = 'concluido'
          AND sdr_stage = 'pending_sdr_send'
    """
    params = {}
    if tenant_id:
        query += " AND user_id = :tid"
        params['tid'] = tenant_id
    query += " ORDER BY processado_em"

    leads = db.execute(text(query), params).fetchall()

    if not leads:
        print("    Nenhum lead para migrar.")
        return 0

    print(f"    Encontrados {len(leads)} leads para migrar:")
    for lead in leads[:20]:  # Mostra os primeiros 20
        print(f"      ID:{lead[0]} | {lead[1][:30]} | Tenant:{lead[2]}")
    if len(leads) > 20:
        print(f"      ... e mais {len(leads) - 20} leads")

    if dry_run:
        print("\n    [DRY-RUN] Nenhuma alteração foi feita.")
        return len(leads)

    # Executar migração
    update_query = """
        UPDATE leads
        SET sdr_stage = 'pendente_wpp',
            atualizado_em = NOW()::text
        WHERE status = 'concluido'
          AND sdr_stage = 'pending_sdr_send'
    """
    if tenant_id:
        update_query += " AND user_id = :tid"

    result = db.execute(text(update_query), params)
    db.commit()

    print(f"\n    ✓ {result.rowcount} leads migrados com sucesso!")
    return result.rowcount


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migração pending_sdr_send -> pendente_wpp")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria feito")
    parser.add_argument("--tenant", type=int, help="ID do tenant específico")
    args = parser.parse_args()

    dry_run = args.dry_run
    tenant_id = args.tenant

    banner("Migração SDR Stage Fix")

    if dry_run:
        print("  [MODO DRY-RUN - Nenhuma alteração será feita]")
    print()

    db = SessionLocal()
    try:
        # Mostrar estado atual
        print("ESTADO ATUAL DOS LEADS:")
        stages = count_leads_by_stage(db, tenant_id)
        for stage, total in stages:
            marker = " <<<" if stage == "pending_sdr_send" else ""
            print(f"  {stage or '(null)':<25} = {total}{marker}")

        # Contar leads pendentes_wpp
        pendente_wpp_count = sum(t for s, t in stages if s == "pendente_wpp")
        pending_sdr_count = sum(t for s, t in stages if s == "pending_sdr_send")

        print(f"\n  Total concluídos: {sum(t for _, t in stages)}")
        print(f"  Pendente WPP: {pendente_wpp_count}")
        print(f"  Pending SDR Send (BUG): {pending_sdr_count}")

        if pending_sdr_count == 0:
            print("\n  ✓ Nenhum lead pendente de correção!")
            return

        print()

        # Executar migração
        migrated = migrate_leads(db, dry_run=dry_run, tenant_id=tenant_id)

        if not dry_run and migrated > 0:
            print("\nESTADO APÓS MIGRAÇÃO:")
            stages = count_leads_by_stage(db, tenant_id)
            for stage, total in stages:
                print(f"  {stage or '(null)':<25} = {total}")

    finally:
        db.close()

    if dry_run:
        print("\n" + "="*60)
        print(" Para executar a migração, rode sem --dry-run")
        print("="*60)


if __name__ == "__main__":
    main()
