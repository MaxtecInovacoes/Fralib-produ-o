/* site-editor/state.js — Global state, selectors, DOM helpers, modal lifecycle */
(function(global){
  'use strict';

  var state = window._ed.state;
  var $ = window._ed.$;
  var escapeText = window._ed.escapeText;
  var status = window._ed.status;
  var setDirty = window._ed.setDirty;

  /* ── State already initialised by this module (shared via window._ed) ── */

  /* ── Public API: open / close ── */

  function abrir(leadId){
    if(!leadId){ alert('Lead invalido'); return; }
    state.leadId = leadId;
    state.selectedId = null;
    state.nextId = 1;
    state.history = [];
    state.historyIndex = -1;
    setDirty(false);
    $('editorSiteModal').classList.add('open');
    global.editorSetDevice(state.device || 'desktop');
    $('editorSiteTitle').textContent = 'Carregando site...';
    $('editorIframe').srcdoc = '<p style="font-family:sans-serif;padding:32px;color:#666">Carregando...</p>';
    global.renderInspector(null);

    window.authFetch('/api/sites/' + encodeURIComponent(leadId) + '/html')
      .then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data){
        state.htmlOriginal = data.html || '';
        state.slug = data.slug || '';
        $('editorSiteTitle').textContent = 'Editando: ' + (data.slug || state.leadId);
        $('editorIframe').srcdoc = state.htmlOriginal;
        global.preencherCamposPorInspecao();
      })
      .catch(function(err){
        $('editorSiteTitle').textContent = 'Erro ao carregar';
        $('editorIframe').srcdoc = '<p style="font-family:sans-serif;padding:32px;color:#dc2626">Falha: ' + escapeText(err.message || err) + '</p>';
      });
  }

  function fechar(){
    if(state.dirty && !confirm('Voce fez alteracoes nao salvas. Fechar mesmo assim?')) return;
    $('editorSiteModal').classList.remove('open');
    $('editorIframe').srcdoc = '';
    clearTimeout(state.snapshotTimer);
    state.selectedId = null;
    setDirty(false);
  }

  function getIframeDoc(){
    var ifr = $('editorIframe');
    try{ return ifr.contentDocument || ifr.contentWindow.document; }
    catch(e){ return null; }
  }

  document.addEventListener('DOMContentLoaded', function(){
    var ifr = $('editorIframe');
    if(!ifr) return;
    ifr.addEventListener('load', function(){
      var doc = getIframeDoc();
      if(!doc || !doc.body) return;
      try { global.ligarEdicao(doc); } catch(e){ console.error('[Editor] ligar', e); }
    });
  });

  function ligarEdicao(doc){
    injectEditorStyles(doc);
    assignEditorIds(doc);
    global.bindEditableText(doc);
    global.bindCanvasEvents(doc);
    global.renderSections();
    global.renderImages();
    if(state.restoring){
      state.restoring = false;
      global.updateHistoryButtons();
    } else {
      global.pushHistory(true);
    }
    status('Selecione qualquer texto, botão, imagem ou seção.', false);
  }

  function injectEditorStyles(doc){
    var old = doc.getElementById('fralib-editor-style');
    if(old) old.remove();
    var style = doc.createElement('style');
    style.id = 'fralib-editor-style';
    style.textContent = [
      '[data-fralib-editor-id]{outline-offset:2px;}',
      '[data-fralib-editor-id]:hover{outline:2px solid rgba(14,165,233,.55)!important;cursor:pointer;}',
      '[data-fralib-editor-selected="true"]{outline:3px solid #0ea5e9!important;box-shadow:0 0 0 4px rgba(14,165,233,.18)!important;}',
      '[contenteditable="true"]:focus{outline:3px solid #10b981!important;outline-offset:2px;}'
    ].join('\n');
    doc.head.appendChild(style);
  }

  function assignEditorIds(doc){
    var nodes = doc.querySelectorAll(window._ed.SELECTABLE);
    nodes.forEach(function(el){
      if(el.closest('script,style,noscript,template')) return;
      if(!el.dataset.fralibEditorId){
        el.dataset.fralibEditorId = 'ed-' + (state.nextId++);
      }
    });
  }

  /* ── Exports ── */
  global.abrirEditorWYSIWYG = abrir;
  global.editorFechar = fechar;
  global.getIframeDoc = getIframeDoc;
  global.ligarEdicao = ligarEdicao;
  global.injectEditorStyles = injectEditorStyles;
  global.assignEditorIds = assignEditorIds;

})(window);
