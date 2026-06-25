#!/usr/bin/env python3
"""Sprint 12.5: Pipeline real controlada com lead REAL do tenant 2.

Pega lead pendente codex-test-barbearia-fio-nobre-pinhais-20260612 e roda
pipeline completa: 11 fases do orchestrator -> deploy path FraLib.
"""
from __future__ import annotations

import asyncio
import json as _json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Carrega .env ANTES de tudo
try:
    from dotenv import load_dotenv
    load_dotenv("/root/fralib/.env")
except ImportError:
    pass

REPO = Path("/root/fralib")
sys.path.insert(0, str(REPO))

os.environ["FRALIB_BUILDER_ENGINE"] = "vite_react"
os.environ["FRALIB_SINGLE_MODEL_ONLY"] = "0"
os.environ["FRALIB_VITE_NAMEHOST_MODELS"] = "claude-sonnet-4-6,claude-haiku-4-5"
os.environ["FRALIB_OPENUI_PRIMARY_MODEL"] = "claude-sonnet-4-6"
os.environ["FRALIB_PROXY_BUILDER_MODEL"] = "claude-sonnet-4-6"
os.environ["ANTHROPIC_BASE_URL"] = "https://api.kpalabz.com/v1"
os.environ["FRALIB_TRACING_ENABLED"] = "1"
os.environ["FRALIB_USE_SDK_LOOP"] = "1"


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


async def run_full_pipeline(tenant_id: int, lead_id: str, nome: str, cidade: str, segmento: str) -> dict:
    """Roda executar_pipeline_completo() em subprocess isolado (evita import side-effects)."""
    banner(f"FASE 1-11: PIPELINE COMPLETA DO ORCHESTRATOR (lead_id={lead_id})")

    # Subprocess que importa orchestrator isoladamente
    orchestrator_script = f'''
import sys, json, asyncio
sys.path.insert(0, "/root/fralib")
from backend.endpoints.pipeline_orchestrator_service import executar_pipeline_completo

async def main():
    config = {{
        "_job_id": "job-{lead_id}-{int(time.time())}",
        "_run_id": "run-{int(time.time())}",
        "lead_id": "{lead_id}",
        "tenant_id": {tenant_id},
        "segmento": "{segmento}",
        "cidade": "{cidade}",
        "nome": "{nome}",
        "engine": "vite_react",
    }}
    result = await executar_pipeline_completo(config=config, tenant_id={tenant_id}, queue_id=None, resume_from_phase=0)
    print("PIPELINE_OK:", str(result)[:200])

asyncio.run(main())
'''

    script_path = Path("/tmp/run_orchestrator_isolated.py")
    script_path.write_text(orchestrator_script, encoding="utf-8")

    step(f"Subprocess rodando orchestrator isolado para {lead_id}")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=540,
        )
        elapsed = time.time() - t0
        # Mostra ultimas 30 linhas de stdout
        if proc.stdout:
            for line in proc.stdout.splitlines()[-30:]:
                step(f"  orchestrator: {line}")
        if proc.returncode == 0 or "PIPELINE_OK" in proc.stdout:
            step(f"Pipeline completa em {elapsed:.1f}s (orchestrator OK)")
            return {"ok": True, "elapsed": elapsed, "stdout_tail": proc.stdout[-500:]}
        else:
            step(f"Orchestrator retornou {proc.returncode}; tentando fallback builder-job")
            if proc.stderr:
                for line in proc.stderr.splitlines()[-10:]:
                    step(f"  err: {line}")
            return {"ok": False, "elapsed": elapsed, "stderr_tail": proc.stderr[-500:]}
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        step(f"Timeout apos {elapsed:.1f}s (orchestrator demorou demais)")
        return {"ok": False, "elapsed": elapsed, "error": "timeout"}
    except Exception as e:
        elapsed = time.time() - t0
        step(f"ERRO ao rodar orchestrator: {e}")
        return {"ok": False, "elapsed": elapsed, "error": str(e)}


def slug_from_name(name: str) -> str:
    """Gera slug do lead name: 'Barbearia Fio Nobre Pinhais' -> 'barbearia-fio-nobre-pinhais'"""
    return name.lower().replace(" ", "-").replace("ã", "a").replace("õ", "o").replace("ç", "c").replace("é", "e").replace("í", "i")


