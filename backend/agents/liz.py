import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
from skill_loader import carregar_skills, get_skills_agente
Agente Liz - QA/Auditora
Migração de agente_liz.FINAL.js para Pydantic AI
"""
import json
import re
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from llm_direct import call_claude
from memory import salvar_memoria
from agent_rag import format_rag_prompt, get_agent_temperature, buscar_contexto_rag, mark_rag_used
# from design_system_validator import validar_html, calcular_score_tiers
from validation_layer import validar_html, calcular_score_validacao

# ===== MODELOS PYDANTIC =====

class ProblemaAuditoria(BaseModel):
    """Problema encontrado na auditoria"""
    gravidade: str  # CRÍTICO, ALTO, MÉDIO, BAIXO
    dimensao: str  # HTML, CSS, Conversão, Semântica
    problema: str

class AuditoriaTecnica(BaseModel):
    """Resultado da auditoria técnica"""
    score: int = Field(..., ge=0, le=100)
    aprovado: bool
    problemas: List[ProblemaAuditoria]

class AuditoriaSemantica(BaseModel):
    """Resultado da auditoria semântica"""
    score: int = Field(..., ge=0, le=100)
    aprovado: bool
    problemas: List[str]

class LizOutput(BaseModel):
    correcoes_cirurgicas: Optional[List[Dict[str, str]]] = []  # [{"secao": "hero", "instrucao": "..."}]
    """Saída da Liz - Auditoria completa"""
    aprovado: bool
    score: int = Field(..., ge=0, le=100)
    tecnica: AuditoriaTecnica
    semantica: AuditoriaSemantica
    tentativa: int = 1

# ===== CONSTANTES =====

SCORE_MINIMO = 70

# ===== AUDITORIA TÉCNICA =====

def auditoria_tecnica(html: str, briefing: str = "") -> AuditoriaTecnica:
    """
    Auditoria técnica do HTML (validação estrutural)

    Args:
        html: HTML a auditar

    Returns:
        Resultado da auditoria técnica
    """
    problemas = []
    score = 100

    # ===== VETOS AUTOMATICOS (bloqueantes independente do score) =====
    # DOCTYPE duplicado = falha estrutural critica
    _doctype_count = html.lower().count('<!doctype')
    if _doctype_count > 1:
        problemas.append(ProblemaAuditoria(gravidade="CRITICO", dimensao="HTML", problema=f"DOCTYPE duplicado ({_doctype_count}x) — documento HTML invalido, layout quebrado"))
        score -= 40
    
    # height:100vh fora do hero = layout quebrado em mobile
    import re as _re_liz_veto
    _100vh_fora_hero = _re_liz_veto.findall(r'(?i)height\s*:\s*100vh', html)
    if len(_100vh_fora_hero) > 1:
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="CSS", problema=f"height:100vh em {len(_100vh_fora_hero)} elementos — apenas hero pode ter 100vh"))
        score -= 20

    # Validação DOCTYPE
    if "<!DOCTYPE html>" not in html:
        problemas.append(ProblemaAuditoria(
            gravidade="CRÍTICO",
            dimensao="HTML",
            problema="Falta DOCTYPE"
        ))
        score -= 15

    # Validação Tailwind CSS
    if "tailwindcss" not in html:
        problemas.append(ProblemaAuditoria(
            gravidade="ALTO",
            dimensao="CSS",
            problema="Tailwind CSS não incluído"
        ))
        score -= 10

    # Validação WhatsApp
    if "wa.me" not in html and "whatsapp" not in html.lower():
        problemas.append(ProblemaAuditoria(
            gravidade="CRÍTICO",
            dimensao="Conversão",
            problema="Falta link WhatsApp"
        ))
        score -= 15

    # Validação UTF-8
    if '<meta charset="UTF-8">' not in html and '<meta charset="utf-8">' not in html:
        problemas.append(ProblemaAuditoria(
            gravidade="ALTO",
            dimensao="HTML",
            problema="Falta charset UTF-8"
        ))
        score -= 10

    # Validacao de animacoes — aceita AOS ou GSAP (ambos validos)
    tem_aos = "aos" in html.lower() and ("data-aos" in html.lower() or "aos.init" in html.lower())
    tem_gsap = "gsap" in html.lower()
    if not tem_aos and not tem_gsap:
        problemas.append(ProblemaAuditoria(
            gravidade="MEDIO",
            dimensao="JavaScript",
            problema="Falta biblioteca de animacao (AOS ou GSAP)"
        ))
        score -= 5

    # Validação SEO
    if "application/ld+json" not in html:
        problemas.append(ProblemaAuditoria(
            gravidade="MÉDIO",
            dimensao="SEO",
            problema="Falta JSON-LD (Schema.org)"
        ))
        score -= 5

    # Validação animações
    if "reveal" not in html:
        problemas.append(ProblemaAuditoria(
            gravidade="MÉDIO",
            dimensao="UX",
            problema="Falta classes de animação (.reveal)"
        ))
        score -= 5

    import re as _re

    # LGPD - banner de cookies
    if "lgpd" not in html.lower() and "cookie" not in html.lower():
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="LGPD", problema="Falta banner LGPD de cookies"))
        score -= 10

    # SEO local - H1 unico com cidade (mapa SEO local)
    h1_matches = _re.findall(r"<h1[^>]*>(.*?)</h1>", html, _re.IGNORECASE | _re.DOTALL)
    if len(h1_matches) == 0:
        problemas.append(ProblemaAuditoria(gravidade="CRITICO", dimensao="SEO", problema="Falta H1 na pagina"))
        score -= 15
    elif len(h1_matches) > 1:
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="SEO", problema="Multiplos H1 (" + str(len(h1_matches)) + ") - deve ter apenas 1"))
        score -= 10
    else:
        h1_text = _re.sub(r"<[^>]+>", "", h1_matches[0]).strip().lower()
        if briefing:
            import re as _re2
            cidade_m = _re2.search(r"cidade[^:]*:[^a-zA-Z]*([a-zA-Z ]+)", briefing, _re2.IGNORECASE)
            if cidade_m:
                cidade_val = cidade_m.group(1).strip().lower()[:20]
                if cidade_val and cidade_val not in h1_text:
                    problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="SEO", problema="H1 nao contem a cidade - prejudica SEO local"))
                    score -= 8

    # H2 por secao - minimo 4 conforme mapa SEO local
    h2_matches = _re.findall(r"<h2[^>]*>", html, _re.IGNORECASE)
    if len(h2_matches) < 4:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="SEO", problema="Poucos H2 (" + str(len(h2_matches)) + ") - mapa SEO exige 4: Servicos, Diferenciais, Prova Social, CTA"))
        score -= 8

    # H3 - minimo 6 (2 por H2)
    h3_matches = _re.findall(r"<h3[^>]*>", html, _re.IGNORECASE)
    if len(h3_matches) < 6:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="SEO", problema="Poucos H3 (" + str(len(h3_matches)) + ") - cada H2 deve ter minimo 2 H3"))
        score -= 5

    # FAQ Schema - visibilidade em buscas por IA (informativo, sem penalidade — FAQ e gerado quando disponivel)
    has_faq = "FAQPage" in html or "faq" in html.lower()
    if not has_faq:
        problemas.append(ProblemaAuditoria(gravidade="BAIXO", dimensao="SEO", problema="FAQ ausente - quando disponivel, aumenta visibilidade em buscas por IA"))
        # sem desconto de score — FAQ e opcional

    # Google Maps / OpenStreetMap embed
    has_maps = any(p in html for p in [
        "maps.google", "google.com/maps",
        "openstreetmap.org", "leafletjs.com",
        "leaflet", "osm", "mapbox.com",
        "maps.googleapis.com",
    ])
    if not has_maps:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="SEO", problema="Falta embed de mapa (Google Maps ou OpenStreetMap) - sinal SEO local"))
        score -= 5

    # Valores/precos proibidos
    if _re.search(r"R\$\s*\d|mensalidade\s+de|plano\s+\w+\s+R\$", html, _re.IGNORECASE):
        problemas.append(ProblemaAuditoria(gravidade="CRITICO", dimensao="Negocio", problema="Site contem precos/valores - PROIBIDO"))
        score -= 20

    # Comentarios de secao para edicao cirurgica
    if "<!-- SECTION:" not in html:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="Manutencao", problema="Falta comentarios de secao para edicao cirurgica"))
        score -= 5

    # Imagens em /tmp/ (expiram)
    if "/tmp/" in html:
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="Assets", problema="Imagens apontando para /tmp/ - vao expirar"))
        score -= 10

    # Dark mode: se briefing pede dark, verificar background escuro
    if briefing and "MODO_VISUAL: DARK" in briefing.upper():
        if "#0a0a0a" not in html and "#111111" not in html and "#1a1a1a" not in html:
            problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="Design", problema="Briefing pede dark mode mas background nao e escuro"))
            score -= 5


    # Emojis no conteudo — cara de IA
    import re as _re_liz
    _emoji_re_liz = _re_liz.compile(u"[🀀-🿿☀-➿🤀-🫿]+")
    _html_sem_scripts = _re_liz.sub(r"<script[\s\S]*?</script>", "", html)
    if _emoji_re_liz.search(_html_sem_scripts):
        _emoji_count = len(_emoji_re_liz.findall(_html_sem_scripts))
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="Design", problema="Emojis no conteudo (" + str(_emoji_count) + ") — cara de IA, usar SVG icons"))
        score -= 20

    # Cor generica #e85d04 hardcoded (fallback nao substituido pela paleta real)
    if html.count("#e85d04") > 3:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="Design", problema="Cor fallback generica hardcoded — paleta da marca nao foi aplicada"))
        score -= 10

    # Toggle dark/light ausente
    if "theme-toggle" not in html and "fralib-motion" not in html:
        problemas.append(ProblemaAuditoria(gravidade="MEDIO", dimensao="UX", problema="Toggle dark/light ausente — fralib-motion nao injetado"))
        score -= 10

    # Conflito de CSS vars — mais de 1 bloco :root
    if html.count(":root") > 2:
        problemas.append(ProblemaAuditoria(gravidade="ALTO", dimensao="CSS", problema="Multiplos blocos :root (" + str(html.count(":root")) + ") — conflito de CSS vars"))
        score -= 15

    score = max(0, score)
    _tem_critico = any(p.gravidade in ("CRITICO", "CRÍTICO") for p in problemas)
    aprovado = score >= SCORE_MINIMO and not _tem_critico

    return AuditoriaTecnica(
        score=score,
        aprovado=aprovado,
        problemas=problemas
    )

# ===== AUDITORIA SEMÂNTICA =====

LIZ_INSTRUCTIONS = """Você é Liz, Auditora de QA Sênior do FraLib.

