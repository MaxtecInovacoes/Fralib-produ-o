"""Make budget bypass unconditional in llm_direct.py."""
import sys

p = sys.argv[1]
with open(p, encoding='utf-8') as f:
    src = f.read()

# Replace conditional bypass with unconditional
old_block = (
    '            # FASE 1 BYPASS: skip budget check when flag is set\n'
    '            if os.environ.get("DISABLE_DAILY_BUDGET", "").lower() == "true":\n'
    '                print("[LLM] Budget check BYPASSED (DISABLE_DAILY_BUDGET=true)")'
)
new_block = (
    '            # FASE 1 BYPASS_UNCONDITIONAL: budget check disabled permanently (FRA-LIB 2026-08-17)\n'
    '            print("[LLM] Budget check BYPASSED (FRA-LIB 2026-08-17 unconditional)")'
)

if old_block in src:
    src = src.replace(old_block, new_block)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(src)
    print('[OK] Bypass made unconditional')
else:
    # try alternate match
    idx = src.find('FASE 1 BYPASS')
    if idx >= 0:
        print(f'[DEBUG] Found FASE 1 BYPASS at offset {idx}')
        print(repr(src[idx:idx+300]))
    else:
        print('[FAIL] No FASE 1 BYPASS found')
    sys.exit(1)
