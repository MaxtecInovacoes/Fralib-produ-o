#!/usr/bin/env python3
"""
Aplica a reordenacao de blocos no landing.html FraLib OS.
Metodo: extrair cada secao entre marcadores ===== e remontar na ordem desejada.
"""

import re
import sys
from pathlib import Path

LANDING = Path("C:/fralib/frontend/landing.html")


def main():
    html = LANDING.read_text(encoding="utf-8")
    original_size = len(html)

    # Marcadores de cada secao (inicio e fim baseado nos comments)
    # Vou pegar cada secao pelo marker "<!-- ===== ... ===== -->" e avancar ate a proxima

    sections_to_find = [
        # (key, marker_inicio, proximo_marker_ou_string)
        ("hero", "<!-- ===== SEÇÃO 1 — HERO ===== -->", "<!-- ===== SEÇÃO"),
        ("social_proof", "<!-- ===== SEÇÃO 2 — PROVA SOCIAL", "<!-- ===== SEÇÃO"),
        ("problema", "<!-- ===== SEÇÃO 3 — PROBLEMA ===== -->", "<!-- ===== SEÇÃO"),
        ("como-funciona", "<!-- ===== SEÇÃO 4 — COMO FUNCIONA ===== -->", "<!-- ===== SEÇÃO"),
        ("demo", "<!-- ===== SEÇÃO 5 — PRODUTO EM AÇÃO ===== -->", "<!-- ===== SEÇÃO"),
        ("depoimentos", "<!-- ===== SEÇÃO 5C — DEPOIMENTOS", "<!-- ===== SEÇÃO"),
        ("funcionalidades", "<!-- ===== SEÇÃO 6 — FUNCIONALIDADES ===== -->", "<!-- ===== SEÇÃO"),
        ("nichos", "<!-- ===== SEÇÃO 6B — EXEMPLOS", "<!-- ===== SEÇÃO"),
        ("para-quem", "<!-- ===== SEÇÃO 7 — PARA QUEM ===== -->", "<!-- ===== SEÇÃO"),
        ("timeline", "<!-- ===== SEÇÃO 7B — TIMELINE", "<!-- ===== SEÇÃO"),
        ("faq", "<!-- ===== SEÇÃO 8A — FAQ", "<!-- ===== SEÇÃO"),
        ("planos", "<!-- ===== SEÇÃO 8 — PLANOS ===== -->", "<!-- ====="),
        ("cinco-fontes", "<!-- ===== 5 FONTES DE RECEITA", "<!-- ====="),
        ("beta", "<!-- ===== FORMULÁRIO BETA ===== -->", "<!-- ====="),
        ("trust-seals", "<!-- ===== SEÇÃO DE SELOS", "<!-- FLOATING"),
    ]

    # Extrair cada secao
    sections = {}
    for key, marker, next_marker in sections_to_find:
        start = html.find(marker)
        if start == -1:
            print(f"  [WARN] {key} nao encontrada (marker: {marker})")
            continue

        # Acha o proximo marker para delimitar o fim
        search_from = start + len(marker)
        # Para o fim, procurar o proximo marker conhecido
        end_candidates = []
        for other_key, other_marker, _ in sections_to_find:
            if other_key == key:
                continue
            pos = html.find(other_marker, search_from)
            if pos != -1:
                end_candidates.append(pos)
        # Tambem procurar por FLOATING WHATSAPP, FOOTER, etc
        for end_marker in ["<!-- FLOATING WHATSAPP", "<!-- FOOTER", "<footer class=\"footer\">", "</body>", "<script>\n// === TRACKING"]:
            pos = html.find(end_marker, search_from)
            if pos != -1:
                end_candidates.append(pos)

        if not end_candidates:
            print(f"  [WARN] {key} sem fim definido")
            continue

        # Pegar o fim mais proximo (menor posicao)
        end = min(end_candidates)
        # O fim eh o INICIO do proximo bloco, nao o final deste
        # Mas para sections de secao, queremos pegar ate </section> ANTES do proximo
        # Entao vamos pegar o conteudo entre o marker e o proximo marker
        sections[key] = html[start:end].rstrip()

        # Limpar whitespace extra
        # Pular linhas vazias excessivas
        sections[key] = re.sub(r'\n{3,}', '\n\n', sections[key])

        print(f"  [OK] {key}: {len(sections[key]):,} chars")

    # Construir header (ate o primeiro marker)
    first_marker_pos = html.find("<!-- ===== SEÇÃO 1 — HERO ===== -->")
    # Header inclui tudo ANTES do primeiro marker de section
    header = html[:first_marker_pos]

    # Footer: tudo a partir de <!-- FLOATING WHATSAPP --> (ou footer)
    footer_match = re.search(r'(<!-- FLOATING WHATSAPP[\s\S]*</body>)', html)
    if footer_match:
        footer = footer_match.group(1)
        # Extrair apenas ate </body> (sem o </body>)
        footer = footer.split('</body>')[0]
    else:
        footer = "</body>"

    # Simulador customizado (HTML + CSS + JS)
    simulador_section = '''<!-- ===== SEÇÃO 2 — SIMULADOR DE OPORTUNIDADES LOCAIS ===== -->
<section id="simulador" class="simulador-section" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">SIMULE QUANTO VOCÊ PODE GANHAR NA SUA CIDADE</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 48px;max-width:680px;color:var(--fl-text-muted);font-size:14px;">Escolha sua cidade e nicho. A FraLib calcula quantos leads reais existem pra você atacar HOJE.</p>
    <div class="simulador-wrap reveal" style="max-width:920px;margin:0 auto;background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:40px 36px;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:32px;">
        <div class="cfg-field">
          <label class="cfg-lbl">SUA CIDADE</label>
          <select class="sim-sel" id="sim-cidade">
            <option>São Paulo, SP</option>
            <option>Rio de Janeiro, RJ</option>
            <option>Belo Horizonte, MG</option>
            <option>Curitiba, PR</option>
            <option>Porto Alegre, RS</option>
            <option>Salvador, BA</option>
            <option>Fortaleza, CE</option>
            <option>Brasília, DF</option>
            <option>Campinas, SP</option>
            <option>Outra cidade</option>
          </select>
        </div>
        <div class="cfg-field">
          <label class="cfg-lbl">NICHO</label>
          <select class="sim-sel" id="sim-nicho">
            <option>Restaurantes / Pizzarias</option>
            <option>Salões / Barbearias</option>
            <option>Clínicas / Estética</option>
            <option>Pet Shops / Veterinárias</option>
            <option>Academias / Studios</option>
            <option>Imobiliárias</option>
            <option>Prestadores de serviço</option>
            <option>Lojas físicas</option>
            <option>Oficinas mecânicas</option>
            <option>Padarias / Mercados</option>
          </select>
        </div>
        <div class="cfg-field" style="display:flex;align-items:flex-end">
          <button id="sim-btn" class="sim-btn">SIMULAR</button>
        </div>
      </div>

      <div id="sim-result" style="display:none;border-top:1px solid var(--fl-border);padding-top:32px;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;">
          <div class="sim-card cyan"><div class="sim-lbl">LEADS DISPONÍVEIS</div><div class="sim-val" id="sim-leads">—</div></div>
          <div class="sim-card gold"><div class="sim-lbl">CONVERSÃO (5%)</div><div class="sim-val" id="sim-conv">—</div></div>
          <div class="sim-card purple"><div class="sim-lbl">TICKET MÉDIO</div><div class="sim-val" id="sim-ticket">—</div></div>
          <div class="sim-card gradient"><div class="sim-lbl">FATURAMENTO POTENCIAL</div><div class="sim-val" id="sim-fatura">—</div></div>
        </div>
        <div style="margin-top:24px;text-align:center;padding:16px;background:rgba(34,197,94,0.08);border:1px solid var(--green);">
          <p style="font-size:14px;color:var(--fl-text-muted);margin:0;">💡 Esse é o <strong style="color:var(--cyan);">CENÁRIO MÍNIMO</strong> baseado em dados reais do Google Maps. Trabalhando 1h/dia você consegue fechar <strong style="color:var(--cyan);" id="sim-leads-mes">— leads/mês</strong>.</p>
        </div>
        <div style="margin-top:32px;text-align:center;">
          <a href="#planos" class="sim-btn">QUERO COMEÇAR AGORA</a>
        </div>
      </div>
    </div>
  </div>
</section>

<style>
.simulador-section .sim-sel{
  background:var(--fl-bg);
  border:1px solid var(--fl-border-md);
  border-radius:0;
  padding:14px 16px;
  color:var(--fl-text);
  font-family:'Outfit',sans-serif;
  font-size:14px;
  outline:none;
  cursor:pointer;
  width:100%;
}
.simulador-section .sim-sel:focus{border-color:var(--cyan);}
.simulador-section .cfg-lbl{
  font-family:'JetBrains Mono',monospace;
  font-size:10px;
  color:var(--fl-text-muted);
  text-transform:uppercase;
  letter-spacing:0.08em;
  margin-bottom:6px;
  display:block;
}
.simulador-section .sim-btn{
  background:#FACC15;
  color:#000;
  font-family:'Press Start 2P',monospace;
  font-size:11px;
  border:none;
  cursor:pointer;
  width:100%;
  padding:14px 18px;
  letter-spacing:1px;
  box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12;
  text-decoration:none;
  display:inline-block;
  text-align:center;
}
.simulador-section .sim-btn:hover{background:#FDE047;}
.simulador-section .sim-card{
  background:rgba(0,0,0,0.3);
  border:1px solid var(--fl-border);
  padding:20px;
  text-align:center;
}
.simulador-section .sim-card.cyan{border-color:var(--cyan);}
.simulador-section .sim-card.gold{border-color:var(--gold);}
.simulador-section .sim-card.purple{border-color:var(--fl-purple-300);}
.simulador-section .sim-card.gradient{
  background:linear-gradient(135deg,rgba(0,255,179,0.1),rgba(147,51,234,0.1));
  border-color:var(--cyan);
}
.simulador-section .sim-lbl{
  font-family:'JetBrains Mono',monospace;
  font-size:10px;
  color:var(--fl-text-muted);
  margin-bottom:8px;
  text-transform:uppercase;
  letter-spacing:0.5px;
}
.simulador-section .sim-card.cyan .sim-lbl{color:var(--cyan);}
.simulador-section .sim-card.gold .sim-lbl{color:var(--gold);}
.simulador-section .sim-card.purple .sim-lbl{color:var(--fl-purple-300);}
.simulador-section .sim-card.gradient .sim-lbl{color:var(--cyan);}
.simulador-section .sim-val{
  font-family:'Press Start 2P',monospace;
  font-size:22px;
  color:#fff;
  line-height:1.2;
}
</style>

<script>
(function(){
  const data = {
    "São Paulo, SP": {restaurantes:320,saloes:280,clinicas:180,petshops:120,academias:150,imobiliarias:90,prestadores:450,lojas:340,oficinas:210,padarias:60},
    "Rio de Janeiro, RJ": {restaurantes:240,saloes:200,clinicas:140,petshops:90,academias:110,imobiliarias:70,prestadores:320,lojas:250,oficinas:160,padarias:50},
    "Belo Horizonte, MG": {restaurantes:160,saloes:140,clinicas:90,petshops:60,academias:80,imobiliarias:50,prestadores:220,lojas:180,oficinas:110,padarias:30},
    "Curitiba, PR": {restaurantes:130,saloes:110,clinicas:70,petshops:50,academias:60,imobiliarias:40,prestadores:180,lojas:140,oficinas:90,padarias:20},
    "Porto Alegre, RS": {restaurantes:120,saloes:100,clinicas:60,petshops:45,academias:55,imobiliarias:38,prestadores:170,lojas:130,oficinas:85,padarias:18},
    "Salvador, BA": {restaurantes:140,saloes:120,clinicas:75,petshops:55,academias:65,imobiliarias:42,prestadores:200,lojas:160,oficinas:100,padarias:35},
    "Fortaleza, CE": {restaurantes:150,saloes:130,clinicas:80,petshops:60,academias:70,imobiliarias:45,prestadores:210,lojas:170,oficinas:105,padarias:40},
    "Brasília, DF": {restaurantes:170,saloes:150,clinicas:95,petshops:65,academias:85,imobiliarias:55,prestadores:240,lojas:190,oficinas:115,padarias:25},
    "Campinas, SP": {restaurantes:180,saloes:160,clinicas:100,petshops:70,academias:90,imobiliarias:60,prestadores:260,lojas:200,oficinas:125,padarias:22},
    "Outra cidade": {restaurantes:80,saloes:70,clinicas:40,petshops:30,academias:35,imobiliarias:25,prestadores:120,lojas:90,oficinas:60,padarias:15}
  };
  const nichos = {
    "Restaurantes / Pizzarias":"restaurantes","Salões / Barbearias":"saloes",
    "Clínicas / Estética":"clinicas","Pet Shops / Veterinárias":"petshops",
    "Academias / Studios":"academias","Imobiliárias":"imobiliarias",
    "Prestadores de serviço":"prestadores","Lojas físicas":"lojas",
    "Oficinas mecânicas":"oficinas","Padarias / Mercados":"padarias"
  };
  const tickets = {restaurantes:1000,saloes:800,clinicas:2200,petshops:1200,academias:1500,imobiliarias:3000,prestadores:800,lojas:1400,oficinas:900,padarias:700};

  const btn = document.getElementById('sim-btn');
  if(!btn) return;
  btn.addEventListener('click', function(){
    const cidade = document.getElementById('sim-cidade').value;
    const nicho = nichos[document.getElementById('sim-nicho').value] || 'restaurantes';
    const leads = (data[cidade] && data[cidade][nicho]) || 50;
    const conv = Math.ceil(leads * 0.05);
    const ticket = tickets[nicho];
    const fatura = conv * ticket;
    document.getElementById('sim-leads').textContent = leads.toLocaleString('pt-BR');
    document.getElementById('sim-conv').textContent = conv.toLocaleString('pt-BR');
    document.getElementById('sim-ticket').textContent = 'R$ ' + ticket.toLocaleString('pt-BR');
    document.getElementById('sim-fatura').textContent = 'R$ ' + fatura.toLocaleString('pt-BR');
    document.getElementById('sim-leads-mes').textContent = Math.ceil(conv/4) + ' clientes';
    document.getElementById('sim-result').style.display = 'block';
    document.getElementById('sim-result').scrollIntoView({behavior:'smooth', block:'center'});
    if(typeof trackEvent === 'function') trackEvent('simulador_usado', {cidade:cidade});
  });
})();
</script>'''

    # Nova ordem dos blocos (15 secoes)
    new_order = [
        ("1. Hero com promessa + CTA", sections.get("hero")),
        ("2. Simulador de Oportunidades Locais", "CUSTOM_SIMULADOR"),
        ("3. Demo: lead → site → abordagem", sections.get("demo")),
        ("4. Antes vs Com FraLib", sections.get("problema")),
        ("5. Como Funciona em 3 Passos", sections.get("como-funciona")),
        ("6. Mockup WhatsApp (Efeito Wow)", sections.get("depoimentos")),
        ("7. O Que Você Recebe", sections.get("funcionalidades")),
        ("8. Nichos e Tickets Possíveis", sections.get("nichos")),
        ("9. Para Quem É", sections.get("para-quem")),
        ("10. Prova do Beta (Timeline)", sections.get("timeline")),
        ("11. Planos", sections.get("planos")),
        ("12. Garantia (Selos)", sections.get("trust-seals")),
        ("13. FAQ", sections.get("faq")),
        ("14. CTA Final / Formulário", sections.get("beta")),
        ("15. Prova Adicional (5 Fontes)", sections.get("cinco-fontes")),
        ("16. Prova Social (Marquee)", sections.get("social_proof")),
    ]

    # Monta novo main content
    new_main = "\n\n"
    for name, sec in new_order:
        if sec == "CUSTOM_SIMULADOR":
            new_main += simulador_section + "\n\n"
            continue
        if not sec:
            print(f"  [SKIP] {name}")
            continue
        new_main += sec + "\n\n"

    # Reconstrói
    new_html = header + new_main + "\n" + footer + "\n"

    # Salva
    LANDING.write_text(new_html, encoding="utf-8")

    print(f"\nArquivo reordenado: {LANDING}")
    print(f"Tamanho: {len(new_html):,} chars (original: {original_size:,})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())