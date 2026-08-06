#!/usr/bin/env python3
"""
build_admin.py — Concatena os partials de admin em admin.html
Uso: python3 /root/fralib/frontend/build_admin.py
"""

import os

PARTIALS_DIR = '/opt/fralib/frontend/partials/admin/'
OUTPUT_PROD  = '/var/www/fralib/admin.html'
OUTPUT_LOCAL = '/opt/fralib/frontend/admin.html'

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
        path = os.path.join(PARTIALS_DIR, name)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        chunks.append(content)
        print(f'  + {name} ({len(content.splitlines())} linhas)')

    full = ''.join(chunks)
    total_lines = len(full.splitlines())

    for dest in (OUTPUT_PROD, OUTPUT_LOCAL):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(full)
        print(f'Salvo em: {dest}')

    print(f'Total de linhas geradas: {total_lines}')
    return total_lines

if __name__ == '__main__':
    print('Iniciando build de admin.html...')
    build()
    print('Build concluido.')
