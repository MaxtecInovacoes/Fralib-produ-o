"""
Design Guidelines - Impeccable + Motion Principles
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
