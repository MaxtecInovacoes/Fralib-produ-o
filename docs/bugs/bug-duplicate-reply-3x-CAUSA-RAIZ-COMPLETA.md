# Causa Raiz COMPLETA: Por que Franz responde 3x SEMPRE

## Resumo do Problema
Franz SDR está respondendo 3x à mesma mensagem do lead. O bug NUNCA é fixado porque a causa raiz é **race condition em memória compartilhada** que afeta TODAS as camadas do sistema.

## Causa Raiz PRIMÁRIA: Race Condition em Memória

### 1. **Concorrência Não Controlada no Entry Point**
**Arquivo**: `backend/agents/sdr_langgraph/compat.py:203` (função `responder_lead`)

**Cenário**:
1. 2 threads/processos chamam `responder_lead()` simultaneamente pra mesma lead
2. Ambas carregam a mesma memória Redis (stage=hook)
3. Ambas processam a mesma mensagem de lead
4. Ambas geram a mesma resposta opt-out
5. Ambas salvam memória (sobrescrevendo a mesma chave Redis)
6. Ambas enviam a resposta pro WhatsApp

**Código problemático**:
```python
# compat.py:203-225
def responder_lead(...):
    # Thread 1 e Thread 2 entram aqui
    session_id = f"franz_lead_{telefone}"
    memoria = carregar_memoria(session_id, user_id=user_id)  # Mesmo estado lido
    # ...
    result = graph.invoke(initial_state)  # 2x processamento concorrente
    # ...
    salvar_memoria(session_id, memory.model_dump(), user_id=user_id)  # 2x save
```

### 2. **Deduplicação Ineficiente no Grafo**
**Arquivo**: `backend/agents/sdr_langgraph/agent.py:1278-1330`

**Problema**: O `save_and_send` lê o reply 2x:
- Linha 1202: `reply = state.get("proposed_reply", "")`
- Linha 1278: `reply = state.get("proposed_reply", "")`

Entre essas linhas, o humanization modifica o reply mas só atualiza `state["proposed_reply"]`. Se 2 threads estiverem no mesmo node, uma pode ler o reply modificado pela outra.

### 3. **WebSocket Race Condition (MeoWhats)**
**Arquivo**: `backend/whatsapp_listener.py:244-329`

**Problema**: O `_debounce_incoming` não usa o `key.id` do WhatsApp para deduplicação:
```python
key_data = msg_data.get("key", {})
jid = key_data.get("remoteJid", "")
# NÃO usa: msg_id = key_data.get("id", "")
```

Se o MeoWhats enviar 2 msgs com mesmo `key.id` em 4ms, o debounce cria 2 timers separados.

### 4. **Memory Save/Load Race**
**Arquivo**: `backend/agents/sdr_langgraph/compat.py:254-262`

**Problema**: O dedup de history usa chave fraca:
```python
key = f"{item.get('role')}:{item.get('content', '')[:50]}"
```

Se 2 respostas "Entendido!" forem geradas, mas com prefixos diferentes (ex: "Entendido! Vou remover" vs "Entendido! Removido 👍"), viram entradas distintas.

### 5. **FSM State Machine Loop**
**Arquivo**: `backend/agents/sdr_langgraph/agent.py:1190-1346`

**Problema**: O `save_and_send` node:
- Lê `reply` em 2 lugares diferentes (linhas 1202 e 1278)
- Modifica state entre as leituras
- Não tem atomicidade entre leitura/modificação/gravação

## Solução COMPLETA (Não Parcial)

### 1. **Lock por Lead ID** (Prioridade: CRÍTICA)
```python
# backend/agents/sdr_langgraph/compat.py
import threading
from contextlib import contextmanager

# Global lock registry por lead_id
_LEAD_LOCKS: Dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()

@contextmanager
def _lead_lock_guard(lead_id: str):
    with _LOCK_GUARD:
        if lead_id not in _LEAD_LOCKS:
            _LEAD_LOCKS[lead_id] = threading.Lock()
        lock = _LEAD_LOCKS[lead_id]
    with lock:
        yield

def responder_lead(...):
    with _lead_lock_guard(lead_id):
        # Toda a função dentro do lock
        session_id = f"franz_lead_{telefone}"
        memoria = carregar_memoria(session_id, user_id=user_id)
        result = graph.invoke(initial_state)
        # ...
```

### 2. **Deduplicação por Message ID**
```python
# backend/whatsapp_listener.py:244
def _debounce_incoming(tenant_id: str, msg_data: dict, executor, loop):
    key_data = msg_data.get("key", {})
    msg_id = key_data.get("id", "")
    jid = key_data.get("remoteJid", "")
    
    # Cache global de message_ids processados nos últimos 60s
    if msg_id and _is_duplicate_message_id(msg_id):
        return
    
    # Restante do código...

def _is_duplicate_message_id(msg_id: str) -> bool:
    # Implementar cache com TTL de 60s
    pass
```

### 3. **Atomicidade no Save/Send**
```python
# backend/agents/sdr_langgraph/agent.py
@sdr_traced("node_save_and_send")
def node_save_and_send(state: SDRState) -> dict:
    # Ler reply UMA vez no início
    reply = state.get("proposed_reply", "") or state.get("draft", "")
    
    # Processar todo o fluxo com a mesma variável
    if reply:
        # site_offer, simplify_language, quality_judge
        # humanization - tudo modifica a mesma variável reply
        pass
    
    # No final, escrever DEPOIS de tudo processado
    state["proposed_reply"] = reply
    state["send_delay_seconds"] = delay.seconds
    
    return {}
```

### 4. **Redis Distributed Lock** (Para multi-processo)
Se houver múltiplos workers, usar Redis com `SET lead_lock ... NX PX 30000`

### 5. **Idempotência no Envio**
```python
# backend/whatsapp/response_executor.py
def send_response(ctx: ExecutionContext):
    # Gerar hash da resposta ANTES de enviar
    reply_hash = hashlib.sha256(ctx.resposta.encode()).hexdigest()[:16]
    
    # Checar se já foi enviada nos últimos 5min
    if _was_reply_sent_recently(ctx.lead_id, reply_hash):
        return False
    
    # Enviar e marcar como enviada
    _mark_reply_sent(ctx.lead_id, reply_hash)
    # ... enviar via MeoWhats
```

## Por que o Bug SEMPRE Volta

1. **O debounce só agrupa por lead_key, não por message_id**
2. **O compat.py não tem locks - é thread-unsafe por design**
3. **O LangGraph state é compartilhado entre threads sem proteção**
4. **O Redis memory é lido/escrito sem atomicidade**
5. **O MeoWhats pode reenviar msgs não-ack'd em reconexão**

## Implementação Necessária

1. **Lock global por lead_id** no entry point (`compat.py`)
2. **Deduplicação por message_id** no listener (`whatsapp_listener.py`)
3. **Atomicidade no save/send** no grafo (`agent.py`)
4. **Idempotência no envio** no executor (`response_executor.py`)
5. **Testes de concorrência** com 2 threads/processos simultâneos

## Verificação

```bash
# Teste 1: Simular 2 threads chamando responder_lead() pro mesmo lead
# Deve retornar só 1 resposta

# Teste 2: Enviar mesma msg 2x rapidamente via WhatsApp
# Deve processar só 1

# Teste 3: Rodar com 2 workers fralib-franz
# Deve deduplicar automaticamente
```

## Conclusão

O bug SEMPRE volta porque a solução parcial (só dedup no listener) não resolve o problema raiz: **concorrência não controlada no entry point**. Sem locks por lead_id, qualquer thread/processo pode processar a mesma mensagem simultaneamente.