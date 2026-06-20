# Fix Report: PERF_001.2 - N+1 Query em registrar_feedback

## Problema
**Arquivo:** `backend/endpoints/leads_crud_sdr.py`
**Severidade:** CRITICO
**Impacto:** 2 queries round-trip → 1 query

## Antes (2 queries)
```python
lead = db.execute(text("SELECT id, segmento, tier, telefone FROM leads WHERE ...")).fetchone()
ultima_msg = db.execute(text("SELECT i.mensagem FROM interacoes i JOIN leads l ...")).fetchone()
```

## Depois (1 query com LEFT JOIN)
```python
dados = db.execute(text("""
    SELECT
        l.id, l.segmento, l.tier, l.telefone,
        sub.mensagem_usada
    FROM leads l
    LEFT JOIN (
        SELECT lead_id, mensagem AS mensagem_usada
        FROM interacoes
        WHERE lead_id = :lead_id AND direcao = 'saida'
        ORDER BY id DESC LIMIT 1
    ) sub ON sub.lead_id = l.id
    WHERE l.id = :lead_id AND l.user_id = :uid
""")).fetchone()
```

## Métricas
| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Queries por request | 2 | 1 | -50% |
| Latência estimada | ~20ms | ~10ms | -50% |

## Status
✅ CORRIGIDO
