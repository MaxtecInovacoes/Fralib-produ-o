## Context

FraLib already has the Phase 6 site contract, deployment hook, smoke preflight and security hardening in the repo, but two local host limits were still being treated as blockers: this Windows host has no Docker CLI, and local Postgres on `localhost:5433` is not running. The production-like services exist on the VPS, so runtime validation must run there through SSH while preserving the AGENTS.md rule that forbids SCP, rsync and direct file edits.

The Aibee/API outage also blocks a full LLM-backed Builder run. The practical validation path is an offline Builder run with `FRALIB_VITE_FORCE_LOCAL_FALLBACK=1`, using the real `render_site_with_builder` pipeline and then auditing the produced `dist/index.html`.

Authentication has two larger hardening items that are intentionally not bundled into the publication fix: mandatory TOTP enforcement and migration from localStorage bearer tokens to HttpOnly cookies plus CSRF. They need a rollout spec because frontend scripts and existing API clients still depend on bearer-token compatibility.

## Goals / Non-Goals

**Goals:**

- Make OpenSpec the repo-local planning record for runtime, auth and offline Builder contracts.
- Validate Docker Compose and smoke on the VPS when local Windows lacks Docker/Postgres.
- Prove the Builder can generate and publish a site without Aibee while keeping Phase 6 markers, pt-BR language, SEO keywords, schemas, GSAP/Lenis, theme toggle and hero video/image decisions.
- Fix publication repair so a Vite shell `dist/index.html` does not lose critical SEO/Fase 6 contracts.
- Keep current security hardening from breaking the smoke or published site path.

**Non-Goals:**

- Do not implement full 2FA enrollment/enforcement in this change.
- Do not remove all frontend `localStorage` token usage in this change.
- Do not use SCP, rsync or manual VPS edits.
- Do not claim Aibee-backed generation is healthy while the provider API is unavailable.

## Decisions

1. Use VPS as the authoritative runtime validator for Docker/Postgres.

   Local Docker/Postgres failures on this host are environment gaps, not product failures. The VPS owns Docker Compose, Postgres 5433, PM2 and smoke ports, so `docker compose config --quiet` and `python3 pipeline.py smoke --dry-run` are the correct proofs.

2. Keep Builder offline validation inside the real Builder service.

   A mocked HTML fixture would miss publication bugs. The offline test must call `render_site_with_builder`, force the local fallback model and inspect the resulting `dist/index.html`.

3. Repair publication contracts at the HTML gate boundary.

   Vite/React output can be a shell whose visible React tree is in bundled JS. The publication sanitizer must materialize deterministic head/body contracts in the delivered HTML: title, description, keywords, hero type, Pexels video when appropriate, T6 scramble, cursor DOM, grain SVG, GSAP/Lenis and theme toggle.

4. Treat auth cookie/2FA as a separate implementation rollout.

   The safer path is to specify cookie/CSRF and TOTP behavior now, then implement with backward-compatible bearer-token support and focused frontend migration. Shipping that together with publication fixes would increase blast radius.

## Risks / Trade-offs

- Vite shell repair can add deterministic fallback markup before React mounts -> Keep fallback limited to contract-critical elements and validate with Phase 6 contract tests.
- VPS validation depends on SSH access -> Use read-only/status commands plus repo-deployed code; no manual file mutation.
- Auth migration can break active sessions -> Require dual-read bearer/cookie phase before localStorage removal.
- Offline fallback is not equivalent to Aibee creativity -> Use it only to prove contracts, not final visual quality from the LLM provider.

## Migration Plan

1. Commit OpenSpec artifacts and publication sanitizer fixes.
2. Run local unit contracts and offline Builder generation with API disabled.
3. Push through the official git flow and let the VPS deploy hook publish.
4. Validate `/api/version`, `/llms.txt`, Docker Compose config and smoke on the VPS.
5. Keep auth-session-hardening as an OpenSpec capability for the next implementation change.
