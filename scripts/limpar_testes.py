"""
Script para excluir usuarios de teste do FraLib
Critério: emails contendo 'test', 'demo', 'fake', 'example', 'admin@', 'codex', '@fralib', 'suporte@', 'jesus'
NAO remove o superadmin!
"""

import sys
import os

# Adicionar paths para os imports funcionarem
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')
sys.path.insert(0, '/root/fralib/backend/core')

from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')

from database import engine
from sqlalchemy import text


def listar_testes():
    """Lista usuarios de teste (sem excluir)"""
    print("=" * 60)
    print("USUARIOS DE TESTE ENCONTRADOS")
    print("=" * 60)

    with engine.connect() as conn:
        # Query: emails de teste que NAO sao superadmin
        rows = conn.execute(text("""
            SELECT id, email, nome, role, plano, status, criado_em
            FROM users
            WHERE (
                LOWER(email) LIKE '%test%'
                OR LOWER(email) LIKE '%demo%'
                OR LOWER(email) LIKE '%fake%'
                OR LOWER(email) LIKE '%example%'
                OR LOWER(email) LIKE '%admin@%'
                OR LOWER(email) LIKE '%codex%'
                OR LOWER(email) LIKE '%@fralib%'
                OR LOWER(email) LIKE '%suporte@%'
                OR LOWER(email) LIKE '%jesus%'
            )
            AND role != 'superadmin'
            ORDER BY id DESC
        """)).fetchall()

        if not rows:
            print("Nenhum usuario de teste encontrado.")
            return []

        print(f"\nEncontrados: {len(rows)} usuarios de teste\n")
        for r in rows:
            print(f"  #{r[0]:3d} | {r[1]:40s} | nome={str(r[2])[:20]:20s} | {r[3]}")

        return rows


def excluir_testes(dry_run=True):
    """Exclui usuarios de teste (exceto superadmin)"""
    with engine.connect() as conn:
        # Listar IDs
        rows = conn.execute(text("""
            SELECT id FROM users
            WHERE (
                LOWER(email) LIKE '%test%'
                OR LOWER(email) LIKE '%demo%'
                OR LOWER(email) LIKE '%fake%'
                OR LOWER(email) LIKE '%example%'
                OR LOWER(email) LIKE '%admin@%'
                OR LOWER(email) LIKE '%codex%'
                OR LOWER(email) LIKE '%@fralib%'
                OR LOWER(email) LIKE '%suporte@%'
                OR LOWER(email) LIKE '%jesus%'
            )
            AND role != 'superadmin'
        """)).fetchall()

        ids = [r[0] for r in rows]

        if not ids:
            print("\nNenhum teste para excluir.")
            return

        if dry_run:
            print(f"\n[DRY RUN] {len(ids)} usuarios seriam excluidos: {ids}")
            print("\nPara excluir de verdade, rode: python scripts/limpar_testes.py --excluir")
            return

        print(f"\nExcluindo {len(ids)} usuarios...")

        # Excluir dependencias primeiro (para nao dar erro de FK)

        # Leads dos usuarios
        result = conn.execute(text("""
            DELETE FROM leads WHERE user_id IN :ids
        """).bindparams(ids=tuple(ids)))
        print(f"  Leads excluidos: {result.rowcount}")

        # Token transactions
        result = conn.execute(text("""
            DELETE FROM token_transactions WHERE user_id IN :ids
        """).bindparams(ids=tuple(ids)))
        print(f"  Token transactions: {result.rowcount}")

        # LLM usage
        try:
            result = conn.execute(text("""
                DELETE FROM llm_usage WHERE user_id IN :ids
            """).bindparams(ids=tuple(ids)))
            print(f"  LLM usage: {result.rowcount}")
        except Exception as e:
            print(f"  LLM usage: erro {e}")

        # Outros (silencioso, se nao existir a tabela)
        for tabela in ['outreach_events', 'sdr_messages', 'interacoes']:
            try:
                result = conn.execute(text(f"""
                    DELETE FROM {tabela} WHERE user_id IN :ids
                """).bindparams(ids=tuple(ids)))
                print(f"  {tabela}: {result.rowcount}")
            except Exception as e:
                print(f"  {tabela}: skip ({str(e)[:50]})")

        # Users
        result = conn.execute(text("""
            DELETE FROM users WHERE id IN :ids
        """).bindparams(ids=tuple(ids)))
        print(f"\n  Usuarios excluidos: {result.rowcount}")

        conn.commit()
        print("\nConcluido!")


if __name__ == '__main__':
    print("\nFralib - Limpeza de Usuarios de Teste\n")

    # Sempre listar primeiro
    testes = listar_testes()

    # Se passou --excluir como argumento, excluir
    if '--excluir' in sys.argv:
        print("\n" + "=" * 60)
        print("ATENCAO: Modo de exclusao REAL!")
        print("=" * 60)
        resp = input("\nDigite 'EXCLUIR' para confirmar: ")
        if resp.strip() == 'EXCLUIR':
            excluir_testes(dry_run=False)
        else:
            print("\nCancelado.")
    else:
        print("\n" + "=" * 60)
        print("MODO: Apenas listagem")
        print("=" * 60)
        print("\nPara EXCLUIR de verdade, rode:")
        print("  cd /root/fralib && python scripts/limpar_testes.py --excluir")