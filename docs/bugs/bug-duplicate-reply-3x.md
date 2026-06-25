# Causa Raiz do Bug: SDR Respondendo 3x Mensagens

## Resumo do Problema
Franz SDR está respondendo 3x à mesma mensagem do lead, como mostrado na captura de tela onde ele enviou "Entendido! Vou remover seu contato agora..." 3x para o mesmo lead.

## Causa Raiz Identificada

### 1. **Webhook Race Condition** (Fonte: MeoWhats)
- O MeoWhats está entregando a mesma mensagem 2x via webhook em rápida sucessão (4ms de diferença)
- Isso acontece porque o WhatsApp Web pode enviar duplicatas em casos de race condition

### 2. **Debounce Ineficiente** 
- O `_debounce_incoming()` acumula mensagens do mesmo lead por 4s antes de processar
- MAS: se o webhook entrega 2 msgs rápidas, o debounce cria 2 timers separados
- Resultado: 2 processamentos diferentes para a mesma mensagem

### 3. `is_duplicate_reply` Frágil
- Usa comparação de substring: `reply.strip() in last_bot_msg`
- Exemplo: "Entendido! Vou remover seu contato agora" contém "Entendido!" → considera duplicado
- MAS: se o LLM gerar variações (ex: "Entendido! Vou remover agora..."), a detecção falha

### 4. `sanitize_reply` Incompleto
- Só lida com campo `"resposta"` (PT), não com `"reply"` (EN)
- Quando o LLM retorna JSON com `"reply"`, a limpeza falha
- Resulta em JSON cru sendo enviado para o lead

## Fluxo do Bug

```
WhatsApp Lead → MeoWhats → Webhook Race → 2x msg rápida → 
↓
Debounce cria 2 timers → 2x _processar_mensagem_batch → 
↓
2x Franz → 2x resposta → is_duplicate_reply falha → 
↓
2x envio para lead
```

## Solução Proposta

### 1. **Deduplicação por Message ID** (Prioridade: ALTA)
- Extrair `key.id` do webhook JSON
- Armazenar IDs processados nos últimos 60s
- Ignorar mensagens com ID já visto

### 2. **Melhorar `is_duplicate_reply`**
- Usar hash SHA256 do conteúdo
- Comparar exatamente igual (não substring)
- Limiar de similaridade: 95% (não 55%)

### 3. **Fixar `sanitize_reply`**
- Adicionar suporte a campo `"reply"` (EN)
- Mesmo tratamento que `"resposta"`

### 4. **Testes Unitários**
- Criar classe `TestDuplicateDetection` com 15 casos
- Cobrir: race, variações, JSON malformado, campos mistos

## Código a Modificar

### `backend/whatsapp_listener.py:244`
```python
def _debounce_incoming(tenant_id: str, msg_data: dict, executor, loop):
    # Extrair message ID do WhatsApp
    key_data = msg_data.get("key", {})
    msg_id = key_data.get("id", "")
    jid = key_data.get("remoteJid", "")
    
    # Ignorar se já processamos este ID nos últimos 60s
    if msg_id and _is_duplicate_message_id(msg_id):
        print(f"[WPP-Listener] Mensagem duplicada por ID: {msg_id[:16]}... ignorada")
        return
```

### `backend/whatsapp/sdr_reply_service.py:145`
```python
def is_duplicate_reply(history, reply: str) -> bool:
    try:
        # Usar hash exato em vez de substring
        reply_hash = hashlib.sha256(reply.strip().encode()).hexdigest()[:16]
        last_bot_msg = next(
            (
                (item.get("content") or "").strip()
                for item in reversed(history or [])
                if item.get("role") == "assistant" and (item.get("content") or "").strip()
            ),
            "",
        )
        if last_bot_msg:
            last_hash = hashlib.sha256(last_bot_msg.encode()).hexdigest()[:16]
            return reply_hash == last_hash
        return False
    except Exception:
        return False
```

### `backend/whatsapp/sdr_reply_service.py:109`
```python
def sanitize_reply(reply: str, retry_extractor=None, fallback_reply="Opa, tudo bem? Me dá um minuto que já te respondo! 👍"):
    resposta = reply or ""
    if not resposta.strip():
        return resposta

    # Suportar ambos os campos: "resposta" (PT) e "reply" (EN)
    if (resposta.strip().startswith("{") or 
        '"resposta"' in resposta or 
        '"novo_stage"' in resposta or
        '"reply"' in resposta):
        
        # Tentar extrair de "resposta" primeiro (PT)
        resp_match = re.search(r'"resposta"\s*:\s*"((?:[^"\\]|\\.)*)"', resposta)
        if resp_match:
            resposta = resp_match.group(1).replace('\\"', '"').replace("\\n", "\n")
        else:
            # Tentar extrair de "reply" (EN)
            reply_match = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', resposta)
            if reply_match:
                resposta = reply_match.group(1).replace('\\"', '"').replace("\\n", "\n")
            else:
                # Fallback: remover JSON
                resposta = re.sub(r"\{[\s\S]*?\}", "", resposta).strip()
                resposta = re.sub(r"```[\s\S]*?```", "", resposta).strip()
```

## Implementação
1. Criar função `_is_duplicate_message_id()` com cache de 60s
2. Modificar `_debounce_incoming` para checar message ID
3. Atualizar `is_duplicate_reply` para usar hash
4. Fixar `sanitize_reply` para campo "reply"
5. Adicionar testes unitários
6. Commit como `fix(sdr): deduplica mensagem por message.id do WhatsApp`
7. Deploy na VPS

## Verificação
- Enviar mensagem de teste via WhatsApp
- Verificar que só 1 resposta é enviada
- Checar logs: "Mensagem duplicada por ID" se ocorrer race