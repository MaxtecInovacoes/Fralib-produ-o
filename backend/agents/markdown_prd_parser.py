"""
Parser de Markdown estruturado para PRD do ArquitetoMestre.
Substitui JSON como formato de output - mais robusto com LLMs.
"""
import re
import json
from typing import Dict, Any, Optional

from backend.agents._text_utils import strip_control_chars  # noqa: E402,F401  — B2 DRY


VALID_SECTIONS = ('hero', 'sobre', 'servicos', 'depoimentos', 'faq', 'localizacao', 'contato', 'footer')


def parse_bloco1_markdown(text: str) -> Dict[str, Any]:
    """
    Parse Bloco 1 (estrutura + direcao criativa) de Markdown para dict.

    Formato esperado:
    layout_type: brutalist
    business_name: Nome

    ## INSTRUCAO CRIATIVA
    (texto livre multi-linha)

    ## SECOES
    - hero | hero-split
    - sobre | sobre-grid
    - servicos | services-cards
    """
    result = {
        'business_name': '',
        'layout_type': 'corporate',
        'instrucao_criativa_para_dev': '',
        'sections': []
    }

    m = re.search(r'layout_type:\s*(.+)', text, re.IGNORECASE)
    if m:
        result['layout_type'] = m.group(1).strip()

    m = re.search(r'business_name:\s*(.+)', text, re.IGNORECASE)
    if m:
        result['business_name'] = m.group(1).strip()

    # Instrucao criativa: bloco entre ## INSTRUCAO CRIATIVA e ## SECOES
    m = re.search(r'##\s*INSTRUC.O\s*CRIATIVA\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL | re.IGNORECASE)
    if m:
        result['instrucao_criativa_para_dev'] = m.group(1).strip()
    else:
        m = re.search(r'instruc.o.criativa[^:]*:\s*(.*?)(?=\n##\s*SEC|\Z)', text, re.DOTALL | re.IGNORECASE)
        if m:
            result['instrucao_criativa_para_dev'] = m.group(1).strip()

    # Secoes: lista com formato "- nome | layout_type"
    secoes_block = re.search(r'##\s*SEC.ES\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL | re.IGNORECASE)
    if secoes_block:
        for line in secoes_block.group(1).strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('-'):
                continue
            line = line.lstrip('- ').strip()
            parts = [p.strip() for p in line.split('|')]
            nome = parts[0].lower() if parts else ''
            layout = parts[1].strip() if len(parts) > 1 else 'padrao'
            if nome:
                result['sections'].append({'name': nome, 'layout_type': layout, 'required': True})

    # Fallback: procurar lista em qualquer lugar do texto
    if not result['sections']:
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- ') and '|' in line:
                line = line.lstrip('- ').strip()
                parts = [p.strip() for p in line.split('|')]
                nome = parts[0].lower()
                layout = parts[1].strip() if len(parts) > 1 else 'padrao'
                if nome in VALID_SECTIONS:
                    result['sections'].append({'name': nome, 'layout_type': layout, 'required': True})

    return result


def parse_bloco2_markdown(text: str) -> Dict[str, Any]:
    """
    Parse Bloco 2 (copy por secao) de Markdown para dict.

    Formato esperado:
    ## hero
    h1: Texto do titulo
    subtitulo: Texto do subtitulo
    cta: Texto do botao
    eyebrow: Tag acima do h1

    ## sobre
    titulo: Texto
    descricao: Texto multi-linha

    ## depoimentos
    omitir: true
    """
    result = {'sections': []}

    # Split por ## (secoes)
    parts = re.split(r'^##\s+', text, flags=re.MULTILINE)

    for part in parts:
        if not part.strip():
            continue

        lines = part.strip().split('\n')
        nome_secao = lines[0].strip().lower()

        if nome_secao not in VALID_SECTIONS:
            continue

        copy = {}
        omitir = False
        current_key = None
        current_value = []

        for line in lines[1:]:
            stripped = line.strip()

            if stripped.lower().startswith('omitir:'):
                val = stripped.split(':', 1)[1].strip().lower()
                omitir = val in ('true', 'sim', '1', 'yes')
                continue

            # Detectar chave: valor (ex: h1, h2, subtitulo, cta)
            kv_match = re.match(r'^([a-z0-9_]+)\s*:\s*(.*)$', stripped, re.IGNORECASE)
            if kv_match and not stripped.startswith('-'):
                if current_key:
                    copy[current_key] = '\n'.join(current_value).strip()
                current_key = kv_match.group(1).lower()
                val = kv_match.group(2).strip()
                current_value = [val] if val else []
            elif stripped.startswith('- ') and current_key:
                current_value.append(stripped)
            elif current_key:
                current_value.append(stripped)

        if current_key:
            copy[current_key] = '\n'.join(current_value).strip()

        section = {'name': nome_secao, 'copy': copy}
        if omitir:
            section['omitir'] = True

        result['sections'].append(section)

    return result


def parse_bloco1_with_fallback(text: str) -> Optional[Dict[str, Any]]:
    """Tenta Markdown primeiro, fallback para JSON."""
    cleaned = text.strip()

    # Se comeca com {, tenta JSON primeiro
    if cleaned.startswith('{'):
        try:
            cleaned_json = strip_control_chars(cleaned)
            cleaned_json = cleaned_json.replace(' ', ' ').replace(' ', ' ')
            data = json.loads(cleaned_json)
            return data
        except Exception:
            pass

    # Tenta Markdown
    result = parse_bloco1_markdown(text)
    if result['sections'] and result['instrucao_criativa_para_dev']:
        return result

    # Fallback: tenta extrair JSON de dentro do texto
    try:
        # Remover markdown code blocks
        no_blocks = re.sub(r'```json\s*', '', text)
        no_blocks = re.sub(r'```\s*', '', no_blocks)
        json_match = re.search(r'\{.*\}', no_blocks, re.DOTALL)
        if json_match:
            cleaned_json = strip_control_chars(json_match.group())
            data = json.loads(cleaned_json)
            return data
    except Exception:
        pass

    # Se Markdown parcial, retorna o que tem
    if result['sections'] or result['instrucao_criativa_para_dev']:
        return result

    return None


def parse_bloco2_with_fallback(text: str) -> Optional[Dict[str, Any]]:
    """Tenta Markdown primeiro, fallback para JSON."""
    cleaned = text.strip()

    if cleaned.startswith('{'):
        try:
            cleaned_json = strip_control_chars(cleaned)
            cleaned_json = cleaned_json.replace(' ', ' ').replace(' ', ' ')
            data = json.loads(cleaned_json)
            return data
        except Exception:
            pass

    result = parse_bloco2_markdown(text)
    if result['sections']:
        return result

    try:
        no_blocks = re.sub(r'```json\s*', '', text)
        no_blocks = re.sub(r'```\s*', '', no_blocks)
        json_match = re.search(r'\{.*\}', no_blocks, re.DOTALL)
        if json_match:
            cleaned_json = strip_control_chars(json_match.group())
            data = json.loads(cleaned_json)
            return data
    except Exception:
        pass

    return None
