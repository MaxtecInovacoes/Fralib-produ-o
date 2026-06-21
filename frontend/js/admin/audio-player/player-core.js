/**
 * FraLib Admin - Audio Player Core
 * Wrapper do elemento HTML5 <audio>. Encapsula o <audio>, play/pause,
 * volume e emite eventos via window.fralibAudioEvents.
 *
 * NAO conhece UI, NAO conhece lista de estacoes - so toca um stream URL.
 *
 * Eventos emitidos:
 *   'loaded'   - audio carregou metadados
 *   'playing'  - audio comecou a tocar
 *   'paused'   - audio pausou
 *   'error'    - erro (data = MediaError code ou mensagem)
 *   'volume'   - volume mudou (data = 0-100)
 */
(function () {
  'use strict';

  var DEFAULT_VOLUME = 50; // 50% - equilibrado

  /** Elemento <audio> interno */
  var audio = null;
  var currentUrl = '';
  var isPlaying = false;
  var volume = DEFAULT_VOLUME;

  /** Pega o modulo de eventos (carregado antes deste script) */
  function E() { return window.fralibAudioEvents; }

  /**
   * Cria e injeta o elemento <audio> invisivel no DOM.
   * Idempotente: nao recria se ja existir.
   */
  function ensureAudio() {
    if (audio) return audio;
    audio = document.createElement('audio');
    audio.id = 'fralib-audio-element';
    audio.preload = 'none'; // nao baixa nada ate play()
    audio.style.cssText = 'position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0;pointer-events:none;';
    // Listeners -> eventos
    audio.addEventListener('playing', function () {
      isPlaying = true;
      E().emit('playing');
    });
    audio.addEventListener('pause', function () {
      isPlaying = false;
      E().emit('paused');
    });
    audio.addEventListener('loadedmetadata', function () {
      E().emit('loaded');
    });
    audio.addEventListener('error', function () {
      isPlaying = false;
      var code = audio.error ? audio.error.code : 'unknown';
      E().emit('error', code);
    });
    // Anexa ao body (so depois do body existir)
    function append() { document.body.appendChild(audio); }
    if (document.body) append();
    else document.addEventListener('DOMContentLoaded', append);
    return audio;
  }

  /**
   * Carrega e toca um stream URL.
   * @param {string} url URL do stream MP3/AAC
   * @returns {boolean} true se comecou a carregar
   */
  function play(url) {
    if (!url || typeof url !== 'string') return false;
    var el = ensureAudio();
    currentUrl = url.trim();
    el.src = currentUrl;
    el.volume = volume / 100;
    // play() retorna Promise - alguns browsers bloqueiam ate user gesture
    var p = el.play();
    if (p && typeof p.catch === 'function') {
      p.catch(function () {
        // Autoplay bloqueado - emite paused mas URL esta carregada
        E().emit('paused');
      });
    }
    return true;
  }

  /** Pausa a reproducao atual. */
  function pause() {
    if (audio && !audio.paused) audio.pause();
  }

  /** Retoma a reproducao pausada. */
  function resume() {
    if (audio && audio.paused && currentUrl) {
      var p = audio.play();
      if (p && typeof p.catch === 'function') p.catch(function () {});
    }
  }

  /**
   * Define o volume (0-100).
   * @param {number} value
   */
  function setVolume(value) {
    var v = Math.max(0, Math.min(100, Math.round(value)));
    volume = v;
    if (audio) audio.volume = v / 100;
    E().emit('volume', v);
  }

  /** @returns {number} volume 0-100 */
  function getVolume() { return volume; }

  /**
   * Retorna o estado atual.
   * @returns {{url: string, isPlaying: boolean, volume: number, ready: boolean}}
   */
  function getState() {
    return {
      url: currentUrl,
      isPlaying: isPlaying,
      volume: volume,
      ready: !!audio
    };
  }

  /**
   * Para tudo e limpa o src.
   */
  function clear() {
    if (audio) {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    }
    currentUrl = '';
    isPlaying = false;
  }

  // Expoe no namespace global do modulo
  window.fralibAudioCore = {
    play: play,
    pause: pause,
    resume: resume,
    setVolume: setVolume,
    getVolume: getVolume,
    getState: getState,
    clear: clear,
    DEFAULT_VOLUME: DEFAULT_VOLUME
  };
})();
