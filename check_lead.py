import psycopg2
conn = psycopg2.connect(host='postgres', database='fralib_db',
                        user='fralib_user', password='fralib_dev_password')
c = conn.cursor()
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='leads' AND column_name='sdr_stage'")
print('sdr_stage exists:', c.fetchone() is not None)
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='leads' ORDER BY ordinal_position")
print([r[0] for r in c.fetchall()])
conn.close()
