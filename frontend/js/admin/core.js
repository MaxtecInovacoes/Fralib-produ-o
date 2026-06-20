/**
 * FraLib Admin - Core State & Auth
 * Global state, authentication guard, and XSS helpers
 * Auto-generated from _scripts.html - DO NOT EDIT DIRECTLY
 */
<script>
/* ══ ESTADO GLOBAL ════════════════════════════════════════════════ */
var periodoAtual = 'mes';
var chartsInstances = {};
var leadAtualModal = null;
var lastStatus = {};
var crmPeriodAtual = 'tudo';
var crmSearchAtual = '';
var utiPeriodAtual = 'tudo';
var utiSearchAtual = '';
var _crmDataCache = null;
var _utiDataCache = null;
var _pipelinePermissionState = null;

/* ══ AUTH GUARD ═══════════════════════════════════════════════════ */
(function(){
  var token = localStorage.getItem('fralib_token');
  var apiUrl = window.location.protocol + '//' + window.location.host + '/api/auth/me';
  var headers = {};
  if (token) headers.Authorization = 'Bearer ' + token;

  fetch(apiUrl, {
    headers: headers,
    credentials: 'include'
  })
    .then(async function(r){
      var data = await r.json().catch(function(){ return {}; });
      if (!r.ok) {
        console.error('[Auth] Status:', r.status, r.statusText);
      }
      if (r.status === 401 || (r.status === 403 && data.detail === 'Not authenticated')) {
        console.warn('[Auth] Sessao invalida, redirecionando para login');
        localStorage.removeItem('fralib_token');
        window.location.href = '/login';
        return data;
      }
      if (r.status === 403) {
        alert('Seu plano venceu. Renove para continuar.');
        window.location.href = '/planos';
      }
      return data;
    })
    .then(function(data){
      if (data && data.email) {
        console.log('[Auth] Usuário autenticado:', data.email);
      }
    })
    .catch(function(err){
      console.error('[Auth] Erro ao validar token:', err);
    });
})();

/* ══ HELPER FETCH AUTENTICADO ═════════════════════════════════════ */
async function authFetch(url, opts) {
  return window.AuthHelper.authFetch(url, opts || {});
}

/* ══ SANITIZAÇÃO XSS ═══════════════════════════════════════════════ */
function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function sanitizeUrl(url) {
  if (!url) return '';
  var trimmed = (url || '').trim();
  if (trimmed.toLowerCase().startsWith('javascript:') ||
      trimmed.toLowerCase().startsWith('data:') ||
      trimmed.toLowerCase().startsWith('vbscript:')) {
    return '#';
  }
  return trimmed;
}
</script>
