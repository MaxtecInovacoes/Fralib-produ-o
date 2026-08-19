p = r'C:\fralib\agent_remote.py'
with open(p, encoding='utf-8') as f:
    lines = f.readlines()

# Insert DEPOIMENTOS block after line 730 (index 729, 0-indexed), before "    )"
insert_at = 730  # after line 730, before line 731
new_block = [
    '        "DEPOIMENTOS (OBRIGAT\u00d3RIO):\\n"\n',
    '        "- Use APENAS os reviews reais da lista `reviews_list` (autor + nota + texto).\\n"\n',
    '        "- N\u00c3O invente depoimentos, N\u00c3O use placeholder como \'Cliente satisfeito\'.\\n"\n',
    '        "- M\u00e1ximo 3 depoimentos, ordenados por nota (maior primeiro).\\n"\n',
    '        "- Se `reviews_list` estiver vazia: renderizar bloco \'Compromissos e Diferenciais\' "\n',
    '        "com 3 bullets, NUNCA depoimentos inventados.\\n"\n',
]
lines = lines[:insert_at] + new_block + lines[insert_at:]
with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f'Inserted {len(new_block)} lines at position {insert_at}. Total: {len(lines)}')
