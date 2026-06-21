/**
 * FraLib Admin - Audio Panel (orquestrador UI)
 * Combina panel-styles + panel-dom + panel-events + audio-player.
 * Auto-inicializa no DOMContentLoaded.
 *
 * Dependencias (carregadas ANTES deste script, em ordem):
 *   - audio-player/events.js
 *   - audio-player/storage.js
 *   - audio-player/player-core.js
 *   - audio-player/stations.js
 *   - audio-player.js
 *   - audio-panel/panel-styles.js
 *   - audio-panel/panel-dom.js
 *   - audio-panel/panel-events.js
 */
(function () {
  'use strict';

  function A() { return window.fralibAudio; }
  function Styles() { return window.fralibAudioPanelStyles; }
  function Dom() { return window.fralibAudioPanelDom; }
  function Evt() { return window.fralibAudioPanelEvents; }
  function Store() { return window.fralibAudioStorage; }

  /**
   * Inicializa o painel: injeta CSS, HTML, anexa listeners e sincroniza com estado.
   * @returns {Promise<void>}
   */
  function init() {
    if (!A()) {
      console.warn('[fralib-audio] audio-player.js nao carregou');
      return Promise.resolve();
    }
    Styles().inject();
    var stations = A().getStations();
    var container = document.createElement('div');
    container.innerHTML = Dom().build(stations);
    document.body.appendChild(container.firstChild);
    // Estado minimizado
    var panel = document.getElementById(Dom().PANEL_ID);
    if (panel && Store().loadCollapsed()) {
      panel.setAttribute('data-collapsed', 'true');
    }
    Evt().attach();
    return A().init().then(function () { Evt().syncFromState(); });
  }

  window.fralibAudioPanel = { init: init };

  // Auto-inicializa
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
