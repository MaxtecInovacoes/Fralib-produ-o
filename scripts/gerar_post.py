#!/usr/bin/env python3
"""
Gerador de posts com TOM HUMANO.
Estilo conversacional, opinião, exemplos do dia-a-dia.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("Instale: pip install requests", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
TENDENCIAS_FILE = Path(__file__).parent / "tendencias.json"

CATEGORIES = {
    "marketing": {"name": "Marketing", "color": "#9333ea"},
    "ia": {"name": "IA & Automação", "color": "#00FFB3"},
    "vendas": {"name": "Vendas", "color": "#FFB800"},
    "freelancer": {"name": "Freelancer", "color": "#7c3aed"},
    "tech": {"name": "Tecnologia", "color": "#c084fc"},
    "negócios": {"name": "Negócios", "color": "#22d3a0"},
    "finanças": {"name": "Finanças", "color": "#FF6B6B"},
    "produtividade": {"name": "Produtividade", "color": "#4ECDC4"},
}


# ============================================================================
# TOM HUMANO - PROMPT ENGINEERED
# ============================================================================

HUMAN_TONE_PROMPT = """Você é um redator brasileiro que escreve como se estivesse conversando com um amigo no WhatsApp.

Tom: conversacional, opinativo, direto, sem corporativo.

Regras OBRIGATÓRIAS:
1. Comece com frase de impacto pessoal ("Sabe aquele momento...", "Vou ser sincero...", "Confesso que...")
2. Use "você" e "a gente", nunca "o leitor" ou "o profissional"
3. Inclua pelo menos 1 opinião genuína (algo como "na minha visão..." ou "sinceramente, acho que...")
4. Dê 3 dicas práticas que a pessoa pode aplicar HOJE
5. Termine com reflexão ou pergunta (não com CTA agressivo)
6. PROIBIDO usar: "Neste artigo", "É importante", "Conclui-se", "Vale ressaltar", "Em suma"
7. PROIBIDO: bullet points genéricos. Use parágrafos corridos como conversa
8. Use no máximo 600 palavras
9. Termine mencionando o FraLib de forma orgânica (não forçada)

Tópico: {TOPIC}
Categoria: {CATEGORY}

Estrutura:
- Parágrafo 1: Impacto pessoal + conexão
- Parágrafo 2: Explicação simples (como se falasse com amigo)
- Parágrafo 3-5: 3 dicas práticas
- Parágrafo 6: Sua opinião genuína
- Parágrafo 7: Onde aprender mais (mencionar FraLib aqui)

Retorne APENAS o conteúdo do post, em HTML, com h2 para os títulos das seções, p para parágrafos. SEM doctype, SEM html, SEM body."""


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def slugify(text: str) -> str:
    """Converte texto para slug URL-friendly."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:80]


def call_llm_for_post(topic: str, category: str) -> Optional[str]:
    """Gera post via OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    prompt = HUMAN_TONE_PROMPT.replace("{TOPIC}", topic).replace("{CATEGORY}", category)

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "anthropic/claude-haiku-4-5",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0.8,
            },
            timeout=60,
        )

        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)

    return None


def generate_fallback_post(topic: str, category: str) -> str:
    """Conteúdo fallback com tom humano (caso LLM não disponível)."""

    return f"""
<h2>Sabe aquela sensação?</h2>
<p>Quando você ouve falar de <strong>{topic.lower()}</strong> pela primeira vez, bate aquela dúvida: "isso é pra mim mesmo ou é papo de gente grande"? Foi exatamente assim que me senti quando comecei a pesquisar sobre isso.</p>

<p>Mas depois de fuçar bastante, testar ferramentas e conversar com gente que tá usando no dia a dia, a resposta ficou clara: <strong>sim, é pra você também</strong>. Vou te contar o que descobri.</p>

<h2>Mas afinal, o que isso significa na prática?</h2>
<p>Em vez de definir com termos difíceis, deixa eu te explicar como se eu tivesse contando isso num café: imagine automatizar aquela parte chata do seu trabalho que te toma horas — e sobrar tempo pra você focar no que realmente importa.</p>

