import sys
sys.path.insert(0, "/app/backend/agents")
"""
Theo - Estrategista / PRD + Jina AI Research
"""
import os
import json
import re
import requests
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional
from llm_direct import call_claude
from agent_rag import format_rag_prompt, get_agent_temperature
from skill_loader import get_skills_agente, carregar_skills
from designer_prd import DesignerPRD, AnimationSpec, SectionSpec, ColorPalette

def clean_json_response(text: str) -> str:
    """Remove markdown, control chars e extrai o MAIOR JSON valido do texto"""
    import re as _rcj
    bt = chr(96)
    text = text.replace(bt*3 + "json", "").replace(bt*3, "").strip()
    # Remover caracteres de controle invalidos em JSON (manter tab=9, newline=10, cr=13)
    text = _rcj.sub(r"[" + chr(0) + "-" + chr(8) + chr(11) + chr(12) + chr(14) + "-" + chr(31) + chr(127) + "]", "", text)

    # Encontrar TODOS os JSONs e retornar o maior
    candidates = []
    i = 0
    while i < len(text):
        if text[i] != '{':
            i += 1
            continue
        start_idx = i
        depth = 0
        in_string = False
        escape_next = False
        j = i
        while j < len(text):
            ch = text[j]
            if escape_next:
                escape_next = False
                j += 1
                continue
            if ch == chr(92) and in_string:
                escape_next = True
                j += 1
                continue
            if ch == chr(34):
                in_string = not in_string
                j += 1
                continue
            if in_string:
                j += 1
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidates.append(text[start_idx:j+1])
                    break
            j += 1
        i += 1

    if not candidates:
        return text

    # Retornar o maior JSON encontrado
    return max(candidates, key=len)



# ===== MODELOS PYDANTIC (importados de designer_prd.py) =====
# ===== JINA AI INTEGRATION =====

