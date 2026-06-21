/**
 * pipeline-timeline.js
 * ====================
 * Render animado do agente ATIVO da esteira FraLib.
 *
 * UX: mostra APENAS o agente que esta trabalhando agora, com:
 *   - icone grande + nome em destaque
 *   - mensagem rotativa do que esta fazendo
 *   - barra de progresso fake (0% -> 100%) que cicla automaticamente
 *   - quando completa, mostra "site enviado para SDR!" e passa pro proximo
 *
 * Mantem a mesma assinatura renderPipelineTimeline(ativo, status) que o
 * codigo legado usava, para garantir compatibilidade com chamadas
 * pre-existentes em admin.html.
 */
(function () {
  'use strict';

  // ── Personas dos agentes (icone + label + 4 mensagens cada) ───
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
    'hunter',
    'caio',
    'jina',
    'market_intelligence',
    'media',
    'prompt_agent',
    'designer',
    'builder_renderer',
    'deploy',
    'franz'
  ];

  // ── CSS injetado uma unica vez ─────────────────────────────────
  var STYLE_ID = 'pipeline-timeline-anim-css';
  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      '@keyframes tlPulse {',
      '  0%,100% { box-shadow: 0 0 0 4px rgba(168,85,247,.14), 0 0 24px rgba(168,85,247,.35); }',
      '  50%    { box-shadow: 0 0 0 10px rgba(168,85,247,.06), 0 0 42px rgba(168,85,247,.6); }',
      '}',
      '@keyframes tlBarFill {',
      '  0%   { background-position: 0% 50%; }',
      '  100% { background-position: 200% 50%; }',
      '}',
      '@keyframes tlMsgFade {',
      '  0%,100% { opacity: 0; transform: translateY(4px); }',
      '  20%,80% { opacity: 1; transform: translateY(0); }',
      '}',
      '@keyframes tlDonePop {',
      '  0%   { transform: scale(1); }',
      '  50%  { transform: scale(1.08); }',
      '  100% { transform: scale(1); }',
      '}',
      '.tl-card {',
      '  position:relative;',
      '  display:flex;',
      '  flex-direction:column;',
      '  align-items:center;',
      '  justify-content:center;',
      '  gap:6px;',
      '  padding:10px 8px;',
      '  border-radius:10px;',
      '  border:1px solid rgba(168,85,247,.4);',
      '  background:rgba(168,85,247,.08);',
      '  text-align:center;',
      '  min-height:110px;',
      '  width:100%;',
      '  max-width:100%;',
      '  box-sizing:border-box;',
      '  overflow:hidden;',
      '}',
      '.tl-card.is-active { animation: tlPulse 1.8s ease-in-out infinite; }',
      '.tl-card.is-done {',
      '  border-color: rgba(16,185,129,.5);',
      '  background: rgba(16,185,129,.10);',
      '  animation: tlDonePop .45s ease;',
      '}',
      '.tl-card.is-idle {',
      '  border-color: rgba(148,163,184,.3);',
      '  background: rgba(15,23,42,.55);',
      '  color: var(--fl-text-muted);',
      '}',
      '.tl-icon {',
      '  font-size:26px;',
      '  line-height:1;',
      '  filter: drop-shadow(0 0 10px rgba(168,85,247,.45));',
      '  flex-shrink:0;',
      '}',
      '.tl-card.is-done .tl-icon { filter: drop-shadow(0 0 12px rgba(16,185,129,.45)); }',
      '.tl-label {',
      '  font-family: var(--fl-font-brand);',
      '  font-size: 11px;',
      '  letter-spacing: 1.5px;',
      '  color: #a855f7;',
      '  white-space:nowrap;',
      '}',
      '.tl-card.is-done .tl-label { color: #10b981; }',
      '.tl-card.is-idle .tl-label { color: rgba(148,163,184,.7); }',
      '.tl-msg {',
      '  font-size: 11px;',
      '  color: var(--fl-text);',
      '  min-height: 14px;',
      '  font-weight: 500;',
      '  animation: tlMsgFade 6s ease-in-out infinite;',
      '  white-space:nowrap;',
      '  overflow:hidden;',
      '  text-overflow:ellipsis;',
      '  max-width:100%;',
      '}',
      '.tl-card.is-done .tl-msg { animation: none; color: #10b981; font-weight: 700; }',
      '.tl-card.is-idle .tl-msg { color: var(--fl-text-muted); }',
      '.tl-bar-track {',
      '  width:100%;',
      '  height: 8px;',
      '  background: rgba(15,23,42,.6);',
      '  border-radius: 99px;',
      '  overflow: hidden;',
      '  position:relative;',
      '  margin-top: 4px;',
      '}',
      '.tl-bar-fill {',
      '  height: 100%;',
      '  width: 0%;',
      '  background: linear-gradient(90deg, #a855f7, #ec4899, #06b6d4, #a855f7);',
      '  background-size: 200% 100%;',
      '  animation: tlBarFill 2s linear infinite;',
      '  border-radius: 99px;',
      '  transition: width .25s ease;',
      '}',
      '.tl-card.is-done .tl-bar-fill {',
      '  background: linear-gradient(90deg, #10b981, #34d399, #10b981);',
      '  width: 100% !important;',
      '}',
      '.tl-card.is-idle .tl-bar-fill { display:none; }',
      '.tl-pct {',
      '  font-family: var(--fl-font-mono);',
      '  font-size: 11px;',
      '  color: var(--fl-text-muted);',
      '  margin-top: 2px;',
      '}',
      '.tl-card.is-done .tl-pct { color: #10b981; font-weight: 700; }',
      '@media (prefers-reduced-motion: reduce) {',
      '  .tl-card, .tl-msg, .tl-bar-fill { animation: none !important; }',
      '}'
    ].join('\n');
    document.head.appendChild(s);
  }

  // ── Estado da animacao ─────────────────────────────────────────
  var state = {
    currentIdx: 0,           // indice na PIPELINE_TIMELINE
    progress: 0,             // 0..100
    active: false,           // se ha pipeline rodando
    cycleTimer: null,        // timer do progresso
    msgIdx: 0,               // mensagem rotativa
    msgTimer: null,          // timer de troca de mensagem
    doneFlash: false         // flag para mostrar "site enviado"
  };

  // ── Render principal ───────────────────────────────────────────
  function renderPipelineTimeline(ativo, status) {
    injectStyles();
    var el = document.getElementById('pipelineTimeline');
    if (!el) return;

    // Determinar se o pipeline esta rodando e qual agente
    if (ativo) {
      var idx = PIPELINE_TIMELINE.indexOf(ativo);
      if (idx >= 0) {
        state.currentIdx = idx;
        state.active = true;
        state.progress = 0;
        state.doneFlash = false;
      }
    } else if (ativo === null) {
      state.active = false;
    }

    // Status global
    var statusEl = document.getElementById('pipelineTimelineStatus');
    if (statusEl) statusEl.textContent = status || (state.active ? 'em andamento' : 'aguardando');

    // Render do card
    renderCard();
  }

  function renderCard() {
    var el = document.getElementById('pipelineTimeline');
    if (!el) return;

    var key = PIPELINE_TIMELINE[state.currentIdx];
    var persona = AGENT_PERSONAS[key];
    if (!persona) return;

    var msg = persona.msgs[state.msgIdx % persona.msgs.length];
    var pct = Math.min(100, Math.round(state.progress));
    var cls = 'tl-card';
    if (state.doneFlash) cls += ' is-done';
    else if (state.active) cls += ' is-active';
    else cls += ' is-idle';

    var displayMsg = state.doneFlash
      ? 'Site enviado para o SDR!'
      : msg;

    el.innerHTML =
      '<div class="' + cls + '">' +
        '<div class="tl-icon">' + persona.icon + '</div>' +
        '<div class="tl-label">' + persona.label.toUpperCase() + '</div>' +
        '<div class="tl-msg" data-msg-idx="' + state.msgIdx + '">' + displayMsg + '</div>' +
        '<div class="tl-bar-track"><div class="tl-bar-fill" id="tlBarFill" style="width:' + pct + '%"></div></div>' +
        '<div class="tl-pct" id="tlPct">' + pct + '%</div>' +
      '</div>';

    // Atualizar o bar via DOM direto (mais leve que re-renderizar tudo)
    var bar = document.getElementById('tlBarFill');
    var pctEl = document.getElementById('tlPct');
    if (bar) bar.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
  }

  // ── Animacao do progresso (fake, sobe de 0 a 100%) ───────────
  var PROGRESS_INTERVAL = 250;  // 4x por segundo
  var PROGRESS_STEP = 3;        // +3% a cada tick (~75s para completar)
  function tickProgress() {
    if (!state.active || state.doneFlash) return;
    state.progress += PROGRESS_STEP;
    if (state.progress >= 100) {
      state.progress = 100;
      state.doneFlash = true;
      // Ciclar para o proximo agente apos 1.8s
      setTimeout(advanceAgent, 1800);
    }
    var bar = document.getElementById('tlBarFill');
    var pctEl = document.getElementById('tlPct');
    if (bar) bar.style.width = state.progress + '%';
    if (pctEl) pctEl.textContent = Math.round(state.progress) + '%';
  }

  // ── Avancar para o proximo agente ──────────────────────────────
  function advanceAgent() {
    state.currentIdx = (state.currentIdx + 1) % PIPELINE_TIMELINE.length;
    state.progress = 0;
    state.doneFlash = false;
    state.msgIdx = 0;
    renderCard();
  }

  // ── Trocar mensagem a cada 6s ──────────────────────────────────
  var MSG_INTERVAL = 6000;
  function tickMessage() {
    if (!state.active || state.doneFlash) return;
    var key = PIPELINE_TIMELINE[state.currentIdx];
    var persona = AGENT_PERSONAS[key];
    if (!persona) return;
    state.msgIdx = (state.msgIdx + 1) % persona.msgs.length;
    var msgEl = document.querySelector('.tl-msg');
    if (msgEl && !state.doneFlash) {
      msgEl.textContent = persona.msgs[state.msgIdx];
    }
  }

  // ── Inicializacao dos timers ───────────────────────────────────
  function startLoops() {
    if (state.cycleTimer) return;
    state.cycleTimer = setInterval(tickProgress, PROGRESS_INTERVAL);
    state.msgTimer = setInterval(tickMessage, MSG_INTERVAL);
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      renderPipelineTimeline(null);
      startLoops();
    });
  } else {
    renderPipelineTimeline(null);
    startLoops();
  }

  // ── API publica (substitui a funcao legada) ────────────────────
  window.renderPipelineTimeline = renderPipelineTimeline;
})();