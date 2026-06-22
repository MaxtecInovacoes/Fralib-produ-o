/* FraLib Motion Runtime
   Carregado via CDN no deploy do OpenUI.
   Ativa parallax, scroll-reveal, smooth scroll (Lenis) e marquee infinito.
   Respeita prefers-reduced-motion.
   Idempotente: detecta <script id="fralib-motion-runtime"> e sai.
   (function () {
     if (document.getElementById('fralib-motion-runtime')) return;
     const s = document.createElement('script');
     s.id = 'fralib-motion-runtime';
     s.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js';
     s.onload = function () { initMotion(); };
     document.head.appendChild(s);
     function initMotion() {
       const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
       // 1. ScrollTrigger (CDN inline, so carrega se parallax/reveal ativo)
       const hasParallax = document.querySelector('[data-parallax]');
       const hasReveal = document.querySelector('[data-reveal]');
       const hasMarquee = document.querySelector('[data-marquee]');
       if (!reduce && (hasParallax || hasReveal || hasMarquee)) {
         const st = document.createElement('script');
         st.src = 'https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js';
         st.onload = function () { setupMotion(); };
         document.head.appendChild(st);
       } else {
         setupMotion();
       }
       function setupMotion() {
         if (typeof gsap === 'undefined') return;
         if (hasParallax && !reduce) {
           gsap.registerPlugin(ScrollTrigger);
           document.querySelectorAll('[data-parallax]').forEach(function (el) {
             const speed = parseFloat(el.dataset.parallax || '0.3');
             gsap.to(el, {
               y: -50 * speed,
               ease: 'none',
               scrollTrigger: { trigger: el, start: 'top bottom', end: 'bottom top', scrub: 0.6 }
             });
           });
         }
         if (hasReveal && !reduce && typeof ScrollTrigger !== 'undefined') {
           gsap.registerPlugin(ScrollTrigger);
           document.querySelectorAll('[data-reveal]').forEach(function (el, i) {
             gsap.from(el, {
               opacity: 0,
               y: 30,
               duration: 0.8,
               delay: i * 0.05,
               ease: 'power2.out',
               scrollTrigger: { trigger: el, start: 'top 85%', once: true }
             });
           });
         }
         if (hasMarquee && !reduce) {
           document.querySelectorAll('[data-marquee]').forEach(function (track) {
             const dir = track.dataset.marquee || 'left';
             const speed = parseFloat(track.dataset.marqueeSpeed || '30');
             const w = track.scrollWidth;
             gsap.to(track, {
               x: dir === 'right' ? w : -w,
               duration: speed,
               ease: 'none',
               repeat: -1
             });
           });
         }
         // 2. Lenis smooth scroll (opcional, so carrega se tiver anchor)
         if (!reduce && document.querySelector('a[href^=\"#\"]')) {
           const l = document.createElement('script');
           l.src = 'https://cdn.jsdelivr.net/npm/lenis@1.1.13/dist/lenis.min.js';
           l.onload = function () {
             if (typeof Lenis === 'undefined') return;
             const lenis = new Lenis({ smoothWheel: true, smoothTouch: false });
             function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
             requestAnimationFrame(raf);
             // Hook com GSAP ScrollTrigger se existir
             if (typeof ScrollTrigger !== 'undefined') {
               lenis.on('scroll', ScrollTrigger.update);
               gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
               gsap.ticker.lagSmoothing(0);
             }
           };
           document.head.appendChild(l);
         }
       }
     }
   })();
