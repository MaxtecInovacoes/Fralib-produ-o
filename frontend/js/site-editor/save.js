/* site-editor/save.js — Save function, public API export */
(function(global){
  'use strict';

  var state = global.state;
  var $ = global.$;
  var status = global.status;
  var setDirty = global.setDirty;

  function salvar(options){
    options = options || {};
    var html = global.serializeForSave();
    if(!html){
      status('Nada para salvar', true);
      if(options.throwOnError) return Promise.reject(new Error('Nada para salvar'));
      return Promise.resolve(null);
    }
    if(!/<body[\s>]/i.test(html) || !/<\/body>/i.test(html)){
      status('HTML invalido: sem body.', true);
      if(options.throwOnError) return Promise.reject(new Error('HTML invalido: sem body'));
      return Promise.resolve(null);
    }
    status('Salvando...', false);
    return window.authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/salvar-html', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({html: html}),
    })
      .then(function(r){
        return r.json().then(function(j){ return {ok: r.ok, status: r.status, body: j}; });
      })
      .then(function(res){
        if(!res.ok){
          var msg = (res.body && res.body.detail) ? res.body.detail : ('HTTP ' + res.status);
          status('Erro: ' + msg, true);
          throw new Error(msg);
        }
        state.htmlOriginal = html;
        setDirty(false);
        global.pushHistory(true);
        status('Site salvo com sucesso.', false);
        return res.body;
      })
      .catch(function(err){
        status('Falha de rede: ' + (err.message || err), true);
        if(options.throwOnError) throw err;
        return null;
      });
  }

  /* ── Public API exports ── */
  global.salvar = salvar;
  global.editorSalvarSite = salvar;

})(window);
