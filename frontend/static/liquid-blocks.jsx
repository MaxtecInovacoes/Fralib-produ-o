/**
 * ============================================================================
 * FRA LIB - LIQUID BLOCKS
 * ============================================================================
 * Sistema de Blocos Líquidos - Componentes React com 4 Polos Estéticos
 *
 * Polos: SOFT | BOLD | CORPORATE | MINIMAL
 *
 * Uso: <HeroPole pole="bold" headline="Texto" /> ou usePoleTokens('soft')
 *
 * ============================================================================
 */

import React, { useEffect, useState, useRef } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// HOOK: usePoleTokens
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Hook para obter tokens CSS do polo atual.
 * Lê de data-pole no documento ou aceita pole via props.
 */
export function usePoleTokens(pole?: string) {
  const [tokens, setTokens] = useState({
    pole: pole || 'corporate',
    radius: '6px',
    headingFont: 'Inter',
    headingCase: 'capitalize',
    headingStyle: 'normal',
    textSkew: '0deg',
    motionSpeed: '300ms',
    motionEase: 'ease',
    sectionOverlap: '0px',
    textStroke: false,
    textStrokeWidth: '0px',
    shadowCard: '0 1px 3px rgba(0,0,0,0.1)',
    shadowButton: 'none',
    shadowGlow: '0 0 20px rgba(59,130,246,0.15)',
  });

  useEffect(() => {
    if (pole) {
      setTokens(prev => ({ ...prev, pole }));
      return;
    }

    // Ler do data-pole do documento
    const docPole = document.documentElement.getAttribute('data-pole');
    if (docPole) {
      const newTokens = getPoleTokensFromCSS(docPole);
      setTokens(newTokens);
    }
  }, [pole]);

  return tokens;
}

/**
 * Obtém tokens CSS de um polo específico.
 */
function getPoleTokensFromCSS(pole: string) {
  const styles = getComputedStyle(document.documentElement);

  const defaults = {
    soft: {
      radius: '40px',
      headingFont: "'Playfair Display', serif",
      headingCase: 'capitalize',
      headingStyle: 'normal',
      textSkew: '0deg',
      motionSpeed: '600ms',
      motionEase: 'cubic-bezier(0.4, 0, 0.2, 1)',
      sectionOverlap: '0px',
      textStroke: false,
      textStrokeWidth: '0px',
      shadowCard: '0 8px 32px rgba(139, 92, 246, 0.12)',
      shadowButton: '0 4px 16px rgba(139, 92, 246, 0.25)',
      shadowGlow: '0 8px 32px rgba(139, 92, 246, 0.2)',
    },
    bold: {
      radius: '0px',
      headingFont: "'Anton', Impact, sans-serif",
      headingCase: 'uppercase',
      headingStyle: 'italic',
      textSkew: '-5deg',
      motionSpeed: '150ms',
      motionEase: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      sectionOverlap: '-80px',
      textStroke: true,
      textStrokeWidth: '2px',
      shadowCard: '8px 8px 0px var(--fralib-primary)',
      shadowButton: '4px 4px 0px var(--fralib-accent)',
      shadowGlow: '0 0 40px rgba(239, 68, 68, 0.4)',
    },
    corporate: {
      radius: '6px',
      headingFont: "'Inter', system-ui, sans-serif",
      headingCase: 'capitalize',
      headingStyle: 'normal',
      textSkew: '0deg',
      motionSpeed: '300ms',
      motionEase: 'ease',
      sectionOverlap: '0px',
      textStroke: false,
      textStrokeWidth: '0px',
      shadowCard: '0 1px 3px rgba(0, 0, 0, 0.1)',
      shadowButton: 'none',
      shadowGlow: '0 0 20px rgba(59, 130, 246, 0.15)',
    },
    minimal: {
      radius: '12px',
      headingFont: "'Space Grotesk', system-ui, sans-serif",
      headingCase: 'lowercase',
      headingStyle: 'normal',
      textSkew: '2deg',
      motionSpeed: '400ms',
      motionEase: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      sectionOverlap: '-40px',
      textStroke: false,
      textStrokeWidth: '0px',
      shadowCard: '0 0 40px rgba(59, 130, 246, 0.15)',
      shadowButton: '0 0 20px rgba(59, 130, 246, 0.4)',
      shadowGlow: '0 0 60px rgba(59, 130, 246, 0.3)',
    },
  };

  return defaults[pole as keyof typeof defaults] || defaults.corporate;
}

