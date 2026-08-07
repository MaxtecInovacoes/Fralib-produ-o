import psycopg2, bcrypt

conn = psycopg2.connect(host='postgres', database='fralib_db', user='fralib_user', password='fralib_dev_password')
c = conn.cursor()

c.execute('SELECT password_hash FROM users WHERE id = 1')
stored = c.fetchone()[0]
print('Stored hash:', stored)
if stored:
    print('Verify test123:', bcrypt.checkpw(b'test123', stored.encode()))

c.execute('SELECT id, email, status, email_confirmado FROM users WHERE id = 1')
row = c.fetchone()
print('User:', row)

conn.close()
