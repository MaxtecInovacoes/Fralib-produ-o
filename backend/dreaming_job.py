"""
Dreaming Job — Consolidação noturna de aprendizados (PRD #14)
Roda via cron às 3h. Revisa runs do dia, extrai padrões, consolida memória.
Custo: ~$0.10-0.30/noite (Haiku only).
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ajustar path pra imports do projeto
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

__COLD_DIR = Path(os.environ.get("FRALIB_BASE_DIR", str(Path(__file__).resolve().parent))) / "memory" / "cold"
__DREAM_LOG_DIR = Path(os.environ.get("FRALIB_BASE_DIR", str(Path(__file__).resolve().parent))) / "memory" / "dream_logs"
_WARM_DIR = Path(os.environ.get("FRALIB_BASE_DIR", str(Path(__file__).resolve().parent))) / "memory" / "warm"


def coletar_runs_recentes(horas: int = 24) -> list:
    runs = []
    if not _COLD_DIR.exists():
        return runs
    cutoff = datetime.now() - timedelta(hours=horas)
    for path in _COLD_DIR.glob("*.json"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) > cutoff:
                with open(path, 'r', encoding='utf-8') as f:
                    runs.append(json.load(f))
        except Exception:
            continue
    print(f"[DREAM] Coletados {len(runs)} runs das últimas {horas}h")
    return runs


def replay_e_analisar(runs: list) -> dict:
    por_nicho = {}
    for run in runs:
        nicho = run.get("nicho", "desconhecido")
        if nicho not in por_nicho:
            por_nicho[nicho] = {"sucesso": [], "falha": []}
        if run.get("liz_aprovado"):
            por_nicho[nicho]["sucesso"].append(run)
        else:
            por_nicho[nicho]["falha"].append(run)

    resultados = {
        "padroes_sucesso": [],
        "anti_padroes": [],
        "insights_nicho": {},
        "metricas": {
            "total_runs": len(runs),
            "taxa_sucesso": sum(1 for r in runs if r.get("liz_aprovado")) / max(len(runs), 1),
            "por_nicho": {},
        },
    }

    for nicho, dados in por_nicho.items():
        print(f"[DREAM] Analisando nicho '{nicho}' ({len(dados['sucesso'])} sucesso, {len(dados['falha'])} falha)")
        analise = _analisar_nicho(nicho, dados)
        resultados["padroes_sucesso"].extend(analise.get("padroes", []))
        resultados["anti_padroes"].extend(analise.get("anti_padroes", []))
        resultados["insights_nicho"][nicho] = analise.get("insight_geral", "")
        resultados["metricas"]["por_nicho"][nicho] = {
            "sucesso": len(dados["sucesso"]),
            "falha": len(dados["falha"]),
            "taxa": len(dados["sucesso"]) / max(len(dados["sucesso"]) + len(dados["falha"]), 1),
        }

    return resultados


def _analisar_nicho(nicho: str, dados: dict) -> dict:
    from llm_direct import call_claude

    sucesso_resumo = [{"lead": r.get("lead", "?")} for r in dados["sucesso"][:5]]
    falha_resumo = [{"lead": r.get("lead", "?")} for r in dados["falha"][:5]]

    if not sucesso_resumo and not falha_resumo:
        return {"padroes": [], "anti_padroes": [], "insight_geral": ""}

    system = """Você é o Analista de Padrões. Revise resultados de geração de sites para este nicho.

Extraia:
1. PADRÕES DE SUCESSO: o que sites aprovados têm em comum (max 3, específicos e acionáveis)
2. ANTI-PADRÕES: erros recorrentes nos sites reprovados (max 3)
3. INSIGHT GERAL: 1 frase sobre o que este nicho precisa

Formato JSON:
{"padroes": ["padrão 1", "padrão 2"], "anti_padroes": ["erro 1"], "insight_geral": "frase curta"}

Seja ESPECÍFICO. Não genérico."""

    user = f"""Nicho: {nicho}
Sites APROVADOS ({len(dados['sucesso'])}): {json.dumps(sucesso_resumo, ensure_ascii=False)[:1000]}
Sites REPROVADOS ({len(dados['falha'])}): {json.dumps(falha_resumo, ensure_ascii=False)[:1000]}

