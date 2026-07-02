/**
 * FraLib Admin - Phone Health Module
 *
 * Card de saúde do número WhatsApp por tenant (Trilha A).
 * Consome GET /api/admin/phone-health e renderiza:
 *   - Score 0-100 com cor por status
 *   - Badge de status (healthy/degraded/restricted/banned)
 *   - 3 métricas 24h: events / DLQ / opt-outs
 *   - Recommendation textual automática
 *   - Botão "Pausar Franz" (emergência)
 *
 * Auto-refresh a cada 5 min. Refetch on demand.
 *
 * @module phone-health
 */

/* ══ STATE ════════════════════════════════════════════════════════════ */

/** @type {PhoneHealthResponse | null} */
var _phoneHealthState = null;

/** @type {number | null} */
var _phoneHealthPoll = null;

var PHONE_HEALTH_REFRESH_MS = 5 * 60 * 1000; // 5 min

/* ══ TYPES (JSDoc) ════════════════════════════════════════════════════ */

/**
 * @typedef {('healthy'|'degraded'|'restricted'|'banned')} PhoneHealthStatus
 */

/**
 * @typedef {Object} PhoneHealthSignals
 * @property {number} events_24h
 * @property {number} dlq_24h
 * @property {number} optouts_24h
 */

/**
 * @typedef {Object} PhoneHealthEvent
 * @property {number} id
 * @property {('info'|'warn'|'error'|'critical')} severity
 * @property {string} event_type
 * @property {string=} criado_em
 */

/**
 * @typedef {Object} PhoneHealthResponse
 * @property {number} user_id
 * @property {number} score
 * @property {PhoneHealthStatus} status
 * @property {PhoneHealthSignals} signals
 * @property {(string|null)} ultima_restricao_em
 * @property {(string|null)} pause_franz_until
 * @property {(string|null)} atualizado_em
 * @property {PhoneHealthEvent[]} events
 * @property {string} recommendation
 */

/* ══ HELPERS ═══════════════════════════════════════════════════════════ */

/**
 * @param {string} id
 * @param {string} value
 * @returns {void}
 */
function _phSetText(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = String(value);
}

/**
 * @param {string} id
 * @param {string} value
 * @returns {void}
 */
function _phSetHtml(id, value) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

/**
 * @param {string} id
 * @param {string} display
 * @returns {void}
 */
function _phSetDisplay(id, display) {
  var el = document.getElementById(id);
  if (el) el.style.display = display;
}

/**
 * @param {string} status
 * @returns {string} Cor CSS (var)
 */
function _phStatusColor(status) {
  switch (status) {
    case 'healthy':   return 'var(--success, #10b981)';
    case 'degraded':  return 'var(--warning, #f59e0b)';
    case 'restricted': return 'var(--danger, #ef4444)';
    case 'banned':    return 'var(--critical, #b91c1c)';
    default:          return 'var(--fl-text-muted, #94a3b8)';
  }
}

/**
 * @param {string} status
 * @returns {string} Label PT-BR
 */
function _phStatusLabel(status) {
  switch (status) {
    case 'healthy':   return 'Saudável';
    case 'degraded':  return 'Degradado';
    case 'restricted': return 'Restrito';
    case 'banned':    return 'Banido';
    default:          return status || 'desconhecido';
  }
}

function _phEffectiveLimit(score) {
  var n = Number(score);
  var base = 50;
  var factor = 1.0;
  if (!Number.isNaN(n)) {
    if (n >= 80) factor = 1.0;
    else if (n >= 50) factor = 0.7;
    else if (n >= 20) factor = 0.5;
    else factor = 0.1;
  }
  return Math.max(1, Math.floor(base * factor));
}

/**
 * @param {string|null} isoDate
 * @returns {string}
 */
function _phFormatDate(isoDate) {
  if (!isoDate) return '—';
  try {
    var d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  } catch (_e) {
    return '—';
  }
}

/**
 * @param {unknown} err
 * @returns {string}
 */
function _phGetErrorMessage(err) {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return 'Erro inesperado';
}

/* ══ RENDER ═══════════════════════════════════════════════════════════ */

/**
 * Renderiza o card a partir de _phoneHealthState.
 * @returns {void}
 */
