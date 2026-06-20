/**
 * FraLib Admin - Utilities Module
 * UI utilities, modals, profile management, credits, tour
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ 2FA STATUS ════════════════════════════════════════════════════ */
async function checkTwoFactorStatus() {
  try {
    const res = await authFetch("/api/auth/2fa/status");
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById("2fa-status-badge");
    if (badge) {
      badge.textContent = data.enabled ? "Ativo" : "Inativo";
      badge.className = data.enabled ? "badge badge-success" : "badge badge-secondary";
    }
  } catch (err) {
    console.warn("[2FA] Erro ao verificar status:", err.message);
  }
}

/* ══ MEU PERFIL ═════════════════════════════════════════════════ */
function verificarPrimeiroAcesso() {
  verificarOnboarding();
}
function fecharModalPrimeiroAcesso() {
  var m = document.getElementById('modal-primeiro-acesso');
  if (m) m.style.display = 'none';
  document.querySelector('[data-view="perfil"]').click();
}

async function uploadFotoPerfil(input) {
  if (!input.files || !input.files[0]) return;
  var file = input.files[0];
  if (file.size > 2 * 1024 * 1024) { Toast.error('Foto muito grande. Max 2MB.'); return; }
  var reader = new FileReader();
  reader.onload = function(e) {
    var url = e.target.result;
    var img = document.getElementById('perfil-foto-img');
    var icon = document.getElementById('perfil-foto-icon');
    if (img) { img.src = url; img.style.display = 'block'; }
    if (icon) icon.style.display = 'none';
    localStorage.setItem('perfil_foto', url);
    Toast.success('Foto atualizada!');
  };
  reader.readAsDataURL(file);
}

function carregarFotoPerfil() {
  var url = localStorage.getItem('perfil_foto');
  if (!url) return;
  var img = document.getElementById('perfil-foto-img');
  var icon = document.getElementById('perfil-foto-icon');
  if (img) { img.src = url; img.style.display = 'block'; }
  if (icon) icon.style.display = 'none';
  var sImg = document.getElementById('sidebar-foto-img');
  var sIcon = document.getElementById('sidebar-foto-icon');
  if (sImg) { sImg.src = url; sImg.style.display = 'block'; }
  if (sIcon) sIcon.style.display = 'none';
}

async function salvarPerfil() {
  var nome = (document.getElementById('perfilNome') || {}).value || '';
  var telefone = (document.getElementById('perfilTelefone') || {}).value || '';
  var rua = (document.getElementById('perfilRua') || {}).value || '';
  var bairro = (document.getElementById('perfilBairro') || {}).value || '';
  var cidade = (document.getElementById('perfilCidade') || {}).value || '';
  var estado = (document.getElementById('perfilEstado') || {}).value || '';
  var cep = (document.getElementById('perfilCEP') || {}).value || '';
  var nicho = (document.getElementById('perfilNicho') || {}).value || '';
  var origem = (document.getElementById('perfilOrigem') || {}).value || '';

  if (!nome || !telefone || !nicho) {
    mostrarToast('Preencha Nome, Telefone e Nicho');
    return;
  }

  var endereco = [rua, bairro, cidade, estado, cep].filter(Boolean).join(', ');

  try {
    var response = await authFetch('/api/users/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome: nome, telefone: telefone, endereco: endereco, nicho: nicho, origem: origem, cep: cep, rua: rua, bairro: bairro, cidade: cidade, estado: estado })
    });

    if (response.ok) {
      localStorage.setItem('perfil_nome', nome);
      Toast.success('Perfil salvo com sucesso!');
      try { verificarOnboarding(); } catch(_) {}
    } else {
      var err = await response.json().catch(function(){ return {}; });
      Toast.error(err.detail || 'Erro ao salvar perfil');
    }
  } catch (e) {
    console.error('[Perfil] Erro:', e);
    Toast.error('Erro ao salvar perfil: ' + e.message);
  }
}

/* ══ CREDITS ═══════════════════════════════════════════════════════ */
var creditModalNotice = '';

