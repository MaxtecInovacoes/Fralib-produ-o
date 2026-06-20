"""
Validation Layer - Auto-retry se output invalido
Baseado em Vercel v0 + Lovable.dev
"""

import re
from typing import List, Tuple

# Cores genericas proibidas
CORES_PROIBIDAS = [
    '#3b82f6', '#2563eb', '#60a5fa',  # Azuis genericos
    '#1e40af', '#1d4ed8', '#3730a3',  # Azuis escuros genericos
]

def validar_prd(prd_json: dict) -> Tuple[bool, List[str]]:
    """
    Valida PRD do Designer
    Retorna (valido, lista_erros)
    """
    erros = []

    # Validar cores
    cores = prd_json.get('cores', {})

    if not cores:
        erros.append("PRD sem cores definidas")

    for nome_cor, valor_cor in cores.items():
        if valor_cor.lower() in CORES_PROIBIDAS:
            erros.append(f"Cor generica detectada: {nome_cor}={valor_cor} (PROIBIDO)")

    # Validar dark mode
    if not prd_json.get('dark_mode', False):
        erros.append("Dark mode nao implementado (OBRIGATORIO)")

    # Validar headline
    headline = prd_json.get('headline', '')
    if not headline:
        erros.append("Headline vazia")
    elif len(headline) < 30:
        erros.append("Headline muito curta (minimo 30 chars)")

    # Validar cidade na headline
    cidade = prd_json.get('cidade', '')
    if cidade and cidade.lower() not in headline.lower():
        erros.append(f"Headline sem cidade ({cidade})")

    return len(erros) == 0, erros

def validar_html(html: str, prd_json: dict) -> Tuple[bool, List[str]]:
    """
    Valida HTML gerado pelo renderer
    Retorna (valido, lista_erros)
    """
    erros = []
    html_lower = html.lower()

    # Validar cores proibidas no HTML
    for cor_proibida in CORES_PROIBIDAS:
        if cor_proibida in html_lower:
            erros.append(f"Cor generica no HTML: {cor_proibida} (PROIBIDO)")

    # Validar dark mode
    if 'prefers-color-scheme: dark' not in html_lower:
        erros.append("Dark mode nao implementado no HTML (OBRIGATORIO)")

    # Validar prefers-reduced-motion
    if 'prefers-reduced-motion' not in html_lower:
        erros.append("prefers-reduced-motion nao implementado (OBRIGATORIO)")

    # Validar lazy loading
    if '<img' in html_lower and 'loading="lazy"' not in html_lower and 'loading=lazy' not in html_lower:
        erros.append("Imagens sem lazy loading (OBRIGATORIO)")

    # Validar alt text
    img_tags = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
    if img_tags:
        imgs_sem_alt = [img for img in img_tags if 'alt=' not in img.lower()]
        if imgs_sem_alt:
            erros.append(f"{len(imgs_sem_alt)} imagens sem alt text (OBRIGATORIO)")

    # Validar cores do PRD aplicadas
    cores_prd = prd_json.get('cores', {})
    if cores_prd:
        cor_primaria = cores_prd.get('primaria', '')
        if cor_primaria and cor_primaria.lower() not in html_lower:
            erros.append(f"Cor primaria do PRD ({cor_primaria}) nao aplicada no HTML")

    return len(erros) == 0, erros

def gerar_prompt_retry(erros: List[str]) -> str:
    """
    Gera prompt de retry com erros encontrados
    """
    erros_formatados = '\n'.join([f"- {erro}" for erro in erros])

    return f"""
ATENCAO: Sua resposta anterior foi REJEITADA pelos seguintes motivos:

{erros_formatados}

CORRIJA esses erros e gere novamente seguindo os MANDATORY CONSTRAINTS.
"""

def calcular_score_validacao(prd_valido: bool, html_valido: bool, erros_prd: List[str], erros_html: List[str]) -> dict:
    """
    Calcula score de validacao
    """
    total_erros = len(erros_prd) + len(erros_html)

    return {
        'prd_valido': prd_valido,
        'html_valido': html_valido,
        'total_erros': total_erros,
        'erros_prd': erros_prd,
        'erros_html': erros_html,
        'score': 100 - (total_erros * 10),  # -10 pontos por erro
        'aprovado': prd_valido and html_valido
    }
