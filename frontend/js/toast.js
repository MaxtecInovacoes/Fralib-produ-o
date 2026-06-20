// Toast Notifications
(function () {
  const COLORS = {
    success: 'rgba(34, 197, 94, 0.95)',
    error: 'rgba(239, 68, 68, 0.95)',
    warning: 'rgba(245, 158, 11, 0.95)',
    info: 'rgba(59, 130, 246, 0.95)',
    default: 'rgba(147, 51, 234, 0.95)'
  };

  function renderToast(message, kind, duration) {
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + (kind || 'default');
    toast.textContent = String(message || '');
    toast.style.background = COLORS[kind] || COLORS.default;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, duration || 3000);
    return toast;
  }

  window.mostrarToast = function (message, duration = 3000) {
    return renderToast(message, 'default', duration);
  };

  window.Toast = window.Toast || {};
  window.Toast.show = function (message, kind = 'info', duration = 3000) {
    return renderToast(message, kind, duration);
  };
  window.Toast.success = function (message, duration = 3000) {
    return renderToast(message, 'success', duration);
  };
  window.Toast.error = function (message, duration = 3000) {
    return renderToast(message, 'error', duration);
  };
  window.Toast.warning = function (message, duration = 3000) {
    return renderToast(message, 'warning', duration);
  };
  window.Toast.info = function (message, duration = 3000) {
    return renderToast(message, 'info', duration);
  };
})();
