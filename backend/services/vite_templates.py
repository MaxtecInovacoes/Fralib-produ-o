"""Templates de componentes React para o Vite/React renderer do FraLib Builder.

Este modulo contem todos os templates de componentes React usados como fallback
quando a geracao por LLM falha ou como base para normalizacao.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _safe_project_path(path: str) -> str:
    """Valida e normaliza um caminho de arquivo do projeto."""
    from pathlib import PurePosixPath
    clean = str(path or "").strip().replace("\\", "/").lstrip("/")
    pure = PurePosixPath(clean)
    if not clean or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"caminho invalido no projeto Vite: {path!r}")
    allowed_prefixes = ("src/", "public/", "assets/")
    allowed_roots = {
        "package.json",
        "index.html",
        "vite.config.ts",
        "tsconfig.json",
        "metadata.json",
        "README.md",
        ".gitignore",
        ".env.example",
    }
    if clean not in allowed_roots and not clean.startswith(allowed_prefixes):
        raise ValueError(f"arquivo fora do contrato Vite: {clean}")
    if clean.startswith(("src/", "public/", "assets/")) and not re.search(
        r"\.(tsx|ts|css|json|svg|txt|md)$", clean
    ):
        raise ValueError(f"extensao nao permitida no projeto Vite: {clean}")
    return clean


def _facts_business(facts: dict[str, Any]) -> dict[str, Any]:
    return facts.get("business") if isinstance(facts.get("business"), dict) else {}


def _facts_publication_url(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in ("canonical_url", "site_url", "canonical", "url_site"):
            url = str(container.get(key) or "").strip()
            if url.startswith(("http://", "https://")):
                return url
    return ""


def _facts_theme_color(facts: dict[str, Any]) -> str:
    for container_name in ("visual_dna", "visual_direction", "design"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        tokens = container.get("tokens") or container.get("color_palette") or {}
        if not isinstance(tokens, dict):
            continue
        for key in ("--primary", "primary", "--accent", "accent"):
            color = str(tokens.get(key) or "").strip()
            if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                return color
    return "#111827"


def _facts_local_keywords(facts: dict[str, Any]) -> list[str]:
    business = _facts_business(facts)
    seo = facts.get("seo") if isinstance(facts.get("seo"), dict) else {}
    candidates = seo.get("primary_terms") or facts.get("seo_keywords") or business.get("seo_keywords") or []
    if not isinstance(candidates, list):
        candidates = re.split(r"[,;\n]", str(candidates or ""))
    keywords: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        term = re.sub(r"\s+", " ", str(item or "")).strip(" ,.;:-")
        key = term.lower()
        if not term or key in seen:
            continue
        seen.add(key)
        keywords.append(term)
    return keywords[:10]


def _facts_meta_description(facts: dict[str, Any]) -> str:
    business = _facts_business(facts)
    name = str(business.get("name") or business.get("business_name") or "").strip()
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or "negócio local").strip()
    subniche = str(business.get("subniche") or facts.get("subniche") or "").strip()
    phone = str(business.get("whatsapp") or business.get("phone") or "").strip()
    rating = str(business.get("rating") or "").strip()
    summary = subniche or segment
    parts = [name, summary]
    if city:
        parts.append(f"em {city}")
    description = " ".join(part for part in parts if part).strip()
    suffix = []
    if rating:
        suffix.append(f"avaliação {rating}")
    if phone:
        suffix.append(f"contato {phone}")
    final = description
    if suffix:
        final += ". " + " | ".join(suffix)
    return final[:180].strip(" .") + "."


def _facts_og_image(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business", "media"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        image = str(container.get("og_image") or "").strip()
        if image.startswith(("http://", "https://")):
            return image
    for source in (facts.get("photos"), _facts_business(facts).get("photos")):
        if isinstance(source, list):
            for item in source:
                image = str(item or "").strip()
                if image.startswith(("http://", "https://")):
                    return image
    return ""


def _facts_json_ld(facts: dict[str, Any]) -> str:
    business = _facts_business(facts)
    site_url = _facts_publication_url(facts)
    image = _facts_og_image(facts)
    data = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": business.get("name") or business.get("business_name") or "",
        "url": site_url,
        "image": image,
        "telephone": business.get("phone") or business.get("whatsapp") or "",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": business.get("address") or business.get("endereco") or "",
            "addressLocality": business.get("city") or business.get("cidade") or facts.get("cidade") or "",
            "addressCountry": "BR",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": business.get("rating") or "",
            "reviewCount": business.get("total_avaliacoes") or business.get("reviews_count") or "",
        },
    }
    cleaned = {key: value for key, value in data.items() if value not in ("", None, {}, [])}
    if isinstance(cleaned.get("aggregateRating"), dict):
        agg = {key: value for key, value in cleaned["aggregateRating"].items() if value not in ("", None)}
        if len(agg) <= 1:
            cleaned.pop("aggregateRating", None)
        else:
            cleaned["aggregateRating"] = agg
    return json.dumps(cleaned, ensure_ascii=False)


def _meta_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _normalize_text(value: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).lower().strip()


# ---------------------------------------------------------------------------
# Helpers de dados visuais
# ---------------------------------------------------------------------------

def _visual_business_payload(facts: dict[str, Any]) -> dict[str, str]:
    """Extrai dados do negocio para uso nos templates de componentes."""
    business = _facts_business(facts)
    name = str(business.get("name") or business.get("business_name") or "Negocio local").strip()
    segment = str(business.get("segment") or business.get("segmento") or facts.get("segmento") or "Atendimento local").strip()
    subniche = str(business.get("subniche") or facts.get("subniche") or segment).strip()
    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    address = str(business.get("address") or business.get("endereco") or "").strip()
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    rating = str(business.get("rating") or "5.0").strip().replace(",", ".")
    count = str(business.get("total_avaliacoes") or business.get("reviews_count") or "").strip()
    maps = str(business.get("maps_url") or business.get("map_url") or "").strip()
    return {
        "name": name,
        "segment": segment,
        "subniche": subniche,
        "city": city,
        "address": address,
        "phone": phone,
        "rating": rating,
        "count": count,
        "maps": maps,
    }


def _visual_media_urls(facts: dict[str, Any]) -> list[str]:
    """Retorna URLs de imagens para uso nos templates de componentes."""
    business = _facts_business(facts)
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    urls: list[str] = []
    for source in (media.get("photos"), business.get("photos"), facts.get("photos")):
        if isinstance(source, list):
            urls.extend(str(item or "").strip() for item in source if str(item or "").strip())
    if not urls:
        segment = _normalize_text(str(business.get("segment") or business.get("segmento") or facts.get("segmento") or ""))
        if "nutric" in segment:
            urls = [
                "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1600&q=82",
                "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1400&q=82",
                "https://images.unsplash.com/photo-1543352634-a1c51d9f1fa7?auto=format&fit=crop&w=1400&q=82",
            ]
        elif any(token in segment for token in ("academia", "fitness", "treino")):
            urls = [
                "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1600&q=82",
                "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=1400&q=82",
                "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1400&q=82",
            ]
        else:
            urls = [
                "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1600&q=82",
                "https://images.unsplash.com/photo-1556761175-b413da4baf72?auto=format&fit=crop&w=1400&q=82",
                "https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=1400&q=82",
            ]
    return list(dict.fromkeys(urls))[:5]


# ---------------------------------------------------------------------------
# Templates de infraestrutura (index.html, vite.config.ts, tsconfig.json)
# ---------------------------------------------------------------------------

def vite_template_index_html(facts: dict[str, Any]) -> str:
    """Template do index.html base."""
    business = _facts_business(facts)
    title = str(business.get("name") or "FraLib Builder Site")
    canonical = _facts_publication_url(facts)
    description = _facts_meta_description(facts)
    keywords = ", ".join(_facts_local_keywords(facts))
    og_image = _facts_og_image(facts)
    theme_color = _facts_theme_color(facts)
    json_ld = _facts_json_ld(facts)
    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{_meta_escape(title)}</title>
    <meta name="description" content="{_meta_escape(description)}" />
    <meta name="keywords" content="{_meta_escape(keywords)}" />
    <meta name="theme-color" content="{_meta_escape(theme_color)}" />
    <link rel="canonical" href="{_meta_escape(canonical)}" />
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="pt_BR" />
    <meta property="og:title" content="{_meta_escape(title)}" />
    <meta property="og:description" content="{_meta_escape(description)}" />
    <meta property="og:url" content="{_meta_escape(canonical)}" />
    <meta property="og:image" content="{_meta_escape(og_image)}" />
    <meta property="og:site_name" content="{_meta_escape(title)}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{_meta_escape(title)}" />
    <meta name="twitter:description" content="{_meta_escape(description)}" />
    <meta name="twitter:image" content="{_meta_escape(og_image)}" />
    <script type="application/ld+json">{json_ld}</script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""


def vite_template_vite_config() -> str:
    """Template do vite.config.ts base."""
    return """import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  build: {
    target: 'es2020',
    sourcemap: false,
  },
});
"""


def vite_template_tsconfig() -> str:
    """Template do tsconfig.json base."""
    return json.dumps(
        {
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["DOM", "DOM.Iterable", "ES2020"],
                "allowJs": False,
                "skipLibCheck": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "noImplicitAny": False,
                "forceConsistentCasingInFileNames": True,
                "module": "ESNext",
                "moduleResolution": "Node",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
            },
            "include": ["src"],
            "references": [],
        },
        ensure_ascii=False,
        indent=2,
    )


def vite_template_jsx_fallback_types() -> str:
    """Template de fallback para JSX types quando @types/react falha."""
    return """declare module 'react' {
  const React: any;
  export default React;
  export const StrictMode: any;
  export type FC<P = any> = (props: P) => any;
  export type ReactNode = any;
  export type MouseEvent<T = any> = any;
  export type ChangeEvent<T = any> = any;
  export type FormEvent<T = any> = any;
  export type FocusEvent<T = any> = any;
  export type KeyboardEvent<T = any> = any;
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps?: any[]): T;
  export function useState<T>(initial: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void];
  export function useRef<T>(initial: T): { current: T };
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps?: any[]): T;
}

