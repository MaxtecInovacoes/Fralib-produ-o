# Inventário dos try/except no pipeline_orchestrator_service.py

E1 do plano 2026-07-02.

| Linha | Contexto | Ação atual | Ação desejada |
|-------|----------|------------|---------------|
| 188 | checkpoint agent_state | silencioso | raise |
| 355 | parse_briefing | raise (já correto) | OK |
| 371 | TokenTracker setup | silencioso | warning + continuar |
| 382 | pipeline_ledger setup | silencioso | warning + continuar |
| 397 | AgentRouter setup | silencioso | warning + continuar |
| 423 | validador LLM setup | silencioso | warning + continuar |
| 498 | JSONDecodeError | raise | OK |
| 567 | Jina call | silencioso | retry 3x |
| 593 | salvamento debug | logger.warning | OK |
| 636 | keyword research | warning | OK |
| 746 | salvamento check | warning | OK |
| 1035 | StopIteration | silencioso | warning |
| 1037 | dup check | silencioso | warning + raise |
| 1102 | JSON decode | silencioso | raise |
| 1117 | fallback_err | silencioso | warning + raise |
| 1385 | _e_sub | silencioso | raise |
| 1453 | _dd_err (DesignDirector) | warning | retry 3x já aplicado (A3) |
| 1479 | _router_err | warning | OK |
| 1489 | AgentConfig | silencioso | warning + continuar |
| 1518 | _intel_err | warning | OK |
| 1584 | checkpoint Nicho | silencioso | raise |
| 1612 | Nicho briefing LLM | silencioso | raise |
| 1674 | checkpoint Variacao | silencioso | warning |
| 1698 | Variacao briefing | silencioso | raise |
| 1763 | _prd_err | warning | OK |

Total: ~18 try/except com `except Exception` que precisa revisão.

**Ação geral**: Trocar `except Exception: pass` por `logger.exception("...contexto..."); raise` para que erros propaguem.
Para erros esperados/transientes (DB, rede, I/O): trocar por `tentar(fn, max_retries=3)`.
Para erros de configuração que devem silenciar: manter warning + log detalhado.