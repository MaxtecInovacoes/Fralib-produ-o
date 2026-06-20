#!/usr/bin/env python3
"""
build_admin.py — Concatena os partials de admin em admin.html
Uso: python3 frontend/build_admin.py
"""

import os

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(FRONTEND_DIR)
PARTIALS_DIR = os.path.join(FRONTEND_DIR, 'partials', 'admin')
OUTPUT_LOCAL = os.path.join(FRONTEND_DIR, 'admin.html')

PARTIALS_ORDER = [
    '_head.html',
    '_sidebar.html',
    '_main-header.html',
    '_view-overview.html',
    '_view-crm.html',
    '_view-uti.html',
    '_view-config.html',
    '_view-perfil.html',
    '_modals.html',
    '../shared/_modal-editor-site.html',
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

    with open(OUTPUT_LOCAL, 'w', encoding='utf-8') as f:
        f.write(full)
    print(f'Salvo em: {OUTPUT_LOCAL}')

    print(f'Total de linhas geradas: {total_lines}')
    return total_lines

if __name__ == '__main__':
    print('Iniciando build de admin.html...')
    build()
    print('Build concluido.')
