/**
 * pipeline-timeline.js
 * ====================
 * Render animado da esteira de agentes do FraLib com:
 *   - icone unico por agente
 *   - mensagens curtas que rotacionam a cada ~7s (com fade)
 *   - barra de progresso animada no agente ativo
 *   - pulse intenso no card ativo
 *
 * Mantem a mesma assinatura renderPipelineTimeline(ativo, status) que o
 * codigo legado usava, para garantir compatibilidade com chamadas
 * pre-existentes em admin.html e partials/admin/_scripts.html.
 */
(function () {
  'use strict';

  // ── Personas dos agentes (icone + 4 mensagens cada) ─────────────
  var AGENT_PERSONAS = {
    hunter: {
      icon: '🔍',
      label: 'Hunter',
      msgs: [
        'vasculhando Google Maps',
        'procurando leads na regiao',
        'filtrando empresas qualificadas',
        'coletando telefones e enderecos'
      ]
    },
    caio: {
      icon: '🤖',
      label: 'Caio',
      msgs: [
        'analisando perfil do lead',
        'verificando se tem potencial',
        'avaliando presenca digital',
        'calculando score de qualidade'
      ]
    },
    jina: {
      icon: '🧠',
      label: 'Jina',
      msgs: [
        'pesquisando concorrentes',
        'extraindo palavras-chave',
        'mapeando tons de voz',
        'analisando sites do segmento'
      ]
    },
    market_intelligence: {
      icon: '📊',
      label: 'Mercado',
      msgs: [
        'coletando insights de mercado',
        'cruzando dados regionais',
        'identificando oportunidades',
        'montando estrategia SEO'
      ]
    },
    media: {
      icon: '🎨',
      label: 'Midia',
      msgs: [
        'buscando fotos profissionais',
        'selecionando imagens premium',
        'curando galeria do site',
        'otimizando resolucao'
      ]
    },
    prompt_agent: {
      icon: '✍️',
      label: 'Prompt',
      msgs: [
        'escrevendo copy persuasiva',
        'gerando headlines de impacto',
        'criando CTAs irresistiveis',
        'adaptando tom de voz'
      ]
    },
    designer: {
      icon: '🎯',
      label: 'Designer',
      msgs: [
        'desenhando layout do site',
        'aplicando identidade visual',
        'organizando secoes',
        'balanceando composicao'
      ]
    },
    builder_renderer: {
      icon: '⚡',
      label: 'Builder',
      msgs: [
        'escrevendo HTML do site',
        'compilando paginas',
        'gerando CSS responsivo',
        'empacotando arquivos finais'
      ]
    },
    deploy: {
      icon: '🚀',
      label: 'Deploy',
      msgs: [
        'publicando no servidor',
        'configurando DNS',
        'ativando HTTPS',
        'seu site vai estar no ar em instantes'
      ]
    },
    franz: {
      icon: '💬',
      label: 'Franz',
      msgs: [
        'preparando abordagem de vendas',
        'estudando o lead',
        'montando primeira mensagem',
        'pronto para iniciar conversa'
      ]
    }
  };

  // Ordem canonica da esteira
  var PIPELINE_TIMELINE = [
    { key: 'hunter',              fase: 1 },
    { key: 'caio',                fase: 2 },
    { key: 'jina',                fase: 3 },
    { key: 'market_intelligence', fase: 4 },
    { key: 'media',               fase: 5 },
    { key: 'prompt_agent',        fase: 6 },
    { key: 'designer',            fase: 8 },
    { key: 'builder_renderer',    fase: 9 },
    { key: 'deploy',              fase: 10 },
    { key: 'franz',               fase: 11 }
  ];

  // ── CSS injetado uma unica vez ─────────────────────────────────
  var STYLE_ID = 'pipeline-timeline-anim-css';
  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      '@keyframes timelinePulse {',
      '  0%,100% { box-shadow: 0 0 0 4px rgba(168,85,247,.14), 0 0 18px rgba(168,85,247,.35); }',
      '  50%    { box-shadow: 0 0 0 8px rgba(168,85,247,.08), 0 0 32px rgba(168,85,247,.55); }',
      '}',
      '@keyframes timelineProgress {',
      '  0%   { background-position: 0% 50%; }',
      '  100% { background-position: 200% 50%; }',
      '}',
      '@keyframes timelineFade {',
      '  from { opacity: 0; transform: translateY(-4px); }',
      '  to   { opacity: 1; transform: translateY(0); }',
      '}',
      '.timeline-card { position:relative;display:grid;grid-template-columns:32px 1fr;gap:10px;align-items:center;border-radius:8px;padding:9px 10px;min-height:54px;transition:all .25s ease; }',
      '.timeline-icon { width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:16px;line-height:1; }',
      '.timeline-label { font-family:var(--fl-font-brand);font-size:9px;letter-spacing:1px; }',
      '.timeline-msg { font-size:11px;color:var(--fl-text-muted);margin-top:5px;min-height:14px;transition:opacity .3s ease; }',
      '.timeline-progress-bar { height:3px;background:linear-gradient(90deg,#a855f7,#ec4899,#a855f7);background-size:200% 100%;animation:timelineProgress 2s linear infinite;border-radius:2px;margin-top:5px;opacity:0; }',
      '.timeline-card.is-active { animation: timelinePulse 1.6s ease-in-out infinite, timelineFade .4s ease; }',
      '.timeline-card.is-active .timeline-progress-bar { opacity: 1; }',
      '.timeline-card.is-done .timeline-icon { filter: saturate(.6); }',
      '@media (prefers-reduced-motion: reduce) {',
      '  .timeline-card.is-active { animation: none; }',
      '  .timeline-progress-bar { animation: none; }',
      '  .timeline-msg { transition: none; }',
      '}'
    ].join('\n');
    document.head.appendChild(s);
  }

  // ── Render principal ───────────────────────────────────────────
  function renderPipelineTimeline(ativo, status) {
    injectStyles();

    var el = document.getElementById('pipelineTimeline');
    if (!el) return;

    // Status global (ex: "Pipeline em andamento")
    var statusEl = document.getElementById('pipelineTimelineStatus');
    if (statusEl) statusEl.textContent = status || (ativo ? 'em andamento' : 'aguardando');

    var activeIndex = -1;
    if (ativo) {
      activeIndex = -1;
      for (var i = 0; i < PIPELINE_TIMELINE.length; i++) {
        if (PIPELINE_TIMELINE[i].key === ativo) { activeIndex = i; break; }
      }
    }

    el.innerHTML = PIPELINE_TIMELINE.map(function (p, idx) {
      var persona = AGENT_PERSONAS[p.key] || { icon: '•', label: p.key, msgs: ['processando...'] };
      var done = activeIndex >= 0 && idx < activeIndex;
      var active = activeIndex === idx;

      var border = active ? '#a855f7' : (done ? '#10b981' : 'rgba(148,163,184,.35)');
      var bg     = active ? 'rgba(168,85,247,.18)' : (done ? 'rgba(16,185,129,.12)' : 'rgba(15,23,42,.55)');
      var iconBg = active ? '#a855f7' : (done ? '#10b981' : 'rgba(148,163,184,.4)');
      var iconColor = (done && !active) ? '#080814' : (active ? '#080814' : '#fff');
      var labelColor = active ? '#a855f7' : (done ? '#10b981' : 'rgba(148,163,184,.85)');

      // Mensagem inicial: pega um index estavel por agente + fase (evita piscar igual em todos)
      var msgIdx = (idx + Math.floor(Date.now() / 7000)) % persona.msgs.length;
      var msg = persona.msgs[msgIdx];

      var cls = 'timeline-card';
      if (active) cls += ' is-active';
      if (done) cls += ' is-done';

      return '<div class="' + cls + '" data-timeline-agent="' + p.key + '" data-msg-idx="' + msgIdx + '" '
           + 'style="border:1px solid ' + border + ';background:' + bg + ';">'
           + '<div class="timeline-icon" style="background:' + iconBg + ';color:' + iconColor + ';">'
           +   persona.icon
           + '</div>'
           + '<div>'
           +   '<div class="timeline-label" style="color:' + labelColor + ';">' + persona.label.toUpperCase() + '</div>'
           +   '<div class="timeline-msg">' + msg + '</div>'
           +   '<div class="timeline-progress-bar"></div>'
           + '</div>'
           + '</div>';
    }).join('');
  }

  // ── Rotacao automatica a cada 7s com fade ──────────────────────
  var ROTATION_MS = 7000;
  var _intervalId = null;

  function startRotation() {
    if (_intervalId) return;
    _intervalId = setInterval(function () {
      var cards = document.querySelectorAll('[data-timeline-agent]');
      for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var agent = card.getAttribute('data-timeline-agent');
        var persona = AGENT_PERSONAS[agent];
        if (!persona || !persona.msgs || !persona.msgs.length) continue;

        var currentIdx = parseInt(card.getAttribute('data-msg-idx') || '0', 10);
        var nextIdx = (currentIdx + 1) % persona.msgs.length;

        var msgEl = card.querySelector('.timeline-msg');
        if (!msgEl) continue;

        // fade out
        msgEl.style.opacity = '0';
        setTimeout(function (el, idx, txt) {
          el.textContent = txt;
          el.style.opacity = '1';
          // Atualiza o atributo no card pai
          var parent = el.closest('[data-timeline-agent]');
          if (parent) parent.setAttribute('data-msg-idx', String(idx));
        }, 300, msgEl, nextIdx, persona.msgs[nextIdx]);
      }
    }, ROTATION_MS);
  }

  // Inicializa ao carregar a pagina
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      renderPipelineTimeline(null);
      startRotation();
    });
  } else {
    renderPipelineTimeline(null);
    startRotation();
  }

  // ── API publica (substitui a funcao legada) ────────────────────
  window.renderPipelineTimeline = renderPipelineTimeline;
})();