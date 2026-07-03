/**
 * sdr-personalization.js — UI "🤖 Configurar Franz" (Sprint 1.3).
 *
 * Sistema de 3 tabs (Básico / Avançado / Base de conhecimento) onde cada
 * campo personalizável tem toggle "Personalizar" e botão "Restaurar nativo".
 *
 * Quando o toggle está OFF → usa o valor nativo do motor FraLib (campo disabled).
 * Quando está ON → campo editável + valor persistido em /api/users/sdr-config.
 *
 * Integra com o card "Simulador Franz" do Sprint 1.1 via scrollIntoView
 * no botão "Testar no simulador".
 *
 * Endpoint backend: /api/users/sdr-config (já existe via users_endpoints.py).
 *
 * @module admin/sdr-personalization
 */

(function () {
  'use strict';

  /** Tamanho máximo da base de conhecimento (espelha MAX_CUSTOM_KNOWLEDGE_CHARS). */
  var MAX_CUSTOM_KNOWLEDGE_CHARS = 8000;

  /** Campos personalizáveis → mapeamento para chave do payload do backend. */
  var FIELD_MAP = {
    sdrPersAgentName:        { key: 'agent_name',       default: 'Franz' },
    sdrPersAgentSignature:   { key: 'agent_signature',  default: '' },
    sdrPersTone:             { key: 'personality',      default: '' },
    sdrPersAllowedActions:   { key: 'allowed_actions',  default: [], isList: true },
    sdrPersBlockedActions:   { key: 'blocked_actions',  default: [], isList: true },
    sdrPersHandoffTriggers:  { key: 'handoff.triggers', default: [], isList: true, wrap: 'handoff' },
    sdrPersHandoffNote:      { key: 'handoff.note',     default: '',   wrap: 'handoff' },
    sdrPersCustomKnowledge:  { key: 'custom_knowledge', default: '' }
  };

  /** Aliases de DOM usados no UI para evitar typos. */
  var $ = function (id) { return document.getElementById(id); };

  /**
   * Faz request autenticado para /api/users/sdr-config.
   * Reutiliza authFetch se existir (injetado pelo admin); senão usa fetch.
   *
   * @param {string} method - 'GET' ou 'PUT'
   * @param {Object|null} body
   * @returns {Promise<Object>}
   */
  function callSdrConfigAPI(method, body) {
    method = (method || 'GET').toUpperCase();
    var url = '/api/users/sdr-config' + (method === 'GET' ? '?_=' + Date.now() : '');
    var opts = {
      method: method,
      cache: 'no-store',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);

    var fetcher = (typeof window.authFetch === 'function')
      ? window.authFetch
      : function (u, o) {
          var token = window.AUTH_TOKEN || localStorage.getItem('auth_token') || '';
          o = o || {};
          o.headers = o.headers || {};
          if (token) o.headers['Authorization'] = 'Bearer ' + token;
          return fetch(u, o);
        };

    return fetcher(url, opts).then(function (resp) {
      if (!resp.ok) {
        return resp.text().then(function (t) {
          throw new Error('HTTP ' + resp.status + ' — ' + (t || resp.statusText));
        });
      }
      return resp.json();
    });
  }

  /**
   * Ativa/desativa o toggle "Personalizar" de um campo.
   * Quando OFF: campo desabilitado + valor aparente some (placeholder indica nativo).
   * Quando ON: campo editável.
   *
   * @param {string} fieldId - id do campo personalizável (chave em FIELD_MAP)
   * @returns {void}
   */
  function togglePersonalizar(fieldId) {
    var meta = FIELD_MAP[fieldId];
    if (!meta) return;
    var toggleEl = document.querySelector('.sdr-pers-toggle[data-target="' + fieldId + '"]');
    var inputEl  = $(fieldId);
    if (!toggleEl || !inputEl) return;

    var on = !!toggleEl.checked;
    inputEl.disabled = !on;
    if (on) {
      inputEl.removeAttribute('readonly');
      inputEl.dataset.personalized = '1';
    } else {
      inputEl.dataset.personalized = '0';
      // Restaura placeholder nativo representativo (sem mexer em valor já salvo).
      inputEl.value = meta.isList ? '' : (typeof meta.default === 'string' ? meta.default : '');
    }
    atualizarPreview();
  }

  /**
   * "Restaurar nativo" por campo: desliga o toggle e limpa o valor,
   * sinalizando ao backend que o tenant não quer personalizar este campo.
   *
   * @param {string} fieldId - id do campo
   * @returns {void}
   */
  function restaurarNativo(fieldId) {
    var meta = FIELD_MAP[fieldId];
    if (!meta) return;
    var toggleEl = document.querySelector('.sdr-pers-toggle[data-target="' + fieldId + '"]');
    var inputEl  = $(fieldId);
    if (!toggleEl || !inputEl) return;
    toggleEl.checked = false;
    inputEl.disabled = true;
    inputEl.dataset.personalized = '0';
    inputEl.value = meta.isList ? '' : (typeof meta.default === 'string' ? meta.default : '');
    atualizarPreview();
  }

  /**
   * Liga togglePersonalizar e restaurarNativo a TODOS os campos configurados.
   *
   * @returns {void}
   */
  function bindHandlers() {
    Object.keys(FIELD_MAP).forEach(function (fieldId) {
      var toggleEl = document.querySelector('.sdr-pers-toggle[data-target="' + fieldId + '"]');
      if (toggleEl) {
        toggleEl.addEventListener('change', function () { togglePersonalizar(fieldId); });
      }
      var restoreBtn = document.querySelector('.sdr-pers-restore[data-target="' + fieldId + '"]');
      if (restoreBtn) {
        restoreBtn.addEventListener('click', function () { restaurarNativo(fieldId); });
      }
      var inputEl = $(fieldId);
      if (inputEl) {
        inputEl.addEventListener('input', atualizarPreview);
      }
    });
  }

  /**
   * Ativa/desativa tabs.
   *
   * @param {string} tabKey - 'basico' | 'avancado' | 'base'
   * @returns {void}
   */
  function ativarTab(tabKey) {
    ['basico', 'avancado', 'base'].forEach(function (k) {
      var tab = document.querySelector('.sdr-pers-tab[data-tab="' + k + '"]');
      var panel = document.querySelector('.sdr-pers-panel[data-panel="' + k + '"]');
      if (!tab || !panel) return;
      var active = (k === tabKey);
      tab.classList.toggle('sdr-pers-tab--active', active);
      panel.style.display = active ? '' : 'none';
    });
  }

  /**
   * Liga click nas tabs e carrega listeners de teclado (Esc fecha preview).
   *
   * @returns {void}
   */
  function bindTabs() {
    var tabs = document.querySelectorAll('.sdr-pers-tab');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        ativarTab(tab.getAttribute('data-tab'));
      });
    });
  }

  /**
   * Lê uma string de textarea e devolve lista por linha.
   *
   * @param {string} fieldId
   * @returns {string[]}
   */
  function readLines(fieldId) {
    var el = $(fieldId);
    if (!el) return [];
    return (el.value || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  }

  /**
   * Seta valor de um campo (string) — respeitando estado de disabled.
   *
   * @param {string} id
   * @param {string} value
   * @returns {void}
   */
  function setFieldValue(id, value) {
    var el = $(id);
    if (!el) return;
    el.value = (value == null ? '' : String(value));
  }

  /**
   * Seta valor de um campo lista (uma linha por item).
   *
   * @param {string} id
   * @param {string[]} arr
   * @returns {void}
   */
  function setLinesField(id, arr) {
    setFieldValue(id, Array.isArray(arr) ? arr.join('\n') : '');
  }

  /**
   * Liga o estado do toggle a partir do payload: se o tenant personalizou
   * o campo (valor ≠ nativo esperado), checked=true; senão, false.
   *
   * @param {string} fieldId
   * @param {string} currentValue
   * @returns {boolean} se o toggle ficou marcado
   */
  function applyToggleFromValue(fieldId, currentValue) {
    var meta = FIELD_MAP[fieldId];
    if (!meta) return false;
    var toggleEl = document.querySelector('.sdr-pers-toggle[data-target="' + fieldId + '"]');
    var inputEl  = $(fieldId);
    if (!toggleEl || !inputEl) return false;
    var hasValue = Array.isArray(currentValue) ? currentValue.length > 0 : !!currentValue;
    toggleEl.checked = hasValue;
    inputEl.disabled = !hasValue;
    inputEl.dataset.personalized = hasValue ? '1' : '0';
    return hasValue;
  }

  /**
   * Aplica settings carregadas na UI: preenche campos e toggles.
   *
   * @param {Object} cfg - payload do backend
   * @returns {void}
   */
  function applyConfig(cfg) {
    if (!cfg || typeof cfg !== 'object') cfg = {};
    var handoff = cfg.handoff || {};

    setFieldValue('sdrPersAgentName', cfg.agent_name);
    applyToggleFromValue('sdrPersAgentName', cfg.agent_name && cfg.agent_name !== 'Franz');
    setFieldValue('sdrPersAgentSignature', cfg.agent_signature);
    applyToggleFromValue('sdrPersAgentSignature', cfg.agent_signature);
    setFieldValue('sdrPersTone', cfg.personality);
    applyToggleFromValue('sdrPersTone', cfg.personality);

    setLinesField('sdrPersAllowedActions', cfg.allowed_actions);
    applyToggleFromValue('sdrPersAllowedActions', cfg.allowed_actions);
    setLinesField('sdrPersBlockedActions', cfg.blocked_actions);
    applyToggleFromValue('sdrPersBlockedActions', cfg.blocked_actions);

    setLinesField('sdrPersHandoffTriggers', handoff.triggers);
    applyToggleFromValue('sdrPersHandoffTriggers', handoff.triggers);
    setFieldValue('sdrPersHandoffNote', handoff.note);
    applyToggleFromValue('sdrPersHandoffNote', handoff.note);

    setFieldValue('sdrPersCustomKnowledge', cfg.custom_knowledge);
    applyToggleFromValue('sdrPersCustomKnowledge', cfg.custom_knowledge);

    atualizarContadorBase();
    atualizarPreview();
  }

  /**
   * Atualiza o contador regressivo do textarea de Base de conhecimento.
   *
   * @returns {void}
   */
  function atualizarContadorBase() {
    var ta = $('sdrPersCustomKnowledge');
    var counter = $('sdrPersCharCounter');
    if (!ta || !counter) return;
    var len = (ta.value || '').length;
    counter.textContent = (MAX_CUSTOM_KNOWLEDGE_CHARS - len) + ' restantes (máx ' + MAX_CUSTOM_KNOWLEDGE_CHARS + ')';
  }

  /**
   * Atualiza o preview do system prompt final calculado localmente
   * (espelha build_sdr_system_prompt do backend de forma simplificada —
   * o runtime real é montado pelo Franz em produção).
   *
   * @returns {void}
   */
  function atualizarPreview() {
    var preview = $('sdrPersPromptPreview');
    if (!preview) return;
    atualizarContadorBase();

    var name = ($('sdrPersAgentName') || {}).value || 'Franz';
    var sig  = ($('sdrPersAgentSignature') || {}).value || '';
    var tone = ($('sdrPersTone') || {}).value || '';
    var allowed = readLines('sdrPersAllowedActions');
    var blocked = readLines('sdrPersBlockedActions');
    var triggers = readLines('sdrPersHandoffTriggers');
    var handoffNote = ($('sdrPersHandoffNote') || {}).value || '';
    var knowledge = ($('sdrPersCustomKnowledge') || {}).value || '';

    var bloco = [];
    bloco.push('# SYSTEM PROMPT — ' + name);
    if (sig) bloco.push('Assinatura: ' + sig);
    if (tone) bloco.push('\n## Personalidade\n' + tone);
    if (allowed.length) bloco.push('\n## Pode fazer\n- ' + allowed.join('\n- '));
    if (blocked.length) bloco.push('\n## Nao pode\n- ' + blocked.join('\n- '));
    if (triggers.length || handoffNote) {
      bloco.push('\n## Handoff');
      if (triggers.length) bloco.push('Gatilhos: ' + triggers.join(' | '));
      if (handoffNote) bloco.push('Nota: ' + handoffNote);
    }
    if (knowledge) {
      var snippet = knowledge.length > 1200 ? knowledge.slice(0, 1200) + '...' : knowledge;
      bloco.push('\n## Base de conhecimento\n' + snippet);
    }
    bloco.push('\n--- (preview local; runtime real montado por build_sdr_system_prompt) ---');
    preview.value = bloco.join('\n');
  }

  /**
   * GET /api/users/sdr-config e aplica na UI.
   *
   * @returns {Promise<void>}
   */
  function carregarPersonalizacao() {
    var statusEl = $('sdrPersStatus');
    if (statusEl) statusEl.textContent = 'Carregando personalizacao...';
    return callSdrConfigAPI('GET').then(function (cfg) {
      applyConfig(cfg);
      if (statusEl) statusEl.textContent = 'Personalizacao carregada.';
    }).catch(function (err) {
      if (statusEl) statusEl.textContent = 'Falha: ' + (err && err.message ? err.message : err);
    });
  }

  /**
   * Monta payload do backend a partir da UI. Apenas campos com
   * toggle ON (dataset.personalized='1') sao enviados como override;
   * campos nativos permanecem no default do servidor.
   *
   * @returns {Object}
   */
  function buildPayload() {
    function val(fieldId) {
      var el = $(fieldId);
      if (!el) return '';
      if (el.dataset && el.dataset.personalized === '1') return el.value;
      // Nao personalizado: nao envia override
      return undefined;
    }
    function lines(fieldId) {
      var el = $(fieldId);
      if (!el) return undefined;
      if (el.dataset && el.dataset.personalized === '1') {
        return (el.value || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
      }
      return undefined;
    }

    var payload = {};
    var nameVal = val('sdrPersAgentName');
    if (nameVal !== undefined) payload.agent_name = nameVal;
    var sigVal = val('sdrPersAgentSignature');
    if (sigVal !== undefined) payload.agent_signature = sigVal;
    var personalityVal = val('sdrPersTone');
    if (personalityVal !== undefined) payload.personality = personalityVal;

    var allowed = lines('sdrPersAllowedActions');
    if (allowed !== undefined) payload.allowed_actions = allowed;
    var blocked = lines('sdrPersBlockedActions');
    if (blocked !== undefined) payload.blocked_actions = blocked;

    var triggers = lines('sdrPersHandoffTriggers');
    var noteVal = val('sdrPersHandoffNote');
    if (triggers !== undefined || noteVal !== undefined) {
      payload.handoff = {
        enabled: true,
        triggers: triggers || [],
        note: noteVal || ''
      };
    }

    var knowledgeVal = val('sdrPersCustomKnowledge');
    if (knowledgeVal !== undefined) payload.custom_knowledge = knowledgeVal;

    return payload;
  }

  /**
   * PUT /api/users/sdr-config com o payload construido.
   *
   * @returns {Promise<Object>}
   */
  function salvarPersonalizacao() {
    var payload = buildPayload();
    var statusEl = $('sdrPersStatus');
    var btn = $('sdrPersSaveBtn');
    if (statusEl) statusEl.textContent = 'Salvando personalizacao...';
    if (btn) { btn.disabled = true; btn.textContent = 'SALVANDO...'; }
    return callSdrConfigAPI('PUT', payload).then(function (data) {
      if (statusEl) statusEl.textContent = 'Personalizacao salva.';
      return data;
    }).catch(function (err) {
      if (statusEl) statusEl.textContent = 'Falha ao salvar: ' + (err && err.message ? err.message : err);
      throw err;
    }).then(function (data) {
      return carregarPersonalizacao().then(function () { return data; });
    }).finally(function () {
      if (btn) { btn.disabled = false; btn.textContent = 'SALVAR PERSONALIZACAO'; }
    });
  }

  /**
   * Integra com o card Simulador Franz do Sprint 1.1: leva o admin
   * até o simulador com um scroll suave e foco no textarea de mensagem.
   *
   * @returns {void}
   */
  function testarNoSimulador() {
    // Card agora vive na view 'agents' (aba separada). Navega primeiro.
    if (typeof mostrarView === 'function') {
      mostrarView('agents');
    }
    setTimeout(function () {
      var card = $('sdrSimulatorCard');
      if (card && typeof card.scrollIntoView === 'function') {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      var msg = $('sdrSimulatorMessage');
      if (msg) {
        // valor exemplo para evitar simulação em branco
        if (!msg.value) msg.value = 'Oi, me conta mais sobre o que vocês fazem?';
        msg.focus();
      }
    }, 250);
  }

  /**
   * Inicializa bindings (handlers de input, tabs, botões).
   *
   * @returns {void}
   */
  function init() {
    bindHandlers();
    bindTabs();
    ativarTab('basico');
    var testBtn = $('sdrPersTestSimulator');
    if (testBtn) testBtn.addEventListener('click', testarNoSimulador);
    var saveBtn = $('sdrPersSaveBtn');
    if (saveBtn) saveBtn.addEventListener('click', function () { salvarPersonalizacao(); });

    // Carregamento automático se a UI já estiver montada.
    carregarPersonalizacao();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expor para testes/console
  window.SDR_PERSONALIZATION = {
    carregarPersonalizacao: carregarPersonalizacao,
    salvarPersonalizacao: salvarPersonalizacao,
    togglePersonalizar: togglePersonalizar,
    restaurarNativo: restaurarNativo,
    atualizarPreview: atualizarPreview,
    buildPayload: buildPayload,
    applyConfig: applyConfig,
    testarNoSimulador: testarNoSimulador
  };
})();