<p>Pra quem vende site, por exemplo, isso significa <strong>parar de prospectar cliente um por um no Google</strong> e deixar a tecnologia fazer essa parte. O resto é seu: fechar a venda e entregar.</p>

<h2>3 coisas práticas que você pode fazer HOJE</h2>
<p><strong>1. Testa com 1 cliente só.</strong> Não precisa automatizar tudo de uma vez. Pega um caso real e vê como funciona na prática. Erro pequeno é melhor que plano perfeito que nunca sai do papel.</p>
<p><strong>2. Mede tempo vs. resultado.</strong> Antes de adotar qualquer ferramenta, cronometra quanto tempo você gasta hoje naquela tarefa. Depois de adotar, mede de novo. Você vai se surpreender com a diferença.</p>
<p><strong>3. Não cai em armadilha de "tudo ou nada".</strong> Quem começa pequeno e vai crescendo tem mais chance de sucesso do que quem tenta revolucionar tudo de uma vez. Esse último cenário costuma dar burnout.</p>

<h2>Minha opinião sincera</h2>
<p>Sinceramente? A maioria das pessoas ainda tá fazendo as coisas do jeito antigo porque <strong>tem medo de testar</strong>. Mas quem testa primeiro, na frente, leva vantagem. A janela de oportunidade tá aberta agora — em 2 anos vai estar saturada.</p>

<p>Eu não tô dizendo que é fácil ou que vai resolver tudo da noite pro dia. Tô dizendo que vale o teste. E se não funcionar pra você, você volta pro jeito antigo. Sem drama.</p>

<h2>Onde aprender mais</h2>
<p>Se você quer se aprofundar, recomendo começar pelo <strong>FraLib</strong> — uma plataforma brasileira que faz exatamente isso: acha cliente no Google Maps, cria site e vende no WhatsApp. Você não mexe em nada, só recebe o resultado.</p>

<p>Tem também bastante conteúdo bom no YouTube de gente que já testa ferramenta de IA no trabalho real. Procura por "automação para freelancers BR" e você acha coisa útil.</p>

