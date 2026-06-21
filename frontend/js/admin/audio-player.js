/**
 * FraLib Admin - Audio Player (orquestrador)
 * Une os modulos: events + storage + player-core + stations.
 * Expoe window.fralibAudio com API unificada.
 *
 * Dependencias (carregadas ANTES deste script, em ordem):
 *   - audio-player/events.js
 *   - audio-player/storage.js
 *   - audio-player/player-core.js
 *   - audio-player/stations.js
 */
(function () {
  'use strict';

  function E() { return window.fralibAudioEvents; }
  function S() { return window.fralibAudioStorage; }
  function C() { return window.fralibAudioCore; }
  function T() { return window.fralibAudioStations; }

  // Estado atual (cache em memoria)
  var state = {
    stationSlug: '',
    stationName: '',
    volume: 50,
    isPlaying: false,
    loading: false
  };

  /**
   * Inicializa o player: restaura estado, configura volume inicial,
   * registra listeners de eventos do player-core.
   * @returns {Promise<void>}
   */
  function init() {
    var saved = S().loadState();
    if (saved) {
      state.stationSlug = saved.stationSlug;
      state.volume = saved.volume;
      C().setVolume(saved.volume);
    } else {
      C().setVolume(C().DEFAULT_VOLUME);
    }
    // Bridge: player-core -> estado
    E().on('playing', function () {
      state.isPlaying = true;
      persist();
    });
    E().on('paused', function () {
      state.isPlaying = false;
      persist();
    });
    E().on('volume', function (v) {
      state.volume = v;
      persist();
    });
    return Promise.resolve();
  }

  /** Persiste estado atual no localStorage */
  function persist() {
    S().saveState({
      stationSlug: state.stationSlug,
      volume: state.volume,
      isPlaying: state.isPlaying
    });
  }

  /**
   * Toca uma estacao (resolvendo a URL via Radio-Browser).
   * @param {string} stationId ex: 'kboing'
   * @returns {Promise<boolean>} true se comecou a tocar
   */
  function playStation(stationId) {
    if (state.loading) return Promise.resolve(false);
    state.loading = true;
    E().emit('station', stationId);
    return T().resolveStreamUrl(stationId).then(function (resolved) {
      state.loading = false;
      if (!resolved) {
        E().emit('error', 'Estacao nao encontrada');
        return false;
      }
      state.stationSlug = stationId;
      state.stationName = resolved.name;
      C().play(resolved.url);
      persist();
      return true;
    });
  }

  /** Pausa a reproducao atual. */
  function pause() { C().pause(); }

  /** Retoma a reproducao pausada. */
  function resume() { C().resume(); }

  /**
   * Define o volume (0-100).
   * @param {number} value
   */
  function setVolume(value) { C().setVolume(value); }

  /** @returns {number} volume 0-100 */
  function getVolume() { return C().getVolume(); }

  /**
   * Retorna o estado atual (estacao, volume, tocando).
   * @returns {object}
   */
  function getState() {
    var core = C().getState();
    return {
      stationSlug: state.stationSlug,
      stationName: state.stationName,
      volume: state.volume,
      isPlaying: state.isPlaying,
      loading: state.loading,
      url: core.url
    };
  }

  /** @returns {Array} lista de estacoes disponiveis */
  function getStations() { return T().getAll(); }

  /**
   * Para tudo e limpa o estado.
   */
  function clear() {
    C().clear();
    state.stationSlug = '';
    state.stationName = '';
    state.isPlaying = false;
    persist();
  }

  // API publica
  window.fralibAudio = {
    init: init,
    playStation: playStation,
    pause: pause,
    resume: resume,
    setVolume: setVolume,
    getVolume: getVolume,
    getState: getState,
    getStations: getStations,
    clear: clear
  };
})();
