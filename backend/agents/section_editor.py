"""Section editor — edição de seções HTML via LLM."""

import re


def editar_secao(html: str, secao: str, instrucao: str) -> str:
    from llm_direct import call_claude

    pattern = rf"<!--\s*SECTION:\s*{secao}\s*-->(.*?)<!--\s*/SECTION:\s*{secao}\s*-->"
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if not match:
        print("[SectionEditor] Secao nao encontrada: " + secao)
        secoes = re.findall(r"<!-- SECTION:(\w+) -->", html)
        print("[SectionEditor] Secoes disponiveis: " + str(secoes))
        return html
    bloco_original = match.group(0)
    conteudo = match.group(1).strip()
    print(
        "[SectionEditor] Editando secao "
        + secao
        + " ("
        + str(len(conteudo))
        + " chars)..."
    )
    prompt = "REGRAS ABSOLUTAS:\n"
    prompt += "1. Voce e um compilador estrito. Sua UNICA funcao e corrigir erros de sintaxe (tags HTML nao fechadas) apontados na auditoria.\n"
    prompt += "2. E ESTRITAMENTE PROIBIDO adicionar novos textos, imagens, SVGs ou mudar as classes Tailwind originais.\n"
    prompt += "3. E ESTRITAMENTE PROIBIDO reescrever o design. Mantenha o codigo original intacto, adicionando APENAS os caracteres exatos que faltavam para fechar as tags.\n"
    prompt += "4. Retorne APENAS o HTML corrigido, sem markdown, sem explicacoes.\n\n"
    prompt += "PROBLEMA A CORRIGIR: " + instrucao + "\n\n"
    prompt += "BLOCO ATUAL (corrija apenas o necessario):\n" + conteudo + "\n\n"
    prompt += (
        "Retorne apenas o HTML interno do bloco corrigido (sem delimitadores SECTION)."
    )
    html_editado = call_claude(
        system=(
            "You are a strict HTML compiler. Fix ONLY syntax errors. "
            "NEVER rewrite, expand, or redesign. Return ONLY HTML.\n"
            "All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."
        ),
        user=prompt,
        model="haiku",
        max_tokens=8000,
        temperature=0.0,
        agent_name="section_editor",
    )
    _match = re.search(
        r"```html\s*(.*?)\s*```", html_editado, re.DOTALL | re.IGNORECASE
    )
    if _match:
        html_editado = _match.group(1).strip()
    else:
        html_editado = html_editado.replace("```html", "").replace("```", "").strip()
    _first_tag = re.search(r"<[a-zA-Z]", html_editado)
    if _first_tag and _first_tag.start() > 0:
        html_editado = html_editado[_first_tag.start() :]
    novo_bloco = (
        "<!-- SECTION:"
        + secao
        + " -->\n"
        + html_editado
        + "\n<!-- /SECTION:"
        + secao
        + " -->"
    )
    html_final = html.replace(bloco_original, novo_bloco)
    print("[SectionEditor] Secao " + secao + " editada com sucesso")
    return html_final


def listar_secoes(html: str) -> list:
    return re.findall(r"<!-- SECTION:(\w+) -->", html)