def pesquisar_referencias_jina(segmento: str, cidade: str = '') -> str:
    """
    Espia de performance: analisa sites que estao retendo e convertendo
    no nicho. Extrai o que faz o usuario ficar e agir para modelar no site.
    Cache de 48h por segmento+cidade para evitar rate limit 429.
    """
    import os, time, hashlib
    _cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jina_cache")
    os.makedirs(_cache_dir, exist_ok=True)
    _cache_key = hashlib.md5((segmento.lower() + cidade.lower()).encode()).hexdigest()[:12]
    _cache_file = os.path.join(_cache_dir, f"jina_{_cache_key}.txt")
    _TTL = 48 * 3600  # 48 horas
    if os.path.exists(_cache_file) and (time.time() - os.path.getmtime(_cache_file)) < _TTL:
        print("[Jina AI] Cache HIT para segmento: " + segmento)
        with open(_cache_file, "r", encoding="utf-8") as _f:
            return _f.read()

    # Queries de design premium por nicho — focadas em UI/UX, nao em grandes redes
    QUERIES_DESIGN_NICHO = {
        "academia":     "academia independente site design premium UI UX moderno brasil",
        "crossfit":     "crossfit box site design premium dark energetico UI UX",
        "gym":          "gym fitness studio site design premium moderno UI UX brasil",
        "fitness":      "personal trainer studio fitness site design premium UI UX",
        "musculacao":   "musculacao studio site design premium dark energetico UI UX",
        "barbearia":    "barbearia premium site design moderno masculino UI UX brasil",
        "salao":        "salao de beleza premium site design elegante UI UX brasil",
        "clinica":      "clinica medica site design premium clean profissional UI UX",
        "odontologica": "clinica odontologica site design premium clean UI UX brasil",
        "dentista":     "dentista consultorio site design premium moderno UI UX",
        "estetica":     "clinica estetica site design premium luxuoso UI UX brasil",
        "restaurante":  "restaurante local site design premium gastronomia UI UX brasil",
        "lanchonete":   "lanchonete artesanal site design premium moderno UI UX",
        "padaria":      "padaria artesanal site design premium aconchegante UI UX",
        "confeitaria":  "confeitaria artesanal site design premium elegante UI UX",
        "cafe":         "cafeteria independente site design premium aconchegante UI UX",
        "advocacia":    "escritorio advocacia site design premium sober UI UX brasil",
        "imobiliaria":  "imobiliaria boutique site design premium moderno UI UX",
        "escola":       "escola curso site design premium moderno educacao UI UX",
        "farmacia":     "farmacia manipulacao site design premium clean UI UX brasil",
        "pet":          "petshop veterinaria site design premium moderno UI UX brasil",
        "auto":         "oficina mecanica site design premium moderno UI UX brasil",
        "nutricionista":"nutricionista site design premium clean saude UI UX brasil",
        "psicologia":   "psicologo clinica site design premium acolhedor UI UX brasil",
        "arquitetura":  "escritorio arquitetura site design premium portfolio UI UX",
        "fotografia":   "fotografo site design premium portfolio visual UI UX brasil",
    }

    seg_lower = segmento.lower()
    query = None
    for key, q in QUERIES_DESIGN_NICHO.items():
        if key in seg_lower:
            query = q
            break

    if not query:
        query = segmento + " site design premium UI UX moderno brasil"

    if cidade:
        query = query + " " + cidade

    print("[Jina AI] Query de design: " + query)

    # Buscar via Google Search pelo Jina — sites reais do nicho, nao grandes redes
    sites_ref = []
    EXCLUIR = [
        "google", "facebook", "instagram", "youtube", "linkedin", "twitter",
        "smartfit", "bodytech", "bluefit", "mcdonalds", "starbucks", "outback",
        "giraffas", "subway", "burger", "sorridents", "odontoprev", "drogasil",
        "drogaraia", "cobasi", "petz", "petlove", "kumon", "wizard", "ccaa",
        "quintoandar", "vivareal", "zapimoveis", "localiza", "movida", "unidas",
        "wix.com", "wordpress.com", "blogspot", "squarespace", "webflow.io",
        "maps", "wikipedia", "amazon", "mercadolivre", "ifood",
    ]
    try:
        search_url = "https://r.jina.ai/https://www.google.com/search?q=" + requests.utils.quote(query)
        headers_search = {"X-Return-Format": "markdown", "X-Timeout": "15"}
        if jina_key := os.getenv("JINA_API_KEY"):
            headers_search["Authorization"] = f"Bearer {jina_key}"
        response = requests.get(search_url, headers=headers_search, timeout=20)
        if response.status_code == 200:
            for line in response.text.split(chr(10)):
                if "http" in line:
                    url_match = re.search(r"https?://[^\s\)\"\x27]+", line)
                    if url_match:
                        url = url_match.group(0).rstrip(".,)")
                        url_lower = url.lower()
                        if not any(exc in url_lower for exc in EXCLUIR):
                            if url not in sites_ref and len(url) > 15:
                                sites_ref.append(url)
                                if len(sites_ref) >= 3:
                                    break
    except Exception as e:
        print("[Jina AI] Erro busca Google: " + str(e))

    if not sites_ref:
        return "Jina AI: Sem referencias. Usar padroes premium do segmento " + segmento + "."

    print("[Jina AI] Analisando " + str(len(sites_ref)) + " referencias para " + segmento)

    insights = []
    headers_site = {"X-Return-Format": "markdown", "X-Timeout": "15"}
    if jina_key := os.getenv("JINA_API_KEY"):
        headers_site["Authorization"] = f"Bearer {jina_key}"

    for i, site_url in enumerate(sites_ref, 1):
        try:
            print("[Jina AI] Referencia " + str(i) + ": " + site_url)
            resp = requests.get("https://r.jina.ai/" + site_url, headers=headers_site, timeout=15)
            if resp.status_code == 200:
                content = resp.text[:3000]
                insights.append("**Referencia " + str(i) + " (" + site_url + "):**" + chr(10) + content + chr(10))
                print("[Jina AI] OK: " + str(len(content)) + " chars")
        except Exception as e:
            print("[Jina AI] Erro " + site_url + ": " + str(e))

    if not insights:
        return "Jina AI: Referencias sem conteudo. Usar padroes premium do segmento."

    header = (
        "INTELIGENCIA DE MERCADO - NICHO: " + segmento.upper() + " | CIDADE: " + (cidade or "Brasil").upper() + chr(10) + chr(10) +
        "Voce e um especialista em marketing digital e SEO. Analise os sites abaixo e responda OBRIGATORIAMENTE:" + chr(10) + chr(10) +
        "## 1. CONCORRENTES PRINCIPAIS" + chr(10) +
        "Quem sao os principais concorrentes do nicho " + segmento + " com presenca digital forte no Brasil?" + chr(10) +
        "Para cada um: nome, URL, por que estao dominando, qual diferencial os destaca." + chr(10) + chr(10) +
        "## 2. PALAVRAS-CHAVE QUE ESTAO GERANDO DINHEIRO AGORA" + chr(10) +
        "Quais palavras-chave esses concorrentes estao ranqueando e que geram conversao real?" + chr(10) +
        "Separe em 3 grupos:" + chr(10) +
        "- ALTA INTENCAO DE COMPRA: termos que indicam cliente pronto para contratar (ex: 'nutricionista consulta online', 'nutricionista perto de mim')" + chr(10) +
        "- INFORMACIONAL: termos de pesquisa educativa que atraem trafego (ex: 'como emagrecer com nutricionista')" + chr(10) +
        "- LOCAL: termos com cidade/bairro (ex: 'nutricionista " + (cidade or "sua cidade") + "')" + chr(10) + chr(10) +
        "## 3. VOLUME E TENDENCIA" + chr(10) +
        "Quais desses termos tem maior volume de busca no Brasil agora?" + chr(10) +
        "Ordene do maior para o menor volume estimado. Indique quais estao em alta." + chr(10) + chr(10) +
        "## 4. COPY E CONVERSAO" + chr(10) +
        "1. HOOK DO HERO: headline que para o scroll em 3 segundos para " + segmento + chr(10) +
        "2. CTA PRINCIPAL: texto exato que converte neste nicho" + chr(10) +
        "3. PROVA SOCIAL: como os lideres exibem rating e depoimentos" + chr(10) +
        "4. DIFERENCIAIS QUE CONVERTEM: 3-5 frases de valor que geram cliques" + chr(10) + chr(10) +
        "## 5. DESIGN E VIBE VISUAL" + chr(10) +
        "5. PALETA DOMINANTE: cores de fundo, texto, botoes CTA dos lideres" + chr(10) +
        "6. TOM VISUAL: dark/light, minimalista/denso, energetico/elegante/clinico" + chr(10) +
        "7. O QUE NENHUM SITE DO NICHO FAZ: oportunidade de diferenciacao" + chr(10) + chr(10)
    )

    result = header + chr(10).join(insights)
    # Extrair FAQ e keywords estruturados via LLM
    try:
        from llm_direct import call_claude
        _faq_prompt = (
            "Analise o conteudo abaixo de sites do nicho '" + segmento + "' e extraia:\n"
            "1. FAQ_QUESTIONS: lista de 6 perguntas frequentes reais que clientes fazem (formato JSON array de strings)\n"
            "2. SEO_KEYWORDS: lista de 10 termos de busca reais do nicho (formato JSON array de strings)\n"
            "3. VALUE_PROPS: lista de 4 diferenciais que convertem (formato JSON array de strings)\n"
            "Retorne APENAS JSON valido: {\"faq_questions\": [...], \"seo_keywords\": [...], \"value_props\": [...]}\n\n"
            + chr(10).join(insights)[:4000]
        )
        _faq_resp = call_claude(
            system="Voce extrai dados estruturados de conteudo web. Retorne APENAS JSON valido sem markdown.",
            user=_faq_prompt,
            model="sonnet",
            max_tokens=1000,
            temperature=0.1,
        )
        import json as _json
        _faq_data = _json.loads(_faq_resp.strip())
        # Append structured data to result
        result += chr(10) + chr(10) + "=== DADOS ESTRUTURADOS PARA SEO ===" + chr(10)
        result += "FAQ_QUESTIONS: " + _json.dumps(_faq_data.get('faq_questions', []), ensure_ascii=False) + chr(10)
        result += "SEO_KEYWORDS: " + _json.dumps(_faq_data.get('seo_keywords', []), ensure_ascii=False) + chr(10)
        result += "VALUE_PROPS: " + _json.dumps(_faq_data.get('value_props', []), ensure_ascii=False) + chr(10)
        print("[Jina AI] FAQ/keywords extraidos: " + str(len(_faq_data.get('faq_questions', []))) + " FAQs, " + str(len(_faq_data.get('seo_keywords', []))) + " keywords")
    except Exception as _fe:
        print("[Jina AI] Aviso: extracao FAQ falhou: " + str(_fe))
    print("[Jina AI] Analise concluida: " + str(len(result)) + " chars")
    try:
        with open(_cache_file, "w", encoding="utf-8") as _f:
            _f.write(result)
        print("[Jina AI] Cache salvo: " + _cache_file)
    except Exception as _ce:
        print("[Jina AI] Aviso: nao foi possivel salvar cache: " + str(_ce))
    return result


