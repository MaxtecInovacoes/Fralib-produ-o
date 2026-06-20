/**
 * FraLib Site Editor
 * ============================================================================
 * ⚠️  SHIM DE COMPATIBILIDADE - NÃO É MONOLITO
 * ============================================================================
 * Mantido para backward compatibility apenas.
 * Módulos reais estão em /js/site-editor/:
 *   - bootstrap.js  → Namespace window._ed
 *   - state.js      → Estado global
 *   - editing.js    → Edição de elementos
 *   - commands.js   → Comandos (upload, delete, etc)
 *   - sync.js       → Sincronização de campos
 *   - save.js       → Persistência
 *   - history.js    → Undo/redo
 *   - ai.js         → Integração AI
 *
 * Para novo código, importe diretamente dos módulos.
 *
 * @deprecated Use /js/site-editor/* modules directly
 * @architecture Shim (0 lógica de negócio - apenas bootstrapping)
 * ============================================================================
 */
(function(global){
  'use strict';

  /* ================================================================
   * state.js — Global state, selectors, DOM helpers, modal lifecycle
   * ================================================================ */

  var state = {
    leadId: null,
    slug: null,
    htmlOriginal: '',
    dirty: false,
    selectedId: null,
    selectedKind: null,
    nextId: 1,
    history: [],
    historyIndex: -1,
    snapshotTimer: null,
    device: 'desktop',
    restoring: false,
  };

  var SELECTABLE = [
    'section','header','footer','nav','main','article','aside',
    'h1','h2','h3','h4','h5','p','li','a','button','blockquote',
    'img','picture','figure','form','input','textarea','select',
    '.card','[class*="card"]','[class*="hero"]','[class*="cta"]'
  ].join(',');

  var TEXT_SELECTOR = 'h1,h2,h3,h4,h5,p,li,a,button,span,strong,em,small,blockquote,figcaption,label,td,th';

  function $(id){ return document.getElementById(id); }

  function escapeText(value){
    return String(value == null ? '' : value)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;')
      .replace(/'/g,'&#039;');
  }

  function status(msg, isErr){
    var el = $('editorStatus');
    if(!el) return;
    el.textContent = msg;
    el.classList.toggle('err', !!isErr);
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(function(){ el.classList.remove('show'); }, 2800);
  }

  function setDirty(value){
    state.dirty = value !== false;
    var sub = $('editorSiteSubtitle');
    if(sub){
      sub.textContent = state.dirty
        ? 'Alterações locais ainda não salvas.'
        : 'Selecione um elemento no site para editar texto, estilo, imagem ou seção.';
    }
  }

  function abrir(leadId){
    if(!leadId){ alert('Lead invalido'); return; }
    state.leadId = leadId;
    state.selectedId = null;
    state.nextId = 1;
    state.history = [];
    state.historyIndex = -1;
    setDirty(false);
    $('editorSiteModal').classList.add('open');
    editorSetDevice(state.device || 'desktop');
    $('editorSiteTitle').textContent = 'Carregando site...';
    $('editorIframe').srcdoc = '<p style="font-family:sans-serif;padding:32px;color:#666">Carregando...</p>';
    renderInspector(null);

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
      try { ligarEdicao(doc); } catch(e){ console.error('[Editor] ligar', e); }
    });
  });

  function ligarEdicao(doc){
    injectEditorStyles(doc);
    assignEditorIds(doc);
    bindEditableText(doc);
    bindCanvasEvents(doc);
    renderSections();
    renderImages();
    if(state.restoring){
      state.restoring = false;
      updateHistoryButtons();
    } else {
      pushHistory(true);
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
    var nodes = doc.querySelectorAll(SELECTABLE);
    nodes.forEach(function(el){
      if(el.closest('script,style,noscript,template')) return;
      if(!el.dataset.fralibEditorId){
        el.dataset.fralibEditorId = 'ed-' + (state.nextId++);
      }
    });
  }

  /* ================================================================
   * editing.js — Text editing, selection, element classification, inspector panel
   * ================================================================ */

  function isTextOnly(el){
    return Array.prototype.every.call(el.childNodes, function(n){
      return n.nodeType === 3 || (n.nodeType === 1 && /^(BR|STRONG|EM|SPAN|A|B|I|U|SMALL)$/i.test(n.tagName));
    });
  }

  function bindEditableText(doc){
    doc.querySelectorAll(TEXT_SELECTOR).forEach(function(el){
      if(el.closest('script,style,noscript,template')) return;
      if(!isTextOnly(el)) return;
      el.contentEditable = 'true';
      el.setAttribute('spellcheck','false');
      el.addEventListener('focus', function(){ selecionarElemento(el); });
      el.addEventListener('input', function(){
        setDirty(true);
        syncInspectorFromSelected();
        scheduleSnapshot();
      });
    });
  }

  function bindCanvasEvents(doc){
    doc.addEventListener('click', function(e){
      var target = e.target;
      var selectable = target && target.closest ? target.closest('[data-fralib-editor-id]') : null;
      var link = target && target.closest ? target.closest('a') : null;
      if(link) e.preventDefault();
      if(selectable){
        e.preventDefault();
        selecionarElemento(selectable);
      }
    }, true);
  }

  function getSelected(){
    var doc = getIframeDoc();
    if(!doc || !state.selectedId) return null;
    return doc.querySelector('[data-fralib-editor-id="' + state.selectedId + '"]');
  }

  function selecionarElemento(elOrId){
    var doc = getIframeDoc();
    if(!doc) return;
    var el = typeof elOrId === 'string'
      ? doc.querySelector('[data-fralib-editor-id="' + elOrId + '"]')
      : elOrId;
    if(!el) return;
    doc.querySelectorAll('[data-fralib-editor-selected="true"]').forEach(function(node){
      node.removeAttribute('data-fralib-editor-selected');
    });
    el.dataset.fralibEditorSelected = 'true';
    state.selectedId = el.dataset.fralibEditorId;
    state.selectedKind = classifyElement(el);
    renderInspector(el);
    renderSelectedPath(el);
    renderImages();
    renderSections();
  }

  function classifyElement(el){
    var tag = (el.tagName || '').toLowerCase();
    if(tag === 'img' || tag === 'picture' || tag === 'figure') return 'media';
    if(tag === 'a' || tag === 'button') return 'button';
    if(tag === 'section' || tag === 'header' || tag === 'footer' || tag === 'nav' || tag === 'main' || tag === 'article') return 'section';
    if(/^(h1|h2|h3|h4|h5|p|li|span|strong|em|small|blockquote|figcaption|label|td|th)$/.test(tag)) return 'text';
    return 'block';
  }

  function elementLabel(el){
    if(!el) return 'Nenhum elemento';
    var tag = (el.tagName || '').toLowerCase();
    var text = '';
    if(tag === 'img') text = el.getAttribute('alt') || el.getAttribute('src') || '';
    else text = (el.innerText || el.textContent || '').trim().replace(/\s+/g,' ');
    if(text.length > 54) text = text.slice(0,54) + '...';
    return tag + (text ? ' · ' + text : '');
  }

  function renderSelectedPath(el){
    var path = $('editorSelectedPath');
    if(path) path.textContent = elementLabel(el);
    var hint = $('editorInspectorHint');
    if(hint) hint.textContent = state.selectedKind === 'media'
      ? 'Edite imagem, alt text e enquadramento.'
      : 'Ajuste texto, link, espaçamento, cor e aparência.';
  }

  function renderInspector(el){
    var body = $('editorInspectorBody');
    if(!body) return;
    if(!el){
      body.innerHTML = '<div class="editor-empty">Nenhum elemento selecionado.</div>';
      return;
    }
    var tag = (el.tagName || '').toLowerCase();
    var textValue = state.selectedKind === 'media' ? '' : (el.innerText || el.textContent || '').trim();
    var canEditText = state.selectedKind === 'text' || state.selectedKind === 'button';
    var href = tag === 'a' ? (el.getAttribute('href') || '') : '';
    var imgSrc = tag === 'img' ? (el.getAttribute('src') || '') : '';
    var imgAlt = tag === 'img' ? (el.getAttribute('alt') || '') : '';
    body.innerHTML =
      '<div class="editor-tab-panel active">' +
        '<div class="editor-row" style="margin-bottom:12px"><span class="editor-row-main"><span class="editor-row-title">' + escapeText(tag.toUpperCase()) + '</span><span class="editor-row-sub">' + escapeText(classifyElement(el)) + '</span></span></div>' +
        (canEditText ? '<div class="editor-field"><label for="editorSelectedText">Texto</label><textarea id="editorSelectedText" rows="4" oninput="editorUpdateSelectedText(this.value)">' + escapeText(textValue) + '</textarea></div>' : '') +
        (tag === 'a' ? '<div class="editor-field"><label for="editorSelectedHref">Link</label><input id="editorSelectedHref" value="' + escapeText(href) + '" oninput="editorUpdateSelectedAttr(\'href\',this.value)" /></div>' : '') +
        (tag === 'img' ? '<div class="editor-field"><label for="editorSelectedSrc">Imagem</label><input id="editorSelectedSrc" value="' + escapeText(imgSrc) + '" oninput="editorUpdateSelectedAttr(\'src\',this.value)" /></div><div class="editor-field"><label for="editorSelectedAlt">Alt</label><input id="editorSelectedAlt" value="' + escapeText(imgAlt) + '" oninput="editorUpdateSelectedAttr(\'alt\',this.value)" /></div>' : '') +
        '<div class="editor-grid-2">' +
          '<div class="editor-field"><label>Texto</label><input type="color" value="' + rgbToHex(getComputedStyleSafe(el,'color') || '#ffffff') + '" onchange="editorApplyStyle(\'color\',this.value)" /></div>' +
          '<div class="editor-field"><label>Fundo</label><input type="color" value="' + rgbToHex(getComputedStyleSafe(el,'backgroundColor') || '#111827') + '" onchange="editorApplyStyle(\'backgroundColor\',this.value)" /></div>' +
        '</div>' +
        '<div class="editor-grid-2">' +
          '<div class="editor-field"><label for="editorFontSize">Fonte</label><input id="editorFontSize" type="number" min="10" max="96" value="' + parseInt(getComputedStyleSafe(el,'fontSize') || '16',10) + '" onchange="editorApplyStyle(\'fontSize\',this.value + \'px\')" /></div>' +
          '<div class="editor-field"><label for="editorRadius">Raio</label><input id="editorRadius" type="number" min="0" max="40" value="' + parseInt(getComputedStyleSafe(el,'borderRadius') || '0',10) + '" onchange="editorApplyStyle(\'borderRadius\',this.value + \'px\')" /></div>' +
        '</div>' +
        '<div class="editor-grid-2">' +
          '<div class="editor-field"><label for="editorPadding">Padding</label><input id="editorPadding" type="number" min="0" max="120" value="' + parseInt(getComputedStyleSafe(el,'paddingTop') || '0',10) + '" onchange="editorApplyStyle(\'padding\',this.value + \'px\')" /></div>' +
          '<div class="editor-field"><label for="editorMargin">Margem</label><input id="editorMargin" type="number" min="0" max="120" value="' + parseInt(getComputedStyleSafe(el,'marginTop') || '0',10) + '" onchange="editorApplyStyle(\'margin\',this.value + \'px 0\')" /></div>' +
        '</div>' +
        '<div class="editor-field"><label>Alinhamento</label><div class="editor-pill-row"><button class="editor-pill" onclick="editorApplyStyle(\'textAlign\',\'left\')">Esq.</button><button class="editor-pill" onclick="editorApplyStyle(\'textAlign\',\'center\')">Centro</button><button class="editor-pill" onclick="editorApplyStyle(\'textAlign\',\'right\')">Dir.</button></div></div>' +
      '</div>';
  }

  function getComputedStyleSafe(el, prop){
    try { return el.ownerDocument.defaultView.getComputedStyle(el)[prop]; }
    catch(e){ return ''; }
  }

  function rgbToHex(value){
    if(!value || value === 'transparent' || value === 'rgba(0, 0, 0, 0)') return '#111827';
    if(value.charAt(0) === '#') return value.slice(0,7);
    var m = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if(!m) return '#111827';
    return '#' + [m[1],m[2],m[3]].map(function(n){
      return Math.max(0, Math.min(255, parseInt(n,10))).toString(16).padStart(2,'0');
    }).join('');
  }

  function editorSetTab(tab){
    ['content','style','media','sections','ai'].forEach(function(name){
      var panel = $('editorTab' + cap(name));
      var btn = $('editorTab' + cap(name) + 'Btn');
      if(panel) panel.classList.toggle('active', name === tab);
      if(btn) btn.classList.toggle('active', name === tab);
    });
  }

  function cap(value){ return value.charAt(0).toUpperCase() + value.slice(1); }

  function editorSetDevice(device){
    state.device = device || 'desktop';
    var modal = $('editorSiteModal');
    if(modal){
      modal.classList.remove('device-desktop','device-tablet','device-mobile');
      modal.classList.add('device-' + state.device);
    }
    ['Desktop','Tablet','Mobile'].forEach(function(name){
      var btn = $('editorDevice' + name);
      if(btn) btn.classList.toggle('active', name.toLowerCase() === state.device);
    });
  }

  function editorUpdateSelectedText(value){
    var el = getSelected();
    if(!el) return;
    if(state.selectedKind !== 'text' && state.selectedKind !== 'button') return;
    el.textContent = value;
    setDirty(true);
    renderSelectedPath(el);
    scheduleSnapshot();
  }

  function editorUpdateSelectedAttr(attr, value){
    var el = getSelected();
    if(!el) return;
    if(value) el.setAttribute(attr, value);
    else el.removeAttribute(attr);
    setDirty(true);
    renderSelectedPath(el);
    scheduleSnapshot();
    renderImages();
  }

  function editorApplyStyle(prop, value){
    var el = getSelected();
    if(!el || !prop) return;
    el.style[prop] = value;
    setDirty(true);
    scheduleSnapshot();
    renderInspector(el);
  }

  function editorApplyPalette(color){
    var el = getSelected();
    if(!el){ status('Selecione um elemento primeiro.', true); return; }
    var tag = (el.tagName || '').toLowerCase();
    if(tag === 'a' || tag === 'button'){
      el.style.backgroundColor = color;
      el.style.borderColor = color;
      el.style.color = readableTextOn(color);
    } else if(state.selectedKind === 'section' || state.selectedKind === 'block'){
      el.style.backgroundColor = color;
      el.style.color = readableTextOn(color);
    } else {
      el.style.color = color;
    }
    setDirty(true);
    scheduleSnapshot();
    renderInspector(el);
  }

  function readableTextOn(hex){
    var h = (hex || '#111827').replace('#','');
    if(h.length === 3) h = h.split('').map(function(c){ return c + c; }).join('');
    var r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
    var yiq = (r * 299 + g * 587 + b * 114) / 1000;
    return yiq > 150 ? '#111827' : '#ffffff';
  }

  function editorApplyGlobalAccent(color){
    var doc = getIframeDoc();
    if(!doc) return;
    var root = doc.documentElement;
    ['--accent','--primary','--brand','--fl-accent'].forEach(function(name){
      root.style.setProperty(name, color);
    });
    setDirty(true);
    scheduleSnapshot();
    status('Acento global aplicado.', false);
  }

  function editorApplyQuickStyle(kind){
    var el = getSelected();
    if(!el){ status('Selecione um elemento primeiro.', true); return; }
    if(kind === 'dark-section'){
      el.style.background = 'linear-gradient(135deg,#09090b,#18181b)';
      el.style.color = '#f8fafc';
      el.style.borderColor = 'rgba(255,255,255,.12)';
    } else if(kind === 'light-section'){
      el.style.background = '#f8fafc';
      el.style.color = '#111827';
      el.style.borderColor = 'rgba(17,24,39,.12)';
    } else if(kind === 'button-primary'){
      el.style.background = '#10b981';
      el.style.color = '#06130d';
      el.style.borderRadius = '999px';
      el.style.padding = '14px 22px';
      el.style.fontWeight = '800';
      el.style.display = 'inline-flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
    } else if(kind === 'card-polish'){
      el.style.border = '1px solid rgba(255,255,255,.14)';
      el.style.borderRadius = '14px';
      el.style.padding = '24px';
      el.style.boxShadow = '0 8px 24px rgba(0,0,0,.10)';
    }
    setDirty(true);
    scheduleSnapshot();
    renderInspector(el);
  }

  function editorUpdateSelectedImage(){
    var el = getSelected();
    if(!el || (el.tagName || '').toLowerCase() !== 'img'){
      var doc = getIframeDoc();
      if(doc) el = doc.querySelector('img[data-fralib-editor-selected="true"]');
    }
    if(!el) return;
    var src = $('editorImageSrc') ? $('editorImageSrc').value.trim() : '';
    var alt = $('editorImageAlt') ? $('editorImageAlt').value.trim() : '';
    if(src) el.setAttribute('src', src);
    el.setAttribute('alt', alt);
    setDirty(true);
    scheduleSnapshot();
    renderImages();
  }

  function editorApplyLogo(){
    var doc = getIframeDoc();
    var url = $('editorLogoUrl') ? $('editorLogoUrl').value.trim() : '';
    if(!doc || !url){ status('Informe a URL do logo.', true); return; }
    var logo = doc.querySelector('img[alt*="logo" i], header img, nav img');
    if(!logo){
      status('Nenhuma imagem de logo encontrada. Selecione uma imagem e troque manualmente.', true);
      return;
    }
    logo.setAttribute('src', url);
    logo.setAttribute('alt', 'Logo');
    selecionarElemento(logo);
    setDirty(true);
    scheduleSnapshot();
    renderImages();
    status('Logo atualizado no preview.', false);
  }

  function syncInspectorFromSelected(){
    var el = getSelected();
    if(!el) return;
    var input = $('editorSelectedText');
    if(input && document.activeElement !== input) input.value = (el.textContent || '').trim();
    renderSelectedPath(el);
  }

  /* ================================================================
   * commands.js — File conversion, image upload, element operations, section insertion
   * ================================================================ */

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
    status('Enviando imagem...', false);
    return fileToBase64(file).then(function(dataBase64){
      return authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/upload-asset', {
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
    var el = getSelected();
    if(!el || (el.tagName || '').toLowerCase() !== 'img'){
      status('Selecione uma imagem no canvas antes do upload.', true);
      return;
    }
    uploadAsset(file)
      .then(function(asset){
        el.setAttribute('src', asset.url);
        if($('editorImageSrc')) $('editorImageSrc').value = asset.url;
        setDirty(true);
        pushHistory();
        renderInspector(el);
        renderImages();
        status('Imagem enviada e aplicada.', false);
      })
      .catch(function(err){ status('Upload falhou: ' + (err.message || err), true); });
  }

  function editorUploadLogo(file){
    uploadAsset(file)
      .then(function(asset){
        if($('editorLogoUrl')) $('editorLogoUrl').value = asset.url;
        editorApplyLogo();
        status('Logo enviado e aplicado.', false);
      })
      .catch(function(err){ status('Upload falhou: ' + (err.message || err), true); });
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
    var selected = getSelected();
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
    selecionarElemento(id);
  }

  function editorDuplicateSelected(){
    var el = getSelected();
    if(!el){ status('Selecione um elemento primeiro.', true); return; }
    var clone = el.cloneNode(true);
    scrubEditorAttrs(clone);
    el.parentNode.insertBefore(clone, el.nextSibling);
    assignEditorIds(getIframeDoc());
    selecionarElemento(clone);
    setDirty(true);
    pushHistory();
    renderSections();
    renderImages();
  }

  function editorMoveSelected(direction){
    var el = getSelected();
    if(!el || !el.parentNode){ status('Selecione um elemento primeiro.', true); return; }
    if(direction === 'up' && el.previousElementSibling){
      el.parentNode.insertBefore(el, el.previousElementSibling);
    } else if(direction === 'down' && el.nextElementSibling){
      el.parentNode.insertBefore(el.nextElementSibling, el);
    } else {
      status('Não há para onde mover.', true);
      return;
    }
    setDirty(true);
    pushHistory();
    renderSections();
  }

  function editorDeleteSelected(){
    var el = getSelected();
    if(!el){ status('Selecione um elemento primeiro.', true); return; }
    if(!confirm('Excluir este elemento do site?')) return;
    var parent = el.parentNode;
    el.remove();
    state.selectedId = null;
    renderInspector(null);
    renderSelectedPath(null);
    setDirty(true);
    pushHistory();
    if(parent && parent.dataset && parent.dataset.fralibEditorId) selecionarElemento(parent);
    renderSections();
    renderImages();
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
    assignEditorIds(doc);
    bindEditableText(doc);
    selecionarElemento(section);
    setDirty(true);
    pushHistory();
    renderSections();
    status('Seção adicionada.', false);
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

  /* ================================================================
   * sync.js — Field polling, schema mutation, sincronizarCampos
   * ================================================================ */

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
    pushHistory();
    renderSections();
    renderImages();
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

  /* ================================================================
   * history.js — History stack, undo/redo
   * ================================================================ */

  function serializeForSave(){
    var doc = getIframeDoc();
    if(!doc) return '';
    var clone = doc.documentElement.cloneNode(true);
    scrubEditorAttrs(clone);
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
    updateHistoryButtons();
  }

  function scheduleSnapshot(){
    clearTimeout(state.snapshotTimer);
    state.snapshotTimer = setTimeout(function(){ pushHistory(); }, 600);
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
    updateHistoryButtons();
  }

  function editorUndo(){ restoreHistory(state.historyIndex - 1); }
  function editorRedo(){ restoreHistory(state.historyIndex + 1); }

  /* ================================================================
   * ai.js — AI presets and execution
   * ================================================================ */

  function serializeSelectedForPrompt(el){
    if(!el) return '';
    var clone = el.cloneNode(true);
    scrubEditorAttrs(clone);
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
    return authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/html')
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
        renderInspector(null);
        renderSelectedPath(null);
        setTimeout(function(){ status(message || 'Site recarregado.', false); }, 350);
      });
  }

  function editorRunAiPrompt(){
    var promptInput = $('editorAiPrompt');
    var prompt = promptInput ? promptInput.value.trim() : '';
    var scope = $('editorAiScope') ? $('editorAiScope').value : 'selected';
    var btn = $('editorAiRunBtn');
    var selected = getSelected();
    if(!prompt){ status('Escreva o pedido para a IA.', true); return; }
    if(scope === 'selected' && !selected){
      status('Selecione um elemento ou mude o escopo para site inteiro.', true);
      return;
    }
    if(scope === 'selected'){
      prompt = [
        'Edite somente o elemento selecionado quando encontrar trecho equivalente no HTML.',
        'Preserve o restante do site sem mudancas desnecessarias.',
        'Elemento selecionado: ' + elementLabel(selected),
        'HTML do elemento selecionado:',
        serializeSelectedForPrompt(selected),
        'Pedido: ' + prompt,
      ].join('\n');
    }
    if(btn) btn.disabled = true;
    status(state.dirty ? 'Salvando antes de aplicar IA...' : 'Aplicando IA...', false);
    var beforeAi = state.dirty ? salvar({throwOnError: true}) : Promise.resolve();
    return beforeAi.then(function(){
      return authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/editar-ia', {
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

  /* ================================================================
   * save.js — Save function, public API export
   * ================================================================ */

  function salvar(options){
    options = options || {};
    var html = serializeForSave();
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
    return authFetch('/api/sites/' + encodeURIComponent(state.leadId) + '/salvar-html', {
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
        pushHistory(true);
        status('Site salvo com sucesso.', false);
        return res.body;
      })
      .catch(function(err){
        status('Falha de rede: ' + (err.message || err), true);
        if(options.throwOnError) throw err;
        return null;
      });
  }

  /* ================================================================
   * Public API — global window exports
   * ================================================================ */
  global.abrirEditorWYSIWYG = abrir;
  global.editorFechar = fechar;
  global.editorSalvarSite = salvar;
  global.editorSincronizarCampos = sincronizarCampos;
  global.editorSetTab = editorSetTab;
  global.editorSetDevice = editorSetDevice;
  global.editorUpdateSelectedText = editorUpdateSelectedText;
  global.editorUpdateSelectedAttr = editorUpdateSelectedAttr;
  global.editorApplyStyle = editorApplyStyle;
  global.editorApplyPalette = editorApplyPalette;
  global.editorApplyGlobalAccent = editorApplyGlobalAccent;
  global.editorApplyQuickStyle = editorApplyQuickStyle;
  global.editorUpdateSelectedImage = editorUpdateSelectedImage;
  global.editorApplyLogo = editorApplyLogo;
  global.editorUploadSelectedImage = editorUploadSelectedImage;
  global.editorUploadLogo = editorUploadLogo;
  global.editorSelectById = editorSelectById;
  global.editorDuplicateSelected = editorDuplicateSelected;
  global.editorMoveSelected = editorMoveSelected;
  global.editorDeleteSelected = editorDeleteSelected;
  global.editorAddSection = editorAddSection;
  global.editorUseAiPreset = editorUseAiPreset;
  global.editorRunAiPrompt = editorRunAiPrompt;
  global.editorUndo = editorUndo;
  global.editorRedo = editorRedo;

})(window);
