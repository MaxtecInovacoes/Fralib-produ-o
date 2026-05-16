// Auth Helper
window.AuthHelper = {
  getToken: function() {
    return localStorage.getItem('fralib_token');
  },
  authFetch: async function(url, options = {}) {
    const token = this.getToken();
    if (!token) {
      window.location.href = '/login';
      throw new Error('No token');
    }
    options.headers = options.headers || {};
    options.headers['Authorization'] = 'Bearer ' + token;
    return fetch(url, options);
  },
  register: async function(nome, email, password) {
    const r = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password, nome: nome })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Erro ao criar conta');
    return d;
  },
  login: async function(email, password) {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, password: password })
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Erro ao fazer login');
    if (d.access_token) localStorage.setItem('fralib_token', d.access_token);
    return d;
  }
};
window.authFetch = window.AuthHelper.authFetch.bind(window.AuthHelper);