Analise e extraia padrões."""

    try:
        import re
        resposta = call_claude(system=system, user=user, model='haiku', max_tokens=1500, temperature=0.3)
        resposta = resposta.strip()
        if resposta.startswith("```"):
            resposta = re.sub(r"^```\w*\n?", "", resposta)
            resposta = re.sub(r"\n?```$", "", resposta)
        return json.loads(resposta)
    except Exception as e:
        print(f"[DREAM] Análise falhou pra {nicho}: {e}")
        return {"padroes": [], "anti_padroes": [], "insight_geral": ""}


def consolidar_memorias(resultados: dict):
    from agent_memory import CoreMemory, WarmMemory, MemoryEntry

    core = CoreMemory()
    warm = WarmMemory()

    for padrao in resultados["padroes_sucesso"]:
        conteudo = padrao if isinstance(padrao, str) else str(padrao)
        entry = MemoryEntry(
            id=f"dream_{datetime.now().strftime('%Y%m%d')}_{hash(conteudo) % 10000}",
            tipo="padrao",
            agente="liam",
            nicho="*",
            conteudo=conteudo[:100],
            confianca=0.6,
            fonte="dreaming_job",
        )
        warm.adicionar(entry)
        print(f"[DREAM] Warm +1: '{conteudo[:50]}'")

    for anti in resultados["anti_padroes"]:
        conteudo = f"EVITAR: {anti}" if isinstance(anti, str) else f"EVITAR: {str(anti)}"
        entry = MemoryEntry(
            id=f"dream_anti_{datetime.now().strftime('%Y%m%d')}_{hash(conteudo) % 10000}",
            tipo="erro",
            agente="liam",
            nicho="*",
            conteudo=conteudo[:100],
            confianca=0.7,
            fonte="dreaming_job",
        )
        warm.adicionar(entry)

    warm.promover_para_core(core)
    _podar_memorias_fracas()


def _podar_memorias_fracas():
    warm_dir = _WARM_DIR
    if not warm_dir.exists():
        return
    podadas = 0
    for nicho_file in warm_dir.glob("*.json"):
        try:
            with open(nicho_file, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            antes = len(entries)
            entries = [
                e for e in entries
                if e.get("confianca", 0) >= 0.3
                and (datetime.now() - datetime.fromisoformat(e.get("atualizado_em", datetime.now().isoformat()))).days < 30
            ]
            podadas += antes - len(entries)
            with open(nicho_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        except Exception:
            continue
    if podadas > 0:
        print(f"[DREAM] Podadas {podadas} memórias fracas")


def counterfactual_replay(runs_falhos: list) -> list:
    if not runs_falhos:
        return []
    from llm_direct import call_claude

    hipoteses = []
    for run in runs_falhos[:3]:
        system = """Analise este pipeline run que FALHOU e gere 1 hipótese:
"Se tivesse feito X diferente na fase Y, provavelmente teria funcionado porque Z."
Retorne JSON: {"fase": int, "hipotese": "...", "confianca": 0.5}"""

        user = f"""Run falho:
- Nicho: {run.get('nicho')}
- Lead: {run.get('lead')}
O que poderia ter sido feito diferente?"""

        try:
            import re
            resp = call_claude(system=system, user=user, model='haiku', max_tokens=500, temperature=0.5)
            resp = resp.strip()
            if resp.startswith("```"):
                resp = re.sub(r"^```\w*\n?", "", resp)
                resp = re.sub(r"\n?```$", "", resp)
            hipoteses.append(json.loads(resp))
        except Exception:
            pass

    return hipoteses


def gerar_relatorio(resultados: dict, hipoteses: list) -> str:
    _DREAM_LOG_DIR.mkdir(parents=True, exist_ok=True)
    data = datetime.now().strftime("%Y-%m-%d")
    metricas = resultados["metricas"]

    relatorio = f"""# Dream Report — {data}

## Métricas do Dia
- Runs: {metricas['total_runs']}
- Taxa sucesso: {metricas['taxa_sucesso']:.0%}
- Por nicho: {json.dumps(metricas['por_nicho'], indent=2, ensure_ascii=False)}

## Padrões de Sucesso
{chr(10).join(f'- {p}' for p in resultados['padroes_sucesso']) or '- Nenhum identificado'}

## Anti-Padrões
{chr(10).join(f'- {a}' for a in resultados['anti_padroes']) or '- Nenhum identificado'}

## Insights por Nicho
{chr(10).join(f'- **{k}**: {v}' for k, v in resultados['insights_nicho'].items() if v) or '- Nenhum'}

## Hipóteses Counterfactual
{chr(10).join(f'- Fase {h.get("fase", "?")}: {h.get("hipotese", "?")} (conf: {h.get("confianca", 0):.0%})' for h in hipoteses) or '- Nenhuma'}
"""

    path = _DREAM_LOG_DIR / f"dream_{data}.md"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(relatorio)
    print(f"[DREAM] Relatório salvo: {path}")
    return relatorio


def executar_dreaming_job():
    print(f"[DREAM] {'=' * 50}")
    print(f"[DREAM] Iniciando dreaming job — {datetime.now().isoformat()}")
    print(f"[DREAM] {'=' * 50}")

    runs = coletar_runs_recentes(horas=24)
    if not runs:
        print("[DREAM] Nenhum run nas últimas 24h. Abortando.")
        return

    resultados = replay_e_analisar(runs)

    runs_falhos = [r for r in runs if not r.get("liz_aprovado")]
    hipoteses = counterfactual_replay(runs_falhos)

    consolidar_memorias(resultados)

    gerar_relatorio(resultados, hipoteses)

    print(f"[DREAM] {'=' * 50}")
    print(f"[DREAM] Concluído | Padrões: {len(resultados['padroes_sucesso'])} | Anti: {len(resultados['anti_padroes'])} | Hipóteses: {len(hipoteses)}")
    print(f"[DREAM] {'=' * 50}")


# Cleanup: remover dream logs > 30 dias
def _cleanup_dream_logs():
    if not _DREAM_LOG_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=30)
    for f in _DREAM_LOG_DIR.glob("*.md"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()


if __name__ == "__main__":
    _cleanup_dream_logs()
    executar_dreaming_job()
