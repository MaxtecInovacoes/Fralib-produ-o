/**
 * FraLib Admin - CRM & UTI Module
 * Lead table management, Kanban, and UTI processing
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ CRM — Tabela Kanban ════════════════════════════════════════════ */
async function carregarLeads() {
  try {
    var resp = await authFetch('/api/leads?status=crm');
    if (!resp.ok) return;
    var data = await resp.json();
    _crmDataCache = data;
    renderKanban(data);
  } catch(e) { console.error('Leads:', e.message); }
}

function setCrmPeriod(period, btn) {
  crmPeriodAtual = period;
  document.querySelectorAll('[data-period]').forEach(function(b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  if (_crmDataCache) renderKanban(_crmDataCache);
}

function renderKanban(data) {
  var board = document.getElementById('kanbanBoard');
  if (!board) return;

  var search = (document.getElementById('crm-search') || {}).value || '';
  var period = crmPeriodAtual;
  var now = new Date();
  var filtered = data.filter(function(l) {
    if (search && !(l.nome || '').toLowerCase().includes(search.toLowerCase()) && !(l.nicho || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (period === 'hoje') {
      var d = new Date(l.criado_em || l.created_at || now);
      return d.toDateString() === now.toDateString();
    }
    if (period === 'semana') {
      var d = new Date(l.criado_em || l.created_at || now);
      var weekAgo = new Date(now.getTime() - 7 * 86400000);
      return d >= weekAgo;
    }
    if (period === 'mes') {
      var d = new Date(l.criado_em || l.created_at || now);
      return d >= new Date(now.getFullYear(), now.getMonth(), 1);
    }
    return true;
  });

  var cols = [
    { id: 'novo', label: 'NOVO', color: 'var(--fl-purple)' },
    { id: 'contato', label: 'CONTATO', color: 'var(--cyan)' },
    { id: 'proposta', label: 'PROPOSTA', color: 'var(--gold)' },
    { id: 'negociacao', label: 'NEGOCIAÇÃO', color: 'var(--info)' },
    { id: 'ganho', label: 'GANHO', color: 'var(--success)' },
    { id: 'perdido', label: 'PERDIDO', color: 'var(--danger)' }
  ];

  var byStatus = {};
  cols.forEach(function(c) { byStatus[c.id] = []; });
  filtered.forEach(function(l) {
    var s = l.status_pipeline || l.etapa || 'novo';
    if (!byStatus[s]) byStatus[s] = [];
    byStatus[s].push(l);
  });

  var html = cols.map(function(c) {
    var cards = (byStatus[c.id] || []).map(function(l) {
      return '<div class="kanban-card" onclick="abrirModalLead(' + l.id + ')">' +
        '<div class="kanban-card-name">' + escapeHtml(l.nome || '—') + '</div>' +
        '<div class="kanban-card-meta">' + escapeHtml(l.nicho || '—') + ' · ' + escapeHtml(l.cidade || '—') + '</div>' +
        '</div>';
    }).join('');
    return '<div class="kanban-col"><div class="kanban-col-header" style="border-color:' + c.color + ';color:' + c.color + '">' + c.label + ' <span>' + (byStatus[c.id] || []).length + '</span></div><div class="kanban-col-body">' + cards + '</div></div>';
  }).join('');

  board.innerHTML = html;
  var countEl = document.getElementById('crm-count');
  if (countEl) countEl.textContent = filtered.length + ' leads';
}

/* ══ UTI — Leads Incompletos ═════════════════════════════════════════ */
async function carregarUTI() {
  try {
    var resp = await authFetch('/api/leads/uti');
    if (!resp.ok) return;
    var data = await resp.json();
    _utiDataCache = data;
    renderUTI(data);
  } catch(e) { console.error('UTI:', e.message); }
}

function setUtiPeriod(period, btn) {
  utiPeriodAtual = period;
  document.querySelectorAll('[data-uti-period]').forEach(function(b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  if (_utiDataCache) renderUTI(_utiDataCache);
}

function renderUTI(data) {
  var table = document.getElementById('uti-table-body');
  if (!table) return;

  var search = (document.getElementById('uti-search') || {}).value || '';
  var period = utiPeriodAtual;
  var now = new Date();

  var filtered = data.filter(function(l) {
    if (search && !(l.nome || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (period === 'hoje') {
      var d = new Date(l.criado_em || l.created_at || now);
      return d.toDateString() === now.toDateString();
    }
    if (period === 'semana') {
      var d = new Date(l.criado_em || l.created_at || now);
      var weekAgo = new Date(now.getTime() - 7 * 86400000);
      return d >= weekAgo;
    }
    if (period === 'mes') {
      var d = new Date(l.criado_em || l.created_at || now);
      return d >= new Date(now.getFullYear(), now.getMonth(), 1);
    }
    return true;
  });

  var rows = filtered.map(function(l) {
    var incomplete = [];
    if (!l.telefone || l.telefone === l.email) incomplete.push('sem telefone');
    if (!l.nome || l.nome === l.email) incomplete.push('sem nome');
    if (!l.endereco) incomplete.push('sem endereço');

    return '<tr onclick="abrirModalLead(' + l.id + ')" style="cursor:pointer">' +
      '<td style="padding:10px;border-bottom:1px solid var(--fl-border)">' + escapeHtml(l.nome || '—') + '</td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--fl-border);color:var(--fl-text-muted)">' + escapeHtml(l.email || '—') + '</td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--fl-border)"><span style="background:rgba(245,158,11,0.15);color:var(--warning);padding:3px 8px;border-radius:4px;font-size:10px">' + escapeHtml(incomplete.join(', ') || 'completo') + '</span></td>' +
      '<td style="padding:10px;border-bottom:1px solid var(--fl-border);color:var(--fl-text-muted)">' + escapeHtml(l.criado_em || '') + '</td>' +
      '</tr>';
  }).join('');

  table.innerHTML = rows || '<tr><td colspan="4" style="padding:20px;text-align:center;color:var(--fl-text-muted)">Nenhum lead incompleto encontrado</td></tr>';
}

async function enriquecerLead(leadId) {
  try {
    Toast && Toast.info && Toast.info('Enriquecendo dados...');
    var resp = await authFetch('/api/leads/' + leadId + '/enriquecer', { method: 'POST' });
    if (resp.ok) {
      Toast && Toast.success && Toast.success('Lead enriquecido!');
      carregarUTI();
    } else {
      Toast && Toast.error && Toast.error('Erro ao enriquecer');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}

async function requalificarLead(leadId) {
  try {
    Toast && Toast.info && Toast.info('Requalificando...');
    var resp = await authFetch('/api/leads/' + leadId + '/requalificar', { method: 'POST' });
    if (resp.ok) {
      Toast && Toast.success && Toast.success('Lead requalificado!');
      carregarUTI();
    } else {
      Toast && Toast.error && Toast.error('Erro ao requalificar');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}
</script>
