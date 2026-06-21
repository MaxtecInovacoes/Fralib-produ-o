/**
 * FraLib Admin - Audio Panel Events
 * Anexa event listeners no DOM do painel e faz bridge com window.fralibAudio.
 *
 * Dependencias:
 *   - window.fralibAudio        (orquestrador do player)
 *   - window.fralibAudioEvents  (pub/sub)
 *   - window.fralibAudioStorage (localStorage)
 */
(function () {
  'use strict';

  function A() { return window.fralibAudio; }
  function E() { return window.fralibAudioEvents; }
  function S() { return window.fralibAudioStorage; }

  /** Helper: $ = querySelector */
  function $(sel) { return document.querySelector(sel); }

  /** Atualiza o texto e estado visual do badge de status */
  function setStatus(state, text) {
    var el = $('#fralib-audio-status');
    if (!el) return;
    el.setAttribute('data-state', state);
    el.textContent = text;
  }

  /** Atualiza o botao play/pause */
  function setPlayButton(isPlaying) {
    var btn = $('#fralib-audio-play');
    if (!btn) return;
    btn.textContent = isPlaying ? '⏸' : '▶';
    btn.setAttribute('aria-label', isPlaying ? 'Pausar' : 'Tocar');
    btn.disabled = false;
  }

  /** Mostra mensagem de erro */
  function showError(msg) {
    var el = $('#fralib-audio-error');
    if (el) el.textContent = msg || '';
  }

  /** Handler do botao play/pause principal */
  function onPlayClick() {
    if (!A()) return;
    var st = A().getState();
    if (st.isPlaying) {
      A().pause();
    } else if (st.stationSlug) {
      A().resume();
    } else {
      showError('Escolha uma estacao no dropdown acima');
    }
  }

  /** Handler do slider de volume */
  function onVolumeInput(slider) {
    var v = parseInt(slider.value, 10);
    var label = $('#fralib-audio-volume-label');
    if (label) label.textContent = v + '%';
    if (A()) A().setVolume(v);
  }

  /** Handler do dropdown de estacao */
  function onStationChange(select) {
    var stationId = select.value;
    if (!stationId) return;
    select.disabled = true;
    showError('Carregando ' + stationId + '...');
    A().playStation(stationId).then(function (ok) {
      select.disabled = false;
      if (ok) {
        showError('');
      } else {
        showError('Estacao nao encontrada. Tente outra.');
      }
    });
  }

  /** Handler do botao minimizar */
  function onToggleClick(panel) {
    var isCollapsed = panel.getAttribute('data-collapsed') === 'true';
    panel.setAttribute('data-collapsed', isCollapsed ? 'false' : 'true');
    S().saveCollapsed(!isCollapsed);
  }

  /** Bridge: eventos do player -> UI */
  function bindPlayerEvents() {
    E().on('playing', function () {
      setStatus('playing', '▶ Tocando');
      setPlayButton(true);
      showError('');
    });
    E().on('paused', function () {
      setStatus('paused', '⏸ Pausado');
      setPlayButton(false);
    });
    E().on('loaded', function () {
      setStatus('loaded', '🎵 Pronto');
    });
    E().on('error', function (code) {
      var msg = 'Erro ao tocar';
      if (code === 1) msg = 'Reproducao abortada';
      else if (code === 2) msg = 'Erro de rede';
      else if (code === 3) msg = 'Erro de decodificacao';
      else if (code === 4) msg = 'Estacao indisponivel';
      else if (typeof code === 'string') msg = code;
      setStatus('error', '⚠ Erro');
      showError(msg);
      setPlayButton(false);
    });
    E().on('volume', function (v) {
      var slider = $('#fralib-audio-volume');
      var label = $('#fralib-audio-volume-label');
      if (slider) slider.value = v;
      if (label) label.textContent = v + '%';
    });
  }

  /**
   * Anexa todos os event listeners no painel.
   * Chamar apos o DOM do painel ter sido injetado.
   */
  function attach() {
    var playBtn = $('#fralib-audio-play');
    if (playBtn) playBtn.addEventListener('click', onPlayClick);

    var volumeSlider = $('#fralib-audio-volume');
    if (volumeSlider) volumeSlider.addEventListener('input', function () { onVolumeInput(volumeSlider); });

    var stationSelect = $('#fralib-audio-station');
    if (stationSelect) stationSelect.addEventListener('change', function () { onStationChange(stationSelect); });

    var panel = document.getElementById(window.fralibAudioPanelDom.PANEL_ID);
    var toggleBtn = $('#fralib-audio-toggle');
    if (toggleBtn && panel) toggleBtn.addEventListener('click', function () { onToggleClick(panel); });

    // Bridge player -> UI
    bindPlayerEvents();
  }

  /**
   * Sincroniza o DOM do painel com o estado atual do player.
   * Chamado na inicializacao.
   */
  function syncFromState() {
    if (!A()) return;
    var st = A().getState();
    var stationSelect = $('#fralib-audio-station');
    if (stationSelect && st.stationSlug) stationSelect.value = st.stationSlug;
    var volumeSlider = $('#fralib-audio-volume');
    if (volumeSlider) volumeSlider.value = st.volume;
    var volumeLabel = $('#fralib-audio-volume-label');
    if (volumeLabel) volumeLabel.textContent = st.volume + '%';
    if (st.isPlaying) {
      setStatus('playing', '▶ Tocando');
      setPlayButton(true);
    } else if (st.stationSlug) {
      setStatus('loaded', '🎵 Pronto');
      setPlayButton(false);
    } else {
      setStatus('empty', 'Vazio');
      setPlayButton(false);
    }
  }

  window.fralibAudioPanelEvents = {
    attach: attach,
    syncFromState: syncFromState
  };
})();
