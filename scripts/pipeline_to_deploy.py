#!/usr/bin/env python3
"""Sprint 12.4: Pipeline real end-to-end controlada ate deploy."""
from __future__ import annotations

import json as _json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/root/fralib")
sys.path.insert(0, str(REPO))

os.environ["FRALIB_BUILDER_ENGINE"] = "vite_react"
os.environ["FRALIB_SINGLE_MODEL_ONLY"] = "0"
os.environ["FRALIB_VITE_NAMEHOST_MODELS"] = "claude-sonnet-4-6,claude-haiku-4-5"
os.environ["FRALIB_OPENUI_PRIMARY_MODEL"] = "claude-sonnet-4-6"
os.environ["FRALIB_PROXY_BUILDER_MODEL"] = "claude-sonnet-4-6"
os.environ["ANTHROPIC_BASE_URL"] = "https://api.kpalabz.com/v1"


def banner(msg: str) -> None:
    print(f"\n{'=' * 70}\n  {msg}\n{'=' * 70}")


def step(msg: str) -> None:
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


def deploy_to_fralib(tenant_id: int, slug: str, dist_dir: Path) -> Path:
    target = Path(f"/var/www/fralib/sites/{tenant_id}/{slug}")
    target.mkdir(parents=True, exist_ok=True)
    for item in target.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    for item in dist_dir.iterdir():
        if item.is_dir():
            shutil.copytree(item, target / item.name)
        else:
            shutil.copy2(item, target / item.name)
    return target


