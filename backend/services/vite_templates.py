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
    """Get theme color from facts, with archetype-based fallback."""
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

    # Sprint 16: Use archetype palette from facts if available
    archetype_data = facts.get("_archetype_palette") if isinstance(facts.get("_archetype_palette"), dict) else {}
    if archetype_data.get("primary"):
        return archetype_data["primary"]

    return "#111827"


def _facts_local_keywords(facts: dict[str, Any]) -> list[str]:
    business = _facts_business(facts)
    seo = facts.get("seo") if isinstance(facts.get("seo"), dict) else {}
    candidates = seo.get("primary_terms") or facts.get("seo_keywords") or business.get("seo_keywords") or []
    if not isinstance(candidates, list):
        candidates = re.split(r"[,;\n]", str(candidates or ""))
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(item: Any) -> None:
        term = re.sub(r"\s+", " ", str(item or "")).strip(" ,.;:-")
        key = term.lower()
        if not term or key in seen:
            return
        seen.add(key)
        keywords.append(term)

    for item in candidates:
        _add(item)

    city = str(business.get("city") or business.get("cidade") or facts.get("cidade") or "").strip()
    state = str(business.get("state") or business.get("estado") or facts.get("estado") or "").strip()
    segment = str(business.get("segmento") or business.get("segment") or facts.get("segmento") or "").strip()
    subniche = str(business.get("subnicho") or business.get("subniche") or facts.get("subnicho") or facts.get("subniche") or "").strip()
    context = f"{segment} {subniche}".lower()
    _add(city)
    _add(state)
    _add(segment)
    _add(subniche)
    if city and segment:
        _add(f"{segment} em {city}")
        _add(f"{segment} {city}")
    if city and any(token in context for token in ("barbearia", "barber", "barbeiro")):
        _add(f"barbearia em {city}")
        _add(f"corte masculino {city}")
        _add(f"barba e cabelo {city}")
    if city and any(token in context for token in ("nutri", "nutric")):
        _add(f"nutricionista em {city}")
        _add(f"nutricionista esportivo {city}")
        _add(f"consulta nutricional {city}")
    if city and any(token in context for token in ("academia", "crossfit", "muscul", "fitness", "funcional", "personal")):
        _add(f"academia em {city}")
        _add(f"musculação {city}")
        _add(f"aula experimental academia {city}")
    address = str(business.get("address") or business.get("endereco") or facts.get("endereco") or "")
    for part in re.split(r"[,\-]", address)[-2:]:
        _add(part)
    return keywords[:12]


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
    """Retorna URLs de imagens para uso nos templates de componentes.

    Fail-fast: retorna lista vazia se não houver fotos — não usa fallbacks.
    """
    business = _facts_business(facts)
    media = facts.get("media") if isinstance(facts.get("media"), dict) else {}
    urls: list[str] = []
    for source in (media.get("photos"), business.get("photos"), facts.get("photos")):
        if isinstance(source, list):
            urls.extend(str(item or "").strip() for item in source if str(item or "").strip())
    if not urls:
        from backend.pipeline_exceptions import ImageNotAvailableError
        raise ImageNotAvailableError(
            "_visual_media_urls: Sem imagens no facts.",
            context={"segmento": business.get("segment", ""), "acao": "Forneca fotos no lead"},
        )
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
    chunkSizeWarningLimit: 250,
    rollupOptions: {
      output: {
        manualChunks: {
          motion: ['motion/react', 'gsap', 'gsap/ScrollTrigger'],
          icons: ['lucide-react'],
        },
      },
    },
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


def vite_template_utils_ts() -> str:
    return """import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
"""


def vite_template_avatar_ui() -> str:
    return """import { cn } from '../../lib/utils';

function Avatar({ className, children, ...props }: any) {
  return (
    <div
      className={cn('relative flex h-11 w-11 shrink-0 overflow-hidden rounded-full border border-white/10 bg-white/10', className)}
      {...props}
    >
      {children}
    </div>
  );
}

function AvatarImage({ className, ...props }: any) {
  return <img className={cn('aspect-square h-full w-full object-cover', className)} {...props} />;
}

function AvatarFallback({ className, children, ...props }: any) {
  return (
    <div
      className={cn('flex h-full w-full items-center justify-center bg-white/10 text-sm font-semibold text-white', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export { Avatar, AvatarFallback, AvatarImage };
"""


def vite_template_separator_ui() -> str:
    return """import { cn } from '../../lib/utils';

function Separator({ className, orientation = 'horizontal', ...props }: any) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'shrink-0 bg-white/10',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className
      )}
      {...props}
    />
  );
}

export { Separator };
"""


