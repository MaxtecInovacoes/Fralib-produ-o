"""Agente de Inteligência de Nicho Local — analisa dados brutos do lead + concorrentes
e devolve briefing estruturado para os próximos agentes."""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from handoff_types import NichoBriefing
from llm_direct import call_claude

try:
    from agente_variacao import detect_subniche
except Exception:
    def detect_subniche(segmento, servicos=None, atributos=None):  # type: ignore
        return "default"

SYSTEM_PROMPT = """You are the Local Niche Intelligence Agent.

Your role is to analyze raw lead data and competitor data and return a structured briefing for the next agents.
You do NOT write final copy and do NOT generate HTML.
You do NOT invent information.
Only infer what is strongly supported by the received data.

INPUT:
- Lead data
- Competitor data
- Scraped site content
- Reviews, testimonials, FAQs, descriptions, services, location

OUTPUT:
Always return Markdown plus compact JSON.

REQUIRED BLOCKS:
1. Main niche
2. Sub-niches
3. Primary and secondary target audience
4. USPs and real strengths
5. Differentiators vs competitors
6. Likely objections
7. Local SEO keywords
8. Recommended tone of voice
9. Notes for the Master Architect
10. Risk field or missing data

RULES:
- If niche is vague, propose the best inference and mark low confidence
- If data is insufficient, say "not informed"
- Never create fictional narrative
- Always highlight what makes the business different
- Always point out repetition risk with similar competitors
- Always indicate 3 to 5 local SEO keywords

OUTPUT FORMAT:
First the Markdown with the 10 blocks above (fixed titles, short lists).
Then the JSON with this exact format:
{
  "nicho": "",
  "subnichos": [],
  "publico_alvo": [],
  "usp": [],
  "diferenciais": [],
  "objcoes": [],
  "keywords": [],
  "tom_de_voz": "",
  "notas": "",
  "confianca": "alta|media|baixa",
  "dados_ausentes": [],
  "competidores": []
}

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""

def gerar_briefing(
    dados_lead: dict,
    segmento: str,
    cidade: str,
    jina_insights: str = "",
    task_id: str = "",
) -> NichoBriefing:
    _nome = dados_lead.get("nome", "")
    _rating = dados_lead.get("rating", 0)
    _total_av = dados_lead.get("total_avaliacoes", 0)
    _tel = dados_lead.get("telefone", "")
    _end = dados_lead.get("endereco", "")
    _servicos = dados_lead.get("servicos", [])
    _reviews = dados_lead.get("reviews", [])
    _atributos = dados_lead.get("atributos", [])
    _faixa_preco = dados_lead.get("faixa_preco", "")

    _reviews_text = []
    for r in _reviews[:6]:
        if isinstance(r, str):
            _reviews_text.append(r[:200])
        elif isinstance(r, dict):
            _txt = (
                r.get("text", "")
                or r.get("comentario", "")
                or r.get("review", "")
                or str(r)
            )
            _reviews_text.append(str(_txt)[:200])
        else:
            _reviews_text.append(str(r)[:200])

    user_prompt = f"""Analise os dados abaixo e gere o briefing de nicho.

== DADOS DO LEAD ==
Nome: {_nome}
Segmento: {segmento}
Cidade: {cidade}
Telefone: {_tel}
Endereço: {_end}
Rating: {_rating}/5 ({_total_av} avaliações)
Faixa de preço: {_faixa_preco or "não informado"}
Serviços: {", ".join(_servicos[:10]) if _servicos else "não informado"}
Atributos: {", ".join(_atributos[:10]) if _atributos else "não informado"}

== REVIEWS REAIS ==
{chr(10).join(f"- {r}" for r in _reviews_text) if _reviews_text else "nenhuma review disponível"}

== DADOS DOS CONCORRENTES (Jina) ==
{jina_insights[:4000] if jina_insights else "dados de concorrentes não disponíveis"}

Gere o briefing seguindo o formato obrigatório: MARKDOWN primeiro, depois JSON."""
    import time as _time

    _start = _time.time()

    resposta = call_claude(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="sonnet",
        max_tokens=4000,
        temperature=0.3,
        agent_name="agente_nicho",
    )

    _elapsed = _time.time() - _start

    # Extrair JSON da resposta
    import json as _json, re as _re

    _json_match = _re.search(r"\{[^{}]*\}[^}]*$", resposta, _re.DOTALL)
    _dados = {}
    if _json_match:
        try:
            _dados = _json.loads(_json_match.group(0))
        except _json.JSONDecodeError:
            pass

    # Fallback se JSON não foi parseado
    if not _dados:
        _dados = {
            "nicho": segmento,
            "subnichos": [],
            "publico_alvo": [],
            "usp": [],
            "diferenciais": [],
            "objeções": [],
            "keywords": [],
            "tom_de_voz": "profissional",
            "notas": "",
            "confianca": "baixa",
            "dados_ausentes": ["JSON não foi extraído corretamente"],
        }

    # Extrair nomes dos concorrentes do jina_insights (heurística simples)
    _competidores = []
    for _linha in (jina_insights or "").split("\n"):
        _linha = _linha.strip()
        if _linha.startswith("- **") or _linha.startswith("**"):
            _nome_conc = (
                _linha.replace("**", "").replace("- ", "").split(":")[0].strip()
            )
            if _nome_conc and len(_nome_conc) < 60:
                _competidores.append(_nome_conc)

    # Detectar subnicho canonico a partir de segmento + servicos + atributos.
    # Usado pelo agente_variacao para escolher SUB_NICHO_TEMPLATES.
    _subnicho = detect_subniche(segmento, _servicos, _atributos)

    return NichoBriefing(
        task_id=task_id,
        source_agent="agente_nicho",
        target_agent="agente_variacao",
        status="ok",
        task_summary=f"Briefing gerado para {_nome} ({segmento}) em {_elapsed:.1f}s",
        nicho=_dados.get("nicho", segmento),
        subnichos=_dados.get("subnichos", []),
        subnicho=_subnicho,
        cidade=cidade,
        publico_alvo=_dados.get("publico_alvo", []),
        usp=_dados.get("usp", []),
        diferenciais=_dados.get("diferenciais", []),
        objeções=_dados.get("objeções", []),
        keywords=_dados.get("keywords", []),
        tom_de_voz=_dados.get("tom_de_voz", "profissional"),
        notas=_dados.get("notas", ""),
        confianca=_dados.get("confianca", "media"),
        dados_ausentes=_dados.get("dados_ausentes", []),
        competidores=_competidores[:6],
    )
