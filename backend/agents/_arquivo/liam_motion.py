"""MOTION_SCRIPT — GSAP + Lenis + Toggle + Animacoes"""

MOTION_SCRIPT = """window.addEventListener("load", () => {
  if (typeof gsap === "undefined") {
    setTimeout(() => { if (typeof gsap !== "undefined") { window.dispatchEvent(new Event("load")); } }, 800);
    return;
  }
  gsap.registerPlugin(ScrollTrigger);

  // ===== LENIS SMOOTH SCROLL =====
  if (typeof Lenis !== "undefined") {
    const lenis = new Lenis({ duration: 1.2, easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)) });
    gsap.ticker.add((time) => { lenis.raf(time * 1000); });
    gsap.ticker.lagSmoothing(0);
  }

  // ===== PAINEIS ANIMADOS (fralib-panels) =====
  // Cada section com .fralib-panels-container troca paineis internamente
  document.querySelectorAll(".fralib-panels-container").forEach(container => {
    const panels = container.querySelectorAll(".fralib-panel");
    if (!panels.length) return;
    const section = container.closest("section");
    if (!section) return;

    // Garantir overflow hidden na section
    section.style.overflow = "hidden";
    section.style.position = "relative";

    // Posicionar paineis empilhados
    panels.forEach((panel, i) => {
      gsap.set(panel, {
        position: "absolute", top: 0, left: 0,
        width: "100%", height: "100%",
        opacity: i === 0 ? 1 : 0,
        zIndex: i === 0 ? 2 : 1,
        pointerEvents: i === 0 ? "auto" : "none"
      });
    });
    container.style.position = "relative";
    container.style.height = "100%";

    let current = 0;
    let animating = false;

    function goTo(next) {
      if (animating || next === current || next < 0 || next >= panels.length) return;
      animating = true;
      const dir = next > current ? 1 : -1;
      const outPanel = panels[current];
      const inPanel = panels[next];

      gsap.set(inPanel, { opacity: 0, y: dir * 60, zIndex: 2, pointerEvents: "none" });
      gsap.set(outPanel, { zIndex: 1 });

      const tl = gsap.timeline({ onComplete: () => {
        gsap.set(outPanel, { opacity: 0, pointerEvents: "none", zIndex: 1 });
        gsap.set(inPanel, { pointerEvents: "auto", zIndex: 2 });
        current = next;
        animating = false;
        updateDots();
      }});
      tl.to(outPanel, { opacity: 0, y: -dir * 40, duration: 0.5, ease: "power2.in" }, 0);
      tl.to(inPanel, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    }

    // Dots de navegacao
    const dots = document.createElement("div");
    dots.style.cssText = "position:absolute;bottom:24px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:10;";
    panels.forEach((_, i) => {
      const dot = document.createElement("button");
      dot.style.cssText = "width:8px;height:8px;border-radius:50%;border:none;cursor:pointer;transition:all 0.3s;background:" + (i === 0 ? "var(--color-accent,#e85d04)" : "rgba(255,255,255,0.4)") + ";";
      dot.setAttribute("aria-label", "Painel " + (i+1));
      dot.addEventListener("click", () => goTo(i));
      dots.appendChild(dot);
    });
    section.appendChild(dots);

    function updateDots() {
      dots.querySelectorAll("button").forEach((d, i) => {
        d.style.background = i === current ? "var(--color-accent,#e85d04)" : "rgba(255,255,255,0.4)";
        d.style.transform = i === current ? "scale(1.4)" : "scale(1)";
      });
    }

    // Auto-avancar a cada 5s se mais de 1 painel
    if (panels.length > 1) {
      let autoTimer = setInterval(() => { if (!animating) goTo((current + 1) % panels.length); }, 5000);
      section.addEventListener("mouseenter", () => clearInterval(autoTimer));
      section.addEventListener("mouseleave", () => { autoTimer = setInterval(() => { if (!animating) goTo((current + 1) % panels.length); }, 5000); });
    }

    // Setas de navegacao
    if (panels.length > 1) {
      ["prev","next"].forEach(dir => {
        const btn = document.createElement("button");
        btn.style.cssText = "position:absolute;" + (dir==="prev"?"left:16px":"right:16px") + ";top:50%;transform:translateY(-50%);z-index:10;width:40px;height:40px;border-radius:50%;border:none;cursor:pointer;background:rgba(0,0,0,0.3);color:white;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);";
        btn.innerHTML = dir==="prev" ? "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polyline points='15,18 9,12 15,6'/></svg>" : "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><polyline points='9,18 15,12 9,6'/></svg>";
        btn.addEventListener("click", () => goTo(dir==="prev" ? current-1 : current+1));
        section.appendChild(btn);
      });
    }
  });

  // ===== HERO: 3D cinematografico =====
  const heroContent = document.querySelector("#hero > *, .hero > *, section:first-of-type > div:first-child");
  if (heroContent) {
    gsap.from(heroContent, { opacity: 0, scale: 0.92, y: 60, rotateX: 8, duration: 1.6, ease: "power4.out", delay: 0.2, transformPerspective: 1200 });
  }
  const heroBg = document.querySelector("#hero, section:first-of-type");
  if (heroBg) {
    gsap.to(heroBg, { backgroundPositionY: "40%", ease: "none", scrollTrigger: { trigger: heroBg, start: "top top", end: "bottom top", scrub: true } });
  }

  // ===== SOBRE: slide da esquerda =====
  const sobre = document.querySelector("#sobre");
  if (sobre) {
    gsap.from(sobre.querySelectorAll("h2, h3, p, img"), { opacity: 0, x: -60, stagger: 0.15, duration: 1.0, ease: "power3.out", scrollTrigger: { trigger: sobre, start: "top 80%" } });
  }

  // ===== SERVICOS: stagger com scale + rotacao =====
  const servicos = document.querySelector("#servicos");
  if (servicos) {
    const cards = servicos.querySelectorAll("[class*=card], article, li");
    if (cards.length) {
      gsap.from(cards, { opacity: 0, y: 70, scale: 0.92, rotateY: 8, stagger: 0.12, duration: 0.9, ease: "back.out(1.4)", scrollTrigger: { trigger: servicos, start: "top 78%" } });
    }
  }

  // ===== DEPOIMENTOS: flip 3D stagger =====
  const depo = document.querySelector("#depoimentos");
  if (depo) {
    const dc = depo.querySelectorAll("[class*=card], blockquote, article");
    if (dc.length) {
      gsap.from(dc, { opacity: 0, rotateX: 20, y: 50, stagger: 0.18, duration: 1.0, ease: "power2.out", scrollTrigger: { trigger: depo, start: "top 78%" } });
    }
  }

  // ===== LOCALIZACAO: slide da direita =====
  const loc = document.querySelector("#localizacao");
  if (loc) {
    gsap.from(loc.querySelectorAll("h2, h3, p, iframe"), { opacity: 0, x: 60, stagger: 0.12, duration: 1.0, ease: "power3.out", scrollTrigger: { trigger: loc, start: "top 80%" } });
  }

  // ===== CONTATO: scale in =====
  const contato = document.querySelector("#contato");
  if (contato) {
    gsap.from(contato.querySelectorAll("h2, h3, form, input, button, a"), { opacity: 0, scale: 0.9, y: 30, stagger: 0.1, duration: 0.8, ease: "back.out(1.7)", scrollTrigger: { trigger: contato, start: "top 82%" } });
  }

  // ===== PARALLAX em elementos com data-speed =====
  document.querySelectorAll(".parallax-layer, [data-speed]").forEach(el => {
    const speed = parseFloat(el.dataset.speed || 0.3);
    gsap.to(el, { y: () => window.innerHeight * speed, ease: "none", scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true } });
  });

  // ===== CARDS 3D hover =====
  document.querySelectorAll(".card-3d, [class*=card]").forEach(el => {
    el.style.transformStyle = "preserve-3d";
    el.style.willChange = "transform";
    el.addEventListener("mouseenter", () => gsap.to(el, { rotateY: 6, rotateX: -3, scale: 1.03, duration: 0.4, ease: "power2.out" }));
    el.addEventListener("mouseleave", () => gsap.to(el, { rotateY: 0, rotateX: 0, scale: 1, duration: 0.4, ease: "power2.out" }));
  });

  // ===== IMAGENS zoom =====
  document.querySelectorAll("img[loading=lazy]").forEach(img => {
    gsap.from(img, { opacity: 0, scale: 1.1, duration: 1.1, ease: "power3.out", scrollTrigger: { trigger: img, start: "top 85%" } });
  });

  // ===== MAGNETIC CTAs =====
  document.querySelectorAll("a[href*='wa.me'], .magnetic").forEach(btn => {
    if (btn.id === "wpp-float") return;
    btn.addEventListener("mousemove", e => {
      const r = btn.getBoundingClientRect();
      gsap.to(btn, { x: (e.clientX-r.left-r.width/2)*0.3, y: (e.clientY-r.top-r.height/2)*0.3, duration: 0.3, ease: "power2.out" });
    });
    btn.addEventListener("mouseleave", () => gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1,0.3)" }));
  });

  // ===== SCROLL PROGRESS BAR =====
  const bar = document.createElement("div");
  bar.style.cssText = "position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,var(--color-accent,#e85d04),var(--color-primary,#374151));z-index:9999;width:0;pointer-events:none";
  document.body.prepend(bar);
  gsap.to(bar, { width: "100%", ease: "none", scrollTrigger: { trigger: "body", start: "top top", end: "bottom bottom", scrub: 0.3 } });

  // ===== COUNTER ANIMADO =====
  document.querySelectorAll("[data-count]").forEach(el => {
    ScrollTrigger.create({ trigger: el, start: "top 90%", onEnter: () => {
      if (el.dataset.counted) return;
      el.dataset.counted = "1";
      const target = parseFloat(el.dataset.count), dur = 2000, t0 = Date.now();
      const tick = () => { const p=Math.min((Date.now()-t0)/dur,1),e=1-Math.pow(1-p,3); el.textContent=Math.floor(target*e)+(el.dataset.suffix||""); if(p<1) requestAnimationFrame(tick); };
      tick();
    }});
  });

  // ===== H2/H3 fallback =====
  document.querySelectorAll("h2, h3").forEach(el => {
    if (!el.closest("#hero, #sobre, #servicos, #depoimentos, #localizacao, #contato")) {
      gsap.from(el, { opacity: 0, y: 30, duration: 0.8, ease: "power3.out", scrollTrigger: { trigger: el, start: "top 88%" } });
    }
  });

  // ===== WHATSAPP FLOAT PULSE =====
  const wpp = document.getElementById("wpp-float");
  if (wpp) gsap.to(wpp, { scale: 1.08, boxShadow: "0 0 0 16px rgba(37,211,102,0.15)", duration: 1.4, repeat: -1, yoyo: true, ease: "power1.inOut" });

  // ===== DARK/LIGHT TOGGLE =====
  (function() {
    const saved = localStorage.getItem("fralib-theme");
    const theme = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
    if (!document.getElementById("theme-toggle")) {
      const btn = document.createElement("button");
      btn.id = "theme-toggle";
      btn.setAttribute("aria-label", "Alternar tema claro/escuro");
      btn.style.cssText = "position:fixed;bottom:80px;right:16px;z-index:9997;width:40px;height:40px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;background:var(--color-surface,#f9fafb);box-shadow:0 2px 12px rgba(0,0,0,0.2);transition:all 0.3s ease;opacity:0.9;";
      btn.innerHTML = "<svg id='icon-sun' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' style='display:none'><circle cx='12' cy='12' r='5'/></svg><svg id='icon-moon' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/></svg>";
      document.body.appendChild(btn);
      function upd(t) { document.getElementById("icon-sun").style.display=t==="dark"?"block":"none"; document.getElementById("icon-moon").style.display=t==="light"?"block":"none"; btn.style.color=t==="dark"?"#f0f0f5":"#374151"; }
      upd(theme);
      btn.addEventListener("click", () => { const n=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark"; document.documentElement.setAttribute("data-theme",n); localStorage.setItem("fralib-theme",n); upd(n); gsap.from(btn,{rotate:180,duration:0.4,ease:"back.out(1.7)"}); });
    }
  })();
});
"""


