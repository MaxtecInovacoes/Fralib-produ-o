/**
 * FraLib Admin - Audio Panel UI
 * Player flutuante (canto inferior direito) que controla o audio-player.
 * Cada usuário cola sua URL do YouTube - preferência salva no localStorage.
 */
(function () {
  'use strict';

  var PANEL_ID = 'fralib-audio-panel';
  var COLLAPSE_KEY = 'fralib_audio_panel_collapsed';

  /** Cria o HTML do painel */
  function buildPanelHTML() {
    return '' +
      '<div id="' + PANEL_ID + '" class="fralib-audio-panel" data-collapsed="false">' +
        '<button class="fralib-audio-toggle" id="fralib-audio-toggle" aria-label="Minimizar player" title="Minimizar">' +
          '<span class="fralib-audio-toggle-icon">▼</span>' +
        '</button>' +
        '<div class="fralib-audio-header">' +
          '<span class="fralib-audio-icon">🎵</span>' +
          '<span class="fralib-audio-title">Player de Música</span>' +
          '<span class="fralib-audio-status" id="fralib-audio-status">Pausado</span>' +
        '</div>' +
        '<div class="fralib-audio-body">' +
          '<div class="fralib-audio-controls">' +
            '<button class="fralib-audio-btn" id="fralib-audio-play" aria-label="Tocar/Pausar">▶</button>' +
            '<input type="range" class="fralib-audio-volume" id="fralib-audio-volume" min="0" max="50" value="20" aria-label="Volume">' +
            '<span class="fralib-audio-volume-label" id="fralib-audio-volume-label">20%</span>' +
          '</div>' +
          '<div class="fralib-audio-url-row">' +
            '<input type="text" class="fralib-audio-url" id="fralib-audio-url" placeholder="Cole URL do YouTube aqui..." aria-label="URL do YouTube">' +
            '<button class="fralib-audio-load" id="fralib-audio-load">Carregar</button>' +
          '</div>' +
          '<div class="fralib-audio-error" id="fralib-audio-error" role="alert"></div>' +
        '</div>' +
      '</div>';
  }

  /** Cria os estilos CSS do painel */
  function injectStyles() {
    if (document.getElementById('fralib-audio-styles')) return;
    var css = '' +
      '.fralib-audio-panel{' +
        'position:fixed;bottom:16px;right:16px;z-index:9999;' +
        'background:linear-gradient(135deg,rgba(15,23,42,0.95),rgba(30,41,59,0.95));' +
        'backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);' +
        'border:1px solid rgba(148,163,184,0.2);border-radius:12px;' +
        'box-shadow:0 10px 40px rgba(0,0,0,0.4);' +
        'color:#f1f5f9;font-family:"DM Sans",system-ui,sans-serif;' +
        'min-width:320px;max-width:380px;overflow:hidden;' +
        'transition:all 0.3s ease;' +
      '}' +
      '.fralib-audio-header{' +
        'display:flex;align-items:center;gap:8px;padding:10px 14px;' +
        'background:rgba(15,23,42,0.6);border-bottom:1px solid rgba(148,163,184,0.1);' +
        'font-size:13px;font-weight:500;' +
      '}' +
      '.fralib-audio-icon{font-size:16px;}' +
      '.fralib-audio-title{flex:1;}' +
      '.fralib-audio-status{' +
        'font-size:11px;padding:2px 8px;border-radius:10px;' +
        'background:rgba(100,116,139,0.3);color:#cbd5e1;' +
      '}' +
      '.fralib-audio-status[data-state="playing"]{background:rgba(34,197,94,0.25);color:#86efac;}' +
      '.fralib-audio-status[data-state="loaded"]{background:rgba(59,130,246,0.25);color:#93c5fd;}' +
      '.fralib-audio-status[data-state="error"]{background:rgba(239,68,68,0.25);color:#fca5a5;}' +
      '.fralib-audio-body{padding:12px 14px;}' +
      '.fralib-audio-controls{display:flex;align-items:center;gap:10px;margin-bottom:10px;}' +
      '.fralib-audio-btn{' +
        'width:36px;height:36px;border:none;border-radius:50%;cursor:pointer;' +
        'background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;' +
        'font-size:14px;display:flex;align-items:center;justify-content:center;' +
        'transition:transform 0.15s,box-shadow 0.15s;flex-shrink:0;' +
      '}' +
      '.fralib-audio-btn:hover{transform:scale(1.08);box-shadow:0 4px 12px rgba(59,130,246,0.4);}' +
      '.fralib-audio-btn:active{transform:scale(0.96);}' +
      '.fralib-audio-volume{' +
        'flex:1;height:4px;-webkit-appearance:none;appearance:none;' +
        'background:rgba(148,163,184,0.2);border-radius:2px;outline:none;cursor:pointer;' +
      '}' +
      '.fralib-audio-volume::-webkit-slider-thumb{' +
        '-webkit-appearance:none;appearance:none;width:14px;height:14px;' +
        'border-radius:50%;background:#3b82f6;cursor:pointer;' +
        'box-shadow:0 0 0 3px rgba(59,130,246,0.2);' +
      '}' +
      '.fralib-audio-volume::-moz-range-thumb{' +
        'width:14px;height:14px;border-radius:50%;background:#3b82f6;cursor:pointer;' +
        'border:none;box-shadow:0 0 0 3px rgba(59,130,246,0.2);' +
      '}' +
      '.fralib-audio-volume-label{font-size:11px;color:#94a3b8;min-width:32px;text-align:right;}' +
      '.fralib-audio-url-row{display:flex;gap:6px;}' +
      '.fralib-audio-url{' +
        'flex:1;padding:6px 10px;border:1px solid rgba(148,163,184,0.2);border-radius:6px;' +
        'background:rgba(15,23,42,0.6);color:#f1f5f9;font-size:12px;outline:none;' +
        'transition:border-color 0.15s;min-width:0;' +
      '}' +
      '.fralib-audio-url:focus{border-color:#3b82f6;}' +
      '.fralib-audio-url::placeholder{color:#64748b;}' +
      '.fralib-audio-load{' +
        'padding:6px 12px;border:none;border-radius:6px;cursor:pointer;' +
        'background:#3b82f6;color:#fff;font-size:12px;font-weight:500;flex-shrink:0;' +
        'transition:background 0.15s;' +
      '}' +
      '.fralib-audio-load:hover{background:#2563eb;}' +
      '.fralib-audio-error{' +
        'font-size:11px;color:#fca5a5;min-height:14px;margin-top:6px;' +
      '}' +
      '.fralib-audio-toggle{' +
        'position:absolute;top:6px;right:6px;background:transparent;border:none;' +
        'color:#94a3b8;cursor:pointer;font-size:10px;padding:4px 6px;border-radius:4px;' +
        'transition:background 0.15s;' +
      '}' +
      '.fralib-audio-toggle:hover{background:rgba(148,163,184,0.15);color:#f1f5f9;}' +
      '.fralib-audio-panel[data-collapsed="true"] .fralib-audio-body{' +
        'display:none;' +
      '}' +
      '.fralib-audio-panel[data-collapsed="true"]{' +
        'min-width:auto;' +
      '}' +
      '.fralib-audio-panel[data-collapsed="true"] .fralib-audio-toggle-icon{' +
        'transform:rotate(-90deg);' +
      '}' +
      '@media (max-width:640px){' +
        '.fralib-audio-panel{left:16px;right:16px;min-width:auto;max-width:none;}' +
      '}';
    var style = document.createElement('style');
    style.id = 'fralib-audio-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /** Helper: $ para querySelector */
  function $(sel) { return document.querySelector(sel); }

  /** Atualiza o texto do status */
  function setStatus(state, text) {
    var el = $('#fralib-audio-status');
    if (!el) return;
    el.setAttribute('data-state', state);
    el.textContent = text;
  }

  /** Atualiza o botão play/pause */
  function setPlayButton(isPlaying) {
    var btn = $('#fralib-audio-play');
    if (!btn) return;
    btn.textContent = isPlaying ? '⏸' : '▶';
    btn.setAttribute('aria-label', isPlaying ? 'Pausar' : 'Tocar');
  }

  /** Mostra mensagem de erro */
  function showError(msg) {
    var el = $('#fralib-audio-error');
    if (el) el.textContent = msg || '';
  }

  /** Anexa event listeners */
  function attachListeners() {
    // Botão Play/Pause
    var playBtn = $('#fralib-audio-play');
    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (!window.fralibAudio) return;
        var st = window.fralibAudio.getState();
        if (st.isPlaying) {
          window.fralibAudio.pause();
        } else {
          if (st.videoId) {
            window.fralibAudio.resume();
          } else {
            showError('Cole uma URL do YouTube primeiro');
          }
        }
      });
    }

    // Slider de volume
    var volumeSlider = $('#fralib-audio-volume');
    var volumeLabel = $('#fralib-audio-volume-label');
    if (volumeSlider && volumeLabel) {
      volumeSlider.addEventListener('input', function () {
        var v = parseInt(volumeSlider.value, 10);
        volumeLabel.textContent = v + '%';
        if (window.fralibAudio) window.fralibAudio.setVolume(v);
      });
    }

    // Botão Carregar
    var loadBtn = $('#fralib-audio-load');
    var urlInput = $('#fralib-audio-url');
    if (loadBtn && urlInput) {
      var handleLoad = function () {
        var url = urlInput.value.trim();
        if (!url) { showError('Cole uma URL do YouTube'); return; }
        if (!window.fralibAudio) { showError('Player não inicializado'); return; }
        if (window.fralibAudio.play(url)) {
          showError('');
        } else {
          showError('URL inválida. Use youtube.com/watch?v=... ou youtu.be/...');
        }
      };
      loadBtn.addEventListener('click', handleLoad);
      urlInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') handleLoad();
      });
    }

    // Botão minimizar
    var toggleBtn = $('#fralib-audio-toggle');
    var panel = document.getElementById(PANEL_ID);
    if (toggleBtn && panel) {
      // Restaurar estado minimizado
      var collapsed = localStorage.getItem(COLLAPSE_KEY) === 'true';
      panel.setAttribute('data-collapsed', collapsed ? 'true' : 'false');
      toggleBtn.addEventListener('click', function () {
        var isCollapsed = panel.getAttribute('data-collapsed') === 'true';
        panel.setAttribute('data-collapsed', isCollapsed ? 'false' : 'true');
        localStorage.setItem(COLLAPSE_KEY, isCollapsed ? 'false' : 'true');
      });
    }

    // Listener de status do player
    if (window.fralibAudio) {
      window.fralibAudio.onStatusChange(function (status, code) {
        switch (status) {
          case 'playing':
            setStatus('playing', '▶ Tocando');
            setPlayButton(true);
            showError('');
            break;
          case 'paused':
            setStatus('paused', '⏸ Pausado');
            setPlayButton(false);
            break;
          case 'loaded':
            setStatus('loaded', '🎵 Pronto');
            setPlayButton(false);
            break;
          case 'error':
            var msg = 'Vídeo indisponível';
            if (code === 2) msg = 'Parâmetro inválido';
            else if (code === 5) msg = 'Erro de reprodução';
            else if (code === 100 || code === 101 || code === 150) msg = 'Vídeo com restrição';
            setStatus('error', '⚠ Erro');
            showError(msg);
            setPlayButton(false);
            break;
          case 'cleared':
            setStatus('empty', 'Vazio');
            setPlayButton(false);
            showError('');
            break;
          case 'empty':
            setStatus('empty', 'Vazio');
            break;
        }
      });
    }
  }

  /** Inicializa o painel */
  function init() {
    injectStyles();
    // Injeta HTML
    var container = document.createElement('div');
    container.innerHTML = buildPanelHTML();
    document.body.appendChild(container.firstChild);

    // Inicializa o player e sincroniza UI
    if (window.fralibAudio) {
      window.fralibAudio.init().then(function () {
        var st = window.fralibAudio.getState();
        // Restaurar URL no input
        var urlInput = $('#fralib-audio-url');
        if (urlInput && st.url) urlInput.value = st.url;
        // Restaurar volume
        var volSlider = $('#fralib-audio-volume');
        var volLabel = $('#fralib-audio-volume-label');
        if (volSlider) volSlider.value = st.volume;
        if (volLabel) volLabel.textContent = st.volume + '%';
        // Status inicial
        if (st.videoId) {
          setStatus('loaded', '🎵 Pronto');
        } else {
          setStatus('empty', 'Vazio');
        }
      }).catch(function (err) {
        setStatus('error', '⚠ API falhou');
        showError('Não foi possível carregar o player do YouTube');
      });
    } else {
      showError('audio-player.js não carregou');
    }

    attachListeners();
  }

  // Expõe a API do painel
  window.fralibAudioPanel = {
    init: init
  };

  // Auto-inicializa quando DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
