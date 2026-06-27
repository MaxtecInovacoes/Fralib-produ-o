import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
eng = create_engine(os.environ["DATABASE_URL"])
with eng.connect() as c:
    print("Colunas da tabela leads:")
    for row in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='leads' ORDER BY ordinal_position")):
        print(f"  {row[0]}")