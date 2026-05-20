"""
Liam Constitutional AI — Auto-crítica antes de enviar pra Liz
PRD #5: Generate → Self-Critique → Revise → Entrega

Padrão: Constitutional AI (Anthropic) — agente critica contra princípios fixos.
Usa Haiku pra crítica (barato), Opus pra revisão (só se necessário).
"""

import json
import re

CONSTITUICAO_LIAM = [
    {
        "id": "C2_SEM_FICCAO",
        "regra": "PROIBIDO inventar depoimentos, nomes de clientes, estatísticas ou histórias. Se não veio no PRD, não existe.",
        "severidade": "critica",
        "fix_hint": "Remover conteúdo fictício. Usar apenas dados do PRD ou depoimentos reais do Google Maps"
    },
    {
        "id": "C3_CORES_TOKEN",
        "regra": "Todas as cores DEVEM vir dos tokens CSS fornecidos. Proibido hex/rgb hardcoded fora da paleta.",
        "severidade": "alta",
        "fix_hint": "Substituir cores hardcoded por variáveis CSS dos tokens"
    },
    {
        "id": "C4_CTA_ACAO",
        "regra": "Todo CTA deve ter verbo de ação + benefício. Proibido: 'Saiba mais', 'Clique aqui', 'Veja mais'. Correto: 'Agende seu horário', 'Garanta sua vaga'.",
        "severidade": "alta",
        "fix_hint": "Reescrever CTA com verbo imperativo + benefício claro"
    },
    {
        "id": "C5_MOBILE_OVERFLOW",
        "regra": "Nenhum elemento pode ter width fixo > 100%. Usar max-width, %, vw, ou clamp(). Proibido: width: 500px sem max-width.",
        "severidade": "alta",
        "fix_hint": "Converter width fixo para max-width ou unidades relativas"
    },
    {
        "id": "C6_LAZY_LOADING",
        "regra": "Toda <img> abaixo do fold (não hero) DEVE ter loading='lazy'. Hero pode ter loading='eager'.",
        "severidade": "media",
        "fix_hint": "Adicionar loading='lazy' nas imgs que não são hero"
    },
    {
        "id": "C7_CONTRASTE",
        "regra": "Texto sobre fundo escuro deve usar cor clara. Texto sobre fundo claro deve usar cor escura. Nunca texto escuro sobre fundo escuro.",
        "severidade": "alta",
        "fix_hint": "Ajustar cor do texto para garantir contraste com fundo"
    },
    {
        "id": "C8_SEMANTICA",
        "regra": "Usar tags semânticas: <section>, <article>, <nav>, <header>, <footer>, <main>. Proibido div-soup sem semântica.",
        "severidade": "media",
        "fix_hint": "Substituir divs genéricos por tags semânticas apropriadas"
    },
    {
        "id": "C9_FRASES_GENERICAS",
        "regra": "Proibido: 'Somos uma empresa comprometida com a qualidade', 'Nosso diferencial é o atendimento', 'Trabalhamos com excelência'. Copy deve ser específico ao negócio.",
        "severidade": "alta",
        "fix_hint": "Reescrever com dados específicos do negócio (nome, localização, serviços reais)"
    },
    {
        "id": "C10_ALT_TEXT",
        "regra": "Toda <img> DEVE ter atributo alt descritivo. Proibido: alt='' ou alt ausente (exceto imagens decorativas com role='presentation').",
        "severidade": "media",
        "fix_hint": "Adicionar alt descritivo relevante ao contexto da seção"
    }
]

_SEVERIDADE_MAP = {c["id"]: c["severidade"] for c in CONSTITUICAO_LIAM}


def _severidade(violacao_id: str) -> str:
    return _SEVERIDADE_MAP.get(violacao_id, "media")


