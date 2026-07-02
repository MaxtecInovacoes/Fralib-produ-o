/**
 * sdr-simulator.js — Card "Simulador Franz" no admin.
 *
 * Sprint 1.1: o admin pode digitar uma mensagem, mandar simular,
 * ver a resposta que o Franz daria, a intent detectada, o stage_after
 * do Kanban, a kanban_action resultante e as rules_applied.
 *
 * Persiste no backend via POST /api/admin/simulate. Histórico carregado
 * via GET /api/admin/simulations.
 *
 * @module admin/sdr-simulator
 */
(function () {
  'use strict';

  var HISTORY_LIMIT = 10;
  var $ = function (id) { return document.getElementById(id); };

  /**
   * Faz POST para /api/admin/simulate com token Bearer.
   * @param {Object} payload - { tenant_id?, message, history? }
   * @returns {Promise<Object>}
   */
  function callSimulateAPI(payload) {
    var token = window.AUTH_TOKEN || localStorage.getItem('auth_token') || '';
    return fetch('/api/admin/simulate', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? 'Bearer ' + token : ''
      },
      body: JSON.stringify(payload)
    }).then(function (resp) {
      if (!resp.ok) {
        return resp.text().then(function (t) {
          throw new Error('HTTP ' + resp.status + ' — ' + (t || resp.statusText));
        });
      }
      return resp.json();
    });
  }

  /**
   * Faz GET em /api/admin/simulations?limit=N.
   * @param {number} limit
   * @returns {Promise<Array>}
   */
  function callHistoryAPI(limit) {
    var token = window.AUTH_TOKEN || localStorage.getItem('auth_token') || '';
    return fetch('/api/admin/simulations?limit=' + (limit || HISTORY_LIMIT), {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Authorization': token ? 'Bearer ' + token : ''
      }
    }).then(function (resp) {
      if (!resp.ok) return [];
      return resp.json();
    }).catch(function () { return []; });
  }

  /**
   * Renderiza o card de resultado da simulação corrente.
   * @param {Object|null} result
   * @param {string|null} errorMessage
   */
  function renderResult(result, errorMessage) {
    var out = $('sdrSimulatorOutput');
    if (!out) return;
    if (errorMessage) {
      out.innerHTML =
        '<div style="padding:12px;border:1px solid rgba(239,68,68,.4);' +
        'background:rgba(239,68,68,.08);border-radius:8px;color:#ef4444;">' +
        'Erro: ' + escapeHtml(errorMessage) + '</div>';
      return;
    }
    if (!result) {
      out.innerHTML = '';
      return;
    }
    var meta = [
      ['Intent', result.intent],
      ['Stage after', result.stage_after],
      ['Kanban action', result.kanban_action],
      ['Latência', (result.latency_ms || 0) + ' ms'],
      ['ID', result.id]
    ];
    var metaHtml = meta.map(function (kv) {
      return '<div style="display:flex;gap:8px;align-items:center;">' +
        '<span style="font-size:11px;color:var(--fl-text-muted,' +
        "'#888'" + ');min-width:90px;text-transform:uppercase;letter-spacing:.04em;">' +
        escapeHtml(kv[0]) + '</span>' +
        '<span style="font-family:var(--fl-font-mono,monospace);font-size:12px;">' +
        escapeHtml(kv[1] == null ? '—' : String(kv[1])) + '</span>' +
        '</div>';
    }).join('');

    var rules = (result.rules_applied || []).map(function (r) {
      return '<span style="display:inline-block;padding:2px 8px;background:rgba(56,189,248,.12);' +
        'border:1px solid rgba(56,189,248,.3);border-radius:6px;font-size:11px;' +
        'margin-right:4px;margin-bottom:4px;">' + escapeHtml(r) + '</span>';
    }).join('');

    out.innerHTML =
      '<div style="padding:14px;background:rgba(16,185,129,.06);' +
      'border:1px solid rgba(16,185,129,.25);border-radius:10px;">' +
      '<div style="font-size:11px;color:var(--fl-text-muted,#888);text-transform:uppercase;' +
      'letter-spacing:.06em;margin-bottom:6px;">Resposta do Franz</div>' +
      '<div style="font-size:14px;line-height:1.5;white-space:pre-wrap;margin-bottom:12px;">' +
      escapeHtml(result.response || '(vazio)') + '</div>' +
      '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));' +
      'gap:6px 14px;padding-top:10px;border-top:1px dashed rgba(255,255,255,.08);">' +
      metaHtml + '</div>' +
      (rules
        ? '<div style="margin-top:12px;"><div style="font-size:11px;color:var(--fl-text-muted,#888);' +
          'text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Regras aplicadas</div>' +
          '<div>' + rules + '</div></div>'
        : '') +
      '</div>';
  }

  /**
   * Renderiza o histórico de simulações.
   * @param {Array} items
   */
  function renderHistory(items) {
    var host = $('sdrSimulatorHistory');
    if (!host) return;
    if (!items || !items.length) {
      host.innerHTML = '<div style="font-size:12px;color:var(--fl-text-muted,#888);' +
        'padding:8px 0;">Nenhuma simulação anterior.</div>';
      return;
    }
    host.innerHTML = items.map(function (it) {
      var when = it.criado_em ? new Date(it.criado_em).toLocaleString('pt-BR') : '';
      return '<div style="padding:10px 12px;background:rgba(255,255,255,.02);' +
        'border:1px solid rgba(255,255,255,.06);border-radius:8px;margin-bottom:6px;">' +
        '<div style="font-size:11px;color:var(--fl-text-muted,#888);' +
        'display:flex;justify-content:space-between;margin-bottom:4px;">' +
        '<span>' + escapeHtml(when) + '</span>' +
        '<span>' + escapeHtml(it.intent || '—') + ' · ' +
        escapeHtml(it.stage_after || '—') + ' · ' +
        (it.latency_ms || 0) + 'ms</span></div>' +
        '<div style="font-size:13px;color:var(--fl-text,#fff);white-space:nowrap;' +
        'overflow:hidden;text-overflow:ellipsis;">' +
        '<strong>Lead:</strong> ' + escapeHtml((it.message || '').slice(0, 120)) + '</div>' +
        '<div style="font-size:12px;color:#10b981;margin-top:2px;white-space:nowrap;' +
        'overflow:hidden;text-overflow:ellipsis;">' +
        '<strong>Franz:</strong> ' + escapeHtml((it.response || '').slice(0, 120)) + '</div>' +
        (it.kanban_action
          ? '<div style="font-size:11px;color:#38bdf8;margin-top:2px;">→ ' +
            escapeHtml(it.kanban_action) + '</div>'
          : '') +
        '</div>';
    }).join('');
  }

  /**
   * Submete o que está digitado no textarea.
   */
  function onSubmit() {
    var msgEl = $('sdrSimulatorMessage');
    var btn = $('sdrSimulatorSubmit');
    var historyEl = $('sdrSimulatorHistory');
    var msg = (msgEl && msgEl.value || '').trim();
    if (!msg) {
      msgEl && msgEl.focus();
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Simulando…';
    renderResult(null, null);

    var history = parseHistoryFromTextarea();

    callSimulateAPI({ message: msg, history: history })
      .then(function (result) {
        renderResult(result, null);
        return callHistoryAPI(HISTORY_LIMIT);
      })
      .then(function (items) { renderHistory(items); })
      .catch(function (err) {
        renderResult(null, err && err.message ? err.message : String(err));
      })
      .then(function () {
        btn.disabled = false;
        btn.textContent = 'Testar mensagem';
      });
  }

  /**
   * Lê textarea opcional de histórico (linhas no formato "user: ..." / "lead: ..." / "franz: ...").
   * @returns {Array<{role:string,content:string}>}
   */
  function parseHistoryFromTextarea() {
    var el = $('sdrSimulatorHistoryInput');
    if (!el) return [];
    var raw = (el.value || '').split('\n');
    var out = [];
    for (var i = 0; i < raw.length; i++) {
      var line = raw[i].trim();
      if (!line) continue;
      var idx = line.indexOf(':');
      if (idx <= 0) {
        out.push({ role: 'user', content: line });
        continue;
      }
      var prefix = line.slice(0, idx).trim().toLowerCase();
      var content = line.slice(idx + 1).trim();
      if (!content) continue;
      var role = 'user';
      if (prefix === 'franz' || prefix === 'assistant' || prefix === 'bot') role = 'assistant';
      else if (prefix === 'lead' || prefix === 'user' || prefix === 'humano') role = 'user';
      out.push({ role: role, content: content });
      if (out.length >= 20) break;
    }
    return out;
  }

  /**
   * Escapa texto para inserção em HTML.
   * @param {string} text
   * @returns {string}
   */
  function escapeHtml(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Carrega histórico e faz bind dos handlers.
   */
  function load_simulator() {
    var btn = $('sdrSimulatorSubmit');
    if (btn) btn.addEventListener('click', onSubmit);
    var ta = $('sdrSimulatorMessage');
    if (ta) {
      ta.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); onSubmit(); }
      });
    }
    callHistoryAPI(HISTORY_LIMIT).then(renderHistory).catch(function () {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load_simulator);
  } else {
    load_simulator();
  }

  // Expor para testes manuais / console
  window.SDR_SIMULATOR = {
    callSimulateAPI: callSimulateAPI,
    callHistoryAPI: callHistoryAPI,
    renderResult: renderResult,
    renderHistory: renderHistory
  };
})();