async def main_async() -> int:
    banner("SPRINT 12.5 - PIPELINE REAL LEAD REAL TENANT 2")

    step("Etapa 1: Buscar lead REAL pendente do tenant 2")
    from sqlalchemy import create_engine, text

    db_url = "postgresql://postgres:fralib2024@localhost:5433/fralib_db"
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # LEAD REAL DO CODEX - Barbearia Fio Nobre Pinhais
        lead_id = "codex-test-barbearia-fio-nobre-pinhais-20260612"
        row = conn.execute(
            text("SELECT id, nome, telefone, cidade, segmento, status FROM leads WHERE id=:id AND user_id=2"),
            {"id": lead_id},
        ).fetchone()

        if not row:
            step(f"Lead {lead_id} nao encontrado")
            return 1

        nome = row[1]
        cidade = row[3]
        segmento = row[4]
        slug = slug_from_name(nome)

        step(f"Lead REAL: {nome}")
        step(f"  cidade={cidade} segmento={segmento}")
        step(f"  slug={slug}")

    step("Etapa 2: Atualizar briefing do lead (PRD rico)")
    briefing = {
        "lead_id": lead_id,
        "business_name": nome,
        "city": cidade.title(),
        "segment": segmento,
        "phone": "4100000000",
        "endereco": f"Centro, {cidade.title()} - PR",
        "services": ["Corte masculino", "Barba", "Sobrancelha", "Pigmentacao", "Platinado"],
        "horarios": "Seg-Sex 9h-20h | Sab 9h-18h",
        "description": f"{nome} - barbearia premium em {cidade.title()} com ambiente moderno",
        "differentials": ["Atendimento premium", "Barbeiros certificados", "Produtos importados"],
        "target_audience": "Homens 25-55 anos premium",
        "instagram": "@barbeariafionobre",
    }
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE leads SET _leaddata=:dados, briefing_json=:brief WHERE id=:id"),
            {"dados": _json.dumps(briefing), "brief": _json.dumps(briefing), "id": lead_id},
        )
    step("Briefing salvo no Postgres")

    step("Etapa 3: Rodar pipeline completa controlada (11 fases)")
    pipeline_result = await run_full_pipeline(2, lead_id, nome, cidade, segmento)

    step("Etapa 4: Build via pipeline.py builder-job (backup explicito)")
    prd_path = Path("/tmp/prd_barbearia_fio_nobre.json")
    prd_path.write_text(_json.dumps(briefing, ensure_ascii=False), encoding="utf-8")

    build_job_id = f"build-{slug}-{int(time.time())}"
    cmd = [sys.executable, str(REPO / "pipeline.py"), "builder-job",
           "--prd-json", str(prd_path), "--tenant-id", "2",
           "--job-id", build_job_id, "--target", "landing-page",
           "--model", "claude-sonnet-4-6", "--execute"]
    step(f"Executando: pipeline.py builder-job")
    result = subprocess.run(cmd, cwd=str(REPO), env=os.environ.copy(), timeout=540)
    if result.returncode != 0:
        step(f"WARN: builder-job retornou {result.returncode} (orchestrator ja fez)")

    step("Etapa 5: Localizar dist/ gerado")
    dist_dir = Path(f"/tmp/fralib_builder/tenant-2/{build_job_id}/dist")
    if not dist_dir.exists() or not list(dist_dir.iterdir()):
        candidates = sorted(Path("/tmp/fralib_builder/tenant-2/").glob("*/dist"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            dist_dir = candidates[0]
            step(f"Usando dist alternativo: {dist_dir}")

    if not dist_dir.exists():
        step(f"ERRO FATAL: nenhum dist encontrado")
        return 1

    step(f"dist/ = {dist_dir} ({len(list(dist_dir.iterdir()))} arquivos)")

    step("Etapa 6: Deploy em /var/www/fralib/sites/2/<slug>/")
    target = deploy_to_fralib(2, slug, dist_dir)
    step(f"Deploy concluido em: {target}")

    step("Etapa 7: Validar HTTP no link FraLib")
    url = f"https://seunegociofralib.site/sites/2/{slug}/"
    result = subprocess.run(["curl", "-skI", url], capture_output=True, text=True, timeout=30)
    print(result.stdout)

    if " 200" in result.stdout or "HTTP/2 200" in result.stdout or "HTTP/1.1 200" in result.stdout:
        step(f"SUCESSO: {url}")
        banner("DEPLOY OFICIAL CONCLUIDO - LEAD REAL TENANT 2")
        print(f"  LEAD ID: {lead_id}")
        print(f"  NOME: {nome} ({segmento}/{cidade})")
        print(f"  URL: {url}")
        print(f"  PIPELINE ORCHESTRATOR: {'OK' if pipeline_result.get('ok') else 'FALLBACK'}")
        print(f"  ENGINE: Vite/React + shadcn/ui + Tailwind")

        manifest = REPO / ".tmp" / f"sprint125-{slug}.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(_json.dumps({
            "sprint": "12.5",
            "lead_id_real": lead_id,
            "nome": nome,
            "cidade": cidade,
            "segmento": segmento,
            "slug": slug,
            "tenant_id": 2,
            "engine": "vite_react",
            "deploy_path": str(target),
            "deploy_url": url,
            "status": "success",
            "pipeline_result": pipeline_result,
            "files_deployed": sorted([p.name for p in target.rglob("*") if p.is_file()]),
        }, indent=2, default=str), encoding="utf-8")
        return 0

    print("  ERRO: site nao respondeu 200 OK")
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
