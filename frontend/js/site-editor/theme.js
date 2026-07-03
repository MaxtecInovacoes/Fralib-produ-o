/*
 * Editor de Tema Global (G1)
 *
 * Le/escreve CSS variables do :root via API /api/sites/{lead_id}/theme.
 * Permite ao admin mudar paleta do site inteiro em 1 clique, sem rebuild.
 *
 * Dependencias:
 *   - window.csrfFetch (csrf-helper.js) — para POST/PUT com CSRF
 *   - window.AUTH_TOKEN — token JWT
 *   - editorCurrentLeadId — setado quando o editor abre
 */

(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  // Cor fallback (cinza) quando valor nao parseia
  var FALLBACK_COLOR = '#888888';
  var FALLBACK_RADIUS = '8px';

  // ─── Helpers ────────────────────────────────────────────────────────

  function setStatus(msg, kind) {
    var el = $('editorThemeStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.style.color = (kind === 'error') ? '#ef4444'
      : (kind === 'success') ? '#10b981'
      : '#8b8ba3';
  }

  function isValidHex(v) {
    return /^#[0-9a-fA-F]{3,8}$/.test(v);
  }

  function readColorInput(id, fallback) {
    var el = $(id);
    if (!el) return fallback;
    var v = (el.value || '').trim();
    return isValidHex(v) ? v : fallback;
  }

  function readTextInput(id, fallback) {
    var el = $(id);
    if (!el) return fallback;
    return (el.value || '').trim() || fallback;
  }

  function applyVarsToForm(vars) {
    if (!vars) return;
    if (vars['--color-primary']) $('editorThemePrimary').value = vars['--color-primary'];
    if (vars['--color-secondary']) $('editorThemeSecondary').value = vars['--color-secondary'];
    if (vars['--color-accent']) $('editorThemeAccent').value = vars['--color-accent'];
    if (vars['--color-bg']) $('editorThemeBg').value = vars['--color-bg'];
    if (vars['--color-text']) $('editorThemeText').value = vars['--color-text'];
    if (vars['--radius']) $('editorThemeRadius').value = vars['--radius'];
  }

  // ─── API ────────────────────────────────────────────────────────────

  function getLeadId() {
    return (typeof window.editorCurrentLeadId !== 'undefined' && window.editorCurrentLeadId)
      || (window.EDITOR_STATE && window.EDITOR_STATE.leadId)
      || null;
  }

  async function fetchWithCsrf(url, options) {
    options = options || {};
    if (window.csrfFetch) {
      return window.csrfFetch(url, Object.assign({ method: 'GET' }, options));
    }
    var token = window.AUTH_TOKEN || localStorage.getItem('auth_token') || '';
    return fetch(url, Object.assign({
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
      },
      credentials: 'include',
    }, options));
  }

  // ─── Public functions ───────────────────────────────────────────────

  window.editorLoadTheme = async function () {
    var leadId = getLeadId();
    if (!leadId) {
      setStatus('Abra o editor de um site antes de carregar o tema.', 'error');
      return;
    }
    setStatus('Carregando tema...', 'info');
    try {
      var resp = await fetchWithCsrf('/api/sites/' + encodeURIComponent(leadId) + '/theme');
      if (!resp.ok) {
        var err = await resp.text();
        setStatus('Erro: ' + (err || resp.status), 'error');
        return;
      }
      var data = await resp.json();
      applyVarsToForm(data.vars || {});
      setStatus('Tema carregado (' + Object.keys(data.vars || {}).length + ' vars).', 'success');
    } catch (e) {
      setStatus('Erro de rede: ' + (e && e.message || e), 'error');
    }
  };

  window.editorSaveTheme = async function () {
    var leadId = getLeadId();
    if (!leadId) {
      setStatus('Abra o editor de um site antes de aplicar o tema.', 'error');
      return;
    }
    var updates = {
      '--color-primary': readColorInput('editorThemePrimary', FALLBACK_COLOR),
      '--color-secondary': readColorInput('editorThemeSecondary', FALLBACK_COLOR),
      '--color-accent': readColorInput('editorThemeAccent', FALLBACK_COLOR),
      '--color-bg': readColorInput('editorThemeBg', FALLBACK_COLOR),
      '--color-text': readColorInput('editorThemeText', FALLBACK_COLOR),
      '--radius': readTextInput('editorThemeRadius', FALLBACK_RADIUS),
    };

    setStatus('Aplicando tema...', 'info');
    try {
      var resp = await fetchWithCsrf('/api/sites/' + encodeURIComponent(leadId) + '/theme', {
        method: 'PUT',
        body: JSON.stringify({ vars: updates }),
      });
      if (!resp.ok) {
        var errText = await resp.text();
        try {
          var errJson = JSON.parse(errText);
          setStatus('Erro: ' + (errJson.detail || errText), 'error');
        } catch (pe) {
          setStatus('Erro: ' + errText, 'error');
        }
        return;
      }
      var data = await resp.json();
      applyVarsToForm(data.vars || {});
      setStatus('Tema aplicado! ' + (data.updated || []).length + ' vars atualizadas.', 'success');

      // Recarregar iframe pra refletir mudanca
      try {
        var iframe = document.getElementById('editorIframe');
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.location.reload();
        }
      } catch (reloadErr) {
        // ignore cross-origin or detached
      }
    } catch (e) {
      setStatus('Erro de rede: ' + (e && e.message || e), 'error');
    }
  };

  // Carrega tema automaticamente quando o editor abrir (silencioso)
  document.addEventListener('DOMContentLoaded', function () {
    // Aguarda 500ms pra garantir que editorCurrentLeadId foi setado
    setTimeout(function () {
      if (getLeadId() && typeof window.editorLoadTheme === 'function') {
        // Silencioso — se falhar, nao incomoda
        window.editorLoadTheme();
      }
    }, 800);
  });
})();
