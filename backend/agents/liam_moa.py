"""
Liam MoA — Mixture of Agents para seção Hero (PRD #12)
Gera 3 versões paralelas com direções criativas diferentes,
aggregator (Sonnet) escolhe/combina a melhor.
Só ativa em leads médios/complexos (router decide).
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

DIRECOES_HERO = [
    {
        "id": "impacto_visual",
        "instrucao": """Priorize IMPACTO VISUAL máximo:
- Gradient overlay dramático sobre foto hero
- Tipografia grande e bold (clamp(2.5rem, 5vw, 4rem))
- Contraste extremo texto/fundo
- Animação de entrada marcante (fade-up + scale)
- Menos texto, mais presença visual""",
    },
    {
        "id": "copy_persuasivo",
        "instrucao": """Priorize COPY PERSUASIVO:
- Headline com benefício claro e urgência
- Sub-headline que elimina objeção principal
- CTA irresistível com verbo de ação + resultado
- Prova social visível (número de clientes, avaliação)
- Texto > visual nesta versão""",
    },
    {
        "id": "confianca_social",
        "instrucao": """Priorize CONFIANÇA e PROVA SOCIAL:
- Badge/selo de avaliação Google (★ rating)
- Contador de clientes atendidos
- Depoimento curto em destaque
- Layout que transmite profissionalismo e solidez
- Trust signals acima do fold""",
    },
]

MOA_CONFIG = {
    "complexo": {"model_geracao": "opus", "model_aggregator": "sonnet"},
    "medio": {"model_geracao": "sonnet", "model_aggregator": "sonnet"},
}


def gerar_hero_moa(prd_hero: dict, design_tokens_str: str, fotos: list, complexidade: str = "medio") -> str:
    """
    Gera 3 versões da hero em paralelo, aggregator escolhe melhor.
    Returns: HTML da melhor hero
    """
    from llm_direct import call_claude

    config = MOA_CONFIG.get(complexidade, MOA_CONFIG["medio"])
    model_gen = config["model_geracao"]
    model_agg = config["model_aggregator"]

    print(f"[MOA] Hero | Gerando 3 versões paralelas (model={model_gen})...")

    versoes = {}

    def _gerar(direcao):
        system = f"""Você é Liam. Gere a seção HERO em HTML seguindo o PRD e a direção criativa.

DIREÇÃO CRIATIVA: {direcao['instrucao']}

REGRAS:
- Usar tokens de design fornecidos (variáveis CSS)
- Foto hero obrigatória (usar URL fornecida)
- Mobile-first (funcionar em 375px)
- Semântica HTML5 (<section>)
- Max 1 CTA principal + 1 secundário opcional
- Retorne APENAS HTML (sem markdown, sem ```)"""

        fotos_str = json.dumps(fotos[:3], ensure_ascii=False) if fotos else "[]"
        user = f"""## PRD Hero:
{json.dumps(prd_hero, ensure_ascii=False)[:2000]}

## Tokens de Design:
{design_tokens_str[:500]}

## Fotos disponíveis (usar a primeira como hero):
{fotos_str}

Gere HTML completo da <section> hero. Direção: {direcao['id']}."""

        return call_claude(
            system=system, user=user, model=model_gen,
            max_tokens=4000, temperature=0.9, agent_name='liam_moa'
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for direcao in DIRECOES_HERO:
            future = executor.submit(_gerar, direcao)
            futures[future] = direcao["id"]

        for future in as_completed(futures, timeout=90):
            direcao_id = futures[future]
            try:
                html = future.result(timeout=60)
                if html and len(html) > 200:
                    versoes[direcao_id] = html
                    print(f"[MOA] Hero versão '{direcao_id}' OK ({len(html)} chars)")
            except Exception as e:
                print(f"[MOA][WARN] Versão '{direcao_id}' falhou: {e}")

    if len(versoes) == 0:
        print("[MOA][WARN] Todas versões falharam. Retornando None.")
        return None

    if len(versoes) == 1:
        return list(versoes.values())[0]

    melhor = _aggregator_escolher(versoes, prd_hero, design_tokens_str, model_agg)
    print(f"[MOA] Hero | Aggregator escolheu versão final ({len(melhor)} chars)")
    return melhor


def _aggregator_escolher(versoes: dict, prd_hero: dict, design_tokens_str: str, model: str) -> str:
    from llm_direct import call_claude
    import re

    versoes_fmt = ""
    for i, (direcao_id, html) in enumerate(versoes.items(), 1):
        versoes_fmt += f"\n### Versão {i} — Direção: {direcao_id}\n{html[:3000]}\n"

    system = """Você é o Aggregator. Recebeu múltiplas versões de uma seção hero.
Sua tarefa:
1. Avaliar cada versão em: impacto visual, copy, mobile, performance, coerência com PRD
2. Escolher a MELHOR versão OU combinar os melhores elementos de cada uma
3. Retornar HTML final (versão escolhida ou combinação)

REGRAS:
- Se uma versão é claramente superior, retorne ela intacta
- Se cada versão tem pontos fortes diferentes, combine: layout da melhor + copy da melhor + CTA da melhor
- Ao combinar, manter coerência visual (não misturar estilos conflitantes)
- Retorne APENAS o HTML final da <section> hero, sem explicação, sem markdown"""

    user = f"""## PRD Hero:
{json.dumps(prd_hero, ensure_ascii=False)[:1000]}

## Tokens de Design:
{design_tokens_str[:300]}

## Versões para avaliar:
{versoes_fmt}

Avalie e retorne o HTML final da melhor hero."""

    resultado = call_claude(
        system=system, user=user, model=model,
        max_tokens=5000, temperature=0.3, agent_name='moa_aggregator'
    )

    resultado = resultado.strip()
    if resultado.startswith("```"):
        resultado = re.sub(r"^```\w*\n?", "", resultado)
        resultado = re.sub(r"\n?```$", "", resultado)

    return resultado
