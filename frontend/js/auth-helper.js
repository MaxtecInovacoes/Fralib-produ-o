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
  }
};
window.authFetch = window.AuthHelper.authFetch.bind(window.AuthHelper);
