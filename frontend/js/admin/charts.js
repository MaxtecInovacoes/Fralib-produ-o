/**
 * FraLib Admin - Charts Module
 * Chart.js-based analytics charts and funnel visualization
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ CHARTS — Chart.js ═════════════════════════════════════════════ */

async function carregarStatsConfig() {
  try {
    var data = await authFetch('/api/pipeline/stats').then(function(r){ return r.json(); });
    var set = function(id, val){ var el = document.getElementById(id); if(el) el.textContent = val; };
    set('stat-taxa-resposta', (data.taxa_resposta || 0) + '%');
    set('stat-nicho-top', data.nicho_top || '—');
    set('stat-nicho-top-conv', (data.nicho_top_conv || 0) + '%');
    set('stat-cidade-top', data.cidade_top || '—');
    set('stat-cidade-top-total', data.cidade_top_total || 0);
    set('stat-ticket-medio', 'R$ ' + (data.ticket_medio || 0).toLocaleString('pt-BR', {minimumFractionDigits:0}));
    set('stat-msgs-bryan', (data.total_msgs_franz || data.total_msgs_bryan || 0).toLocaleString('pt-BR'));
  } catch(e) { console.warn('Stats:', e.message); }
}

async function carregarCharts(periodo) {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js não carregado');
    return;
  }
  try {
    var data = await authFetch('/api/pipeline/analytics/overview?periodo=' + (periodo || 'mes')).then(function(r){ return r.json(); });
    renderLinhaChart(data.por_dia || []);
    renderCidadeChart(data.por_cidade || []);
    renderNichoChart(data.por_nicho || []);
    renderFunil(data);
  } catch(e) { console.warn('Charts:', e.message); }
}

function destroyChart(id) {
  if (chartsInstances[id]) {
    chartsInstances[id].destroy();
    delete chartsInstances[id];
  }
}

var CHART_COLORS = [
  'rgba(147,51,234,0.85)',
  'rgba(0,255,179,0.85)',
  'rgba(255,184,0,0.85)',
  'rgba(56,189,248,0.85)',
  'rgba(239,68,68,0.85)',
  'rgba(34,197,94,0.85)',
  'rgba(245,158,11,0.85)',
  'rgba(192,132,252,0.85)'
];

var CHART_SCALES = {
  x: {
    grid: { color: 'rgba(255,255,255,0.05)' },
    ticks: { color: '#8888a0', font: { family: "'JetBrains Mono', monospace", size: 10 } }
  },
  y: {
    grid: { color: 'rgba(255,255,255,0.05)' },
    ticks: { color: '#8888a0', font: { family: "'JetBrains Mono', monospace", size: 10 } },
    beginAtZero: true
  }
};

function renderLinhaChart(porDia) {
  destroyChart('linha');
  var canvas = document.getElementById('chartLinha');
  if (!canvas) return;
  chartsInstances['linha'] = new Chart(canvas, {
    type: 'line',
    data: {
      labels: porDia.map(function(x){ return x.dia ? x.dia.slice(5) : ''; }),
      datasets: [{
        label: 'Leads',
        data: porDia.map(function(x){ return x.total; }),
        borderColor: 'rgba(147,51,234,0.9)',
        backgroundColor: 'rgba(147,51,234,0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#c084fc',
        pointRadius: 4,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: CHART_SCALES
    }
  });
}

function renderCidadeChart(porCidade) {
  destroyChart('cidade');
  var canvas = document.getElementById('chartCidade');
  if (!canvas) return;
  chartsInstances['cidade'] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: porCidade.map(function(x){ return x.nome || '—'; }),
      datasets: [{
        label: 'Leads',
        data: porCidade.map(function(x){ return x.total; }),
        backgroundColor: porCidade.map(function(_, i){ return CHART_COLORS[i % CHART_COLORS.length]; }),
        borderWidth: 0,
        borderRadius: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: CHART_SCALES
    }
  });
}

function renderNichoChart(porNicho) {
  destroyChart('nicho');
  var canvas = document.getElementById('chartNicho');
  if (!canvas) return;
  chartsInstances['nicho'] = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: porNicho.map(function(x){ return x.nome || '—'; }),
      datasets: [{
        data: porNicho.map(function(x){ return x.total; }),
        backgroundColor: CHART_COLORS.slice(0, porNicho.length),
        borderColor: '#0a0714',
        borderWidth: 3
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#8888a0',
            font: { size: 10, family: "'JetBrains Mono', monospace" },
            padding: 12,
            boxWidth: 12
          }
        }
      },
      cutout: '60%'
    }
  });
}

function renderFunil(analytics) {
  var wrap = document.getElementById('funnelWrap');
  if (!wrap) return;

  var totalLeads = analytics.total_leads || 0;
  var totalSites = lastStatus.totalSites || Math.round(totalLeads * (analytics.conversao || 0) / 100);
  var totalEnviados = lastStatus.totalEnviados || 0;

  var steps = [
    { label: 'LEADS PROSPECTADOS', count: totalLeads, color: 'var(--fl-purple)' },
    { label: 'SITES GERADOS', count: totalSites, color: 'var(--cyan)' },
    { label: 'WHATSAPP ENVIADOS', count: totalEnviados, color: 'var(--info)' }
  ];

  var maxCount = steps[0].count || 1;

  wrap.innerHTML = steps.map(function(s) {
    var pct = Math.max(15, Math.round((s.count / maxCount) * 100));
    return '<div class="funnel-step" style="--pct:' + pct + '%;--color:' + s.color + '">' +
      '<div class="funnel-count" style="color:' + s.color + '">' + s.count.toLocaleString('pt-BR') + '</div>' +
      '<div class="funnel-label">' + s.label + '</div></div>';
  }).join('');
}
</script>
