/* site-editor/commands.js — File conversion, image upload, element operations, section insertion */
(function(global){
  'use strict';

  var state = window._ed.state;
  var $ = window._ed.$;
  var escapeText = window._ed.escapeText;
  var getIframeDoc = window._ed.getIframeDoc;

  function fileToBase64(file){
    return new Promise(function(resolve, reject){
      var reader = new FileReader();
      reader.onload = function(){ resolve(reader.result || ''); };
      reader.onerror = function(){ reject(new Error('Falha ao ler arquivo')); };
      reader.readAsDataURL(file);
    });
  }

  function uploadAsset(file){
    if(!file) return Promise.reject(new Error('Nenhum arquivo selecionado'));
    if(!state.leadId) return Promise.reject(new Error('Lead invalido'));
    if(file.size > 5 * 1024 * 1024){
      return Promise.reject(new Error('Imagem maior que 5MB'));
    }
    var allowed = ['image/png','image/jpeg','image/webp','image/gif'];
    if(file.type && allowed.indexOf(file.type) === -1){
      return Promise.reject(new Error('Use PNG, JPG, WebP ou GIF'));
    }
    window._ed.status('Enviando imagem...', false);
    return fileToBase64(file).then(function(dataBase64){
      return window.authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/upload-asset', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          filename: file.name || 'imagem',
          content_type: file.type || '',
          data_base64: dataBase64,
        }),
      });
    }).then(function(r){
      return r.json().then(function(j){ return {ok: r.ok, status: r.status, body: j}; });
    }).then(function(res){
      if(!res.ok){
        var msg = (res.body && res.body.detail) ? res.body.detail : ('HTTP ' + res.status);
        throw new Error(msg);
      }
      return res.body;
    });
  }

  function editorUploadSelectedImage(file){
    var el = global.getSelected();
    if(!el || (el.tagName || '').toLowerCase() !== 'img'){
      window._ed.status('Selecione uma imagem no canvas antes do upload.', true);
      return;
    }
    uploadAsset(file)
      .then(function(asset){
        el.setAttribute('src', asset.url);
        if($('editorImageSrc')) $('editorImageSrc').value = asset.url;
        window._ed.setDirty(true);
        global.pushHistory();
        global.renderInspector(el);
        global.renderImages();
        window._ed.status('Imagem enviada e aplicada.', false);
      })
      .catch(function(err){ window._ed.status('Upload falhou: ' + (err.message || err), true); });
  }

  function editorUploadLogo(file){
    uploadAsset(file)
      .then(function(asset){
        if($('editorLogoUrl')) $('editorLogoUrl').value = asset.url;
        global.editorApplyLogo();
        window._ed.status('Logo enviado e aplicado.', false);
      })
      .catch(function(err){ window._ed.status('Upload falhou: ' + (err.message || err), true); });
  }

  function renderImages(){
    var doc = getIframeDoc();
    var list = $('editorImageList');
    if(!doc || !list) return;
    var images = Array.prototype.slice.call(doc.querySelectorAll('img'));
    list.innerHTML = images.length ? images.map(function(img, index){
      var id = img.dataset.fralibEditorId || '';
      var src = img.getAttribute('src') || '';
      var alt = img.getAttribute('alt') || '';
      return '<div class="editor-row">' +
        '<img class="editor-thumb" src="' + escapeText(src) + '" alt="">' +
        '<span class="editor-row-main"><span class="editor-row-title">Imagem ' + (index + 1) + '</span><span class="editor-row-sub">' + escapeText(alt || src) + '</span></span>' +
        '<button onclick="editorSelectById(\'' + escapeText(id) + '\')">Editar</button>' +
      '</div>';
    }).join('') : '<div class="editor-empty">Nenhuma imagem encontrada neste HTML.</div>';
    var selected = global.getSelected();
    if(selected && (selected.tagName || '').toLowerCase() === 'img'){
      if($('editorImageSrc')) $('editorImageSrc').value = selected.getAttribute('src') || '';
      if($('editorImageAlt')) $('editorImageAlt').value = selected.getAttribute('alt') || '';
    }
  }

  function renderSections(){
    var doc = getIframeDoc();
    var list = $('editorSectionList');
    if(!doc || !list) return;
    var sections = Array.prototype.slice.call(doc.querySelectorAll('header,main>section,section,footer'))
      .filter(function(el, index, arr){ return arr.indexOf(el) === index; });
    list.innerHTML = sections.length ? sections.map(function(el, index){
      var id = el.dataset.fralibEditorId || '';
      var title = sectionTitle(el, index);
      return '<div class="editor-row">' +
        '<span class="editor-row-main"><span class="editor-row-title">' + escapeText(title) + '</span><span class="editor-row-sub">' + escapeText((el.tagName || '').toLowerCase()) + '</span></span>' +
        '<button onclick="editorSelectById(\'' + escapeText(id) + '\')">Selecionar</button>' +
      '</div>';
    }).join('') : '<div class="editor-empty">Nenhuma seção detectada.</div>';
  }

  function sectionTitle(el, index){
    var heading = el.querySelector && el.querySelector('h1,h2,h3');
    var text = heading ? (heading.textContent || '').trim() : '';
    if(!text) text = (el.getAttribute('id') || el.getAttribute('class') || '').trim();
    return text || ('Seção ' + (index + 1));
  }

  function editorSelectById(id){
    if(!id) return;
    global.selecionarElemento(id);
  }

  function editorDuplicateSelected(){
    var el = global.getSelected();
    if(!el){ window._ed.status('Selecione um elemento primeiro.', true); return; }
    var clone = el.cloneNode(true);
    global.scrubEditorAttrs(clone);
    el.parentNode.insertBefore(clone, el.nextSibling);
    global.assignEditorIds(getIframeDoc());
    global.selecionarElemento(clone);
    window._ed.setDirty(true);
    global.pushHistory();
    global.renderSections();
    global.renderImages();
  }

  function editorMoveSelected(direction){
    var el = global.getSelected();
    if(!el || !el.parentNode){ window._ed.status('Selecione um elemento primeiro.', true); return; }
    if(direction === 'up' && el.previousElementSibling){
      el.parentNode.insertBefore(el, el.previousElementSibling);
    } else if(direction === 'down' && el.nextElementSibling){
      el.parentNode.insertBefore(el.nextElementSibling, el);
    } else {
      window._ed.status('Não há para onde mover.', true);
      return;
    }
    window._ed.setDirty(true);
    global.pushHistory();
    global.renderSections();
  }

  function editorDeleteSelected(){
    var el = global.getSelected();
    if(!el){ window._ed.status('Selecione um elemento primeiro.', true); return; }
    if(!confirm('Excluir este elemento do site?')) return;
    var parent = el.parentNode;
    el.remove();
    state.selectedId = null;
    global.renderInspector(null);
    global.renderSelectedPath(null);
    window._ed.setDirty(true);
    global.pushHistory();
    if(parent && parent.dataset && parent.dataset.fralibEditorId) global.selecionarElemento(parent);
    global.renderSections();
    global.renderImages();
  }

  function editorAddSection(type){
    var doc = getIframeDoc();
    if(!doc || !doc.body) return;
    var section = doc.createElement('section');
    section.innerHTML = sectionTemplate(type);
    if(type === 'contact') section.id = 'contato';
    section.setAttribute('data-reveal','');
    section.style.padding = 'clamp(48px,8vw,96px) clamp(20px,6vw,72px)';
    var darkSection = type === 'cta' || type === 'hero' || type === 'offer';
    section.style.background = darkSection ? 'linear-gradient(135deg,#09090b,#18181b)' : '#ffffff';
    section.style.color = darkSection ? '#ffffff' : '#111827';
    var footer = doc.querySelector('footer');
    if(footer && footer.parentNode) footer.parentNode.insertBefore(section, footer);
    else doc.body.appendChild(section);
    global.assignEditorIds(doc);
    global.bindEditableText(doc);
    global.selecionarElemento(section);
    window._ed.setDirty(true);
    global.pushHistory();
    global.renderSections();
    window._ed.status('Seção adicionada.', false);
  }

  function sectionTemplate(type){
    if(type === 'hero'){
      return '<div style="max-width:1180px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:32px;align-items:center"><div><p style="font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#10b981;margin:0 0 12px">Atendimento local</p><h1 style="font-size:clamp(42px,7vw,88px);line-height:.95;margin:0 0 18px">Resolva com uma equipe perto de você</h1><p style="font-size:18px;line-height:1.65;color:#d1d5db;max-width:620px;margin:0 0 28px">Uma chamada clara para explicar o valor principal, reduzir dúvida e levar o visitante direto ao WhatsApp.</p><a href="#contato" style="display:inline-flex;align-items:center;justify-content:center;padding:15px 24px;border-radius:999px;background:#10b981;color:#06130d;text-decoration:none;font-weight:900">Falar agora</a></div><figure style="margin:0"><img src="https://images.unsplash.com/photo-1556745757-8d76bdb6984b?auto=format&fit=crop&w=1000&q=80" alt="Equipe em atendimento" style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:18px"></figure></div>';
    }
    if(type === 'offer'){
      return '<div style="max-width:1050px;margin:0 auto;text-align:center"><p style="font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#10b981;margin:0 0 12px">Oferta principal</p><h2 style="font-size:clamp(38px,6vw,76px);line-height:.96;margin:0 0 18px">Condição especial para quem chama hoje</h2><p style="font-size:18px;line-height:1.65;color:#d1d5db;max-width:720px;margin:0 auto 26px">Explique o benefício real sem prometer o que o negócio não entrega. Mantenha clareza, prazo e próximo passo.</p><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;text-align:left"><article style="padding:18px;border:1px solid rgba(255,255,255,.16);border-radius:14px"><strong>Resposta rápida</strong><p style="color:#d1d5db">Contato direto pelo WhatsApp.</p></article><article style="padding:18px;border:1px solid rgba(255,255,255,.16);border-radius:14px"><strong>Orientação clara</strong><p style="color:#d1d5db">Sem burocracia para começar.</p></article><article style="padding:18px;border:1px solid rgba(255,255,255,.16);border-radius:14px"><strong>Atendimento local</strong><p style="color:#d1d5db">Confirme endereço e horários.</p></article></div></div>';
    }
    if(type === 'pricing'){
      return '<div style="max-width:1120px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 22px">Escolha o melhor caminho</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px"><article style="padding:24px;border:1px solid rgba(17,24,39,.14);border-radius:14px"><h3>Essencial</h3><p style="font-size:34px;font-weight:900;margin:10px 0">Consulte</p><p>Para quem precisa tirar dúvidas e entender disponibilidade.</p></article><article style="padding:24px;border:2px solid #10b981;border-radius:14px;box-shadow:0 16px 36px rgba(16,185,129,.16)"><h3>Mais escolhido</h3><p style="font-size:34px;font-weight:900;margin:10px 0">Sob medida</p><p>Opção principal com atendimento e orientação completa.</p></article><article style="padding:24px;border:1px solid rgba(17,24,39,.14);border-radius:14px"><h3>Premium</h3><p style="font-size:34px;font-weight:900;margin:10px 0">Personalizado</p><p>Para necessidades específicas, prazo ou suporte dedicado.</p></article></div></div>';
    }
    if(type === 'process'){
      return '<div style="max-width:1040px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 26px">Como funciona</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px"><article style="padding:22px;border-left:4px solid #10b981;background:#f8fafc;border-radius:10px"><strong>1. Chame no WhatsApp</strong><p>Envie sua dúvida ou necessidade principal.</p></article><article style="padding:22px;border-left:4px solid #0ea5e9;background:#f8fafc;border-radius:10px"><strong>2. Confirme detalhes</strong><p>A equipe informa horários, endereço e próximos passos.</p></article><article style="padding:22px;border-left:4px solid #f59e0b;background:#f8fafc;border-radius:10px"><strong>3. Siga com segurança</strong><p>Você decide com informação clara e contato direto.</p></article></div></div>';
    }
    if(type === 'team'){
      return '<div style="max-width:1120px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 22px">Equipe de atendimento</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px"><article style="padding:18px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=700&q=80" alt="Pessoa da equipe" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:12px"><h3>Responsável</h3><p>Atendimento inicial e orientação.</p></article><article style="padding:18px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><img src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=700&q=80" alt="Especialista" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:12px"><h3>Especialista</h3><p>Suporte para dúvidas técnicas.</p></article><article style="padding:18px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><img src="https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=700&q=80" alt="Atendente" style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:12px"><h3>Relacionamento</h3><p>Acompanha o contato até a decisão.</p></article></div></div>';
    }
    if(type === 'contact'){
      return '<div style="max-width:1040px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px;align-items:start"><div><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 16px">Fale com a equipe</h2><p style="font-size:18px;line-height:1.65">Use WhatsApp, telefone ou endereço para confirmar informações antes de ir.</p><a href="https://wa.me/5500000000000" style="display:inline-flex;align-items:center;justify-content:center;padding:14px 22px;border-radius:999px;background:#10b981;color:#06130d;text-decoration:none;font-weight:900">Chamar no WhatsApp</a></div><div style="padding:22px;border:1px solid rgba(17,24,39,.14);border-radius:14px;background:#f8fafc"><h3>Contato</h3><p><strong>Telefone:</strong> (00) 00000-0000</p><p><strong>Endereço:</strong> Rua principal, 123</p><p><strong>Horário:</strong> Seg-Sex, 08:00 - 18:00</p><a href="https://www.google.com/maps/search/Rua%20principal%20123" style="color:#0369a1;font-weight:900">Ver rota no mapa</a></div></div>';
    }
    if(type === 'testimonials'){
      return '<div style="max-width:1100px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 22px">O que clientes destacam</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px"><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><p>Atendimento rápido e direto.</p><strong>Cliente local</strong></article><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><p>Consegui resolver tudo pelo WhatsApp.</p><strong>Cliente recorrente</strong></article><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><p>Fácil de encontrar e falar com a equipe.</p><strong>Morador da região</strong></article></div></div>';
    }
    if(type === 'faq'){
      return '<div style="max-width:900px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 24px">Dúvidas frequentes</h2><details open style="padding:18px 0;border-bottom:1px solid rgba(17,24,39,.14)"><summary style="font-weight:800;cursor:pointer">Como faço contato?</summary><p>Use o botão de WhatsApp para falar com a equipe.</p></details><details style="padding:18px 0;border-bottom:1px solid rgba(17,24,39,.14)"><summary style="font-weight:800;cursor:pointer">Onde fica?</summary><p>Confira o endereço e confirme detalhes antes de ir.</p></details><details style="padding:18px 0;border-bottom:1px solid rgba(17,24,39,.14)"><summary style="font-weight:800;cursor:pointer">Preciso agendar?</summary><p>Entre em contato para confirmar disponibilidade.</p></details></div>';
    }
    if(type === 'gallery'){
      return '<div style="max-width:1100px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 22px">Galeria</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px"><img src="https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=800&q=80" alt="Imagem editorial do negócio" style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:14px"><img src="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=800&q=80" alt="Detalhe visual" style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:14px"><img src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80" alt="Ambiente" style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:14px"></div></div>';
    }
    if(type === 'services'){
      return '<div style="max-width:1100px;margin:0 auto"><h2 style="font-size:clamp(32px,5vw,56px);line-height:1;margin:0 0 22px">Como podemos ajudar</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px"><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><h3>Atendimento</h3><p>Fale com a equipe e confirme o melhor caminho.</p></article><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><h3>Orientação</h3><p>Receba informações claras antes de decidir.</p></article><article style="padding:22px;border:1px solid rgba(17,24,39,.12);border-radius:14px"><h3>Contato direto</h3><p>Use WhatsApp, telefone ou endereço para seguir.</p></article></div></div>';
    }
    return '<div style="max-width:980px;margin:0 auto;text-align:center"><h2 style="font-size:clamp(36px,6vw,72px);line-height:1;margin:0 0 16px">Pronto para conversar?</h2><p style="font-size:18px;line-height:1.6;max-width:640px;margin:0 auto 24px">Fale com a equipe agora e tire suas dúvidas pelo canal mais rápido.</p><a href="#contato" style="display:inline-flex;align-items:center;justify-content:center;padding:14px 24px;border-radius:999px;background:#10b981;color:#06130d;text-decoration:none;font-weight:900">Chamar no WhatsApp</a></div>';
  }

  /* ── Exports ── */
  global.editorUploadSelectedImage = editorUploadSelectedImage;
  global.editorUploadLogo = editorUploadLogo;
  global.renderImages = renderImages;
  global.renderSections = renderSections;
  global.sectionTitle = sectionTitle;
  global.editorSelectById = editorSelectById;
  global.editorDuplicateSelected = editorDuplicateSelected;
  global.editorMoveSelected = editorMoveSelected;
  global.editorDeleteSelected = editorDeleteSelected;
  global.editorAddSection = editorAddSection;
  global.sectionTemplate = sectionTemplate;

})(window);