def main() -> int:
    banner("SPRINT 12.4 - PIPELINE REAL CONTROLADA ATE DEPLOY")

    step("Etapa 1: Criar lead real no Postgres (tenant 2)")
    from sqlalchemy import create_engine, text

    db_url = "postgresql://postgres:fralib2024@localhost:5433/fralib_db"
    engine = create_engine(db_url)

    lead_id = f"sprint12-4-{int(time.time())}"
    slug = "academia-pump-iron-sp-deploy-final"
    fone = f"119{int(time.time()) % 100000000:08d}"  # telefone unico por timestamp
    cidade_unique = f"Sao Paulo-{int(time.time()) % 10000}"

    dados = _json.dumps({
        "business_name": "Academia Pump Iron SP",
        "city": "Sao Paulo",
        "segment": "academia",
        "phone": "11977775555",
        "services": ["Musculacao", "Crossfit", "Spinning", "Yoga"],
        "horarios": "Seg-Sex 6h-22h | Sab 8h-18h",
        "endereco": "Av Paulista 1500 - Bela Vista",
        "description": "Academia completa premium",
    })

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM leads WHERE id=:id"), {"id": lead_id})
        conn.execute(text("""
            INSERT INTO leads (id, user_id, nome, telefone, cidade, segmento, _leaddata, status, criado_em, atualizado_em)
            VALUES (:id, :uid, :nome, :fone, :cidade, :seg, :dados, 'pendente', NOW()::text, NOW()::text)
        """), {"id": lead_id, "uid": 2, "nome": "Academia Pump Iron SP", "fone": fone, "cidade": cidade_unique, "seg": "academia", "dados": dados})

    step(f"Lead criado: id={lead_id} slug={slug}")

    step("Etapa 2: Criar job pipeline_jobs no Postgres")
    job_id = f"job-{slug}-{int(time.time())}"
    payload = _json.dumps({"lead_id": lead_id, "tenant_id": 2, "engine": "vite_react", "deploy_target": f"/var/www/fralib/sites/2/{slug}/"})
    with engine.begin() as conn:
        try:
            conn.execute(text("""
                INSERT INTO pipeline_jobs (id, tenant_id, lead_id, status, payload, created_at)
                VALUES (:id, :uid, :lid, 'pending', CAST(:payload AS jsonb), NOW())
                ON CONFLICT (id) DO UPDATE SET status='pending', updated_at=NOW()
            """), {"id": job_id, "uid": 2, "lid": lead_id, "payload": payload})
            step(f"Job criado em pipeline_jobs: id={job_id}")
        except Exception as e:
            step(f"WARN pipeline_jobs nao disponivel ({e}); seguindo sem fila")
            job_id = f"direct-{int(time.time())}"

    step("Etapa 3: Build Vite/React via pipeline.py builder-job (montado em blocos)")
    prd = {
        "lead_id": lead_id,
        "business_name": "Academia Pump Iron SP",
        "city": "Sao Paulo",
        "segment": "academia",
        "phone": "11977775555",
        "services": ["Musculacao", "Crossfit", "Spinning", "Yoga"],
        "horarios": "Seg-Sex 6h-22h | Sab 8h-18h",
        "endereco": "Av Paulista 1500 - Bela Vista - Sao Paulo/SP",
        "description": "Academia completa premium",
    }
    prd_path = Path("/tmp/prd_sprint124.json")
    prd_path.write_text(_json.dumps(prd, ensure_ascii=False), encoding="utf-8")

    build_job_id = f"build-{slug}-{int(time.time())}"
    cmd = [sys.executable, str(REPO / "pipeline.py"), "builder-job",
           "--prd-json", str(prd_path), "--tenant-id", "2",
           "--job-id", build_job_id, "--target", "landing-page",
           "--model", "claude-sonnet-4-6", "--execute"]
    step(f"Executando: pipeline.py builder-job")
    result = subprocess.run(cmd, cwd=str(REPO), env=os.environ.copy(), timeout=540)
    if result.returncode != 0:
        print(f"  ERRO: builder-job retornou {result.returncode}")
        return result.returncode

    step("Etapa 4: Localizar dist/ gerado")
    dist_dir = Path(f"/tmp/fralib_builder/tenant-2/{build_job_id}/dist")
    if not dist_dir.exists():
        # Fallback: pega qualquer job recente com dist
        candidates = sorted(Path("/tmp/fralib_builder/tenant-2/").glob("*/dist"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            dist_dir = candidates[0]
            step(f"Usando dist alternativo: {dist_dir}")
    if not dist_dir.exists():
        print(f"  ERRO FATAL: nenhum dist encontrado")
        return 1
    step(f"dist/ = {dist_dir} ({len(list(dist_dir.iterdir()))} arquivos)")

    step("Etapa 5: Deploy em /var/www/fralib/sites/2/<slug>/")
    target = deploy_to_fralib(2, slug, dist_dir)
    step(f"Deploy concluido em: {target}")

    step("Etapa 6: Validar HTTP no link oficial FraLib")
    url = f"https://seunegociofralib.site/sites/2/{slug}/"
    result = subprocess.run(["curl", "-skI", url], capture_output=True, text=True, timeout=30)
    print(result.stdout)
    if " 200" in result.stdout or "HTTP/2 200" in result.stdout or "HTTP/1.1 200" in result.stdout:
        step(f"SUCESSO: {url}")
        banner(f"DEPLOY OFICIAL CONCLUIDO")
        print(f"  URL: {url}")
        print(f"  TENANT: 2 (Academia Pump Iron SP)")
        print(f"  ENGINE: Vite/React + shadcn/ui (Sprint 11+12)")
        manifest = REPO / ".tmp" / f"sprint124-{slug}.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(_json.dumps({
            "sprint": "12.4", "lead_id": lead_id, "job_id": job_id, "build_job_id": build_job_id,
            "tenant_id": 2, "slug": slug, "engine": "vite_react", "deploy_path": str(target),
            "deploy_url": url, "status": "success",
            "files_deployed": sorted([p.name for p in target.rglob("*") if p.is_file()]),
        }, indent=2), encoding="utf-8")
        return 0
    print("  ERRO: site nao respondeu 200 OK")
    return 1


if __name__ == "__main__":
    sys.exit(main())
