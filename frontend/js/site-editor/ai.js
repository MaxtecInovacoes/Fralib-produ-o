/* site-editor/ai.js — AI presets and execution */
(function(global){
  'use strict';

  var state = global.state;
  var $ = global.$;
  var status = global.status;
  var setDirty = global.setDirty;

  function getIframeDoc(){
    var ifr = $('editorIframe');
    try{ return ifr.contentDocument || ifr.contentWindow.document; }
    catch(e){ return null; }
  }

  function serializeSelectedForPrompt(el){
    if(!el) return '';
    var clone = el.cloneNode(true);
    global.scrubEditorAttrs(clone);
    var html = clone.outerHTML || '';
    return html.length > 3600 ? html.slice(0, 3600) + '\n...' : html;
  }

  function editorUseAiPreset(kind){
    var input = $('editorAiPrompt');
    if(!input) return;
    var preset = '';
    if(kind === 'copy'){
      preset = 'Reescreva a copy para ficar mais clara, persuasiva e local, sem inventar fatos novos.';
    } else if(kind === 'visual'){
      preset = 'Deixe o visual mais premium usando melhor hierarquia, espaçamento e destaque nos CTAs, preservando o conteúdo factual.';
    } else if(kind === 'cta'){
      preset = 'Fortaleça a chamada para WhatsApp com texto direto, benefício claro e senso de próximo passo.';
    }
    input.value = input.value ? input.value + '\n' + preset : preset;
    input.focus();
  }

  function reloadSiteFromServer(message){
    return window.authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/html')
      .then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data){
        state.htmlOriginal = data.html || '';
        state.slug = data.slug || state.slug;
        state.selectedId = null;
        state.history = [];
        state.historyIndex = -1;
        $('editorIframe').srcdoc = state.htmlOriginal;
        setDirty(false);
        global.renderInspector(null);
        global.renderSelectedPath(null);
        setTimeout(function(){ status(message || 'Site recarregado.', false); }, 350);
      });
  }

  function editorRunAiPrompt(){
    var promptInput = $('editorAiPrompt');
    var prompt = promptInput ? promptInput.value.trim() : '';
    var scope = $('editorAiScope') ? $('editorAiScope').value : 'selected';
    var btn = $('editorAiRunBtn');
    var selected = global.getSelected();
    if(!prompt){ status('Escreva o pedido para a IA.', true); return; }
    if(scope === 'selected' && !selected){
      status('Selecione um elemento ou mude o escopo para site inteiro.', true);
      return;
    }
    if(scope === 'selected'){
      prompt = [
        'Edite somente o elemento selecionado quando encontrar trecho equivalente no HTML.',
        'Preserve o restante do site sem mudancas desnecessarias.',
        'Elemento selecionado: ' + global.elementLabel(selected),
        'HTML do elemento selecionado:',
        serializeSelectedForPrompt(selected),
        'Pedido: ' + prompt,
      ].join('\n');
    }
    if(btn) btn.disabled = true;
    status(state.dirty ? 'Salvando antes de aplicar IA...' : 'Aplicando IA...', false);
    var beforeAi = state.dirty ? global.salvar({throwOnError: true}) : Promise.resolve();
    return beforeAi.then(function(){
      return window.authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/editar-ia', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt: prompt}),
      });
    }).then(function(r){
      return r.json().then(function(j){ return {ok: r.ok, status: r.status, body: j}; });
    }).then(function(res){
      if(!res.ok){
        var msg = (res.body && res.body.detail) ? res.body.detail : ('HTTP ' + res.status);
        throw new Error(msg);
      }
      return reloadSiteFromServer('Alteração por IA aplicada.');
    }).catch(function(err){
      status('IA falhou: ' + (err.message || err), true);
    }).finally(function(){
      if(btn) btn.disabled = false;
    });
  }

  /* ── Exports ── */
  global.serializeSelectedForPrompt = serializeSelectedForPrompt;
  global.editorUseAiPreset = editorUseAiPreset;
  global.reloadSiteFromServer = reloadSiteFromServer;
  global.editorRunAiPrompt = editorRunAiPrompt;

})(window);
