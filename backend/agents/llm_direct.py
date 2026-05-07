import os
import requests
import json
from dotenv import load_dotenv

# Carregar .env — tenta multiplos caminhos para garantir que encontra
import pathlib as _pathlib
_env_paths = [
    '/root/fralib/.env',
    str(_pathlib.Path(__file__).parent.parent.parent / '.env'),
    str(_pathlib.Path(__file__).parent.parent / '.env'),
]
for _env_path in _env_paths:
    if _pathlib.Path(_env_path).exists():
        load_dotenv(_env_path, override=True)
        break
else:
    load_dotenv()  # fallback

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud')

def call_claude(system, user, model='opus', max_tokens=4000, temperature=0.7, agent_name=None, base_url=None):
    """
    Chama Claude API com suporte automático a RAG e Skills
    
    Args:
        system: System prompt
        user: User prompt
        model: 'opus', 'sonnet' ou 'haiku'
        max_tokens: Limite de tokens
        temperature: Temperatura (0.0-1.0)
        agent_name: Nome do agente (ex: 'Caio', 'Liam') - ativa RAG + Skills automaticamente
    
    Returns:
        Resposta do Claude
    """
    
    # ✅ AUTOMÁTICO: Se agent_name foi passado, ativar RAG + Skills
    if agent_name:
        try:
            # 1. Importar funções (lazy import para não quebrar se não existir)
            from agent_rag import buscar_contexto_rag, format_rag_prompt, mark_rag_used
            from skill_loader import get_skills_agente, carregar_skills
            
            # 2. Buscar e injetar RAG
            rag_context = buscar_contexto_rag(user, agent_name.lower())
            if rag_context:
                user = format_rag_prompt(user, rag_context)
                mark_rag_used(agent_name)
                print(f"[LLM Direct] ✅ RAG ativado para {agent_name}")
            
            # 3. Buscar e injetar Skills
            skills = get_skills_agente(agent_name.lower())
            if skills:
                guidelines = carregar_skills(skills)
                if guidelines:
                    system = f"{system}\n\n{'='*60}\n# SKILLS ATIVADAS\n{'='*60}\n{guidelines}"
                    print(f"[LLM Direct] ✅ Skills ativadas para {agent_name}: {', '.join(skills)}")
        
        except Exception as e:
            print(f"[LLM Direct] ⚠️ Erro ao ativar RAG/Skills para {agent_name}: {e}")
            # Continua sem RAG/Skills se der erro
    
    # 4. Mapear modelo
    model_map = {
        'opus': 'claude-opus-4-7',
        'sonnet': 'claude-sonnet-4-6',
        'haiku': 'claude-haiku-4-5'
    }
    
    model_id = model_map.get(model, model_map['opus'])
    
    # 5. Chamar API Claude
    _base = base_url or ANTHROPIC_BASE_URL
    url = f'{_base}/v1/messages'
    
    headers = {
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'messages': [{'role': 'user', 'content': user}]
    }

    import time as _llm_time
    for _llm_attempt in range(1, 4):
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code == 429:
            wait = 15 * _llm_attempt
            print(f'[LLM] 429 Rate Limit - aguardando {wait}s (tentativa {_llm_attempt}/3)...')
            _llm_time.sleep(wait)
            continue
        if response.status_code in (529, 503, 502):
            wait = 20 * _llm_attempt
            print(f'[LLM] {response.status_code} Proxy Overloaded - aguardando {wait}s (tentativa {_llm_attempt}/3)...')
            _llm_time.sleep(wait)
            continue
        if response.status_code == 400:
            print(f'[LLM] 400 Bad Request - payload pode ser grande demais, tentativa {_llm_attempt}/3')
            if _llm_attempt < 3:
                _llm_time.sleep(5 * _llm_attempt)
                continue
        response.raise_for_status()
        break

    data = response.json()
    stop_reason = data.get('stop_reason', '?')
    usage = data.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    print(f"[LLM] stop_reason={stop_reason} input={input_tokens} output={output_tokens}")

    # O proxy aibee.cloud sempre adiciona bloco tool_use extra no final
    # Extrair texto IMEDIATAMENTE se houver bloco text (ignorar tool_use)
    for block in data.get('content', []):
        if block.get('type') == 'text':
            return block['text']

    # Sem bloco text — retry apenas se nao ha texto algum
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        retry_count += 1
        import time; time.sleep(2 * retry_count)
        print('[LLM] Retry ' + str(retry_count) + '/3 - sem bloco text, retentando')
        payload_retry = {k: v for k, v in payload.items() if k != 'tools' and k != 'tool_choice'}
        response2 = requests.post(url, headers=headers, json=payload_retry, timeout=600)
        response2.raise_for_status()
        data = response2.json()
        stop_reason = data.get('stop_reason', '?')
        usage = data.get('usage', {})
        output_tokens = usage.get('output_tokens', 0)
        print('[LLM] Retry ' + str(retry_count) + ': stop=' + stop_reason + ' out=' + str(output_tokens))
        for block in data.get('content', []):
            if block.get('type') == 'text':
                return block['text']

    # Ultimo fallback: procurar qualquer bloco com chave 'text'
    for block in data.get('content', []):
        if 'text' in block:
            return block['text']

    # Ultimo fallback: tentar extrair texto do input do no_tool_available
    for block in data.get('content', []):
        if block.get('name') == 'no_tool_available':
            inp = block.get('input', {})
            if isinstance(inp, dict):
                # Tentar campos comuns onde o proxy pode ter colocado o texto
                for key in ['text', 'content', 'response', 'message', 'output']:
                    if key in inp and inp[key]:
                        print(f"[LLM] Recuperado de no_tool_available.input.{key}")
                        return str(inp[key])
            elif isinstance(inp, str) and inp:
                print("[LLM] Recuperado de no_tool_available.input (string)")
                return inp
    print(f"[LLM] ERRO: nenhum bloco text encontrado. content={data.get('content', [])}")
    return ""  


