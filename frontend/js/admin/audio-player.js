/**
 * FraLib Admin - Audio Player (YouTube Audio Only)
 * Player invisível que toca áudio do YouTube sem exibir vídeo.
 * Usa YouTube IFrame Player API (oficial Google, sem API key).
 *
 * Estado persistido em localStorage.chave: 'fralib_admin_audio'
 *   { url: string, volume: number (0-50), isPlaying: boolean }
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'fralib_admin_audio';
  var MAX_VOLUME = 50; // limite de volume conforme requisito

  /** Estado interno do player */
  var state = {
    url: '',
    volume: 20, // 20% por padrão (conservador)
    isPlaying: false,
    currentVideoId: null
  };

  /** Referência ao player do YouTube */
  var player = null;
  var apiReady = false;
  var apiReadyCallbacks = [];

  /**
   * Extrai o videoId de uma URL do YouTube.
   * Suporta: watch?v=, youtu.be/, embed/, shorts/, ou ID direto (11 chars).
   * @param {string} url URL do YouTube ou ID do vídeo
   * @returns {string|null} videoId ou null se inválido
   */
  function extractYouTubeId(url) {
    if (!url || typeof url !== 'string') return null;
    var trimmed = url.trim();
    // ID direto (11 caracteres alfanuméricos, _ ou -)
    if (/^[a-zA-Z0-9_-]{11}$/.test(trimmed)) return trimmed;
    // Padrões de URL
    var patterns = [
      /(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.*&v=)([^&\?\/#]+)/,
      /youtu\.be\/([^&\?\/#]+)/,
      /youtube\.com\/embed\/([^&\?\/#]+)/,
      /youtube\.com\/shorts\/([^&\?\/#]+)/
    ];
    for (var i = 0; i < patterns.length; i++) {
      var match = trimmed.match(patterns[i]);
      if (match && match[1]) return match[1];
    }
    return null;
  }

  /**
   * Carrega a YouTube IFrame API dinamicamente.
   * @returns {Promise<void>}
   */
  function loadYouTubeAPI() {
    return new Promise(function (resolve, reject) {
      // Se já estiver carregada
      if (window.YT && window.YT.Player) {
        apiReady = true;
        resolve();
        return;
      }
      // Callback global que a API chama quando fica pronta
      var previousReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function () {
        if (typeof previousReady === 'function') previousReady();
        apiReady = true;
        // Notifica callbacks pendentes
        apiReadyCallbacks.forEach(function (cb) { cb(); });
        apiReadyCallbacks = [];
        resolve();
      };
      // Injeta o script
      var tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      tag.onerror = function () { reject(new Error('Falha ao carregar YouTube API')); };
      var firstScript = document.getElementsByTagName('script')[0];
      if (firstScript && firstScript.parentNode) {
        firstScript.parentNode.insertBefore(tag, firstScript);
      } else {
        document.head.appendChild(tag);
      }
      // Timeout de segurança
      setTimeout(function () {
        if (!apiReady) reject(new Error('Timeout ao carregar YouTube API'));
      }, 10000);
    });
  }

  /**
   * Inicializa o player do YouTube quando a API estiver pronta.
   */
  function initPlayer() {
    if (player) return;
    player = new window.YT.Player('yt-audio-player', {
      height: '1',
      width: '1',
      videoId: state.currentVideoId || '',
      playerVars: {
        'autoplay': 0,
        'controls': 0,
        'disablekb': 1,
        'fs': 0,
        'modestbranding': 1,
        'playsinline': 1,
        'rel': 0
      },
      events: {
        'onReady': function () {
          player.setVolume(state.volume);
          // Se tinha um vídeo salvo, carrega mas não toca (browser policy)
          if (state.url && state.currentVideoId) {
            notifyStatusChange('loaded');
          } else {
            notifyStatusChange('empty');
          }
        },
        'onStateChange': function (event) {
          // 1 = playing, 2 = paused, 0 = ended
          if (event.data === 1) {
            state.isPlaying = true;
            saveState();
            notifyStatusChange('playing');
          } else if (event.data === 2 || event.data === 0) {
            state.isPlaying = false;
            saveState();
            notifyStatusChange('paused');
          }
        },
        'onError': function (event) {
          state.isPlaying = false;
          // 2 = invalid param, 5 = HTML5 error, 100/101/150 = not found/embed restricted
          notifyStatusChange('error', event.data);
        }
      }
    });
  }

  /** Lista de listeners do painel UI */
  var statusListeners = [];

  function notifyStatusChange(status, code) {
    statusListeners.forEach(function (cb) {
      try { cb(status, code); } catch (e) { /* silent */ }
    });
  }

  /**
   * Persiste o estado atual no localStorage.
   */
  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        url: state.url,
        volume: state.volume,
        isPlaying: state.isPlaying
      }));
    } catch (e) {
      // localStorage indisponível (modo privado) - silencioso
    }
  }

  /**
   * Carrega o estado persistido do localStorage.
   */
  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // ─── API PÚBLICA ──────────────────────────────────────────────────────

  /**
   * Inicializa o player (carrega API e restaura estado).
   * @returns {Promise<void>}
   */
  function init() {
    var saved = loadState();
    if (saved) {
      state.url = saved.url || '';
      state.volume = (typeof saved.volume === 'number') ? saved.volume : 20;
      state.currentVideoId = extractYouTubeId(state.url);
    }
    return loadYouTubeAPI().then(function () {
      initPlayer();
    });
  }

  /**
   * Carrega e toca uma URL do YouTube.
   * @param {string} url URL do YouTube ou videoId
   * @returns {boolean} true se a URL é válida
   */
  function play(url) {
    var videoId = extractYouTubeId(url);
    if (!videoId) return false;
    state.url = url.trim();
    state.currentVideoId = videoId;
    if (player && player.loadVideoById) {
      player.loadVideoById(videoId);
      // setVolume precisa ser reaplicado após load
      player.setVolume(state.volume);
      saveState();
      return true;
    }
    return false;
  }

  /**
   * Carrega e toca um videoId direto (sem precisar de URL completa).
   * Usado pela lista curada de estacoes.
   * @param {string} videoId ID do YouTube (11 chars)
   * @param {string} [label] rotulo opcional (ex: "Lofi Girl")
   * @returns {boolean} true se carregou
   */
  function playVideoId(videoId, label) {
    if (!videoId || !/^[a-zA-Z0-9_-]{11}$/.test(videoId)) return false;
    state.url = label ? ('[station] ' + label) : videoId;
    state.currentVideoId = videoId;
    if (player && player.loadVideoById) {
      player.loadVideoById(videoId);
      player.setVolume(state.volume);
      saveState();
      return true;
    }
    return false;
  }

  /**
   * Pausa a reprodução atual.
   */
  function pause() {
    if (player && player.pauseVideo) {
      player.pauseVideo();
    }
  }

  /**
   * Retoma a reprodução pausada.
   */
  function resume() {
    if (player && state.currentVideoId) {
      if (player.getPlayerState && player.getPlayerState() === 2) {
        player.playVideo();
      } else {
        player.playVideo();
      }
    }
  }

  /**
   * Define o volume (0-50).
   * @param {number} value volume entre 0 e 50
   */
  function setVolume(value) {
    var v = Math.max(0, Math.min(MAX_VOLUME, Math.round(value)));
    state.volume = v;
    if (player && player.setVolume) {
      player.setVolume(v);
    }
    saveState();
  }

  /**
   * Retorna o volume atual.
   * @returns {number} volume (0-50)
   */
  function getVolume() {
    return state.volume;
  }

  /**
   * Retorna o estado atual.
   * @returns {object}
   */
  function getState() {
    return {
      url: state.url,
      videoId: state.currentVideoId,
      volume: state.volume,
      isPlaying: state.isPlaying,
      maxVolume: MAX_VOLUME,
      apiReady: apiReady
    };
  }

  /**
   * Registra listener para mudanças de status.
   * @param {function} callback (status, code) => void
   */
  function onStatusChange(callback) {
    if (typeof callback === 'function') {
      statusListeners.push(callback);
    }
  }

  /**
   * Limpa o player (para de tocar e remove vídeo).
   */
  function clear() {
    if (player && player.stopVideo) player.stopVideo();
    state.url = '';
    state.currentVideoId = null;
    state.isPlaying = false;
    saveState();
    notifyStatusChange('cleared');
  }

  // Expõe a API no escopo global
  window.fralibAudio = {
    init: init,
    play: play,
    playVideoId: playVideoId,
    pause: pause,
    resume: resume,
    setVolume: setVolume,
    getVolume: getVolume,
    getState: getState,
    onStatusChange: onStatusChange,
    clear: clear,
    extractYouTubeId: extractYouTubeId
  };

  // Injeta o container invisível do player
  if (document.body) {
    injectPlayerContainer();
  } else {
    document.addEventListener('DOMContentLoaded', injectPlayerContainer);
  }

  function injectPlayerContainer() {
    if (document.getElementById('yt-audio-player')) return;
    var div = document.createElement('div');
    div.id = 'yt-audio-player';
    div.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0;pointer-events:none;';
    document.body.appendChild(div);
  }

})();
