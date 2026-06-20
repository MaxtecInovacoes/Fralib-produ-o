/**
 * FraLib Admin - Lead Supply Module
 * Hunter/Caio lead supply engine for separating from production
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ LEAD SUPPLY — Hunter/Caio separado da produção ═══════════════ */
var _leadSupplyState = null;
var _leadSupplyPoll = null;
var _leadSupplyActionTimer = null;
var _leadSupplyProviderAlert = null;

function _csvToList(value) {
  return (value || '').split(/[,;\n]+/).map(function(v){ return v.trim(); }).filter(Boolean);
}

function _listToText(list) {
  return (list || []).join(', ');
}

function _setText(id, value) {
  var el = document.getElementById(id);
  if (el) el.textContent = value;
}

function _leadSupplyStatusLabel(s) {
  if (!s) return 'desconhecido';
  if (s === 'active' || s === 'rodando') return 'ativo';
  if (s === 'paused' || s === 'pausado') return 'pausado';
  if (s === 'done' || s === 'concluido') return 'concluído';
  return s;
}

function _leadSupplyStatusColor(s) {
  if (!s) return 'var(--fl-text-dim)';
  if (s === 'active' || s === 'rodando') return 'var(--success)';
  if (s === 'paused' || s === 'pausado') return 'var(--warning)';
  if (s === 'done' || s === 'concluido') return 'var(--cyan)';
  return 'var(--fl-text-muted)';
}

function _leadSupplyFilteredErrors(state) {
  var filter = _leadSupplyState && _leadSupplyState.filter;
  if (!filter || filter === 'todos') return state.errors || [];
  return (state.errors || []).filter(function(e) {
    return e.status === filter || (e.provider && e.provider.toLowerCase().includes(filter.toLowerCase()));
  });
}

function _leadSupplyApplyFilters() {
  if (!_leadSupplyState) return;
  _leadSupplyState.errors = _leadSupplyFilteredErrors(_leadSupplyState);
  renderLeadSupply();
}

function setLeadSupplyFilter(value) {
  if (!_leadSupplyState) return;
  _leadSupplyState.filter = value;
  document.querySelectorAll('.ls-filter-btn').forEach(function(b) {
    b.classList.toggle('active', b.dataset.filter === value);
  });
  _leadSupplyApplyFilters();
}

