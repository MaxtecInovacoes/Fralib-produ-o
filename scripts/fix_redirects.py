#!/usr/bin/env python3
"""Fix dashboard redirects to admin in HTML files."""
import re
import sys

files = [
    'frontend/login.html',
    'frontend/superadmin.html',
    'frontend/onboarding.html',
    'frontend/planos.html',
]

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        new_content = re.sub(r"location\.href='/dashboard'", "location.href='/admin.html'", content)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(new_content)
        count = content.count("dashboard")
        print(f"{f}: {count} referencias corrigidas")
    except Exception as e:
        print(f"{f}: ERRO {e}")
