/* site-editor/history.js — History stack, undo/redo */
(function(global){
  'use strict';

  var state = global.state;
  var $ = global.$;
  var setDirty = global.setDirty;

  function getIframeDoc(){ return global.getIframeDoc(); }

  function serializeForSave(){
    var doc = getIframeDoc();
    if(!doc) return '';
    var clone = doc.documentElement.cloneNode(true);
    global.scrubEditorAttrs(clone);
    var style = clone.querySelector('#fralib-editor-style');
    if(style) style.remove();
    return '<!DOCTYPE html>\n' + clone.outerHTML;
  }

  function scrubEditorAttrs(root){
    if(!root || !root.querySelectorAll) return;
    var nodes = [root].concat(Array.prototype.slice.call(root.querySelectorAll('*')));
    nodes.forEach(function(el){
      el.removeAttribute('contenteditable');
      el.removeAttribute('spellcheck');
      el.removeAttribute('data-fralib-editor-id');
      el.removeAttribute('data-fralib-editor-selected');
    });
  }

  function pushHistory(force){
    var html = serializeForSave();
    if(!html) return;
    if(!force && state.history[state.historyIndex] === html) return;
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(html);
    if(state.history.length > 40) state.history.shift();
    state.historyIndex = state.history.length - 1;
    global.updateHistoryButtons();
  }

  function scheduleSnapshot(){
    clearTimeout(state.snapshotTimer);
    state.snapshotTimer = setTimeout(function(){ global.pushHistory(); }, 600);
  }

  function updateHistoryButtons(){
    if($('editorUndoBtn')) $('editorUndoBtn').disabled = state.historyIndex <= 0;
    if($('editorRedoBtn')) $('editorRedoBtn').disabled = state.historyIndex >= state.history.length - 1;
  }

  function restoreHistory(index){
    if(index < 0 || index >= state.history.length) return;
    state.historyIndex = index;
    state.selectedId = null;
    state.restoring = true;
    $('editorIframe').srcdoc = state.history[index];
    setDirty(true);
    global.updateHistoryButtons();
  }

  function editorUndo(){ restoreHistory(state.historyIndex - 1); }
  function editorRedo(){ restoreHistory(state.historyIndex + 1); }

  /* ── Exports ── */
  global.serializeForSave = serializeForSave;
  global.scrubEditorAttrs = scrubEditorAttrs;
  global.pushHistory = pushHistory;
  global.scheduleSnapshot = scheduleSnapshot;
  global.updateHistoryButtons = updateHistoryButtons;
  global.restoreHistory = restoreHistory;
  global.editorUndo = editorUndo;
  global.editorRedo = editorRedo;

})(window);