def pesquisar_concorrentes_jina(segmento: str, cidade: str) -> str:
    return pesquisar_referencias_jina(segmento, cidade)

# ===== FUNÇÃO PRINCIPAL =====

def gerar_prd_com_debate(
    briefing_theo: str,
    dados_hunter: Dict[str, Any],
    cidade: str,
    segmento: str,
    debate_result: Dict[str, Any],
    alex_colors: Dict[str, str],
    jina_insights_externo: str = ''
) -> DesignerPRD:
    """
    Gera PRD detalhado usando 4 skills + debate + Jina AI + paleta Alex

    Args:
        briefing_theo: Briefing estratégico do Theo
        dados_hunter: Dados reais do Hunter V2
        cidade: Cidade do negócio
        segmento: Segmento do negócio
        debate_result: Decisões do Conselho de Especialistas
        alex_colors: Paleta de cores extraída pelo Alex

    Returns:
        DesignerPRD estruturado
    """
    print(f"\n[Designer PRD v3] Gerando PRD para {dados_hunter.get('nome', 'negócio')}...")

    # ✅ 1. CARREGAR 4 SKILLS
    skills_designer = get_skills_agente("designer")
    guidelines_skills = carregar_skills(skills_designer)
    print(f"[Designer PRD v3] ✅ Skills carregadas: {', '.join(skills_designer)}")

    # ✅ 2. PESQUISAR CONCORRENTES COM JINA AI (usar externo se fornecido)
    if jina_insights_externo:
        jina_insights = jina_insights_externo
        print(f'[Designer PRD v3] Jina AI: usando insights externos ({len(jina_insights)} chars)')
    else:
        jina_insights = pesquisar_concorrentes_jina(segmento, cidade)

    # ✅ 3. EXTRAIR DECISÕES DO DEBATE
    decisoes_debate = {
        "estilo_visual": debate_result.get("estilo_visual", "moderno-minimalista"),
        "animacoes": debate_result.get("animacoes", []),
        "secoes": debate_result.get("secoes", []),
        "cta_principal": debate_result.get("cta_principal", "WhatsApp")
    }

    print(f"[Designer PRD v3] ✅ Debate: {decisoes_debate['estilo_visual']}, {len(decisoes_debate['animacoes'])} animações")

    # Formatar reviews
    reviews_texto = "\n".join([
        f"- {r.get('autor', 'Anônimo')}: \"{r.get('texto', '')}\" ({r.get('rating', 5)}★)"
        for r in dados_hunter.get('reviews', [])[:5]
    ])

    # ✅ 4. CONSTRUIR PROMPT COM SKILLS + DEBATE + JINA + ALEX
    user_prompt = f"""
{'='*60}
SKILLS ATIVADAS (4)
{'='*60}
{guidelines_skills}

{'='*60}
DECISÕES DO DEBATE (OBRIGATÓRIO SEGUIR)
{'='*60}
Estilo Visual: {decisoes_debate['estilo_visual']}
Animações Aprovadas: {', '.join(decisoes_debate['animacoes']) if decisoes_debate['animacoes'] else 'Gerar 8-12 específicas do segmento'}
Seções: {', '.join(decisoes_debate['secoes']) if decisoes_debate['secoes'] else 'Definir baseado no segmento'}
CTA Principal: {decisoes_debate['cta_principal']}

{'='*60}
PALETA DE CORES (ALEX - OBRIGATÓRIO USAR)
{'='*60}
Primária: {alex_colors.get('primary', '#4A90E2')}
Secundária: {alex_colors.get('secondary', '#f9fafb')}
Acento: {alex_colors.get('accent', '#0ea5e9')}
Fundo: {alex_colors.get('background', '#ffffff')}
Texto: {alex_colors.get('text', '#1f2937')}

{'='*60}
INSIGHTS JINA AI (CONCORRENTES)
{'='*60}
{jina_insights}

{'='*60}
BRIEFING ESTRATÉGICO (THEO)
{'='*60}
{briefing_theo}

{'='*60}
DADOS REAIS (HUNTER V2)
{'='*60}
- Nome: {dados_hunter.get('nome')}
- Cidade: {cidade}
- Segmento: {segmento}
- Telefone: {dados_hunter.get('telefone')}
- Rating: {dados_hunter.get('rating')}/5
- Total de avaliações: {dados_hunter.get('total_avaliacoes')}
- Reviews: {len(dados_hunter.get('reviews', []))} capturadas
- Endereço: {dados_hunter.get('endereco')}
- Fotos: {len(dados_hunter.get('fotos', []))} disponíveis
- Logo: {'Sim' if dados_hunter.get('logo_url') else 'Não'}

**REVIEWS REAIS:**
{reviews_texto}

{'='*60}
TAREFA
{'='*60}
Gere um PRD estruturado para o site seguindo:

1. **USAR EXATAMENTE** as animações aprovadas no debate (ou gerar 8-12 específicas do segmento)
2. **USAR EXATAMENTE** a paleta de cores do Alex (não inventar outras)
3. **SEGUIR** insights dos concorrentes (Jina AI) para diferenciar
4. **GERAR** animações específicas do segmento (não genéricas)
5. **RETORNAR** JSON estruturado (não texto livre)

**FORMATO DE SAÍDA (JSON):**
{{
    "sections": [
        {{
            "name": "hero",
            "required": true,
            "components": ["hero-cta"],
            "data_source": "Hunter V2",
            "schema_org": "LocalBusiness",
            "animation": "parallax-3d-hero"
        }},
        ...
    ],
    "animations": [
        {{
            "name": "parallax-3d-hero",
            "type": "parallax",
            "target": ".hero",
            "trigger": "scroll",
            "duration": "0.8s",
            "easing": "cubic-bezier(0.25,1,0.5,1)",
            "parameters": {{"velocity": 0.5, "direction": "vertical"}}
        }},
        ...
    ],
    "color_palette": {{
        "primary": "{alex_colors.get('primary', '#4A90E2')}",
        "secondary": "{alex_colors.get('secondary', '#f9fafb')}",
        "accent": "{alex_colors.get('accent', '#0ea5e9')}",
        "background": "{alex_colors.get('background', '#ffffff')}",
        "text": "{alex_colors.get('text', '#1f2937')}",
        "reasoning": "Paleta extraída do logo pelo Alex"
    }},
    "typography": {{
        "heading": "Montserrat",
        "body": "Open Sans",
        "accent": "Playfair Display"
    }},
    "business_name": "{dados_hunter.get('nome')}",
    "reviews_count": {dados_hunter.get('total_avaliacoes', 0)},
    "reviews_rating": {dados_hunter.get('rating', 0)},
    "reviews_list": [...],
    "address": "{dados_hunter.get('endereco', '')}",
    "phone": "{dados_hunter.get('telefone', '')}",
    "hours": {{"seg-sex": "9h-18h"}},
    "photos": [...],
    "logo_url": "{dados_hunter.get('logo_url', '')}",
    "google_maps_embed": "https://www.google.com/maps/embed?pb=...",
    "components_21dev": ["hero-cta", "testimonials-carousel", ...],
    "competitor_analysis": "Análise dos 3 concorrentes (Jina AI)",
    "anti_patterns": ["Não usar paleta X", "Evitar layout Y"],
    "schema_org_types": ["LocalBusiness", "Review"],
    "skills_usadas": {skills_designer},
    "jina_insights": "Resumo dos insights"
}}

**CRÍTICO:**
- Mínimo 8 animações (máximo 12)
- Usar EXATAMENTE as cores do Alex
- Seguir decisões do debate
- Diferenciar dos concorrentes (Jina AI)
"""

    # ===== GERACAO EM 1 BLOCO OTIMIZADO =====
    temperature = get_agent_temperature('designer_prd')
    print('[Designer PRD v3] Gerando PRD em 1 bloco otimizado...')

    ctx_base = (
        'Negocio: ' + str(dados_hunter.get('nome', '')) + chr(10) +
        'Segmento: ' + segmento + ' | Cidade: ' + cidade + chr(10) +
        'Rating: ' + str(dados_hunter.get('rating', 0)) + '/5 | ' +
        str(dados_hunter.get('total_avaliacoes', 0)) + ' avaliacoes' + chr(10) +
        'Paleta: primaria=' + alex_colors.get('primary', '#374151') +
        ' secundaria=' + alex_colors.get('secondary', '#f9fafb') +
        ' acento=' + alex_colors.get('accent', '#0ea5e9') + chr(10) +
        'Estilo: ' + decisoes_debate.get('estilo_visual', 'moderno-minimalista') + chr(10) +
        'Briefing: ' + briefing_theo[:400]
    )
    system_prd = 'Voce e Designer PRD. Retorne APENAS JSON valido sem markdown.'

    prompt_unico = (
        ctx_base + chr(10)*2 +
        'Crie o plano de design completo para este negocio.' + chr(10) +
        'Inclua: secoes do site (hero, sobre, servicos, depoimentos, localizacao, contato, footer),' + chr(10) +
        'paleta de cores com primary/secondary/accent/background/text,' + chr(10) +
        'tipografia (heading, body, accent),' + chr(10) +
        '8 animacoes GSAP especificas para ' + segmento + ',' + chr(10) +
        '5 componentes UI modernos,' + chr(10) +
        'analise de 100 palavras sobre o mercado local,' + chr(10) +
        '5 padroes de design a evitar,' + chr(10) +
        'dados do negocio: nome, avaliacoes, nota, endereco, telefone, fotos, logo.' + chr(10) +
        'Retorne como objeto estruturado com todos esses campos.'
    )

    import time as _prd_time
    response_json = {}
    for _prd_attempt in range(1, 4):
        try:
            r = call_claude(system=system_prd, user=prompt_unico, model='sonnet', max_tokens=6000, temperature=temperature, agent_name='theo')
            r = r.replace('```json', '').replace('```', '').strip()
            if not r:
                print(f'[Designer PRD v3] Resposta vazia (tentativa {_prd_attempt}/3), retentando...')
                _prd_time.sleep(3 * _prd_attempt)
                continue
            response_json = json.loads(clean_json_response(r))
            print('[Designer PRD v3] PRD JSON OK: ' + str(list(response_json.keys())))
            break
        except Exception as e:
            print(f'[Designer PRD v3] Erro PRD (tentativa {_prd_attempt}/3): ' + str(e))
            if _prd_attempt < 3:
                _prd_time.sleep(3 * _prd_attempt)
            response_json = {}

    response_json['skills_usadas'] = skills_designer

    # Normalizar chaves alternativas que o Claude pode retornar
    key_aliases = {
        'business': 'business_name',
        'nome': 'business_name',
        'name': 'business_name',
        'palette': 'color_palette',
        'colors': 'color_palette',
        'cores': 'color_palette',
        'anims': 'animations',
        'animation_list': 'animations',
        'gsap_animations': 'animations',
        'gsap_anims': 'animations',
        'animacoes': 'animations',
        'ui_components': 'components_21dev',
        'components': 'components_21dev',
        'market_analysis': 'competitor_analysis',
        'concorrentes': 'competitor_analysis',
        'design_patterns_to_avoid': 'anti_patterns',
        'padroes_evitar': 'anti_patterns',
        'meta': 'schema_org_types',
    }
    for alias, canonical in key_aliases.items():
        if alias in response_json and canonical not in response_json:
            response_json[canonical] = response_json.pop(alias)

    # Normalizar business_name se for dict
    if 'business_name' in response_json and isinstance(response_json['business_name'], dict):
        bn = response_json['business_name']
        response_json['business_name'] = bn.get('name', bn.get('nome', dados_hunter.get('nome', '')))

    # Normalizar color_palette se vier com chaves diferentes
    if 'color_palette' in response_json and isinstance(response_json['color_palette'], dict):
        cp = response_json['color_palette']
        # Garantir chaves corretas usando Alex como fallback
        response_json['color_palette'] = {
            'primary': cp.get('primary', cp.get('primaria', alex_colors.get('primary', '#374151'))),
            'secondary': cp.get('secondary', cp.get('secundaria', alex_colors.get('secondary', '#f9fafb'))),
            'accent': cp.get('accent', cp.get('acento', alex_colors.get('accent', '#0ea5e9'))),
            'background': cp.get('background', cp.get('fundo', alex_colors.get('background', '#ffffff'))),
            'text': cp.get('text', cp.get('texto', alex_colors.get('text', '#1f2937'))),
            'reasoning': cp.get('reasoning', cp.get('justificativa', 'Paleta Alex')),
        }

    campos_obrigatorios = {
        'sections': [{'name': 'Hero', 'required': True, 'components': ['hero-cta'], 'data_source': 'Hunter'}],
        'color_palette': {'primary': alex_colors.get('primary', '#374151'), 'secondary': alex_colors.get('secondary', '#f9fafb'), 'accent': alex_colors.get('accent', '#0ea5e9'), 'background': '#0a0a0a' if decidir_modo_visual(segmento) == 'dark' else '#ffffff', 'text': '#f0f0f5' if decidir_modo_visual(segmento) == 'dark' else '#1f2937', 'reasoning': 'Paleta baseada no segmento'},
        'typography': {'heading': 'Inter', 'body': 'Inter', 'accent': 'Montserrat'},
        'animations': [{'name': 'fade-in', 'type': 'fade', 'target': '.hero', 'trigger': 'load', 'duration': '0.6s', 'easing': 'ease-out'}],
        'business_name': dados_hunter.get('nome', ''),
        'reviews_count': int(dados_hunter.get('total_avaliacoes', 0) or 0),
        'reviews_rating': float(dados_hunter.get('rating', 0) or 0),
        'reviews_list': dados_hunter.get('reviews', []),
        'address': dados_hunter.get('endereco', ''),
        'phone': dados_hunter.get('telefone', ''),
        'photos': dados_hunter.get('fotos', []),
        'logo_url': dados_hunter.get('logo_url'),
        'google_maps_embed': 'https://www.google.com/maps/embed/v1/place?key=AIzaSyD&q=' + str(dados_hunter.get('endereco', '')),
        'components_21dev': ['hero-cta'],
        'competitor_analysis': jina_insights[:800],
        'anti_patterns': [],
        'schema_org_types': ['LocalBusiness'],
        'jina_insights': jina_insights[:1500],
    }
    # Normalizar animations - converter strings para AnimationSpec dicts
    if 'animations' in response_json and isinstance(response_json['animations'], list):
        anims_normalizadas = []
        for anim in response_json['animations']:
            if isinstance(anim, str):
                anims_normalizadas.append({'name': anim, 'type': 'fade', 'target': '.reveal', 'trigger': 'scroll', 'duration': '0.6s', 'easing': 'ease-out'})
            elif isinstance(anim, dict):
                anims_normalizadas.append(anim)
        response_json['animations'] = anims_normalizadas
        print('[Designer PRD v3] Animations normalizadas: ' + str(len(anims_normalizadas)))

    # Normalizar anti_patterns - converter dicts para strings
    if 'anti_patterns' in response_json and isinstance(response_json['anti_patterns'], list):
        response_json['anti_patterns'] = [
            item.get('pattern', str(item)) if isinstance(item, dict) else str(item)
            for item in response_json['anti_patterns']
        ]

    # Normalizar jina_insights - converter dict para string
    if 'jina_insights' in response_json and isinstance(response_json['jina_insights'], dict):
        ji = response_json['jina_insights']
        response_json['jina_insights'] = ji.get('summary', ji.get('insights', str(ji)))

    # Normalizar sections - converter dict keyed para lista
    if 'sections' in response_json and isinstance(response_json['sections'], dict):
        secs = []
        for key, val in response_json['sections'].items():
            if isinstance(val, dict):
                val.setdefault('name', val.get('id', key).capitalize())
                val.setdefault('required', True)
                val.setdefault('components', ['cta'])
                val.setdefault('data_source', 'Claude')
                secs.append(val)
        response_json['sections'] = secs if secs else [{'name': 'Hero', 'required': True, 'components': ['hero-cta'], 'data_source': 'Fallback'}]

    # Normalizar typography - converter dict aninhado para Dict[str, str]
    if 'typography' in response_json and isinstance(response_json['typography'], dict):
        typo = response_json['typography']
        normalized = {}
        for k, v in typo.items():
            if isinstance(v, dict):
                normalized[k] = v.get('family', v.get('name', 'Inter'))
            elif isinstance(v, str):
                normalized[k] = v
            else:
                normalized[k] = 'Inter'
        for req in ['heading', 'body', 'accent']:
            if req not in normalized:
                normalized[req] = 'Inter'
        response_json['typography'] = normalized

    for campo, valor in campos_obrigatorios.items():
        if campo not in response_json or not response_json[campo]:
            response_json[campo] = valor

    try:
        prd = DesignerPRD(**response_json)
        prd.cidade = cidade
        prd.segmento = segmento
        secoes_faltando = [s for s in ['Hero', 'Sobre', 'Depoimentos', 'Contato'] if s not in [sec.name for sec in prd.sections]]
        if secoes_faltando:
            print('[Designer PRD v3] Secoes faltando: ' + str(secoes_faltando))
            for s in secoes_faltando:
                prd.sections.append(SectionSpec(name=s, required=True, components=['cta'], data_source='Fallback'))
        print('[Designer PRD v3] PRD validado: ' + str(len(prd.sections)) + ' secoes, ' + str(len(prd.animations)) + ' animacoes')
        return prd
    except Exception as e:
        print('[Designer PRD v3] Erro fatal: ' + str(e))
        raise Exception('Designer PRD falhou: ' + str(e))






