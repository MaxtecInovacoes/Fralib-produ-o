"""
FraLib scripts package.

Key reconciliation and fix scripts (idempotent, --apply for mutations):
- fix_one_truth_mirror.py       — corrige espelhos users.plan e leads.pipeline_stage
- fix_job_577_ledger.py          — consolida tokens/custo do Job 577 do ledger canonico
- reconcile_one_truth.py         — reconcilia estados divergentes com fonte canônica

For audit and monitoring:
- audit_one_truth.py            — audit read-only do estado canônico vs. espelhos
- pipeline_smoke.py              — smoke tests locais (dry-run)
- hermes_watchdog.py            — Hermes auto-remediation watchdog

Always run with --dry-run (or without --apply) first to see the plan.
"""
