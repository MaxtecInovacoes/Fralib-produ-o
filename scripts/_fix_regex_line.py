#!/usr/bin/env python3
"""Fix the malformed regex line 1655 in vite_react_renderer.py"""
import re

filepath = '/root/fralib/backend/services/vite_react_renderer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 1655 (0-indexed: 1654)
target = 1654
print(f'Line {target+1} before: {repr(lines[target])}')

# The correct regex pattern
correct = '                    r"import\\s*\\{([^}]*)\\}\\s*from\\s*[\\\'\\"]react[\\\'\\"]\\s*;?",\n'
lines[target] = correct

print(f'Line {target+1} after: {repr(lines[target])}')

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Written!')

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    verify_lines = f.readlines()
print(f'Verify line {target+1}: {repr(verify_lines[target])}')