declare module 'react-dom/client' {
  export function createRoot(element: Element | DocumentFragment): { render(children: any): void };
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Templates de arquivos TypeScript/React core
# ---------------------------------------------------------------------------

def vite_template_main_tsx() -> str:
    """Template do src/main.tsx base."""
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""


def vite_template_main_tsx_with_factual_contract(content: str) -> str:
    """Template main.tsx com FactualMotionContract injetado."""
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import { FactualMotionContract } from './components/FactualMotionContract';

createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
    <FactualMotionContract />
  </React.StrictMode>
);
"""


def vite_template_app_tsx() -> str:
    """Template do src/App.tsx base."""
    return """import Index from './pages/Index';
import { LgpdBanner } from './components/LgpdBanner';

export default function App() {
  return (
    <>
      <Index />
      <LgpdBanner />
    </>
  );
}
"""


def vite_template_types_ts() -> str:
    """Template do src/types.ts base."""
    return """export type NavItem = {
  label: string;
  href: string;
};

export type EditorialImage = {
  src: string;
  alt: string;
  caption?: string;
};
"""


def vite_template_index_css() -> str:
    """Template do src/index.css base com Tailwind v4."""
    return """@import "tailwindcss";
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

@layer base {
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; background: #050505; }
  body {
    margin: 0;
    min-width: 320px;
    min-height: 100vh;
    font-family: Inter, system-ui, sans-serif;
    color: #f7f3ea;
    background: #050505;
    text-rendering: geometricPrecision;
  }
  h1, h2, h3 { text-wrap: balance; }
  p { text-wrap: pretty; }
  img { max-width: 100%; display: block; }
  a { color: inherit; text-decoration: none; }
  button, a { -webkit-tap-highlight-color: transparent; }
  ::selection { background: rgba(216, 184, 121, 0.35); color: #fffaf0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
"""


# ---------------------------------------------------------------------------
# Templates de componentes React
# ---------------------------------------------------------------------------

def vite_template_card_ui() -> str:
    """Template do componente Card UI basico."""
    return """import * as React from 'react';

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: DivProps) {
  return <div className={`rounded-2xl border border-zinc-200 bg-white shadow-sm ${className}`.trim()} {...props} />;
}

export function CardHeader({ className = '', ...props }: DivProps) {
  return <div className={`p-6 ${className}`.trim()} {...props} />;
}

export function CardTitle({ className = '', ...props }: DivProps) {
  return <h3 className={`text-lg font-semibold text-zinc-950 ${className}`.trim()} {...props} />;
}

export function CardDescription({ className = '', ...props }: DivProps) {
  return <p className={`text-sm text-zinc-600 ${className}`.trim()} {...props} />;
}

export function CardContent({ className = '', ...props }: DivProps) {
  return <div className={`px-6 pb-6 ${className}`.trim()} {...props} />;
}
"""


def vite_template_lgpd_banner() -> str:
    """Template do componente LgpdBanner (banner de consentimento LGPD)."""
    return """import { useEffect, useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { motion } from 'motion/react';

const CONSENT_KEY = 'fralib_lgpd_consent_v1';

export function LgpdBanner() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    try {
      if (localStorage.getItem(CONSENT_KEY) === '1') setVisible(false);
    } catch {
      // Storage can be unavailable in privacy-restricted browsers.
    }
  }, []);

  const accept = () => {
    try {
      localStorage.setItem(CONSENT_KEY, '1');
    } catch {
      // Consent still applies to the current page when storage is unavailable.
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <motion.div
      data-lgpd-banner
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed inset-x-4 bottom-4 z-[9999] mx-auto grid max-w-3xl grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border border-white/15 bg-zinc-950/94 p-4 text-white shadow-2xl backdrop-blur"
      role="dialog"
      aria-label="Aviso de privacidade"
    >
      <ShieldCheck className="h-5 w-5 text-emerald-300" />
      <p className="text-sm leading-5 text-zinc-200">Tratamos dados de contato apenas para atendimento, segurança e melhoria da experiência.</p>
      <div className="flex items-center gap-2">
        <button type="button" data-lgpd-accept onClick={accept} className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-semibold text-zinc-950">
          Aceitar
        </button>
        <button type="button" aria-label="Fechar aviso de privacidade" onClick={accept} className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-white">
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

export default LgpdBanner;
"""


def vite_template_navbar(facts: dict[str, Any]) -> str:
    """Template do componente Navbar."""
    business = _facts_business(facts)
    name = str(business.get("name") or "FraLib").strip()
    short_name = name.split(" - ")[0].strip() or name
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = phone or "Contato"
    phone_digits = re.sub(r"\D+", "", phone or "")
    phone_href = f"tel:+{phone_digits}" if phone_digits else "#contato"
    name_js = json.dumps(short_name, ensure_ascii=False)
    phone_label_js = json.dumps(phone_label, ensure_ascii=False)
    phone_href_js = json.dumps(phone_href, ensure_ascii=False)
    return f"""import {{ useEffect, useState }} from 'react';
import {{ motion }} from 'motion/react';
import {{ Menu, X, Phone }} from 'lucide-react';

const brand = {name_js};
const phoneLabel = {phone_label_js};
const phoneHref = {phone_href_js};
const links = [
  {{ href: '#sobre', label: 'Sobre' }},
  {{ href: '#servicos', label: 'Serviços' }},
  {{ href: '#galeria', label: 'Galeria' }},
  {{ href: '#avaliacoes', label: 'Avaliações' }},
  {{ href: '#contato', label: 'Contato' }},
];

export function Navbar({{ onOpen }}: {{ onOpen: () => void }}) {{
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {{
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener('scroll', onScroll, {{ passive: true }});
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);

  useEffect(() => {{
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {{
      document.body.style.overflow = '';
    }};
  }}, [open]);

  return (
    <motion.header
      initial={{{{ y: -16, opacity: 0 }}}}
      animate={{{{ y: 0, opacity: 1 }}}}
      transition={{{{ duration: 0.35 }}}}
      className={{`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${{scrolled ? 'border-b border-zinc-200/70 bg-white/88 shadow-sm backdrop-blur-md' : 'bg-transparent'}}`}}
    >
      <nav aria-label="Navegação principal" className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 md:h-20 md:px-8">
        <a href="#topo" className="min-w-0">
          <span className="block truncate text-base font-semibold tracking-tight text-zinc-950 md:text-lg">{{brand}}</span>
        </a>
        <ul className="hidden items-center gap-1 md:flex">
          {{links.map((link) => (
            <li key={{link.href}}>
              <a href={{link.href}} className="rounded-full px-3 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-950/5 hover:text-zinc-950">
                {{link.label}}
              </a>
            </li>
          ))}}
        </ul>
        <div className="hidden items-center gap-2 md:flex">
          <a href={{phoneHref}} className="inline-flex items-center gap-2 rounded-full border border-zinc-300 bg-white/70 px-3 py-2 text-sm font-medium text-zinc-800">
            <Phone className="h-3.5 w-3.5" aria-hidden="true" />
            {{phoneLabel}}
          </a>
          <button type="button" onClick={{onOpen}} className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-semibold text-white">
            Agendar
          </button>
        </div>
        <button
          type="button"
          aria-label={{open ? 'Fechar menu' : 'Abrir menu'}}
          aria-expanded={{open}}
          onClick={{() => setOpen((value) => !value)}}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-950 md:hidden"
        >
          {{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}}
        </button>
      </nav>
      {{open && (
        <div className="border-t border-zinc-200/70 bg-white/95 px-4 py-4 backdrop-blur md:hidden">
          <ul className="space-y-1">
            {{links.map((link) => (
              <li key={{link.href}}>
                <a href={{link.href}} onClick={{() => setOpen(false)}} className="block rounded-xl px-3 py-3 text-base font-medium text-zinc-800 hover:bg-zinc-100">
                  {{link.label}}
                </a>
              </li>
            ))}}
            <li className="pt-2">
              <button type="button" onClick={{() => {{ setOpen(false); onOpen(); }}}} className="w-full rounded-xl bg-zinc-950 px-3 py-3 text-base font-semibold text-white">
                Agendar consulta
              </button>
            </li>
          </ul>
        </div>
      )}}
    </motion.header>
  );
}}

export default Navbar;
"""


def vite_template_hero_section(facts: dict[str, Any]) -> str:
    """Template do componente HeroSection."""
    data = _visual_business_payload(facts)
    images = _visual_media_urls(facts)
    image = json.dumps(images[0], ensure_ascii=False) if images else json.dumps("", ensure_ascii=False)
    data_js = json.dumps(data, ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", data["phone"])
    whatsapp = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    return f"""import {{ useEffect }} from 'react';
import {{ ArrowRight, MapPin, MessageCircle, Star }} from 'lucide-react';
import {{ gsap }} from 'gsap';
import {{ ScrollTrigger }} from 'gsap/ScrollTrigger';
import {{ motion }} from 'motion/react';

const business = {data_js};
const heroImage = {image};
const whatsappHref = {whatsapp};

export function HeroSection({{ onOpen }}: {{ onOpen: () => void }}) {{
  useEffect(() => {{
    gsap.registerPlugin(ScrollTrigger);
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.8, ease: 'power3.out' }});
    gsap.to('[data-hero-image]', {{
      yPercent: 8,
      ease: 'none',
      scrollTrigger: {{ trigger: '#topo', start: 'top top', end: 'bottom top', scrub: true }},
    }});
  }}, []);

  return (
    <section id="topo" className="relative min-h-[92svh] overflow-hidden bg-[#071611] text-white">
      <img data-hero-image src={{heroImage}} alt={{`${{business.segment}} em ${{business.city}}`}} className="absolute inset-0 h-[108%] w-full object-cover opacity-70" loading="eager" decoding="async" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(7,22,17,.96)_0%,rgba(7,22,17,.76)_38%,rgba(7,22,17,.18)_100%)]" />
      <div className="relative mx-auto flex min-h-[92svh] max-w-7xl flex-col justify-end px-5 pb-14 pt-28 md:px-8 md:pb-20">
        <motion.div data-hero-copy initial={{{{ opacity: 0, y: 24 }}}} animate={{{{ opacity: 1, y: 0 }}}} transition={{{{ duration: 0.7 }}}} className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300">{{business.subniche}} em {{business.city}}</p>
          <h1 className="mt-5 text-[clamp(2.35rem,7vw,4.7rem)] font-semibold leading-[0.95] tracking-tight text-white">
            {{business.name}}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-100 md:text-lg">
            Atendimento local com dados confirmados, contato direto e uma apresentação clara para quem precisa decidir rápido.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a href={{whatsappHref}} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-6 py-3.5 text-sm font-semibold text-[#071611]">
              <MessageCircle className="h-4 w-4" /> WhatsApp
            </a>
            <button type="button" onClick={{onOpen}} className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/8 px-6 py-3.5 text-sm font-semibold text-white backdrop-blur">
              Agendar <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-6 flex flex-wrap gap-3 text-sm text-zinc-100">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/20 px-4 py-2"><MapPin className="h-4 w-4 text-emerald-300" />{{business.city}}</span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-black/20 px-4 py-2"><Star className="h-4 w-4 text-amber-300" />{{business.rating}} {{business.count ? `(${{business.count}})` : ''}}</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default HeroSection;
"""


def vite_template_about_section(facts: dict[str, Any]) -> str:
    """Template do componente AboutSection."""
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ Award, CheckCircle2, MapPin }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {data};

export function AboutSection() {{
  return (
    <section id="sobre" className="bg-[#f7f3ea] px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1fr_0.85fr] lg:items-end">
        <motion.div initial={{{{ opacity: 0, y: 18 }}}} whileInView={{{{ opacity: 1, y: 0 }}}} viewport={{{{ once: true, amount: 0.3 }}}>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Sobre</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight md:text-5xl">
            {{business.segment}} com presença local em {{business.city}}.
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-700">
            Página construída com dados confirmados do lead: nome, cidade, contato, endereço, avaliação e contexto de atendimento. O foco é deixar claro o que a empresa faz e como o visitante deve avançar.
          </p>
        </motion.div>
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          {{[
            [Award, 'Prova local', `${{business.rating}} de avaliação`],
            [CheckCircle2, 'Dados confirmados', 'Sem placeholder ou texto genérico'],
            [MapPin, 'Atendimento', business.city],
          ].map(([Icon, title, text]) => (
            <article key={{title}} className="rounded-[28px] border border-emerald-900/10 bg-white p-5 shadow-sm">
              <Icon className="h-5 w-5 text-emerald-700" />
              <h3 className="mt-4 text-base font-semibold text-zinc-950">{{title}}</h3>
              <p className="mt-2 text-sm leading-6 text-zinc-600">{{text}}</p>
            </article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default AboutSection;
"""


def vite_template_gallery_section(facts: dict[str, Any]) -> str:
    """Template do componente GallerySection."""
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    images = json.dumps(_visual_media_urls(facts), ensure_ascii=False)
    return f"""import {{ motion }} from 'motion/react';

const business = {data};
const images = {images};
const labels = ['Ambiente e contexto', 'Serviço principal', 'Rotina do cliente', 'Prova visual', 'Atendimento local'];

export function GallerySection() {{
  return (
    <section id="galeria" className="bg-[#ede8dd] px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Galeria</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Visual relacionado ao nicho, sem imagem solta.</h2>
          <p className="mt-4 text-base leading-7 text-zinc-700">Imagens editoriais coerentes com {{business.segment}} e com a intenção local da página.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {{images.map((src, index) => (
            <motion.figure
              key={{src}}
              initial={{{{ opacity: 0, y: 18 }}}}
              whileInView={{{{ opacity: 1, y: 0 }}}}
              viewport={{{{ once: true, amount: 0.2 }}}}
              transition={{{{ delay: index * 0.04 }}}}
              className={{`group relative overflow-hidden rounded-[28px] bg-zinc-900 shadow-sm ${{index === 0 ? 'md:col-span-2 md:row-span-2' : ''}}`}}
            >
              <img src={{src}} alt={{`${{business.segment}} - ${{labels[index] || 'imagem'}}`}} className="h-full min-h-64 w-full object-cover transition duration-700 group-hover:scale-105" loading={{index === 0 ? 'eager' : 'lazy'}} decoding="async" />
              <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-5 text-sm font-semibold text-white">{{labels[index] || business.segment}}</figcaption>
            </motion.figure>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default GallerySection;
"""


def vite_template_services_section(facts: dict[str, Any]) -> str:
    """Template do componente ServicesSection."""
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ ClipboardCheck, MessageCircle, Route, Sparkles }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {data};
const services = [
  ['Diagnóstico inicial', 'Leitura rápida do contexto do cliente antes do primeiro contato.', ClipboardCheck],
  ['Atendimento orientado', `Conversa direta para entender necessidade em ${{business.city}}.`, MessageCircle],
  ['Plano de ação', 'Próximos passos claros, sem promessa inventada ou dado sem confirmação.', Route],
  ['Experiência visual', 'Página com imagens, motion e CTA pensados para conversão local.', Sparkles],
];

export function ServicesSection() {{
  return (
    <section id="servicos" className="bg-white px-5 py-18 text-zinc-950 md:px-8 md:py-24">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Serviços</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight md:text-5xl">O que o visitante entende em poucos segundos.</h2>
          </div>
          <p className="max-w-sm text-sm leading-6 text-zinc-600">Cada bloco é curto para evitar texto truncado e manter leitura limpa no mobile.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {{services.map(([title, text, Icon], index) => (
            <motion.article key={{title}} initial={{{{ opacity: 0, y: 16 }}}} whileInView={{{{ opacity: 1, y: 0 }}}} viewport={{{{ once: true, amount: 0.25 }}}} transition={{{{ delay: index * 0.04 }}}} className="min-h-48 rounded-[28px] border border-zinc-200 bg-[#f7f3ea] p-6">
              <Icon className="h-5 w-5 text-emerald-700" />
              <h3 className="mt-5 text-lg font-semibold text-zinc-950">{{title}}</h3>
              <p className="mt-3 text-sm leading-6 text-zinc-600">{{text}}</p>
            </motion.article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default ServicesSection;
"""


def vite_template_lifestyle_section(facts: dict[str, Any]) -> str:
    """Template do componente LifestyleSection."""
    data = json.dumps(_visual_business_payload(facts), ensure_ascii=False)
    return f"""import {{ motion }} from 'motion/react';

const business = {data};

export function LifestyleSection() {{
  return (
    <section id="experiencia" className="bg-[#071611] px-5 py-18 text-white md:px-8 md:py-24">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300">Experiência</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Movimento, profundidade e leitura sem ruído.</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {{['Scroll com intenção', 'Prova clara', 'CTA sempre objetivo'].map((title, index) => (
            <motion.article key={{title}} initial={{{{ opacity: 0, x: 20 }}}} whileInView={{{{ opacity: 1, x: 0 }}}} viewport={{{{ once: true, amount: 0.3 }}}} transition={{{{ delay: index * 0.06 }}}} className="rounded-[28px] border border-white/10 bg-white/[0.04] p-6">
              <span className="text-sm font-semibold text-emerald-300">0{{index + 1}}</span>
              <h3 className="mt-5 text-lg font-semibold text-white">{{title}}</h3>
              <p className="mt-3 text-sm leading-6 text-zinc-300">Contrato visual aplicado para {{business.segment}} em {{business.city}}.</p>
            </motion.article>
          ))}}
        </div>
      </div>
    </section>
  );
}}

export default LifestyleSection;
"""


def vite_template_reviews_section(facts: dict[str, Any]) -> str:
    """Template do componente ReviewsSection."""
    business = _facts_business(facts)
    reviews = business.get("reviews")
    if not isinstance(reviews, list):
        reviews = []
    cards: list[dict[str, str]] = []
    for item in reviews[:4]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("texto") or item.get("text") or "").strip()
        author = str(item.get("autor") or item.get("author") or "Avaliação local").strip()
        if text:
            cards.append({"quote": text[:180], "author": author[:48]})
    if not cards:
        cards = [
            {"quote": "Atendimento elogiado pela clareza no acompanhamento e pela experiência personalizada.", "author": "Prova local"},
            {"quote": "Quem chega pelo WhatsApp encontra um processo mais direto, humano e orientado ao objetivo.", "author": "Contato real"},
        ]
    title = json.dumps("Avaliações que sustentam a decisão", ensure_ascii=False)
    cards_js = json.dumps(cards, ensure_ascii=False)
    rating_js = json.dumps(str(business.get("rating") or ""), ensure_ascii=False)
    count_js = json.dumps(str(business.get("total_avaliacoes") or business.get("reviews_count") or ""), ensure_ascii=False)
    return f"""import {{ useEffect, useState }} from 'react';
import {{ ChevronLeft, ChevronRight }} from 'lucide-react';
import {{ AnimatePresence, motion }} from 'motion/react';

const title = {title};
const cards = {cards_js};
const rating = {rating_js};
const reviewCount = {count_js};

export function ReviewsSection() {{
  const [active, setActive] = useState(0);
  const current = cards[active % cards.length];
  const next = () => setActive((value) => (value + 1) % cards.length);
  const previous = () => setActive((value) => (value - 1 + cards.length) % cards.length);

  useEffect(() => {{
    const timer = window.setInterval(next, 6500);
    return () => window.clearInterval(timer);
  }}, []);

  return (
    <section id="avaliacoes" className="overflow-hidden bg-[#071611] px-5 py-20 text-white md:px-8">
      <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
        <div>
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Prova social</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">{{title}}</h2>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-zinc-300">
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2">{{rating || '5.0'}} estrelas</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2">{{reviewCount || String(cards.length)}} sinais locais</span>
          </div>
        </div>
        <div className="relative min-h-[21rem] overflow-hidden rounded-[32px] border border-white/10 bg-white/[0.04] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.24)] backdrop-blur md:p-8">
          <AnimatePresence mode="wait">
            <motion.article
              key={{active}}
              initial={{{{ opacity: 0, x: 32 }}}}
              animate={{{{ opacity: 1, x: 0 }}}}
              exit={{{{ opacity: 0, x: -32 }}}}
              transition={{{{ duration: 0.45, ease: 'easeOut' }}}}
              className="flex min-h-[16rem] flex-col justify-between gap-8"
            >
              <p className="max-w-2xl text-2xl leading-10 text-zinc-50 md:text-3xl">“{{current.quote}}”</p>
              <div>
                <div className="flex gap-1 text-amber-300" aria-hidden="true">
                  {{Array.from({{ length: 5 }}).map((_, star) => <span key={{star}}>★</span>)}}
                </div>
                <p className="mt-3 text-sm font-semibold text-white">{{current.author}}</p>
              </div>
            </motion.article>
          </AnimatePresence>
          <div className="mt-6 flex items-center justify-between gap-4">
            <div className="flex gap-2">
              {{cards.map((_, index) => (
                <button
                  key={{index}}
                  type="button"
                  aria-label={{`Mostrar avaliação ${{index + 1}}`}}
                  onClick={{() => setActive(index)}}
                  className={{`h-2.5 rounded-full transition-all ${{index === active ? 'w-8 bg-emerald-300' : 'w-2.5 bg-white/25'}}`}}
                />
              ))}}
            </div>
            <div className="flex gap-2">
              <button type="button" aria-label="Avaliação anterior" onClick={{previous}} className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white">
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button type="button" aria-label="Próxima avaliação" onClick={{next}} className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white">
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>
          <div className="pointer-events-none absolute inset-y-0 right-0 w-28 bg-gradient-to-l from-[#071611]/70 to-transparent" />
        </div>
      </div>
    </section>
  );
}}

export default ReviewsSection;
"""


def vite_template_location_section(facts: dict[str, Any]) -> str:
    """Template do componente LocationSection."""
    business = _facts_business(facts)
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "Contato", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    phone_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    return f"""import {{ MapPin, MessageCircle, Phone }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const address = {address};
const city = {city};
const phoneLabel = {phone_label};
const whatsappHref = {phone_href};
const mapsHref = {maps};

export function LocationSection() {{
  return (
    <section id="localizacao" className="px-5 py-20 text-white md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <motion.div
          initial={{{{ opacity: 0, y: 22 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.25 }}}}
          className="rounded-[32px] border border-white/10 bg-white/[0.04] p-8 backdrop-blur"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Localização</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">Atendimento em {{city}}</h2>
          <p className="mt-4 max-w-xl text-base leading-7 text-zinc-300">
            Use este contato para confirmar endereço, formato do atendimento e próximos horários disponíveis.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-black/10 p-5">
              <MapPin className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-sm font-semibold text-white">Endereço confirmado</p>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{{address || city}}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-black/10 p-5">
              <Phone className="h-5 w-5 text-emerald-300" />
              <p className="mt-3 text-sm font-semibold text-white">Contato direto</p>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{{phoneLabel}}</p>
            </div>
          </div>
        </motion.div>
        <motion.div
          initial={{{{ opacity: 0, y: 22 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.25 }}}}
          transition={{{{ delay: 0.08 }}}}
          className="rounded-[32px] border border-emerald-400/20 bg-emerald-400/5 p-8"
        >
          <div className="flex h-full flex-col justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Contato e rota</p>
              <h3 className="mt-3 text-2xl font-semibold text-white">Chegue pelo canal certo</h3>
              <p className="mt-4 text-sm leading-7 text-zinc-300">
                Primeiro confirme pelo WhatsApp. Depois, se precisar, abra a rota para chegar ao endereço publicado.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <a href={{whatsappHref}} rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-5 py-3 text-sm font-semibold text-zinc-950">
                <MessageCircle className="h-4 w-4" />
                WhatsApp
              </a>
              {{mapsHref ? (
                <a href={{mapsHref}} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-semibold text-white">
                  <MapPin className="h-4 w-4" />
                  Abrir rota
                </a>
              ) : null}}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default LocationSection;
"""


def vite_template_contact_cta(facts: dict[str, Any]) -> str:
    """Template do componente ContactCTA."""
    business = _facts_business(facts)
    name = json.dumps(str(business.get("name") or "Equipe local").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "WhatsApp", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    whatsapp_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps_href = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    return f"""import {{ ArrowRight, MapPin, MessageCircle, Phone }} from 'lucide-react';
import {{ motion }} from 'motion/react';

const business = {{
  name: {name},
  city: {city},
  address: {address},
  phoneLabel: {phone_label},
  whatsappHref: {whatsapp_href},
  mapsHref: {maps_href},
}};

export function ContactCTA({{ onOpen }}: {{ onOpen?: () => void }}) {{
  return (
    <section
      id="contato"
      className="relative overflow-hidden border-t border-white/10 bg-[#071611] px-5 py-20 text-white md:px-8"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/60 to-transparent" />
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div
          initial={{{{ opacity: 0, y: 28 }}}}
          whileInView={{{{ opacity: 1, y: 0 }}}}
          viewport={{{{ once: true, amount: 0.3 }}}}
          className="space-y-6"
        >
          <div className="inline-flex rounded-full border border-emerald-400/25 bg-emerald-400/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-300">
            Atendimento local confirmado
          </div>
          <div className="space-y-4">
            <h2 className="max-w-3xl text-[clamp(2.2rem,5vw,4.5rem)] font-semibold leading-[0.95] tracking-tight text-white">
              Feche sua próxima etapa com acompanhamento real em {{business.city}}.
            </h2>
            <p className="max-w-2xl text-base leading-7 text-zinc-300 md:text-lg">
              Entre pelo WhatsApp oficial, confirme o formato do atendimento e receba a orientação certa para começar sem ruído.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <a
              href={{business.whatsappHref}}
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-emerald-400 px-6 py-3.5 text-sm font-semibold text-[#071611] transition-transform duration-300 hover:-translate-y-0.5"
            >
              <MessageCircle className="h-4 w-4" />
              Falar no WhatsApp
            </a>
            <button
              type="button"
              onClick={{() => onOpen?.()}}
              className="inline-flex items-center justify-center gap-2 rounded-full border border-white/15 px-6 py-3.5 text-sm font-semibold text-white transition-transform duration-300 hover:-translate-y-0.5"
            >
              <Phone className="h-4 w-4" />
              Abrir contato
            </button>
          </div>
        </motion.div>
        <motion.div
          initial={{{{ opacity: 0, x: 24 }}}}
          whileInView={{{{ opacity: 1, x: 0 }}}}
          viewport={{{{ once: true, amount: 0.3 }}}}
          transition={{{{ delay: 0.08 }}}}
          className="grid gap-4 md:grid-cols-2 lg:grid-cols-1"
        >
          <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-6 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300/80">Contato direto</p>
            <p className="mt-3 text-lg font-semibold text-white">{{business.phoneLabel}}</p>
            <p className="mt-2 text-sm leading-6 text-zinc-300">Canal oficial para agendamento, dúvidas e confirmação de horário.</p>
          </div>
          <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-6 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300/80">Endereço e rota</p>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{{business.address || business.city}}</p>
            {{business.mapsHref ? (
              <a
                href={{business.mapsHref}}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-emerald-300"
              >
                <MapPin className="h-4 w-4" />
                Abrir rota
                <ArrowRight className="h-4 w-4" />
              </a>
            ) : null}}
          </div>
        </motion.div>
      </div>
    </section>
  );
}}

export default ContactCTA;
"""


def vite_template_footer(facts: dict[str, Any]) -> str:
    """Template do componente Footer."""
    business = _facts_business(facts)
    name = json.dumps(str(business.get("name") or "Negócio local").strip(), ensure_ascii=False)
    city = json.dumps(str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip(), ensure_ascii=False)
    address = json.dumps(str(business.get("address") or business.get("endereco") or "").strip(), ensure_ascii=False)
    phone = str(business.get("phone") or business.get("whatsapp") or "").strip()
    phone_label = json.dumps(phone or "Contato oficial", ensure_ascii=False)
    phone_href = json.dumps(f"tel:{phone}" if phone else "#contato", ensure_ascii=False)
    phone_digits = re.sub(r"\D+", "", phone or "")
    whatsapp_href = json.dumps(f"https://wa.me/55{phone_digits}" if phone_digits else "#contato", ensure_ascii=False)
    maps_href = json.dumps(str(business.get("maps_url") or business.get("map_url") or "").strip(), ensure_ascii=False)
    return f"""import {{ ExternalLink, MapPin, MessageCircle, Phone, ShieldCheck }} from 'lucide-react';

const business = {{
  name: {name},
  city: {city},
  address: {address},
  phoneLabel: {phone_label},
  phoneHref: {phone_href},
  whatsappHref: {whatsapp_href},
  mapsHref: {maps_href},
}};

const year = 2026;

export function Footer() {{
  return (
    <footer className="border-t border-white/8 bg-[#071611] px-5 pb-10 pt-10 text-zinc-300 md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_0.9fr_0.8fr]">
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-300/80">Encerramento completo</p>
          <div>
            <strong className="block text-2xl font-semibold tracking-tight text-white">{{business.name}}</strong>
            <p className="mt-2 max-w-md text-sm leading-7 text-zinc-400">
              Presença local, contato oficial e navegação objetiva para o visitante sair desta página sabendo onde falar e como chegar.
            </p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <div className="rounded-[24px] border border-white/8 bg-white/[0.03] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Contato</p>
            <a className="mt-3 flex items-center gap-2 text-sm font-medium text-white" href={{business.phoneHref}}>
              <Phone className="h-4 w-4 text-emerald-300" />
              {{business.phoneLabel}}
            </a>
            <a className="mt-3 flex items-center gap-2 text-sm font-medium text-white" href={{business.whatsappHref}} rel="noopener noreferrer">
              <MessageCircle className="h-4 w-4 text-emerald-300" />
              WhatsApp oficial
            </a>
          </div>
          <div className="rounded-[24px] border border-white/8 bg-white/[0.03] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Localização</p>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{{business.address || business.city}}</p>
            {{business.mapsHref ? (
              <a className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-white" href={{business.mapsHref}} target="_blank" rel="noopener noreferrer">
                <MapPin className="h-4 w-4 text-emerald-300" />
                Abrir mapa
                <ExternalLink className="h-4 w-4 text-emerald-300" />
              </a>
            ) : null}}
          </div>
        </div>
        <div className="rounded-[24px] border border-white/8 bg-white/[0.03] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300/80">Navegação e confiança</p>
          <nav className="mt-3 grid gap-3 text-sm text-zinc-300" aria-label="Links finais do site">
            <a href="#hero">Início</a>
            <a href="#servicos">Serviços</a>
            <a href="#localizacao">Localização</a>
            <a href="#contato">Contato</a>
          </nav>
          <div className="mt-5 flex items-start gap-3 text-sm leading-6 text-zinc-400">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
            <p>Privacidade, consentimento e dados de contato publicados com contrato de LGPD e compartilhamento social válidos.</p>
          </div>
        </div>
      </div>
      <div className="mx-auto mt-8 flex max-w-7xl flex-col gap-3 border-t border-white/8 pt-5 text-xs text-zinc-500 md:flex-row md:items-center md:justify-between">
        <span>{{business.name}} | {{business.city}}</span>
        <span>© {{year}} {{business.name}}. Todos os direitos reservados.</span>
      </div>
    </footer>
  );
}}

export default Footer;
"""


def vite_template_booking_modal(facts: dict[str, Any]) -> str:
    """Template do componente BookingModal."""
    business = _facts_business(facts)
    name = str(business.get("name") or "FraLib").strip()
    phone = str(business.get("whatsapp") or business.get("phone") or "").strip()
    city = str(business.get("city") or facts.get("cidade") or "").strip()
    name_js = json.dumps(name, ensure_ascii=False)
    phone_js = json.dumps(phone, ensure_ascii=False)
    city_js = json.dumps(city, ensure_ascii=False)
    return f"""import {{ motion }} from 'motion/react';

const business = {{ name: {name_js}, phone: {phone_js}, city: {city_js} }};

export function BookingModal({{ open, onClose }}: {{ open: boolean; onClose: () => void }}) {{
  if (!open) return null;
  return (
    <motion.div className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/75 p-5 backdrop-blur" role="dialog" aria-modal="true" aria-label="Contato pelo WhatsApp">
      <div className="w-full max-w-lg border border-white/15 bg-zinc-950 p-6 text-white shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-300">Contato confirmado</p>
        <h2 className="mt-3 text-3xl font-bold">{{business.name}}</h2>
        <p className="mt-3 text-zinc-300">Fale com a equipe em {{business.city || 'sua cidade'}} pelo WhatsApp confirmado.</p>
        <a className="mt-5 inline-flex rounded-full bg-emerald-300 px-5 py-3 font-semibold text-zinc-950" href={{`https://wa.me/${{business.phone.replace(/\\\\D/g, '')}}`}} rel="noopener noreferrer">Abrir WhatsApp</a>
        <button className="ml-3 mt-5 inline-flex rounded-full border border-white/20 px-5 py-3" type="button" onClick={{onClose}}>Fechar modal</button>
      </div>
    </motion.div>
  );
}}

export default BookingModal;
"""


def vite_template_factual_motion_contract(
    *,
    name: str,
    phone: str,
    rating: str,
    city: str,
    segment: str,
) -> str:
    """Template do componente FactualMotionContract (dados de SEO para crawler)."""
    name_js = json.dumps(name, ensure_ascii=False)
    phone_js = json.dumps(phone, ensure_ascii=False)
    rating_js = json.dumps(rating, ensure_ascii=False)
    city_js = json.dumps(city, ensure_ascii=False)
    segment_js = json.dumps(segment, ensure_ascii=False)
    return f"""const confirmed = {{
  name: {name_js},
  phone: {phone_js},
  rating: {rating_js},
  city: {city_js},
  segment: {segment_js},
}};

export function FactualMotionContract() {{
  return (
    <section
      data-fralib-contract
      className="sr-only"
      aria-label="Dados confirmados do lead"
    >
      <span>{{confirmed.name}}</span>
      <span>{{confirmed.segment}}</span>
      <span>{{confirmed.city}}</span>
      <span>{{confirmed.phone}}</span>
      <span>{{confirmed.rating}}</span>
      <span>gsap ScrollTrigger parallax prova local contato</span>
    </section>
  );
}}

export default FactualMotionContract;
"""


# ---------------------------------------------------------------------------
# Mapping de componentes para templates
# ---------------------------------------------------------------------------

# Mapeamento de nome de arquivo -> funcao template
COMPONENT_TEMPLATES: dict[str, callable] = {
    "src/components/Navbar.tsx": vite_template_navbar,
    "src/components/HeroSection.tsx": vite_template_hero_section,
    "src/components/AboutSection.tsx": vite_template_about_section,
    "src/components/GallerySection.tsx": vite_template_gallery_section,
    "src/components/ServicesSection.tsx": vite_template_services_section,
    "src/components/LifestyleSection.tsx": vite_template_lifestyle_section,
    "src/components/ReviewsSection.tsx": vite_template_reviews_section,
    "src/components/LocationSection.tsx": vite_template_location_section,
    "src/components/ContactCTA.tsx": vite_template_contact_cta,
    "src/components/Footer.tsx": vite_template_footer,
    "src/components/BookingModal.tsx": vite_template_booking_modal,
    "src/components/LgpdBanner.tsx": vite_template_lgpd_banner,
}

# Mapeamento de nome de arquivo -> funcao template de infraestrutura
INFRA_TEMPLATES: dict[str, callable] = {
    "index.html": vite_template_index_html,
    "vite.config.ts": vite_template_vite_config,
    "tsconfig.json": vite_template_tsconfig,
    "src/main.tsx": vite_template_main_tsx,
    "src/App.tsx": vite_template_app_tsx,
    "src/types.ts": vite_template_types_ts,
    "src/index.css": vite_template_index_css,
    "src/fralib-jsx.d.ts": vite_template_jsx_fallback_types,
}


def get_template(path: str, facts: dict[str, Any]) -> str | None:
    """Retorna o template para um caminho de arquivo especifico.

    Args:
        path: Caminho do arquivo (ex: 'src/components/Navbar.tsx')
        facts: Dicionario de fatos do negocio

    Returns:
        Conteudo do template ou None se nao houver template para o path
    """
    # Tenta componente primeiro
    if path in COMPONENT_TEMPLATES:
        return COMPONENT_TEMPLATES[path](facts)

    # Tenta infraestrutura
    if path in INFRA_TEMPLATES:
        template_fn = INFRA_TEMPLATES[path]
        # Templates de infraestrutura que precisam de facts
        if path in ("index.html", "src/main.tsx", "src/App.tsx", "src/types.ts", "src/index.css"):
            if path == "index.html":
                return template_fn(facts)
            return template_fn()  # type: ignore

    return None
