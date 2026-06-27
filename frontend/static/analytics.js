/**
 * FraLib Analytics - Sistema de Tracking e Métricas
 *
 * Features:
 * - UTM Tracking automático
 * - Eventos de conversão
 * - Funil de conversão
 * - KPIs em tempo real
 * - Pixel e Clarity integration
 */

class FraLibAnalytics {
  constructor() {
    this.utmParams = this.extractUTMParams();
    this.sessionId = this.generateSessionId();
    this.events = [];
    this.userId = null;
    this.pixelId = '1022692323751129';
    this.clarityId = 'wv8xiy7kvk';

    this.init();
  }

  init() {
    // Track page view
    this.track('page_view', {
      page: window.location.pathname,
      title: document.title,
      timestamp: Date.now()
    });

    // Track UTM params
    if (Object.keys(this.utmParams).length > 0) {
      this.track('utm_view', this.utmParams);
    }

    // Track form submissions
    this.trackForms();

    // Track clicks
    this.trackClicks();

    // Track scroll depth
    this.trackScrollDepth();

    // Initialize Pixel and Clarity
    this.initPixel();
    this.initClarity();

    // Auto-send events every 30s
    setInterval(() => this.flushEvents(), 30000);
  }

  extractUTMParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const utm = {};

    const utmKeys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];

    utmKeys.forEach(key => {
      const value = urlParams.get(key);
      if (value) {
        utm[key] = value;
      }
    });

    return utm;
  }

  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  track(eventName, data = {}) {
    const event = {
      id: this.generateEventId(),
      session_id: this.sessionId,
      user_id: this.userId,
      event_name: eventName,
      data: {
        ...data,
        utm: this.utmParams,
        timestamp: Date.now(),
        url: window.location.href,
        referrer: document.referrer,
        user_agent: navigator.userAgent,
        screen_resolution: `${window.screen.width}x${window.screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`
      }
    };

    this.events.push(event);

    // Auto-flush if > 10 events
    if (this.events.length >= 10) {
      this.flushEvents();
    }
  }

  generateEventId() {
    return 'evt_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  trackForms() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
      form.addEventListener('submit', (e) => {
        const formData = new FormData(form);
        const data = {};

        formData.forEach((value, key) => {
          data[key] = value;
        });

        this.track('form_submit', {
          form_id: form.id || 'unknown',
          form_action: form.action,
          form_method: form.method,
          data: data
        });
      });
    });
  }

  trackClicks() {
    document.addEventListener('click', (e) => {
      const target = e.target;

      // Track button clicks
      if (target.tagName === 'BUTTON' || target.tagName === 'A') {
        this.track('click', {
          element: target.tagName,
          id: target.id || null,
          class: target.className || null,
          text: target.textContent.trim().substring(0, 100),
          url: target.href || null
        });
      }

      // Track specific elements
      if (target.closest('[data-track]')) {
        const tracked = target.closest('[data-track]');
        this.track('tracked_click', {
          track_id: tracked.dataset.track,
          element: target.tagName,
          text: tracked.textContent.trim().substring(0, 100)
        });
      }
    });
  }

  trackScrollDepth() {
    let maxScroll = 0;
    let scrollTimer;

    window.addEventListener('scroll', () => {
      clearTimeout(scrollTimer);

      const scrollPercent = Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100);

      if (scrollPercent > maxScroll) {
        maxScroll = scrollPercent;

        this.track('scroll_depth', {
          depth: scrollPercent,
          max_depth: maxScroll
        });
      }

      scrollTimer = setTimeout(() => {
        this.track('scroll_complete', {
          max_depth: maxScroll
        });
      }, 1000);
    });
  }

  initPixel() {
    // Meta Pixel
    !function(f,b,e,v,n,t,s)
    {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};
    if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
    n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];
    s.parentNode.insertBefore(t,s)}(window, document,'script',
    'https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', this.pixelId);
    fbq('track', 'PageView');
  }

  initClarity() {
    // Microsoft Clarity
    (function(c,l,a,r,i,t,y){
        c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", this.clarityId);
  }

  // Conversion tracking
  trackLeadGeneration(formData) {
    this.track('lead_generated', {
      form_data: formData,
      utm: this.utmParams
    });

    // Track to Pixel
    fbq('track', 'Lead');
  }

  trackTrialStart(userId) {
    this.userId = userId;
    this.track('trial_started', {
      user_id: userId,
      utm: this.utmParams
    });

    // Track to Pixel
    fbq('track', 'StartTrial');
  }

  trackPayment(orderData) {
    this.track('payment_completed', {
      order_id: orderData.id,
      amount: orderData.amount,
      currency: orderData.currency,
      utm: this.utmParams
    });

    // Track to Pixel
    fbq('track', 'Purchase', {
      value: orderData.amount,
      currency: orderData.currency
    });
  }

  // Funnel tracking
  trackFunnelStep(step, data = {}) {
    this.track('funnel_step', {
      step: step,
      utm: this.utmParams,
      ...data
    });
  }

  // Get analytics data
  async getFunnelData(period = '7d') {
    try {
      const response = await fetch(`/api/analytics/funnel?period=${period}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching funnel data:', error);
      return null;
    }
  }

  async getUTMData() {
    try {
      const response = await fetch('/api/analytics/utm');
      return await response.json();
    } catch (error) {
      console.error('Error fetching UTM data:', error);
      return null;
    }
  }

  async getKPIData() {
    try {
      const response = await fetch('/api/analytics/kpi');
      return await response.json();
    } catch (error) {
      console.error('Error fetching KPI data:', error);
      return null;
    }
  }

  // Flush events to server
  async flushEvents() {
    if (this.events.length === 0) return;

    const eventsToSend = [...this.events];
    this.events = [];

    try {
      const response = await fetch('/api/analytics/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          events: eventsToSend
        })
      });

      if (!response.ok) {
        // Re-queue events on failure
        this.events.unshift(...eventsToSend);
      }
    } catch (error) {
      console.error('Error sending events:', error);
      // Re-queue events on error
      this.events.unshift(...eventsToSend);
    }
  }
}

// Initialize analytics when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.fralibAnalytics = new FraLibAnalytics();
});

// UTM Builder utility
class UTMBuilder {
  static buildURL(baseURL, utmParams) {
    const url = new URL(baseURL);
    const params = new URLSearchParams(url.search);

    Object.entries(utmParams).forEach(([key, value]) => {
      params.set(key, value);
    });

    url.search = params.toString();
    return url.toString();
  }

  static generateUTM(source, medium, campaign, content = '', term = '') {
    const utm = {
      utm_source: source,
      utm_medium: medium,
      utm_campaign: campaign
    };

    if (content) utm.utm_content = content;
    if (term) utm.utm_term = term;

    return utm;
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { FraLibAnalytics, UTMBuilder };
}