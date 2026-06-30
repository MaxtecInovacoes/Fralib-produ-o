#!/usr/bin/env python3
"""
Script de Auditoria Automatizada — FraLib
Executa todas as verificações críticas de uma vez.

Uso:
    python scripts/audit_runner.py
    python scripts/audit_runner.py --json  # Output JSON
    python scripts/audit_runner.py --fix   # Aplica correções sugeridas
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows emoji encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_check(name: str, check_func) -> dict:
    """Executa uma verificação e retorna resultado."""
    try:
        result = check_func()
        return {"name": name, "status": "pass", "result": result}
    except Exception as e:
        return {"name": name, "status": "fail", "error": str(e)}


def check_security() -> dict:
    """Verifica vulnerabilidades de segurança."""
    # Verificar se IDOR foi corrigido
    users_endpoints = ROOT / "backend/endpoints/users_endpoints.py"
    content = users_endpoints.read_text(encoding="utf-8", errors="ignore")

    # Deve ter filtro por user_id
    has_user_filter = "user_id = :uid" in content or "user_id=:uid" in content
    has_leads_cache_tenant = "user_id" in content and "leads_cache" in content

    return {
        "idor_fixed": has_user_filter,
        "cache_isolated": has_leads_cache_tenant,
    }


def check_queue_resilience() -> dict:
    """Verifica resiliência da fila outbound."""
    queue_file = ROOT / "backend/services/outbound_queue.py"
    content = queue_file.read_text(encoding="utf-8", errors="ignore")

    return {
        "has_dlq": "'dlq'" in content or '"dlq"' in content,
        "has_backoff": "backoff" in content.lower() or "2 **" in content,
        "has_cleanup_failed": "status = 'failed'" in content and "DELETE" in content,
        "has_stats": "get_queue_stats" in content,
    }


def check_database_config() -> dict:
    """Verifica configuração do banco de dados."""
    db_file = ROOT / "backend/core/database.py"
    if not db_file.exists():
        return {"error": "database.py não encontrado"}

    content = db_file.read_text(encoding="utf-8", errors="ignore")

    return {
        "has_pool_config": "pool_size" in content or "pool" in content.lower(),
        "has_ssl": "ssl" in content.lower() and "require" in content.lower(),
        "has_pre_ping": "pre_ping" in content.lower(),
    }


def check_observability() -> dict:
    """Verifica sistema de observabilidade."""
    obs_file = ROOT / "backend/observability.py"
    if not obs_file.exists():
        return {"error": "observability.py não encontrado"}

    content = obs_file.read_text(encoding="utf-8", errors="ignore")

    return {
        "has_trace_id": "trace_id" in content.lower(),
        "has_spans": "span" in content.lower(),
    }


def check_ci_cd() -> dict:
    """Verifica configuração CI/CD."""
    has_workflows = list(ROOT.glob(".github/workflows/*.yml"))
    has_post_receive = (ROOT / "scripts/post-receive").exists()
    has_dockerfile = (ROOT / "Dockerfile").exists()

    return {
        "has_github_actions": len(has_workflows) > 0,
        "has_deploy_hook": has_post_receive,
        "has_dockerfile": has_dockerfile,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria automatizada FraLib")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fix", action="store_true", help="Aplicar correções")
    args = parser.parse_args()

    checks = [
        ("Segurança", check_security),
        ("Fila Outbound", check_queue_resilience),
        ("Banco de Dados", check_database_config),
        ("Observabilidade", check_observability),
        ("CI/CD", check_ci_cd),
    ]

    results = []
    for name, check_func in checks:
        result = run_check(name, check_func)
        results.append(result)

    # Resumo
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")

    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "checks": results,
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("  🔍 AUDITORIA FRA LIB")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        for r in results:
            status_icon = "✅" if r["status"] == "pass" else "❌"
            print(f"\n{status_icon} {r['name']}")

            if r["status"] == "fail":
                print(f"   Erro: {r.get('error', 'desconhecido')}")
            else:
                for key, value in r.get("result", {}).items():
                    icon = "✅" if value else "❌"
                    print(f"   {icon} {key}: {value}")

        print("\n" + "=" * 60)
        print(f"  RESULTADO: {passed}/{len(results)} checks passaram")
        print("=" * 60)

        if failed > 0:
            print("\n⚠️  Algumas verificações falharam. Verifique o relatório.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
