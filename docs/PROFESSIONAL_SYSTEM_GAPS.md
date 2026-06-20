# Professional System Gaps

This is the working gap register for turning FraLib into a professional SaaS
that a new operator or AI can understand and operate safely.

## P0 Before Broad Sales

1. Prove Mercado Pago webhook and reconciliation with multiple payment methods.
2. Keep payment idempotency tests green.
3. Finish cookie-only auth migration and remove normal localStorage token use.
4. Add full 2FA setup with QR and backup codes before requiring 2FA broadly.
5. Keep `FRALIB_ENV=prod`, Redis and secure cookies validated after deploy.
6. Add automated post-deploy canary for login, dashboard, plans and credits.
7. Add a user-visible payment status page/history.
8. Add a support/operator payment lookup flow without exposing secrets.
9. Add cross-tenant tests for every new endpoint touching leads/jobs/sites.
10. Add queue stuck alerts and operator runbook links in admin.

## P1 Reliability

11. Keep Hermes read-only snapshot collector covered by tests.
12. Keep incident log/table with severity and evidence covered by tests.
13. Keep watchdog denylist/allowlist tests in release gate.
14. Expand automated stuck-job detection dashboard with trend history.
15. Add p50/p95 phase timing by plan and tenant.
16. Add failure budgets for Builder/provider phases.
17. Add circuit breaker visibility in admin.
18. Add safer provider failover policy docs and tests.
19. Add runbook for restoring from database backup.
20. Add runbook for deploy rollback through Git.

## P1 Product Experience

21. Complete first-login tour for every critical user role.
22. Add empty states for no credits, no leads, WhatsApp disconnected and queue
    busy.
23. Add plan comparison inside dashboard, not only landing.
24. Add clear renewal/subscription management page.
25. Add credit purchase receipt and invoice reference.
26. Add failed payment recovery emails/messages.
27. Add visible cooldown timer before next generation.
28. Add trial progress indicator: lead captured, site ready, WhatsApp sent.
29. Add site generation history with status and public URL.
30. Add user-facing explanation when a lead is blocked by plan.

## P1 Security

31. Remove Bearer compatibility after cookie migration is proven.
32. Add CSP cleanup to remove unnecessary inline script allowances.
33. Add SRI or self-hosting strategy for critical CDNs.
34. Rotate any secret that was ever pasted in chat or screenshots.
35. Add automated secret scanning in pre-release gate.
36. Add RLS evaluation/spec for PostgreSQL or stronger repository guards.
37. Add audit trail for admin/superadmin actions.
38. Add IP/device/session management page.
39. Add lockout/rate-limit telemetry for auth.
40. Add backup-code flow for 2FA.

## P2 Scale

41. Benchmark worker throughput with 2, 4 and 8 workers.
42. Define target `MAX_PIPELINES_GLOBAL` by VPS resources.
43. Add queue priority dashboard by plan.
44. Add per-tenant concurrency caps.
45. Add lead supply precompute for high-volume niches.
46. Add provider pool/key capacity report.
47. Add cost forecast per 100 generated sites.
48. Add archival policy for old generated artifacts.
49. Add Postgres index audit for hot queries.
50. Add storage growth dashboard.

## P2 Documentation

51. Add generated file inventory for all tracked files.
52. Add database schema dictionary.
53. Add API endpoint catalog with auth/tenant rules.
54. Add frontend route catalog.
55. Add environment variable catalog with secret/public classification.
56. Add test matrix by capability.
57. Add release checklist.
58. Add incident postmortem template.
59. Add onboarding checklist for support agents.
60. Add architecture decision records for major choices.

## P2 Quality

61. Add visual regression screenshots for landing/admin.
62. Add generated-site contract screenshots for top niches.
63. Add offline Builder fixture library.
64. Add payment webhook replay fixtures.
65. Add WhatsApp bridge simulator tests.
66. Add load test for queue/status polling.
67. Add smoke that validates `/llms.txt` and legal pages publicly.
68. Add browser test for credit popup when balance is zero.
69. Add browser test for first-login tour.
70. Add browser test for plan upgrade/downgrade UX.

## P3 Operations

71. Add runbook for provider outage.
72. Add runbook for WhatsApp reconnection.
73. Add runbook for Mercado Pago dispute/chargeback.
74. Add runbook for tenant data export/deletion LGPD.
75. Add runbook for compromised admin account.
76. Add runbook for accidental deploy regression.
77. Add monthly dependency update routine.
78. Add quarterly security review.
79. Add uptime/status page.
80. Add customer-facing changelog.

## P3 Architecture

81. Split remaining large endpoint modules by responsibility.
82. Add repository/service layer for critical SQL.
83. Move long-running orchestration fully out of HTTP paths.
84. Evaluate managed queue when Postgres queue hits measured limits.
85. Add template-first Builder mode for cost/latency reduction.
86. Add cache/DNA policy by niche and city cluster.
87. Add domain event model for payment/credit/plan changes.
88. Add typed contracts for pipeline phase inputs/outputs.
89. Add explicit deprecation registry for legacy files.
90. Add dependency graph documentation.

## P3 Business Controls

91. Add admin plan override audit.
92. Add refund workflow with Mercado Pago event correlation.
93. Add abuse detection for repeated free trials.
94. Add quota policy for Agency subaccounts.
95. Add terms/privacy re-acceptance flow on version changes.
96. Add customer data retention policy enforcement.
97. Add support escalation labels by severity.
98. Add billing dunning policy.
99. Add customer success health score.
100. Add launch readiness scorecard.
