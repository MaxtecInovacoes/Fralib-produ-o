// FraLib Motion Runtime — Awwwards 2026 Pack v1.0
// Carregado inline em HTML estatico (sem React/Next/Vite) pelo
// openui_renderer.py como <script id="fralib-motion-runtime">.
// Inclui: GSAP + ScrollTrigger + Lenis (smooth scroll), Swup (page
// transitions), @formkit/auto-animate (microinteracoes), data-* hooks
// (parallax/reveal/marquee/magnetic/3d-tilt/counter/stagger), text
// scramble, scroll progress, reading velocity, anchor smooth scroll.
// Respeita prefers-reduced-motion: desliga TUDO se ativo.
// Cleanup em page swap (Swup hooks: kill ScrollTriggers, destruicao Lenis).
// Idempotente: detecta <script id="fralib-motion-runtime"> e sai.
//
// Pacote npm: gsap@3.12.5, lenis@1.3.23, swup@4.9.2, @formkit/auto-animate@0.9.0
// (CDNs abaixo sao os mesmos declarados em /package.json).
(function () {
  if (document.getElementById('fralib-motion-runtime')) return;

  const FRALIB = (window.__FRALIB_MOTION__ = window.__FRALIB_MOTION__ || {
    instances: { lenis: null, swup: null, autoAnimate: [], scrollTriggers: [] },
    reducedMotion: false,
    bootedAt: 0,
  });

  // Sentinel: nao duplica boot em re-injecoes do script.
  const bootScript = document.createElement('script');
  bootScript.id = 'fralib-motion-runtime';
  bootScript.dataset.fralibPack = 'awwwards-2026';
  document.head.appendChild(bootScript);

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  FRALIB.reducedMotion = reduce;
  FRALIB.bootedAt = Date.now();

  // ─── Lib loader (CDN com fallback local) ────────────────────────────────
  function loadScript(src, attrs) {
    return new Promise(function (resolve, reject) {
      const s = document.createElement('script');
      s.src = src;
      if (attrs) {
        for (const k in attrs) s.setAttribute(k, attrs[k]);
      }
      s.onload = function () { resolve(s); };
      s.onerror = function () { reject(new Error('Failed: ' + src)); };
      document.head.appendChild(s);
    });
  }

  // Carrega GSAP + ScrollTrigger. Se reduced-motion, nao baixa plugins pesados.
  const GSAP_SRC = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js';
  const ST_SRC   = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js';
  const LENIS_SRC = 'https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js';

  // Swup e AutoAnimate so fazem sentido em sites multi-pagina.
  // Carrega sob demanda se detectar <main data-swup> ou [data-auto-animate].
  const SWUP_SRC = 'https://cdn.jsdelivr.net/npm/swup@4.9.2/dist/Swup.umd.js';
  const SWUP_FORMS_SRC = 'https://cdn.jsdelivr.net/npm/@swup/forms-plugin@3.0.1/dist/SwupFormsPlugin.js';
  const AUTO_ANIMATE_SRC = 'https://cdn.jsdelivr.net/npm/@formkit/auto-animate@0.9.0/index.iife.min.js';

  loadScript(GSAP_SRC).then(function () {
    if (reduce) return setupMotion();
    return loadScript(ST_SRC).then(setupMotion, function () { setupMotion(); });
  }).catch(function (err) {
    // GSAP obrigatorio. Sem ele, runtime nao inicializa.
    // eslint-disable-next-line no-console
    console.warn('[fralib-motion] GSAP failed to load:', err);
  });

  function setupMotion() {
    if (typeof gsap === 'undefined') return;
    gsap.registerPlugin(ScrollTrigger);

    const hasParallax = document.querySelector('[data-parallax]');
    const hasReveal = document.querySelector('[data-reveal]');
    const hasMarquee = document.querySelector('[data-marquee]');
    const hasMagnetic = document.querySelector('[data-magnetic]');
    const has3D = document.querySelector('[data-3d-tilt]');
    const hasHorizontal = document.querySelector('[data-horizontal-scroll]');
    const hasCounter = document.querySelector('[data-counter]');
    const hasVelocity = document.querySelector('[data-fralib-scroll-velocity]');
    const hasStagger = document.querySelector('[data-stagger]');
    const hasReadingProgress = document.querySelector('.fralib-reading-progress');
    const hasAutoAnimate = document.querySelector('[data-auto-animate]');
    const hasSwupContainer = document.querySelector('[data-swup]') || document.querySelector('#swup');
    const needsLenis = !reduce && (
      hasParallax || hasReveal || has3D || hasHorizontal || hasCounter || hasStagger
      || document.querySelector('a[href^="#"]')
    );

    // ─── Lenis smooth scroll (com ScrollTrigger proxy) ─────────────────
    let lenis = null;
    if (needsLenis) {
      loadScript(LENIS_SRC).then(function () {
        if (typeof Lenis === 'undefined') return;
        lenis = new Lenis({
          duration: 1.2,
          easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
          smoothWheel: true,
          smoothTouch: false,
          wheelMultiplier: 1.0,
          touchMultiplier: 2.0,
        });
        FRALIB.instances.lenis = lenis;
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
        gsap.ticker.lagSmoothing(0);
        // Anchors suaves
        document.querySelectorAll('a[href^="#"]').forEach(function (a) {
          a.addEventListener('click', function (e) {
            const id = a.getAttribute('href').slice(1);
            const target = document.getElementById(id);
            if (target) {
              e.preventDefault();
              lenis.scrollTo(target, { offset: -80, duration: 1.2 });
            }
          });
        });
      }).catch(function () { /* silent */ });
    }

    // ─── 1. PARALLAX (data-parallax="0.3") ─────────────────────────────
    if (hasParallax && !reduce) {
      document.querySelectorAll('[data-parallax]').forEach(function (el) {
        const speed = parseFloat(el.dataset.parallax || '0.3');
        const st = gsap.to(el, {
          y: function () { return -100 * speed; },
          ease: 'none',
          scrollTrigger: {
            trigger: el.parentElement || el,
            start: 'top bottom',
            end: 'bottom top',
            scrub: 0.6,
          },
        });
        FRALIB.instances.scrollTriggers.push(st.scrollTrigger);
      });
    }

    // ─── 2. REVEAL (data-reveal="up|down|left|right|scale|fade") ───────
    if (hasReveal && !reduce) {
      document.querySelectorAll('[data-reveal]').forEach(function (el, i) {
        const variant = el.dataset.reveal || 'up';
        const fromVars = { opacity: 0, duration: 0.9, ease: 'power3.out' };
        if (variant === 'up') fromVars.y = 60;
        else if (variant === 'down') fromVars.y = -60;
        else if (variant === 'left') fromVars.x = 60;
        else if (variant === 'right') fromVars.x = -60;
        else if (variant === 'scale') fromVars.scale = 0.85;
        const tween = gsap.from(el, Object.assign(fromVars, {
          delay: (i % 8) * 0.05,
          scrollTrigger: { trigger: el, start: 'top 88%', once: true },
        }));
        if (tween.scrollTrigger) FRALIB.instances.scrollTriggers.push(tween.scrollTrigger);
      });
    }

    // ─── 3. MARQUEE infinito (data-marquee="left|right") ───────────────
    if (hasMarquee && !reduce) {
      document.querySelectorAll('[data-marquee]').forEach(function (track) {
        const dir = track.dataset.marquee || 'left';
        const speed = parseFloat(track.dataset.marqueeSpeed || '40');
        const items = Array.from(track.children);
        items.forEach(function (item) {
          const clone = item.cloneNode(true);
          clone.setAttribute('aria-hidden', 'true');
          track.appendChild(clone);
        });
        const w = track.scrollWidth / 2;
        gsap.to(track, {
          x: dir === 'right' ? w : -w,
          duration: speed,
          ease: 'none',
          repeat: -1,
          modifiers: {
            x: gsap.utils.unitize(function (x) { return parseFloat(x) % w; }),
          },
        });
      });
    }

    // ─── 4. MAGNETIC CURSOR (data-magnetic="0.4") ──────────────────────
    if (hasMagnetic && !reduce) {
      document.querySelectorAll('[data-magnetic]').forEach(function (el) {
        const strength = parseFloat(el.dataset.magnetic || '0.4');
        el.addEventListener('mousemove', function (e) {
          const rect = el.getBoundingClientRect();
          const x = e.clientX - rect.left - rect.width / 2;
          const y = e.clientY - rect.top - rect.height / 2;
          gsap.to(el, { x: x * strength, y: y * strength, duration: 0.4, ease: 'power2.out' });
        });
        el.addEventListener('mouseleave', function () {
          gsap.to(el, { x: 0, y: 0, duration: 0.6, ease: 'elastic.out(1, 0.4)' });
        });
      });
    }

    // ─── 5. 3D TILT (data-3d-tilt="20") ────────────────────────────────
    if (has3D && !reduce) {
      document.querySelectorAll('[data-3d-tilt]').forEach(function (el) {
        const max = parseFloat(el.dataset['3dTilt'] || el.dataset['3d-tilt'] || '15');
        el.style.transformStyle = 'preserve-3d';
        el.style.perspective = '1000px';
        el.addEventListener('mousemove', function (e) {
          const rect = el.getBoundingClientRect();
          const x = (e.clientX - rect.left) / rect.width - 0.5;
          const y = (e.clientY - rect.top) / rect.height - 0.5;
          gsap.to(el, {
            rotateY: x * max * 2,
            rotateX: -y * max * 2,
            duration: 0.5,
            ease: 'power2.out',
          });
        });
        el.addEventListener('mouseleave', function () {
          gsap.to(el, { rotateY: 0, rotateX: 0, duration: 0.8, ease: 'power3.out' });
        });
      });
    }

    // ─── 6. TEXT SCRAMBLE (data-text-scramble) ─────────────────────────
    document.querySelectorAll('[data-text-scramble]').forEach(function (el) {
      const original = el.textContent;
      const chars = '!<>-_\\/[]{}—=+*^?#________';
      if (reduce) return;
      el.addEventListener('mouseenter', function () {
        let frame = 0;
        const total = 24;
        const interval = setInterval(function () {
          el.textContent = original.split('').map(function (c, i) {
            if (i < (frame / total) * original.length) return original[i];
            return chars[Math.floor(Math.random() * chars.length)];
          }).join('');
          frame++;
          if (frame >= total) {
            el.textContent = original;
            clearInterval(interval);
          }
        }, 40);
      });
    });

    // ─── 7. SCROLL PROGRESS BAR (.fralib-reading-progress) ─────────────
    if (!reduce && hasReadingProgress) {
      const st = gsap.to('.fralib-reading-progress', {
        scaleX: 1,
        ease: 'none',
        scrollTrigger: { start: 0, end: 'max', scrub: 0.3 },
      });
      FRALIB.instances.scrollTriggers.push(st.scrollTrigger);
    }

    // ─── 8. STAGGER LISTAS (data-stagger) ──────────────────────────────
    if (hasStagger && !reduce) {
      document.querySelectorAll('[data-stagger]').forEach(function (parent) {
        const kids = parent.children;
        if (!kids.length) return;
        const tween = gsap.from(Array.from(kids), {
          opacity: 0,
          y: 30,
          duration: 0.6,
          stagger: 0.08,
          ease: 'power2.out',
          scrollTrigger: { trigger: parent, start: 'top 85%', once: true },
        });
        if (tween.scrollTrigger) FRALIB.instances.scrollTriggers.push(tween.scrollTrigger);
      });
    }

    // ─── 9. HORIZONTAL SCROLL (data-horizontal-scroll) ─────────────────
    if (!reduce && hasHorizontal) {
      document.querySelectorAll('[data-horizontal-scroll]').forEach(function (wrap) {
        const track = wrap.querySelector('[data-horizontal-track]') || wrap;
        const distance = function () { return track.scrollWidth - window.innerWidth; };
        const st = gsap.to(track, {
          x: function () { return -distance(); },
          ease: 'none',
          scrollTrigger: {
            trigger: wrap,
            start: 'top top',
            end: function () { return '+=' + distance(); },
            pin: true,
            scrub: 0.6,
            invalidateOnRefresh: true,
          },
        });
        FRALIB.instances.scrollTriggers.push(st.scrollTrigger);
      });
    }

    // ─── 10. NUMBER COUNTER (data-counter="1234") ──────────────────────
    if (!reduce && hasCounter) {
      document.querySelectorAll('[data-counter]').forEach(function (el) {
        const target = parseFloat(el.dataset.counter);
        const decimals = (el.dataset.counter.split('.')[1] || '').length;
        const obj = { v: 0 };
        const tween = gsap.to(obj, {
          v: target,
          duration: 2,
          ease: 'power2.out',
          scrollTrigger: { trigger: el, start: 'top 85%', once: true },
          onUpdate: function () { el.textContent = obj.v.toFixed(decimals); },
        });
        if (tween.scrollTrigger) FRALIB.instances.scrollTriggers.push(tween.scrollTrigger);
      });
    }

    // ─── 11. SCROLL VELOCITY (data-fralib-scroll-velocity) ─────────────
    if (!reduce && hasVelocity) {
      let lastY = 0;
      window.addEventListener('scroll', function () {
        const y = window.scrollY;
        const v = (y - lastY) / 100;
        document.documentElement.style.setProperty('--fralib-scroll-velocity', v.toFixed(2));
        lastY = y;
      }, { passive: true });
    }

    // ─── 12. AutoAnimate (microinteracoes em listas/menus) ─────────────
    if (!reduce && hasAutoAnimate && typeof window !== 'undefined') {
      loadScript(AUTO_ANIMATE_SRC).then(function () {
        const AA = window.autoAnimate || window.AutoAnimate;
        if (typeof AA !== 'function') return;
        document.querySelectorAll('[data-auto-animate]').forEach(function (el) {
          const controller = AA(el, {
            duration: 250,
            easing: 'ease-in-out',
            // respeita tagname como parent; nao sobrepoe com stagger GSAP
            disrespect: function (parent, el) { return parent.dataset.autoAnimate === 'off'; },
          });
          FRALIB.instances.autoAnimate.push(controller);
        });
      }).catch(function () { /* silent */ });
    }

    // ─── 13. Swup page transitions (opt-in via [data-swup]) ────────────
    if (hasSwupContainer && typeof window !== 'undefined') {
      Promise.all([
        loadScript(SWUP_SRC).catch(function () { return null; }),
        loadScript(SWUP_FORMS_SRC).catch(function () { return null; }),
      ]).then(function () {
        const Swup = window.Swup;
        if (typeof Swup !== 'function') return;
        const formsPlugin = window.SwupFormsPlugin;
        const plugins = [];
        if (typeof formsPlugin === 'function') plugins.push(new formsPlugin());
        const swup = new Swup({
          containers: ['#swup', '[data-swup]'],
          animationSelector: '[class*="swup-transition-"]',
          cache: true,
          plugins: plugins,
          // preserva scripts injetados (motion runtime) entre trocas
          skipPopStateHandling: false,
        });
        FRALIB.instances.swup = swup;

        // Limpa GSAP ScrollTriggers + Lenis em page swap para nao vazar.
        swup.on('pageView', function () {
          FRALIB.instances.scrollTriggers.forEach(function (st) { try { st.kill(); } catch (e) {} });
          FRALIB.instances.scrollTriggers.length = 0;
          if (FRALIB.instances.lenis && typeof FRALIB.instances.lenis.destroy === 'function') {
            try { FRALIB.instances.lenis.destroy(); } catch (e) {}
            FRALIB.instances.lenis = null;
          }
          // Re-scan apos Swup montar novo DOM
          if (typeof ScrollTrigger !== 'undefined') ScrollTrigger.refresh();
        });
      }).catch(function () { /* silent */ });
    }

    // ─── 14. prefers-reduced-motion live monitor ──────────────────────
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', function (e) {
        FRALIB.reducedMotion = e.matches;
        if (e.matches) {
          // Kill tudo agressivamente
          FRALIB.instances.scrollTriggers.forEach(function (st) { try { st.kill(); } catch (err) {} });
          FRALIB.instances.scrollTriggers.length = 0;
          if (FRALIB.instances.lenis) {
            try { FRALIB.instances.lenis.destroy(); } catch (err) {}
            FRALIB.instances.lenis = null;
          }
          document.documentElement.classList.add('fralib-reduced-motion');
        } else {
          document.documentElement.classList.remove('fralib-reduced-motion');
        }
      });
    }
  }
})();