// ═══════════════════════════════════════════════════════════════════════════
// HERO SECTION - 4 Display Modes
// ═══════════════════════════════════════════════════════════════════════════

export function HeroPole({
  pole = 'corporate',
  headline,
  subheadline,
  badge,
  ctaText = 'Comece Agora',
  onCtaClick,
  backgroundImage,
  displayMode, // override automatic mode selection
}) {
  const tokens = usePoleTokens(pole);

  // Auto-select display mode based on pole if not specified
  const effectiveMode = displayMode || getDefaultHeroMode(pole);

  const modeConfig = {
    // SOFT modes
    centered: {
      container: 'flex flex-col items-center justify-center text-center min-h-[70vh] px-8',
      headline: 'text-center max-w-3xl',
      imageStyle: 'rounded-[40px] shadow-2xl max-w-lg',
      ctaStyle: 'rounded-full px-8 py-4',
      badgeStyle: 'rounded-full px-4 py-2',
    },
    // BOLD modes
    impact: {
      container: 'relative overflow-hidden min-h-screen',
      headline: 'uppercase italic skew-x-[-5deg] text-[clamp(4rem,15vw,12vw)] leading-none',
      imageStyle: 'absolute inset-0 w-full h-full object-cover opacity-30',
      ctaStyle: 'rounded-none px-8 py-4 uppercase tracking-wider shadow-[4px_4px_0px_var(--fralib-accent)]',
      badgeStyle: 'rounded-none px-4 py-2 uppercase tracking-widest',
    },
    split_tension: {
      container: 'grid md:grid-cols-2 gap-0 items-center',
      headline: 'col-span-2 uppercase italic',
      imageStyle: '-ml-8 rounded-none shadow-none',
      ctaStyle: 'rounded-none px-6 py-3 uppercase',
      badgeStyle: 'rounded-none px-3 py-1 uppercase text-sm',
    },
    // CORPORATE modes
    split: {
      container: 'grid md:grid-cols-2 gap-8 items-center py-16',
      headline: 'text-4xl font-semibold',
      imageStyle: 'rounded-lg',
      ctaStyle: 'rounded-md px-6 py-3',
      badgeStyle: 'rounded px-3 py-1 text-sm',
    },
    centered_credibility: {
      container: 'flex flex-col items-center text-center py-16',
      headline: 'text-5xl font-semibold',
      imageStyle: 'rounded-lg max-w-md',
      ctaStyle: 'rounded-md px-6 py-3',
      badgeStyle: 'rounded px-3 py-1 text-sm',
    },
    // MINIMAL modes
    bento: {
      container: 'grid grid-cols-12 gap-4 auto-rows-[minmax(100px,auto)]',
      headline: 'col-span-8 text-6xl lowercase font-medium',
      imageStyle: 'col-span-4 rounded-xl',
      ctaStyle: 'rounded-xl px-6 py-3 shadow-[0_0_20px_rgba(59,130,246,0.4)]',
      badgeStyle: 'rounded-xl px-3 py-1 text-sm',
    },
    glass_overlay: {
      container: 'relative min-h-[80vh] flex items-center',
      headline: 'text-7xl font-mono lowercase',
      imageStyle: 'rounded-xl',
      ctaStyle: 'rounded-xl px-6 py-3 backdrop-blur-md',
      badgeStyle: 'rounded-xl px-3 py-1 text-sm backdrop-blur-sm',
    },
  };

  const mode = modeConfig[effectiveMode as keyof typeof modeConfig] || modeConfig.centered;

  return (
    <section className={`relative ${mode.container}`} data-pole={pole}>
      {/* Background Image */}
      {backgroundImage && (
        <img
          src={backgroundImage}
          alt=""
          className={mode.imageStyle}
          style={{
            position: effectiveMode === 'impact' ? 'absolute' : undefined,
            inset: effectiveMode === 'impact' ? 0 : undefined,
          }}
        />
      )}

      {/* Content Overlay for impact mode */}
      {effectiveMode === 'impact' && (
        <div className="absolute inset-0 bg-gradient-to-t from-[--fralib-bg-dark] via-transparent to-transparent" />
      )}

      {/* Badge */}
      {badge && (
        <span
          className={`inline-block ${mode.badgeStyle} bg-[--fralib-primary] text-white mb-6`}
          style={{
            borderRadius: tokens.radius,
            textTransform: tokens.headingCase,
          }}
        >
          {badge}
        </span>
      )}

      {/* Headline */}
      <h1
        className={mode.headline}
        style={{
          fontFamily: tokens.headingFont,
          fontStyle: tokens.headingStyle,
          textTransform: tokens.headingCase === 'capitalize' ? undefined : tokens.headingCase,
          WebkitTextStroke: tokens.textStroke ? `${tokens.textStrokeWidth} var(--fralib-primary)` : 'none',
          transform: tokens.textSkew !== '0deg' ? `skewX(${tokens.textSkew})` : undefined,
          color: tokens.textStroke ? 'transparent' : 'var(--fralib-text-light)',
          backgroundClip: tokens.textStroke ? 'text' : undefined,
          WebkitBackgroundClip: tokens.textStroke ? 'text' : undefined,
          backgroundImage: tokens.textStroke
            ? 'linear-gradient(to bottom, var(--fralib-text-light), var(--fralib-text-light))'
            : undefined,
        }}
      >
        {headline}
      </h1>

      {/* Subheadline */}
      {subheadline && (
        <p
          className="text-gray-400 max-w-xl mt-4"
          style={{
            transform: tokens.textSkew !== '0deg' ? `skewX(${tokens.textSkew})` : undefined,
          }}
        >
          {subheadline}
        </p>
      )}

      {/* CTA Button */}
      {ctaText && (
        <button
          onClick={onCtaClick}
          className={`mt-8 ${mode.ctaStyle}`}
          style={{
            fontFamily: tokens.headingFont,
            textTransform: tokens.headingCase === 'capitalize' ? undefined : tokens.headingCase,
            borderRadius: tokens.radius === '0px' ? 0 : tokens.radius,
            boxShadow: tokens.shadowButton,
            transition: `all ${tokens.motionSpeed} ${tokens.motionEase}`,
          }}
        >
          {ctaText}
        </button>
      )}
    </section>
  );
}

