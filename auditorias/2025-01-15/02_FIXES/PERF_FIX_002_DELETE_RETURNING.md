# Fix Report: PERF_001.5 - SELECT + DELETE Redundante

## Problema
**Arquivo:** `backend/endpoints/leads_crud.py`
**Severidade:** MEDIO
**Impacto:** 3 queries → 2 queries

## Antes (3 queries)
```python
lead = db.execute(text("SELECT id FROM leads WHERE ...")).fetchone()  # Query 1
if not lead: raise 404
db.execute(text("DELETE FROM interacoes WHERE lead_id IN (SELECT id FROM leads WHERE ...)"))  # Query 2
db.execute(text("DELETE FROM leads WHERE ..."))  # Query 3
```

## Depois (2 queries com RETURNING)
```python
deleted = db.execute(text("""
    DELETE FROM leads WHERE id = :lead_id AND user_id = :uid RETURNING id
""")).fetchone()
if not deleted: raise 404
db.execute(text("DELETE FROM interacoes WHERE lead_id = :lead_id"))  # Query 2
```

## Métricas
| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Queries por delete | 3 | 2 | -33% |
| Latência estimada | ~15ms | ~10ms | -33% |

## Status
✅ CORRIGIDO
