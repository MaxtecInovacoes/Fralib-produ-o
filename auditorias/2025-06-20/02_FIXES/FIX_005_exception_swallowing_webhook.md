# FIX_005 - Corrigir Exception Swallowing no Webhook Credits

## PROBLEMA
**Local:** `backend/endpoints/credits_endpoints.py:541-550`

**Descrição:**
O webhook do MercadoPago usa `except Exception` genérico que captura TODAS as exceções, incluindo `HTTPException` do FastAPI. Isso faz com que erros HTTP 400 sejam "engolidos" e retornados como `{"status": "erro_logado"}` em vez de respostas HTTP de erro.

**Impacto:**
- Erros 400 de APIs internas (payment_id ausente, preapproval_id ausente) são silenciados
- MercadoPago recebe resposta 200 OK mesmo quando webhook falha internamente
- Webhook não é retentado pelo MercadoPago quando há falha real

## ANTES (Código Problemático)
```python
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
        print(f"[MercadoPago webhook] FALHA em {tipo} ({event_id}): {err_msg}")
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE mercadopago_events SET erro=:err WHERE event_id=:e"),
                {"e": event_id, "err": err_msg},
            )
            conn.commit()
        return {"status": "erro_logado", "tipo": tipo or "payment", "erro": err_msg}
```

## DEPOIS (Correção)
```python
    except HTTPException:
        raise  # Re-raise HTTPException para resposta correta ao MercadoPago
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
        print(f"[MercadoPago webhook] FALHA em {tipo} ({event_id}): {err_msg}")
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE mercadopago_events SET erro=:err WHERE event_id=:e"),
                {"e": event_id, "err": err_msg},
            )
            conn.commit()
        raise HTTPException(500, f"Falha no processamento: {err_msg}")
```

## TESTE
```bash
ruff check backend/endpoints/credits_endpoints.py
# Result: All checks passed!
```

## COMMIT
```
fix: corrige exception swallowing no webhook MercadoPago

Re-raise HTTPException para garantir que erros 400/500 sejam
retornados corretamente ao MercadoPago, permitindo retries.
```
