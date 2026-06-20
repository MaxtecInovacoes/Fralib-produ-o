// Auth Helper
// @ts-check
window.AuthHelper = {
  getToken: function() {
    return localStorage.getItem('fralib_token');
  },
  toApiUrl: function(url) {
    if (!url) return url;
    if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
    if (url.charAt(0) === '/') {
      return window.location.protocol + '//' + window.location.host + url;
    }
    return url;
  },
  authFetch: async function(url, options = {}) {
    const token = this.getToken();
    const requestOptions = Object.assign({}, options);
    requestOptions.headers = Object.assign({}, options.headers || {});
    if (token) requestOptions.headers['Authorization'] = 'Bearer ' + token;
    requestOptions.credentials = 'include';
    const method = (requestOptions.method || 'GET').toUpperCase();
    if (window.CSRFHelper && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      requestOptions.headers = await window.CSRFHelper.addToHeaders(requestOptions.headers);
    }
    return fetch(this.toApiUrl(url), requestOptions).then(function(response) {
      if (response.status === 401) {
        window.__fralibAuthExpired = true;
        localStorage.removeItem('fralib_token');
        window.location.href = '/login';
        throw new Error('Unauthorized');
      }
      return response;
    }).catch(function(err) {
      console.error('[authFetch] Erro na requisicao:', url, err);
      throw err;
    });
  },
  register: async function(nome, email, password, legalAccepted = false) {
    const r = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        email: email,
        password: password,
        nome: nome,
        accept_terms: legalAccepted,
        accept_privacy: legalAccepted
      })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Erro ao criar conta');
    return d;
  },
  login: async function(email, password) {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: email, password: password })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Erro ao fazer login');
    if (d.access_token) localStorage.removeItem('fralib_token');
    return d;
  },
  logout: async function() {
    try {
      const headers = {};
      if (window.CSRFHelper) await window.CSRFHelper.addToHeaders(headers);
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: headers,
        credentials: 'include'
      });
    } catch (_) {}
    ['fralib_token', 'fralib_user', 'fralib_onboarded'].forEach(function(k) {
      localStorage.removeItem(k);
    });
    window.location.href = '/login';
  }
};
window.authFetch = window.AuthHelper.authFetch.bind(window.AuthHelper);
