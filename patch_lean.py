"""Patch: strengthen prompt in _render_full_document and fix AOS fallback."""
import re

p = r'C:\fralib\builder_lean.py'
with open(p, encoding='utf-8') as f:
    src = f.read()

# 1) Strengthen prompt: replace the ESTUTURA block + add explicit requirements
old_prompt = """ESTRUTURA DE SEÇÕES (gerar TODAS, nesta ordem):
1. NAVBAR sticky (nome + links internos: Diferenciais, Planos, FAQ, Contato + CTA).
2. HERO — <h1> persuasivo, subtítulo, 2 CTAs (primário + secundário), imagem de fundo
   do Unsplash (https://images.unsplash.com/photo-1534438327276-14e5300c3a48).
3. DIFERENCIAIS — 3 cards (icone + título + descrição), grid responsivo 1→3 colunas.
4. {review_section_hint.rstrip()}
5. PLANOS — 3 cards (Mensal / Trimestral / Anual), destaque no plano "mais popular".
6. FAQ — perguntas/respostas usando <details> + <summary> (NUNCA <ul>/<li>).
7. CONTATO — telefone ({spec.get('phone','N/A')}), WhatsApp, endereço ({spec.get('address','N/A')}),
   horário de funcionamento, botão flutuante de WhatsApp.
8. FOOTER — nome do negócio + copyright.

SEO: <title> com "NOME | CATEGORIA em CIDADE". <meta description> persuasiva (≤160 chars).
Schema.org: LocalBusiness com nome, endereço, telefone, cidade, horário."""

new_prompt = """REGRAS DE GERAÇÃO:
- Gere o HTML COMPLETO de ponta a ponta, de <!DOCTYPE html> até </html>.
- Use Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>).
- Use Google Fonts via <link> no <head> (heading + body).
- Inclua AOS CSS/JS no <head>/<body> (o pipeline injeta automaticamente, mas pode incluir).
- NUNCA use <ul>/<li> para FAQ — use <details>/<summary>.
- NUNCA invente depoimentos — use apenas os da lista fornecida no bloco DEPOIMENTOS abaixo.
- NUNCA use `min-w-[Npx]` em grids ou cards (causa coluna esmagada em mobile).
- Títulos (h1, h2): SEMPRE `max-w-2xl w-full break-normal`. Proibido: whitespace-nowrap, truncate, overflow-hidden em headings.
- Hero: imagem de fundo do Unsplash com overlay gradiente escuro ≥60% opacidade. Texto com `text-white`.
- Toda seção animável: data-aos="fade-up" + data-aos-delay="100"/"200"/"300".

ORDEM OBRIGATÓRIA DAS SEÇÕES (não pode faltar nenhuma):
1. NAVBAR — sticky, com logo + links âncora (Diferenciais, Planos, FAQ, Contato) + CTA primário.
2. HERO — <h1> persuasivo com nome do negócio, subtítulo USP, 2 CTAs (primário + outline),
   imagem de fundo profissional do nicho (https://images.unsplash.com/photo-1534438327276-14e5300c3a48),
   overlay gradiente escuro. Texto 100% branco (text-white).
3. COMPROMISSOS E DIFERENCIAIS — 3 cards com ícone + título + descrição. Grid 1 coluna (mobile) → 3 (desktop).
4. {review_section_hint.rstrip()}
5. PLANOS — 3 cards de preço (Mensal, Trimestral, Anual). Destaque visual no "mais popular".
6. FAQ — 3 a 5 perguntas usando <details>/<summary> (NUNCA <ul>/<li>).
7. CONTATO — telefone ({spec.get('phone','N/A')}), WhatsApp, endereço ({spec.get('address','N/A')}),
   horário de funcionamento, botão flutuante de WhatsApp (fixed bottom-right).
8. FOOTER — nome do negócio + copyright.

SEO:
- <title>: "NOME | CATEGORIA em CIDADE"
- <meta name="description">: texto persuasivo ≤160 chars.
- Schema.org: LocalBusiness com nome, endereço, telefone, cidade, horário."""

if old_prompt in src:
    src = src.replace(old_prompt, new_prompt)
    print("[OK] Prompt strengthened")
else:
    print("[FAIL] Could not find prompt block")
    # Try to show what's there
    idx = src.find('ESTRUTURA DE SE')
    if idx >= 0:
        print(f"Found 'ESTRUTURA DE SE' at offset {idx}")
        print(repr(src[idx:idx+200]))
    else:
        print("Block not found at all")

# 2) AOS fallback: make inject_deterministic_assets robust when no </head>/</body>
old_aos = '''    html = re.sub(r"(?is)(</head>)", f"{brand_style}\\n{aos_head}\\n\\1", html, count=1)
    html = re.sub(r"(?is)(</body>)", f"{aos_body}\\n\\1", html, count=1)
    if "</head>" not in html.lower():
        html = f"{brand_style}\\n{aos_head}\\n{html}"
    if "</body>" not in html.lower():
        html = f"{html}\\n{aos_body}"
    return html'''

new_aos = '''    if "</head>" in html.lower():
        html = re.sub(r"(?is)(</head>)", f"{brand_style}\\n{aos_head}\\n\\1", html, count=1)
    else:
        html = f"{brand_style}\\n{aos_head}\\n{html}"
    if "</body>" in html.lower():
        html = re.sub(r"(?is)(</body>)", f"{aos_body}\\n\\1", html, count=1)
    else:
        html = f"{html}\\n{aos_body}"
    return html'''

if old_aos in src:
    src = src.replace(old_aos, new_aos)
    print("[OK] AOS fallback improved")
else:
    print("[FAIL] AOS block not found")

with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print(f"Total size: {len(src)} bytes")

import py_compile
try:
    py_compile.compile(p, doraise=True)
    print("[OK] py_compile")
except py_compile.PyCompileError as e:
    print(f"[FAIL] py_compile: {e}")
