/* site-editor/_shared.js — Utilitários compartilhados pelos módulos do site-editor.
 *
 * Canônico para T5 do plano DRY (codex/dry-refactor).
 * Substitui as 6 cópias idênticas de getIframeDoc() que existiam em:
 *   - state.js, sync.js, history.js, editing.js, ai.js, commands.js
 *
 * Uso: este módulo expõe um IIFE que recebe `global` e registra
 * `getIframeDoc` como propriedade. Os demais módulos do site-editor
 * passam a ler `global.getIframeDoc` em vez de redefinir localmente.
 */
(function(global){
  'use strict';

  /**
   * Retorna o Document do iframe de edição ou null se inacessível.
   * @param {string} [iframeId='editorIframe'] - id do iframe
   * @returns {Document|null}
   */
  function getIframeDoc(iframeId){
    var ifr = $(iframeId || 'editorIframe');
    if(!ifr) return null;
    try{ return ifr.contentDocument || ifr.contentWindow.document; }
    catch(e){ return null; }
  }

  global.getIframeDoc = getIframeDoc;
})(typeof window !== 'undefined' ? window : this);