function renderPhoneHealth() {
  var card = document.getElementById('phoneHealthCard');
  var sdrWidget = document.getElementById('sdrPhoneHealthWidget');
  if (!card && !sdrWidget) return;

  if (!_phoneHealthState) {
    _phSetHtml('phoneHealthBody', '<div class="ph-loading">Carregando saúde do número…</div>');
    return;
  }

  var state = _phoneHealthState;
  var color = _phStatusColor(state.status);
  var label = _phStatusLabel(state.status);
  var signals = state.signals || { events_24h: 0, dlq_24h: 0, optouts_24h: 0 };

  if (card) {
    _phSetText('phoneHealthSync', 'ok');
    _phSetText('phoneHealthScore', String(state.score));
    _phSetHtml('phoneHealthScore', '<span style="color:' + color + ';">' + state.score + '</span>');
    _phSetText('phoneHealthStatus', label);
    var badge = document.getElementById('phoneHealthStatus');
    if (badge) {
      badge.style.background = color;
      badge.style.color = '#fff';
    }
    _phSetText('phoneHealthEvents', String(signals.events_24h || 0));
    _phSetText('phoneHealthDlq', String(signals.dlq_24h || 0));
    _phSetText('phoneHealthOptouts', String(signals.optouts_24h || 0));
    _phSetText('phoneHealthRecommendation', state.recommendation || '—');
    _phSetText('phoneHealthUpdatedAt', 'Atualizado: ' + _phFormatDate(state.atualizado_em));

    var restricaoEl = document.getElementById('phoneHealthLastRestricao');
    if (restricaoEl) {
      if (state.ultima_restricao_em) {
        restricaoEl.textContent = 'Última restrição: ' + _phFormatDate(state.ultima_restricao_em);
        restricaoEl.style.display = 'block';
      } else {
        restricaoEl.style.display = 'none';
      }
    }

    var pauseIndicator = document.getElementById('phoneHealthPausedIndicator');
    if (pauseIndicator) {
      if (state.pause_franz_until) {
        var until = _phFormatDate(state.pause_franz_until);
        pauseIndicator.innerHTML = '⏸ <strong>Franz pausado</strong> até ' + until;
        pauseIndicator.style.display = 'block';
      } else {
        pauseIndicator.style.display = 'none';
      }
    }

    _phSetDisplay('phoneHealthLoading', 'none');
    _phSetDisplay('phoneHealthBody', 'block');
  }

  if (sdrWidget) {
    _phSetText('sdrPhoneHealthSync', _phFormatDate(state.atualizado_em));
    _phSetHtml('sdrPhoneHealthScore', '<span style="color:' + color + ';">' + state.score + '</span>');
    _phSetHtml('sdrPhoneHealthStatus', '<span style="color:' + color + ';">' + label + '</span>');
    _phSetText('sdrPhoneHealthEffectiveLimit', _phEffectiveLimit(state.score) + ' msgs/lead');
  }
}

/* ══ FETCH ════════════════════════════════════════════════════════════ */

/**
 * Busca saúde atual. Atualiza _phoneHealthState e re-renderiza.
 * @returns {Promise<void>}
 */
async function loadPhoneHealth() {
  try {
    var resp = await authFetch('/api/admin/phone-health');
    if (!resp.ok) {
      _phSetHtml('phoneHealthBody', '<div class="ph-error">Erro ao carregar (HTTP ' + resp.status + ')</div>');
      _phSetText('phoneHealthSync', 'erro HTTP ' + resp.status);
      _phSetText('sdrPhoneHealthSync', 'erro HTTP ' + resp.status);
      return;
    }
    var data = await resp.json();
    _phoneHealthState = data;
    renderPhoneHealth();
  } catch (err) {
    _phSetHtml('phoneHealthBody', '<div class="ph-error">Erro: ' + _phGetErrorMessage(err) + '</div>');
    _phSetText('phoneHealthSync', 'erro');
    _phSetText('sdrPhoneHealthSync', 'erro');
  }
}

/**
 * Força refresh manual (botão "Atualizar").
 * @returns {Promise<void>}
 */
async function refreshPhoneHealth() {
  await loadPhoneHealth();
}

/**
 * Pausa o Franz por N horas (emergência).
 * @param {number} [hours=24]
 * @returns {Promise<void>}
 */
async function pausePhoneHealth(hours) {
  var h = hours || 24;
  if (!confirm('Pausar o Franz por ' + h + 'h? O atendimento automático ficará suspenso.')) {
    return;
  }
  try {
    var resp = await authFetch('/api/admin/phone-health/pause?hours=' + h, {
      method: 'POST',
    });
    if (!resp.ok) {
      alert('Erro ao pausar (HTTP ' + resp.status + ')');
      return;
    }
    await loadPhoneHealth();
  } catch (err) {
    alert('Erro: ' + _phGetErrorMessage(err));
  }
}

/**
 * Inicia polling automático (5 min).
 * @returns {void}
 */
function startPhoneHealthPolling() {
  if (_phoneHealthPoll) return;
  _phoneHealthPoll = window.setInterval(loadPhoneHealth, PHONE_HEALTH_REFRESH_MS);
}

/**
 * Para polling.
 * @returns {void}
 */
function stopPhoneHealthPolling() {
  if (_phoneHealthPoll) {
    window.clearInterval(_phoneHealthPoll);
    _phoneHealthPoll = null;
  }
}

/* ══ INIT ════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
  // Carrega + inicia polling se o card existir no DOM
  if (document.getElementById('phoneHealthCard')) {
    loadPhoneHealth();
    startPhoneHealthPolling();
  }
});