def call_claude_structured(system, user, tool_name, tool_description, input_schema, model='opus', max_tokens=8000, temperature=0.7):
    """
    Chama Claude com tool_use para forcar retorno de JSON estruturado exato.
    O Claude e obrigado a preencher o schema definido - sem texto livre.

    Args:
        system: System prompt
        user: User prompt
        tool_name: Nome da tool (ex: 'gerar_prd')
        tool_description: Descricao da tool
        input_schema: JSON Schema dict com os campos obrigatorios
        model: 'opus', 'sonnet' ou 'haiku'
        max_tokens: Limite de tokens
        temperature: Temperatura

    Returns:
        Dict com os campos retornados pelo Claude
    """
    model_map = {
        'opus': 'claude-opus-4-7',
        'sonnet': 'claude-sonnet-4-6',
        'haiku': 'claude-haiku-4-5'
    }
    model_id = model_map.get(model, model_map['opus'])

    url = f'{ANTHROPIC_BASE_URL}/v1/messages'
    headers = {
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'tools': [{
            'name': tool_name,
            'description': tool_description,
            'input_schema': input_schema
        }],
        'tool_choice': {'type': 'tool', 'name': tool_name},
        'messages': [{'role': 'user', 'content': user}]
    }

    import time as _time_struct
    for _attempt in range(1, 4):
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code == 429:
            wait = 15 * _attempt
            print(f'[LLM Structured] 429 Rate Limit - aguardando {wait}s (tentativa {_attempt}/3)...')
            _time_struct.sleep(wait)
            continue
        response.raise_for_status()
        data = response.json()
        # Verificar se proxy retornou no_tool_available (falso tool_use)
        content_blocks = data.get('content', [])
        has_fake = any(b.get('name') == 'no_tool_available' for b in content_blocks)
        for block in content_blocks:
            if block.get('type') == 'tool_use' and block.get('name') == tool_name:
                return block['input']
        if has_fake and _attempt < 3:
            print(f'[LLM Structured] Proxy retornou no_tool_available, tentativa {_attempt}/3...')
            _time_struct.sleep(3 * _attempt)
            continue
        break
    raise ValueError(f'Claude nao retornou tool_use para {tool_name} apos 3 tentativas')
