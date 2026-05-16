"""design_context.py — Sistema de Design por Nicho (Open Design adaptado)
6 tokens CSS universais em OKLch + direção visual + perfil de animação por nicho.
"""
from typing import Dict

# ─── 5 DIREÇÕES VISUAIS ────────────────────────────────────────────────────────
# Cada direção define os 6 tokens universais em OKLch + tipografia + animação
# --bg       : fundo da página
# --surface  : cards, modais, painéis
# --fg       : texto primário
# --muted    : texto secundário / labels
# --border   : divisores, outlines
# --accent   : 1 cor de destaque — usada NO MÁXIMO 2x por tela

DIRECOES_VISUAIS = {
    "editorial": {"nome": "Editorial", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(7% 0.0 0)"}, "font_heading": "Gelasio", "font_body": "Gelasio", "vibe": "revista, tipografia serif refinada, grids estruturados", "animation": "elegante"},
    "agentic": {"nome": "Agentic", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(42% 0.0 0)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(46% 0.199 20)"}, "font_heading": "Playfair Display", "font_body": "Playfair Display", "vibe": "AI-first conversacional, controles minimos, fluxos delegados", "animation": "elegante"},
    "airbnb": {"nome": "Airbnb", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.0 0)", "--fg": "oklch(13% 0.0 0)", "--muted": "oklch(42% 0.0 0)", "--border": "oklch(87% 0.0 0)", "--accent": "oklch(40% 0.156 349)"}, "font_heading": "Airbnb Cereal VF", "font_body": "Airbnb Cereal VF", "vibe": "hospitaleiro, foto-driven, coral quente, UI arredondada", "animation": "elegante"},
    "airtable": {"nome": "Airtable", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(98% 0.003 210)", "--fg": "oklch(11% 0.011 219)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(89% 0.005 220)", "--accent": "oklch(35% 0.136 216)"}, "font_heading": "Haas Groot Disp", "font_body": "Haas", "vibe": "planilha-banco colorido, amigavel, estruturado", "animation": "elegante"},
    "ant": {"nome": "Ant", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(42% 0.183 215)"}, "font_heading": "Plus Jakarta Sans", "font_body": "Plus Jakarta Sans", "vibe": "enterprise estruturado, clareza, consistencia", "animation": "elegante"},
    "apple": {"nome": "Apple", "tokens": {"--bg": "oklch(96% 0.002 240)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(11% 0.002 240)", "--muted": "oklch(43% 0.004 240)", "--border": "oklch(82% 0.004 240)", "--accent": "oklch(38% 0.178 210)"}, "font_heading": "SF Pro Display", "font_body": "SF Pro Text", "vibe": "premium, white space generoso, cinematico", "animation": "elegante"},
    "application": {"nome": "Application", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(4% 0.002 240)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.144 271)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "dashboard app roxo, card-based, developer-first", "animation": "elegante"},
    "arc": {"nome": "Arc", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(10% 0.004 240)", "--muted": "oklch(55% 0.005 240)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(59% 0.125 12)"}, "font_heading": "Argent CF", "font_body": "Inter", "vibe": "translucido, gradientes quentes, sidebar-first", "animation": "vibrante"},
    "artistic": {"nome": "Artistic", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Limelight", "font_body": "Inter", "vibe": "expressivo, alto contraste, tipografia criativa", "animation": "vibrante"},
    "atelier_zero": {"nome": "Atelier Zero", "tokens": {"--bg": "oklch(91% 0.023 43)", "--surface": "oklch(94% 0.02 46)", "--fg": "oklch(8% 0.005 50)", "--muted": "oklch(33% 0.014 40)", "--border": "oklch(82% 0.031 43)", "--accent": "oklch(53% 0.114 8)"}, "font_heading": "Inter Tight", "font_body": "Inter", "vibe": "editorial magazine, canvas papel quente, tipografia oversized", "animation": "elegante"},
    "bento": {"nome": "Bento", "tokens": {"--bg": "oklch(96% 0.02 36)", "--surface": "oklch(96% 0.02 36)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(86% 0.045 21)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "modular grid, blocos card-like, hierarquia clara", "animation": "elegante"},
    "binance": {"nome": "Binance", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.0 0)", "--fg": "oklch(13% 0.006 225)", "--muted": "oklch(55% 0.019 215)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(72% 0.18 46)"}, "font_heading": "BinancePlex", "font_body": "BinancePlex", "vibe": "crypto exchange, amarelo dourado, urgencia trading", "animation": "energetico"},
    "bmw": {"nome": "Bmw", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(15% 0.0 0)", "--muted": "oklch(46% 0.0 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(38% 0.144 215)"}, "font_heading": "BMWTypeNextLatin Light", "font_body": "BMWTypeNextLatin", "vibe": "automotivo luxo, engenharia alema precisa", "animation": "elegante"},
    "bmw_m": {"nome": "Bmw M", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(10% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(49% 0.0 0)", "--border": "oklch(24% 0.0 0)", "--accent": "oklch(30% 0.158 4)"}, "font_heading": "BMW Type Next Latin Light", "font_body": "BMW Type Next Latin", "vibe": "motorsport, cockpit near-black, tricolor M", "animation": "energetico"},
    "bold": {"nome": "Bold", "tokens": {"--bg": "oklch(8% 0.0 0)", "--surface": "oklch(12% 0.0 0)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(60% 0.0 0)", "--border": "oklch(25% 0.0 0)", "--accent": "oklch(55% 0.18 210)"}, "font_heading": "Archivo Black", "font_body": "Inter", "vibe": "tipografia pesada, alto contraste, comanda atencao", "animation": "energetico"},
    "brutalism": {"nome": "Brutalism", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(9% 0.017 221)", "--accent": "oklch(48% 0.114 9)"}, "font_heading": "Darker Grotesque", "font_body": "Darker Grotesque", "vibe": "anti-design cru, concreto, minimalismo funcional", "animation": "energetico"},
    "bugatti": {"nome": "Bugatti", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(60% 0.0 0)", "--border": "oklch(60% 0.0 0)", "--accent": "oklch(100% 0.0 0)"}, "font_heading": "Bugatti Display", "font_body": "Bugatti Text Regular", "vibe": "hypercar, cinema-black, monocromatico monumental", "animation": "elegante"},
    "cafe": {"nome": "Cafe", "tokens": {"--bg": "oklch(97% 0.003 30)", "--surface": "oklch(97% 0.003 30)", "--fg": "oklch(18% 0.025 24)", "--muted": "oklch(37% 0.02 26)", "--border": "oklch(89% 0.009 30)", "--accent": "oklch(28% 0.034 25)"}, "font_heading": "Poppins", "font_body": "Poppins", "vibe": "aconchegante, tons quentes cafe, tipografia suave", "animation": "elegante"},
    "cal": {"nome": "Cal", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(14% 0.0 0)", "--muted": "oklch(54% 0.0 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(14% 0.0 0)"}, "font_heading": "Cal Sans", "font_body": "Inter", "vibe": "agendamento open-source, monocromatico, developer", "animation": "elegante"},
    "canva": {"nome": "Canva", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.002 220)", "--fg": "oklch(7% 0.008 210)", "--muted": "oklch(39% 0.007 213)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(29% 0.149 266)"}, "font_heading": "Canva Sans", "font_body": "Canva Sans", "vibe": "criacao visual, gradiente roxo-azul, geometria amigavel", "animation": "vibrante"},
    "cisco": {"nome": "Cisco", "tokens": {"--bg": "oklch(9% 0.013 212)", "--surface": "oklch(22% 0.002 240)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(62% 0.003 240)", "--border": "oklch(35% 0.002 240)", "--accent": "oklch(51% 0.167 196)"}, "font_heading": "CiscoSansTT", "font_body": "CiscoSansTT", "vibe": "infra enterprise, dark confianca, Cisco Blue", "animation": "elegante"},
    "claude": {"nome": "Claude", "tokens": {"--bg": "oklch(96% 0.006 53)", "--surface": "oklch(98% 0.004 48)", "--fg": "oklch(8% 0.001 60)", "--muted": "oklch(52% 0.006 53)", "--border": "oklch(93% 0.008 48)", "--accent": "oklch(47% 0.106 15)"}, "font_heading": "Anthropic Serif", "font_body": "Anthropic Sans", "vibe": "AI assistente, terracota quente, parchment premium", "animation": "elegante"},
    "clay": {"nome": "Clay", "tokens": {"--bg": "oklch(98% 0.002 40)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(83% 0.014 40)", "--accent": "oklch(42% 0.103 154)"}, "font_heading": "Roobert", "font_body": "Roobert", "vibe": "agencia criativa, formas organicas, gradientes suaves", "animation": "vibrante"},
    "claymorphism": {"nome": "Claymorphism", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(22% 0.089 225)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Poppins", "font_body": "Montserrat", "vibe": "3D suave arredondado, argila maleavel, puffy colorido", "animation": "vibrante"},
    "clean": {"nome": "Clean", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Poppins", "font_body": "Roboto", "vibe": "simplicidade, whitespace amplo, paleta limitada", "animation": "elegante"},
    "clickhouse": {"nome": "Clickhouse", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(8% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(63% 0.0 0)", "--border": "oklch(25% 0.0 0)", "--accent": "oklch(95% 0.118 62)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "analytics rapido, amarelo-neon acido em preto", "animation": "energetico"},
    "cohere": {"nome": "Cohere", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(98% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(58% 0.009 240)", "--border": "oklch(85% 0.003 240)", "--accent": "oklch(36% 0.154 217)"}, "font_heading": "CohereText", "font_body": "Unica77", "vibe": "AI enterprise, gradientes vibrantes, data-rich", "animation": "elegante"},
    "coinbase": {"nome": "Coinbase", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(94% 0.004 216)", "--fg": "oklch(4% 0.002 220)", "--muted": "oklch(38% 0.015 221)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(30% 0.2 221)"}, "font_heading": "CoinbaseDisplay", "font_body": "CoinbaseText", "vibe": "crypto exchange, azul limpo, confianca institucional", "animation": "elegante"},
    "colorful": {"nome": "Colorful", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "paletas vibrantes, alto contraste, gradientes memoraveis", "animation": "vibrante"},
    "composio": {"nome": "Composio", "tokens": {"--bg": "oklch(6% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(27% 0.0 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(8% 0.161 238)"}, "font_heading": "abcDiatype", "font_body": "abcDiatype", "vibe": "integracao ferramentas, dark moderno, terminal developer", "animation": "elegante"},
    "contemporary": {"nome": "Contemporary", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(23% 0.175 294)"}, "font_heading": "Jost", "font_body": "Jost", "vibe": "minimalista era-atual, bento grids, dark mode", "animation": "vibrante"},
    "corporate": {"nome": "Corporate", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Poppins", "font_body": "Open Sans", "vibe": "profissional brand-aligned, grids estruturados, enterprise", "animation": "elegante"},
    "cosmic": {"nome": "Cosmic", "tokens": {"--bg": "oklch(4% 0.013 240)", "--surface": "oklch(8% 0.027 240)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(54% 0.027 240)", "--border": "oklch(21% 0.027 240)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Audiowide", "font_body": "Inter", "vibe": "sci-fi futurista, temas escuros, neon vibrante, espacial", "animation": "vibrante"},
    "creative": {"nome": "Creative", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Bangers", "font_body": "Inter", "vibe": "playful character-driven, tipografia expressiva, ousado", "animation": "energetico"},
    "cursor": {"nome": "Cursor", "tokens": {"--bg": "oklch(94% 0.004 48)", "--surface": "oklch(90% 0.005 50)", "--fg": "oklch(14% 0.006 53)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(83% 0.005 50)", "--accent": "oklch(42% 0.192 19)"}, "font_heading": "CursorGothic", "font_body": "jjannon", "vibe": "editor AI-first, dark sleek, minimalismo quente", "animation": "elegante"},
    "dashboard": {"nome": "Dashboard", "tokens": {"--bg": "oklch(4% 0.002 240)", "--surface": "oklch(4% 0.002 240)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(32% 0.125 210)"}, "font_heading": "IBM Plex Sans", "font_body": "IBM Plex Sans", "vibe": "cloud-platform dark, grids modulares, glass-like", "animation": "elegante"},
    "default": {"nome": "Default", "tokens": {"--bg": "oklch(98% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(7% 0.0 0)", "--muted": "oklch(42% 0.0 0)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(42% 0.147 220)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "neutro moderno, B2B tools, dashboards utilitarios", "animation": "elegante"},
    "discord": {"nome": "Discord", "tokens": {"--bg": "oklch(20% 0.005 223)", "--surface": "oklch(18% 0.005 220)", "--fg": "oklch(87% 0.005 210)", "--muted": "oklch(60% 0.013 214)", "--border": "oklch(25% 0.006 225)", "--accent": "oklch(43% 0.121 235)"}, "font_heading": "gg sans", "font_body": "gg sans", "vibe": "voz/chat, blurple profundo, dark-first, playful", "animation": "vibrante"},
    "dithered": {"nome": "Dithered", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Space Grotesk", "font_body": "Open Sans", "vibe": "dot-pattern retro, paleta limitada, nostalgico", "animation": "elegante"},
    "doodle": {"nome": "Doodle", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(64% 0.122 198)"}, "font_heading": "Delius Swash Caps", "font_body": "Inter", "vibe": "hand-drawn sketch, fontes manuscritas, playful informal", "animation": "vibrante"},
    "dramatic": {"nome": "Dramatic", "tokens": {"--bg": "oklch(4% 0.002 240)", "--surface": "oklch(4% 0.002 240)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(44% 0.121 258)"}, "font_heading": "Outfit", "font_body": "Outfit", "vibe": "teatral alto contraste, layouts ousados, imersivo", "animation": "energetico"},
    "duolingo": {"nome": "Duolingo", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.0 0)", "--fg": "oklch(24% 0.0 0)", "--muted": "oklch(47% 0.0 0)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(65% 0.158 94)"}, "font_heading": "Feather Bold", "font_body": "Mona Sans", "vibe": "aprendizado, verde owl, sombras chunky, gamificado", "animation": "energetico"},
    "warm_editorial": {"nome": "Editorial", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(7% 0.0 0)"}, "font_heading": "Gelasio", "font_body": "Gelasio", "vibe": "revista, tipografia serif refinada, grids estruturados", "animation": "elegante"},
    "elegant": {"nome": "Elegant", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Google Sans", "font_body": "Google Sans", "vibe": "gracioso refinado, tipografia delicada, sofisticacao", "animation": "elegante"},
    "elevenlabs": {"nome": "Elevenlabs", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(45% 0.011 34)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "Waldenburg", "font_body": "Inter", "vibe": "voz AI, cinematico, audio-waveform, headings finos", "animation": "elegante"},
    "energetic": {"nome": "Energetic", "tokens": {"--bg": "oklch(98% 0.005 0)", "--surface": "oklch(96% 0.008 0)", "--fg": "oklch(12% 0.01 0)", "--muted": "oklch(45% 0.01 0)", "--border": "oklch(88% 0.01 0)", "--accent": "oklch(55% 0.22 145)"}, "font_heading": "Oswald", "font_body": "Inter", "vibe": "dinamico vibrante, bordas grossas, geometrico, movimento", "animation": "energetico"},
    "enterprise": {"nome": "Enterprise", "tokens": {"--bg": "oklch(92% 0.012 48)", "--surface": "oklch(92% 0.012 48)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(14% 0.029 180)"}, "font_heading": "Oswald", "font_body": "Ubuntu", "vibe": "enterprise limpo, data-driven, drag-and-drop", "animation": "elegante"},
    "expo": {"nome": "Expo", "tokens": {"--bg": "oklch(94% 0.002 240)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(39% 0.009 220)", "--border": "oklch(23% 0.007 213)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "React Native, tema escuro, pill-shaped, codigo", "animation": "elegante"},
    "expressive": {"nome": "Expressive", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.141 333)"}, "font_heading": "IBM Plex Mono", "font_body": "IBM Plex Mono", "vibe": "personality-driven, cores ousadas, playful dinamico", "animation": "vibrante"},
    "fantasy": {"nome": "Fantasy", "tokens": {"--bg": "oklch(4% 0.013 240)", "--surface": "oklch(8% 0.027 240)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(54% 0.027 240)", "--border": "oklch(21% 0.027 240)", "--accent": "oklch(28% 0.158 217)"}, "font_heading": "New Rocker", "font_body": "Inter", "vibe": "game-inspired, visuais premium, paletas ricas, imersivo", "animation": "vibrante"},
    "ferrari": {"nome": "Ferrari", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(19% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(56% 0.0 0)", "--border": "oklch(82% 0.0 0)", "--accent": "oklch(30% 0.149 4)"}, "font_heading": "FerrariSans", "font_body": "FerrariSans", "vibe": "luxo automotivo, chiaroscuro, Ferrari Red, cinematico", "animation": "elegante"},
    "figma": {"nome": "Figma", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "figmaSans", "font_body": "figmaSans", "vibe": "design tool, gradientes multi-color, black-and-white chrome", "animation": "elegante"},
    "flat": {"nome": "Flat", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(51% 0.143 14)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "2D minimalista, cores vibrantes, sem efeitos 3D", "animation": "elegante"},
    "framer": {"nome": "Framer", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(4% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(65% 0.0 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(50% 0.2 204)"}, "font_heading": "GT Walsheim Framer Medium", "font_body": "Inter Variable", "vibe": "cinematico dark, letter-spacing negativo, electric blue", "animation": "energetico"},
    "friendly": {"nome": "Friendly", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(87% 0.02 353)"}, "font_heading": "Noto Serif Display", "font_body": "Noto Serif Display", "vibe": "arredondado, whitespace amplo, pastel suave", "animation": "elegante"},
    "futuristic": {"nome": "Futuristic", "tokens": {"--bg": "oklch(4% 0.013 240)", "--surface": "oklch(8% 0.027 240)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(54% 0.027 240)", "--border": "oklch(21% 0.027 240)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Audiowide", "font_body": "Roboto", "vibe": "tech-inspired, layouts modernos, inovacao sleek", "animation": "vibrante"},
    "github": {"nome": "Github", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.003 210)", "--fg": "oklch(14% 0.007 213)", "--muted": "oklch(42% 0.013 212)", "--border": "oklch(84% 0.011 210)", "--accent": "oklch(36% 0.164 212)"}, "font_heading": "system-ui", "font_body": "system-ui", "vibe": "code-forward, funcional denso, blue-on-white, Primer", "animation": "elegante"},
    "glassmorphism": {"nome": "Glassmorphism", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(8% 0.0 0)", "--muted": "oklch(22% 0.02 254)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.181 224)"}, "font_heading": "Plus Jakarta Sans", "font_body": "Plus Jakarta Sans", "vibe": "frosted glass, blur translucido, bordas luminosas", "animation": "elegante"},
    "gradient": {"nome": "Gradient", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(24% 0.184 275)"}, "font_heading": "Space Grotesk", "font_body": "Montserrat", "vibe": "transicoes suaves, gradient-rich, playful com profundidade", "animation": "vibrante"},
    "hashicorp": {"nome": "Hashicorp", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(95% 0.002 210)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(41% 0.013 222)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(34% 0.096 268)"}, "font_heading": "HashiCorp Sans", "font_body": "system-ui", "vibe": "infra automation, enterprise dual-mode, multi-product", "animation": "elegante"},
    "hud": {"nome": "Hud", "tokens": {"--bg": "oklch(4% 0.0 0)", "--surface": "oklch(7% 0.004 216)", "--fg": "oklch(73% 0.2 135)", "--muted": "oklch(53% 0.05 120)", "--border": "oklch(13% 0.008 210)", "--accent": "oklch(73% 0.2 135)"}, "font_heading": "Inter", "font_body": "JetBrains Mono", "vibe": "fighter jet display, phosphor green, all-caps data", "animation": "energetico"},
    "huggingface": {"nome": "Huggingface", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(98% 0.0 0)", "--fg": "oklch(7% 0.008 216)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(81% 0.176 48)"}, "font_heading": "IBM Plex Mono", "font_body": "Source Sans Pro", "vibe": "ML community, sunshine yellow, monospace, cheerful", "animation": "vibrante"},
    "ibm": {"nome": "Ibm", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.0 0)", "--fg": "oklch(9% 0.0 0)", "--muted": "oklch(32% 0.0 0)", "--border": "oklch(78% 0.0 0)", "--accent": "oklch(36% 0.187 219)"}, "font_heading": "IBM Plex Sans", "font_body": "IBM Plex Sans", "vibe": "enterprise Carbon, structured blue, corporate precision", "animation": "elegante"},
    "intercom": {"nome": "Intercom", "tokens": {"--bg": "oklch(98% 0.003 45)", "--surface": "oklch(98% 0.003 45)", "--fg": "oklch(7% 0.0 0)", "--muted": "oklch(48% 0.002 60)", "--border": "oklch(86% 0.006 37)", "--accent": "oklch(45% 0.2 20)"}, "font_heading": "Saans", "font_body": "Saans", "vibe": "messaging, warm off-white, negative tracking, Fin Orange", "animation": "vibrante"},
    "kami": {"nome": "Kami", "tokens": {"--bg": "oklch(96% 0.006 53)", "--surface": "oklch(98% 0.004 48)", "--fg": "oklch(8% 0.001 60)", "--muted": "oklch(31% 0.005 43)", "--border": "oklch(90% 0.009 50)", "--accent": "oklch(20% 0.052 215)"}, "font_heading": "Charter", "font_body": "Charter", "vibe": "editorial paper, parchment quente, ink-blue, serif-led", "animation": "elegante"},
    "kraken": {"nome": "Kraken", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(7% 0.003 225)", "--muted": "oklch(59% 0.016 231)", "--border": "oklch(87% 0.005 240)", "--accent": "oklch(30% 0.153 259)"}, "font_heading": "Kraken-Brand", "font_body": "IBM Plex Sans", "vibe": "crypto trading, purple profissional, data-dense", "animation": "elegante"},
    "lamborghini": {"nome": "Lamborghini", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(13% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(49% 0.0 0)", "--border": "oklch(27% 0.0 0)", "--accent": "oklch(75% 0.2 45)"}, "font_heading": "LamboType", "font_body": "LamboType", "vibe": "supercar, true black, gold accents, uppercase extremo", "animation": "energetico"},
    "levels": {"nome": "Levels", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(15% 0.002 240)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "conversion-focused, remove fricao, clareza e velocidade", "animation": "elegante"},
    "linear": {"nome": "Linear", "tokens": {"--bg": "oklch(3% 0.002 210)", "--surface": "oklch(6% 0.002 210)", "--fg": "oklch(97% 0.001 180)", "--muted": "oklch(56% 0.011 219)", "--border": "oklch(13% 0.0 0)", "--accent": "oklch(44% 0.091 234)"}, "font_heading": "Inter Variable", "font_body": "Inter Variable", "vibe": "ultra-minimal dark, project management, purple accent", "animation": "elegante"},
    "lingo": {"nome": "Lingo", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(24% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(65% 0.158 94)"}, "font_heading": "Nunito", "font_body": "Nunito", "vibe": "playful minimal, bright colors, tactile 3D borders", "animation": "vibrante"},
    "loom": {"nome": "Loom", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.001 240)", "--fg": "oklch(12% 0.003 240)", "--muted": "oklch(43% 0.009 229)", "--border": "oklch(89% 0.002 240)", "--accent": "oklch(41% 0.119 242)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "async video, purple primary, friendly, profissional", "animation": "elegante"},
    "lovable": {"nome": "Lovable", "tokens": {"--bg": "oklch(96% 0.008 42)", "--surface": "oklch(96% 0.008 42)", "--fg": "oklch(11% 0.0 0)", "--muted": "oklch(37% 0.002 60)", "--border": "oklch(92% 0.006 45)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Camera Plain Variable", "font_body": "Camera Plain Variable", "vibe": "AI full-stack, parchment quente, humanist typeface", "animation": "elegante"},
    "luxury": {"nome": "Luxury", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(98% 0.0 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(98% 0.0 0)"}, "font_heading": "Oswald", "font_body": "Oswald", "vibe": "high-end dark, bold headings, monocromatico premium", "animation": "elegante"},
    "mastercard": {"nome": "Mastercard", "tokens": {"--bg": "oklch(94% 0.009 44)", "--surface": "oklch(98% 0.002 30)", "--fg": "oklch(8% 0.001 60)", "--muted": "oklch(41% 0.0 0)", "--border": "oklch(81% 0.008 36)", "--accent": "oklch(37% 0.162 20)"}, "font_heading": "MarkForMC", "font_body": "MarkForMC", "vibe": "pagamentos global, cream quente, pill shapes, editorial", "animation": "elegante"},
    "material": {"nome": "Material", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.116 254)"}, "font_heading": "Roboto", "font_body": "Inter", "vibe": "Google Material, layered surfaces, dynamic theming", "animation": "vibrante"},
    "meta": {"nome": "Meta", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.005 210)", "--fg": "oklch(2% 0.0 0)", "--muted": "oklch(40% 0.005 220)", "--border": "oklch(82% 0.005 220)", "--accent": "oklch(34% 0.176 213)"}, "font_heading": "Optimistic VF", "font_body": "Optimistic VF", "vibe": "tech retail, photography-first, Meta Blue CTAs", "animation": "elegante"},
    "minimal": {"nome": "Minimal", "tokens": {"--bg": "oklch(96% 0.002 60)", "--surface": "oklch(96% 0.002 60)", "--fg": "oklch(5% 0.002 60)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(5% 0.002 60)"}, "font_heading": "Inter", "font_body": "Open Sans", "vibe": "stripped-back, whitespace, tipografia restrained, clareza", "animation": "elegante"},
    "minimax": {"nome": "Minimax", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(13% 0.0 0)", "--muted": "oklch(56% 0.004 240)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.173 222)"}, "font_heading": "Outfit", "font_body": "DM Sans", "vibe": "AI model provider, white-dominant, pill-button geometry", "animation": "vibrante"},
    "mintlify": {"nome": "Mintlify", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(5% 0.0 0)", "--muted": "oklch(40% 0.0 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(70% 0.158 158)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "docs platform, green-accented, reading-optimized", "animation": "elegante"},
    "miro": {"nome": "Miro", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(11% 0.002 240)", "--muted": "oklch(35% 0.016 226)", "--border": "oklch(89% 0.006 225)", "--accent": "oklch(48% 0.128 230)"}, "font_heading": "Roobert PRO Medium", "font_body": "Noto Sans", "vibe": "visual collaboration, pastel accents, infinite canvas", "animation": "vibrante"},
    "mission_control": {"nome": "Mission Control", "tokens": {"--bg": "oklch(7% 0.016 223)", "--surface": "oklch(9% 0.017 221)", "--fg": "oklch(94% 0.017 218)", "--muted": "oklch(63% 0.047 216)", "--border": "oklch(21% 0.051 214)", "--accent": "oklch(73% 0.2 43)"}, "font_heading": "Inter", "font_body": "JetBrains Mono", "vibe": "aerospace mission, dark command center, amber telemetry", "animation": "energetico"},
    "mistral_ai": {"nome": "Mistral Ai", "tokens": {"--bg": "oklch(98% 0.016 45)", "--surface": "oklch(94% 0.048 45)", "--fg": "oklch(12% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(44% 0.184 17)"}, "font_heading": "Arial", "font_body": "Arial", "vibe": "french AI, golden-amber, massive display, warm declarativo", "animation": "energetico"},
    "modern": {"nome": "Modern", "tokens": {"--bg": "oklch(28% 0.053 259)", "--surface": "oklch(28% 0.053 259)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(80% 0.0 0)", "--border": "oklch(39% 0.053 255)", "--accent": "oklch(28% 0.053 259)"}, "font_heading": "IBM Plex Serif", "font_body": "IBM Plex Serif", "vibe": "editorial contemporaneo, serif, paletas minimas, polido", "animation": "elegante"},
    "mongodb": {"nome": "Mongodb", "tokens": {"--bg": "oklch(10% 0.034 198)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(41% 0.02 202)", "--border": "oklch(76% 0.009 170)", "--accent": "oklch(69% 0.186 145)"}, "font_heading": "MongoDB Value Serif", "font_body": "Euclid Circular A", "vibe": "database, forest teal-black, neon green, editorial serif", "animation": "vibrante"},
    "mono": {"nome": "Mono", "tokens": {"--bg": "oklch(90% 0.002 20)", "--surface": "oklch(90% 0.002 20)", "--fg": "oklch(45% 0.01 28)", "--muted": "oklch(45% 0.01 28)", "--border": "oklch(83% 0.002 20)", "--accent": "oklch(74% 0.18 110)"}, "font_heading": "Space Mono", "font_body": "Space Mono", "vibe": "monospace-driven, matrix-inspired, hacker-chic", "animation": "energetico"},
    "neobrutalism": {"nome": "Neobrutalism", "tokens": {"--bg": "oklch(98% 0.002 60)", "--surface": "oklch(98% 0.002 60)", "--fg": "oklch(16% 0.025 216)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(16% 0.025 216)", "--accent": "oklch(77% 0.198 47)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "brutalism moderno, bold borders, vivid accents, raw", "animation": "energetico"},
    "neon": {"nome": "Neon", "tokens": {"--bg": "oklch(4% 0.013 240)", "--surface": "oklch(8% 0.027 240)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(54% 0.027 240)", "--border": "oklch(21% 0.027 240)", "--accent": "oklch(86% 0.127 81)"}, "font_heading": "STIX Two Text", "font_body": "Roboto", "vibe": "electric neon glow, alto contraste, attention-grabbing", "animation": "energetico"},
    "neumorphism": {"nome": "Neumorphism", "tokens": {"--bg": "oklch(90% 0.002 20)", "--surface": "oklch(90% 0.002 20)", "--fg": "oklch(16% 0.02 215)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(83% 0.002 20)", "--accent": "oklch(31% 0.08 180)"}, "font_heading": "Space Mono", "font_body": "Space Mono", "vibe": "soft extruded, inner/outer shadows, tactile monocromatico", "animation": "elegante"},
    "nike": {"nome": "Nike", "tokens": {"--bg": "oklch(8% 0.0 0)", "--surface": "oklch(14% 0.0 0)", "--fg": "oklch(97% 0.0 0)", "--muted": "oklch(60% 0.0 0)", "--border": "oklch(22% 0.0 0)", "--accent": "oklch(60% 0.22 30)"}, "font_heading": "Oswald", "font_body": "Inter", "vibe": "athletic retail, monochrome, massive uppercase, kinetic", "animation": "energetico"},
    "notion": {"nome": "Notion", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.002 30)", "--fg": "oklch(10% 0.0 0)", "--muted": "oklch(62% 0.009 33)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(39% 0.174 208)"}, "font_heading": "NotionInter", "font_body": "NotionInter", "vibe": "workspace, warm minimalism, soft surfaces, analog warmth", "animation": "elegante"},
    "nvidia": {"nome": "Nvidia", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(10% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(46% 0.0 0)", "--border": "oklch(37% 0.0 0)", "--accent": "oklch(62% 0.145 82)"}, "font_heading": "NVIDIA-EMEA", "font_body": "NVIDIA-EMEA", "vibe": "GPU computing, green-black energy, precision engineering", "animation": "energetico"},
    "ollama": {"nome": "Ollama", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(98% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(45% 0.0 0)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "SF Pro Rounded", "font_body": "system-ui", "vibe": "LLMs local, terminal-first, radical minimalism, grayscale", "animation": "elegante"},
    "openai": {"nome": "Openai", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(98% 0.0 0)", "--fg": "oklch(5% 0.0 0)", "--muted": "oklch(43% 0.0 0)", "--border": "oklch(90% 0.0 0)", "--accent": "oklch(51% 0.115 165)"}, "font_heading": "Signifier", "font_body": "Inter", "vibe": "research lab, near-monochrome, editorial serif, clinical", "animation": "elegante"},
    "opencode_ai": {"nome": "Opencode Ai", "tokens": {"--bg": "oklch(12% 0.002 0)", "--surface": "oklch(18% 0.003 0)", "--fg": "oklch(99% 0.001 0)", "--muted": "oklch(60% 0.002 0)", "--border": "oklch(27% 0.0 0)", "--accent": "oklch(41% 0.2 211)"}, "font_heading": "Berkeley Mono", "font_body": "Berkeley Mono", "vibe": "AI coding, terminal-native monospace, warm dark", "animation": "elegante"},
    "pacman": {"nome": "Pacman", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(77% 0.053 8)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(28% 0.147 233)"}, "font_heading": "Press Start 2P", "font_body": "Inter", "vibe": "retro arcade, pixel fonts, dotted borders, 8-bit", "animation": "energetico"},
    "paper": {"nome": "Paper", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(7% 0.0 0)"}, "font_heading": "Montserrat", "font_body": "Roboto", "vibe": "print-inspired, texturas papel, cores minimas, tactile", "animation": "elegante"},
    "perspective": {"nome": "Perspective", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(57% 0.148 160)"}, "font_heading": "Oswald", "font_body": "Poppins", "vibe": "spatial depth, isometric, vanishing points, 3D-like", "animation": "vibrante"},
    "pinterest": {"nome": "Pinterest", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(90% 0.004 60)", "--fg": "oklch(11% 0.007 293)", "--muted": "oklch(57% 0.004 60)", "--border": "oklch(90% 0.004 60)", "--accent": "oklch(20% 0.18 351)"}, "font_heading": "Pin Sans", "font_body": "Pin Sans", "vibe": "visual discovery, olive-toned, red accent, masonry grid", "animation": "elegante"},
    "playstation": {"nome": "Playstation", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.004 216)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(42% 0.0 0)", "--border": "oklch(95% 0.0 0)", "--accent": "oklch(37% 0.16 207)"}, "font_heading": "SST", "font_body": "SST", "vibe": "gaming console, three-surface, quiet-authority, cyan hover", "animation": "vibrante"},
    "posthog": {"nome": "Posthog", "tokens": {"--bg": "oklch(97% 0.01 37)", "--surface": "oklch(93% 0.005 70)", "--fg": "oklch(31% 0.007 73)", "--muted": "oklch(40% 0.007 73)", "--border": "oklch(75% 0.008 72)", "--accent": "oklch(42% 0.192 19)"}, "font_heading": "IBM Plex Sans Variable", "font_body": "IBM Plex Sans Variable", "vibe": "product analytics, hedgehog, sage/olive, anti-corporate", "animation": "vibrante"},
    "premium": {"nome": "Premium", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "Apple-inspired, spacing preciso, polished refined", "animation": "elegante"},
    "professional": {"nome": "Professional", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(80% 0.184 48)"}, "font_heading": "Poppins", "font_body": "Poppins", "vibe": "business-ready, moderno, trustworthy, estruturado", "animation": "elegante"},
    "publication": {"nome": "Publication", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.024 213)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(45% 0.127 271)"}, "font_heading": "Oswald", "font_body": "Nunito", "vibe": "print-inspired, editorial grids, tipografia expressiva", "animation": "elegante"},
    "raycast": {"nome": "Raycast", "tokens": {"--bg": "oklch(3% 0.002 220)", "--surface": "oklch(7% 0.001 180)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(42% 0.002 210)", "--border": "oklch(15% 0.003 195)", "--accent": "oklch(52% 0.122 0)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "productivity launcher, dark chrome, gradient accents, macOS", "animation": "elegante"},
    "refined": {"nome": "Refined", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Playfair Display", "font_body": "Playfair Display", "vibe": "curated minimal, serif elegante, paletas sofisticadas", "animation": "elegante"},
    "renault": {"nome": "Renault", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(85% 0.002 60)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(82% 0.187 56)"}, "font_heading": "NouvelR", "font_body": "NouvelR", "vibe": "automotivo frances, aurora gradients, bold energy", "animation": "vibrante"},
    "replicate": {"nome": "Replicate", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(13% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(31% 0.18 9)"}, "font_heading": "rb-freigeist-neue", "font_body": "basier-square", "vibe": "ML API, orange-red gradient, massive display, pill-shaped", "animation": "energetico"},
    "resend": {"nome": "Resend", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(94% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(58% 0.176 26)"}, "font_heading": "Domaine Display", "font_body": "Inter", "vibe": "email API, minimal dark, cinematic black, icy borders", "animation": "elegante"},
    "retro": {"nome": "Retro", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Macondo", "font_body": "Inter", "vibe": "vintage-inspired, high-contrast retro, nostalgico", "animation": "vibrante"},
    "revolut": {"nome": "Revolut", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(96% 0.0 0)", "--fg": "oklch(11% 0.005 210)", "--muted": "oklch(58% 0.013 208)", "--border": "oklch(79% 0.003 240)", "--accent": "oklch(35% 0.118 238)"}, "font_heading": "Aeonik Pro", "font_body": "Inter", "vibe": "digital banking, fintech precision, pill-everything", "animation": "elegante"},
    "runwayml": {"nome": "Runwayml", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(10% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(49% 0.014 217)", "--border": "oklch(15% 0.002 240)", "--accent": "oklch(100% 0.0 0)"}, "font_heading": "abcNormal", "font_body": "abcNormal", "vibe": "AI video, cinematico dark, full-bleed, interface invisivel", "animation": "elegante"},
    "sanity": {"nome": "Sanity", "tokens": {"--bg": "oklch(4% 0.0 0)", "--surface": "oklch(13% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(47% 0.0 0)", "--border": "oklch(21% 0.0 0)", "--accent": "oklch(51% 0.122 5)"}, "font_heading": "waldenburgNormal", "font_body": "IBM Plex Mono", "vibe": "headless CMS, near-black, precision typography, coral-red", "animation": "elegante"},
    "sentry": {"nome": "Sentry", "tokens": {"--bg": "oklch(10% 0.023 259)", "--surface": "oklch(7% 0.016 258)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(91% 0.005 220)", "--border": "oklch(20% 0.035 252)", "--accent": "oklch(85% 0.126 77)"}, "font_heading": "Dammit Sans", "font_body": "Rubik", "vibe": "error monitoring, dark purple, data-dense, lime-green", "animation": "vibrante"},
    "shadcn": {"nome": "Shadcn", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "Geist", "font_body": "Geist", "vibe": "minimal components, monochrome, utility-first", "animation": "elegante"},
    "shopify": {"nome": "Shopify", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(3% 0.006 188)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(63% 0.007 240)", "--border": "oklch(16% 0.015 196)", "--accent": "oklch(78% 0.149 155)"}, "font_heading": "NeueHaasGrotesk", "font_body": "Inter Variable", "vibe": "e-commerce, dark-first cinematico, neon green accent", "animation": "elegante"},
    "simple": {"nome": "Simple", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "no-frills, clean typography, neutral, intuitivo", "animation": "elegante"},
    "skeumorphism": {"nome": "Skeumorphism", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(38% 0.196 14)"}, "font_heading": "Germania One", "font_body": "Roboto", "vibe": "real-world mimicry, textured surfaces, 3D effects", "animation": "vibrante"},
    "slack": {"nome": "Slack", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(97% 0.0 0)", "--fg": "oklch(11% 0.001 300)", "--muted": "oklch(38% 0.001 300)", "--border": "oklch(87% 0.0 0)", "--accent": "oklch(14% 0.042 299)"}, "font_heading": "Larsseit", "font_body": "system-ui", "vibe": "workplace, aubergine-primary, warm approachable", "animation": "vibrante"},
    "sleek": {"nome": "Sleek", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Inter", "font_body": "Inter", "vibe": "modern minimalist, clean lines, subtle interactions", "animation": "elegante"},
    "spacex": {"nome": "Spacex", "tokens": {"--bg": "oklch(0% 0.0 0)", "--surface": "oklch(0% 0.0 0)", "--fg": "oklch(94% 0.008 240)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(27% 0.0 0)", "--accent": "oklch(100% 0.0 0)"}, "font_heading": "D-DIN-Bold", "font_body": "D-DIN", "vibe": "space tech, stark black-white, full-bleed, aerospace stencil", "animation": "elegante"},
    "spacious": {"nome": "Spacious", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Montserrat", "font_body": "Open Sans", "vibe": "generous whitespace, consistent padding, grid-based", "animation": "elegante"},
    "spotify": {"nome": "Spotify", "tokens": {"--bg": "oklch(7% 0.0 0)", "--surface": "oklch(9% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(70% 0.0 0)", "--border": "oklch(30% 0.0 0)", "--accent": "oklch(66% 0.145 141)"}, "font_heading": "CircularSp", "font_body": "CircularSp", "vibe": "music streaming, vibrant green on dark, album-art-driven", "animation": "energetico"},
    "starbucks": {"nome": "Starbucks", "tokens": {"--bg": "oklch(94% 0.005 43)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(29% 0.077 160)", "--muted": "oklch(92% 0.003 30)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(35% 0.092 158)"}, "font_heading": "SoDoSans", "font_body": "SoDoSans", "vibe": "coffee retail, four-tier green, warm cream, full-pill", "animation": "vibrante"},
    "storytelling": {"nome": "Storytelling", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.017 221)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(48% 0.147 217)"}, "font_heading": "Abril Fatface", "font_body": "Inter", "vibe": "narrative-driven, emotionally resonant, visuals+copy", "animation": "vibrante"},
    "stripe": {"nome": "Stripe", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.034 211)", "--muted": "oklch(45% 0.032 217)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(30% 0.153 248)"}, "font_heading": "sohne-var", "font_body": "sohne-var", "vibe": "payment infra, purple gradients, weight-300 elegance", "animation": "elegante"},
    "supabase": {"nome": "Supabase", "tokens": {"--bg": "oklch(9% 0.0 0)", "--surface": "oklch(6% 0.0 0)", "--fg": "oklch(98% 0.0 0)", "--muted": "oklch(54% 0.0 0)", "--border": "oklch(18% 0.0 0)", "--accent": "oklch(67% 0.114 153)"}, "font_heading": "Circular", "font_body": "Circular", "vibe": "open-source Firebase, dark emerald, code-first, HSL layers", "animation": "elegante"},
    "superhuman": {"nome": "Superhuman", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(16% 0.002 30)", "--muted": "oklch(85% 0.007 27)", "--border": "oklch(85% 0.007 27)", "--accent": "oklch(75% 0.053 258)"}, "font_heading": "Super Sans VF", "font_body": "Super Sans VF", "vibe": "fast email, premium dark hero, lavender purple glow", "animation": "elegante"},
    "tesla": {"nome": "Tesla", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(10% 0.007 220)", "--muted": "oklch(37% 0.005 220)", "--border": "oklch(93% 0.0 0)", "--accent": "oklch(41% 0.128 224)"}, "font_heading": "Universal Sans Display", "font_body": "Universal Sans Text", "vibe": "electric automotive, radical subtraction, full-viewport photo", "animation": "elegante"},
    "tetris": {"nome": "Tetris", "tokens": {"--bg": "oklch(91% 0.025 225)", "--surface": "oklch(91% 0.025 225)", "--fg": "oklch(22% 0.089 225)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(13% 0.012 224)"}, "font_heading": "Bangers", "font_body": "Inter", "vibe": "block-game, playful colors, bold display, high-energy", "animation": "energetico"},
    "theverge": {"nome": "Theverge", "tokens": {"--bg": "oklch(7% 0.0 0)", "--surface": "oklch(18% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(58% 0.0 0)", "--border": "oklch(100% 0.0 0)", "--accent": "oklch(82% 0.153 166)"}, "font_heading": "Manuka", "font_body": "Manuka", "vibe": "tech editorial, acid-mint, rave-flyer, brutally heavy", "animation": "energetico"},
    "together_ai": {"nome": "Together Ai", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(38% 0.153 314)"}, "font_heading": "The Future", "font_body": "The Future", "vibe": "open-source AI, pastel-gradient, technical blueprint", "animation": "elegante"},
    "totality_festival": {"nome": "Totality Festival", "tokens": {"--bg": "oklch(8% 0.005 230)", "--surface": "oklch(12% 0.005 231)", "--fg": "oklch(89% 0.006 255)", "--muted": "oklch(78% 0.029 44)", "--border": "oklch(57% 0.027 44)", "--accent": "oklch(82% 0.2 51)"}, "font_heading": "Space Grotesk", "font_body": "Inter", "vibe": "festival, dark surfaces, gold primary, cyan secondary", "animation": "energetico"},
    "trading_terminal": {"nome": "Trading Terminal", "tokens": {"--bg": "oklch(5% 0.0 0)", "--surface": "oklch(8% 0.0 0)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(51% 0.0 0)", "--border": "oklch(16% 0.0 0)", "--accent": "oklch(64% 0.166 168)"}, "font_heading": "monospace", "font_body": "monospace", "vibe": "Bloomberg-style, dark-only, data-dense, cyan/coral signals", "animation": "elegante"},
    "uber": {"nome": "Uber", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(29% 0.0 0)", "--border": "oklch(0% 0.0 0)", "--accent": "oklch(0% 0.0 0)"}, "font_heading": "UberMove", "font_body": "UberMoveText", "vibe": "mobility, bold black-white, tight type, pill-shaped, urban", "animation": "energetico"},
    "urdu": {"nome": "Urdu", "tokens": {"--bg": "oklch(95% 0.008 42)", "--surface": "oklch(98% 0.002 60)", "--fg": "oklch(12% 0.014 220)", "--muted": "oklch(33% 0.024 218)", "--border": "oklch(91% 0.011 214)", "--accent": "oklch(29% 0.062 184)"}, "font_heading": "Noto Nastaliq Urdu", "font_body": "Noto Nastaliq Urdu", "vibe": "Urdu-first, RTL native, Nastaliq typography, bilingual", "animation": "elegante"},
    "vercel": {"nome": "Vercel", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(9% 0.0 0)", "--muted": "oklch(40% 0.0 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(40% 0.18 213)"}, "font_heading": "Geist Sans", "font_body": "Geist Sans", "vibe": "frontend deploy, black-white precision, shadow-as-border", "animation": "elegante"},
    "vibrant": {"nome": "Vibrant", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(16% 0.014 37)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(44% 0.09 254)"}, "font_heading": "Fascinate", "font_body": "Noto Sans", "vibe": "colorido playful, bold tipografia, dynamic visual energy", "animation": "energetico"},
    "vintage": {"nome": "Vintage", "tokens": {"--bg": "oklch(75% 0.0 0)", "--surface": "oklch(75% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(60% 0.0 0)", "--accent": "oklch(40% 0.1 180)"}, "font_heading": "Silkscreen", "font_body": "Inter", "vibe": "1950s-1990s nostalgia, skeuomorphic, grainy, pixel-style", "animation": "vibrante"},
    "vodafone": {"nome": "Vodafone", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(16% 0.005 210)", "--muted": "oklch(49% 0.0 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(19% 0.18 0)"}, "font_heading": "Vodafone Display", "font_body": "Vodafone Display", "vibe": "telecom global, monumental uppercase, Red chapter bands", "animation": "energetico"},
    "voltagent": {"nome": "Voltagent", "tokens": {"--bg": "oklch(2% 0.002 240)", "--surface": "oklch(6% 0.0 0)", "--fg": "oklch(95% 0.0 0)", "--muted": "oklch(58% 0.015 212)", "--border": "oklch(23% 0.003 15)", "--accent": "oklch(65% 0.17 160)"}, "font_heading": "system-ui", "font_body": "Inter", "vibe": "AI agent framework, void-black, emerald accent, terminal", "animation": "elegante"},
    "warm_editorial": {"nome": "Warm Editorial", "tokens": {"--bg": "oklch(97% 0.006 38)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(10% 0.004 36)", "--muted": "oklch(51% 0.013 26)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(40% 0.114 14)"}, "font_heading": "GT Sectra", "font_body": "Sohne", "vibe": "serif-led magazine, terracotta on warm off-white, editorial", "animation": "elegante"},
    "warp": {"nome": "Warp", "tokens": {"--bg": "oklch(10% 0.001 60)", "--surface": "oklch(21% 0.001 60)", "--fg": "oklch(98% 0.003 45)", "--muted": "oklch(52% 0.002 30)", "--border": "oklch(27% 0.0 0)", "--accent": "oklch(100% 0.0 0)"}, "font_heading": "Matter", "font_body": "Matter", "vibe": "modern terminal, warm dark campfire, monochromatic, nature", "animation": "elegante"},
    "webex": {"nome": "Webex", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(0% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(39% 0.149 210)"}, "font_heading": "Momentum", "font_body": "Momentum", "vibe": "collaboration, blue action system, multi-user spectrum", "animation": "elegante"},
    "webflow": {"nome": "Webflow", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(3% 0.0 0)", "--muted": "oklch(35% 0.0 0)", "--border": "oklch(85% 0.0 0)", "--accent": "oklch(39% 0.176 216)"}, "font_heading": "WF Visual Sans Variable", "font_body": "WF Visual Sans Variable", "vibe": "visual web builder, blue-accented, polished marketing", "animation": "vibrante"},
    "wechat": {"nome": "Wechat", "tokens": {"--bg": "oklch(93% 0.0 0)", "--surface": "oklch(97% 0.0 0)", "--fg": "oklch(10% 0.0 0)", "--muted": "oklch(53% 0.0 0)", "--border": "oklch(88% 0.0 0)", "--accent": "oklch(57% 0.146 149)"}, "font_heading": "PingFang SC", "font_body": "PingFang SC", "vibe": "super-app, simplicity, green brand, clean white, minimal", "animation": "elegante"},
    "wired": {"nome": "Wired", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(10% 0.0 0)", "--muted": "oklch(46% 0.0 0)", "--border": "oklch(91% 0.011 214)", "--accent": "oklch(41% 0.144 201)"}, "font_heading": "WiredDisplay", "font_body": "BreveText", "vibe": "tech magazine, paper-white broadsheet, mono kickers", "animation": "elegante"},
    "wise": {"nome": "Wise", "tokens": {"--bg": "oklch(100% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(6% 0.002 80)", "--muted": "oklch(53% 0.001 60)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(81% 0.094 96)"}, "font_heading": "Wise Sans", "font_body": "Inter", "vibe": "money transfer, lime-green accent, billboard bold, friendly", "animation": "energetico"},
    "x_ai": {"nome": "X Ai", "tokens": {"--bg": "oklch(13% 0.007 220)", "--surface": "oklch(18% 0.007 220)", "--fg": "oklch(100% 0.0 0)", "--muted": "oklch(53% 0.0 0)", "--border": "oklch(20% 0.0 0)", "--accent": "oklch(100% 0.0 0)"}, "font_heading": "GeistMono", "font_body": "universalSans", "vibe": "AI lab, stark monochrome, futuristic, monospace-as-luxury", "animation": "elegante"},
    "xiaohongshu": {"nome": "Xiaohongshu", "tokens": {"--bg": "oklch(96% 0.0 0)", "--surface": "oklch(100% 0.0 0)", "--fg": "oklch(10% 0.0 0)", "--muted": "oklch(60% 0.01 0)", "--border": "oklch(25% 0.02 250)", "--accent": "oklch(33% 0.172 352)"}, "font_heading": "PingFang SC", "font_body": "PingFang SC", "vibe": "lifestyle UGC, brand red, generous radius, content-first", "animation": "vibrante"},
    "zapier": {"nome": "Zapier", "tokens": {"--bg": "oklch(100% 0.003 45)", "--surface": "oklch(100% 0.003 45)", "--fg": "oklch(9% 0.009 0)", "--muted": "oklch(56% 0.012 48)", "--border": "oklch(75% 0.016 45)", "--accent": "oklch(43% 0.2 19)"}, "font_heading": "Degular Display", "font_body": "Inter", "vibe": "automation, warm orange, cream canvas, illustration-driven", "animation": "vibrante"},
}


# Dark mode: sobrepõe --bg, --surface, --fg, --muted, --border
DARK_OVERLAY = {
    "--bg":      "oklch(12% 0.010 260)",
    "--surface": "oklch(17% 0.012 260)",
    "--fg":      "oklch(93% 0.005 0)",
    "--muted":   "oklch(65% 0.010 260)",
    "--border":  "oklch(28% 0.015 260)",
}

# ─── MAPEAMENTO TIER → DIREÇÃO ─────────────────────────────────────────────────
TIER_DIRECAO = {
    "PREMIUM":  ["warm_editorial", "minimal"],
    "STANDARD": ["cafe", "clean"],
    "BASIC":    ["clean"],
}

# ─── PERFIS DE ANIMAÇÃO ────────────────────────────────────────────────────────
# Durações convergidas: Material 3 + IBM Carbon + Shopify Polaris
ANIMATION_PROFILES = {
    "elegante": {
        "instant":    "50ms",
        "feedback":   "150ms",
        "enter":      "300ms",
        "transition": "500ms",
        "easing_enter":  "cubic-bezier(0.0, 0.0, 0.2, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.4, 0.0, 0.2, 1)",
        "hero_type":  "fade-up",
        "card_type":  "fade-up",
        "stagger":    "80ms",
        "note": "fade-up lento, blur-in, sem bounce — clínica, advocacia, estética",
    },
    "vibrante": {
        "instant":    "50ms",
        "feedback":   "100ms",
        "enter":      "250ms",
        "transition": "400ms",
        "easing_enter":  "cubic-bezier(0.0, 0.0, 0.2, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.4, 0.0, 0.2, 1)",
        "hero_type":  "slide-up",
        "card_type":  "slide-left",
        "stagger":    "60ms",
        "note": "slide lateral, stagger agressivo — restaurante, pizzaria, lanchonete",
    },
    "energetico": {
        "instant":    "30ms",
        "feedback":   "80ms",
        "enter":      "200ms",
        "transition": "300ms",
        "easing_enter":  "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "easing_exit":   "cubic-bezier(0.4, 0.0, 1, 1)",
        "easing_std":    "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "hero_type":  "scale-in",
        "card_type":  "scale-in",
        "stagger":    "40ms",
        "note": "scale-in, bounce leve — academia, barbearia, crossfit",
    },
}

# ─── NICHOS ────────────────────────────────────────────────────────────────────
NICHOS: Dict[str, Dict] = {
    "barbearia":    {"dir": "luxury", "dir_variantes": ["editorial", "brutalism", "cal"],      "components": "galeria de cortes, lista de serviços, CTA agendamento WhatsApp, badge avaliação Google, horários", "tom": "direto, masculino, confiante — sem adjetivos vagos", "seo": "H1 com cidade, schema BarberShop, FAQ sobre cortes e preços", "anti": "pastéis, fontes cursivas, fotos de stock, contadores inventados"},
    "restaurante":  {"dir": "cafe", "dir_variantes": ["cafe", "starbucks", "warm_editorial"],      "components": "foto hero do prato principal, cardápio resumido, horários, localização embed, CTA reserva WhatsApp, avaliações reais", "tom": "apetitoso, acolhedor, local", "seo": "H1 com cidade e culinária, schema Restaurant + Menu, FAQ sobre reservas", "anti": "fotos de stock de comida, layout genérico de delivery"},
    "clinica":      {"dir": "clean", "dir_variantes": ["clean", "minimal", "friendly"], "components": "especialidades, equipe com CRM, CTA agendamento WhatsApp, convênios, localização", "tom": "profissional, empático, claro", "seo": "H1 com especialidade e cidade, schema MedicalBusiness, FAQ sobre consultas", "anti": "jargão médico, fotos de stock de médicos, promessas de cura"},
    "nutricionista": {"dir": "friendly", "dir_variantes": ["friendly", "warm_editorial", "clean"], "components": "especialidades, CTA agendamento WhatsApp, depoimentos, FAQ sobre consultas, localização", "tom": "acolhedor, empático, motivador — fala de saúde sem ser clínico", "seo": "H1 com especialidade e cidade, schema MedicalBusiness, FAQ sobre nutrição", "anti": "jargão médico, fotos de stock, promessas de emagrecimento rápido"},
    "academia":     {"dir": "bold", "dir_variantes": ["bold", "nike", "energetic"],      "components": "modalidades, planos e preços, CTA matrícula WhatsApp, fotos do espaço real, horários de aulas", "tom": "energético, motivador, direto", "seo": "H1 com modalidade e cidade, schema SportsActivityLocation, FAQ sobre planos", "anti": "atletas de stock, promessas em X dias, layout corporativo"},
    "pet_shop":     {"dir": "friendly", "dir_variantes": ["friendly", "duolingo", "lingo"],      "components": "serviços (banho, tosa, vet), galeria de pets, CTA WhatsApp, produtos, horários", "tom": "carinhoso, confiável — fala com o dono", "seo": "H1 com serviço e cidade, schema AnimalShelter, FAQ sobre serviços", "anti": "fotos de stock de animais, tom infantilizado"},
    "advocacia":    {"dir": "warm_editorial", "dir_variantes": ["warm_editorial", "editorial", "professional"],      "components": "áreas de atuação, perfil com OAB, CTA consulta WhatsApp, casos de sucesso, localização", "tom": "sério, competente, acessível — sem juridiquês", "seo": "H1 com área do direito e cidade, schema LegalService, FAQ sobre honorários", "anti": "promessas de ganhar causas, jargão no hero, stock de martelo"},
    "odontologia":  {"dir": "clean", "dir_variantes": ["clean", "minimal", "friendly"], "components": "tratamentos, antes/depois, CTA WhatsApp, convênios, equipe com CRO, localização", "tom": "profissional, acolhedor — reduz ansiedade", "seo": "H1 com tratamento e cidade, schema Dentist, FAQ sobre dor e procedimentos", "anti": "sorrisos perfeitos de stock, jargão técnico, promessas imediatas"},
    "estetica":     {"dir": "elegant", "dir_variantes": ["elegant", "refined", "warm_editorial"],      "components": "tratamentos, galeria de resultados reais, CTA WhatsApp, certificações, faixa de preço", "tom": "elegante, confiante — foco em autoestima", "seo": "H1 com tratamento e cidade, schema BeautySalon, FAQ sobre recuperação", "anti": "modelos perfeitas de stock, promessas milagrosas"},
    "pizzaria":     {"dir": "cafe", "dir_variantes": ["cafe", "vibrant", "starbucks"],      "components": "cardápio com fotos reais, sabores em destaque, CTA pedido WhatsApp, horários, área de entrega", "tom": "apetitoso, descontraído, local", "seo": "H1 com cidade e tipo, schema FoodEstablishment, FAQ sobre entrega", "anti": "fotos de stock de pizza, layout de app de delivery"},
    "farmacia":     {"dir": "clean", "dir_variantes": ["clean", "minimal", "simple"],   "components": "serviços (manipulação, delivery, plantão), produtos em destaque, CTA WhatsApp, horários, localização", "tom": "confiável, claro — saúde sem alarmismo", "seo": "H1 com cidade e diferencial, schema Pharmacy, FAQ sobre manipulação", "anti": "jargão farmacêutico, e-commerce genérico"},
    "imobiliaria":  {"dir": "airbnb", "dir_variantes": ["airbnb", "minimal", "warm_editorial"], "components": "tipos de imóveis, lançamentos, CTA WhatsApp com corretor, avaliações, área de atuação", "tom": "profissional, local — conhece o bairro", "seo": "H1 com cidade e tipo, schema RealEstateAgent, FAQ sobre financiamento", "anti": "casas perfeitas de stock, promessas de valorização"},
    "contabilidade":{"dir": "professional", "dir_variantes": ["professional", "clean", "corporate"],   "components": "serviços (MEI, PJ, IR), diferenciais, CTA WhatsApp, equipe com CRC, cases", "tom": "técnico mas acessível, parceiro", "seo": "H1 com serviço e cidade, schema AccountingService, FAQ sobre abertura de empresa", "anti": "jargão contábil no hero, calculadora de stock"},
    "escola":       {"dir": "duolingo", "dir_variantes": ["duolingo", "friendly", "lingo"],      "components": "níveis de ensino, diferenciais, CTA matrícula WhatsApp, fotos reais, depoimentos de pais", "tom": "acolhedor, inspirador — fala com os pais", "seo": "H1 com nível e cidade, schema School, FAQ sobre matrícula", "anti": "crianças felizes de stock, jargão pedagógico"},
    "salao_beleza": {"dir": "elegant", "dir_variantes": ["elegant", "refined", "warm_editorial"],      "components": "serviços com galeria, equipe com especialidades, CTA WhatsApp, produtos usados, horários", "tom": "elegante, pessoal — o salão tem personalidade", "seo": "H1 com serviço e cidade, schema HairSalon, FAQ sobre coloração", "anti": "modelos de stock, tom neutro sem personalidade"},
    "auto_pecas":   {"dir": "bold", "dir_variantes": ["bold", "brutalism", "clean"],   "components": "marcas atendidas, serviços, CTA WhatsApp, localização com referência, horários", "tom": "direto, técnico, confiável", "seo": "H1 com serviço e cidade, schema AutoRepair, FAQ sobre garantia", "anti": "e-commerce genérico, carros de stock, tom corporativo"},
}

ALIASES = {
    "restaurantes": "restaurante", "barbearias": "barbearia",
    "clinicas": "clinica", "clinica_medica": "clinica",
    "pet": "pet_shop", "pets": "pet_shop",
    "advogado": "advocacia", "advogados": "advocacia",
    "dentista": "odontologia", "dentistas": "odontologia",
    "estetica_facial": "estetica", "estetica_corporal": "estetica",
    "pizzarias": "pizzaria", "farmacias": "farmacia",
    "imoveis": "imobiliaria", "contabil": "contabilidade",
    "escolas": "escola", "salao": "salao_beleza",
    "auto_peca": "auto_pecas", "mecanica": "auto_pecas",
    "crossfit": "academia",
    "psicologia": "clinica", "lanchonete": "restaurante",
    "padaria": "restaurante",
}


def get_design_context(segmento: str, nome_negocio: str = "", tier: str = "STANDARD", dark_mode: bool = False) -> dict:
    """Retorna dict com tokens, tipografia e perfil de animação para o nicho.
    
    Retorna dict (não string) para que o ArquitetoMestre possa usar os valores
    diretamente sem parsing — e montar o :root CSS com precisão.
    """
    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)
    nicho = NICHOS.get(seg, {
        "dir": "minimal",
        "components": "hero com proposta de valor, serviços, CTA WhatsApp, localização, avaliações",
        "tom": "profissional, claro, local",
        "seo": "H1 com serviço e cidade, schema LocalBusiness",
        "anti": "fotos de stock genéricas, contadores inventados",
    })
    tier_upper = tier.upper()
    opcoes = TIER_DIRECAO.get(tier_upper, ["clean"])
    # Direção do nicho tem prioridade absoluta — tier só influencia nichos sem direção definida
    # (nichos com dir explícito sempre usam sua direção, independente do tier)
    # Variantes por nicho: sorteia entre direcoes compativeis para cada lead ser visualmente unico
    import hashlib as _hlib
    _variantes = nicho.get("dir_variantes", [nicho["dir"]])
    import random as _rnd
    if nome_negocio:
        _seed = int(_hlib.md5(nome_negocio.encode()).hexdigest(), 16)
        _rnd_local = _rnd.Random(_seed)
        dir_key = _rnd_local.choice(_variantes)
    else:
        dir_key = _rnd.choice(_variantes)
    if dir_key not in DIRECOES_VISUAIS:
        dir_key = nicho["dir"]
    d = DIRECOES_VISUAIS[dir_key]
    tokens = dict(d["tokens"])
    if dark_mode:
        tokens.update(DARK_OVERLAY)
    anim = ANIMATION_PROFILES[d["animation"]]
    return {
        "dir_key":       dir_key,
        "dir_nome":      d["nome"],
        "tokens":        tokens,
        "font_heading":  d["font_heading"],
        "font_body":     d["font_body"],
        "vibe":          d["vibe"],
        "animation":     d["animation"],
        "animation_profile": anim,
        "components":    nicho["components"],
        "tom":           nicho["tom"],
        "seo":           nicho["seo"],
        "anti":          nicho["anti"] + " | " + d.get("anti", ""),
        "segmento":      seg,
        "tier":          tier_upper,
    }



# ─────────────────────────────────────────────────────────────────────────────
# HERO STYLES — gradiente animado + layout por direção visual
# Cada direção tem um hero visualmente distinto. Zero invenção pelo LLM.
# ─────────────────────────────────────────────────────────────────────────────
HERO_STYLES = {
    "editorial": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(12% 0.015 260) 0%,"
            "oklch(18% 0.020 280) 50%,"
            "oklch(14% 0.012 240) 100%);"
            "animation:hero-shift 12s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-shift{"
            "0%{background-position:0% 50%}"
            "100%{background-position:100% 50%}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.55)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:contrast(1.05) saturate(0.9);",
    },
    "minimal": {
        "layout":   "hero-center",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(97% 0.005 260) 0%,"
            "oklch(93% 0.010 240) 60%,"
            "oklch(95% 0.008 220) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(255,255,255,0.0)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(0.85) brightness(0.95);",
    },
    "cafe": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(150deg,"
            "oklch(30% 0.040 50) 0%,"
            "oklch(22% 0.030 40) 50%,"
            "oklch(18% 0.020 35) 100%);"
            "background-size:200% 200%;"
            "animation:hero-warm 10s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-warm{"
            "0%{background-position:0% 0%}"
            "100%{background-position:100% 100%}"
            "}"
        ),
        "overlay":  "rgba(20,10,5,0.50)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(1.1) brightness(0.85);",
    },
    "clean": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(120deg,"
            "oklch(14% 0.020 220) 0%,"
            "oklch(20% 0.025 230) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.45)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:contrast(1.1) saturate(0.8);",
    },
    "brutalism": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:oklch(98% 0.000 0);"
            "position:relative;"
        ),
        "keyframes": (
            "@keyframes hero-noise{"
            "0%,100%{opacity:0.03}"
            "50%{opacity:0.06}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.0)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:grayscale(0.3) contrast(1.15);",
        "noise": True,  # adiciona camada de ruído CSS
    },
    "bold": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(5% 0.01 220) 0%,"
            "oklch(12% 0.02 240) 50%,"
            "oklch(8% 0.015 200) 100%);"
            "background-size:200% 200%;"
            "animation:hero-bold 8s ease-in-out infinite alternate;"
        ),
        "keyframes": (
            "@keyframes hero-bold{"
            "0%{background-position:0% 50%}"
            "100%{background-position:100% 50%}"
            "}"
        ),
        "overlay":  "rgba(0,0,0,0.50)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.2) brightness(0.75) saturate(1.1);",
    },
    "nike": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:oklch(4% 0.0 0);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.60)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.3) brightness(0.7) saturate(0.9);",
    },
    "energetic": {
        "layout":   "hero-fullscreen",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(8% 0.02 250) 0%,"
            "oklch(15% 0.04 200) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.45)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:contrast(1.15) brightness(0.8) saturate(1.2);",
    },
    "friendly": {
        "layout":   "hero-center",
        "gradient": (
            "background:linear-gradient(160deg,"
            "oklch(97% 0.01 350) 0%,"
            "oklch(95% 0.015 340) 50%,"
            "oklch(98% 0.005 0) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(0,0,0,0.0)",
        "text_pos": "center",
        "img_style": "object-fit:cover;filter:saturate(0.9) brightness(1.0);border-radius:16px;",
    },
    "warm_editorial": {
        "layout":   "hero-split",
        "gradient": (
            "background:linear-gradient(135deg,"
            "oklch(25% 0.03 50) 0%,"
            "oklch(18% 0.02 40) 100%);"
        ),
        "keyframes": "",
        "overlay":  "rgba(20,10,5,0.45)",
        "text_pos": "left",
        "img_style": "object-fit:cover;filter:saturate(1.05) brightness(0.9);",
    },
}


def get_hero_style(dir_key: str) -> dict:
    """Retorna o estilo de hero para a direção visual do nicho."""
    if dir_key in HERO_STYLES:
        return HERO_STYLES[dir_key]
    # Fallback inteligente baseado na direcao
    d = DIRECOES_VISUAIS.get(dir_key, {})
    tokens = d.get("tokens", {})
    bg = tokens.get("--bg", "oklch(100% 0.0 0)")
    # Se bg eh escuro (lightness < 30%), usar hero dark
    import re as _re
    m = _re.search(r"oklch\((\d+)%", bg)
    lightness = int(m.group(1)) if m else 100
    if lightness < 30:
        return {
            "layout": "hero-fullscreen",
            "gradient": "background:" + bg + ";",
            "keyframes": "",
            "overlay": "rgba(0,0,0,0.40)",
            "text_pos": "center",
            "img_style": "object-fit:cover;filter:contrast(1.1) brightness(0.85);",
        }
    else:
        return {
            "layout": "hero-center",
            "gradient": "background:" + bg + ";",
            "keyframes": "",
            "overlay": "rgba(0,0,0,0.0)",
            "text_pos": "center",
            "img_style": "object-fit:cover;filter:saturate(0.9) brightness(0.95);",
        }


def get_hero_css(dir_key: str) -> str:
    """Retorna o CSS completo do hero (keyframes + gradient) para injetar no wrapper."""
    style = get_hero_style(dir_key)
    css = ""
    if style.get("keyframes"):
        css += style["keyframes"] + "\n"
    css += f"#hero{{min-height:100vh;{style['gradient']}}}" + "\n"
    if style.get("noise"):
        css += (
            "#hero::after{content:'';position:absolute;inset:0;pointer-events:none;"
            "background:repeating-linear-gradient(0deg,transparent,transparent 2px,"
            "rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px);"
            "opacity:0.04;animation:hero-noise 3s ease-in-out infinite;}" + "\n"
        )
    return css


def get_design_context_prompt(segmento: str, nome_negocio: str = "", tier: str = "STANDARD", dark_mode: bool = False) -> str:
    """Versão string para injetar em prompts LLM."""
    ctx = get_design_context(segmento, nome_negocio, tier, dark_mode)
    tokens_str = "\n".join(f"  {k}: {v}" for k, v in ctx["tokens"].items())
    anim = ctx["animation_profile"]
    _posture = ctx.get("posture", [])
    posture_fmt = chr(10).join("  - " + p for p in _posture) if _posture else "  padrao"
    result = f"""
=== DESIGN SYSTEM DO NICHO — SIGA OBRIGATORIAMENTE ===
SEGMENTO: {ctx['segmento'].upper()} | TIER: {ctx['tier']} | DIREÇÃO: {ctx['dir_nome']}

CSS TOKENS (6 universais — use EXATAMENTE estes valores no :root):
{tokens_str}

TIPOGRAFIA:
  heading: {ctx['font_heading']}
  body:    {ctx['font_body']}

VIBE: {ctx['vibe']}

PERFIL DE ANIMAÇÃO: {ctx['animation']}
  enter:      {anim['enter']} | feedback: {anim['feedback']}
  easing_std: {anim['easing_std']}
  hero_type:  {anim['hero_type']} | card_type: {anim['card_type']}
  stagger:    {anim['stagger']}
  OBRIGATÓRIO: @media (prefers-reduced-motion: reduce) substitui translate/scale por opacity

COMPONENTES OBRIGATÓRIOS:
  {ctx['components']}

TOM DE VOZ: {ctx['tom']}

SEO LOCAL: {ctx['seo']}

ANTI-PATTERNS (proibido neste nicho):
  {ctx['anti']}

POSTURA VISUAL (cues de layout):
{posture_fmt}
=== FIM DESIGN SYSTEM ===
"""
    return result
