"""
Liam LATS — Language Agent Tree Search para seções que falham (PRD #13)
Quando reflection falha 2x, explora 3 abordagens alternativas em paralelo.
Avalia cada branch com Liz rubrica, escolhe melhor.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

LATS_STRATEGIES = [
    {
        "id": "simplificar",
        "instrucao": """ABORDAGEM: SIMPLIFICAR
A versão anterior foi reprovada por complexidade excessiva.
- Reduzir elementos visuais ao mínimo essencial
- Layout mais limpo e direto
- Menos animações, menos gradients
- Foco em legibilidade e clareza
- Mobile-first extremo (pensar em 375px primeiro)""",
    },
    {
        "id": "reestruturar",
        "instrucao": """ABORDAGEM: REESTRUTURAR LAYOUT
A versão anterior tinha problemas estruturais.
- Mudar completamente o layout (se era grid, tentar flex column; se era full-width, tentar contained)
- Repensar hierarquia visual do zero
- Inverter ordem dos elementos se fizer sentido
- Novo approach pra CTA (posição, tamanho, cor)
- Manter conteúdo do PRD mas reorganizar apresentação""",
    },
    {
        "id": "referencia_nicho",
        "instrucao": """ABORDAGEM: REFERÊNCIA DO NICHO
A versão anterior não capturou a essência do nicho.
- Usar padrões visuais reconhecíveis do segmento
- Cores e tipografia que o público-alvo espera
- Imagens posicionadas como referências do setor
- Copy no tom exato que este público responde
- Estrutura que sites TOP deste nicho usam""",
    },
]


def lats_retry(
    nome_secao: str,
    prd_secao: dict,
    design_tokens_str: str,
    fotos: list,
    historico_falhas: list,
    nicho: str = "",
    tier: str = "STANDARD",
) -> dict:
    """
    Tree search: explora 3 abordagens alternativas em paralelo.
    Returns: {"html": str, "score": float, "strategy": str, "aprovado": bool}
    """
    from llm_direct import call_claude
    from agent_router import get_router

    print(f"[LATS] Seção {nome_secao} | Ativando tree search (reflection falhou 2x)")

    falhas_contexto = _formatar_historico_falhas(historico_falhas)

    _router = get_router()
    modelo = _router.get_model("liam") if _router else "opus"

    branches = {}

    def _gerar(strategy):
        system = f"""Você é Liam. Gere a seção '{nome_secao}' em HTML.

IMPORTANTE: Tentativas anteriores FALHARAM. Você DEVE usar uma abordagem DIFERENTE.

{strategy['instrucao']}

REGRAS:
- Seguir PRD (conteúdo obrigatório)
- Usar tokens de design fornecidos (variáveis CSS)
- Foto obrigatória se disponível
- Mobile-first
- Retorne APENAS HTML da <section> (sem markdown, sem ```)
- NÃO repetir os erros das tentativas anteriores"""

        fotos_str = json.dumps(fotos[:3], ensure_ascii=False) if fotos else "[]"
        user = f"""## PRD da seção:
{json.dumps(prd_secao, ensure_ascii=False)[:2000]}

## Tokens de Design:
{design_tokens_str[:500]}

## Fotos disponíveis:
{fotos_str}

## TENTATIVAS ANTERIORES QUE FALHARAM (NÃO REPETIR):
{falhas_contexto}

Gere HTML com abordagem '{strategy['id']}'. Seja criativo e DIFERENTE."""

        import re
        html = call_claude(
            system=system, user=user, model=modelo,
            max_tokens=6000, temperature=0.95, agent_name='lats_branch'
        )
        html = html.strip()
        if html.startswith("```"):
            html = re.sub(r"^```\w*\n?", "", html)
            html = re.sub(r"\n?```$", "", html)

        score = _avaliar_branch(html, nome_secao, nicho, tier)
        return {"html": html, "score": score, "strategy": strategy["id"]}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for strategy in LATS_STRATEGIES:
            future = executor.submit(_gerar, strategy)
            futures[future] = strategy["id"]

        for future in as_completed(futures, timeout=120):
            strategy_id = futures[future]
            try:
                resultado = future.result(timeout=90)
                if resultado["html"] and len(resultado["html"]) > 200:
                    branches[strategy_id] = resultado
                    print(f"[LATS] Branch '{strategy_id}' | score={resultado['score']:.1f}")
            except Exception as e:
                print(f"[LATS][WARN] Branch '{strategy_id}' falhou: {e}")

    if not branches:
        print("[LATS][WARN] Todas branches falharam. Retornando última tentativa.")
        last = historico_falhas[-1] if historico_falhas else {"html": "", "score": 0}
        return {"html": last.get("html", ""), "score": last.get("score", 0),
                "strategy": "fallback", "aprovado": False}

    melhor_id = max(branches, key=lambda k: branches[k]["score"])
    melhor = branches[melhor_id]

    threshold = 7.0 if tier == "STANDARD" else 8.5
    melhor["aprovado"] = melhor["score"] >= threshold

    if melhor["aprovado"]:
        print(f"[LATS] Seção {nome_secao} | APROVADA via branch '{melhor_id}' (score={melhor['score']:.1f})")
    else:
        print(f"[LATS] Seção {nome_secao} | Nenhuma branch passou threshold. Melhor: '{melhor_id}' ({melhor['score']:.1f})")

    return melhor


def _avaliar_branch(html: str, nome_secao: str, nicho: str, tier: str) -> float:
    """Avalia branch com rubrica simplificada (Haiku, rápido)."""
    from llm_direct import call_claude

    system = """Avalie este HTML de seção de landing page em escala 0-10.
Critérios: responsividade, contraste, semântica HTML, CTA claro, fotos reais, copy específico.
Retorne APENAS um número decimal (ex: 7.5). Nada mais."""

    user = f"Nicho: {nicho} | Tier: {tier} | Seção: {nome_secao}\n\nHTML:\n{html[:3000]}"

    try:
        resp = call_claude(system=system, user=user, model='haiku', max_tokens=50, temperature=0.1, agent_name='lats_eval')
        import re
        match = re.search(r'(\d+\.?\d*)', resp.strip())
        if match:
            return min(10.0, max(0.0, float(match.group(1))))
    except Exception:
        pass
    return 5.0


def _formatar_historico_falhas(historico: list) -> str:
    if not historico:
        return "Nenhuma tentativa anterior."
    linhas = []
    for i, falha in enumerate(historico, 1):
        problemas = falha.get("problemas", "score baixo")
        if isinstance(problemas, list):
            problemas = ", ".join([str(p)[:80] for p in problemas[:3]])
        linhas.append(f"Tentativa {i} (score={falha.get('score', 0):.1f}): {str(problemas)[:150]}")
    return "\n".join(linhas)
