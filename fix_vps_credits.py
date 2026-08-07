#!/usr/bin/env python3
"""Fix credits_manager.py on VPS — guard token_transactions INSERT"""
path = '/opt/fralib/backend/services/credits_manager.py'
with open(path, 'r') as f:
    content = f.read()

# Find and replace the corrupted block
old_block = """    try:
        db.execute(text("""
            # Guarda: tabela token_transactions pode nao existir ainda
        try:
            db.execute(text("SELECT to_regclass('public.token_transactions')"))
            has_table = db.fetchone()[0] is not None
        except Exception:
            has_table = False
        if has_table:
            INSERT INTO token_transactions (user_id, tipo, tokens_consumidos, custo_usd, descricao)
            VALUES (:uid, :tipo, :tokens, :custo, :desc)
        """), {
            "uid": user_id, "tipo": tipo,
            "tokens": tokens_consumidos, "custo": custo_usd, "desc": descricao
        })
        db.commit()
    except Exception as e:
        print(f"[Credits] Erro ao registrar transacao: {e}")"""

new_block = """    # Guarda: tabela token_transactions pode nao existir ainda
    try:
        db.execute(text("SELECT to_regclass('public.token_transactions')"))
        has_table = db.fetchone()[0] is not None
    except Exception:
        has_table = False
    if not has_table:
        return
    try:
        db.execute(text("""
            INSERT INTO token_transactions (user_id, tipo, tokens_consumidos, custo_usd, descricao)
            VALUES (:uid, :tipo, :tokens, :custo, :desc)
        """), {
            "uid": user_id, "tipo": tipo,
            "tokens": tokens_consumidos, "custo": custo_usd, "desc": descricao
        })
        db.commit()
    except Exception as e:
        print(f"[Credits] Erro ao registrar transacao: {e}")"""

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with open(path, 'w') as f:
        f.write(content)
    print('FIXED: _registrar_transacao on VPS')
else:
    print('ERROR: old block not found')
    # Try to find what's there
    import re
    match = re.search(r'def _registrar_transacao.*?(?=\ndef |\nclass |\Z)', content, re.DOTALL)
    if match:
        print('Current function:')
        print(match.group(0)[:500])
