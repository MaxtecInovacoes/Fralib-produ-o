/* site-editor/sync.js — Field polling, schema mutation, sincronizarCampos */
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

  function preencherCamposPorInspecao(){
    setTimeout(function(){
      var doc = getIframeDoc();
      if(!doc) return;
      var h1 = doc.querySelector('h1');
      if(h1 && $('edHeadline')) $('edHeadline').value = (h1.textContent || '').trim();
      var schema = doc.querySelector('script[type="application/ld+json"]');
      if(schema){
        try {
          var obj = JSON.parse(schema.textContent);
          if(obj.name && $('edNome')) $('edNome').value = obj.name;
          if(obj.telephone && $('edTelefone')) $('edTelefone').value = obj.telephone;
          if(obj.address && $('edEndereco')){
            var addr = obj.address;
            var parts = [addr.streetAddress, addr.addressLocality, addr.addressRegion].filter(Boolean);
            if(parts.length) $('edEndereco').value = parts.join(' - ');
          }
        } catch(e){}
      }
      if($('edTelefone') && !$('edTelefone').value){
        var telLink = doc.querySelector('a[href^="tel:"]');
        if(telLink) $('edTelefone').value = telLink.getAttribute('href').replace('tel:', '').trim();
      }
    }, 300);
  }

  function sincronizarCampos(){
    var doc = getIframeDoc();
    if(!doc){ status('Site nao carregado', true); return; }
    var tel = ($('edTelefone') && $('edTelefone').value || '').trim();
    var nome = ($('edNome') && $('edNome').value || '').trim();
    var headline = ($('edHeadline') && $('edHeadline').value || '').trim();
    var end = ($('edEndereco') && $('edEndereco').value || '').trim();
    var horSeg = ($('edHorSeg') && $('edHorSeg').value || '').trim();
    var horSab = ($('edHorSab') && $('edHorSab').value || '').trim();

    if(tel){
      var telDigits = tel.replace(/\D/g, '');
      var wnum = telDigits.length >= 10 ? (telDigits.indexOf('55') === 0 ? telDigits : '55' + telDigits) : telDigits;
      doc.querySelectorAll('a[href^="tel:"]').forEach(function(a){ a.setAttribute('href', 'tel:' + tel); a.textContent = tel; });
      doc.querySelectorAll('a[href*="wa.me/"], a[href*="api.whatsapp.com"]').forEach(function(a){
        var oldHref = a.getAttribute('href') || '';
        a.setAttribute('href', oldHref.replace(/wa\.me\/\d+/, 'wa.me/' + wnum).replace(/phone=\d+/, 'phone=' + wnum));
      });
      atualizarSchema(doc, function(obj){ obj.telephone = tel; return obj; });
    }
    if(headline){
      var h1 = doc.querySelector('h1');
      if(h1) h1.textContent = headline;
    }
    if(nome){
      doc.title = nome;
      atualizarSchema(doc, function(obj){ obj.name = nome; return obj; });
    }
    if(end){
      atualizarSchema(doc, function(obj){
        if(!obj.address) obj.address = {'@type':'PostalAddress'};
        obj.address.streetAddress = end;
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
    }
    setDirty(true);
    global.pushHistory();
    global.renderSections();
    global.renderImages();
    status('Dados aplicados. Clique em Salvar site para persistir.', false);
  }

  function atualizarSchema(doc, mutator){
    var node = doc.querySelector('script[type="application/ld+json"]');
    if(!node) return;
    try {
      var obj = JSON.parse(node.textContent);
      node.textContent = JSON.stringify(mutator(obj), null, 2);
    } catch(e){ console.warn('[Editor] schema parse', e); }
  }

  /* ── Exports ── */
  global.preencherCamposPorInspecao = preencherCamposPorInspecao;
  global.sincronizarCampos = sincronizarCampos;
  global.atualizarSchema = atualizarSchema;
  global.editorSincronizarCampos = sincronizarCampos;

})(window);
