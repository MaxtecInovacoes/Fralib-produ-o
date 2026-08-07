path = '/opt/fralib/backend/services/credits_manager.py'
with open(path, 'r') as f:
    content = f.read()

# Fix 1: Guard token_transactions INSERT with table existence check
old_insert = 'INSERT INTO token_transactions'
new_insert = """# Guarda: tabela token_transactions pode nao existir ainda
        try:
            db.execute(text("SELECT to_regclass('public.token_transactions')"))
            has_table = db.fetchone()[0] is not None
        except Exception:
            has_table = False
        if has_table:
            INSERT INTO token_transactions"""

if old_insert in content:
    content = content.replace(old_insert, new_insert, 1)
    print('FIXED: token_transactions table guard added')
else:
    print('ERROR: INSERT INTO token_transactions not found')

with open(path, 'w') as f:
    f.write(content)