def vite_template_accordion_ui() -> str:
    return """import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

function Accordion({ children, className = '' }: any) {
  return <div className={className}>{children}</div>;
}

function AccordionItem({ value, children, className = '' }: any) {
  const [open, setOpen] = useState(false);
  const childArray = Array.isArray(children) ? children : [children];
  const trigger = childArray.find((child: any) => child?.type?.displayName === 'FraAccordionTrigger');
  const content = childArray.find((child: any) => child?.type?.displayName === 'FraAccordionContent');
  return (
    <div className={cn('border-b border-white/10', className)} data-value={value}>
      {trigger ? trigger.type({ ...trigger.props, open, onToggle: () => setOpen((prev: boolean) => !prev) }) : null}
      {content ? content.type({ ...content.props, open }) : null}
    </div>
  );
}

function AccordionTrigger({ className, children, open = false, onToggle, ...props }: any) {
  return (
    <button
      type="button"
      className={cn(
        'flex w-full items-center justify-between py-4 text-left text-base font-semibold transition hover:text-white',
        className
      )}
      aria-expanded={open}
      onClick={onToggle}
      {...props}
    >
      <span>{children}</span>
      <ChevronDown className={cn('h-4 w-4 shrink-0 transition-transform duration-200', open ? 'rotate-180' : '')} />
    </button>
  );
}
AccordionTrigger.displayName = 'FraAccordionTrigger';

function AccordionContent({ className, children, open = false, ...props }: any) {
  if (!open) return null;
  return (
    <div className={cn('overflow-hidden pb-4 text-sm leading-7 text-zinc-300', className)} {...props}>
      {children}
    </div>
  );
}
AccordionContent.displayName = 'FraAccordionContent';

export { Accordion, AccordionContent, AccordionItem, AccordionTrigger };
"""


def vite_template_lgpd_banner(facts: dict[str, Any] | None = None) -> str:
    """Template do componente LgpdBanner (banner de consentimento LGPD).

    Quando facts e fornecido, gera versao personalizada por negocio usando
    backend.agents.lgpd_personalized.build_personalized_lgpd().
    Caso contrario, usa o template generico.
    """
    if facts:
        try:
            from backend.agents.lgpd_personalized import build_personalized_lgpd
            return build_personalized_lgpd(facts)
        except Exception:
            pass  # Fallback to generic template below
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
      className="fixed inset-x-4 bottom-4 z-[9999] mx-auto grid max-w-3xl grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl p-4 shadow-2xl"
      style={{ background: 'var(--bg-light)', color: 'var(--text-dark)', border: '1px solid color-mix(in srgb, var(--accent) 26%, transparent)' }}
      role="dialog"
      aria-label="Aviso de privacidade"
    >
      <ShieldCheck className="h-5 w-5" style={{ color: 'var(--accent)' }} />
      <p className="text-sm leading-5" style={{ color: 'var(--text-dark)' }}>Tratamos dados de contato apenas para atendimento, segurança e melhoria da experiência.</p>
      <div className="flex items-center gap-2">
        <button type="button" data-lgpd-accept onClick={accept} className="rounded-full px-4 py-2 text-sm font-semibold" style={{ background: 'var(--accent)', color: 'var(--accent-contrast)' }}>
          Aceitar
        </button>
        <button type="button" aria-label="Fechar aviso de privacidade" onClick={accept} className="inline-flex h-9 w-9 items-center justify-center rounded-full" style={{ color: 'var(--text-dark)', border: '1px solid color-mix(in srgb, var(--accent) 18%, transparent)' }}>
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

export default LgpdBanner;
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
# shadcn/ui — Sprint 11
# ---------------------------------------------------------------------------
# Catálogo de componentes shadcn/ui disponíveis para os projetos Vite/React
# gerados pela pipeline. O LLM recebe esse catálogo como referência em vez de
# inventar componentes do zero.

from typing import Final


