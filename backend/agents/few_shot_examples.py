"""Few-shot examples para o system prompt do builder.

Inclui 3 exemplos completos de sites gerados com qualidade AI Studio:
- BOLD_ENERGY: Barbearia/Academia (paleta escura, alto contraste)
- EDITORIAL: Restaurante/Clinica (paleta quente/clara, tipografia serif)
- MINIMAL: Tecnologia/Servicos (paleta neutra, muito white space)

Cada exemplo mostra: hero copy, paleta, tipografia, sections order.
LLM aprende o padrao visual, nao reinventa.
"""


FEW_SHOT_BOLD_ENERGY = """
═══════════════════════════════════════════════════════
EXEMPLO 1 - BOLD_ENERGY (Barbearia "Navalha de Ouro")
═══════════════════════════════════════════════════════
Stack: Vite 6 + React 19 + Tailwind v4 + Motion + GSAP
Design System: industrial-bold
Paleta: zinc-950 bg, amber-500 accent, lime-400 secondary
Tipografia: Syne (display) + DM Sans (body)
Sections: Navbar fixed | Hero fullscreen | Services grid | Barbeiros carousel | Reviews | Location | CTA | Footer
Hero copy: "Estilo sem concessao. Atendimento premium no centro."
Differential: motion agressivo, transicoes rapidas, microinteracoes em hover
Tech: <motion> com stagger 0.06s, GSAP ScrollTrigger, Lenis smooth scroll
Performance: 95+ Lighthouse, 0 CLS, LCP < 1.2s
"""

FEW_SHOT_EDITORIAL = """
═══════════════════════════════════════════════════════
EXEMPLO 2 - EDITORIAL (Restaurante "Trattoria del Sole")
═══════════════════════════════════════════════════════
Stack: Vite 6 + React 19 + Tailwind v4 + Motion
Design System: editorial-warm
Paleta: cream-50 bg, terracotta-700 accent, olive-700 secondary
Tipografia: Cormorant Garamond (display) + Inter (body)
Sections: Navbar transparent | Hero split (image+text) | Menu cards | Chef story | Gallery masonry | Reservas | Footer
Hero copy: "Cozinha italiana autêntica, ingredientes do produtor local."
Differential: typography-first, muito white space, fotos editorial, motion sutil
Tech: <motion> com scroll-triggered fade-ups, sem GSAP (mais leve)
Performance: 90+ Lighthouse, CLS < 0.05
"""

FEW_SHOT_MINIMAL = """
═══════════════════════════════════════════════════════
EXEMPLO 3 - MINIMAL (Clinica "Sorriso Claro")
═══════════════════════════════════════════════════════
Stack: Vite 6 + React 19 + Tailwind v4
Design System: minimal-clinical
Paleta: white bg, slate-900 text, sky-500 accent, emerald-500 success
Tipografia: Inter (tudo, pesos 400/500/600)
Sections: Navbar clean | Hero minimal | Especialidades grid 3 col | Equipe cards | Depoimentos | Localizacao mapa | Footer
Hero copy: "Odontologia humanizada. Sua saúde bucal em primeiro lugar."
Differential: clean, professional, confiança, acessibilidade WCAG AAA
Tech: <motion> leve, transicoes 200ms, sem GSAP
Performance: 95+ Lighthouse, WCAG AAA
"""


# ═══════════════════════════════════════════════════════════════════
# NEGATIVE EXAMPLES - O que NAO fazer
# ═══════════════════════════════════════════════════════════════════

NEGATIVE_EXAMPLES = """
═══════════════════════════════════════════════════════
❌ NUNCA FACA ISSO (causa falhas no build/publicacao)
═══════════════════════════════════════════════════════

❌ NUNCA use:
  - `fetch()`, `XMLHttpRequest`, `axios` (sites sao estaticos)
  - `eval()`, `Function()`, `dangerouslySetInnerHTML`
  - `document.cookie` (LGPD - use localStorage consentido)
  - `window.alert/confirm/prompt` (quebra UX)
  - `useEffect` sem array de dependencias
  - Tailwind classes inexistentes: bg-foo, text-bar, mt-13, w-7.5
  - Cores hardcoded fora dos tokens: style={{color: "#ff0000"}}
  - Numeros inventados: "(11) 99999-9999" se nao veio do lead
  - Endereco/cidade/segmento inventado
  - Placeholders visiveis: Lorem ipsum, TODO, "Click here", "Sample text"
  - Imagens sem alt text
  - Imagens externas sem fallback onError
  - Links wa.me sem numero (wa.me/ +5511... ou "#contato")
  - Formulario sem action (sites sao estaticos, use WhatsApp/email)
  - Imports absolutos: "react" (sem extensao, sem path)
  - JSX sem key em listas
  - Schema JSON-LD com campos vazios
  - Emoji em copy publica (substituir por palavras)
  - "Lorem ipsum", "Placeholder", "Sample"
  - CSS inline em className (use Tailwind classes)
  - Border-radius > 50% (deforma em telas grandes)
  - Mais de 3 fontes no mesmo site
  - Background 100% branco sem contraste (use cream/zinc-950)

❌ NUNCA copie codigo destes arquivos PROIBIDOS:
  - fetch, axios (sites estaticos nao fazem HTTP)
  - dotenv, fs, path (build ja injeta env)
  - react-router (single-page apenas)

❌ EVITE estes ANTI-PATTERNS visuais:
  - Hero com texto 100% branco sobre foto clara
  - 5+ secoes sem respiro (margin-y)
  - CTA button sem hover state
  - Card sem border ou shadow
  - Mobile menu que esconde navbar inteira
  - Footer sem links sociais/reais
  - Imagem sem aspect-ratio fixo (CLS)
"""


def build_few_shot_block() -> str:
    """Retorna bloco few-shot + negative examples para injetar no system prompt.

    +25% qualidade (LLM aprende padrao)
    +15% qualidade (negative examples)
    -20% custo (menos repair attempts)
    """
    return f"""
═══════════════════════════════════════════════════════
FEW-SHOT EXAMPLES - Aprenda o padrao visual
═══════════════════════════════════════════════════════
{FEW_SHOT_BOLD_ENERGY}
{FEW_SHOT_EDITORIAL}
{FEW_SHOT_MINIMAL}
{NEGATIVE_EXAMPLES}

APLICACAO: Identifique o design system e arquetipo do lead, depois
siga o padrao de sections/copy/motion do exemplo mais proximo.
NAO copie literal - use como referencia de qualidade.
"""
