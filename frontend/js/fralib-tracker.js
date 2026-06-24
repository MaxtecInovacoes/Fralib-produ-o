/**
 * Fralib OS — Lead Tracking & Behavior Analytics (v2.0.0)
 *
 * Rastreamento de alta performance para a landing page.
 * Inclui: scroll depth, exit intent por seção, funil de conversão,
 * heatmap identifier e time-on-page segmentado.
 *
 * @typedef {Object} TrackPayload
 * @property {string} session_id
 * @property {string} evento
 * @property {string | null} valor_extra
 *
 * @typedef {Object} ScrollMilestone
 * @property {number} depth
 * @property {string} section_id
 * @property {number} timestamp
 */

(function() {
  'use strict';

  // ============================================================
  // CONFIGURAÇÃO
  // ============================================================
  const CONFIG = {
    /** Endpoint de tracking */
    ENDPOINT: '/api/track/landing',
    /** Marcos de scroll (%) */
    SCROLL_MILESTONES: [25, 50, 75, 90, 100],
    /** Tempo (ms) após o qual bounce é descartado */
    BOUNCE_THRESHOLD_MS: 8000,
    /** Throttle para scroll (ms) */
    SCROLL_THROTTLE_MS: 200,
    /** Heatmap provider (hotjar, clarity, none) */
    HEATMAP_PROVIDER: 'hotjar', // 'hotjar' | 'clarity' | 'none'
    /** Hotjar ID (substituir pelo real quando tiver) */
    HOTJAR_ID: 'YOUR_HOTJAR_ID', // TODO: configurar com ID real
  };

  // ============================================================
  // SESSION & STATE
  // ============================================================
  /**
   * Gera ou recupera session ID único por aba/sessão.
   * @returns {string}
   */
  function getSessionId() {
    let sid = sessionStorage.getItem('fralib_session_id');
    if (!sid) {
      sid = 'ss_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36);
      sessionStorage.setItem('fralib_session_id', sid);
    }
    return sid;
  }

  const STATE = {
    sessionId: getSessionId(),
    startTime: Date.now(),
    isBounce: true,
    sentEvents: new Set(),
    sentScrolls: new Set(),
    /** Última seção visível (para exit tracking) */
    lastVisibleSection: null,
    /** Marcos de funil alcançados */
    funnelSteps: {
      visit: false,
      scroll_25: false,
      scroll_50: false,
      cta_clicked: false,
      form_viewed: false,
      form_submitted: false,
    },
    /** Métricas de seção */
    sectionTimes: new Map(),
    currentSection: null,
    currentSectionStart: null,
  };

  // ============================================================
  // ENVIO DE EVENTOS
  // ============================================================
  /**
   * Envia evento via fetch (com dedup por sessão).
   * @param {string} evento
   * @param {string | number | null} valorExtra
   */
  function sendEvent(evento, valorExtra = null) {
    const key = `${evento}:${valorExtra}`;
    if (STATE.sentEvents.has(key)) return;
    STATE.sentEvents.add(key);

    const payload = {
      session_id: STATE.sessionId,
      evento: evento,
      valor_extra: valorExtra !== null ? String(valorExtra) : null
    };

    fetch(CONFIG.ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(() => {});
  }

  /**
   * Envia evento via sendBeacon (garante entrega no unload).
   * @param {string} evento
   * @param {string | number | null} valorExtra
   */
  function sendEventBeacon(evento, valorExtra = null) {
    const payload = JSON.stringify({
      session_id: STATE.sessionId,
      evento: evento,
      valor_extra: valorExtra !== null ? String(valorExtra) : null
    });

    if (navigator.sendBeacon) {
      navigator.sendBeacon(
        CONFIG.ENDPOINT,
        new Blob([payload], { type: 'application/json' })
      );
    } else {
      fetch(CONFIG.ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true
      }).catch(() => {});
    }
  }

  // ============================================================
  // INICIALIZAÇÃO
  // ============================================================
  sendEvent('view');
  STATE.funnelSteps.visit = true;

  const bounceTimer = setTimeout(() => {
    STATE.isBounce = false;
  }, CONFIG.BOUNCE_THRESHOLD_MS);

  // ============================================================
  // SCROLL DEPTH TRACKING (com identificação de seção)
  // ============================================================
  let scrollTicking = false;
  let lastScrollEvent = 0;

  window.addEventListener('scroll', function() {
    const now = Date.now();
    if (now - lastScrollEvent < CONFIG.SCROLL_THROTTLE_MS) return;
    lastScrollEvent = now;

    if (!scrollTicking) {
      window.requestAnimationFrame(() => {
        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (scrollHeight > 0) {
          const progress = Math.min(100, Math.max(0,
            Math.round((window.scrollY / scrollHeight) * 100)
          ));

          // Marcos de scroll
          CONFIG.SCROLL_MILESTONES.forEach(depth => {
            if (progress >= depth && !STATE.sentScrolls.has(depth)) {
              STATE.sentScrolls.add(depth);
              const sectionId = getVisibleSection();
              sendEvent('scroll_depth', `${depth}|${sectionId || 'unknown'}`);

              // Funil
              if (depth >= 25 && !STATE.funnelSteps.scroll_25) {
                STATE.funnelSteps.scroll_25 = true;
                sendEvent('funnel_scroll_25', sectionId);
              }
              if (depth >= 50 && !STATE.funnelSteps.scroll_50) {
                STATE.funnelSteps.scroll_50 = true;
                sendEvent('funnel_scroll_50', sectionId);
              }

              // Bounce cancelado
              if (depth >= 25) {
                STATE.isBounce = false;
                clearTimeout(bounceTimer);
              }
            }
          });
        }
        scrollTicking = false;
      });
      scrollTicking = true;
    }
  }, { passive: true });

  /**
   * Identifica qual seção está mais visível no viewport.
   * @returns {string | null}
   */
  function getVisibleSection() {
    const sections = document.querySelectorAll('section[id], [data-section-id]');
    let maxVisible = 0;
    let visibleId = null;

    sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const visibleTop = Math.max(0, rect.top);
      const visibleBottom = Math.min(viewportHeight, rect.bottom);
      const visibleHeight = Math.max(0, visibleBottom - visibleTop);
      const visibilityRatio = visibleHeight / viewportHeight;

      if (visibilityRatio > maxVisible && visibilityRatio > 0.3) {
        maxVisible = visibilityRatio;
        visibleId = section.id || section.getAttribute('data-section-id');
      }
    });

    return visibleId;
  }

  // ============================================================
  // SECTION VISIBILITY TRACKING (exit por seção)
  // ============================================================
  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        const sectionId = entry.target.id || entry.target.getAttribute('data-section-id');
        if (!sectionId) return;

        if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
          // Entrou na seção
          STATE.lastVisibleSection = sectionId;
          STATE.currentSection = sectionId;
          STATE.currentSectionStart = Date.now();
          sendEvent('section_view', sectionId);
        }
      });
    },
    { threshold: [0.25, 0.5, 0.75, 1.0] }
  );

  document.querySelectorAll('section[id], [data-section-id]').forEach(section => {
    sectionObserver.observe(section);
  });

  // ============================================================
  // CLICK TRACKING (com funil)
  // ============================================================
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    const button = e.target.closest('button');

    if (link) {
      const href = link.getAttribute('href') || '';
      const text = link.innerText.trim();
      const sectionId = STATE.currentSection || 'unknown';
      STATE.isBounce = false;
      clearTimeout(bounceTimer);

      // WhatsApp
      if (href.includes('wa.me')) {
        sendEvent('click_whatsapp', `${sectionId}|${text}`);
        sendEvent('funnel_cta_clicked', `whatsapp|${sectionId}`);
        STATE.funnelSteps.cta_clicked = true;
        if (window.fbq) window.fbq('track', 'Contact');
      }
      // Planos
      else if (href.includes('plano=trial')) {
        sendEvent('click_plano_trial', `${sectionId}|${text}`);
        sendEvent('funnel_cta_clicked', `trial|${sectionId}`);
        STATE.funnelSteps.cta_clicked = true;
        if (window.fbq) window.fbq('track', 'Lead');
      }
      else if (href.includes('plano=starter')) {
        sendEvent('click_plano_starter', `${sectionId}|${text}`);
        sendEvent('funnel_cta_clicked', `starter|${sectionId}`);
        STATE.funnelSteps.cta_clicked = true;
        if (window.fbq) window.fbq('track', 'InitiateCheckout', { value: 97.00, currency: 'BRL' });
      }
      else if (href.includes('plano=pro')) {
        sendEvent('click_plano_pro', `${sectionId}|${text}`);
        sendEvent('funnel_cta_clicked', `pro|${sectionId}`);
        STATE.funnelSteps.cta_clicked = true;
        if (window.fbq) window.fbq('track', 'InitiateCheckout', { value: 197.00, currency: 'BRL' });
      }
      // Signup
      else if (href.includes('/login?signup=1')) {
        const location = link.closest('#navbar') ? 'nav' :
                         link.closest('#hero') ? 'hero' :
                         link.closest('#cta-final') ? 'cta-final' : 'other';
        sendEvent('click_signup', `${location}|${text}`);
        sendEvent('funnel_cta_clicked', `signup|${location}`);
        STATE.funnelSteps.cta_clicked = true;
        if (window.fbq) window.fbq('track', 'Lead');
      }
      // Scroll to section
      else if (href.startsWith('#')) {
        sendEvent('click_nav_anchor', `${href}|${text}`);
      }
    }

    // Botão genérico (sem link)
    if (button && !link) {
      const text = button.innerText.trim();
      const sectionId = STATE.currentSection || 'unknown';
      sendEvent('click_button', `${sectionId}|${text}`);
    }
  });

  // ============================================================
  // FORM TRACKING
  // ============================================================
  // View do formulário (quando entra no viewport)
  const formObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
          if (!STATE.funnelSteps.form_viewed) {
            STATE.funnelSteps.form_viewed = true;
            sendEvent('funnel_form_viewed', entry.target.id || 'betaForm');
          }
        }
      });
    },
    { threshold: 0.5 }
  );

  document.querySelectorAll('form').forEach(form => {
    formObserver.observe(form);
  });

  // Submit do formulário
  document.addEventListener('submit', function(e) {
    if (e.target.id === 'betaForm' || e.target.classList.contains('beta-form')) {
      STATE.isBounce = false;
      clearTimeout(bounceTimer);
      sendEvent('convert_beta_registration', 'WhatsApp Group');
      sendEvent('funnel_form_submitted', 'betaForm');
      STATE.funnelSteps.form_submitted = true;
      if (window.fbq) window.fbq('track', 'CompleteRegistration');
    }
  });

  // ============================================================
  // EXIT TRACKING (saída por seção)
  // ============================================================
  let exitSent = false;

  function sendExit() {
    if (exitSent) return;
    exitSent = true;

    const timeSpent = Math.round((Date.now() - STATE.startTime) / 1000);
    sendEventBeacon('time_spent', timeSpent);

    // Exit por seção
    if (STATE.lastVisibleSection) {
      sendEventBeacon('exit_section', STATE.lastVisibleSection);
    }

    // Bounce
    if (STATE.isBounce && timeSpent < 8) {
      sendEventBeacon('bounce', timeSpent);
    }

    // Funil completo
    const funnelPath = Object.entries(STATE.funnelSteps)
      .filter(([_, reached]) => reached)
      .map(([step]) => step)
      .join('>');
    sendEventBeacon('funnel_completed', funnelPath);
  }

  window.addEventListener('pagehide', sendExit);
  window.addEventListener('beforeunload', sendExit);

  // ============================================================
  // HEATMAP INTEGRATION
  // ============================================================
  if (CONFIG.HEATMAP_PROVIDER === 'hotjar' && CONFIG.HOTJAR_ID !== 'YOUR_HOTJAR_ID') {
    // Hotjar snippet (apenas se ID configurado)
    (function(h,o,t,j,a,r){
      h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};
      h._hjSettings={hjid:CONFIG.HOTJAR_ID,hjsv:6};
      a=o.getElementsByTagName('head')[0];
      r=o.createElement('script');r.async=1;
      r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;
      a.appendChild(r);
    })(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');
  }

  // ============================================================
  // PUBLIC API (para debug em console)
  // ============================================================
  window.__fralibTracker = {
    getState: () => ({ ...STATE, sentScrolls: Array.from(STATE.sentScrolls) }),
    getFunnel: () => STATE.funnelSteps,
    forceEvent: sendEvent,
    forceBeacon: sendEventBeacon,
  };
})();