SHADCN_COMPONENTS: Final[dict[str, dict[str, Any]]] = {
    "Button": {
        "import": "import { Button } from '@/components/ui/button'",
        "variants": ["default", "destructive", "outline", "secondary", "ghost", "link"],
        "sizes": ["default", "sm", "lg", "icon"],
        "use_case": "CTAs, ações primárias/secundárias, submit de formulários",
        "example": '<Button variant="default" size="lg">Agendar agora</Button>',
    },
    "Card": {
        "imports": [
            "import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'"
        ],
        "parts": ["Card", "CardHeader", "CardTitle", "CardDescription", "CardContent", "CardFooter"],
        "use_case": "Conteúdo em cards (serviços, planos, depoimentos, produtos)",
        "example": '<Card><CardHeader><CardTitle>Plano Premium</CardTitle></CardHeader><CardContent>R$ 199/mês</CardContent></Card>',
    },
    "Input": {
        "import": "import { Input } from '@/components/ui/input'",
        "use_case": "Campos de formulário (nome, email, telefone, mensagem)",
        "example": '<Input type="email" placeholder="seu@email.com" />',
    },
    "Badge": {
        "import": "import { Badge } from '@/components/ui/badge'",
        "variants": ["default", "secondary", "destructive", "outline"],
        "use_case": "Tags, categorias, status, labels de destaque",
        "example": '<Badge variant="secondary">Novo</Badge>',
    },
    # Sprint 11.5: Dialog/Modal — usado por BookingModal, ContactModal, Lightbox
    # Resolve "componente studio obrigatorio: modal" no vite_react_renderer:2094
    "Dialog": {
        "imports": [
            "import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from '@/components/ui/dialog'"
        ],
        "parts": ["Dialog", "DialogContent", "DialogHeader", "DialogTitle", "DialogDescription", "DialogTrigger", "DialogClose"],
        "use_case": "Modais de contato/agendamento, lightbox de galeria, confirmacoes",
        "example": '<Dialog><DialogTrigger asChild><Button>Agendar</Button></DialogTrigger><DialogContent><DialogTitle>Agendar horario</DialogTitle></DialogContent></Dialog>',
    },
    # Sprint 11.5: Tabs (FAQ, detalhes de servicos)
    "Tabs": {
        "imports": [
            "import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'"
        ],
        "parts": ["Tabs", "TabsList", "TabsTrigger", "TabsContent"],
        "use_case": "FAQ em abas, detalhes de servicos/segmentos, secoes alternaveis",
        "example": '<Tabs defaultValue="horarios"><TabsList><TabsTrigger value="horarios">Horarios</TabsTrigger></TabsList><TabsContent value="horarios">Seg-Sex 9h-20h</TabsContent></Tabs>',
    },
    # Sprint 11.5: Textarea (formulario de contato)
    "Textarea": {
        "import": "import { Textarea } from '@/components/ui/textarea'",
        "use_case": "Campos de mensagem longa (contato, feedback, observacoes)",
        "example": '<Textarea placeholder="Sua mensagem..." rows={4} />',
    },
}


# Mapeamento de seção do site → componente shadcn mais adequado.
# Usado pelo vite_prompts.py para sugerir componentes ao LLM sem obrigar.
SECTION_COMPONENT_MAP: Final[dict[str, list[str]]] = {
    "hero": ["Button", "Badge"],
    "cta": ["Button"],
    "features": ["Card", "Badge"],
    "services": ["Card", "Button"],
    "pricing": ["Card", "Button", "Badge"],
    "testimonials": ["Card", "Badge"],
    "faq": ["Tabs", "Card"],
    "contact": ["Input", "Textarea", "Button", "Dialog"],
    "form": ["Input", "Textarea", "Button"],
    "footer": ["Button"],
    "navbar": ["Button", "Dialog"],
    "gallery": ["Card", "Dialog"],
    "about": ["Card", "Badge"],
    "stats": ["Card", "Badge"],
    "modal": ["Dialog", "Button"],  # Sprint 11.5: secao modal explicita
    "booking-modal": ["Dialog", "Button"],  # requerido pelo vite_react_renderer
}


def get_shadcn_component_list() -> str:
    """Retorna a lista formatada de componentes shadcn disponíveis para injetar no prompt do LLM.

    Returns:
        String formatada com nome, use_case e variants de cada componente.
    """
    lines: list[str] = []
    for name, meta in SHADCN_COMPONENTS.items():
        variants = meta.get("variants")
        sizes = meta.get("sizes")
        parts = meta.get("parts")
        line = f"- **{name}**: {meta['use_case']}"
        if variants:
            line += f" | variants: {', '.join(variants)}"
        if sizes:
            line += f" | sizes: {', '.join(sizes)}"
        if parts:
            line += f" | parts: {', '.join(parts)}"
        lines.append(line)
    return "\n".join(lines)


def get_shadcn_imports(components: list[str]) -> list[str]:
    """Gera as linhas de import para os componentes shadcn solicitados.

    Args:
        components: Lista de nomes de componentes (ex: ["Button", "Card"]).

    Returns:
        Lista de statements de import (sem duplicatas).
    """
    seen: set[str] = set()
    imports: list[str] = []
    for name in components:
        meta = SHADCN_COMPONENTS.get(name)
        if not meta:
            continue
        # Componentes com múltiplos imports (Card) ou único
        if "imports" in meta:
            for imp in meta["imports"]:
                if imp not in seen:
                    seen.add(imp)
                    imports.append(imp)
        elif "import" in meta:
            imp = meta["import"]
            if imp not in seen:
                seen.add(imp)
                imports.append(imp)
    return imports


def get_shadcn_components_for_section(section: str) -> list[str]:
    """Sugere componentes shadcn adequados para uma seção do site.

    Args:
        section: Nome da seção (ex: "hero", "pricing").

    Returns:
        Lista de nomes de componentes. Vazio se seção desconhecida.
    """
    return list(SECTION_COMPONENT_MAP.get(section.lower(), []))


# ---------------------------------------------------------------------------
# Mapping de componentes para templates
# ---------------------------------------------------------------------------

# Mapeamento de nome de arquivo -> funcao template
