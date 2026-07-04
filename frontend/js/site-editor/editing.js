/* site-editor/editing.js — Text editing, selection, element classification, inspector panel */
(function(global){
  'use strict';

  var state = global.state;
  var $ = global.$;
  var escapeText = global.escapeText;
  var status = global.status;
  var setDirty = global.setDirty;

  function getIframeDoc(){ return global.getIframeDoc(); }

  function isTextOnly(el){
    return Array.prototype.every.call(el.childNodes, function(n){
      return n.nodeType === 3 || (n.nodeType === 1 && /^(BR|STRONG|EM|SPAN|A|B|I|U|SMALL)$/i.test(n.tagName));
    });
  }

  function bindEditableText(doc){
    doc.querySelectorAll(global.TEXT_SELECTOR).forEach(function(el){
      if(el.closest('script,style,noscript,template')) return;
      if(!isTextOnly(el)) return;
      el.contentEditable = 'true';
      el.setAttribute('spellcheck','false');
      el.addEventListener('focus', function(){ global.selecionarElemento(el); });
      el.addEventListener('input', function(){
        setDirty(true);
        global.syncInspectorFromSelected();
        global.scheduleSnapshot();
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
        global.selecionarElemento(selectable);
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
    state.selectedKind = global.classifyElement(el);
    global.renderInspector(el);
    global.renderSelectedPath(el);
    global.renderImages();
    global.renderSections();
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
        '<div class="editor-row" style="margin-bottom:12px"><span class="editor-row-main"><span class="editor-row-title">' + escapeText(tag.toUpperCase()) + '</span><span class="editor-row-sub">' + escapeText(global.classifyElement(el)) + '</span></span></div>' +
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
    global.renderSelectedPath(el);
    global.scheduleSnapshot();
  }

  function editorUpdateSelectedAttr(attr, value){
    var el = getSelected();
    if(!el) return;
    if(value) el.setAttribute(attr, value);
    else el.removeAttribute(attr);
    setDirty(true);
    global.renderSelectedPath(el);
    global.scheduleSnapshot();
    global.renderImages();
  }

  function editorApplyStyle(prop, value){
    var el = getSelected();
    if(!el || !prop) return;
    el.style[prop] = value;
    setDirty(true);
    global.scheduleSnapshot();
    global.renderInspector(el);
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
    global.scheduleSnapshot();
    global.renderInspector(el);
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
    global.scheduleSnapshot();
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
    global.scheduleSnapshot();
    global.renderInspector(el);
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
    global.scheduleSnapshot();
    global.renderImages();
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
    global.selecionarElemento(logo);
    setDirty(true);
    global.scheduleSnapshot();
    global.renderImages();
    status('Logo atualizado no preview.', false);
  }

  function syncInspectorFromSelected(){
    var el = getSelected();
    if(!el) return;
    var input = $('editorSelectedText');
    if(input && document.activeElement !== input) input.value = (el.textContent || '').trim();
    global.renderSelectedPath(el);
  }

  /* ── Exports ── */
  global.bindEditableText = bindEditableText;
  global.bindCanvasEvents = bindCanvasEvents;
  global.getSelected = getSelected;
  global.selecionarElemento = selecionarElemento;
  global.classifyElement = classifyElement;
  global.elementLabel = elementLabel;
  global.renderSelectedPath = renderSelectedPath;
  global.renderInspector = renderInspector;
  global.getComputedStyleSafe = getComputedStyleSafe;
  global.rgbToHex = rgbToHex;
  global.editorSetTab = editorSetTab;
  global.cap = cap;
  global.editorSetDevice = editorSetDevice;
  global.editorUpdateSelectedText = editorUpdateSelectedText;
  global.editorUpdateSelectedAttr = editorUpdateSelectedAttr;
  global.editorApplyStyle = editorApplyStyle;
  global.editorApplyPalette = editorApplyPalette;
  global.readableTextOn = readableTextOn;
  global.editorApplyGlobalAccent = editorApplyGlobalAccent;
  global.editorApplyQuickStyle = editorApplyQuickStyle;
  global.editorUpdateSelectedImage = editorUpdateSelectedImage;
  global.editorApplyLogo = editorApplyLogo;
  global.syncInspectorFromSelected = syncInspectorFromSelected;

})(window);
