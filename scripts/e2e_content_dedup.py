"""Teste FINAL: simula 3x entrega de msg IDENTICA do WhatsApp.

Replicação exata do bug visto em produção:
- Mesmo lead
- Mesmo conteúdo de mensagem
- Chegando em sequência rápida (race do WhatsApp)

O fix deve bloquear as 2 últimas e processar só a 1ª.
"""
import sys
import os
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, "/root/fralib/backend")
sys.path.insert(0, "/root/fralib")

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:fralib2024@localhost:5433/fralib_db")

from sqlalchemy import create_engine, text

# Buscar lead Jaqueline (que tava com bug)
eng = create_engine(os.environ["DATABASE_URL"])
lead_id = None
user_id = None
telefone = None
with eng.connect() as c:
    r = c.execute(text("""
        SELECT id, user_id, telefone FROM leads
        WHERE nome LIKE '%Jaqueline Vieira%' LIMIT 1
    """))
    row = r.fetchone()
    if row:
        lead_id, user_id, telefone = row[0], row[1], row[2]
    else:
        # pegar qualquer lead ativo
        r = c.execute(text("SELECT id, user_id, telefone FROM leads WHERE id IS NOT NULL LIMIT 1"))
        row = r.fetchone()
        lead_id, user_id, telefone = row[0], row[1], row[2]

print(f"Lead: {lead_id[:16]}... user_id={user_id} tel={telefone}")

# Simular conteúdo exato do bug (msg opt-out)
msg_content = "remover"  # Match pattern opt_out
print(f"\n=== Cenario: 3x entregas da mesma msg (simulando race WhatsApp) ===\n")

# Marcar timestamp antes
now_before = datetime.now(timezone.utc).isoformat()

# Contar quantas entradas serao salvas
results = []
def simulate_delivery(idx):
    """Simula o que o _processar_mensagem faz: verificar dedup e salvar."""
    with eng.connect() as c:
        # Esta e a logica EXATA do fix novo (whatsapp_listener.py)
        try:
            r = c.execute(text("""
                SELECT criado_em FROM interacoes
                WHERE lead_id = :lid AND user_id = :uid
                  AND direcao = 'entrada'
                  AND mensagem = :msg
                  AND criado_em > to_char(NOW() - CAST('5 seconds' AS INTERVAL), 'YYYY-MM-DD\"T\"HH24:MI:SS')
                LIMIT 1
            """), {"lid": lead_id, "uid": user_id, "msg": msg_content})
            if r.fetchone():
                results.append((idx, "DEDUPED_BY_CONTENT"))
                return
        except Exception:
            pass

        # Salvar
        try:
            c.execute(text("""
                INSERT INTO interacoes (lead_id, mensagem, direcao, criado_em, user_id)
                VALUES (:lid, :msg, 'entrada', :ts, :uid)
            """), {"lid": lead_id, "msg": msg_content, "ts": datetime.now(timezone.utc).isoformat(), "uid": user_id})
            c.commit()
            results.append((idx, "SAVED"))
        except Exception as e:
            results.append((idx, f"ERROR: {e}"))

# Simular 3 entregas SEQUENCIAIS (mesmo conteúdo)
threads = []
for i in range(3):
    t = threading.Thread(target=simulate_delivery, args=(i,))
    threads.append(t)
    t.start()
    time.sleep(0.01)  # 10ms entre cada (simula race do WhatsApp)

for t in threads:
    t.join()

print("Resultados:")
for idx, status in results:
    print(f"  entrega #{idx}: {status}")

saved = sum(1 for _, s in results if s == "SAVED")
deduped = sum(1 for _, s in results if s == "DEDUPED_BY_CONTENT")

print(f"\nTotal salvo: {saved} (esperado: 1)")
print(f"Total deduplicado: {deduped} (esperado: 2)")

if saved == 1 and deduped == 2:
    print("\n  PASSOU: Content dedup pega duplicatas com msg_id diferentes")
else:
    print(f"\n  FALHOU: esperado 1 saved + 2 deduped, teve {saved} saved + {deduped} deduped")

# Cleanup: remover linhas de teste
with eng.connect() as c:
    c.execute(text("""
        DELETE FROM interacoes
        WHERE lead_id = :lid AND user_id = :uid
          AND mensagem = :msg
          AND criado_em > :ts_before
    """), {"lid": lead_id, "uid": user_id, "msg": msg_content, "ts_before": now_before})
    c.commit()
print(f"\nCleanup: removidas linhas de teste")