# ===== BRIEFING ESTRATEGICO =====

def decidir_modo_visual(segmento: str) -> str:
    """Modo visual: dark para nichos de impacto/premium, light para nichos suaves/saúde."""
    _seg = segmento.lower().strip()
    _dark_nichos = [
        "academia", "crossfit", "barbearia", "advocacia", "artes marciais",
        "musculacao", "box", "luta", "tattoo", "tatuagem", "bar", "pub",
        "cervejaria", "balada", "boate", "night", "rock", "metal",
        "mecanica", "auto", "oficina", "moto", "burger", "hamburgueria",
        "churrascaria", "steakhouse", "pizzaria", "gastronomia", "restaurante",
        "tech", "tecnologia", "startup", "dev", "gaming", "esports",
        "fotografia", "studio", "estudio", "musica", "audio", "podcast",
        "arquitetura", "design", "agencia", "marketing", "consultoria",
    ]
    if any(n in _seg for n in _dark_nichos):
        return "dark"
    return "light"

def gerar_briefing_estrategico(input_data) -> str:
    """Gera briefing estrategico rico em markdown para o Designer PRD e Liam."""
    nome = input_data.nome if hasattr(input_data, "nome") else str(input_data)
    cidade = input_data.cidade if hasattr(input_data, "cidade") else ""
    segmento = input_data.segmento if hasattr(input_data, "segmento") else ""
    rating = input_data.rating if hasattr(input_data, "rating") else 0

    modo_visual = decidir_modo_visual(segmento)

    system = (
        "Voce e Theo, estrategista senior de marketing digital e copywriter especialista em negocios locais. "
        "Sua UNICA funcao e criar briefing de copy e estrategia de conversao — voce NAO define cores, CSS, fontes ou design. "
        "Crie um briefing estrategico DETALHADO em markdown focado em copy e AIDA. "
        "O briefing deve ser rico, especifico e orientado a conversao — nunca generico. "
        "Estruture o site seguindo o framework AIDA (Atencao, Interesse, Desejo, Acao): "
        "Hero captura atencao com promessa forte, Problema/Solucao gera interesse, "
        "Servicos/Prova Social criam desejo, CTA WhatsApp converte em acao. "
        "Ao ler os Insights de Mercado (Jina AI), extraia os melhores angulos de copy do segmento (o que converte). "
        "Retorne APENAS o markdown sem explicacoes extras. NAO mencione cores, hex codes, CSS ou tipografia."
    )

    sep = chr(10)
    partes = [
        "Crie briefing estrategico completo para:",
        "- Negocio: " + nome,
        "- Segmento: " + segmento,
        "- Cidade: " + cidade,
        "- Rating Google: " + str(rating) + "/5",
        "- Modo Visual Decidido: " + modo_visual.upper() + " MODE",
        "",
        "O briefing DEVE incluir obrigatoriamente:",
        "",
        "## 1. HIERARQUIA SEO",
        "- H1 (unico): " + nome + " - " + segmento + " em " + cidade,
        "- H2 para cada secao: Sobre, Servicos, Depoimentos, Galeria, Localizacao, Contato",
        "- H3 para subsecoes: nome de cada servico, cada depoimento",
        "",
        "## 2. ANIMACOES RECOMENDADAS (especificas para " + segmento + ")",
        "- Listar 6-8 animacoes GSAP especificas para o segmento",
        "- Nao usar animacoes genericas",
        "",
        "## 5. COPY SUGERIDA",
        "- Headline principal (H1): especifica para " + segmento + " em " + cidade,
        "- Subheadline: proposta de valor unica",
        "- CTA principal: WhatsApp (NUNCA incluir precos ou valores)",
        "- CTAs secundarios: Consulte valores, Solicite orcamento",
        "",
        "## 6. SECOES DO SITE",
        "- Listar secoes em ordem com descricao do conteudo de cada uma",
        "- Incluir secao LGPD (banner de cookies obrigatorio)",
        "",
        "## 7. GUARDRAILS OBRIGATORIOS",
        "- NUNCA incluir precos, valores, mensalidades ou tabelas de preco",
        "- Usar sempre: Consulte valores, Solicite orcamento, Fale conosco",
        "- NUNCA usar lorem ipsum",
        "- SEMPRE usar dados reais do negocio",
        "",
        "## 8. SCHEMA.ORG",
        "- Tipo recomendado para " + segmento,
        "- Campos obrigatorios: name, address, telephone, aggregateRating",
        "",
        "## 9. ESTRUTURA AIDA DO SITE",
        "- ATENCAO (Hero): headline que para o scroll em 3 segundos para " + segmento,
        "- INTERESSE (Problema/Solucao): conectar com a dor real do cliente de " + segmento,
        "- DESEJO (Servicos + Prova Social): mostrar transformacao, nao features",
        "- ACAO (CTA): WhatsApp com urgencia natural, sem pressao artificial",
        "",
    ]
    # Injetar jina_insights se disponivel
    jina_data = getattr(input_data, 'jina_insights', None) or ''
    if jina_data:
        partes.append('')
        partes.append('## 9. REFERENCIAS DE MERCADO (Jina AI)')
        partes.append(jina_data[:1500])
    user = sep.join(partes)
    try:
        from agent_rag import format_rag_prompt, get_agent_temperature
        full_prompt = format_rag_prompt("theo", user)
        temperature = get_agent_temperature("theo")
        briefing = call_claude(system=system, user=full_prompt, model="sonnet", max_tokens=4000, temperature=temperature, agent_name="theo")
        print("[Theo] Briefing gerado: " + str(len(briefing)) + " chars")
        return briefing
    except Exception as e:
        print("[Theo] Erro briefing: " + str(e))
        return "# MODO_VISUAL: " + modo_visual.upper() + chr(10) + "# Briefing: " + nome + chr(10) + "Segmento: " + segmento + " em " + cidade


# ===== ADAPTER PARA COMPATIBILIDADE COM ORQUESTRADOR =====

from typing import Optional
from pydantic import BaseModel

class TheoInput(BaseModel):
    """Input adapter para compatibilidade com orquestrador"""
    nome: str
    cidade: str
    segmento: str
    nicho: Optional[str] = None
    telefone: str
    whatsapp: Optional[str] = None
    rating: float = 0.0
    instagram: Optional[str] = None
    site: Optional[str] = None
    jina_insights: Optional[str] = None
