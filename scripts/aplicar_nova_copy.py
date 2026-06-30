#!/usr/bin/env python3
"""
Aplica TODA a nova copy na landing.html FraLib OS.
Cria versao com 16 secoes baseadas no briefing do usuario.
"""

import re
import sys
from pathlib import Path

LANDING = Path("C:/fralib/frontend/landing.html")


def main():
    html = LANDING.read_text(encoding="utf-8")

    # ========================================================================
    # 1. ATUALIZAR META TITLE/DESCRIPTION
    # ========================================================================
    html = html.replace(
        "<title>FraLib OS — Acha Cliente, Faz Site e Vende no WPP Automaticamente</title>",
        "<title>FraLib — Encontre Empresas Locais que Precisam de Site e Venda com Pré-via de IA</title>"
    )
    html = html.replace(
        '<meta name="description" content="FraLib acha o cliente que quer site, faz o site automaticão e vende no WhatsApp. Você só recebe o dinheiro. 100% do lucro é seu.">',
        '<meta name="description" content="FraLib encontra empresas locais com presença digital fraca, gera uma prévia de site com IA e produz abordagem pronta para WhatsApp. Beta por R$97.">'
    )

    # ========================================================================
    # 2. SUBSTITUIR SEÇÃO DE PROBLEMA (Antes vs Com FraLib)
    # ========================================================================
    problema_old_pattern = re.compile(
        r'<!--\s*=====\s*SEÇÃO 3[^=]*=====\s*-->.*?</section>',
        re.DOTALL
    )

    problema_new = '''<!-- ===== SEÇÃO 4 — ANTES VS COM FRALIB ===== -->
<section class="problema" id="antes-depois" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">Prospectar manualmente limita sua escala</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 56px;max-width:680px;color:var(--fl-text-muted);font-size:15px;line-height:1.7;">
      O problema não é só criar site com IA. O problema é saber quem abordar e como chamar atenção logo no primeiro contato.
    </p>
    <div class="ad-grid">
      <div class="ad-col ad-hoje reveal">
        <div class="ad-label">HOJE</div>
        <h3 class="ad-title">Você faz no escuro</h3>
        <ul class="ad-list">
          <li>Você abre o Google</li>
          <li>Procura empresa por empresa</li>
          <li>Analisa se tem site</li>
          <li>Tenta entender se vale abordar</li>
          <li>Escreve uma mensagem fria</li>
          <li>Cria site ou proposta só depois que alguém responde</li>
          <li>Perde horas em tarefas repetitivas</li>
        </ul>
      </div>
      <div class="ad-col ad-fralib reveal">
        <div class="ad-label ad-label-cyan">COM FRA LIB</div>
        <h3 class="ad-title">Você chega com prévia</h3>
        <ul class="ad-list ad-list-cyan">
          <li>Você escolhe cidade e nicho</li>
          <li>A FraLib encontra oportunidades</li>
          <li>A IA cria uma prévia de site</li>
          <li>A plataforma gera a abordagem</li>
          <li>Você chama o lead mostrando algo concreto</li>
          <li>Cliente fala "quero" mais rápido</li>
          <li>Tudo fica organizado no painel</li>
        </ul>
      </div>
    </div>
    <div class="ad-cta reveal" style="text-align:center;margin-top:40px;">
      <a href="#simulador" class="btn-hero-secondary">PARAR DE PROSPECTAR NO ESCURO</a>
    </div>
  </div>
</section>'''

    html = problema_old_pattern.sub(problema_new, html, count=1)

    # ========================================================================
    # 3. ATUALIZAR SEÇÃO "COMO FUNCIONA"
    # ========================================================================
    como_funca_pattern = re.compile(
        r'<!--\s*=====\s*SEÇÃO 4[^=]*=====\s*-->.*?</section>',
        re.DOTALL
    )

    como_funca_new = '''<!-- ===== SEÇÃO 5 — COMO FUNCIONA ===== -->
<section class="como-funciona" id="como-funciona" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">A FraLib faz o caminho mais difícil antes da venda</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 48px;max-width:680px;color:var(--fl-text-muted);font-size:15px;">Você define o nicho. A FraLib busca, gera prévia e prepara a abordagem. Você chama o lead no WhatsApp mostrando algo concreto.</p>
    <div class="steps-grid">
      <div class="step-card reveal">
        <div class="step-num">1</div>
        <div class="step-icon-wrap"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg></div>
        <h3 class="step-title">Encontra o lead</h3>
        <p class="step-desc">Escolha cidade e nicho. A FraLib busca empresas locais com sinais de oportunidade, como ausência de site detectado ou presença digital fraca.</p>
      </div>
      <div class="step-card reveal">
        <div class="step-num">2</div>
        <div class="step-icon-wrap"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>
        <h3 class="step-title">Cria a prévia do site</h3>
        <p class="step-desc">A IA usa dados públicos do negócio para montar uma prévia visual com nome, serviços, endereço, mapa e botão de WhatsApp.</p>
      </div>
      <div class="step-card reveal">
        <div class="step-num">3</div>
        <div class="step-icon-wrap"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg></div>
        <h3 class="step-title">Gera a abordagem</h3>
        <p class="step-desc">Em vez de mandar "faço sites", você chama com uma demonstração: "Oi, montei uma prévia de como o site da sua empresa poderia ficar."</p>
      </div>
    </div>
    <div class="section-cta reveal" style="text-align:center;margin-top:48px;">
      <a href="#simulador" class="btn-hero-primary">GERAR UMA PRÉVIA AGORA</a>
    </div>
  </div>
</section>'''

    html = como_funca_pattern.sub(como_funca_new, html, count=1)

    # ========================================================================
    # 4. ATUALIZAR DEPOIMENTOS (Efeito Wow WhatsApp)
    # ========================================================================
    depoimentos_pattern = re.compile(
        r'<!--\s*=====\s*SEÇÃO 5C[^=]*=====\s*-->.*?</section>',
        re.DOTALL
    )

    depoimentos_new = '''<!-- ===== SEÇÃO 6 — EFEITO WOW NO WHATSAPP ===== -->
<section id="whatsapp-wow" style="padding:80px 0;background:linear-gradient(180deg,transparent 0%,rgba(0,255,179,0.03) 100%);">
  <div class="container">
    <h2 class="section-title reveal">Você não vende só falando. Você vende mostrando.</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 56px;max-width:680px;color:var(--fl-text-muted);font-size:15px;line-height:1.7;">A maioria dos freelancers manda mensagens iguais. A FraLib ajuda você a chegar com uma prévia pronta, aumentando a curiosidade e a percepção de valor.</p>

    <div class="wa-demo reveal" style="max-width:680px;margin:0 auto;background:var(--fl-bg-card);border:1px solid var(--fl-border);">
      <div class="wa-demo-header">
        <div class="wa-avatar">F</div>
        <div>
          <div class="wa-name">Conversa real · Efeito wow</div>
          <div class="wa-status">Prévia enviada</div>
        </div>
      </div>
      <div class="wa-demo-msgs">
        <div class="wa-bubble sent">
          <div class="wa-msg-text">Oi, tudo bem? Vi que sua empresa aparece no Google, mas não encontrei um site profissional.</div>
          <div class="wa-msg-time">10:32</div>
        </div>
        <div class="wa-bubble sent">
          <div class="wa-msg-text">Montei uma prévia gratuita de como o site de vocês poderia ficar. Posso te mandar?</div>
          <div class="wa-msg-time">10:33</div>
        </div>
        <div class="wa-bubble received">
          <div class="wa-msg-text">Pode sim, manda aí.</div>
          <div class="wa-msg-time">10:41</div>
        </div>
        <div class="wa-bubble sent">
          <div class="wa-msg-text">Aqui está a prévia: <span class="wa-link">[link-da-demo]</span></div>
          <div class="wa-msg-time">10:42</div>
        </div>
        <div class="wa-bubble received">
          <div class="wa-msg-text">Ficou muito bom. Quanto ficaria pra deixar no ar?</div>
          <div class="wa-msg-time">10:50</div>
        </div>
        <div class="wa-bubble typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <p style="text-align:center;color:var(--fl-text-dim);font-size:12px;margin:24px auto 0;font-style:italic;">Conversa ilustrativa. Resultados dependem da abordagem, nicho e execução.</p>

    <div class="section-cta reveal" style="text-align:center;margin-top:40px;">
      <a href="#oferta" class="btn-hero-primary">USAR ABORDAGEM COM EFEITO WOW</a>
    </div>
  </div>
</section>'''

    html = depoimentos_pattern.sub(depoimentos_new, html, count=1)

    # ========================================================================
    # 5. ATUALIZAR FUNCIONALIDADES (O que você recebe)
    # ========================================================================
    func_pattern = re.compile(
        r'<!--\s*=====\s*SEÇÃO 6 — FUNCIONALIDADES[^=]*=====\s*-->.*?</section>',
        re.DOTALL
    )

    func_new = '''<!-- ===== SEÇÃO 7 — O QUE VOCÊ RECEBE ===== -->
<section class="funcionalidades" id="funcionalidades" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">Tudo para transformar dados locais em oportunidades de venda</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 48px;max-width:680px;color:var(--fl-text-muted);font-size:15px;">Seis blocos prontos. Você conecta, busca, gera prévia, aborda e organiza. Sem código.</p>
    <div class="feat-grid">
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg></div>
        <h3 class="feat-title">Busca de leads locais</h3>
        <p class="feat-desc">Encontre empresas por cidade e nicho, sem ficar pesquisando manualmente.</p>
      </div>
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9"/></svg></div>
        <h3 class="feat-title">Análise de oportunidade</h3>
        <p class="feat-desc">Veja sinais que ajudam a decidir quem vale abordar primeiro.</p>
      </div>
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div>
        <h3 class="feat-title">Prévia de site com IA</h3>
        <p class="feat-desc">Gere uma demonstração visual baseada nos dados públicos do negócio.</p>
      </div>
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
        <h3 class="feat-title">Abordagem personalizada</h3>
        <p class="feat-desc">Receba mensagens prontas para iniciar conversa no WhatsApp.</p>
      </div>
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></div>
        <h3 class="feat-title">CRM simples</h3>
        <p class="feat-desc">Organize leads por status: novo, site criado, enviado, respondeu, proposta, fechado.</p>
      </div>
      <div class="feat-card reveal">
        <div class="feat-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
        <h3 class="feat-title">Grupo WhatsApp</h3>
        <p class="feat-desc">Acesso ao grupo para suporte, networking, troca de nichos, scripts e aprendizados.</p>
      </div>
    </div>
    <div class="section-cta reveal" style="text-align:center;margin-top:48px;">
      <a href="#oferta" class="btn-hero-primary">ENTRAR NO BETA POR R$97</a>
    </div>
  </div>
</section>'''

    html = func_pattern.sub(func_new, html, count=1)

    # ========================================================================
    # 6. ATUALIZAR TIMELINE (PROVA DO BETA) - RENOMEAR
    # ========================================================================
    timeline_pattern = re.compile(
        r'<!--\s*=====\s*SEÇÃO 7B[^=]*=====\s*-->.*?</section>',
        re.DOTALL
    )

    timeline_new = '''<!-- ===== SEÇÃO 10 — PROVA DO BETA ===== -->
<section class="prova-beta" id="prova-beta" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">O beta já está rodando</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 48px;max-width:680px;color:var(--fl-text-muted);font-size:15px;">A FraLib ainda está em evolução, mas já está sendo usada para testar buscas, prévias e abordagens com empresas locais.</p>
    <div class="beta-stats">
      <div class="beta-stat reveal">
        <div class="beta-num">40</div>
        <div class="beta-lbl">usuários beta</div>
      </div>
      <div class="beta-stat reveal">
        <div class="beta-num cyan">+1.000</div>
        <div class="beta-lbl">buscas feitas em 1 mês</div>
      </div>
      <div class="beta-stat reveal">
        <div class="beta-num gold">+1.000</div>
        <div class="beta-lbl">leads encontrados</div>
      </div>
      <div class="beta-stat reveal">
        <div class="beta-num green">2</div>
        <div class="beta-lbl">vendas reportadas por usuários beta</div>
      </div>
    </div>
    <p style="text-align:center;color:var(--fl-text-dim);font-size:12px;margin:32px auto 0;font-style:italic;max-width:680px;">Resultados iniciais do beta. A FraLib não garante vendas ou faturamento. Os resultados dependem da execução, oferta, nicho, abordagem e follow-up de cada usuário.</p>
    <div class="section-cta reveal" style="text-align:center;margin-top:32px;">
      <a href="#oferta" class="btn-hero-primary">FAZER PARTE DO BETA</a>
    </div>
  </div>
</section>'''

    html = timeline_pattern.sub(timeline_new, html, count=1)

    # ========================================================================
    # 7. ADICIONAR CSS para as novas classes
    # ========================================================================
    novo_css = '''<style>
/* NOVO: Antes vs Depois */
.ad-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:1000px;margin:0 auto}
.ad-col{background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:32px 24px;position:relative}
.ad-col.ad-fralib{border-color:var(--cyan);background:linear-gradient(180deg,var(--fl-bg-card) 0%,rgba(0,255,179,0.04) 100%)}
.ad-label{font-family:var(--fl-font-brand);font-size:10px;letter-spacing:2px;color:var(--fl-text-dim);margin-bottom:12px}
.ad-label-cyan{color:var(--cyan)}
.ad-title{font-size:18px;font-weight:700;margin-bottom:20px;color:var(--fl-text)}
.ad-list{list-style:none;padding:0;margin:0}
.ad-list li{font-size:14px;color:var(--fl-text-muted);padding:8px 0 8px 24px;position:relative;line-height:1.5;border-bottom:1px solid var(--fl-border)}
.ad-list li:last-child{border-bottom:none}
.ad-list li::before{content:'×';position:absolute;left:0;top:8px;color:var(--fl-danger);font-weight:700;font-size:14px}
.ad-list-cyan li::before{content:'✓';color:var(--cyan)}
.ad-list-cyan li{color:var(--fl-text)}
@media(max-width:768px){.ad-grid{grid-template-columns:1fr}}

/* NOVO: Como Funciona */
.steps-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1000px;margin:0 auto}
.step-card{background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:32px 24px;text-align:center;position:relative}
.step-num{position:absolute;top:-12px;left:24px;background:var(--fl-purple);color:#fff;font-family:var(--fl-font-brand);font-size:9px;padding:4px 12px;letter-spacing:1px}
.step-icon-wrap{width:56px;height:56px;background:rgba(147,51,234,0.15);border:1px solid var(--fl-purple);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;color:var(--fl-purple-300)}
.step-title{font-size:17px;font-weight:700;margin-bottom:10px;color:var(--fl-text)}
.step-desc{font-size:13px;color:var(--fl-text-muted);line-height:1.7}
@media(max-width:768px){.steps-grid{grid-template-columns:1fr}}

/* NOVO: WhatsApp Demo */
.wa-demo{overflow:hidden}
.wa-demo-header{display:flex;align-items:center;gap:12px;padding:16px 20px;background:#1F2C33;border-bottom:1px solid rgba(255,255,255,.05)}
.wa-demo .wa-avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--fl-purple),var(--cyan));display:flex;align-items:center;justify-content:center;font-family:var(--fl-font-brand);font-size:11px;color:#fff}
.wa-demo .wa-name{font-size:14px;font-weight:600;color:#fff}
.wa-demo .wa-status{font-size:11px;color:#8696A0}
.wa-demo-msgs{padding:20px;display:flex;flex-direction:column;gap:8px;background:#0B141A}
.wa-bubble{max-width:80%;padding:10px 12px;border-radius:8px;font-size:13px;line-height:1.4;position:relative}
.wa-bubble.sent{background:#005C4B;align-self:flex-end;color:#fff}
.wa-bubble.received{background:#1F2C33;align-self:flex-start;color:#fff}
.wa-bubble.typing{background:#1F2C33;align-self:flex-start;display:flex;gap:4px;padding:14px 16px}
.wa-bubble.typing span{width:6px;height:6px;border-radius:50%;background:#8696A0;animation:dot-pulse 1.4s infinite}
.wa-bubble.typing span:nth-child(2){animation-delay:.2s}
.wa-bubble.typing span:nth-child(3){animation-delay:.4s}
.wa-msg-text{color:inherit}
.wa-msg-time{font-size:9px;opacity:0.6;margin-top:4px;text-align:right}
.wa-link{color:var(--cyan);text-decoration:underline}
@keyframes dot-pulse{0%,60%,100%{opacity:.3;transform:scale(.8)}30%{opacity:1;transform:scale(1)}}

/* NOVO: Prova do Beta */
.beta-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:20px;max-width:1000px;margin:0 auto}
.beta-stat{background:var(--fl-bg-card);border:1px solid var(--fl-border);padding:32px 20px;text-align:center}
.beta-num{font-family:var(--fl-font-mono);font-size:36px;font-weight:700;color:#fff;line-height:1;margin-bottom:8px}
.beta-num.cyan{color:var(--cyan)}
.beta-num.gold{color:var(--gold)}
.beta-num.green{color:var(--green)}
.beta-lbl{font-size:11px;color:var(--fl-text-muted);text-transform:uppercase;letter-spacing:.5px;font-family:var(--fl-font-mono)}

/* NOVO: Section CTA */
.section-cta{text-align:center;margin-top:48px}
</style>'''

    # Inserir CSS novo antes do </style> que termina a secao
    html = html.replace(
        '</style>\n\n<!-- ===== SEÇÃO 2 — SIMULADOR',
        '</style>\n' + novo_css + '\n\n<!-- ===== SEÇÃO 2 — SIMULADOR',
        1
    )

    # Salva
    LANDING.write_text(html, encoding="utf-8")
    print(f"Landing atualizada: {LANDING}")
    print(f"Tamanho: {len(html):,} chars")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())