# FraLib Visual System

Data: 2026-05-31

## Objetivo
FraLib deve gerar sites locais com direção editorial, impacto no primeiro viewport,
responsividade real e verdade factual. A IA pode decidir estética, mas não pode
quebrar spacing, contraste, localização, motion ou ritmo de seções.

## Regras Globais
1. Uma decisão visual por página: arquétipo + DNA visual + seed.
2. Seções não podem virar pilha linear de cards iguais.
3. Mapa, endereço e contato são uma composição única; nunca dois mapas.
4. Fallback de serviço não é seção visual. Sem serviços confirmados, a consulta
   vira nota curta em contato/sobre.
5. Texto em superfície clara deve ser escuro; texto em superfície escura deve ser claro.
6. Footer é fechamento de marca, não barra preta genérica.

## Spacing
- Container padrão: `min(1120px, calc(100vw - clamp(2rem, 7vw, 6rem)))`.
- Padding de seção desktop: `clamp(4.5rem, 9vw, 8.5rem)`.
- Padding de seção mobile: `clamp(3.25rem, 14vw, 5rem)`.
- Títulos usam `line-height` próximo de `.92` e `text-wrap: balance`.
- Parágrafos usam `line-height >= 1.6` e linha curta.
- Touch targets devem ter no mínimo `44px`.

## Cores
- Paletas devem usar contraste claro/escuro validável.
- CTAs usam acento saturado, não cinza opaco.
- BOLD_ENERGY: preto profundo, vermelho elétrico, branco quente, surfaces carvão.
- ZEN_PURE: branco/pastel limpo, texto escuro, acento suave e grande respiro.
- TRUST_ELITE: azul/marinho/cinza frio com contraste institucional.

## Motion
- Motion obrigatório por hooks: `data-reveal`, `data-parallax`, `card-stagger`,
  `mask-reveal`, `line-draw`.
- Animar somente `opacity` e `transform`.
- Respeitar `prefers-reduced-motion`.
- Não duplicar GSAP/Lenis; FraLib injeta runtime.

## Gates Visuais
- Rejeitar mapa duplicado.
- Rejeitar fallback visual legado de serviços.
- Rejeitar hero BOLD sem base escura, display, acento vermelho, parallax e stats.
- Normalizar seção de localização para um mapa canônico com endereço real.
- Injetar CSS global de layout/contraste no polish final.

## Referências Aplicadas
- Carbon: spacing com tokens e escala consistente.
- Material Design: layout responsivo guiado por grid e margens.
- Tailwind: breakpoints responsivos e escala utilitária previsível.
- WCAG 2.2: contraste mínimo para legibilidade.
