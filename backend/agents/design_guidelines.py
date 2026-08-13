"""
Design Guidelines - Impeccable + Motion Principles
"""

TAILWIND_FIRST_RULES = """
TAILWIND-FIRST (obrigatório):
- Use classes utilitárias do Tailwind diretamente nos elementos para layout, spacing, cor e tipografia.
- Evite blocos longos de <style> no <head>; CSS customizado só para micro-ajustes ou animações essenciais.
- Gere estrutura semântica limpa: 1 <main> raiz, 1 <h1> principal, seções claras com <section>.
- Elementos decorativos com position:absolute devem ficar dentro de wrapper pai com position:relative e overflow:hidden.
- Não use marcas d'água flutuantes soltas sobre o documento.
- Priorize contraste alto, hierarquia tipográfica clara e responsividade nativa via classes utilitárias.
"""

ANIMATION_PRINCIPLES = """
Timing: 100-150ms feedback, 200-300ms estado, 300-500ms layout, 500-800ms entrada
Easing: cubic-bezier(0.25, 1, 0.5, 1) - suave
Performance: transform + opacity apenas, 60fps
Micro-interactions: hover scale(1.02), click scale(0.95->1)
Accessibility: prefers-reduced-motion obrigatorio
"""

ANIMATION_CSS = """
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.btn-hover { transition: all 200ms cubic-bezier(0.25, 1, 0.5, 1); }
.btn-hover:hover { transform: scale(1.02); }
@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }
"""
