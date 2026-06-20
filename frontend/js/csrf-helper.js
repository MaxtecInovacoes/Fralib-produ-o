// CSRF Helper - Protecao contra CSRF attacks
window.CSRFHelper = {
  token: null,

  // Buscar token CSRF do servidor
  async fetchToken() {
    try {
      const response = await fetch('/api/csrf-token', {
        method: 'GET',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        this.token = data.csrf_token;
        return this.token;
      }
    } catch (error) {
      console.error('[CSRF] Erro ao buscar token:', error);
    }
    return null;
  },

  // Obter token (busca se nao existir)
  async getToken() {
    if (!this.token) {
      await this.fetchToken();
    }
    return this.token;
  },

  // Adicionar token aos headers de uma requisicao
  async addToHeaders(headers = {}) {
    const token = await this.getToken();
    if (token) {
      headers['X-CSRF-Token'] = token;
    }
    return headers;
  },

  // Wrapper para fetch com CSRF automatico
  async fetch(url, options = {}) {
    // Adicionar CSRF token apenas para POST, PUT, DELETE, PATCH
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      options.headers = await this.addToHeaders(options.headers || {});
    }

    // Sempre incluir credentials para cookies
    options.credentials = 'include';

    return fetch(url, options);
  }
};

// Inicializar token ao carregar a pagina
document.addEventListener('DOMContentLoaded', () => {
  CSRFHelper.fetchToken();
});
