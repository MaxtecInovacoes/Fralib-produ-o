/**
 * FraLib Admin - Audio Panel DOM
 * Constroi o HTML do painel flutuante a partir da lista de estacoes.
 * Nao tem side-effects alem de retornar string HTML.
 */
(function () {
  'use strict';

  var PANEL_ID = 'fralib-audio-panel';

  /**
   * Constroi o HTML do painel.
   * @param {Array<{id: string, nome: string, genero: string}>} stations
   * @returns {string} HTML
   */
  function build(stations) {
    var options = (stations || []).map(function (s) {
      return '<option value="' + s.id + '">' + escapeHtml(s.nome) + ' - ' + escapeHtml(s.genero) + '</option>';
    }).join('');

    return '' +
      '<div id="' + PANEL_ID + '" class="fralib-audio-panel" data-collapsed="false">' +
        '<button class="fralib-audio-toggle" id="fralib-audio-toggle" aria-label="Minimizar player" title="Minimizar">' +
          '<span class="fralib-audio-toggle-icon">▼</span>' +
        '</button>' +
        '<div class="fralib-audio-header">' +
          '<span class="fralib-audio-icon">🎵</span>' +
          '<span class="fralib-audio-title">Rádio de Música</span>' +
          '<span class="fralib-audio-status" id="fralib-audio-status" data-state="empty">Vazio</span>' +
        '</div>' +
        '<div class="fralib-audio-body">' +
          '<div class="fralib-audio-controls">' +
            '<button class="fralib-audio-btn" id="fralib-audio-play" aria-label="Tocar/Pausar">▶</button>' +
            '<input type="range" class="fralib-audio-volume" id="fralib-audio-volume" min="0" max="100" value="50" aria-label="Volume">' +
            '<span class="fralib-audio-volume-label" id="fralib-audio-volume-label">50%</span>' +
          '</div>' +
          '<div class="fralib-audio-station-row">' +
            '<label class="fralib-audio-label" for="fralib-audio-station">Estação:</label>' +
            '<select class="fralib-audio-station" id="fralib-audio-station" aria-label="Escolher estação">' +
              '<option value="">- Selecione uma estação -</option>' +
              options +
            '</select>' +
          '</div>' +
          '<div class="fralib-audio-error" id="fralib-audio-error" role="alert"></div>' +
        '</div>' +
      '</div>';
  }

  /** Helper anti-XSS */
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  window.fralibAudioPanelDom = {
    build: build,
    PANEL_ID: PANEL_ID
  };
})();
