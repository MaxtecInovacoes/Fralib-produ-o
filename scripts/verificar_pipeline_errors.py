#!/usr/bin/env python3
"""
Script para verificar erros da pipeline de um tenant.
Uso: python scripts/verificar_pipeline_errors.py [tenant_id]

Exemplo: python scripts/verificar_pipeline_errors.py 2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Configuração do banco
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/fralib")

def verificar_falhas_tenant(tenant_id: int):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    print(f"\n{'='*60}")
    print(f"  VERIFICANDO PIPELINE DO TENANT {tenant_id}")
    print(f"{'='*60}\n")

    # 1. Jobs em execução
    print("📋 JOBS ATIVOS:")
    print("-" * 40)
    jobs = db.execute(text("""
        SELECT id, tipo, status, last_phase, last_error, criado_em
        FROM jobs
        WHERE tenant_id = :tid AND status IN ('running', 'pending', 'failed_retriable')
        ORDER BY criado_em DESC
        LIMIT 10
    """), {"tid": tenant_id}).fetchall()

    if jobs:
        for job in jobs:
            print(f"  ID: {job[0]}")
            print(f"  Tipo: {job[1]}")
            print(f"  Status: {job[2]}")
            print(f"  Fase: {job[3]}")
            print(f"  Erro: {str(job[4])[:200] if job[4] else 'Nenhum'}")
            print(f"  Criado: {job[5]}")
            print()
    else:
        print("  Nenhum job ativo\n")

    # 2. Falhas não resolvidas
    print("❌ FALHAS NÃO RESOLVIDAS:")
    print("-" * 40)
    falhas = db.execute(text("""
        SELECT id, lead_id, lead_nome, fase, mensagem_amigavel,
               erro_tecnico, tentativas_automaticas, criado_em
        FROM pipeline_failures
        WHERE tenant_id = :tid AND resolvido = FALSE
        ORDER BY criado_em DESC
        LIMIT 20
    """), {"tid": tenant_id}).fetchall()

    if falhas:
        for f in falhas:
            print(f"  ID: {f[0]}")
            print(f"  Lead: {f[2] or f[1]}")
            print(f"  Fase: {f[3]}")
            print(f"  Mensagem: {f[4]}")
            print(f"  Tentativas: {f[6]}")
            print(f"  Erro Técnico: {str(f[5])[:300] if f[5] else 'Nenhum'}")
            print(f"  Criado: {f[7]}")
            print()
    else:
        print("  Nenhuma falha não resolvida\n")

    # 3. Leads com problemas
    print("👥 LEADS COM PROBLEMAS:")
    print("-" * 40)
    leads = db.execute(text("""
        SELECT id, nome, cidade, status, score, tier, last_error
        FROM leads
        WHERE user_id = :tid AND status IN ('erro', 'failed', 'capturado')
        ORDER BY created_at DESC
        LIMIT 10
    """), {"tid": tenant_id}).fetchall()

    if leads:
        for l in leads:
            print(f"  ID: {l[0]}")
            print(f"  Nome: {l[1]}")
            print(f"  Status: {l[3]}")
            print(f"  Score: {l[4]}")
            print(f"  Erro: {str(l[6])[:200] if l[6] else 'Nenhum'}")
            print()
    else:
        print("  Nenhum lead com problema\n")

    # 4. Estatísticas
    print("📊 ESTATÍSTICAS:")
    print("-" * 40)

    total_falhas = db.execute(text("""
        SELECT COUNT(*) FROM pipeline_failures
        WHERE tenant_id = :tid AND resolvido = FALSE
    """), {"tid": tenant_id}).scalar()

    total_leads = db.execute(text("""
        SELECT COUNT(*) FROM leads WHERE user_id = :tid
    """), {"tid": tenant_id}).scalar()

    leads_qualificados = db.execute(text("""
        SELECT COUNT(*) FROM leads WHERE user_id = :tid AND status = 'aprovado'
    """), {"tid": tenant_id}).scalar()

    print(f"  Total de Leads: {total_leads}")
    print(f"  Leads Qualificados: {leads_qualificados}")
    print(f"  Falhas Não Resolvidas: {total_falhas}")

    db.close()

    return {
        "total_leads": total_leads,
        "leads_qualificados": leads_qualificados,
        "falhas": len(falhas),
        "jobs_ativos": len(jobs)
    }


if __name__ == "__main__":
    tenant_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    resultado = verificar_falhas_tenant(tenant_id)

    print(f"\n{'='*60}")
    print("  RESUMO")
    print(f"{'='*60}")
    print(f"  Leads: {resultado['total_leads']}")
    print(f"  Qualificados: {resultado['leads_qualificados']}")
    print(f"  Falhas: {resultado['falhas']}")
    print(f"  Jobs Ativos: {resultado['jobs_ativos']}")
