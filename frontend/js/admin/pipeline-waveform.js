/**
 * pipeline-waveform.js
 * ===================
 * Linha do tempo visual estilo player de musica para o pipeline FraLib.
 *
 * Mostra TODAS as 10 etapas da esteira em uma trilha horizontal, com:
 *   - nos coloridos (idle / active pulsando / done com check)
 *   - barra de progresso avancando como em um player de musica
 *   - waveform fake embaixo (barras animadas estilo Spotify)
 *   - label da fase atual + tempo decorrido
 *
 * API publica:
 *   - window.PipelineWaveform.ativar(faseKey, label)  - liga com fase
 *   - window.PipelineWaveform.desativar()             - desliga
 *   - window.PipelineWaveform.setProgress(pct)        - 0..100
 *   - window.PipelineWaveform.tickFake()              - avanca 1% (fallback)
 *
 * Sem dependencias externas. Auto-inicia ao carregar.
 */
(function () {
  'use strict';

  // ── Etapas canonicas da esteira FraLib ────────────────────────────
  // Mantem alinhado com backend/agents/pipeline_phase_tracking.py
  var ETAPAS = [
    { key: 'hunter',              icon: '🔍', label: 'Hunter',     tone: '#a855f7' },
    { key: 'caio',                icon: '🤖', label: 'Caio',       tone: '#a855f7' },
    { key: 'jina',                icon: '🧠', label: 'Jina',       tone: '#a855f7' },
    { key: 'market_intelligence', icon: '📊', label: 'Mercado',    tone: '#06b6d4' },
    { key: 'media',               icon: '🎨', label: 'Midia',      tone: '#06b6d4' },
    { key: 'prompt_agent',        icon: '✍️', label: 'Prompt',     tone: '#ec4899' },
    { key: 'designer',            icon: '🎯', label: 'Designer',   tone: '#ec4899' },
    { key: 'builder_renderer',    icon: '⚡', label: 'Builder',    tone: '#f59e0b' },
    { key: 'deploy',              icon: '🚀', label: 'Deploy',     tone: '#10b981' },
    { key: 'franz',               icon: '💬', label: 'Franz',      tone: '#10b981' }
  ];

  var STYLE_ID = 'pipeline-waveform-css';

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      '@keyframes pwPulse {',
      '  0%,100% { box-shadow: 0 0 0 3px rgba(168,85,247,.18), 0 0 18px rgba(168,85,247,.45); transform: scale(1); }',
      '  50%     { box-shadow: 0 0 0 9px rgba(168,85,247,.04), 0 0 36px rgba(168,85,247,.75); transform: scale(1.06); }',
      '}',
      '@keyframes pwBarBounce {',
      '  0%,100% { transform: scaleY(.35); }',
      '  50%     { transform: scaleY(1); }',
      '}',
      '@keyframes pwFillMove {',
      '  0%   { background-position: 0% 50%; }',
      '  100% { background-position: 200% 50%; }',
      '}',
      '@keyframes pwShimmer {',
      '  0%   { left: -40%; }',
      '  100% { left: 140%; }',
      '}',
      '.pw-wrap {',
      '  position: relative;',
      '  background: linear-gradient(135deg, rgba(15,23,42,.85), rgba(30,41,59,.7));',
      '  border: 1px solid rgba(168,85,247,.35);',
      '  border-radius: 12px;',
      '  padding: 16px 18px 14px;',
      '  margin: 12px 0;',
      '  font-family: var(--fl-font-mono, "JetBrains Mono", monospace);',
      '  overflow: hidden;',
      '  box-shadow: 0 10px 40px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.04);',
      '}',
      '.pw-wrap::before {',
      '  content: "";',
      '  position: absolute;',
      '  top: 0; left: -40%;',
      '  width: 40%; height: 100%;',
      '  background: linear-gradient(90deg, transparent, rgba(168,85,247,.07), transparent);',
      '  animation: pwShimmer 6s linear infinite;',
      '  pointer-events: none;',
      '}',
      '.pw-header {',
      '  display: flex; align-items: center; justify-content: space-between; gap: 10px;',
      '  margin-bottom: 14px;',
      '}',
      '.pw-title {',
      '  display: flex; align-items: center; gap: 8px;',
      '  font-family: var(--fl-font-brand, "Inter", sans-serif);',
      '  font-size: 11px;',
      '  letter-spacing: 1.6px;',
      '  color: #cbd5e1;',
      '  text-transform: uppercase;',
      '}',
      '.pw-dot {',
      '  width: 8px; height: 8px; border-radius: 50%;',
      '  background: #10b981;',
      '  box-shadow: 0 0 12px rgba(16,185,129,.7);',
      '  display: inline-block;',
      '}',
      '.pw-dot.idle { background: #475569; box-shadow: none; }',
      '.pw-stage {',
      '  font-family: var(--fl-font-mono, monospace);',
      '  font-size: 10px;',
      '  color: #94a3b8;',
      '  letter-spacing: .5px;',
      '  max-width: 60%;',
      '  overflow: hidden;',
      '  text-overflow: ellipsis;',
      '  white-space: nowrap;',
      '  text-align: right;',
      '}',
      '.pw-stage strong { color: #f1f5f9; }',
      '.pw-track {',
      '  position: relative;',
      '  display: flex;',
      '  align-items: flex-start;',
      '  justify-content: space-between;',
      '  gap: 4px;',
      '  padding: 6px 0 2px;',
      '}',
      '.pw-node {',
      '  flex: 1 1 0;',
      '  display: flex;',
      '  flex-direction: column;',
      '  align-items: center;',
      '  position: relative;',
      '  z-index: 2;',
      '  min-width: 0;',
      '}',
      '.pw-bubble {',
      '  width: 34px; height: 34px;',
      '  border-radius: 50%;',
      '  display: flex; align-items: center; justify-content: center;',
      '  font-size: 16px;',
      '  background: rgba(15,23,42,.9);',
      '  border: 2px solid rgba(148,163,184,.3);',
      '  color: #94a3b8;',
      '  transition: all .25s ease;',
      '  position: relative;',
      '  z-index: 3;',
      '}',
      '.pw-node.is-done .pw-bubble {',
      '  background: linear-gradient(135deg, #10b981, #059669);',
      '  border-color: #10b981;',
      '  color: #fff;',
      '  box-shadow: 0 0 18px rgba(16,185,129,.4);',
      '}',
      '.pw-node.is-active .pw-bubble {',
      '  animation: pwPulse 1.6s ease-in-out infinite;',
      '  border-color: var(--pw-tone, #a855f7);',
      '  background: radial-gradient(circle at 30% 30%, var(--pw-tone, #a855f7), rgba(15,23,42,.95) 75%);',
      '  color: #fff;',
      '}',
      '.pw-node.is-active .pw-bubble::after {',
      '  content: "";',
      '  position: absolute;',
      '  inset: -3px;',
      '  border-radius: 50%;',
      '  border: 1px dashed var(--pw-tone, #a855f7);',
      '  animation: pwPulse 2.4s linear infinite;',
      '  opacity: .5;',
      '}',
      '.pw-name {',
      '  margin-top: 6px;',
      '  font-size: 9px;',
      '  letter-spacing: .8px;',
      '  text-transform: uppercase;',
      '  color: #64748b;',
      '  text-align: center;',
      '  white-space: nowrap;',
      '  overflow: hidden;',
      '  text-overflow: ellipsis;',
      '  max-width: 100%;',
      '}',
      '.pw-node.is-done .pw-name { color: #10b981; }',
      '.pw-node.is-active .pw-name { color: var(--pw-tone, #a855f7); font-weight: 700; }',
      '.pw-rail {',
      '  position: absolute;',
      '  left: 0; right: 0;',
      '  top: 22px;',
      '  height: 4px;',
      '  background: rgba(148,163,184,.18);',
      '  border-radius: 2px;',
      '  z-index: 1;',
      '  overflow: hidden;',
      '}',
      '.pw-rail-fill {',
      '  position: absolute;',
      '  top: 0; bottom: 0;',
      '  left: 0;',
      '  width: 0%;',
      '  background: linear-gradient(90deg, #a855f7, #ec4899, #06b6d4, #10b981, #10b981);',
      '  background-size: 200% 100%;',
      '  animation: pwFillMove 3s linear infinite;',
      '  border-radius: 2px;',
      '  transition: width .35s ease;',
      '  box-shadow: 0 0 12px rgba(168,85,247,.5);',
      '}',
      '.pw-wave {',
      '  display: flex;',
      '  align-items: flex-end;',
      '  justify-content: space-between;',
      '  gap: 2px;',
      '  height: 26px;',
      '  margin-top: 10px;',
      '  padding: 0 2px;',
      '}',
      '.pw-bar {',
      '  flex: 1 1 0;',
      '  background: linear-gradient(180deg, #475569, #334155);',
      '  border-radius: 2px 2px 0 0;',
      '  transform-origin: bottom center;',
      '  min-height: 4px;',
      '  transition: background .25s ease;',
      '}',
      '.pw-bar.is-on {',
      '  background: linear-gradient(180deg, var(--pw-tone, #a855f7), rgba(168,85,247,.25));',
      '  animation: pwBarBounce 1.2s ease-in-out infinite;',
      '}',
      '.pw-bar.is-past {',
      '  background: linear-gradient(180deg, #10b981, rgba(16,185,129,.25));',
      '}',
      '.pw-footer {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: space-between;',
      '  margin-top: 10px;',
      '  font-size: 10px;',
      '  color: #94a3b8;',
      '  letter-spacing: .5px;',
      '}',
      '.pw-eta { display: flex; align-items: center; gap: 6px; }',
      '.pw-eta strong { color: #f1f5f9; font-family: var(--fl-font-mono, monospace); }',
      '.pw-pct { font-size: 12px; color: #10b981; font-weight: 700; }',
      '@media (prefers-reduced-motion: reduce) {',
      '  .pw-bubble, .pw-bar, .pw-rail-fill, .pw-wrap::before { animation: none !important; }',
      '}',
      '@media (max-width: 720px) {',
      '  .pw-name { display: none; }',
      '  .pw-stage { max-width: 50%; }',
      '}'
    ].join('\n');
    document.head.appendChild(s);
  }

  // ── Estado interno ────────────────────────────────────────────────
  var state = {
    running: false,
    activeKey: null,
    activeIdx: 0,
    progress: 0,        // 0..100 da fase ATUAL
    label: '',
    elapsed: 0,         // segundos totais
    fakeTimer: null,
    pctTimer: null,
    tickCount: 0
  };

  function buildHTML() {
    var nodes = ETAPAS.map(function (e, i) {
      return '' +
        '<div class="pw-node" data-idx="' + i + '" data-key="' + e.key + '" style="--pw-tone:' + e.tone + ';">' +
          '<div class="pw-bubble">' + e.icon + '</div>' +
          '<div class="pw-name">' + e.label + '</div>' +
        '</div>';
    }).join('');

    // 80 barras para o waveform (mais detalhe, mas flex:1 distribui igual)
    var bars = [];
    for (var i = 0; i < 80; i++) {
      // altura pseudo-aleatoria fixa (parece waveform estetica)
      var h = 8 + Math.abs(Math.sin(i * 0.42) * 14) + Math.abs(Math.cos(i * 0.27) * 8);
      bars.push('<div class="pw-bar" data-bar="' + i + '" style="height:' + h.toFixed(1) + 'px;"></div>');
    }

    return '' +
      '<div class="pw-wrap" id="pipelineWaveform">' +
        '<div class="pw-header">' +
          '<div class="pw-title">' +
            '<span class="pw-dot idle" id="pwDot"></span>' +
            '<span>LINHA DO TEMPO &middot; ESTEIRA FRA</span>' +
          '</div>' +
          '<div class="pw-stage" id="pwStage"><strong>aguardando</strong></div>' +
        '</div>' +
        '<div class="pw-track">' +
          '<div class="pw-rail"><div class="pw-rail-fill" id="pwRailFill"></div></div>' +
          nodes +
        '</div>' +
        '<div class="pw-wave" id="pwWave">' + bars.join('') + '</div>' +
        '<div class="pw-footer">' +
          '<div class="pw-eta">⏱ <strong id="pwElapsed">00:00</strong> &nbsp;·&nbsp; <span id="pwEta">iniciar para ver previsao</span></div>' +
          '<div class="pw-pct" id="pwPct">0%</div>' +
        '</div>' +
      '</div>';
  }

  function ensureContainer() {
    var host = document.getElementById('pipelineWaveformHost');
    if (!host) {
      // injeta logo apos o banner do pipeline
      var anchor = document.getElementById('pipeline-banner');
      if (!anchor || !anchor.parentNode) return null;
      host = document.createElement('div');
      host.id = 'pipelineWaveformHost';
      anchor.parentNode.insertBefore(host, anchor.nextSibling);
    }
    if (!host.querySelector('#pipelineWaveform')) {
      host.innerHTML = buildHTML();
    }
    return host;
  }

  // ── Render ────────────────────────────────────────────────────────
  function render() {
    var host = ensureContainer();
    if (!host) return;
    var nodes = host.querySelectorAll('.pw-node');
    var bars = host.querySelectorAll('.pw-bar');
    var railFill = document.getElementById('pwRailFill');
    var dot = document.getElementById('pwDot');
    var stage = document.getElementById('pwStage');
    var elapsedEl = document.getElementById('pwElapsed');
    var etaEl = document.getElementById('pwEta');
    var pctEl = document.getElementById('pwPct');
    if (!railFill || !stage) return;

    var idx = state.activeIdx;
    var totalNodes = ETAPAS.length;

    nodes.forEach(function (n, i) {
      n.classList.remove('is-done', 'is-active', 'is-idle');
      if (!state.running) {
        n.classList.add('is-idle');
        return;
      }
      if (i < idx) n.classList.add('is-done');
      else if (i === idx) n.classList.add('is-active');
      else n.classList.add('is-idle');
    });

    // waveform: barras passadas verdes, atual pulsando cor da fase, futuras cinza
    var totalBars = bars.length;
    var perNode = totalBars / totalNodes;
    var activeStart = Math.floor(idx * perNode);
    var activeEnd = Math.floor((idx + 1) * perNode);
    var currentBar = Math.floor(activeStart + (state.progress / 100) * (activeEnd - activeStart));
    bars.forEach(function (b, i) {
      b.classList.remove('is-on', 'is-past');
      if (!state.running) return;
      if (i < currentBar) b.classList.add('is-past');
      else if (i < activeEnd) b.classList.add('is-on');
    });

    // rail: preenche ate o no atual + progresso da fase
    var railPct = state.running
      ? ((idx + state.progress / 100) / (totalNodes - 1)) * 100
      : 0;
    railFill.style.width = Math.min(100, railPct).toFixed(1) + '%';

    // dot
    if (dot) {
      if (state.running) {
        dot.classList.remove('idle');
      } else {
        dot.classList.add('idle');
      }
    }

    // header stage
    if (state.running && state.label) {
      stage.innerHTML = '<strong>' + escapeHtml(ETAPAS[idx].label) + '</strong> &middot; ' + escapeHtml(state.label);
    } else if (state.running) {
      stage.innerHTML = '<strong>' + escapeHtml(ETAPAS[idx].label) + '</strong>';
    } else {
      stage.innerHTML = '<strong>aguardando</strong>';
    }

    // elapsed / eta
    if (elapsedEl) elapsedEl.textContent = formatTime(state.elapsed);
    if (etaEl) {
      if (!state.running) {
        etaEl.textContent = 'iniciar para ver previsao';
      } else {
        var remaining = Math.max(0, ((totalNodes - idx - 1) * 90) - (state.progress * 0.9));
        etaEl.textContent = '~' + Math.round(remaining / 60) + ' min restantes';
      }
    }
    if (pctEl) {
      var totalPct = state.running
        ? Math.round(((idx + state.progress / 100) / totalNodes) * 100)
        : 0;
      pctEl.textContent = totalPct + '%';
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function formatTime(sec) {
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  // ── API publica ───────────────────────────────────────────────────
  function ativar(faseKey, label) {
    state.running = true;
    state.label = label || '';
    var idx = ETAPAS.findIndex(function (e) { return e.key === faseKey; });
    if (idx < 0) idx = 0;
    if (idx !== state.activeIdx) {
      state.activeIdx = idx;
      state.progress = 0;
    }
    state.activeKey = faseKey;
    ensureContainer();
    render();
    startFakeTicker();
  }

  function desativar() {
    state.running = false;
    state.activeKey = null;
    state.activeIdx = 0;
    state.progress = 0;
    state.label = '';
    state.elapsed = 0;
    stopFakeTicker();
    render();
  }

  function setProgress(pct) {
    state.progress = Math.max(0, Math.min(100, pct));
    render();
  }

  // Fallback: se nao vier progresso real, anda 1% a cada 1.5s na fase atual
  function startFakeTicker() {
    stopFakeTicker();
    state.fakeTimer = setInterval(function () {
      if (!state.running) return;
      state.elapsed += 1;
      state.progress = Math.min(100, state.progress + 0.7);
      if (state.progress >= 100) {
        // avanca para o proximo
        if (state.activeIdx < ETAPAS.length - 1) {
          state.activeIdx += 1;
          state.progress = 0;
        }
      }
      render();
    }, 1000);
  }

  function stopFakeTicker() {
    if (state.fakeTimer) {
      clearInterval(state.fakeTimer);
      state.fakeTimer = null;
    }
  }

  // ── Hook com o resto do admin (renderPipelineTimeline ja existente) ──
  // Wrap para capturar as chamadas existentes sem modificar pipeline-timeline.js
  function hookExisting() {
    var orig = window.renderPipelineTimeline;
    if (typeof orig !== 'function' || orig.__pw_wrapped) return;
    window.renderPipelineTimeline = function (ativo, status) {
      orig.call(this, ativo, status);
      if (ativo === null || ativo === undefined) {
        // nao desliga imediatamente: pode ser entre fases. So desliga se nao rodando.
        window.PipelineWaveform._syncFromStatus();
      } else {
        window.PipelineWaveform.ativar(ativo, status || '');
      }
    };
    window.renderPipelineTimeline.__pw_wrapped = true;
  }

  // Sincroniza com /api/pipeline/status a cada 5s (backstop caso SSE caia)
  function _syncFromStatus() {
    if (typeof window.authFetch !== 'function') return;
    window.authFetch('/api/pipeline/status')
      .then(function (r) { return r && r.json ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        if (d.rodando) {
          var key = null;
          if (d.current_job) {
            key = d.current_job.last_phase || d.current_job.phase;
            if (key) key = normalizeKey(key);
          }
          if (!key) key = mapFaseNum(d.fase_num);
          window.PipelineWaveform.ativar(key, d.fase_label || d.fase_atual || '');
        } else {
          // se ja passamos do estado, desativa
          if (state.running) {
            // mantem por mais 4s caso proximo ciclo comece logo
            setTimeout(function () {
              window.PipelineWaveform._recheckIdle();
            }, 4000);
          }
        }
      })
      .catch(function () {});
  }

  function _recheckIdle() {
    if (typeof window.authFetch !== 'function') return;
    window.authFetch('/api/pipeline/status')
      .then(function (r) { return r && r.json ? r.json() : null; })
      .then(function (d) {
        if (d && !d.rodando) desativar();
        else if (d && d.rodando) ativar(mapFaseNum(d.fase_num) || state.activeKey, d.fase_label || '');
      })
      .catch(function () {});
  }

  function normalizeKey(s) {
    s = (s || '').toString().toLowerCase();
    if (s.includes('builder') || s.includes('renderer')) return 'builder_renderer';
    if (s.includes('deploy') || s.includes('public')) return 'deploy';
    if (s.includes('franz') || s.includes('bryan') || s.includes('whatsapp')) return 'franz';
    if (s.includes('designer') || s.includes('design') || s.includes('arquiteto')) return 'designer';
    if (s.includes('prompt') || s.includes('nicho') || s.includes('agente_nicho')) return 'prompt_agent';
    if (s.includes('unsplash') || s.includes('foto') || s.includes('midia') || s.includes('mídia')) return 'media';
    if (s.includes('mercado') || s.includes('market')) return 'market_intelligence';
    if (s.includes('jina') || s.includes('keyword')) return 'jina';
    if (s.includes('caio') || s.includes('qualifica')) return 'caio';
    if (s.includes('hunter') || s.includes('lead:') || s.includes('maps')) return 'hunter';
    return null;
  }

  function mapFaseNum(n) {
    if (!n && n !== 0) return null;
    // mapear 1..10 para as chaves (ordem canonica)
    var map = ['hunter', 'caio', 'jina', 'market_intelligence', 'media', 'prompt_agent', 'designer', 'builder_renderer', 'deploy', 'franz'];
    var i = parseInt(n, 10) - 1;
    if (i < 0 || i >= map.length) return null;
    return map[i];
  }

  // ── Init ──────────────────────────────────────────────────────────
  function init() {
    injectStyles();
    ensureContainer();
    render();
    hookExisting();
    // backstop poll 5s
    setInterval(_syncFromStatus, 5000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expor
  window.PipelineWaveform = {
    ativar: ativar,
    desativar: desativar,
    setProgress: setProgress,
    _syncFromStatus: _syncFromStatus,
    _recheckIdle: _recheckIdle,
    ETAPAS: ETAPAS
  };
})();