<p>No fim do dia, o que importa é <strong>você testar</strong> e ver no seu próprio negócio. Confia no processo — e bom trabalho!</p>
"""


# ============================================================================
# GERADOR DE POST
# ============================================================================

def generate_post_html(topic: str, category: str, slug: str) -> str:
    """Gera HTML do post com tom humano."""

    cat = CATEGORIES.get(category, CATEGORIES["negócios"])
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    iso_date = now.isoformat()

    # Tenta LLM primeiro
    print(f"  Tentando LLM para: {topic}")
    body = call_llm_for_post(topic, cat["name"])

    if not body:
        print(f"  Usando fallback (sem LLM) para: {topic}")
        body = generate_fallback_post(topic, cat["name"])

    # Limpa body (remove doctype se vier)
    body = re.sub(r"<!DOCTYPE[^>]+>", "", body, flags=re.IGNORECASE)
    body = re.sub(r"</?html[^>]*>", "", body, flags=re.IGNORECASE)
    body = re.sub(r"</?body[^>]*>", "", body, flags=re.IGNORECASE)
    body = re.sub(r"<head>.*?</head>", "", body, flags=re.IGNORECASE | re.DOTALL)
    body = body.strip()

    # Garante que tem h2 e p
    if "<h2" not in body:
        body = f"<h2>Sabe aquela sensação?</h2><p>{body}"

    # Calcula tempo de leitura
    word_count = len(re.findall(r"\b\w+\b", body))
    read_time = max(2, word_count // 200)

    # Gera excerpt
    first_p = re.search(r"<p>([^<]+)</p>", body)
    excerpt = (first_p.group(1) if first_p else topic)[:160] + "..."

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{topic} — Blog FraLib</title>
<meta name="description" content="{excerpt}">
<meta name="keywords" content="{topic.lower()}, {category}, freelancer, fralib, marketing digital">
<meta name="author" content="Redação FraLib">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://seunegociofralib.site/blog/posts/{slug}.html">

<meta property="og:title" content="{topic}">
<meta property="og:description" content="{excerpt}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://seunegociofralib.site/blog/posts/{slug}.html">
<meta property="og:image" content="https://seunegociofralib.site/images/og-blog-default.png">
<meta property="og:locale" content="pt_BR">
<meta property="article:published_time" content="{iso_date}">
<meta property="article:modified_time" content="{iso_date}">
<meta property="article:author" content="Redação FraLib">
<meta property="article:section" content="{cat['name']}">
<meta property="article:tag" content="{category}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{topic}">
<meta name="twitter:description" content="{excerpt}">
<meta name="twitter:image" content="https://seunegociofralib.site/images/og-blog-default.png">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{topic}",
  "description": "{excerpt}",
  "datePublished": "{iso_date}",
  "dateModified": "{iso_date}",
  "author": {{
    "@type": "Organization",
    "name": "Redação FraLib",
    "url": "https://seunegociofralib.site"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "FraLib OS",
    "logo": {{
      "@type": "ImageObject",
      "url": "https://seunegociofralib.site/images/Logo%20FraLib.png",
      "width": 512,
      "height": 512
    }}
  }},
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "https://seunegociofralib.site/blog/posts/{slug}.html"
  }},
  "articleSection": "{cat['name']}",
  "keywords": "{category}, freelancer, marketing digital, fralib"
}}
</script>

<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '1022692323751129');
fbq('track', 'PageView');
</script>

<link rel="stylesheet" href="/design-system.css">
<style>
:root{{--fl-bg:#0a0714;--fl-bg-card:#12121a;--fl-text:#f0f0f5;--fl-text-muted:#b0b0c8;--fl-purple-300:#c084fc;--cyan:#00FFB3;--gold:#FFB800}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:var(--fl-bg);color:var(--fl-text);line-height:1.8;max-width:780px;margin:0 auto;padding:100px 24px 60px;font-size:17px}}
nav{{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;justify-content:space-between;align-items:center;padding:14px 32px;background:rgba(6,6,8,0.95);backdrop-filter:blur(20px);border-bottom:1px solid var(--fl-border,rgba(147,51,234,0.12))}}
nav .nav-brand{{font-family:'Press Start 2P',monospace;font-size:14px;color:var(--cyan);text-decoration:none}}
nav .nav-cta{{padding:10px 18px;background:#FACC15;color:#000;font-family:'Press Start 2P',monospace;font-size:8px;text-decoration:none;box-shadow:inset -2px -2px 0 #A16207,inset 2px 2px 0 #FDE68A,0 3px 0 #713F12}}
h1{{font-family:'Press Start 2P',monospace;font-size:clamp(14px,2vw,20px);line-height:1.6;color:var(--fl-text);margin-bottom:24px;margin-top:32px}}
h2{{font-size:22px;font-weight:700;color:var(--fl-purple-300);margin:32px 0 12px;line-height:1.3}}
p{{margin-bottom:18px;color:var(--fl-text)}}
strong{{color:var(--cyan);font-weight:600}}
a{{color:var(--cyan);text-decoration:none;border-bottom:1px solid rgba(0,255,179,0.3)}}
a:hover{{border-bottom-color:var(--cyan)}}
.meta{{display:flex;gap:16px;color:var(--fl-text-muted);font-size:13px;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid rgba(147,51,234,0.12);font-family:'JetBrains Mono',monospace;flex-wrap:wrap}}
.tag{{display:inline-block;padding:3px 10px;background:rgba(147,51,234,0.15);color:var(--fl-purple-300);font-size:10px;font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;margin-right:6px}}
.cta-box{{background:linear-gradient(135deg,rgba(0,255,179,0.06),rgba(147,51,234,0.06));border:1px solid var(--cyan);padding:28px;margin:40px 0 24px;position:relative}}
.cta-box h3{{font-family:'Press Start 2P',monospace;font-size:12px;color:var(--cyan);margin-bottom:12px;line-height:1.6}}
.cta-box p{{font-size:15px;margin-bottom:16px}}
.cta-button{{display:inline-block;background:#FACC15;color:#000;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:10px;text-decoration:none;letter-spacing:1px;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12}}
.cta-button:hover{{background:#FDE047}}
.breadcrumb{{font-size:12px;color:var(--fl-text-muted);margin-bottom:20px;font-family:'JetBrains Mono',monospace}}
.breadcrumb a{{color:var(--fl-text-muted);border:none}}
.back-link{{margin-top:48px;padding-top:24px;border-top:1px solid rgba(147,51,234,0.12);text-align:center}}
.back-link a{{color:var(--fl-text-muted);font-size:13px;border:none}}
footer-note{{display:block;margin-top:32px;padding-top:16px;border-top:1px solid rgba(147,51,234,0.12);color:var(--fl-text-muted);font-size:12px;font-style:italic}}
@media(max-width:768px){{body{{padding:80px 18px 40px;font-size:16px}}nav{{padding:10px 18px}}}}
</style>
</head>
<body>
<nav>
  <a href="/" class="nav-brand">FRA LIB</a>
  <a href="/login?signup=1&utm_source=blog_organico&utm_medium=nav&utm_campaign={slug}" class="nav-cta">TESTAR GRÁTIS</a>
</nav>

<div class="breadcrumb">
  <a href="/">Home</a> / <a href="/blog/">Blog</a> / <span>{cat['name']}</span>
</div>

<span class="tag">{cat['name']}</span>
<span class="tag">{now.strftime("%d/%m/%Y")}</span>

<h1>{topic}</h1>

<div class="meta">
  <span>Por Redação FraLib</span>
  <span>·</span>
  <span>{date_str}</span>
  <span>·</span>
  <span>{read_time} min de leitura</span>
</div>

{body}

<div class="cta-box">
  <h3>QUER APLICAR ISSO NO SEU NEGÓCIO?</h3>
  <p>O <strong>FraLib</strong> faz exatamente o que falamos aqui: acha cliente, faz site e vende no WhatsApp. Você só fica com o lucro. Sem fazer nada.</p>
  <a href="/login?signup=1&utm_source=blog_organico&utm_medium=cta_box&utm_campaign={slug}" class="cta-button">TESTA 7 DIAS GRÁTIS →</a>
</div>

<p style="margin-top:32px;color:var(--fl-text-muted);font-size:14px">Gostou? Compartilha com alguém que precisa ler isso. E se quiser receber mais posts assim, <a href="/blog/rss.xml">assina o RSS</a> ou <a href="/login?signup=1&utm_source=blog_organico&utm_medium=text_link&utm_campaign={slug}">testa o FraLib</a> — vale 7 dias grátis.</p>

<div class="back-link">
  <a href="/blog/">← Ver todos os posts do Blog FraLib</a>
</div>

<footer-note>Post gerado pela equipe FraLib. A gente revisa antes de publicar — mas se achar algo esquisito, <a href="mailto:redacao@fralib.site">fala com a gente</a>.</footer-note>

</body>
</html>"""

    return html, excerpt, read_time, date_str


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Gera posts a partir de tendências."""

    print(f"[{datetime.now()}] Gerando posts...")

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    if not TENDENCIAS_FILE.exists():
        print(f"  Arquivo de tendências não encontrado: {TENDENCIAS_FILE}")
        print(f"  Rode primeiro: python scripts/buscar_tendencias.py")
        return 1

    data = json.loads(TENDENCIAS_FILE.read_text(encoding="utf-8"))
    trends = data.get("trends", [])

    if not trends:
        print("  Nenhuma tendência encontrada.")
        return 0

    print(f"  {len(trends)} tendências disponíveis")

    generated = []
    for i, trend in enumerate(trends[:3]):  # Gera 3 posts por execução
        topic = trend["topic"]
        category = trend.get("category", "negócios")
        slug = slugify(topic)

        post_file = POSTS_DIR / f"{slug}.html"
        if post_file.exists():
            print(f"  Skip (existe): {slug}")
            continue

        print(f"  Gerando [{i+1}/3]: {topic}")

        try:
            html, excerpt, read_time, date_str = generate_post_html(topic, category, slug)
            post_file.write_text(html, encoding="utf-8")
            print(f"    ✓ Salvo: {post_file.name}")

            generated.append({
                "slug": slug,
                "title": topic,
                "category": category,
                "date": date_str,
                "read_time": str(read_time),
                "excerpt": excerpt,
            })
        except Exception as e:
            print(f"    ✗ Erro: {e}", file=sys.stderr)

    print(f"\n✓ {len(generated)} posts gerados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
