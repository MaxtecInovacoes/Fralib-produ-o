/**
 * FraLib Admin - Audio Player Storage
 * Wrapper de localStorage para persistir estado entre sessoes.
 *
 * Chaves:
 *   'fralib_admin_audio'  -> { stationSlug, volume, isPlaying }
 *   'fralib_audio_station' -> string (slug da estacao - mantido por compat com versao YouTube)
 *   'fralib_audio_panel_collapsed' -> 'true' | 'false'
 */
(function () {
  'use strict';

  var STATE_KEY = 'fralib_admin_audio';
  var STATION_KEY = 'fralib_audio_station';
  var COLLAPSED_KEY = 'fralib_audio_panel_collapsed';

  /** @returns {boolean} true se localStorage esta disponivel */
  function isAvailable() {
    try {
      var k = '__fralib_test__';
      window.localStorage.setItem(k, '1');
      window.localStorage.removeItem(k);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Salva o estado do player (estacao, volume, tocando).
   * @param {{stationSlug: string, volume: number, isPlaying: boolean}} state
   */
  function saveState(state) {
    if (!isAvailable()) return;
    try {
      window.localStorage.setItem(STATE_KEY, JSON.stringify({
        stationSlug: state.stationSlug || '',
        volume: typeof state.volume === 'number' ? state.volume : 50,
        isPlaying: !!state.isPlaying
      }));
      if (state.stationSlug) {
        window.localStorage.setItem(STATION_KEY, state.stationSlug);
      }
    } catch (e) { /* silent - localStorage cheio ou bloqueado */ }
  }

  /**
   * Carrega o estado salvo do player.
   * @returns {{stationSlug: string, volume: number, isPlaying: boolean}|null}
   */
  function loadState() {
    if (!isAvailable()) return null;
    try {
      var raw = window.localStorage.getItem(STATE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') return null;
      return {
        stationSlug: parsed.stationSlug || '',
        volume: typeof parsed.volume === 'number' ? parsed.volume : 50,
        isPlaying: !!parsed.isPlaying
      };
    } catch (e) {
      return null;
    }
  }

  /**
   * Salva estado de colapso do painel.
   * @param {boolean} collapsed
   */
  function saveCollapsed(collapsed) {
    if (!isAvailable()) return;
    try {
      window.localStorage.setItem(COLLAPSED_KEY, collapsed ? 'true' : 'false');
    } catch (e) { /* silent */ }
  }

  /**
   * Carrega estado de colapso do painel.
   * @returns {boolean}
   */
  function loadCollapsed() {
    if (!isAvailable()) return false;
    try {
      return window.localStorage.getItem(COLLAPSED_KEY) === 'true';
    } catch (e) {
      return false;
    }
  }

  // Expoe no namespace global do modulo
  window.fralibAudioStorage = {
    saveState: saveState,
    loadState: loadState,
    saveCollapsed: saveCollapsed,
    loadCollapsed: loadCollapsed,
    STATION_KEY: STATION_KEY
  };
})();
