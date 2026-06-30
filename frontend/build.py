#!/usr/bin/env python3
"""
Build script: concatena partials e gera os HTMLs finais.
Uso: python3 build.py
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

def build(name, partials_order):
    parts_dir = os.path.join(BASE, 'partials', name)
    output_path = os.path.join(BASE, f'{name}.html')
    if not os.path.isdir(parts_dir):
        print(f'SKIP {name}.html: partials ausentes em {parts_dir}')
        return False

    chunks = []
    for partial in partials_order:
        path = os.path.join(parts_dir, partial)
        if not os.path.exists(path):
            print(f'SKIP {name}.html: partial ausente {path}')
            return False
        with open(path, 'r', encoding='utf-8') as f:
            chunks.append(f.read())

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(chunks))

    print(f'OK {name}.html gerado ({len(chunks)} blocos)')
    return True

DASHBOARD_ORDER = [
    '_head.html',
    '_sidebar.html',
    '_header.html',
    '_kpi-cards.html',
    '_view-overview.html',
    '_view-crm.html',
    '_view-uti.html',
    '_view-config.html',
    '_view-perfil.html',
    '_modal-lead.html',
    '../shared/_modal-editor-site.html',
    '_scripts.html',
]

LANDING_ORDER = [
    '_head.html',
    '_nav.html',
    '_hero.html',
    '_social-proof.html',
    '_problema.html',
    '_como-funciona.html',
    '_produto.html',
    '_funcionalidades.html',
    '_para-quem.html',
    '_planos.html',
    '_faq.html',
    '_beta-form.html',
    '_footer.html',
    '_scripts.html',
]

if __name__ == '__main__':
    build('dashboard', DASHBOARD_ORDER)
    build('landing', LANDING_ORDER)
    # admin.html possui partials proprios; rode frontend/build_admin.py.
    print('Build completo!')

