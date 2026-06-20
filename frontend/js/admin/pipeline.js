/**
 * FraLib Admin - Pipeline Module
 * Pipeline controls, KPI loading, and status management
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ PIPELINE ADMIN BANNER ════════════════════════════════════════ */
var _pipelineTimerAdmin = null;
var _pipelineStartTimeAdmin = null;

function atualizarCronometroPipelineAdmin() {
  if (!_pipelineStartTimeAdmin) return;
  var elapsed = Math.floor((Date.now() - _pipelineStartTimeAdmin) / 1000);
  var h = Math.floor(elapsed / 3600);
  var m = Math.floor((elapsed % 3600) / 60);
  var s = elapsed % 60;
  var el = document.getElementById('pipeline-banner-tempo');
  if (el) el.textContent = (h > 0 ? String(h).padStart(2,'0') + ':' : '') + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
}

function iniciarCronometroPipelineAdmin() {
  if (!_pipelineStartTimeAdmin) _pipelineStartTimeAdmin = Date.now();
  pararCronometroPipelineAdmin();
  _pipelineTimerAdmin = setInterval(atualizarCronometroPipelineAdmin, 1000);
}

function pararCronometroPipelineAdmin() {
  if (_pipelineTimerAdmin) { clearInterval(_pipelineTimerAdmin); _pipelineTimerAdmin = null; }
}

function carregarPipelineBanner() {
  authFetch('/api/pipeline/status').then(function(r){ return r.json(); }).then(function(d) {
    if (d && d.rodando) {
      var banner = document.getElementById('pipeline-banner');
      if (banner) banner.style.display = 'flex';
      iniciarCronometroPipelineAdmin();
      atualizarTimelineComStatus(d);
    }
  }).catch(function(){});
}

/* ══ PIPELINE CONTROLS ═══════════════════════════════════════════ */
async function carregarPipelineStatus() {
  try {
    var data = await authFetch('/api/pipeline/status').then(function(r){ return r.json(); });
    lastStatus = data;
    atualizarStatusPipeline(data);

    if (typeof window.carregarKPIs === 'function') {
      window.carregarKPIs();
    }

    if (data && data.rodando) {
      iniciarCronometroPipelineAdmin();
    } else {
      pararCronometroPipelineAdmin();
    }
  } catch(e) { console.warn('Pipeline status:', e.message); }
}

function atualizarStatusPipeline(data) {
  data = data || lastStatus;
  var statusEl = document.getElementById('pipelineStatus');
  var btnIniciar = document.getElementById('btnIniciar');
  var btnPausar = document.getElementById('btnPausar');
  var btnRetomar = document.getElementById('btnRetomar');

  if (!statusEl) return;

  if (data && data.rodando) {
    statusEl.textContent = '▶ RODANDO';
    statusEl.className = 'pipeline-status running';
    if (btnIniciar) btnIniciar.style.display = 'none';
    if (btnPausar) btnPausar.style.display = '';
    if (btnRetomar) btnRetomar.style.display = 'none';
    var banner = document.getElementById('pipeline-banner');
    if (banner) banner.style.display = 'flex';
  } else if (data && data.pausado) {
    statusEl.textContent = '⏸ PAUSADO';
    statusEl.className = 'pipeline-status paused';
    if (btnIniciar) btnIniciar.style.display = 'none';
    if (btnPausar) btnPausar.style.display = 'none';
    if (btnRetomar) btnRetomar.style.display = '';
    pararCronometroPipelineAdmin();
    var banner = document.getElementById('pipeline-banner');
    if (banner) banner.style.display = 'none';
  } else {
    statusEl.textContent = '● IDLE';
    statusEl.className = 'pipeline-status idle';
    if (btnIniciar) btnIniciar.style.display = '';
    if (btnPausar) btnPausar.style.display = 'none';
    if (btnRetomar) btnRetomar.style.display = 'none';
    pararCronometroPipelineAdmin();
    var banner = document.getElementById('pipeline-banner');
    if (banner) banner.style.display = 'none';
  }
}

async function iniciarPipeline() {
  if (!verificarCreditosAntesPipeline()) return;
  try {
    var btn = document.getElementById('btnIniciar');
    if (btn) { btn.disabled = true; btn.textContent = '...'; }
    var resp = await authFetch('/api/pipeline/start', { method: 'POST' });
    if (resp.ok) {
      var data = await resp.json();
      Toast && Toast.success && Toast.success('Pipeline iniciado!');
      adicionarLogMagico('🔥 Pipeline ativado! Magic happening...');
      lastStatus.rodando = true;
      atualizarStatusPipeline(lastStatus);
      iniciarCronometroPipelineAdmin();
      if (typeof window.carregarKPIs === 'function') {
        setTimeout(window.carregarKPIs, 2000);
      }
    } else {
      var err = await resp.json().catch(function(){ return {}; });
      Toast && Toast.error && Toast.error(err.detail || 'Erro ao iniciar pipeline');
    }
  } catch(e) {
    Toast && Toast.error && Toast.error('Erro: ' + e.message);
  } finally {
    var btn2 = document.getElementById('btnIniciar');
    if (btn2) { btn2.disabled = false; btn2.textContent = '▶ LIGAR'; }
  }
}

async function pausarPipeline() {
  try {
    var resp = await authFetch('/api/pipeline/pause', { method: 'POST' });
    if (resp.ok) {
      lastStatus.rodando = false;
      lastStatus.pausado = true;
      atualizarStatusPipeline(lastStatus);
      pararCronometroPipelineAdmin();
      Toast && Toast.success && Toast.success('Pipeline pausado');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}

async function retomarPipeline() {
  if (!verificarCreditosAntesPipeline()) return;
  try {
    var resp = await authFetch('/api/pipeline/resume', { method: 'POST' });
    if (resp.ok) {
      lastStatus.rodando = true;
      lastStatus.pausado = false;
      atualizarStatusPipeline(lastStatus);
      iniciarCronometroPipelineAdmin();
      Toast && Toast.success && Toast.success('Pipeline retomado!');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}

// Inicializar controles
document.addEventListener('DOMContentLoaded', function() {
  carregarPipelineStatus();
  setInterval(carregarPipelineStatus, 15000);

  var btnIniciar = document.getElementById('btnIniciar');
  if (btnIniciar) {
    btnIniciar.addEventListener('click', function() {
      iniciarPipeline();
    });
  }
});
</script>
