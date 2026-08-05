# Estado Atual — FraLib OS
> Atualizado: 2026-05-08

## Status Geral
- Backend (Sprint 1): COMPLETO
- Frontend (Sprint 2): QUASE COMPLETO (falta design-tokens.css)
- Inteligência (Sprint 3): COMPLETO
- Pagamento/Onboarding: PENDENTE (decisão Stripe vs Mercado Pago)

## Pipeline de Agentes
Ordem: Hunter → Caio+Alex (paralelo) → Jina → Theo → Arquiteto → Liam → Liz → Deploy → Franz

Todos os 7 fixes aplicados e funcionando. Reprocessar implementado.

Pendente testar: Liam + Liz + Deploy + Franz no reprocessar.

## Pendências Abertas
1. Testar pipeline reprocessar completo (Liam/Liz/Deploy/Franz)
2. Refatorar alex.py (1028 linhas, acima do limite 800)
3. Criar design-tokens.css (Sprint 2.7)
4. Fluxo de pagamento (Stripe vs Mercado Pago — decidir)
5. Alinhamento landing page / planos
6. Franz SDR: estado sempre "intro" — nunca avança na state machine
7. SSE logs: trocar deque por PostgreSQL LISTEN/NOTIFY

## Melhorias de Performance Identificadas
- Liam paralelo por seção: reduziria tempo de 5min para ~1min
- Arquiteto: trocar Opus por Sonnet (mais rápido, mesmo resultado)
- Hunter assíncrono: requests paralelos no Google Maps

## Infraestrutura
- VPS: 187.77.37.72 | PM2: fralib (id 0)
- PostgreSQL: porta 5433, DB fralib_db
- Nginx: sempre 127.0.0.1 (nunca localhost)
- WhatsApp: meowhats WebSocket porta 3001
- Produção: https://seunegociofralib.site

## Como Retomar
Diga "lê o estado atual" no início de qualquer sessão fralib.
Arquivo: /root/fralib/docs/ESTADO_ATUAL.md
