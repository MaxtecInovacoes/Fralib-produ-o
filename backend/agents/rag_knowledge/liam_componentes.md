# Toggle e Dark Mode — Liam RAG

## Toggle Dark/Light Mode (OBRIGATÓRIO em todos os sites)

Todo site gerado JÁ TEM o toggle injetado automaticamente pelo MOTION_SCRIPT.
O botão sol/lua aparece fixo no canto superior direito.

### Como usar no HTML

Use SEMPRE CSS variables para cores — nunca hardcode:
- background: var(--color-background)
- surface: var(--color-surface)  
- texto: var(--color-on-bg)
- primária: var(--color-primary)
- acento: var(--color-accent)

### Transições suaves
Adicionar em elementos que mudam de cor:
transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;

### Ícones e imagens
- Logos: usar versão SVG (funciona em ambos os modos)
- Ícones: usar stroke=currentColor para herdar a cor do tema
- Fotos: não precisam de ajuste (são neutras)

### Modo inicial
- O site detecta preferência do sistema (prefers-color-scheme)
- Salva escolha do usuário em localStorage('fralib-theme')
- Academia/Barbearia/Bar: iniciar em dark por padrão
- Clínica/Padaria/Restaurante: iniciar em light por padrão

## Bibliotecas de Animacao Disponiveis

### Sempre disponivel via CDN
- **GSAP 3.12.2** + ScrollTrigger — animacoes complexas, timelines, scroll-driven
- **Lenis 1.0.42** — smooth scroll, integrado com GSAP ticker
- **Motion One 11.11.9** — micro-animacoes leves (3.8KB), usar para fade/slide/stagger simples
  - Uso: Motion.animate(elemento, {opacity:[0,1], y:[20,0]}, {duration:0.4})
  - Preferir Motion One para animacoes simples, GSAP para timelines complexas

### Condicional (segmentos premium: arquitetura, imobiliaria, tech, luxo, moda)
- **Three.js 0.160.0** — efeitos 3D no hero, particulas, shaders
  - Usar apenas quando o segmento justificar
  - Manter cena minimalista — nao prejudicar performance mobile

### NUNCA adicionar via script tag (ja injetados automaticamente)
- GSAP, Lenis, ScrollTrigger, Motion One, Three.js (premium)
- Tailwind CSS
- Plus Jakarta Sans, Inter (Google Fonts)
