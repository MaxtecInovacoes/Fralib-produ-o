# Prevent Generic Builder Publication

## Summary
Block production publication and SDR outreach when the Builder falls back to a generic local template or produces a site whose visual/content signals do not match the lead segment.

## Problem
Tenant 2 published multiple recent sites with the same dark editorial/barbershop visual system despite different segments such as academia and nutricionista. The database shows zero LLM tokens for those runs, which means the local fallback rendered and passed as a successful site. Franz outreach then ran against those bad artifacts.

## Goals
- Do not publish local fallback output in production unless explicitly enabled for a controlled test.
- Reject Builder source that contains known generic fallback phrases or cross-segment visual contamination.
- Require segment/subsegment-specific language in the React source before build publication.
- Keep SDR/Franz blocked when site quality fails, so no WhatsApp is sent for broken or wrong-niche pages.

## Non-Goals
- Rewriting the whole Builder pipeline.
- Re-enabling Ollama/Open WebUI.
- Deleting historical interaction records.

## Evidence
- `pipeline_token_usage` for affected runs had zero input/output tokens.
- Published artifacts contained `FraLib Studio`, fixed barber-style imagery and repeated generic copy.
- `franz_outreach` jobs for the affected leads completed after publication.
