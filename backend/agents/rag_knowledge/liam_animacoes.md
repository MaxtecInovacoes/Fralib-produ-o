# Animacoes Cinematograficas — Liam RAG

## Biblioteca de Animacoes Cinematograficas (escolher as mais adequadas ao segmento)

### 01. MASK REVEAL - Texto que sobe por tras de mascara
Cinematografico classico. Ideal para: hero headlines, titulos de secao.
`js
gsap.from(".mask-reveal", { yPercent: 110, duration: 1, ease: "power4.out", stagger: 0.1 });
// Container precisa de: overflow-hidden
`

### 02. STAGGER FADE UP - Cards entram em cascata
Ideal para: grids de servicos, cards de beneficios, listas.
`js
gsap.from(".card-stagger", {
  opacity: 0, y: 50, duration: 0.8, ease: "power3.out", stagger: 0.15,
  scrollTrigger: { trigger: ".card-stagger", start: "top 80%" }
});
`

### 03. CLIP-PATH REVEAL - Secao que abre de baixo para cima
Ideal para: imagens hero, banners, fotos de destaque.
`js
gsap.to(".clip-reveal", {
  clipPath: "inset(0% 0 0 0)", duration: 1.2, ease: "power4.inOut",
  scrollTrigger: { trigger: ".clip-reveal", start: "top 75%" }
});
// CSS inicial: clip-path: inset(100% 0 0 0);
`

### 04. PARALLAX SCROLL - Imagem move mais devagar
Ideal para: hero sections, backgrounds de secao.
`js
gsap.to(".parallax-img", {
  yPercent: 30, ease: "none",
  scrollTrigger: { trigger: ".parallax-img", start: "top top", end: "bottom top", scrub: true }
});
`

### 05. COUNTER ANIMATION - Numeros que contam ate o valor
Ideal para: estatisticas, anos de experiencia, numero de clientes, avaliacoes.
`js
document.querySelectorAll(".counter").forEach(el => {
  const target = parseInt(el.dataset.target);
  gsap.to({ val: 0 }, {
    val: target, duration: 2, ease: "power2.out",
    onUpdate: function() { el.textContent = Math.round(this.targets()[0].val); },
    scrollTrigger: { trigger: el, start: "top 80%", once: true }
  });
});
`

### 06. MAGNETIC BUTTON - Botao que atrai o cursor
Ideal para: CTAs principais, botoes de destaque.
`js
document.querySelectorAll(".magnetic-btn").forEach(btn => {
  btn.addEventListener("mousemove", (e) => {
    const rect = btn.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    gsap.to(btn, { x: x * 0.3, y: y * 0.3, duration: 0.3, ease: "power2.out" });
  });
  btn.addEventListener("mouseleave", () => {
    gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1, 0.5)" });
  });
});
`

### 07. FOLLOWER CURSOR - Cursor customizado com lag
Ideal para: sites premium, dark mode, alto ticket.
`js
const dot = document.getElementById("cursor-dot");
const ring = document.getElementById("cursor-ring");
document.addEventListener("mousemove", (e) => {
  gsap.to(dot, { x: e.clientX, y: e.clientY, duration: 0.1 });
  gsap.to(ring, { x: e.clientX, y: e.clientY, duration: 0.4, ease: "power2.out" });
});
document.querySelectorAll("a, button").forEach(el => {
  el.addEventListener("mouseenter", () => gsap.to(ring, { scale: 2.5, duration: 0.3 }));
  el.addEventListener("mouseleave", () => gsap.to(ring, { scale: 1, duration: 0.3 }));
});
`

### 08. SCROLL PROGRESS BAR - Barra de progresso de leitura
Ideal para: qualquer site com conteudo longo.
`js
gsap.to("#scroll-bar", {
  width: "100%", ease: "none",
  scrollTrigger: { start: "top top", end: "bottom bottom", scrub: 0.3 }
});
`

### 09. SCRAMBLE TEXT - Texto embaralhado que se revela
Ideal para: titulos de hero tech/inovacao, palavras-chave de destaque.
`js
function scramble(el, finalText, duration = 1500) {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let start = null;
  function step(timestamp) {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    const revealed = Math.floor(progress * finalText.length);
    el.textContent = finalText.slice(0, revealed) +
      Array.from({ length: finalText.length - revealed }, () =>
        chars[Math.floor(Math.random() * chars.length)]).join("");
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = finalText;
  }
  requestAnimationFrame(step);
}
`

