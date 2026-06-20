#!/usr/bin/env python3
"""Benchmark pipeline - detecta regressões após refatoração.

Uso:
    python scripts/benchmark_pipeline.py before  # salva em /tmp/benchmark_before.json
    python scripts/benchmark_pipeline.py after   # salva em /tmp/benchmark_after.json
    python scripts/benchmark_pipeline.py compare before after

Este script executa o pipeline com um lead fake controlado e mede:
- Tempo total de execução
- Fases executadas
- Créditos consumidos
- Tamanho do HTML gerado

Detecta regressões automaticamente:
- Pipeline quebrou (sucesso → falha)
- Pipeline ficou > 1.5x mais lento
- HTML ficou muito menor (< 50% do original)
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Adicionar backend ao path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (str(BACKEND), str(BACKEND / "core"), str(BACKEND / "services")):
    if path not in sys.path:
        sys.path.insert(0, path)

# Carregar .env para variáveis de ambiente
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
except Exception:
    pass

# Configurar variáveis de ambiente para teste
import os

os.environ.setdefault("TESTING", "true")

# Lead FAKE controlado - restaurante em São Paulo
LEAD_FAKE: dict[str, Any] = {
    "segmento": "restaurante",
    "cidade": "São Paulo",
    "nome": "Restaurante Teste E2E",
    "telefone": "+5511999999999",
    "whatsapp": "+5511999999999",
    "rating": 4.5,
    "total_avaliacoes": 50,
    "reviews": [
        {"autor": "Maria S.", "rating": 5, "texto": "Ótimo!"},
        {"autor": "João P.", "rating": 4, "texto": "Boa comida!"},
    ],
    "website": "",
    "endereco": "Rua Teste, 123 - São Paulo, SP",
}

# Tenant de teste
TENANT_ID_BENCHMARK = 999999


async def run_benchmark() -> dict[str, Any]:
    """Roda pipeline com lead fake."""
    start = time.time()
    try:
        from backend.endpoints.pipeline_orchestrator_service import (
            executar_pipeline_completo,
        )

        result = await executar_pipeline_completo(
            config={
                "segmento": LEAD_FAKE["segmento"],
                "cidade": LEAD_FAKE["cidade"],
                "quantidade": 1,
                "_skip_franz_outreach": True,  # Não tenta WhatsApp real
                "_controlled_test": True,  # Flag de teste controlado
            },
            tenant_id=TENANT_ID_BENCHMARK,
        )

        elapsed = time.time() - start

        # Extrair dados relevantes do resultado
        html_content = result.get("html", "") if result else ""

        output = {
            "success": result.get("sucesso", False) if result else False,
            "elapsed_seconds": round(elapsed, 2),
            "phases_executed": result.get("fases_executadas", [])
            if result
            else [],
            "html_size": len(html_content),
            "site_url": result.get("site_url", "") if result else "",
            "credit_consumed": result.get("credito_consumido", 0) if result else 0,
            "lead_nome": result.get("lead", "?") if result else "?",
            "error": result.get("erro", "") if result else "",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            # Campos extras para debug
            "result_keys": list(result.keys()) if result else [],
        }

        return output

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_seconds": round(time.time() - start, 2),
            "phases_executed": [],
            "html_size": 0,
            "site_url": "",
            "credit_consumed": 0,
            "lead_nome": "?",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


def compare_results(before_path: str, after_path: str) -> bool:
    """Compara dois benchmarks e detecta regressoes."""
    with open(before_path) as f:
        before = json.load(f)
    with open(after_path) as f:
        after = json.load(f)

    print("=" * 60)
    print("COMPARACAO ANTES vs DEPOIS")
    print("=" * 60)
    print(f"Sucesso:        {before.get('success')} -> {after.get('success')}")
    print(
        f"Tempo (s):      {before.get('elapsed_seconds', 0):.2f} -> {after.get('elapsed_seconds', 0):.2f}"
    )
    print(
        f"HTML size:      {before.get('html_size', 0)} -> {after.get('html_size', 0)}"
    )
    print(
        f"Fases executadas: {len(before.get('phases_executed', []))} -> {len(after.get('phases_executed', []))}"
    )
    print(f"Creditos consumidos: {before.get('credit_consumed', 0)} -> {after.get('credit_consumed', 0)}")

    if before.get("error"):
        print(f"Erro antes:     {before.get('error', '')[:80]}")
    if after.get("error"):
        print(f"Erro depois:    {after.get('error', '')[:80]}")

    # Detectar regressoes
    regressions = []

    # Regressao 1: Pipeline quebrou
    if before.get("success") and not after.get("success"):
        regressions.append("Pipeline quebrou (sucesso -> falha)")

    # Regressao 2: Tempo aumentou significativamente
    before_time = before.get("elapsed_seconds", 1)
    after_time = after.get("elapsed_seconds", 1)
    if before_time > 0:
        elapsed_ratio = after_time / max(before_time, 0.1)
        if elapsed_ratio > 1.5:
            regressions.append(
                f"Pipeline ficou {elapsed_ratio:.1f}x mais lento ({before_time:.1f}s -> {after_time:.1f}s)"
            )

    # Regressao 3: HTML ficou muito menor
    before_html = before.get("html_size", 0)
    after_html = after.get("html_size", 0)
    if before_html > 0 and after_html < before_html * 0.5:
        regressions.append(
            f"HTML ficou muito menor ({before_html} -> {after_html} bytes)"
        )

    # Regressao 4: Fases executadas diminuíram significativamente
    before_phases = len(before.get("phases_executed", []))
    after_phases = len(after.get("phases_executed", []))
    if before_phases > 0 and after_phases < before_phases * 0.5:
        regressions.append(
            f"Fases diminuíram significativamente ({before_phases} -> {after_phases})"
        )

    # Resultado final
    print("=" * 60)
    if regressions:
        print("REGRESSOES DETECTADAS:")
        for i, reg in enumerate(regressions, 1):
            print(f"  {i}. {reg}")
        return False
    else:
        print("OK - sem regressoes detectadas")
        return True


def print_usage():
    """Imprime instruções de uso."""
    print("Benchmark Pipeline - Detecta regressões após refatoração")
    print()
    print("Uso:")
    print("  python scripts/benchmark_pipeline.py before  # salva em /tmp/benchmark_before.json")
    print("  python scripts/benchmark_pipeline.py after   # salva em /tmp/benchmark_after.json")
    print("  python scripts/benchmark_pipeline.py compare before after")
    print()
    print("Este script executa o pipeline com um lead fake controlado e mede:")
    print("- Tempo total de execução")
    print("- Fases executadas")
    print("- Créditos consumidos")
    print("- Tamanho do HTML gerado")
    print()
    print("Detecta regressões automaticamente:")
    print("- Pipeline quebrou (sucesso -> falha)")
    print("- Pipeline ficou > 1.5x mais lento")
    print("- HTML ficou muito menor (< 50% do original)")


def main():
    """Entry point principal."""
    if len(sys.argv) < 2:
        print_usage()
        print("\nERRO: Comando não especificado")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--help":
        print_usage()
        sys.exit(0)

    if cmd in ("before", "after"):
        # Executar benchmark e salvar resultado
        print(f"Executando benchmark ({cmd})...")
        print(f"Tenant ID: {TENANT_ID_BENCHMARK}")
        print(f"Lead: {LEAD_FAKE['segmento']} em {LEAD_FAKE['cidade']}")
        print("-" * 40)

        result = asyncio.run(run_benchmark())

        path = f"/tmp/benchmark_{cmd}.json"
        Path(path).write_text(json.dumps(result, indent=2))

        print(f"\nResultado salvo em: {path}")
        print("\n" + "=" * 40)
        print("RESUMO:")
        print(f"  Sucesso: {result.get('success')}")
        print(f"  Tempo: {result.get('elapsed_seconds')}s")
        print(f"  HTML size: {result.get('html_size')} bytes")
        print(f"  Fases: {len(result.get('phases_executed', []))}")
        print(f"  Créditos: {result.get('credit_consumed', 0)}")
        if result.get("error"):
            print(f"  Erro: {result.get('error', '')[:100]}")

        sys.exit(0 if result.get("success") else 1)

    elif cmd == "compare":
        if len(sys.argv) < 4:
            print("Uso: compare <before.json> <after.json>")
            sys.exit(1)

        before_path = sys.argv[2]
        after_path = sys.argv[3]

        if not Path(before_path).exists():
            print(f"ERRO: Arquivo não encontrado: {before_path}")
            sys.exit(1)
        if not Path(after_path).exists():
            print(f"ERRO: Arquivo não encontrado: {after_path}")
            sys.exit(1)

        ok = compare_results(before_path, after_path)
        sys.exit(0 if ok else 1)

    else:
        print(f"ERRO: Comando desconhecido: {cmd}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