function formatBRL(v) {
  return 'R$ ' + (parseFloat(v) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function carregarCreditos() {
  try {
    var data = await authFetch('/api/credits/balance').then(function(r){ return r.json(); });
    var el = document.getElementById('saldo-creditos');
    if (el) el.textContent = data.creditos_disponiveis || 0;
    return data;
  } catch(e) { console.warn('Credits:', e.message); }
}

async function verificarRetornoMercadoPago() {
  var params = new URLSearchParams(window.location.search);
  if (params.has('payment_id') || params.has('checkout_preference_id')) {
    try {
      await authFetch('/api/credits/webhook', { method: 'POST' });
      Toast && Toast.success && Toast.success('Pagamento confirmado! Créditos creditados.');
      carregarCreditos();
      window.history.replaceState({}, '', window.location.pathname);
    } catch(e) {}
  }
}

function criarModalCreditos() {
  const modal = document.createElement('div');
  modal.id = 'modal-creditos';
  modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.82);z-index:9999;align-items:center;justify-content:center;padding:20px;';
  modal.innerHTML = `
    <div style="background:var(--fl-bg-card);border:2px solid var(--fl-border);border-radius:12px;padding:28px;max-width:680px;width:100%;max-height:86vh;overflow-y:auto;box-shadow:0 24px 80px rgba(0,0,0,.45)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;gap:16px">
        <div>
          <h2 style="font-family:var(--fl-font-brand);font-size:15px;color:var(--fl-purple-300);margin:0 0 8px">PAGAMENTOS E CRÉDITOS</h2>
          <div style="font-size:12px;color:var(--fl-text-muted)">Mercado Pago: PIX e cartão no checkout seguro.</div>
        </div>
        <button onclick="fecharModalCreditos()" style="background:none;border:none;color:var(--fl-text-muted);font-size:28px;cursor:pointer;padding:0;width:34px;height:34px">×</button>
      </div>
      <div id="creditos-modal-notice" style="display:none;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.45);color:var(--fl-text);border-radius:10px;padding:12px 14px;margin-bottom:18px;font-size:13px;line-height:1.5"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:22px">
        <div style="background:var(--fl-purple-900);border:2px solid var(--fl-purple);border-radius:10px;padding:18px;text-align:center">
          <div style="font-size:12px;color:var(--fl-text-muted);margin-bottom:8px">Seu saldo atual</div>
          <div style="font-family:var(--fl-font-brand);font-size:26px;color:var(--fl-purple-300)"><span id="saldo-creditos-modal">0</span> créditos</div>
        </div>
        <div style="background:var(--fl-bg-surface);border:1px solid var(--fl-border);border-radius:10px;padding:18px">
          <div style="font-size:12px;color:var(--fl-text-muted);margin-bottom:10px">Recarga livre</div>
          <div style="display:flex;gap:8px;align-items:center">
            <input id="recarga-livre-valor" type="number" min="5" step="1" value="50" style="flex:1;background:var(--fl-bg-card);border:1px solid var(--fl-border-md);border-radius:8px;color:var(--fl-text);padding:12px;font-size:16px" aria-label="Valor da recarga">
            <button onclick="comprarRecargaLivre()" style="background:var(--fl-purple);color:#fff;border:0;border-radius:8px;padding:12px 14px;font-weight:800;cursor:pointer">PAGAR</button>
          </div>
        </div>
      </div>
      <div style="margin-bottom:22px">
        <h3 style="font-size:14px;color:var(--fl-text);margin:0 0 14px;font-weight:700">Pacotes com bônus progressivo</h3>
        <div id="tabela-precos" style="display:flex;flex-direction:column;gap:12px"><div style="text-align:center;color:var(--fl-text-muted)">Carregando...</div></div>
      </div>
    </div>`;
  return modal;
}

function fecharModalCreditos() {
  const modal = document.getElementById('modal-creditos');
  if (modal) modal.style.display = 'none';
  creditModalNotice = '';
}

function abrirModalCreditos(msg) {
  if (!document.getElementById('modal-creditos')) {
    document.body.appendChild(criarModalCreditos());
  }
  const modal = document.getElementById('modal-creditos');
  const notice = document.getElementById('creditos-modal-notice');
  if (msg) {
    creditModalNotice = msg;
    if (notice) { notice.textContent = msg; notice.style.display = 'block'; }
  }
  if (modal) modal.style.display = 'flex';
  carregarCreditos();
  carregarTabelaPrecos();
}

function abrirPlanosPagamento() {
  abrirModalCreditos('Planos renovam mensalmente pelo Mercado Pago. Recargas avulsas continuam disponíveis para créditos extras.');
}

async function carregarTabelaPrecos() {
  try {
    const response = await fetch('/api/credits/pricing', { credentials: 'include' });
    const data = await response.json();
    const precos = Array.isArray(data) ? data : (data.pacotes || []);
    const container = document.getElementById('tabela-precos');
    if (!container) return;
    container.innerHTML = precos.map(p => `
      <div style="display:grid;grid-template-columns:1fr auto auto;gap:14px;align-items:center;padding:15px;background:var(--fl-bg-surface);border:2px solid ${p.bonus_percentual > 0 ? 'var(--fl-purple)' : 'var(--fl-border)'};border-radius:8px;${p.bonus_percentual > 0 ? 'box-shadow:0 0 20px rgba(147,51,234,0.22);' : ''}">
        <div>
          <div style="font-size:18px;font-weight:800;color:var(--fl-text)">${formatBRL(p.valor)}</div>
          <div style="font-size:12px;color:var(--fl-text-muted);margin-top:4px">${formatBRL(p.custo_por_credito)}/crédito</div>
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--fl-font-brand);font-size:18px;color:var(--fl-purple-300)">${p.creditos_totais} créditos</div>
          ${p.bonus_percentual > 0 ? `<div style="display:inline-block;margin-top:5px;padding:4px 8px;background:var(--fl-purple);color:white;border-radius:4px;font-size:10px;font-weight:800">+${p.bonus_percentual}% BÔNUS</div>` : ''}
        </div>
        <button onclick="comprarRecarga(${Number(p.valor)})" style="background:var(--fl-purple);color:white;border:0;border-radius:8px;padding:12px 14px;font-weight:800;cursor:pointer">COMPRAR</button>
      </div>`).join('');
  } catch(e) { console.error('Erro ao carregar preços:', e); }
}

async function comprarRecarga(valor) {
  try {
    var resp = await authFetch('/api/credits/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ valor: valor })
    });
    var data = await resp.json();
    if (data.init_point) {
      window.location.href = data.init_point;
    } else {
      Toast && Toast.error && Toast.error('Erro ao gerar checkout');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}

async function comprarRecargaLivre() {
  var valor = parseFloat((document.getElementById('recarga-livre-valor') || {}).value) || 50;
  if (valor < 5) { Toast && Toast.error && Toast.error('Valor mínimo: R$ 5'); return; }
  await comprarRecarga(valor);
}

async function comprarPlanoMercadoPago(plano) {
  try {
    var resp = await authFetch('/api/billing/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plano: plano })
    });
    var data = await resp.json();
    if (data.init_point) {
      window.location.href = data.init_point;
    } else {
      Toast && Toast.error && Toast.error('Erro ao gerar checkout do plano');
    }
  } catch(e) { Toast && Toast.error && Toast.error('Erro: ' + e.message); }
}

document.addEventListener('DOMContentLoaded', function() {
  carregarCreditos();
  verificarRetornoMercadoPago();
});

/* ══ TOUR GUIADO ══════════════════════════════════════════════════════ */
var TOUR_KEY = 'fralib_tour_done';

function iniciarTour(dismissed) {
  var el = document.getElementById('flMfTour');
  if (!el) return;
  if (window.flMfOpenTour) window.flMfOpenTour();
}

function encerrarTour() {
  localStorage.setItem(TOUR_KEY, '1');
  if (window.flMfCloseTour) window.flMfCloseTour();
}

/* ══ TOAST HELPER ════════════════════════════════════════════════════ */
function mostrarToast(msg, tipo) {
  if (typeof Toast !== 'undefined' && Toast[tipo || 'info']) {
    Toast[tipo || 'info'](msg);
  } else {
    alert(msg);
  }
}

/* ══ ERRORS MODAL ════════════════════════════════════════════════════ */
function mostrarErrosPipelineAdmin(titulo, msg, dica) {
  var overlay = document.getElementById('pipeline-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'pipeline-overlay';
    overlay.id = 'pipeline-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9998;display:flex;align-items:center;justify-content:center;';
    document.body.appendChild(overlay);
  }
  overlay.style.display = 'flex';
  overlay.innerHTML = '<div style="background:var(--fl-bg-card);border:2px solid var(--danger);border-radius:12px;padding:28px;max-width:480px;width:90%;text-align:center">' +
    '<div style="font-size:48px;margin-bottom:16px">🚨</div>' +
    '<h3 style="font-family:var(--fl-font-brand);font-size:14px;color:var(--danger);margin-bottom:12px">' + escapeHtml(titulo) + '</h3>' +
    '<p style="color:var(--fl-text-muted);margin-bottom:16px;line-height:1.6">' + escapeHtml(msg) + '</p>' +
    '<p style="color:var(--fl-text-dim);font-size:12px;margin-bottom:20px">' + escapeHtml(dica || '') + '</p>' +
    '<button onclick="this.closest(\'.pipeline-overlay\').style.display=\'none\'" style="background:var(--fl-purple);color:#fff;border:none;border-radius:8px;padding:12px 24px;font-weight:700;cursor:pointer">ENTENDI</button></div>';
}

/* ══ VIEW SWITCHING ═════════════════════════════════════════════════ */
function mostrarView(view) {
  document.querySelectorAll('.view-section').forEach(function(el) { el.classList.remove('active'); });
  document.querySelectorAll('.sidebar-link').forEach(function(el) { el.classList.remove('active'); });
  var link = document.querySelector('.sidebar-link[data-view="' + view + '"]');
  if (link) link.classList.add('active');
  localStorage.setItem('fralib_view', view);
  var target = document.getElementById('view-' + view);
  if (target) target.classList.add('active');

  var kpiSection = document.getElementById("kpi-section");
  if (kpiSection) {
    kpiSection.style.display = (view === "overview") ? "grid" : "none";
  }
  if (view === 'overview') {
    setTimeout(function(){ carregarCharts(periodoAtual); }, 80);
  }
  if (view === 'uti') {
    carregarUTI();
  }
  if (view === 'config') {
    setTimeout(function(){
      if (window.initPixelOffice) {
        window._pixelOfficeStarted = false;
        window.initPixelOffice();
      }
    }, 50);
    carregarStatsConfig();
  }
  if (view === 'sites') carregarSites();
}

function trocarPeriodo(periodo, btn) {
  periodoAtual = periodo;
  document.querySelectorAll('.btn-period').forEach(function(b){ b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  carregarCharts(periodo);
}

/* ══ SIDEBAR TOGGLE ═════════════════════════════════════════════════ */
(function(){
  var toggle = document.getElementById('sidebarToggle');
  if (toggle) {
    toggle.addEventListener('click', function() {
      var sidebar = document.getElementById('sidebar');
      if (sidebar) sidebar.classList.toggle('open');
    });
  }
  var target = document.getElementById('pipelinePermissionBadge');
  if (target && window.MutationObserver){
    new MutationObserver(function() {
      var t = (target.textContent || '').toLowerCase();
      target.classList.remove('is-ok', 'is-warn', 'is-bad');
      if (t.includes('liberado') || t.includes('pronto') || t.includes('ok')) target.classList.add('is-ok');
      else if (t.includes('espera') || t.includes('cooldown')) target.classList.add('is-warn');
      else if (t.includes('bloqueado') || t.includes('erro')) target.classList.add('is-bad');
    }).observe(target, {childList:true, characterData:true, subtree:true});
  }
})();
</script>
