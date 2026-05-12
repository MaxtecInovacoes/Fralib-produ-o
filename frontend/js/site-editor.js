/* PR13 — Editor Visual WYSIWYG (sem LLM)
   Depende de window.authFetch (definido em _scripts.html).
   Abre modal #editorSiteModal, carrega HTML do site no iframe via srcdoc,
   liga contentEditable nos elementos de texto, salva com POST direto. */
(function(global){
  'use strict';

  var state = {
    leadId: null,
    slug: null,
    htmlOriginal: '',
    dirty: false,
  };

  function $(id){ return document.getElementById(id); }

  function status(msg, isErr){
    var el = $('editorStatus');
    if(!el) return;
    el.textContent = msg;
    el.classList.toggle('err', !!isErr);
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(function(){ el.classList.remove('show'); }, 2500);
  }

  function abrir(leadId){
    if(!leadId){ alert('Lead invalido'); return; }
    state.leadId = leadId;
    state.dirty = false;
    $('editorSiteModal').classList.add('open');
    $('editorSiteTitle').textContent = 'Carregando site...';
    $('editorIframe').srcdoc = '<p style="font-family:sans-serif;padding:32px;color:#666">Carregando...</p>';

    authFetch('/api/sites/' + encodeURIComponent(leadId) + '/html')
      .then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data){
        state.htmlOriginal = data.html || '';
        state.slug = data.slug || '';
        $('editorSiteTitle').textContent = 'Editando: ' + (data.slug || state.leadId);
        $('editorIframe').srcdoc = state.htmlOriginal;
        preencherCamposPorInspecao();
      })
      .catch(function(err){
        $('editorSiteTitle').textContent = 'Erro ao carregar';
        $('editorIframe').srcdoc = '<p style="font-family:sans-serif;padding:32px;color:#dc2626">Falha: ' + (err.message || err) + '</p>';
      });
  }

  function fechar(){
    if(state.dirty){
      if(!confirm('Voce fez alteracoes nao salvas. Fechar mesmo assim?')) return;
    }
    $('editorSiteModal').classList.remove('open');
    $('editorIframe').srcdoc = '';
    state.dirty = false;
  }

  function getIframeDoc(){
    var ifr = $('editorIframe');
    try{ return ifr.contentDocument || ifr.contentWindow.document; }
    catch(e){ return null; }
  }

  // Liga edicao quando iframe terminar de carregar
  document.addEventListener('DOMContentLoaded', function(){
    var ifr = $('editorIframe');
    if(!ifr) return;
    ifr.addEventListener('load', function(){
      var doc = getIframeDoc();
      if(!doc || !doc.body) return;
      try { ligarEdicao(doc); } catch(e){ console.error('[Editor] ligar', e); }
    });
  });

  function ligarEdicao(doc){
    var seletores = 'h1,h2,h3,h4,h5,p,li,a,button,span,strong,em,small,blockquote,figcaption,label,td,th';
    var nodes = doc.querySelectorAll(seletores);
    nodes.forEach(function(el){
      // pular dentro de script/style/noscript
      if(el.closest('script,style,noscript,template')) return;
      // pular elementos vazios ou so com filhos
      var soTexto = Array.prototype.every.call(el.childNodes, function(n){
        return n.nodeType === 3 || (n.nodeType === 1 && /^(BR|STRONG|EM|SPAN|A|B|I|U|SMALL)$/i.test(n.tagName));
      });
      if(!soTexto) return;
      el.contentEditable = 'true';
      el.style.outline = '';
      el.addEventListener('focus', function(){ el.style.outline = '2px dashed #0ea5e9'; });
      el.addEventListener('blur', function(){ el.style.outline = ''; });
      el.addEventListener('input', function(){ state.dirty = true; });
    });
    // bloquear navegacao por links
    doc.addEventListener('click', function(e){
      var a = e.target.closest && e.target.closest('a');
      if(a){ e.preventDefault(); }
    }, true);
    status('Clique nos textos para editar', false);
  }

  // Tenta extrair dados atuais do site pra preencher o painel
  function preencherCamposPorInspecao(){
    setTimeout(function(){
      var doc = getIframeDoc();
      if(!doc) return;
      // Nome do negocio
      var h1 = doc.querySelector('h1');
      if(h1) $('edHeadline').value = (h1.textContent || '').trim();
      // tentar pegar nome via schema.org
      var schema = doc.querySelector('script[type="application/ld+json"]');
      if(schema){
        try {
          var obj = JSON.parse(schema.textContent);
          if(obj.name) $('edNome').value = obj.name;
          if(obj.telephone) $('edTelefone').value = obj.telephone;
          if(obj.address){
            var addr = obj.address;
            var parts = [addr.streetAddress, addr.addressLocality, addr.addressRegion].filter(Boolean);
            if(parts.length) $('edEndereco').value = parts.join(' - ');
          }
        } catch(e){ /* schema invalido, ignorar */ }
      }
      // telefone via link tel:
      if(!$('edTelefone').value){
        var telLink = doc.querySelector('a[href^="tel:"]');
        if(telLink) $('edTelefone').value = telLink.getAttribute('href').replace('tel:', '').trim();
      }
    }, 300);
  }

  // Aplica campos do painel no iframe
  function sincronizarCampos(){
    var doc = getIframeDoc();
    if(!doc){ status('Site nao carregado', true); return; }

    var tel = ($('edTelefone').value || '').trim();
    var nome = ($('edNome').value || '').trim();
    var headline = ($('edHeadline').value || '').trim();
    var end = ($('edEndereco').value || '').trim();
    var horSeg = ($('edHorSeg').value || '').trim();
    var horSab = ($('edHorSab').value || '').trim();

    if(tel){
      var telDigits = tel.replace(/\D/g, '');
      var wnum = telDigits.length >= 10 ? (telDigits.startsWith('55') ? telDigits : '55' + telDigits) : telDigits;
      // tel: links
      doc.querySelectorAll('a[href^="tel:"]').forEach(function(a){ a.setAttribute('href', 'tel:' + tel); a.textContent = tel; });
      // wa.me links
      doc.querySelectorAll('a[href*="wa.me/"], a[href*="api.whatsapp.com"]').forEach(function(a){
        var oldHref = a.getAttribute('href') || '';
        a.setAttribute('href', oldHref.replace(/wa\.me\/\d+/, 'wa.me/' + wnum).replace(/phone=\d+/, 'phone=' + wnum));
      });
      state.dirty = true;
    }

    if(headline){
      var h1 = doc.querySelector('h1');
      if(h1){ h1.textContent = headline; state.dirty = true; }
    }

    if(nome){
      // titulo da pagina
      if(doc.title) doc.title = nome;
      // schema.org
      atualizarSchema(doc, function(obj){
        obj.name = nome;
        return obj;
      });
      state.dirty = true;
    }

    if(end){
      atualizarSchema(doc, function(obj){
        if(!obj.address) obj.address = {'@type': 'PostalAddress'};
        obj.address.streetAddress = end;
        return obj;
      });
      state.dirty = true;
    }

    if(tel){
      atualizarSchema(doc, function(obj){
        obj.telephone = tel;
        return obj;
      });
    }

    if(horSeg || horSab){
      atualizarSchema(doc, function(obj){
        var arr = [];
        if(horSeg){
          var p = horSeg.split(/[-–]/);
          if(p.length === 2) arr.push({'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Tuesday','Wednesday','Thursday','Friday'],'opens':p[0].trim(),'closes':p[1].trim()});
        }
        if(horSab){
          var p2 = horSab.split(/[-–]/);
          if(p2.length === 2) arr.push({'@type':'OpeningHoursSpecification','dayOfWeek':['Saturday'],'opens':p2[0].trim(),'closes':p2[1].trim()});
        }
        if(arr.length) obj.openingHoursSpecification = arr;
        return obj;
      });
      state.dirty = true;
    }

    status('Campos aplicados. Clique SALVAR pra persistir.', false);
  }

  function atualizarSchema(doc, mutator){
    var node = doc.querySelector('script[type="application/ld+json"]');
    if(!node) return;
    try {
      var obj = JSON.parse(node.textContent);
      var novo = mutator(obj);
      node.textContent = JSON.stringify(novo, null, 2);
    } catch(e){ console.warn('[Editor] schema parse', e); }
  }

  function salvar(){
    var doc = getIframeDoc();
    if(!doc){ status('Nada para salvar', true); return; }
    var html = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
    // remove atributos contenteditable antes de salvar
    html = html.replace(/\s+contenteditable="true"/g, '');
    html = html.replace(/\s+style="outline:[^"]*"/g, '');

    status('Salvando...', false);
    authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/salvar-html', {
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
          return;
        }
        state.dirty = false;
        status('Site salvo com sucesso!', false);
      })
      .catch(function(err){
        status('Falha de rede: ' + (err.message || err), true);
      });
  }

  global.abrirEditorWYSIWYG = abrir;
  global.editorFechar = fechar;
  global.editorSalvarSite = salvar;
  global.editorSincronizarCampos = sincronizarCampos;
})(window);
