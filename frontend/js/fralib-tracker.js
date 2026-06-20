/**
 * Fralib OS — Lead Tracking & Behavior Analytics (v1.0.0)
 * Rastreamento de alta performance para a landing page.
 */
(function() {
  'use strict';

  // 1. Geração e Persistência do Session ID
  function getSessionId() {
    let sid = sessionStorage.getItem('fralib_session_id');
    if (!sid) {
      sid = 'ss_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36);
      sessionStorage.setItem('fralib_session_id', sid);
    }
    return sid;
  }
  const sessionId = getSessionId();
  const startTime = Date.now();
  let isBounce = true;
  let sentEvents = new Set();

  // 2. Transmissão de Eventos (API Interna Fralib OS)
  function sendEvent(evento, valorExtra = null) {
    const key = `${evento}:${valorExtra}`;
    if (sentEvents.has(key)) return; // Evita duplicações idênticas na mesma sessão
    sentEvents.add(key);

    const payload = {
      session_id: sessionId,
      evento: evento,
      valor_extra: valorExtra ? String(valorExtra) : null
    };

    fetch('/api/track/landing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true // Garante o envio mesmo se a aba estiver fechando
    }).catch(() => {});
  }

  // Envio de Eventos Rápidos no Unload/Pagehide
  function sendEventBeacon(evento, valorExtra = null) {
    const payload = JSON.stringify({
      session_id: sessionId,
      evento: evento,
      valor_extra: valorExtra ? String(valorExtra) : null
    });

    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/track/landing', new Blob([payload], { type: 'application/json' }));
    } else {
      fetch('/api/track/landing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true
      }).catch(() => {});
    }
  }

  // 3. Inicialização e Page View
  sendEvent('view');

  // Cancelamento do Bounce após 8 segundos de permanência ativa
  const bounceTimer = setTimeout(() => {
    isBounce = false;
  }, 8000);

  // 4. Rastreamento de Rolagem Throttled & Passive
  let ticking = false;
  const sentScrolls = new Set();

  window.addEventListener('scroll', function() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (scrollHeight > 0) {
          const progress = Math.min(100, Math.max(0, Math.round((window.scrollY / scrollHeight) * 100)));
          
          [25, 50, 75, 100].forEach(depth => {
            if (progress >= depth && !sentScrolls.has(depth)) {
              sentScrolls.add(depth);
              sendEvent('scroll_depth', depth);
              if (depth >= 25) {
                isBounce = false;
                clearTimeout(bounceTimer);
              }
            }
          });
        }
        ticking = false;
      });
      ticking = true;
    }
  }, { passive: true });

  // 5. Mapeamento Inteligente de Cliques (Event Delegation)
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    
    if (link) {
      const href = link.getAttribute('href') || '';
      const text = link.innerText.trim();
      isBounce = false;
      clearTimeout(bounceTimer);

      if (href.includes('wa.me')) {
        sendEvent('click_agency_whatsapp', text);
        if (window.fbq) window.fbq('track', 'Contact');
      } else if (href.includes('plano=trial')) {
        sendEvent('click_plano_trial', text);
        if (window.fbq) window.fbq('track', 'Lead');
      } else if (href.includes('plano=starter')) {
        sendEvent('click_plano_starter', text);
        if (window.fbq) window.fbq('track', 'InitiateCheckout', { value: 97.00, currency: 'BRL' });
      } else if (href.includes('plano=pro')) {
        sendEvent('click_plano_pro', text);
        if (window.fbq) window.fbq('track', 'InitiateCheckout', { value: 197.00, currency: 'BRL' });
      } else if (href.includes('/login?signup=1')) {
        if (link.closest('#navbar')) {
          sendEvent('click_nav_cta', text);
        } else {
          sendEvent('click_hero_cta', text);
        }
        if (window.fbq) window.fbq('track', 'Lead');
      }
    }
  });

  // 6. Conversão do Formulário de Vagas Beta
  document.addEventListener('submit', function(e) {
    if (e.target.id === 'betaForm') {
      isBounce = false;
      clearTimeout(bounceTimer);
      sendEvent('convert_beta_registration', 'WhatsApp Group');
      if (window.fbq) window.fbq('track', 'CompleteRegistration');
    }
  });

  // 7. Envio de Métricas de Saída (Tempo de Permanência e Bounce Real)
  window.addEventListener('pagehide', function() {
    const timeSpent = Math.round((Date.now() - startTime) / 1000);
    sendEventBeacon('time_spent', timeSpent);

    if (isBounce && timeSpent < 8) {
      sendEventBeacon('bounce', timeSpent);
    }
  });
})();
