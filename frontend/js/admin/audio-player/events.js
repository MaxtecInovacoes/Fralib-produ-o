/**
 * FraLib Admin - Audio Player Events (pub/sub)
 * Barramento simples de eventos para desacoplar modulos.
 *
 * Eventos emitidos:
 *   'playing'   - audio comecou a tocar
 *   'paused'    - audio pausou
 *   'loaded'    - stream carregado, pronto pra play
 *   'error'     - erro de carregamento/reproducao (data = string ou codigo)
 *   'volume'    - volume mudou (data = 0-100)
 *   'station'   - estacao mudou (data = slug)
 */
(function () {
  'use strict';

  var listeners = {};

  /**
   * Registra um listener para um evento.
   * @param {string} event nome do evento
   * @param {function} callback funcao chamada com (data)
   */
  function on(event, callback) {
    if (typeof callback !== 'function') return;
    if (!listeners[event]) listeners[event] = [];
    listeners[event].push(callback);
  }

  /**
   * Dispara um evento para todos os listeners registrados.
   * @param {string} event nome do evento
   * @param {*} [data] dado opcional passado ao callback
   */
  function emit(event, data) {
    var list = listeners[event];
    if (!list) return;
    list.slice().forEach(function (cb) {
      try { cb(data); } catch (e) { /* silent - nunca quebra o player */ }
    });
  }

  /**
   * Remove um listener especifico (ou todos se callback omitido).
   * @param {string} event
   * @param {function} [callback]
   */
  function off(event, callback) {
    if (!listeners[event]) return;
    if (!callback) { delete listeners[event]; return; }
    listeners[event] = listeners[event].filter(function (cb) {
      return cb !== callback;
    });
  }

  // Expõe no namespace global do modulo (consumido pelos outros modulos)
  window.fralibAudioEvents = { on: on, emit: emit, off: off };
})();
