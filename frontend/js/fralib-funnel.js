/**
 * FraLib OS — UTM & Lead Funnel Tracker v1.0.0
 *
 * Rastreia visitante desde o primeiro acesso ate a primeira acao no app.
 * Cruza utm_source/medium/campaign com cada etapa do funil:
 *   visit -> cta_clicked -> login_start -> signup_done -> whatsapp_joined -> activated
 *
 * Tudo persistido em /api/track/funnel (POST JSON) na tabela lead_funnel.
 *
 * @typedef {Object} UTMParams
 * @property {string|null} source
 * @property {string|null} medium
 * @property {string|null} campaign
 * @property {string|null} content
 * @property {string|null} referer
 * @property {string} landingPath
 *
 * @typedef {Object} FunnelState
 * @property {string} sessionId
 * @property {UTMParams} utm
 * @property {string} etapaAtual
 * @property {number} tsEntrouLanding
 */

(function () {
  'use strict';

  const ENDPOINT = '/api/track/funnel';
  const SESSION_KEY = 'fralib_utm_session';
  const STATE_KEY = 'fralib_utm_state';
  const ENDPOINT_FALLBACK = '/api/track/landing'; // pra nao quebrar se backend ainda nao tem /api/track/funnel

  // ============================================================
  // 1. CAPTURA UTM (uma vez por sessao, persistido em sessionStorage)
  // ============================================================
  /**
   * @returns {UTMParams}
   */
  function captureUTM() {
    const params = new URLSearchParams(window.location.search);
    const source = params.get('utm_source');
    const medium = params.get('utm_medium');
    const campaign = params.get('utm_campaign');
    const content = params.get('utm_content');

    // Se ja capturou nesta sessao, reusar (senao perde ao navegar)
    const stored = sessionStorage.getItem(SESSION_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // se ja tem utm_source definido, mantem (nao sobrescreve com "direto")
        if (parsed.source) return parsed;
      } catch (_) {}
    }

    const utm = {
      source: source || detectSourceFromReferer(document.referrer) || 'direto',
      medium: medium || (source ? 'unknown' : 'organico'),
      campaign: campaign || 'none',
      content: content || null,
      referer: document.referrer || null,
      landingPath: window.location.pathname,
    };

    sessionStorage.setItem(SESSION_KEY, JSON.stringify(utm));
    return utm;
  }

  /**
   * Detecta origem via referer quando UTM nao foi passado.
   * @param {string} ref
   * @returns {string|null}
   */
  function detectSourceFromReferer(ref) {
    if (!ref) return null;
    try {
      const u = new URL(ref);
      const host = u.hostname.toLowerCase();
      if (host.includes('facebook.com') || host.includes('fb.com')) return 'facebook';
      if (host.includes('instagram.com') || host.includes('l.instagram')) return 'instagram';
      if (host.includes('google.com')) return 'google';
      if (host.includes('whatsapp.com') || host.includes('wa.me')) return 'whatsapp';
      if (host.includes('t.me') || host.includes('telegram')) return 'telegram';
      if (host.includes('twitter.com') || host.includes('x.com')) return 'twitter';
      if (host.includes('linkedin.com')) return 'linkedin';
      if (host.includes('youtube.com') || host.includes('youtu.be')) return 'youtube';
      if (host.includes('tiktok.com')) return 'tiktok';
      return 'outro';
    } catch (_) {
      return null;
    }
  }

  // ============================================================
  // 2. ENVIO DE EVENTOS DO FUNIL
  // ============================================================
  /**
   * @param {string} etapa - visit|cta_clicked|login_start|signup_done|whatsapp_joined|activated
   * @param {Object} [extra] - {whatsapp, email, nome, user_id, cta_text, ...}
   */
  function trackFunnel(etapa, extra = {}) {
    const utm = captureUTM();
    const sessionId = getSessionId();

    const payload = {
      session_id: sessionId,
      etapa,
      utm_source: utm.source,
      utm_medium: utm.medium,
      utm_campaign: utm.campaign,
      utm_content: utm.content,
      referer: utm.referrer,
      landing_path: utm.landingPath,
      user_id: extra.user_id || null,
      whatsapp: extra.whatsapp || null,
      email: extra.email || null,
      nome: extra.nome || null,
      cta_text: extra.cta_text || null,
      url: window.location.href,
      ts: Date.now(),
    };

    // Enviar via beacon (nao bloqueia navegacao)
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
      navigator.sendBeacon(ENDPOINT, blob);
    } else {
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {
        // fallback pro endpoint antigo (analytics basico)
        fetch(ENDPOINT_FALLBACK, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...payload, evento: `funnel_${etapa}` }),
          keepalive: true,
        }).catch(() => {});
      });
    }

    // tambem salvar localmente pra usar em form submit
    const state = JSON.parse(sessionStorage.getItem(STATE_KEY) || '{}');
    state.etapa = etapa;
    state.ts = Date.now();
    sessionStorage.setItem(STATE_KEY, JSON.stringify(state));
  }

  // ============================================================
  // 3. SESSION ID (reutiliza se ja existir)
  // ============================================================
  /**
   * @returns {string}
   */
  function getSessionId() {
    let sid = sessionStorage.getItem('fralib_sid');
    if (!sid) {
      sid = 's_' + Math.random().toString(36).slice(2, 11) + '_' + Date.now().toString(36);
      sessionStorage.setItem('fralib_sid', sid);
    }
    return sid;
  }

  // ============================================================
  // 4. INTERCEPTADORES AUTOMATICOS
  // ============================================================

  // 4.1 - Registrar "visit" no primeiro carregamento
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => trackFunnel('visit'));
  } else {
    trackFunnel('visit');
  }

  // 4.2 - Detectar cliques em CTAs
  document.addEventListener('click', (e) => {
    const el = e.target.closest('a, button');
    if (!el) return;

    const text = (el.innerText || el.textContent || '').trim().slice(0, 80);
    const href = el.href || '';

    // CTAs principais: links para /login, /signup, /cadastro
    if (
      href.includes('/login') ||
      href.includes('/signup') ||
      href.includes('/cadastro') ||
      href.includes('/registro') ||
      href.includes('/comecar') ||
      href.includes('wa.me/') ||
      href.includes('whatsapp.com') ||
      /come[çc]ar|assinar|cadastr|criar conta|quero|testar/i.test(text)
    ) {
      trackFunnel('cta_clicked', { cta_text: text });
    }
  }, true);

  // 4.3 - Detectar submit de formularios (login/signup/cadastro)
  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!form) return;
    const formId = (form.id || '').toLowerCase();
    const formAction = (form.action || '').toLowerCase();

    if (
      formId.includes('signup') ||
      formId.includes('cadastro') ||
      formId.includes('registro') ||
      formId.includes('beta') ||
      formAction.includes('/signup') ||
      formAction.includes('/cadastro') ||
      formAction.includes('/register')
    ) {
      const data = new FormData(form);
      const whatsapp = data.get('whatsapp') || data.get('phone') || data.get('telefone') || null;
      const email = data.get('email') || null;
      const nome = data.get('nome') || data.get('name') || null;
      trackFunnel('signup_done', { whatsapp, email, nome });
    } else if (formId.includes('login') || formAction.includes('/login')) {
      trackFunnel('login_start');
    }
  }, true);

  // 4.4 - Detectar entrada em pagina /grupo ou /whatsapp
  function checkWhatsappJoin() {
    const path = window.location.pathname.toLowerCase();
    if (
      path.includes('/grupo') ||
      path.includes('/whatsapp') ||
      path.includes('/comunidade') ||
      path.includes('/onboarding') ||
      path.includes('/welcome')
    ) {
      trackFunnel('whatsapp_joined');
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkWhatsappJoin);
  } else {
    checkWhatsappJoin();
  }

  // 4.5 - Detectar primeira acao no app (criou site, gerou lead, etc)
  window.addEventListener('fralib:activated', (e) => {
    trackFunnel('activated', e.detail || {});
  });

  // ============================================================
  // 5. API PUBLICA
  // ============================================================
  window.FralibFunnel = {
    track: trackFunnel,
    getUTM: captureUTM,
    getSessionId,
    /** Helper pra backend emitir evento customizado */
    emitActivated: function (data) {
      window.dispatchEvent(new CustomEvent('fralib:activated', { detail: data }));
    },
  };
})();