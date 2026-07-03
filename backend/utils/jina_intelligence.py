"""
Jina Intelligence — Inteligência de mercado estruturada.
Substitui a Jina antiga (68 chars genéricos) por dados reais:
- Tom de voz do mercado
- Palavras que vendem
- Frases genéricas observadas
- Headlines/CTAs de referência
- Estilo visual dominante
- Diferencial disponível

Fail-fast: se Jina falhar, lança JinaIntelligenceError — não usa fallbacks.
"""

import os
import re
import json
import hashlib
import time
import sys
import requests  # top-level para que testes possam monkey-patchar

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents"),
)

from backend.pipeline_exceptions import JinaIntelligenceError

JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# Sites de referência por nicho para busca de concorrentes
REFERENCIAS_NICHO = {
    "academia": "https://www.smartfit.com.br",
    "crossfit": "https://www.crossfitbrasil.com.br",
    "hamburgueria": "https://www.bullguer.com.br",
    "pizzaria": "https://www.pizzariabatepapo.com.br",
    "dentista": "https://www.odontocompany.com",
    "nutricionista": "https://www.nutricionistaadrianalauffer.com.br",
    "barbearia": "https://www.barbeariadonjuan.com.br",
    "salao": "https://www.jacquesjanine.com.br",
    "clinica": "https://www.dfrancisco.com.br",
    "pet": "https://www.petlove.com.br",
    "restaurante": "https://www.madero.com.br",
    "pilates": "https://www.pilatesstudiobrasil.com.br",
    "estetica": "https://www.espacolaser.com.br",
    "advocacia": "https://www.mattosfilho.com.br",
    "contabilidade": "https://www.contabilizei.com.br",
    "imobiliaria": "https://www.quintoandar.com.br",
    "escola": "https://www.kumon.com.br",
    "mecanica": "https://www.dpaschoal.com.br",
}


def _normalizar_nicho_jina(nicho: str) -> str:
    """Normalize noisy lead segments to the canonical market key used by Jina."""
    raw = (nicho or "").strip().lower()
    compact = re.sub(r"\s+", " ", raw)
    ascii_key = (
        compact.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )

    aliases = (
        ("nutricion", "nutricionista"),
        ("sala de fitness", "academia"),
        ("academia", "academia"),
        ("crossfit", "crossfit"),
        ("barbear", "barbearia"),
        ("salao", "salao"),
        ("beleza", "salao"),
        ("estetic", "estetica"),
        ("clinica", "clinica"),
        ("advog", "advocacia"),
        ("jurid", "advocacia"),
        ("restaurante", "restaurante"),
        ("pizzaria", "pizzaria"),
        ("hamburg", "hamburgueria"),
        ("dent", "dentista"),
        ("odont", "dentista"),
        ("pet", "pet"),
        ("pilates", "pilates"),
        ("contabil", "contabilidade"),
        ("imobili", "imobiliaria"),
        ("escola", "escola"),
        ("mecanic", "mecanica"),
    )
    for needle, canonical in aliases:
        if needle in ascii_key:
            return canonical
    return compact.rstrip("s") or "negocio local"


# Frases genéricas comuns do mercado. São contexto, não regra para o Builder.
FRASES_GENERICAS_PADRAO = [
    "atendimento personalizado",
    "qualidade e compromisso",
    "resultados reais",
    "os melhores profissionais",
    "pronto para começar",
    "excelência em atendimento",
    "sua satisfação é nossa prioridade",
    "venha nos conhecer",
    "entre em contato",
]


