import bcrypt
import psycopg2

pw = bcrypt.hashpw(b'test123', bcrypt.gensalt()).decode()
print('hash:', pw)

conn = psycopg2.connect(host='postgres', database='fralib_db', user='fralib_user', password='fralib_dev_password')
c = conn.cursor()
c.execute("UPDATE users SET password_hash = %s WHERE id = 1", (pw,))
conn.commit()
print('updated:', c.rowcount)
c.execute('SELECT id, email, password_hash FROM users WHERE id = 1')
row = c.fetchone()
print('user:', row[0], row[1], 'hash_set=', row[2] is not None)
conn.close()