function _renderLeadSupplyDiagnosis(state) {
  var health = state.health || 'unknown';
  var color = health === 'good' ? 'var(--success)' : health === 'warn' ? 'var(--warning)' : 'var(--danger)';
  var bg = health === 'good' ? 'rgba(34,197,94,0.1)' : health === 'warn' ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)';
  var messages = {
    good: 'Tudo funcionando bem!',
    warn: 'Atenção necessária.',
    error: 'Problemas detectados.'
  };
  var tone = health === 'good' ? 'Brilhante!' : health === 'warn' ? 'Precisa de ajuste' : 'Corrigir urgente';
  var title = state.diagnosis_title || tone;
  var text = state.diagnosis_text || messages[health] || '';
  var actions = state.diagnosis_actions || [];

  var html = '<div style="background:' + bg + ';border:1px solid ' + color + ';border-radius:10px;padding:16px;margin-bottom:20px;">';
  html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">';
  html += '<span style="font-size:24px">' + (health === 'good' ? '✨' : health === 'warn' ? '⚠️' : '🚨') + '</span>';
  html += '<div><div style="font-family:var(--fl-font-brand);font-size:12px;color:' + color + '">' + escapeHtml(title) + '</div>';
  html += '<div style="font-size:12px;color:var(--fl-text-muted);margin-top:3px">' + escapeHtml(text) + '</div></div></div>';

  if (actions.length > 0) {
    html += '<div style="display:flex;flex-direction:column;gap:8px">';
    actions.forEach(function(a) {
      var aColor = a.type === 'success' ? 'var(--success)' : a.type === 'warning' ? 'var(--warning)' : 'var(--fl-purple)';
      html += '<button onclick="' + escapeHtml(a.action) + '" style="background:' + aColor + ';color:#000;border:none;border-radius:7px;padding:9px 14px;font-size:12px;font-weight:700;cursor:pointer;text-align:left">' + escapeHtml(a.label) + '</button>';
    });
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function renderLeadSupply() {
  var wrap = document.getElementById('lead-supply-body');
  if (!wrap) return;

  var state = _leadSupplyState;
  if (!state) {
    wrap.innerHTML = '<div style="color:var(--fl-text-muted);padding:20px;text-align:center">Carregando...</div>';
    return;
  }

  var html = '';

  // Insight cards
  if (state.insights) {
    var i = state.insights;
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;">';
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;padding:14px;text-align:center">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:6px">TOTAL HOJE</div>';
    html += '<div style="font-family:var(--fl-font-brand);font-size:22px;color:var(--fl-purple-300)">' + (i.total_today || 0) + '</div></div>';
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;padding:14px;text-align:center">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:6px">VÁLIDOS</div>';
    html += '<div style="font-family:var(--fl-font-brand);font-size:22px;color:var(--success)">' + (i.valid_today || 0) + '</div></div>';
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;padding:14px;text-align:center">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:6px">REPROVADOS</div>';
    html += '<div style="font-family:var(--fl-font-brand);font-size:22px;color:var(--warning)">' + (i.rejected_today || 0) + '</div></div>';
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;padding:14px;text-align:center">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:6px">GAP</div>';
    html += '<div style="font-family:var(--fl-font-brand);font-size:22px;color:var(--cyan)">' + (i.gap || 0) + '</div></div>';
    html += '</div>';

    // Funnel
    var total = i.total_today || 1;
    var valid = i.valid_today || 0;
    var gap = i.gap || 0;
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;padding:16px;margin-bottom:20px;">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:10px">FUNIL</div>';
    html += '<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--fl-bg);">';
    var validPct = Math.round((valid / total) * 100);
    var gapPct = Math.round((gap / total) * 100);
    html += '<div style="width:' + validPct + '%;background:var(--success)"></div>';
    html += '<div style="width:' + gapPct + '%;background:var(--warning)"></div>';
    html += '</div><div style="display:flex;justify-content:space-between;margin-top:8px;font-size:10px">';
    html += '<span style="color:var(--success)">Válidos: ' + validPct + '%</span>';
    html += '<span style="color:var(--warning)">Incompletos: ' + gapPct + '%</span></div></div>';

    // Discard reasons
    if (i.discard_reasons && i.discard_reasons.length > 0) {
      html += '<div style="margin-bottom:20px">';
      html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:8px">MOTIVOS DE REPROVAÇÃO</div>';
      html += '<div style="display:flex;flex-direction:column;gap:6px">';
      i.discard_reasons.forEach(function(r) {
        html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--fl-bg-surface);border-radius:6px;font-size:11px">';
        html += '<span style="color:var(--fl-text-muted)">' + escapeHtml(r.reason) + '</span>';
        html += '<span style="color:var(--warning)">' + r.count + '</span></div>';
      });
      html += '</div></div>';
    }

    // Niche breakdown
    if (i.niche_breakdown && i.niche_breakdown.length > 0) {
      html += '<div style="margin-bottom:20px">';
      html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:8px">POR NICHO</div>';
      html += '<div style="display:flex;flex-direction:column;gap:6px">';
      i.niche_breakdown.forEach(function(n) {
        var pct = Math.round((n.count / total) * 100);
        html += '<div style="padding:8px 12px;background:var(--fl-bg-surface);border-radius:6px">';
        html += '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">';
        html += '<span style="color:var(--fl-text)">' + escapeHtml(n.niche) + '</span>';
        html += '<span style="color:var(--fl-purple-300)">' + n.count + ' (' + pct + '%)</span></div>';
        html += '<div style="height:4px;background:var(--fl-bg);border-radius:2px"><div style="height:100%;width:' + pct + '%;background:var(--fl-purple)"></div></div></div>';
      });
      html += '</div></div>';
    }
  }

  // Diagnosis
  if (state.health) {
    html += _renderLeadSupplyDiagnosis(state);
  }

  // Today's events
  if (state.today) {
    html += '<div style="margin-bottom:20px">';
    html += '<div style="font-size:10px;color:var(--fl-text-dim);margin-bottom:8px">TABELA DE HOJE</div>';
    html += '<div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:8px;overflow:hidden">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:11px">';
    html += '<thead><tr style="background:var(--fl-bg)">';
    ['Provedor','Nicho','Encontrados','Válidos','Inválidos','Status'].forEach(function(h) {
      html += '<th style="padding:8px 10px;text-align:left;color:var(--fl-text-dim);font-weight:500">' + h + '</th>';
    });
    html += '</tr></thead><tbody>';
    state.today.forEach(function(row) {
      html += '<tr style="border-top:1px solid var(--fl-border)">';
      html += '<td style="padding:8px 10px;color:var(--fl-text)">' + escapeHtml(row.provider || '—') + '</td>';
      html += '<td style="padding:8px 10px;color:var(--fl-text-muted)">' + escapeHtml(row.niche || '—') + '</td>';
      html += '<td style="padding:8px 10px;color:var(--fl-text)">' + (row.total || 0) + '</td>';
      html += '<td style="padding:8px 10px;color:var(--success)">' + (row.valid || 0) + '</td>';
      html += '<td style="padding:8px 10px;color:var(--warning)">' + (row.invalid || 0) + '</td>';
      html += '<td style="padding:8px 10px"><span style="color:' + _leadSupplyStatusColor(row.status) + ';font-size:10px;font-family:var(--fl-font-brand)">' + _leadSupplyStatusLabel(row.status).toUpperCase() + '</span></td>';
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
  }

  wrap.innerHTML = html;
}

function _renderLeadSupplyToday(state) {
  if (!state || !state.hunter_status) return '';
  var hs = state.hunter_status;
  var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px;">';
  html += '<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:12px;text-align:center">';
  html += '<div style="font-size:9px;color:var(--fl-text-dim);margin-bottom:4px">ENCONTRADOS</div>';
  html += '<div style="font-family:var(--fl-font-brand);font-size:18px;color:var(--success)">' + (hs.total_found || 0) + '</div></div>';
  html += '<div style="background:rgba(0,255,179,0.08);border:1px solid rgba(0,255,179,0.3);border-radius:8px;padding:12px;text-align:center">';
  html += '<div style="font-size:9px;color:var(--fl-text-dim);margin-bottom:4px">VALIDADOS</div>';
  html += '<div style="font-family:var(--fl-font-brand);font-size:18px;color:var(--cyan)">' + (hs.total_valid || 0) + '</div></div>';
  html += '<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:12px;text-align:center">';
  html += '<div style="font-size:9px;color:var(--fl-text-dim);margin-bottom:4px">DESCARTADOS</div>';
  html += '<div style="font-family:var(--fl-font-brand);font-size:18px;color:var(--warning)">' + (hs.total_discarded || 0) + '</div></div>';
  html += '<div style="background:rgba(147,51,234,0.08);border:1px solid rgba(147,51,234,0.3);border-radius:8px;padding:12px;text-align:center">';
  html += '<div style="font-size:9px;color:var(--fl-text-dim);margin-bottom:4px">GASTOS</div>';
  html += '<div style="font-family:var(--fl-font-brand);font-size:18px;color:var(--fl-purple-300)">R$ ' + ((hs.total_cost || 0)).toFixed(4) + '</div></div>';
  html += '</div>';
  return html;
}

async function carregarLeadSupplyStatus() {
  try {
    var data = await authFetch('/api/lead-supply/status').then(function(r){ return r.json(); });
    _leadSupplyState = data;
    renderLeadSupply();
    if (typeof window.renderPipelinePermission === 'function') {
      window.renderPipelinePermission(data.config);
    }
  } catch(e) {
    console.warn('Lead Supply status:', e.message);
  }
}

async function salvarLeadSupplyConfig(config) {
  try {
    var resp = await authFetch('/api/lead-supply/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config || _leadSupplyState.config)
    });
    if (resp.ok) {
      Toast && Toast.success && Toast.success('Config salvada!');
      carregarLeadSupplyStatus();
    } else {
      var err = await resp.json().catch(function(){ return {}; });
      Toast && Toast.error && Toast.error(err.detail || 'Erro ao salvar');
    }
  } catch(e) {
    Toast && Toast.error && Toast.error('Erro: ' + e.message);
  }
}

function _leadSupplyCopySupport(provider) {
  var text = '';
  if (provider === 'hunter') {
    text = ' hunter.io/api\n' + (_leadSupplyState.config.hunter_api_key || '');
  } else if (provider === 'apollo') {
    text = ' apollo.io\n' + (_leadSupplyState.config.apollo_api_key || '');
  } else if (provider === 'caio') {
    text = ' Caio (Google Scraper)\nAPI Key: ' + (_leadSupplyState.config.caio_api_key || 'não configurada');
  }
  navigator.clipboard && navigator.clipboard.writeText(text).then(function() {
    Toast && Toast.success && Toast.success('Copiado!');
  }).catch(function(){});
}

function _leadSupplyFallbackCopy(provider) {
  Toast && Toast.info && Toast.info('Configure a API key em Configurações Avançadas.');
}
</script>