def buscar_inteligencia_jina(
    nicho: str,
    cidade: str,
    nome_negocio: str,
    concorrentes_urls: list = None,
    tenant_id: int | str | None = None,
) -> dict:
    """
    Busca inteligência real de mercado via Jina Reader.
    Retorna dict estruturado. Síncrono (compatível com pipeline atual).
    Cache de 48h por nicho+cidade.
    """
    nicho_original = nicho
    nicho = _normalizar_nicho_jina(nicho)

    # Cache
    _cache_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "agents",
        "jina_cache",
    )
    os.makedirs(_cache_dir, exist_ok=True)
    _scope = str(tenant_id or "global").strip().lower()
    _cache_key = hashlib.md5(
        (_scope + "::" + nicho.lower() + "::" + cidade.lower() + "::v3").encode()
    ).hexdigest()[:12]
    _cache_file = os.path.join(_cache_dir, f"jina_intel_{_cache_key}.json")
    _TTL = 48 * 3600

    if (
        os.path.exists(_cache_file)
        and (time.time() - os.path.getmtime(_cache_file)) < _TTL
    ):
        try:
            with open(_cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            print(
                f"[Jina Intel] Cache HIT: {nicho} em {cidade} ({len(json.dumps(cached))} chars)"
            )
            return cached
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Buscar inteligência real via Jina (FAIL-CLOSED: se falhar, erro claro)
    resultado = _buscar_real(nicho, cidade, nome_negocio, concorrentes_urls)

    # Fail-fast: sem fallback. Se Jina falhar, pipeline trava com erro claro.
    # Isso é INTENCIONAL - o sistema deve falhar fechado pra você saber que precisa
    # recarregar JINA_API_KEY ou arrumar a integração, NÃO cair em fallback
    # silencioso que esconde o problema.
    if not resultado or not resultado.get("palavras_poder"):
        raise JinaIntelligenceError(
            f"Jina nao retornou inteligencia valida para '{nicho_original}' em '{cidade}'.",
            context={
                "nicho": nicho_original,
                "nicho_normalizado": nicho,
                "cidade": cidade,
                "nome_negocio": nome_negocio,
                "acao": "Recarregue JINA_API_KEY ou arrume a integração Jina (NAO usamos fallback)",
            },
        )

    # Salvar cache
    try:
        with open(_cache_file, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False)
    except (OSError, IOError):
        pass

    total = len(json.dumps(resultado, ensure_ascii=False))
    print(
        f"[Jina Intel] OK: {total} chars, {len(resultado.get('palavras_poder', []))} palavras-poder"
    )
    return resultado


def _buscar_real(
    nicho: str, cidade: str, nome_negocio: str, concorrentes_urls: list = None
) -> dict:
    """Busca real via Jina Reader — lê sites concorrentes e analisa."""
    import requests

    nicho = _normalizar_nicho_jina(nicho)

    urls_analisar = []

    # Prioridade 1: URLs de concorrentes já encontrados
    if concorrentes_urls:
        urls_analisar = [u for u in concorrentes_urls[:2] if u and u.startswith("http")]

    # Prioridade 2: Buscar via Google
    if not urls_analisar:
        urls_analisar = _buscar_concorrentes_google(nicho, cidade)

    # Prioridade 3: Site modelo do nicho
    if not urls_analisar:
        nicho_lower = nicho.lower()
        for key, url in REFERENCIAS_NICHO.items():
            if key in nicho_lower or nicho_lower in key:
                urls_analisar = [url]
                break

    if not urls_analisar:
        return None

    # Ler e analisar cada site
    resultados = []
    headers = {"X-Return-Format": "text", "X-Timeout": "15"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    for url in urls_analisar[:2]:
        try:
            print(f"[Jina Intel] Lendo: {url}")
            resp = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=20)
            # Instrumentação cost_tracker (Sprint 0.3) — fail-safe
            try:
                from backend.agents.cost_tracker import record_cost_event

                record_cost_event(
                    provider="jina",
                    service="jina_reader",
                    units=1,
                    custo_usd=0.001 * len(resp.text or "") / 1000,  # proxy: $1/1M chars
                    latency_ms=int(resp.elapsed.total_seconds() * 1000)
                    if hasattr(resp, "elapsed")
                    else None,
                    status="success" if resp.status_code == 200 else "error",
                    error_message=None
                    if resp.status_code == 200
                    else f"HTTP {resp.status_code}",
                    metadata={"url": url, "status_code": resp.status_code},
                )
            except Exception as iexc:  # pragma: no cover
                print(f"[Jina Intel] cost_event instrumentation falhou: {iexc}")

            if resp.status_code == 200 and len(resp.text) > 200:
                conteudo = resp.text[:5000]
                analise = _analisar_conteudo_llm(conteudo, nicho, cidade, nome_negocio)
                if analise:
                    analise["url_fonte"] = url
                    resultados.append(analise)
                    print(f"[Jina Intel] Análise OK: {url}")
        except Exception as e:
            # Instrumentação de falha também
            try:
                from backend.agents.cost_tracker import record_cost_event

                record_cost_event(
                    provider="jina",
                    service="jina_reader",
                    units=1,
                    custo_usd=0.0,
                    status="error",
                    error_message=str(e)[:200],
                    metadata={"url": url},
                )
            except Exception:
                pass
            print(f"[Jina Intel] Erro lendo {url}: {e}")

    if not resultados:
        return None

    return _consolidar_inteligencia(resultados, nicho, cidade, nome_negocio)


def _buscar_concorrentes_google(nicho: str, cidade: str) -> list:
    """Busca URLs de concorrentes via Jina Search."""
    import requests

    nicho = _normalizar_nicho_jina(nicho)
    query = f"melhor {nicho} {cidade} site oficial"
    headers = {"X-Return-Format": "markdown", "X-Timeout": "15"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    EXCLUIR = [
        "google",
        "facebook",
        "instagram",
        "youtube",
        "linkedin",
        "twitter",
        "smartfit",
        "bodytech",
        "bluefit",
        "mcdonalds",
        "starbucks",
        "yelp",
        "tripadvisor",
        "ifood",
        "rappi",
        "reclameaqui",
        "guiamais",
        "apontador",
        "telelistas",
        "wikipedia",
        "amazon",
        "mercadolivre",
        "wix.com",
        "wordpress.com",
        "blogspot",
    ]

    try:
        search_url = f"https://r.jina.ai/https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(search_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []

        urls = []
        for line in resp.text.split("\n"):
            if "http" in line:
                url_match = re.search(r"https?://[^\s\)\"\x27]+", line)
                if url_match:
                    url = url_match.group(0).rstrip(".,)")
                    if not any(exc in url.lower() for exc in EXCLUIR) and len(url) > 15:
                        urls.append(url)
                        if len(urls) >= 2:
                            break
        return urls
    except Exception as e:
        print(f"[Jina Intel] Erro busca Google: {e}")
        return []


def _analisar_conteudo_llm(
    conteudo: str, nicho: str, cidade: str, nome_negocio: str
) -> dict:
    """Analisa conteúdo extraído via Haiku (barato)."""
    from llm_direct import call_claude

    prompt = f"""Analise este site de {nicho} e extraia APENAS este JSON (sem texto extra):

{{
  "tom_de_voz": "como eles falam (formal/casual/premium/popular/técnico/emocional)",
  "palavras_poder": ["10 palavras/expressões que usam pra vender"],
  "frases_genericas": ["frases comuns ou clichês observados no mercado"],
  "headlines": ["3 headlines eficazes encontradas no site"],
  "ctas": ["os CTAs mais fortes (texto dos botões)"],
  "proposta_valor": "em 1 frase, o que esse negócio promete",
  "estilo_visual": "dark/light, cores dominantes, tipografia, sensação geral",
  "secoes_presentes": ["lista das seções do site na ordem"],
  "diferencial_comunicado": "o que eles dizem que os torna únicos",
  "publico_alvo": "pra quem o site fala (idade, perfil, dor)"
}}

CONTEÚDO DO SITE:
{conteudo[:4000]}

Retorne APENAS o JSON."""

    try:
        resp = call_claude(
            system="Você extrai inteligência de marketing de sites. Retorne APENAS JSON válido.",
            user=prompt,
            model="haiku",
            max_tokens=800,
            temperature=0.1,
            agent_name="jina_intel",
        )
        json_match = re.search(r"\{[\s\S]*\}", resp)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[Jina Intel] Erro análise LLM: {e}")

    return None


def _consolidar_inteligencia(
    resultados: list, nicho: str, cidade: str, nome_negocio: str
) -> dict:
    """Consolida análises de múltiplos concorrentes."""
    palavras_poder = []
    frases_genericas = list(FRASES_GENERICAS_PADRAO)
    headlines = []
    ctas = []
    estilos = []

    for r in resultados:
        palavras_poder.extend(r.get("palavras_poder", []))
        frases_genericas.extend(r.get("frases_genericas", []))
        headlines.extend(r.get("headlines", []))
        ctas.extend(r.get("ctas", []))
        estilos.append(r.get("estilo_visual", ""))

    # Deduplica
    palavras_poder = list(dict.fromkeys(palavras_poder))[:12]
    frases_genericas = list(dict.fromkeys(frases_genericas))[:15]
    headlines = list(dict.fromkeys(headlines))[:5]
    ctas = list(dict.fromkeys(ctas))[:5]

    return {
        "tom_de_voz": resultados[0].get("tom_de_voz", "profissional-direto"),
        "palavras_poder": palavras_poder,
        "frases_genericas": frases_genericas,
        "headlines_referencia": headlines,
        "ctas_referencia": ctas,
        "estilo_visual": estilos[0] if estilos else "moderno, clean",
        "proposta_valor_concorrentes": [
            r.get("proposta_valor", "") for r in resultados if r.get("proposta_valor")
        ],
        "secoes_comuns": resultados[0].get("secoes_presentes", []),
        "diferencial_ausente": _detectar_diferencial(resultados, nome_negocio),
        "publico_alvo": resultados[0].get("publico_alvo", ""),
        "fontes_analisadas": [r.get("url_fonte", "") for r in resultados],
    }


def _detectar_diferencial(resultados: list, nome_negocio: str) -> str:
    """Identifica o que NENHUM concorrente menciona — oportunidade."""
    todos_textos = " ".join(
        json.dumps(r, ensure_ascii=False) for r in resultados
    ).lower()

    diferenciais_possiveis = [
        ("horário estendido", "horário"),
        ("aula experimental grátis", "experimental"),
        ("estacionamento", "estacionamento"),
        ("ar condicionado", "ar condicionado"),
        ("sem matrícula", "matrícula"),
        ("plano sem fidelidade", "fidelidade"),
        ("personal incluso", "personal"),
        ("avaliação física", "avaliação"),
        ("primeira consulta grátis", "primeira consulta"),
        ("atendimento 24h", "24h"),
    ]

    temas_ausentes = []
    for diferencial, keyword in diferenciais_possiveis:
        if keyword not in todos_textos:
            temas_ausentes.append(diferencial)

    if temas_ausentes:
        return f"Nenhum concorrente menciona: {', '.join(temas_ausentes[:3])}. Oportunidade."
    return "Mercado saturado — diferenciar por experiência e tom de voz."



def formatar_inteligencia_para_arquiteto(intel: dict) -> str:
    """Formata o dict de inteligência como texto pro prompt do ArquitetoMestre."""
    if not intel:
        return ""

    partes = [
        "=== INTELIGÊNCIA DE MERCADO (Jina AI) ===",
        "",
        f"TOM DE VOZ DO MERCADO: {intel.get('tom_de_voz', '')}",
        "",
        "LINGUAGEM COMERCIAL OBSERVADA:",
        f"  {', '.join(intel.get('palavras_poder', []))}",
        "",
    ]

    headlines = intel.get("headlines_referencia", [])
    if headlines:
        partes.append("HEADLINES DE REFERÊNCIA (inspiração, não copiar):")
        for h in headlines:
            partes.append(f"  - {h}")
        partes.append("")

    ctas = intel.get("ctas_referencia", [])
    if ctas:
        partes.append("CTAs QUE CONVERTEM:")
        for c in ctas:
            partes.append(f"  - {c}")
        partes.append("")

    partes.append(f"ESTILO VISUAL DO MERCADO: {intel.get('estilo_visual', '')}")
    partes.append(f"PÚBLICO-ALVO: {intel.get('publico_alvo', '')}")

    diferencial = intel.get("diferencial_ausente", "")
    if diferencial:
        partes.append(f"DIFERENCIAL DISPONÍVEL: {diferencial}")

    partes.append("")
    partes.append("Esta inteligência é referência de mercado para o próximo agente.")
    partes.append("=== FIM INTELIGÊNCIA ===")

    return "\n".join(partes)
