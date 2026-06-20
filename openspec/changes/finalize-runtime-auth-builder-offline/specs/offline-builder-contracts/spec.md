## ADDED Requirements

### Requirement: Offline Builder test uses the real render pipeline
FraLib SHALL validate no-API site generation by calling `render_site_with_builder` with local fallback enabled, not by checking a static fixture.

#### Scenario: Offline render writes a Vite dist artifact
- **WHEN** `FRALIB_VITE_FORCE_LOCAL_FALLBACK=1` is set and the test renders a tenant 2 lead
- **THEN** the pipeline writes a real `dist/index.html` through the Builder service

### Requirement: Published HTML preserves language and SEO contracts
FraLib SHALL publish offline Builder output with `lang="pt-BR"`, no CJK visible characters, factual title/description and meta keywords derived from the prompt-agent SEO terms.

#### Scenario: SEO keywords appear in the generated site
- **WHEN** the lead includes `seo_keywords` or prompt-agent `seo.primary_terms`
- **THEN** the published `dist/index.html` contains `meta name="keywords"` and the requested local keyword terms

#### Scenario: Language remains Portuguese
- **WHEN** the offline Builder publishes HTML for a Brazilian lead
- **THEN** the document declares `pt-BR` and does not contain Chinese CJK characters

### Requirement: Phase 6 contracts survive Vite shell publication
FraLib SHALL materialize Phase 6 markers in the delivered `dist/index.html` even when the Builder output is a Vite/React shell.

#### Scenario: Academia lead gets video hero contract
- **WHEN** an academia lead has a Pexels video asset
- **THEN** the published HTML contains `data-hero-type="video"`, a Pexels video tag with autoplay, muted, loop and playsinline, and a Pexels preconnect

#### Scenario: Motion and theme contracts are present
- **WHEN** the offline Builder publishes HTML
- **THEN** the document contains GSAP, ScrollTrigger, Lenis, `gsap.registerPlugin`, theme toggle, `data-theme`, cursor DOM, grain SVG and T6 text scramble markers

### Requirement: Offline Builder contract failures block completion
FraLib SHALL treat missing Phase 6, SEO, language or motion markers in the offline Builder output as a blocking failure.

#### Scenario: Contract audit fails
- **WHEN** `_phase6_contract_problems` reports any issue or offline checks miss required SEO/language markers
- **THEN** the task is not considered complete until the root cause is fixed and the offline render passes
