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

    # Backup do original antes de sobrescrever
    backup_path = output_path + '.backup-modular-' + str(int(__import__('time').time()))
    if os.path.exists(output_path):
        import shutil
        shutil.copy2(output_path, backup_path)
        print(f'  Backup: {backup_path}')

    chunks = []
    for partial in partials_order:
        path = os.path.join(parts_dir, partial)
        with open(path, 'r', encoding='utf-8') as f:
            chunks.append(f.read())

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(chunks))

    print(f'OK {name}.html gerado ({len(chunks)} blocos)')

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


ADMIN_ORDER = [
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
    '_scripts.html',
]

if __name__ == '__main__':
    build('dashboard', DASHBOARD_ORDER)
    # build('landing', LANDING_ORDER)  # DESABILITADO — landing v2 gerenciada manualmente
    # admin.html editado diretamente — NAO rebuildar via partials
    # build('admin', ADMIN_ORDER)
    print('Build completo!')

    import shutil, os
    deploy_dir = '/var/www/fralib'
    for fname in ['dashboard.html']:  # landing.html gerenciada manualmente
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(deploy_dir, fname))
            print(f'  Deploy: {fname} -> {deploy_dir}')

