## 1. OpenSpec Baseline

- [x] 1.1 Initialize repo-local OpenSpec files for Codex.
- [x] 1.2 Create proposal, design and capability specs for runtime validation, auth-session hardening and offline Builder contracts.
- [x] 1.3 Keep TOTP enforcement and HttpOnly cookie migration scoped as a follow-up implementation, not bundled into publication fixes.

## 2. Runtime Validation

- [x] 2.1 Validate Docker Compose config on the VPS because the Windows host has no Docker CLI.
- [x] 2.2 Validate `pipeline.py smoke --dry-run` on the VPS because the Windows host has no local Postgres 5433.
- [x] 2.3 Confirm smoke remains no-API, no-token and no-deploy.
- [x] 2.4 Confirm public `/llms.txt` and deployed version health stay available.

## 3. Offline Builder Contract

- [x] 3.1 Run a no-API tenant 2 Builder render with `FRALIB_VITE_FORCE_LOCAL_FALLBACK=1`.
- [x] 3.2 Reproduce the contract gap in the Vite shell publication output.
- [x] 3.3 Fix publication repair for hero video decision, T6 scramble, SEO keywords, title/description, cursor DOM and grain SVG.
- [x] 3.4 Add a unit regression test for Vite shell publication contracts.
- [x] 3.5 Re-run the offline tenant 2 Builder render and verify pt-BR, no CJK, SEO keywords, schemas, GSAP/Lenis, theme toggle, Pexels hero video and Phase 6 markers.

## 4. Release Validation

- [x] 4.1 Run focused unit tests for Builder, Phase 6 and publication security contracts.
- [x] 4.2 Run OpenSpec validation for `finalize-runtime-auth-builder-offline`.
- [x] 4.3 Review `git diff` and keep unrelated worktree files unstaged.
- [x] 4.4 Update AGENTS.md without exceeding 80 lines.
- [x] 4.5 Commit, push through the official git flow and validate the VPS after deployment.