## TAREFA
Compare o HTML gerado com o briefing do Theo e identifique problemas.

## CRITÉRIOS DE AVALIAÇÃO

### Fidelidade ao Briefing (40 pontos)
- Todas as seções do briefing foram implementadas?
- Os textos seguem o tom e estilo definidos?
- As cores e tipografia estão corretas?

### Qualidade Técnica (30 pontos)
- HTML válido e semântico?
- Responsivo (mobile-first)?
- Performance (lazy loading, otimizações)?

### Conversão (30 pontos)
- CTAs claros e visíveis?
- WhatsApp integrado corretamente?
- Hierarquia visual guia para ação?

## FORMATO DE SAÍDA
Retorne JSON estruturado:
```json
{
  "score": 0-100,
  "aprovado": true/false,
  "problemas": ["problema 1", "problema 2", ...]
}
```

**IMPORTANTE:**
- Score mínimo para aprovação: 90
- Seja rigoroso mas justo
- Foque em problemas que impactam conversão
"""

# Função criar_agente_liz() removida - não é mais necessária com HTTP direto

def clean_json_response(text: str) -> str:
    """Remove markdown code blocks do JSON e valida"""
    if not text or not text.strip():
        raise ValueError("Resposta vazia do LLM")

    # Remover markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()

    # Validar que tem pelo menos { e }
    if '{' not in text or '}' not in text:
        raise ValueError(f"JSON malformado: {text[:100]}")

    # Extrair apenas o JSON (caso tenha texto antes/depois)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)

    return text

def auditoria_semantica(html: str, briefing: str, tentativa: int = 1, cidade: str = "", telefone: str = "", nome: str = "") -> AuditoriaSemantica:
    """
    Auditoria semantica via regex/heuristicas Python puras. Zero LLM.
    Verifica fidelidade ao briefing por presenca de palavras-chave e estrutura HTML.
    """
    problemas = []
    score = 100

    # Usar nome real do lead ou extrair do briefing como fallback
    if nome:
        nome_negocio = nome[:40]
    else:
        _nm = re.search(r"(?:negocio|nome)[^:]*:\s*(\S[^\n]*)", briefing, re.IGNORECASE)
        nome_negocio = _nm.group(1).strip()[:40] if _nm else ""
    # Checar partes do nome (nomes compostos)
    _nome_partes = [p for p in nome_negocio.lower().split() if len(p) > 3]
    _nome_no_html = any(p in html.lower() for p in _nome_partes) if _nome_partes else False
    if nome_negocio and not _nome_no_html:
        problemas.append("Nome do negocio '{}' nao encontrado no HTML".format(nome_negocio))
        score -= 20

    # Verificar secoes obrigatorias
    secoes_obrigatorias = {
        "hero": ["hero", "banner", "destaque"],
        "servicos": ["servico", "service", "oferta"],
        "contato": ["contato", "contact", "whatsapp", "wa.me"],
        "localizacao": ["localizacao", "endereco", "maps", "location"],
    }
    for secao, keywords in secoes_obrigatorias.items():
        if not any(kw in html.lower() for kw in keywords):
            problemas.append("Secao '{}' nao encontrada no HTML".format(secao))
            score -= 10

    # Verificar CTA WhatsApp
    if "wa.me" not in html and "whatsapp" not in html.lower():
        problemas.append("CTA WhatsApp ausente")
        score -= 15

    # Verificar responsividade Tailwind
    if "md:" not in html and "lg:" not in html:
        problemas.append("Classes responsivas Tailwind ausentes (md:/lg:)")
        score -= 10

    # Verificar lazy loading em imagens
    img_tags = re.findall(r"<img[^>]+>", html, re.IGNORECASE)
    imgs_sem_lazy = [t for t in img_tags if "loading" not in t.lower()]
    if len(imgs_sem_lazy) > 3:
        problemas.append("{} imagens sem lazy loading".format(len(imgs_sem_lazy)))
        score -= 5

    # === 3 DIMENSOES OPEN DESIGN ===

    # Dimensao 1 — Especificidade: o site parece feito para ESTE negocio?
    _especifico = False
    if nome_negocio and nome_negocio.lower() in html.lower():
        _especifico = True
    # Verificar se tem dados reais (telefone, endereco, reviews)
    # Telefone: verificar se o telefone real do lead esta no HTML
    _tem_tel = bool(telefone and telefone in html) or bool(re.search(r'\(\d{2}\)\s*[\d\s\-]{8,13}', html))
    # Endereco: aceitar rua/av. OU a cidade real do lead (passada como parametro)
    _tem_end_fixo = any(kw in html.lower() for kw in ["rua ", "av.", "avenida", "travessa", "alameda"])
    _tem_end_cidade = bool(cidade and cidade.lower() in html.lower())
    _tem_end = _tem_end_fixo or _tem_end_cidade
    if not _especifico or (not _tem_tel and not _tem_end):
        problemas.append("Site parece generico — faltam dados especificos do negocio (nome, telefone, endereco)")
        score -= 15

    # Dimensao 2 — Contencao: tem elementos desnecessarios?
    _contadores_zerados = len(re.findall(r'\b0\s*(?:clientes|projetos|anos|avaliacoes|reviews)\b', html, re.IGNORECASE))
    if _contadores_zerados > 0:
        problemas.append(f"{_contadores_zerados} contador(es) zerado(s) encontrado(s) — remover ou usar dados reais")
        score -= 10
    _secoes_vazias = len(re.findall(r'<section[^>]*>\s*</section>', html, re.IGNORECASE))
    if _secoes_vazias > 0:
        problemas.append(f"{_secoes_vazias} secao(oes) vazia(s) encontrada(s)")
        score -= 8
    # Remover atributos placeholder de inputs antes de checar texto placeholder
    _html_sem_inputs = re.sub(r'<(input|textarea)[^>]*>', '', html, flags=re.IGNORECASE)
    _placeholder = len(re.findall(r'lorem ipsum|feature one|feature two|coming soon', _html_sem_inputs, re.IGNORECASE))
    if _placeholder > 0:
        problemas.append(f"Texto placeholder encontrado ({_placeholder} ocorrencias) — substituir por conteudo real")
        score -= 20

    # Dimensao 3 — Consistencia de nicho: tipografia e tom batem com o segmento?
    _tem_whatsapp_cta = "wa.me" in html or "whatsapp" in html.lower()
    _tem_schema = "application/ld+json" in html
    # H1 pode ter tags filhas (br, span, strong) — extrair texto puro
    _h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    _h1_text = re.sub(r'<[^>]+>', ' ', ' '.join(_h1_matches)).strip() if _h1_matches else ''
    _tem_h1_cidade = len(_h1_text) >= 5
    if not _tem_whatsapp_cta:
        problemas.append("CTA WhatsApp ausente — obrigatorio em todas as secoes")
        score -= 15
    if not _tem_schema:
        problemas.append("Schema.org JSON-LD ausente — obrigatorio para SEO local")
        score -= 10
    if not _tem_h1_cidade:
        problemas.append("H1 nao contem cidade — obrigatorio para SEO local")
        score -= 8

    score = max(0, score)
    aprovado = score >= 70

    print(f"[Liz] auditoria_semantica: score={score} aprovado={aprovado} problemas={len(problemas)}")
    return AuditoriaSemantica(
        score=score,
        aprovado=aprovado,
        problemas=problemas,
    )

# ===== AUDITORIA COMPLETA =====

def auditar(
    html: str,
    briefing: str = "",
    tentativa: int = 1,
    lead_id: Optional[int] = None,
    cidade: str = "",
    telefone: str = "",
    nome: str = "",
    user_id: Optional[int] = None,
) -> LizOutput:
    """
    Auditoria completa do HTML (técnica + semântica)

    Args:
        html: HTML a auditar
        briefing: Briefing do Theo
        tentativa: Número da tentativa
        lead_id: ID do lead (para salvar memória)

    Returns:
        Resultado da auditoria completa
    """
    print(f"[Liz] Auditando HTML (tentativa {tentativa})...")

    # Auditoria técnica (síncrona)
    tecnica = auditoria_tecnica(html, briefing=briefing)
    print(f"   Técnica: {tecnica.score}/100 ({len(tecnica.problemas)} problemas)")

    # Auditoria semântica (assíncrona com LLM)
    import time; time.sleep(2)  # Evitar rate limit 429
    semantica = auditoria_semantica(html, briefing, tentativa, cidade=cidade, telefone=telefone, nome=nome)
    print(f"   Semântica: {semantica.score}/100 ({len(semantica.problemas)} problemas)")

    # Score final (60% técnica + 40% semântica)
    score_final = round(tecnica.score * 0.6 + semantica.score * 0.4)
    _veto_tecnico = any(p.gravidade in ("CRITICO", "CRÍTICO") for p in tecnica.problemas)
    aprovado = score_final >= SCORE_MINIMO and not _veto_tecnico

    print(f"   Score Final: {score_final}/100 - {'APROVADO' if aprovado else 'REPROVADO'}")

    # Salvar memória (somente quando user_id presente — multi-tenant)
    if lead_id and user_id:
        salvar_memoria(f"liz_auditoria_{lead_id}_t{tentativa}", {
            "tentativa": tentativa,
            "score_final": score_final,
            "score_tecnico": tecnica.score,
            "score_semantico": semantica.score,
            "aprovado": aprovado,
            "problemas_tecnicos": [p.dict() for p in tecnica.problemas],
            "problemas_semanticos": semantica.problemas
        }, user_id=user_id)

    # Poder de rejeicao: se tentativa < 2 e reprovado, sinalizar para regenerar
    rejeitar = not aprovado and tentativa < 2
    status = "aprovado" if aprovado else ("rejeitar_regenerar" if rejeitar else "revisao_manual")

    if rejeitar:
        problemas_criticos = [p for p in semantica.problemas if any(
            kw in p.lower() for kw in ["placeholder", "generico", "schema", "whatsapp", "h1"]
        )]
        print(f"[Liz] REJEITANDO — tentativa {tentativa}/2 — {len(problemas_criticos)} problemas criticos")
        print(f"[Liz] Instrucoes para regeneracao: {problemas_criticos[:3]}")
    elif status == "revisao_manual":
        print(f"[Liz] 2 tentativas esgotadas — publicando com status revisao_manual (score={score_final})")

    return LizOutput(
        aprovado=aprovado,
        score=score_final,
        tecnica=tecnica,
        semantica=semantica,
        correcoes_cirurgicas=[{"instrucao": p} for p in semantica.problemas[:5]] if rejeitar else [],
        tentativa=tentativa
    )

# ===== TESTE =====


if __name__ == "__main__":
    print("Liz QA Agent - Use via import")


# ===== MANUTENCAO: EDITAR SECAO =====

def editar_secao(html: str, secao: str, instrucao: str) -> str:
    """Edita apenas uma secao do HTML sem regenerar o site inteiro."""
    from llm_direct import call_claude
    pattern = rf'<!--\s*SECTION:\s*{secao}\s*-->(.*?)<!--\s*/SECTION:\s*{secao}\s*-->'
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if not match:
        print("[Liz] Secao nao encontrada: " + secao)
        secoes = re.findall(r'<!-- SECTION:(\w+) -->', html)
        print("[Liz] Secoes disponiveis: " + str(secoes))
        return html
    bloco_original = match.group(0)
    conteudo = match.group(1).strip()
    print("[Liz] Editando secao " + secao + " (" + str(len(conteudo)) + " chars)...")
    prompt = "REGRAS ABSOLUTAS:\n"
    prompt += "1. Voce e um compilador estrito. Sua UNICA funcao e corrigir erros de sintaxe (tags HTML nao fechadas) apontados na auditoria.\n"
    prompt += "2. E ESTRITAMENTE PROIBIDO adicionar novos textos, imagens, SVGs ou mudar as classes Tailwind originais.\n"
    prompt += "3. E ESTRITAMENTE PROIBIDO reescrever o design. Mantenha o codigo original intacto, adicionando APENAS os caracteres exatos que faltavam para fechar as tags.\n"
    prompt += "4. Retorne APENAS o HTML corrigido, sem markdown, sem explicacoes.\n\n"
    prompt += "PROBLEMA A CORRIGIR: " + instrucao + "\n\n"
    prompt += "BLOCO ATUAL (corrija apenas o necessario):\n" + conteudo + "\n\n"
    prompt += "Retorne apenas o HTML interno do bloco corrigido (sem delimitadores SECTION)."
    html_editado = call_claude(
        system="Voce e um compilador estrito de HTML. Corrija APENAS erros de sintaxe. NUNCA reescreva, expanda ou redesenhe. Retorne APENAS HTML.",
        user=prompt,
        model="haiku",
        max_tokens=8000,
        temperature=0.0,
        agent_name="liz",
    )
    # Extração estrita: pegar apenas o HTML, ignorar justificativas em texto plano
    import re as _re_liz
    _match_liz = _re_liz.search(r'```html\s*(.*?)\s*```', html_editado, _re_liz.DOTALL | _re_liz.IGNORECASE)
    if _match_liz:
        html_editado = _match_liz.group(1).strip()
    else:
        html_editado = html_editado.replace("```html", "").replace("```", "").strip()
    # Remover qualquer texto antes da primeira tag HTML
    _first_tag = _re_liz.search(r'<[a-zA-Z]', html_editado)
    if _first_tag and _first_tag.start() > 0:
        html_editado = html_editado[_first_tag.start():]
    novo_bloco = "<!-- SECTION:" + secao + " -->\n" + html_editado + "\n<!-- /SECTION:" + secao + " -->"
    html_final = html.replace(bloco_original, novo_bloco)
    print("[Liz] Secao " + secao + " editada com sucesso")
    return html_final


def listar_secoes(html: str) -> list:
    """Lista todas as secoes disponiveis no HTML."""
    return re.findall(r'<!-- SECTION:(\w+) -->', html)


