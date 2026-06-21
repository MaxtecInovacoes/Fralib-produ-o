/**
 * FraLib Admin - Audio Panel Styles
 * CSS do painel flutuante. Injetado via <style> no <head>.
 * Exporta funcao inject() que eh idempotente.
 */
(function () {
  'use strict';

  var STYLE_ID = 'fralib-audio-styles';

  var CSS = '' +
    // Container principal
    '.fralib-audio-panel{' +
      'position:fixed;bottom:16px;right:16px;z-index:9999;' +
      'background:linear-gradient(135deg,rgba(15,23,42,0.95),rgba(30,41,59,0.95));' +
      'backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);' +
      'border:1px solid rgba(148,163,184,0.2);border-radius:12px;' +
      'box-shadow:0 10px 40px rgba(0,0,0,0.4);' +
      'color:#f1f5f9;font-family:"DM Sans",system-ui,sans-serif;' +
      'min-width:320px;max-width:380px;overflow:hidden;' +
      'transition:all 0.3s ease;' +
    '}' +
    // Header
    '.fralib-audio-header{' +
      'display:flex;align-items:center;gap:8px;padding:10px 14px;' +
      'background:rgba(15,23,42,0.6);border-bottom:1px solid rgba(148,163,184,0.1);' +
      'font-size:13px;font-weight:500;' +
    '}' +
    '.fralib-audio-icon{font-size:16px;}' +
    '.fralib-audio-title{flex:1;}' +
    // Status badge
    '.fralib-audio-status{' +
      'font-size:11px;padding:2px 8px;border-radius:10px;' +
      'background:rgba(100,116,139,0.3);color:#cbd5e1;' +
    '}' +
    '.fralib-audio-status[data-state="playing"]{background:rgba(34,197,94,0.25);color:#86efac;}' +
    '.fralib-audio-status[data-state="loaded"]{background:rgba(59,130,246,0.25);color:#93c5fd;}' +
    '.fralib-audio-status[data-state="error"]{background:rgba(239,68,68,0.25);color:#fca5a5;}' +
    // Body
    '.fralib-audio-body{padding:12px 14px;}' +
    // Controls (play + volume)
    '.fralib-audio-controls{display:flex;align-items:center;gap:10px;margin-bottom:10px;}' +
    '.fralib-audio-btn{' +
      'width:36px;height:36px;border:none;border-radius:50%;cursor:pointer;' +
      'background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;' +
      'font-size:14px;display:flex;align-items:center;justify-content:center;' +
      'transition:transform 0.15s,box-shadow 0.15s;flex-shrink:0;' +
    '}' +
    '.fralib-audio-btn:hover{transform:scale(1.08);box-shadow:0 4px 12px rgba(59,130,246,0.4);}' +
    '.fralib-audio-btn:active{transform:scale(0.96);}' +
    '.fralib-audio-btn:disabled{opacity:0.5;cursor:not-allowed;transform:none;}' +
    // Volume slider
    '.fralib-audio-volume{' +
      'flex:1;height:4px;-webkit-appearance:none;appearance:none;' +
      'background:rgba(148,163,184,0.2);border-radius:2px;outline:none;cursor:pointer;' +
    '}' +
    '.fralib-audio-volume::-webkit-slider-thumb{' +
      '-webkit-appearance:none;appearance:none;width:14px;height:14px;' +
      'border-radius:50%;background:#3b82f6;cursor:pointer;' +
      'box-shadow:0 0 0 3px rgba(59,130,246,0.2);' +
    '}' +
    '.fralib-audio-volume::-moz-range-thumb{' +
      'width:14px;height:14px;border-radius:50%;background:#3b82f6;cursor:pointer;' +
      'border:none;box-shadow:0 0 0 3px rgba(59,130,246,0.2);' +
    '}' +
    '.fralib-audio-volume-label{font-size:11px;color:#94a3b8;min-width:32px;text-align:right;}' +
    // Estacao (dropdown)
    '.fralib-audio-station-row{display:flex;flex-direction:column;gap:4px;margin-bottom:6px;}' +
    '.fralib-audio-label{font-size:11px;color:#94a3b8;font-weight:500;}' +
    '.fralib-audio-station{' +
      'padding:8px 10px;border:1px solid rgba(148,163,184,0.2);border-radius:6px;' +
      'background:rgba(15,23,42,0.6);color:#f1f5f9;font-size:13px;outline:none;' +
      'cursor:pointer;transition:border-color 0.15s;' +
    '}' +
    '.fralib-audio-station:focus{border-color:#3b82f6;}' +
    '.fralib-audio-station option{background:#1e293b;color:#f1f5f9;}' +
    '.fralib-audio-station:disabled{opacity:0.6;cursor:wait;}' +
    // Erro
    '.fralib-audio-error{' +
      'font-size:11px;color:#fca5a5;min-height:14px;margin-top:6px;' +
    '}' +
    // Toggle minimizar
    '.fralib-audio-toggle{' +
      'position:absolute;top:6px;right:6px;background:transparent;border:none;' +
      'color:#94a3b8;cursor:pointer;font-size:10px;padding:4px 6px;border-radius:4px;' +
      'transition:background 0.15s;' +
    '}' +
    '.fralib-audio-toggle:hover{background:rgba(148,163,184,0.15);color:#f1f5f9;}' +
    // Estado colapsado
    '.fralib-audio-panel[data-collapsed="true"] .fralib-audio-body{display:none;}' +
    '.fralib-audio-panel[data-collapsed="true"]{min-width:auto;}' +
    '.fralib-audio-panel[data-collapsed="true"] .fralib-audio-toggle-icon{' +
      'transform:rotate(-90deg);' +
    '}' +
    // Mobile
    '@media (max-width:640px){' +
      '.fralib-audio-panel{left:16px;right:16px;min-width:auto;max-width:none;}' +
    '}';

  /**
   * Injeta o CSS no <head> se ainda nao existir.
   * Idempotente.
   */
  function inject() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  window.fralibAudioPanelStyles = { inject: inject };
})();