function getDefaultHeroMode(pole: string): string {
  const modes = {
    soft: 'centered',
    bold: 'impact',
    corporate: 'split',
    minimal: 'bento',
  };
  return modes[pole] || 'split';
}

// ═══════════════════════════════════════════════════════════════════════════
// CARD POLE - Cards com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function CardPole({
  pole = 'corporate',
  title,
  description,
  icon,
  image,
  badge,
  href,
  onClick,
  variant = 'default', // default, glass, outlined
}) {
  const tokens = usePoleTokens(pole);

  const isGlass = variant === 'glass';
  const isOutlined = variant === 'outlined';

  return (
    <div
      className={`
        p-6 transition-all duration-300
        ${isGlass ? 'glass-card' : ''}
        ${isOutlined ? 'border-2 border-[--fralib-primary]' : ''}
        hover:-translate-y-1
      `}
      style={{
        borderRadius: tokens.radius,
        boxShadow: tokens.shadowCard,
        fontFamily: tokens.headingFont,
        transition: `all ${tokens.motionSpeed} ${tokens.motionEase}`,
      }}
    >
      {/* Badge */}
      {badge && (
        <span
          className="inline-block px-3 py-1 text-xs font-medium rounded-full bg-[--fralib-primary]/10 text-[--fralib-primary] mb-3"
          style={{ borderRadius: tokens.radius }}
        >
          {badge}
        </span>
      )}

      {/* Icon */}
      {icon && (
        <div
          className="w-12 h-12 rounded-full bg-[--fralib-primary]/10 flex items-center justify-center mb-4"
          style={{ borderRadius: tokens.radius }}
        >
          {icon}
        </div>
      )}

      {/* Image */}
      {image && (
        <img
          src={image}
          alt={title}
          className="w-full h-48 object-cover mb-4"
          style={{ borderRadius: tokens.radius }}
        />
      )}

      {/* Title */}
      <h3
        className="text-xl font-semibold mb-2"
        style={{
          fontFamily: tokens.headingFont,
          textTransform: tokens.headingCase,
        }}
      >
        {title}
      </h3>

      {/* Description */}
      <p className="text-gray-400">{description}</p>

      {/* Link/Button */}
      {(href || onClick) && (
        <button
          onClick={onClick}
          className="mt-4 text-[--fralib-primary] font-medium flex items-center gap-2"
        >
          Saiba mais
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// BUTTON POLE - Botões com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function ButtonPole({
  pole = 'corporate',
  children,
  variant = 'primary', // primary, secondary, ghost
  size = 'medium', // small, medium, large
  onClick,
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
}) {
  const tokens = usePoleTokens(pole);

  const sizes = {
    small: { padding: '0.5rem 1rem', fontSize: '0.875rem' },
    medium: { padding: '0.75rem 1.5rem', fontSize: '1rem' },
    large: { padding: '1rem 2rem', fontSize: '1.125rem' },
  };

  const variantStyles = {
    primary: {
      background: 'var(--fralib-primary)',
      color: 'var(--fralib-accent-contrast)',
      border: 'none',
    },
    secondary: {
      background: 'transparent',
      color: 'var(--fralib-primary)',
      border: `2px solid var(--fralib-primary)`,
    },
    ghost: {
      background: 'transparent',
      color: 'var(--fralib-text-light)',
      border: 'none',
    },
  };

  const style = variantStyles[variant];
  const sizeStyle = sizes[size];

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 font-medium
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${loading ? 'opacity-70' : ''}
      `}
      style={{
        ...style,
        ...sizeStyle,
        fontFamily: tokens.headingFont,
        textTransform: tokens.headingCase === 'capitalize' ? undefined : tokens.headingCase,
        borderRadius: tokens.radius === '0px' ? 0 : tokens.radius,
        boxShadow: tokens.shadowButton,
        transition: `all ${tokens.motionSpeed} ${tokens.motionEase}`,
      }}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {!loading && icon && iconPosition === 'left' && icon}
      {children}
      {!loading && icon && iconPosition === 'right' && icon}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SECTION POLE - Seções com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function SectionPole({
  pole = 'corporate',
  children,
  variant = 'default', // default, dark, gradient, glass
  id,
  className = '',
}) {
  const tokens = usePoleTokens(pole);

  const variantStyles = {
    default: {
      background: 'var(--fralib-bg-dark)',
      color: 'var(--fralib-text-light)',
    },
    dark: {
      background: '#000000',
      color: 'var(--fralib-text-light)',
    },
    gradient: {
      background: 'linear-gradient(135deg, var(--fralib-bg-dark), var(--fralib-bg-surface))',
      color: 'var(--fralib-text-light)',
    },
    glass: {
      background: 'var(--pole-glass-bg, rgba(255,255,255,0.05))',
      backdropFilter: 'blur(12px)',
      color: 'var(--fralib-text-light)',
    },
  };

  const style = variantStyles[variant];

  return (
    <section
      id={id}
      className={`py-16 px-8 ${className}`}
      style={{
        ...style,
        marginTop: tokens.sectionOverlap !== '0px' ? tokens.sectionOverlap : undefined,
        transition: `all ${tokens.motionSpeed} ${tokens.motionEase}`,
      }}
    >
      <div className="max-w-7xl mx-auto">{children}</div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// GRID POLE - Grids com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function GridPole({
  pole = 'corporate',
  children,
  columns = 3, // 1, 2, 3, 4
  gap = 'medium', // small, medium, large
  variant = 'default', // default, overlap (para BOLD)
}) {
  const tokens = usePoleTokens(pole);

  const gapSizes = {
    small: '1rem',
    medium: '2rem',
    large: '3rem',
  };

  const colClasses = {
    1: 'grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 lg:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div
      className={`grid ${colClasses[columns]} ${variant === 'overlap' ? '-m-2' : ''}`}
      style={{
        gap: gapSizes[gap],
        marginTop: variant === 'overlap' ? tokens.sectionOverlap : undefined,
      }}
    >
      {React.Children.map(children, (child, index) => (
        <div
          key={index}
          style={{
            marginTop: variant === 'overlap' && index > 0 ? '-80px' : undefined,
            position: variant === 'overlap' ? 'relative' : undefined,
            zIndex: variant === 'overlap' && index > 0 ? 10 - index : undefined,
          }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// BADGE POLE - Badges com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function BadgePole({
  pole = 'corporate',
  children,
  variant = 'default', // default, outlined, ghost
  size = 'medium', // small, medium, large
}) {
  const tokens = usePoleTokens(pole);

  const sizes = {
    small: { padding: '0.125rem 0.5rem', fontSize: '0.75rem' },
    medium: { padding: '0.25rem 0.75rem', fontSize: '0.875rem' },
    large: { padding: '0.375rem 1rem', fontSize: '1rem' },
  };

  const variantStyles = {
    default: {
      background: 'var(--fralib-primary)',
      color: 'var(--fralib-accent-contrast)',
    },
    outlined: {
      background: 'transparent',
      color: 'var(--fralib-primary)',
      border: `1px solid var(--fralib-primary)`,
    },
    ghost: {
      background: 'var(--fralib-primary)/10',
      color: 'var(--fralib-primary)',
    },
  };

  const style = variantStyles[variant];
  const sizeStyle = sizes[size];

  return (
    <span
      className="inline-flex items-center font-medium"
      style={{
        ...style,
        ...sizeStyle,
        fontFamily: tokens.headingFont,
        textTransform: tokens.headingCase === 'capitalize' ? undefined : tokens.headingCase,
        borderRadius: tokens.radius === '0px' ? 0 : tokens.radius,
      }}
    >
      {children}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ANIMATED TEXT - Texto animado com tokens do polo
// ═══════════════════════════════════════════════════════════════════════════

export function AnimatedText({
  children,
  pole = 'corporate',
  animation = 'reveal', // reveal, typewriter, wave
  delay = 0,
}) {
  const [visible, setVisible] = useState(false);
  const ref = useRef(null);
  const tokens = usePoleTokens(pole);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, []);

  const animations = {
    reveal: {
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : 'translateY(20px)',
      transition: `opacity ${tokens.motionSpeed} ${tokens.motionEase}, transform ${tokens.motionSpeed} ${tokens.motionEase}`,
      transitionDelay: `${delay}ms`,
    },
    typewriter: {
      opacity: visible ? 1 : 0,
    },
    wave: {
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0) scale(1)' : 'translateY(10px) scale(0.95)',
      transition: `all ${tokens.motionSpeed} ${tokens.motionEase}`,
      transitionDelay: `${delay}ms`,
    },
  };

  return (
    <span
      ref={ref}
      style={{
        ...animations[animation],
        fontFamily: tokens.headingFont,
        display: 'inline-block',
      }}
    >
      {children}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT DEFAULT - PoleProvider
// ═══════════════════════════════════════════════════════════════════════════

export default {
  HeroPole,
  CardPole,
  ButtonPole,
  SectionPole,
  GridPole,
  BadgePole,
  AnimatedText,
  usePoleTokens,
};
