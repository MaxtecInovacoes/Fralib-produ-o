/**
 * pipeline-waveform.js
 * ===================
 * Linha do tempo visual estilo player de musica para o pipeline FraLib.
 *
 * Mostra 4 etapas MACRO (sem expor nomes internos dos agentes):
 *   1. Buscar    - Hunter vasculhando Google Maps
 *   2. Analisar  - Caio, Jina, Mercado, Midia qualificando o lead
 *   3. Produzir  - Prompt, Designer, Builder gerando o site
 *   4. Publicar  - Deploy e contato SDR (Franz)
 *
 * Cronometro UNICO compartilhado com o banner "PIPELINE RODANDO" e o
 * "Trabalhando ha" (vem de window.__pipelineSharedStart). Assim banner,
 * waveform e inline mostram o MESMO segundo.
 *
 * API publica:
 *   - window.PipelineWaveform.ativar(faseKey, label)  - liga com fase
 *   - window.PipelineWaveform.desativar()             - desliga
 *   - window.PipelineWaveform.setProgress(pct)        - 0..100
 */
(function () {
  'use strict';

  // ── 4 etapas MACRO (nao expoe estrutura interna) ───────────────────
  var ETAPAS = [
    { key: 'buscar',   icon: '🔎', label: 'Buscar',   tone: '#a855f7' },
    { key: 'analisar', icon: '📊', label: 'Analisar', tone: '#06b6d4' },
    { key: 'produzir', icon: '🎨', label: 'Produzir', tone: '#ec4899' },
    { key: 'publicar', icon: '📤', label: 'Publicar', tone: '#10b981' }
  ];

  // Mapeia qualquer chave vinda do backend para a macro correspondente
  // (mantem compatibilidade com o modulo legado que passa 'hunter'/'caio'/etc)
  function macroFromKey(k) {
    if (!k) return null;
    k = String(k).toLowerCase();
    if (k.includes('deploy') || k.includes('public') || k.includes('franz') || k.includes('bryan') || k.includes('whatsapp')) return 'publicar';
    if (k.includes('builder') || k.includes('renderer') || k.includes('designer') || k.includes('design') || k.includes('arquiteto') || k.includes('prompt') || k.includes('nicho') || k.includes('agente_nicho')) return 'produzir';
    if (k.includes('caio') || k.includes('qualifica') || k.includes('jina') || k.includes('keyword') || k.includes('mercado') || k.includes('market') || k.includes('unsplash') || k.includes('midia') || k.includes('mídia') || k.includes('foto')) return 'analisar';
    if (k.includes('hunter') || k.includes('lead:') || k.includes('maps')) return 'buscar';
    return null;
  }

  // Mapeia as 11 fases canonicas do backend em quatro macroetapas.
  function macroFromNum(n) {
    var i = parseInt(n, 10) - 1;
    if (i < 0) return 'buscar';
    if (i <= 0) return 'buscar';     // hunter
    if (i <= 4) return 'analisar';   // caio..midia
    if (i <= 8) return 'produzir';   // prompt..builder
    return 'publicar';               // deploy..franz
  }

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
      '  width: 36px; height: 36px;',
      '  border-radius: 50%;',
      '  display: flex; align-items: center; justify-content: center;',
      '  font-size: 17px;',
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
      '  font-size: 10px;',
      '  letter-spacing: 1px;',
      '  text-transform: uppercase;',
      '  color: #64748b;',
      '  text-align: center;',
      '  white-space: nowrap;',
      '  overflow: hidden;',
      '  text-overflow: ellipsis;',
      '  max-width: 100%;',
      '  font-family: var(--fl-font-brand, "Inter", sans-serif);',
      '  font-weight: 600;',
      '}',
      '.pw-node.is-done .pw-name { color: #10b981; }',
      '.pw-node.is-active .pw-name { color: var(--pw-tone, #a855f7); font-weight: 700; }',
      '.pw-node-status {',
      '  position: absolute;',
      '  top: 64px;',
      '  left: 50%;',
      '  transform: translateX(-50%);',
      '  white-space: nowrap;',
      '  font-size: 9px;',
      '  color: var(--pw-tone, #a855f7);',
      '  background: rgba(15,23,42,.95);',
      '  border: 1px solid var(--pw-tone, #a855f7);',
      '  padding: 2px 8px;',
      '  border-radius: 99px;',
      '  max-width: 220px;',
      '  overflow: hidden;',
      '  text-overflow: ellipsis;',
      '  opacity: 0;',
      '  transition: opacity .25s ease;',
      '  pointer-events: none;',
      '  z-index: 4;',
      '  box-shadow: 0 4px 14px rgba(0,0,0,.4);',
      '  display: none;',
      '}',
      '.pw-node.is-active .pw-node-status { opacity: 1; display: block; }',
      '.pw-rail {',
      '  position: absolute;',
      '  left: 0; right: 0;',
      '  top: 24px;',
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
      '  background: linear-gradient(90deg, #a855f7, #06b6d4, #ec4899, #10b981, #10b981);',
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
      '  margin-top: 12px;',
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
      '.pw-avg { color: #94a3b8; font-family: var(--fl-font-mono, monospace); font-size: 10px; letter-spacing: .3px; }',
      '.pw-telemetry {',
      '  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px;',
      '  margin-top: 10px; padding-top: 10px;',
      '  border-top: 1px solid rgba(148,163,184,.14);',
      '  color: #94a3b8; font-size: 9px;',
      '}',
      '.pw-telemetry strong { color: #f1f5f9; font-size: 11px; font-variant-numeric: tabular-nums; }',
      '.pw-job { margin-left: auto; color: #67e8f9; }',
      '.pw-log-toggle {',
      '  display: inline-flex; min-height: 32px; align-items: center; gap: 8px;',
      '  margin-top: 10px; padding: 7px 10px;',
      '  border: 1px solid rgba(6,182,212,.42); border-radius: 6px;',
      '  background: rgba(8,145,178,.08); color: #67e8f9; cursor: pointer;',
      '  font: 700 9px var(--fl-font-mono, monospace); text-transform: uppercase;',
      '  transition: background .15s, border-color .15s, transform .15s;',
      '}',
      '.pw-log-toggle:hover { border-color: #22d3ee; background: rgba(8,145,178,.16); }',
      '.pw-log-toggle:active { transform: translateY(1px); }',
      '.pw-log-toggle:focus-visible { outline: 2px solid #22d3ee; outline-offset: 2px; }',
      '.pw-log-toggle span {',
      '  display: inline-flex; min-width: 18px; height: 18px; align-items: center;',
      '  justify-content: center; border-radius: 9px; background: #164e63;',
      '}',
      '.pw-live-panel {',
      '  display: grid; grid-template-rows: 0fr; opacity: 0;',
      '  transition: grid-template-rows .22s cubic-bezier(.16,1,.3,1), opacity .18s;',
      '}',
      '.pw-live-panel.is-open { grid-template-rows: 1fr; opacity: 1; }',
      '.pw-call-list { min-height: 0; overflow: hidden; }',
      '.pw-call-row {',
      '  display: grid; grid-template-columns: minmax(80px,.8fr) minmax(100px,1fr) auto auto;',
      '  gap: 10px; padding: 7px 2px; border-bottom: 1px solid rgba(148,163,184,.08);',
      '  color: #b9c4d5; font-size: 9px;',
      '}',
      '.pw-call-row strong { color: #67e8f9; font-weight: 600; }',
      '.pw-log-list { max-height: 220px; overflow: auto; border-top: 1px solid rgba(6,182,212,.2); }',
      '.pw-log-row {',
      '  display: grid; grid-template-columns: 52px 84px 1fr; gap: 8px;',
      '  padding: 6px 2px; border-bottom: 1px solid rgba(148,163,184,.08);',
      '  color: #b9c4d5; font-size: 9px; line-height: 1.45;',
      '}',
      '.pw-log-row time { color: #64748b; }',
      '.pw-log-row strong { color: #67e8f9; font-size: 8px; text-transform: uppercase; }',
      '.pw-empty { padding: 12px 2px; color: #75839a; font-size: 9px; }',
      '@media (prefers-reduced-motion: reduce) {',
      '  .pw-bubble, .pw-bar, .pw-rail-fill, .pw-wrap::before, .pw-live-panel { animation: none !important; transition: none !important; }',
      '}',
      '@media (max-width: 720px) {',
      '  .pw-name { font-size: 9px; }',
      '  .pw-stage { max-width: 50%; }',
      '  .pw-job { width: 100%; margin-left: 0; }',
      '  .pw-call-row { grid-template-columns: 1fr auto; }',
      '  .pw-call-row span:nth-child(2) { display: none; }',
      '  .pw-log-row { grid-template-columns: 46px 1fr; }',
      '  .pw-log-row strong { display: none; }',
      '}'
    ].join('\n');
    document.head.appendChild(s);
  }

  // ── Estado interno ────────────────────────────────────────────────
  var state = {
    running: false,
    status: 'idle',
    activeMacro: 'buscar',
    label: '',
    elapsed: 0,
    queuedAt: null,
    startedAt: null,
    finishedAt: null,
    jobId: null,
    runId: null,
    phases: [],
    llm: { totals: {}, by_phase: [] },
    summary: {},
    logsOpen: false,
    elapsedTimer: null,
    syncTimer: null,
    avgByMacro: null,    // { macros: {...}, total_avg_seconds, window_days, min_samples }
    avgFetchedAt: 0,
    avgTimer: null
  };
  function formatElapsed(sec) {
    sec = Math.max(0, Math.floor(sec));
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function parseTimeMs(value) {
    if (!value) return null;
    var ms = Date.parse(value);
    return Number.isFinite(ms) ? ms : null;
  }

  function measuredElapsedSeconds() {
    var started = parseTimeMs(state.startedAt);
    var finished = parseTimeMs(state.finishedAt);
    if (started) {
      var end = finished || (state.running ? Date.now() : null);
      if (end) return Math.max(0, Math.floor((end - started) / 1000));
    }
    return Math.max(0, Number(state.elapsed) || 0);
  }

  function refreshElapsedDisplay() {
    state.elapsed = measuredElapsedSeconds();
    var elapsed = document.getElementById('pwElapsed');
    if (elapsed) elapsed.textContent = formatElapsed(state.elapsed);
  }

  function buildHTML() {
    var nodes = ETAPAS.map(function (e, i) {
      return '' +
        '<div class="pw-node" data-idx="' + i + '" data-key="' + e.key + '" style="--pw-tone:' + e.tone + ';">' +
          '<div class="pw-bubble">' + e.icon + '</div>' +
          '<div class="pw-name">' + e.label + '</div>' +
          '<div class="pw-node-status" data-status></div>' +
        '</div>';
    }).join('');

    // 60 barras para o waveform
    var bars = [];
    for (var i = 0; i < 60; i++) {
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
          '<div class="pw-eta">⏱ <strong id="pwElapsed">00:00</strong> &nbsp;·&nbsp; <span id="pwEta">aguardando medicoes</span> &nbsp;·&nbsp; <span id="pwAvg" class="pw-avg"></span></div>' +
          '<div class="pw-pct" id="pwPct">0%</div>' +
        '</div>' +
      '</div>';
  }

  function ensureContainer() {
    var host = document.getElementById('pipelineWaveformHost');
    if (!host) {
      // Fallback: ancora no escritorio se admin.html antigo
      var anchor = document.getElementById('pixelOfficeWrap')
        || document.getElementById('pipeline-banner')
        || document.querySelector('.main');
      if (!anchor || !anchor.parentNode) return null;
      host = document.createElement('div');
      host.id = 'pipelineWaveformHost';
      host.style.cssText = 'margin-bottom:16px;min-width:0;';
      // insere ANTES do escritorio (assim a timeline fica acima, escritorio embaixo)
      anchor.parentNode.insertBefore(host, anchor);
    }
    if (!host.querySelector('#pipelineWaveform')) {
      host.innerHTML = buildHTML();
    }
    return host;
  }

  function findIdx(key) {
    for (var i = 0; i < ETAPAS.length; i++) {
      if (ETAPAS[i].key === key) return i;
    }
    return 0;
  }

  function compactNumber(value) {
    var total = Number(value) || 0;
    if (total >= 1000000) return (total / 1000000).toFixed(2) + 'M';
    if (total >= 1000) return (total / 1000).toFixed(1) + 'k';
    return String(total);
  }

  function macroDurations() {
    var result = {};
    (state.phases || []).forEach(function (phase) {
      var macro = macroFromKey(phase.phase || phase.agent) || macroFromNum(phase.phase_num);
      if (!macro) return;
      result[macro] = (result[macro] || 0) + (Number(phase.duration_ms) || 0);
    });
    return result;
  }

  function renderCallDetails() {
    var container = document.getElementById('pwCallList');
    if (!container) return;
    var calls = state.llm && Array.isArray(state.llm.by_phase) ? state.llm.by_phase : [];
    if (!calls.length) {
      container.innerHTML = '<div class="pw-empty">As chamadas LLM aparecerao aqui.</div>';
      return;
    }
    container.innerHTML = calls.map(function (call) {
      var tokens = (Number(call.input_tokens) || 0) + (Number(call.output_tokens) || 0) +
        (Number(call.cache_read_tokens) || 0) + (Number(call.cache_created_tokens) || 0);
      return '<div class="pw-call-row"><strong>' + escapeHtml(call.phase || call.agent || 'pipeline') + '</strong>' +
        '<span>' + escapeHtml((call.provider || '') + ' · ' + (call.model || '')) + '</span>' +
        '<span>' + escapeHtml(String(call.calls || 0)) + ' chamadas · ' + escapeHtml(compactNumber(tokens)) + ' tokens</span>' +
        '<span>US$ ' + (Number(call.cost_usd) || 0).toFixed(4).replace('.', ',') + '</span></div>';
    }).join('');
  }

  // ── Media historica por tenant/fase (PRD #65) ────────────────────
  function fetchAvgByMacro() {
    var now = Date.now();
    if (state.avgByMacro && now - state.avgFetchedAt < 60000) return Promise.resolve();
    if (typeof window.authFetch !== 'function') return Promise.resolve();
    return window.authFetch('/api/pipeline/avg-by-macro?dias=30&min_samples=3')
      .then(function (r) { return r && r.json ? r.json() : null; })
      .then(function (data) {
        if (data) {
          state.avgByMacro = data;
          state.avgFetchedAt = now;
          render();
        }
      })
      .catch(function () { /* sem media, ok */ });
  }

  function renderAvg() {
    var el = document.getElementById('pwAvg');
    if (!el) return;
    var avg = state.avgByMacro;
    if (!avg) { el.textContent = ''; return; }
    var total = avg.total_avg_seconds;
    if (!total) {
      el.textContent = 'média: calculando (' + avg.min_samples + '+ runs por macro)';
      return;
    }
    var elapsed = measuredElapsedSeconds();
    var remaining = Math.max(0, Math.floor(total - elapsed));
    el.textContent = 'média ' + formatElapsed(total) + ' · resta ' + formatElapsed(remaining);
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
    var etaEl = document.getElementById('pwEta');
    var pctEl = document.getElementById('pwPct');
    if (!railFill || !stage) return;

    var running = state.running;

    var idx = findIdx(state.activeMacro);
    var totalNodes = ETAPAS.length;
    var durations = macroDurations();

    nodes.forEach(function (n, i) {
      n.classList.remove('is-done', 'is-active', 'is-idle');
      var statusEl = n.querySelector('[data-status]');
      if (statusEl) statusEl.textContent = '';
      if (!running) {
        if (state.status === 'completed') n.classList.add('is-done');
        else n.classList.add('is-idle');
        return;
      }
      if (i < idx) n.classList.add('is-done');
      else if (i === idx) n.classList.add('is-active');
      else n.classList.add('is-idle');
      var macroKey = n.getAttribute('data-key');
      if (durations[macroKey]) n.title = ETAPAS[i].label + ': ' + formatElapsed(durations[macroKey] / 1000);
      // Mostra label do que esta rodando agora, embaixo do no ativo
      if (i === idx && state.label && statusEl) {
        statusEl.textContent = state.label;
      }
    });

    // waveform: barras passadas verdes, atual pulsando cor da fase, futuras cinza
    var totalBars = bars.length;
    var perNode = totalBars / totalNodes;
    var activeStart = Math.floor(idx * perNode);
    var activeEnd = Math.floor((idx + 1) * perNode);
    bars.forEach(function (b, i) {
      b.classList.remove('is-on', 'is-past');
      if (!running) return;
      if (i < activeStart) b.classList.add('is-past');
      else if (i < activeEnd) b.classList.add('is-on');
    });

    // O preenchimento muda somente quando uma macroetapa real e persistida.
    var railPct = state.status === 'completed' ? 100 : (running ? idx / (totalNodes - 1) * 100 : 0);
    railFill.style.width = Math.min(100, railPct).toFixed(1) + '%';

    if (dot) {
      if (running) dot.classList.remove('idle');
      else dot.classList.add('idle');
    }

    if (running && state.label) {
      stage.innerHTML = '<strong>' + ETAPAS[idx].label + '</strong> &middot; ' + escapeHtml(state.label);
    } else if (running) {
      stage.innerHTML = '<strong>' + ETAPAS[idx].label + '</strong>';
    } else if (state.status === 'pending') {
      stage.innerHTML = '<strong>na fila</strong> &middot; aguardando worker';
    } else if (state.status === 'completed') {
      stage.innerHTML = '<strong>concluido</strong> &middot; ultima execucao';
    } else if (state.status && state.status.indexOf('failed') === 0) {
      stage.innerHTML = '<strong>falhou</strong> &middot; consulte os logs';
    } else {
      stage.innerHTML = '<strong>aguardando</strong>';
    }

    refreshElapsedDisplay();
    renderAvg();

    if (etaEl) {
      if (running && state.startedAt) etaEl.textContent = 'medindo pelo inicio registrado';
      else if (running) etaEl.textContent = 'aguardando inicio registrado';
      else if (state.status === 'pending') etaEl.textContent = 'na fila · aguardando worker';
      else if (state.status === 'completed') etaEl.textContent = 'ultima execucao concluida';
      else etaEl.textContent = 'aguardando medicoes';
    }
    if (pctEl) {
      var totalPct = state.status === 'completed' ? 100 : (running ? Math.round(idx / totalNodes * 100) : 0);
      pctEl.textContent = totalPct + '%';
    }
    var totals = state.llm && state.llm.totals ? state.llm.totals : {};
    if (document.getElementById('pwTokens')) document.getElementById('pwTokens').textContent = compactNumber(totals.total_tokens || 0);
    if (document.getElementById('pwCalls')) document.getElementById('pwCalls').textContent = totals.calls || 0;
    if (document.getElementById('pwCost')) document.getElementById('pwCost').textContent = 'US$ ' + (Number(totals.cost_usd) || 0).toFixed(4).replace('.', ',');
    if (document.getElementById('pwAvg')) document.getElementById('pwAvg').textContent = formatElapsed(state.summary.average_elapsed_seconds || 0);
    if (document.getElementById('pwJob')) document.getElementById('pwJob').textContent = state.jobId ? 'Job #' + state.jobId + (state.runId ? ' · run ' + state.runId : '') : 'sem job ativo';
    renderCallDetails();
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  // ── API publica ───────────────────────────────────────────────────
  function ativar(faseKey, label) {
    var macro = macroFromKey(faseKey);
    if (!macro) macro = 'buscar';
    state.running = true;
    state.status = 'running';
    state.activeMacro = macro;
    state.label = label || '';
    ensureContainer();
    setLogsOpen(true);
    render();
    updateElapsedTimer();
  }

  function desativar() {
    state.running = false;
    updateElapsedTimer();
    render();
  }

  function setProgress() {
    // Compatibilidade: progresso agora vem apenas de fases persistidas.
  }

  function updateElapsedTimer() {
    if (state.elapsedTimer) clearInterval(state.elapsedTimer);
    state.elapsedTimer = null;
    refreshElapsedDisplay();
    if (!state.running || !state.startedAt) return;
    state.elapsedTimer = setInterval(refreshElapsedDisplay, 1000);
  }

  function applyStatus(data) {
    if (!data) return;
    var telemetry = data.telemetry || {};
    var job = data.current_job || data.latest_job || {};
    state.status = telemetry.status || job.status || (state.running ? 'running' : 'idle');
    state.running = state.status === 'running';
    state.jobId = telemetry.job_id || job.id || null;
    state.runId = telemetry.run_id || job.run_id || null;
    state.queuedAt = telemetry.queued_at || job.criado_em || null;
    state.startedAt = telemetry.started_at || job.iniciado_em || null;
    state.finishedAt = telemetry.finished_at || job.concluido_em || null;
    state.elapsed = Number(telemetry.elapsed_seconds) || 0;
    state.phases = Array.isArray(telemetry.phases) ? telemetry.phases : [];
    state.llm = telemetry.llm || { totals: {}, by_phase: [] };
    state.summary = data.runtime_summary || telemetry.runtime_summary || {};
    var phaseKey = job.last_phase || data.fase_atual;
    state.activeMacro = macroFromKey(phaseKey) || macroFromNum(job.phase_num || data.fase_num) || state.activeMacro;
    state.label = data.fase_label || job.phase_label || job.last_phase || state.label;
    if (state.running) setLogsOpen(true);
    updateElapsedTimer();
    render();
  }

  function setLogsOpen(open) {
    state.logsOpen = Boolean(open);
    var panel = document.getElementById('pwLivePanel');
    var toggle = document.getElementById('pwLogToggle');
    if (panel) panel.classList.toggle('is-open', state.logsOpen);
    if (toggle) {
      toggle.setAttribute('aria-expanded', state.logsOpen ? 'true' : 'false');
      var count = document.getElementById('pwLogCount');
      toggle.childNodes[0].nodeValue = state.logsOpen ? 'Ocultar logs ' : 'Acompanhar logs ';
      if (count) toggle.appendChild(count);
    }
  }

  function isPipelineEvent(data) {
    if (!data) return false;
    if (data.event_kind === 'pipeline_phase' || data.evento === 'PIPELINE_STATUS') return true;
    var message = String(data.mensagem || '');
    return Boolean(macroFromKey(data.phase || message)) || /pipeline|fase|deploy|builder|lead:/i.test(message);
  }

  function appendLog(data) {
    if (!isPipelineEvent(data)) return;
    var list = document.getElementById('pwLogList');
    if (!list) return;
    var empty = document.getElementById('pwLogEmpty');
    if (empty) empty.remove();
    var row = document.createElement('div');
    row.className = 'pw-log-row';
    var phase = data.phase || macroFromKey(data.mensagem) || 'pipeline';
    row.innerHTML = '<time>' + escapeHtml(data.ts || new Date().toLocaleTimeString('pt-BR')) + '</time>' +
      '<strong>' + escapeHtml(String(phase).replace('_', ' ')) + '</strong>' +
      '<span>' + escapeHtml(data.mensagem || data.label || 'Atualizacao da pipeline') + '</span>';
    list.appendChild(row);
    while (list.children.length > 80) list.removeChild(list.firstChild);
    list.scrollTop = list.scrollHeight;
    var count = document.getElementById('pwLogCount');
    if (count) count.textContent = list.querySelectorAll('.pw-log-row').length;
    if (state.running || data.event_kind === 'pipeline_phase') setLogsOpen(true);
  }

  function scheduleSync() {
    if (state.syncTimer) clearTimeout(state.syncTimer);
    state.syncTimer = setTimeout(_syncFromStatus, 250);
  }

  function handleSse(data) {
    appendLog(data);
    if (data && (data.type === 'progress' || data.event_kind === 'pipeline_phase')) {
      state.running = true;
      state.status = 'running';
      state.activeMacro = macroFromKey(data.phase) || macroFromNum(data.fase) || state.activeMacro;
      state.label = data.label || data.mensagem || state.label;
      state.jobId = data.job_id || state.jobId;
      state.runId = data.run_id || state.runId;
      setLogsOpen(true);
      render();
      scheduleSync();
    } else if (isPipelineEvent(data)) scheduleSync();
  }

  function hookSse() {
    if (window._pixelOfficeSSEHook && window._pixelOfficeSSEHook.__pw_wrapped) return;
    var original = window._pixelOfficeSSEHook;
    window._pixelOfficeSSEHook = function (data) {
      if (original) original(data);
      handleSse(data);
    };
    window._pixelOfficeSSEHook.__pw_wrapped = true;
  }

  // ── Hook com o modulo legado (renderPipelineTimeline) ─────────────
  function hookExisting() {
    var orig = window.renderPipelineTimeline;
    if (typeof orig !== 'function' || orig.__pw_wrapped) return;
    window.renderPipelineTimeline = function (ativo, status) {
      try { orig.call(this, ativo, status); } catch (e) {}
      if (ativo === null || ativo === undefined) {
        // nao desliga: pode ser entre fases. _syncFromStatus confirma.
        _syncFromStatus();
      } else {
        window.PipelineWaveform.ativar(ativo, status || '');
      }
    };
    window.renderPipelineTimeline.__pw_wrapped = true;
  }

  // Sincroniza com /api/pipeline/status a cada 5s
  function _syncFromStatus() {
    if (typeof window.authFetch !== 'function') return Promise.resolve();
    return window.authFetch('/api/pipeline/status')
      .then(function (r) { return r && r.json ? r.json() : null; })
      .then(applyStatus)
      .catch(function () {});
  }

  // ── Init ──────────────────────────────────────────────────────────
  function init() {
    injectStyles();
    ensureContainer();
    render();
    hookExisting();
    hookSse();
    var toggle = document.getElementById('pwLogToggle');
    if (toggle) toggle.addEventListener('click', function () { setLogsOpen(!state.logsOpen); });
    _syncFromStatus();
    setInterval(_syncFromStatus, 5000);
    fetchAvgByMacro();
    state.avgTimer = setInterval(fetchAvgByMacro, 5 * 60 * 1000);  // 5min
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.PipelineWaveform = {
    ativar: ativar,
    desativar: desativar,
    setProgress: setProgress,
    _syncFromStatus: _syncFromStatus,
    applyStatus: applyStatus,
    handleSse: handleSse,
    macroFromKey: macroFromKey,
    macroFromNum: macroFromNum,
    ETAPAS: ETAPAS
  };
})();
