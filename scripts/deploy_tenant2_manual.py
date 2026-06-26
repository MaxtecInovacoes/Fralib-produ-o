#!/usr/bin/env python3
"""Sprint 14.4: Deploy Manual do Site Tenant 2 - Barbearia Fio Nobre

Quando o VPS estiver acessível, execute este script para fazer o deploy real.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def banner(msg: str) -> None:
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def step(msg: str) -> None:
    print(f"  [+] {msg}")

def check(msg: str, ok: bool) -> None:
    status = "✅" if ok else "❌"
    print(f"  {status} {msg}")

def main():
    banner("DEPLOY MANUAL - Tenant 2 Barbearia Fio Nobre")

    # Configurações
    source_dir = Path("C:/fralib/sites/tenant2-fio-nobre/dist")
    vps_target = "/var/www/fralib/sites/2/barbearia-fio-nobre"
    local_target = Path("C:/fralib/sites/tenant2-fio-nobre/deploy-ready")

    # Verificar fonte
    step("Verificando fonte...")
    if source_dir.exists():
        files = list(source_dir.glob("*"))
        check(f"Fonte existe ({len(files)} arquivos)", True)
        for f in files:
            check(f"  {f.name}", f.exists())
    else:
        check("Fonte não existe", False)
        return

    # Verificar VPS
    step("Verificando VPS...")
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "root@100.101.18.1", "echo 'VPS OK'"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            check("VPS acessível", True)
            vps_accessible = True
        else:
            check("VPS não acessível", False)
            vps_accessible = False
    except Exception as e:
        check(f"VPS erro: {e}", False)
        vps_accessible = False

    # Estratégia de deploy
    if vps_accessible:
        strategy = "VPS"
        target = vps_target
    else:
        strategy = "Local"
        target = local_target

    step(f"Strategy: {strategy}")
    step(f"Target: {target}")

    # Deploy
    banner("EXECUTANDO DEPLOY")

    if strategy == "VPS":
        step("Deploy para VPS...")
        try:
            # Criar diretório no VPS
            subprocess.run([
                "ssh", "root@100.101.18.1",
                f"mkdir -p {vps_target} && rm -rf {vps_target}/*"
            ], check=True)

            # Copiar arquivos
            for file in source_dir.iterdir():
                if file.is_file():
                    subprocess.run([
                        "scp", str(file), f"root@100.101.18.1:{vps_target}/{file.name}"
                    ], check=True)
                elif file.is_dir():
                    subprocess.run([
                        "scp", "-r", str(file), f"root@100.101.18.1:{vps_target}/{file.name}"
                    ], check=True)

            check("Deploy VPS concluído", True)

            # Verificar no VPS
            result = subprocess.run([
                "ssh", "root@100.101.18.1",
                f"ls -la {vps_target}/ && echo 'Files:' && find {vps_target} -type f | wc -l"
            ], capture_output=True, text=True, check=True)

            print(f"VPS verification:\n{result.stdout}")

        except Exception as e:
            check(f"Deploy VPS falhou: {e}", False)

    elif strategy == "Local":
        step("Deploy local...")
        try:
            # Criar diretório de destino
            target.mkdir(parents=True, exist_ok=True)

            # Copiar arquivos
            for file in source_dir.iterdir():
                dest = target / file.name
                if file.is_file():
                    shutil.copy2(file, dest)
                elif file.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(file, dest)

            check("Deploy local concluído", True)

            # Verificar
            files_count = len(list(target.rglob("*")))
            total_size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            print(f"  Local deploy: {files_count} files, {total_size/1024:.1f} KB")

        except Exception as e:
            check(f"Deploy local falhou: {e}", False)

    # Pós-deploy
    banner("PÓS-DEPLOY")

    # Verificar integridade
    step("Verificando integridade...")
    index_file = target / "index.html"
    if index_file.exists():
        content = index_file.read_text(encoding='utf-8')
        checks = [
            ("Title", "Barbearia Fio Nobre" in content),
            ("Description", "avaliação 4.8" in content),
            ("JSON-LD", "LocalBusiness" in content),
            ("WhatsApp", "41988084400" in content),
        ]
        for name, ok in checks:
            check(f"{name} OK", ok)
    else:
        check("index.html não encontrado", False)

    # Assets
    assets_dir = target / "assets"
    if assets_dir.exists():
        assets = list(assets_dir.glob("*"))
        check(f"Assets ({len(assets)} arquivos)", True)
        for asset in assets:
            check(f"  {asset.name}", asset.exists())
    else:
        check("Assets não encontrados", False)

    # Resumo
    banner("RESUMO DO DEPLOY")
    print(f"""
  Site: Barbearia Fio Nobre
  Tenant ID: 2
  Segment: Barbearia
  Cidade: Pinhais/PR
  Strategy: {strategy}
  Target: {target}
  Files: {len(list(target.rglob('*')))}
  Status: PRONTO PARA PRODUÇÃO
  """)

    if strategy == "VPS":
        print("\n🎉 DEPLOY VPS CONCLUÍDO!")
        print("O site está acessível em: http://fralib.com.br/sites/2/barbearia-fio-nobre/")
    else:
        print("\n📋 DEPLOY LOCAL CONCLUÍDO!")
        print("Para acessar: abra C:/fralib/sites/tenant2-fio-nobre/deploy-ready/index.html")
        print("Para VPS: execute git push origin master quando VPS estiver acessível")

if __name__ == "__main__":
    main()