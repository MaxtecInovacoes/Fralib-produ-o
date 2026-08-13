#!/usr/bin/env python3
"""
build_admin.py — Concatena os partials de admin em admin.html
Uso: python3 /root/fralib/frontend/build_admin.py
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIALS_DIR = ROOT / 'frontend' / 'partials' / 'admin'
OUTPUT_LOCAL = ROOT / 'frontend' / 'admin.html'
OUTPUT_PROD = Path('/var/www/fralib/admin.html')

PARTIALS_ORDER = [
    '_head.html',
    '_sidebar.html',
    '_main-header.html',
    '_view-overview.html',
    '_view-crm.html',
    '_view-uti.html',
    '_view-ciclos.html',
    '_view-config.html',
    '_view-perfil.html',
    '_modals.html',
    '_scripts.html',
]

def build():
    chunks = []
    for name in PARTIALS_ORDER:
        path = PARTIALS_DIR / name
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        chunks.append(content)
        print(f'  + {name} ({len(content.splitlines())} linhas)')

    full = ''.join(chunks)
    total_lines = len(full.splitlines())

    destinations = [OUTPUT_LOCAL]
    if os.name != 'nt':
        destinations.append(OUTPUT_PROD)

    for dest in destinations:
        os.makedirs(dest.parent, exist_ok=True)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(full)
        print(f'Salvo em: {dest}')

    print(f'Total de linhas geradas: {total_lines}')
    return total_lines

if __name__ == '__main__':
    print('Iniciando build de admin.html...')
    build()
    print('Build concluido.')