### 10. HOVER IMAGE ZOOM - Zoom suave em imagens no hover
Ideal para: galerias, cards de servico com foto, portfolio.
`js
// CSS: .img-zoom-container { overflow: hidden; }
// CSS: .img-zoom-container img { transition: transform 0.6s cubic-bezier(0.25,1,0.5,1); }
// CSS: .img-zoom-container:hover img { transform: scale(1.08); }
`

### 11. GRAYSCALE TO COLOR - Foto em preto e branco que colore no hover
Ideal para: galerias, fotos de equipe, portfolio.
`css
.grayscale-hover img { filter: grayscale(100%); transition: filter 0.5s ease; }
.grayscale-hover:hover img { filter: grayscale(0%); }
`

### 12. LINE DRAW - Linha que se desenha separando secoes
Ideal para: separadores de secao, decoracao minimalista.
`js
gsap.from(".line-draw", {
  scaleX: 0, transformOrigin: "left center", duration: 1.2, ease: "power3.inOut",
  scrollTrigger: { trigger: ".line-draw", start: "top 80%" }
});
`

### 13. BACKGROUND COLOR SHIFT - Cor de fundo muda ao scrollar
Ideal para: transicao entre secoes dark/light, storytelling.
`js
const sections = document.querySelectorAll("[data-bg]");
sections.forEach(section => {
  ScrollTrigger.create({
    trigger: section,
    start: "top center",
    end: "bottom center",
    onEnter: () => gsap.to("body", { backgroundColor: section.dataset.bg, duration: 0.8 }),
    onEnterBack: () => gsap.to("body", { backgroundColor: section.dataset.bg, duration: 0.8 })
  });
});
`

### 14. STICKY HEADER BLUR - Header que ganha blur ao scrollar
Ideal para: todos os sites.
`js
ScrollTrigger.create({
  start: "top -80",
  onUpdate: (self) => {
    header.classList.toggle("scrolled", self.progress > 0);
  }
});
// CSS: header.scrolled { backdrop-filter: blur(20px); background: rgba(0,0,0,0.8); }
`

### 15. RIPPLE EFFECT - Onda que expande do ponto de clique
Ideal para: botoes de CTA, botoes de WhatsApp.
`js
document.querySelectorAll(".ripple-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    const ripple = document.createElement("span");
    const rect = btn.getBoundingClientRect();
    ripple.style.cssText = "position:absolute;border-radius:50%;transform:scale(0);animation:ripple 0.6s linear;background:rgba(255,255,255,0.3);width:100px;height:100px;left:" + (e.clientX - rect.left - 50) + "px;top:" + (e.clientY - rect.top - 50) + "px;";
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  });
});
// CSS: @keyframes ripple { to { transform: scale(4); opacity: 0; } }
`

### 16. TILT 3D - Card com perspectiva 3D no hover
Ideal para: cards de servico premium, cards de depoimento.
`js
document.querySelectorAll(".tilt-card").forEach(card => {
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    gsap.to(card, { rotateY: x * 15, rotateX: -y * 15, duration: 0.3, ease: "power2.out", transformPerspective: 1000 });
  });
  card.addEventListener("mouseleave", () => {
    gsap.to(card, { rotateY: 0, rotateX: 0, duration: 0.5, ease: "elastic.out(1, 0.5)" });
  });
});
`

### 17. FLOATING ELEMENTS - Elementos que flutuam suavemente
Ideal para: decoracoes, icones de fundo, elementos visuais.
`js
gsap.to(".float-element", {
  y: -20, duration: 2, ease: "sine.inOut", yoyo: true, repeat: -1, stagger: 0.3
});
`

### 18. TEXT SPLIT BY LINE - Cada linha do titulo entra separada
Ideal para: headlines longas, subtitulos de secao.
`js
// Dividir texto em linhas manualmente ou usar SplitText
const lines = title.querySelectorAll(".line");
gsap.from(lines, {
  opacity: 0, y: 60, duration: 0.9, ease: "power4.out", stagger: 0.12,
  scrollTrigger: { trigger: title, start: "top 80%" }
});
`

