/**
 * Bootstrap - Configura namespace compatibilidade window._ed
 * Carregado antes dos módulos para manter compatibilidade com código legacy.
 * Os módulos modernos (state.js, etc.) exportam diretamente para global (window).
 * Este arquivo faz window._ed referenciar window para compatibilidade.
 */
(function(window) {
  'use strict';

  // window._ed aponta para window para compatibilidade
  // Os módulos modernos exportam para global (window), então window._ed.X funciona
  window._ed = window;

})(window);
