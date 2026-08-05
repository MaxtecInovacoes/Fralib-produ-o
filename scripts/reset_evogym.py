"""Reset do lead Evogym para teste"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "/root/fralib/backend")
from dotenv import load_dotenv
load_dotenv("/root/fralib/.env")

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
lead_id = "fcfb6f64-9805-48fc-92c8-d72563217d38"

with engine.connect() as c:
    c.execute(text("UPDATE leads SET sdr_stage = 'pendente_wpp', atualizado_em = NOW()::text WHERE id = :lid"), {"lid": lead_id})
    c.execute(text("DELETE FROM interacoes WHERE lead_id = :lid"), {"lid": lead_id})
    c.commit()

# Limpar memória
memory_dir = Path("/root/fralib/memory/u2")
if memory_dir.exists():
    for f in memory_dir.glob("franz_lead_*.json"):
        f.unlink()
    for f in memory_dir.glob("franz_lead_*.json"):
        f.unlink()
    print(f"OK: memórias em {memory_dir} removidas")

print("OK: lead resetado")