### 19. GLOW PULSE - Brilho pulsante em elementos de destaque
Ideal para: badges de avaliacao, CTAs, elementos de urgencia.
`css
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 8px var(--color-accent); }
  50% { box-shadow: 0 0 24px var(--color-accent), 0 0 48px var(--color-accent)40; }
}
.glow-pulse { animation: glow-pulse 2s ease-in-out infinite; }
`

### 20. REVEAL ON SCROLL - Fade + slide padrao para todos os elementos
Ideal para: qualquer elemento que entra na viewport.
`js
gsap.utils.toArray(".reveal").forEach(el => {
  gsap.from(el, {
    opacity: 0, y: 40, duration: 0.8, ease: "power3.out",
    scrollTrigger: { trigger: el, start: "top 85%", once: true }
  });
});
`

### 21. HORIZONTAL SCROLL - Galeria com scroll horizontal
Ideal para: galerias de fotos, portfolio de trabalhos.
`js
const gallery = document.querySelector(".h-scroll-gallery");
gsap.to(gallery, {
  x: () => -(gallery.scrollWidth - window.innerWidth),
  ease: "none",
  scrollTrigger: { trigger: ".h-scroll-section", start: "top top", end: "+=3000", scrub: 1, pin: true }
});
`

### 22. NOISE TEXTURE OVERLAY - Textura de ruido sobre imagens
Ideal para: hero sections premium, backgrounds dark mode.
`css
.noise-overlay::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  opacity: 0.04;
}
`

### 23. SKELETON LOADING - Placeholder animado enquanto carrega
Ideal para: cards, imagens, qualquer conteudo dinamico.
`css
.skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: skeleton-loading 1.5s infinite; }
@keyframes skeleton-loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
`

### 24. WHATSAPP FLOAT BUTTON - Botao flutuante com pulse
Ideal para: todos os sites de negocio local.
`css
.wpp-float { position: fixed; bottom: 24px; right: 24px; z-index: 999; }
.wpp-float::before { content: ""; position: absolute; inset: -4px; border-radius: 50%; background: #25D366; animation: wpp-pulse 2s ease-out infinite; opacity: 0; }
@keyframes wpp-pulse { 0% { transform: scale(1); opacity: 0.6; } 100% { transform: scale(1.8); opacity: 0; } }
`

### 25. PAGE TRANSITION - Transicao cinematografica entre paginas
Ideal para: sites com multiplas paginas, navegacao interna.
`js
// Overlay que cobre a tela ao navegar
document.querySelectorAll("a[href]").forEach(link => {
  link.addEventListener("click", (e) => {
    if (link.hostname === location.hostname) {
      e.preventDefault();
      const overlay = document.getElementById("page-overlay");
      gsap.to(overlay, {
        scaleY: 1, transformOrigin: "bottom", duration: 0.5, ease: "power4.in",
        onComplete: () => { window.location = link.href; }
      });
    }
  });
});
`

## Selecao de Animacoes por Segmento

### Academia / Fitness / CrossFit (dark mode)
Usar: 01 MASK REVEAL, 05 COUNTER, 06 MAGNETIC, 07 CURSOR, 16 TILT 3D, 19 GLOW PULSE, 24 WHATSAPP

### Barbearia / Salao Masculino (dark mode)
Usar: 01 MASK REVEAL, 03 CLIP-PATH, 10 HOVER ZOOM, 12 LINE DRAW, 17 FLOATING, 24 WHATSAPP

### Clinica / Estetica / Saude (light mode)
Usar: 02 STAGGER, 04 PARALLAX, 14 STICKY HEADER, 20 REVEAL, 24 WHATSAPP

### Restaurante / Lanchonete
Usar: 03 CLIP-PATH, 04 PARALLAX, 10 HOVER ZOOM, 21 HORIZONTAL SCROLL, 24 WHATSAPP

### Padaria / Confeitaria / Cafe (light mode)
Usar: 02 STAGGER, 10 HOVER ZOOM, 17 FLOATING, 20 REVEAL, 24 WHATSAPP

### Bar / Balada / Nightclub (dark mode)
Usar: 01 MASK REVEAL, 07 CURSOR, 13 BG SHIFT, 19 GLOW PULSE, 22 NOISE TEXTURE, 24 WHATSAPP