def auto_critica_constitucional(html_secao: str, nome_secao: str, design_tokens_str: str = "") -> dict:
    """
    Liam critica seu próprio output contra a constituição.
    Usa Haiku (barato). Retorna violações encontradas.

    Returns:
        {
            "violacoes": [...],
            "violacoes_graves": [...],
            "passou": bool,
            "total_violacoes": int
        }
    """
    from llm_direct import call_claude

    constituicao_filtrada = CONSTITUICAO_LIAM

    constituicao_texto = "\n".join([
        f"- [{c['id']}] ({c['severidade']}): {c['regra']}"
        for c in constituicao_filtrada
    ])

    system = f"""Você é o crítico interno do Liam. Analise o HTML e identifique VIOLAÇÕES da constituição abaixo.

CONSTITUIÇÃO:
{constituicao_texto}

REGRAS DO CRÍTICO:
- Só reporte violações REAIS e ESPECÍFICAS (cite o trecho exato)
- Se não há violações, retorne lista vazia
- Não invente problemas. Seja preciso.
- Severidade "critica" = DEVE corrigir. "alta" = DEVERIA corrigir. "media" = BOM corrigir.

Retorne APENAS JSON válido (sem markdown, sem ```):
{{
    "violacoes": [
        {{"id": "C2_SEM_FICCAO", "trecho": "trecho problemático curto", "fix": "como corrigir"}}
    ]
}}"""

    user = f"""## Seção: {nome_secao}
## Tokens de design: {design_tokens_str[:500] if design_tokens_str else 'N/A'}

HTML:
{html_secao[:4000]}

Analise contra a constituição. Liste violações encontradas."""

    try:
        resposta = call_claude(system=system, user=user, model='haiku', max_tokens=1500, temperature=0.2, agent_name='liam_critica')
        resposta = resposta.strip()
        if resposta.startswith("```"):
            resposta = re.sub(r"^```\w*\n?", "", resposta)
            resposta = re.sub(r"\n?```$", "", resposta)
        resultado = json.loads(resposta)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[CONSTITUTIONAL] Parse falhou: {e} — considerando PASSOU")
        return {"violacoes": [], "violacoes_graves": [], "passou": True, "total_violacoes": 0}

    violacoes = resultado.get("violacoes", [])
    violacoes_graves = [v for v in violacoes if _severidade(v.get("id", "")) in ("critica", "alta")]

    return {
        "violacoes": violacoes,
        "violacoes_graves": violacoes_graves,
        "passou": len(violacoes_graves) == 0,
        "total_violacoes": len(violacoes),
    }


def auto_revisar_constitucional(html_secao: str, violacoes: list, nome_secao: str) -> str:
    """
    Liam corrige violações encontradas pela auto-crítica.
    Só chamada se auto_critica encontrou violações graves.
    Usa Opus (mesmo modelo que gerou).

    Returns: HTML corrigido
    """
    from llm_direct import call_claude

    violacoes_texto = "\n".join([
        f"- [{v.get('id','')}] Trecho: '{v.get('trecho','')[:80]}' → Fix: {v.get('fix','')}"
        for v in violacoes
    ])

    system = """Você é Liam. Corrija EXATAMENTE as violações listadas no HTML abaixo.

REGRAS:
- Corrija APENAS o que foi apontado. Não mude mais nada.
- Mantenha estrutura, classes, IDs intactos.
- Se a correção é remover algo fictício, remova sem substituir por outro fictício.
- Retorne APENAS o HTML completo da seção corrigido (sem explicação, sem markdown)."""

    user = f"""## Seção: {nome_secao}

## Violações a corrigir:
{violacoes_texto}

## HTML atual:
{html_secao}

Corrija e retorne HTML completo."""

    resposta = call_claude(system=system, user=user, model='opus', max_tokens=8000, temperature=0.3, agent_name='liam_revisao')

    # Limpar markdown se veio
    resposta = resposta.strip()
    if resposta.startswith("```"):
        resposta = re.sub(r"^```\w*\n?", "", resposta)
        resposta = re.sub(r"\n?```$", "", resposta)

    return resposta


def constitutional_pass(html_secao: str, nome_secao: str, design_tokens_str: str = "") -> str:
    """
    Fluxo completo: Auto-crítica → Auto-revisão (se necessário).
    Chamado após Liam gerar cada seção.

    Returns: HTML (original se passou, corrigido se tinha violações)
    """
    # Seções pequenas (footer, lgpd) — skip
    if len(html_secao) < 200:
        return html_secao

    # 1. Auto-crítica (Haiku)
    critica = auto_critica_constitucional(html_secao, nome_secao, design_tokens_str)

    if critica["passou"]:
        print(f"[CONSTITUTIONAL] {nome_secao} | PASSOU | 0 violações graves")
        return html_secao

    # 2. Auto-revisão (Opus)
    n_graves = len(critica["violacoes_graves"])
    ids = [v.get("id", "?") for v in critica["violacoes_graves"]]
    print(f"[CONSTITUTIONAL] {nome_secao} | {n_graves} violações | corrigindo... {ids}")

    html_corrigido = auto_revisar_constitucional(html_secao, critica["violacoes_graves"], nome_secao)

    # Anti-bloat
    if len(html_corrigido) > len(html_secao) * 1.15:
        print(f"[CONSTITUTIONAL][WARN] {nome_secao} | revisão inflou >15% | mantendo original")
        return html_secao

    # Anti-shrink
    if len(html_corrigido) < len(html_secao) * 0.5:
        print(f"[CONSTITUTIONAL][WARN] {nome_secao} | revisão encolheu >50% | mantendo original")
        return html_secao

    print(f"[CONSTITUTIONAL] {nome_secao} | corrigida | {ids}")
    return html_corrigido
