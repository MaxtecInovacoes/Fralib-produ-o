# Design

## Runtime Guard
`vite_react_renderer` must fail closed when all LLM attempts fail. Local fallback can remain available only behind an explicit environment flag for manual development/testing.

## Semantic Quality Gate
Before writing/building the generated Vite project, validate the source against:
- confirmed business name and phone,
- segment-specific terms for known segments,
- banned generic fallback phrases,
- banned cross-segment terms for academia/nutricionista/barbearia and related niches.

The gate should produce actionable `ViteReactRenderError` messages so the retry loop can ask the LLM to repair output. If all attempts fail, the pipeline fails instead of publishing a wrong site.

## Prompt Hygiene
The Builder system prompt must not provide barber-specific fallback images as universal media. It should require provided media first, then segment-compatible editorial media only when no media exists.

## SDR Safety
Pipeline failure must prevent `franz_outreach` enqueueing. Existing bad leads can be quarantined operationally with a non-sendable `sdr_stage`.

## Validation
- Unit tests for generic fallback phrase rejection.
- Unit tests for academia rejecting barber copy and requiring fitness terms.
- Unit tests for nutricionista rejecting barber/fitness contamination and requiring nutrition terms.
- Live tenant 2 smoke after deploy: Builder should use LLM tokens and output segment-specific pages.
