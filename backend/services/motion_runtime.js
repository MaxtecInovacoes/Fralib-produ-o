// FraLib Motion Runtime
// Carregado via CDN no deploy do OpenUI.
// Animações nível Awwwards em HTML estático puro (sem React/Next/Vite).
// Inclui: parallax, reveal, marquee, smooth scroll, magnetic cursor,
// text scramble, scroll-trigger 3D tilt, scroll-snap, progress bar.
// Respeita prefers-reduced-motion.
// Idempotente: detecta <script id="fralib-motion-runtime"> e sai.
(function () {
  if (document.getElementById('fralib-motion-runtime')) return;

  // Carrega GSAP
  const gsapScript = document.createElement('script');
  gsapScript.id = 'fralib-motion-runtime';
  gsapScript.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js';
  gsapScript.onload = function () { initMotion(); };
  document.head.appendChild(gsapScript);

  function initMotion() {
    if (typeof gsap === 'undefined') return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const hasParallax = document.querySelector('[data-parallax]');
    const hasReveal = document.querySelector('[data-reveal]');
    const hasMarquee = document.querySelector('[data-marquee]');
    const hasMagnetic = document.querySelector('[data-magnetic]');
    const has3D = document.querySelector('[data-3d-tilt]');

    // Carrega ScrollTrigger se necessário
    if (!reduce && (hasParallax || hasReveal || has3D)) {
      const st = document.createElement('script');
      st.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js';
      st.onload = function () { setupMotion(); };
      document.head.appendChild(st);
    } else {
      setupMotion();
    }

    function setupMotion() {
      gsap.registerPlugin(ScrollTrigger);

      // ─── 1. PARALLAX (data-parallax="0.3") ───────────────────────────
      if (hasParallax && !reduce) {
        document.querySelectorAll('[data-parallax]').forEach(function (el) {
          const speed = parseFloat(el.dataset.parallax || '0.3');
          gsap.to(el, {
            y: () => -100 * speed,
            ease: 'none',
            scrollTrigger: {
              trigger: el.parentElement || el,
              start: 'top bottom',
              end: 'bottom top',
              scrub: 0.6
            }
          });
        });
      }

      // ─── 2. REVEAL (data-reveal) com stagger ──────────────────────────
      if (hasReveal && !reduce) {
        document.querySelectorAll('[data-reveal]').forEach(function (el, i) {
          const variant = el.dataset.reveal || 'up';
          const fromVars = { opacity: 0, duration: 0.9, ease: 'power3.out' };
          if (variant === 'up') fromVars.y = 60;
          else if (variant === 'down') fromVars.y = -60;
          else if (variant === 'left') fromVars.x = 60;
          else if (variant === 'right') fromVars.x = -60;
          else if (variant === 'scale') { fromVars.scale = 0.85; }
          else if (variant === 'fade') { /* opacity only */ }
          gsap.from(el, Object.assign(fromVars, {
            delay: (i % 8) * 0.05,
            scrollTrigger: { trigger: el, start: 'top 88%', once: true }
          }));
        });
      }

      // ─── 3. MARQUEE INFINITO (data-marquee="left|right") ─────────────
      if (hasMarquee && !reduce) {
        document.querySelectorAll('[data-marquee]').forEach(function (track) {
          const dir = track.dataset.marquee || 'left';
          const speed = parseFloat(track.dataset.marqueeSpeed || '40');
          // Duplica os itens para loop seamless
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
              x: gsap.utils.unitize(function (x) {
                return parseFloat(x) % w;
              })
            }
          });
        });
      }

      // ─── 4. MAGNETIC CURSOR (data-magnetic) ───────────────────────────
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

      // ─── 5. 3D TILT (data-3d-tilt="20") ───────────────────────────────
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
              ease: 'power2.out'
            });
          });
          el.addEventListener('mouseleave', function () {
            gsap.to(el, { rotateY: 0, rotateX: 0, duration: 0.8, ease: 'power3.out' });
          });
        });
      }

      // ─── 6. TEXT SCRAMBLE (data-text-scramble) ────────────────────────
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

      // ─── 7. SCROLL PROGRESS BAR ───────────────────────────────────────
      if (!reduce && document.querySelector('.fralib-reading-progress')) {
        gsap.to('.fralib-reading-progress', {
          scaleX: 1,
          ease: 'none',
          scrollTrigger: { start: 0, end: 'max', scrub: 0.3 }
        });
      }

      // ─── 8. STAGGER LISTAS (data-stagger) ────────────────────────────
      document.querySelectorAll('[data-stagger]').forEach(function (parent) {
        const kids = parent.children;
        if (!kids.length) return;
        gsap.from(Array.from(kids), {
          opacity: 0,
          y: 30,
          duration: 0.6,
          stagger: 0.08,
          ease: 'power2.out',
          scrollTrigger: { trigger: parent, start: 'top 85%', once: true }
        });
      });

      // ─── 9. LENIS SMOOTH SCROLL ──────────────────────────────────────
      if (!reduce && document.querySelector('a[href^="#"]')) {
        const l = document.createElement('script');
        l.src = 'https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js';
        l.onload = function () {
          if (typeof Lenis === 'undefined') return;
          const lenis = new Lenis({
            smoothWheel: true,
            smoothTouch: false,
            lerp: 0.1,
            wheelMultiplier: 1.0
          });
          function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
          requestAnimationFrame(raf);
          lenis.on('scroll', ScrollTrigger.update);
          gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
          gsap.ticker.lagSmoothing(0);
          // Anchor smooth
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
        };
        document.head.appendChild(l);
      }

      // ─── 10. HORIZONTAL SCROLL (data-horizontal-scroll) ──────────────
      if (!reduce) {
        document.querySelectorAll('[data-horizontal-scroll]').forEach(function (wrap) {
          const track = wrap.querySelector('[data-horizontal-track]') || wrap;
          const distance = () => track.scrollWidth - window.innerWidth;
          gsap.to(track, {
            x: () => -distance(),
            ease: 'none',
            scrollTrigger: {
              trigger: wrap,
              start: 'top top',
              end: () => '+=' + distance(),
              pin: true,
              scrub: 0.6,
              invalidateOnRefresh: true
            }
          });
        });
      }

      // ─── 11. NUMBER COUNTER (data-counter="1234") ────────────────────
      if (!reduce) {
        document.querySelectorAll('[data-counter]').forEach(function (el) {
          const target = parseFloat(el.dataset.counter);
          const decimals = (el.dataset.counter.split('.')[1] || '').length;
          const obj = { v: 0 };
          gsap.to(obj, {
            v: target,
            duration: 2,
            ease: 'power2.out',
            scrollTrigger: { trigger: el, start: 'top 85%', once: true },
            onUpdate: function () {
              el.textContent = obj.v.toFixed(decimals);
            }
          });
        });
      }

      // ─── 12. SCROLL VELOCITY (data-fralib-scroll-velocity) ───────────
      if (!reduce) {
        let lastY = 0;
        window.addEventListener('scroll', function () {
          const y = window.scrollY;
          const v = (y - lastY) / 100;
          document.documentElement.style.setProperty('--fralib-scroll-velocity', v.toFixed(2));
          lastY = y;
        }, { passive: true });
      }
    }
  }
})();
