# 📊 Análise: Arquitetura de Múltiplas API Keys

## 🔍 Situação Atual

### Status das Chaves:
| Provider | Status | Valor/1K tokens |
|----------|--------|-----------------|
| **LITELLM_API_KEY** (.env) | ❌ INVÁLIDA | - |
| **ANTHROPIC_API_KEY** (.env) | ❌ INVÁLIDA | - |
| **provider_keys.google** (DB) | ❌ DESABILITADA | - |
| **provider_keys.groq** (DB) | ❌ DESABILITADA | - |
| **provider_keys.openrouter** (DB) | ⚠️ HABILITAR? | FREE (Roteável!) |

---

## 💰 Preços dos Modelos (OpenRouter)

### Modelos FREE (US$0):
| Modelo | Descrição |
|--------|-----------|
| `cohere/north-mini-code:free` | Code assistant |
| `nex-agi/nex-n2-pro:free` | - |
| `nvidia/nemotron-3.5-content-safety:free` | Safety |
| `openrouter/owl-alpha:free` | - |
| `poolside/laguna-xs.2:free` | - |
| `poolside/laguna-m.1:free` | - |

### Modelos MUITO BARATOS (< US$0.00001/1K prompt):
| Modelo | Prompt/1K | Completion/1K | Uso |
|--------|-----------|--------------|-----|
| `anthropic/claude-opus-4.8` | $0.000005 | $0.000025 | Premium |
| `~anthropic/claude-sonnet-latest` | $0.000003 | $0.000015 | Bom custo-benefício |
| `google/gemini-3.1-flash-lite` | $0.00000025 | $0.0000015 | Ultra barato |
| `deepseek/deepseek-v4-flash` | $0.00000009 | $0.00000018 | Mais barato |
| `qwen/qwen3.7-plus` | $0.00000032 | $0.00000128 | Barato |
| `~openai/gpt-mini-latest` | $0.00000075 | $0.0000045 | Barato OpenAI |

---

## ⚖️ PRÓS e CONTRAS

### ✅ PRÓS da Arquitetura Multi-Key

1. **Resiliência**: Se uma key bate limite, outra assume automaticamente
2. **Custo**: Modelos free eliminam custo de API
3. **Fallback LRU**: Sistema escolhe automaticamente a key menos usada
4. **Cooldown automático**: Keys com erro ficam em cooldown
5. **Balanceamento**: Distribui carga entre múltiplas contas

### ❌ CONTRAS da Arquitetura Multi-Key

1. **Complexidade**: Mais código, mais pontos de falha
2. **Monitoramento**: Difícil rastrear gastos por cliente
3. **Latência**: Round-robin pode adicionar delay
4. **Rate Limits**: Cada provider tem limites próprios
5. **Manutenção**: Keys expiram, precisam rotacionar

---

## 🎯 RECOMENDAÇÃO

### Opção 1: MANTER Arquitetura Multi-Key ✅ (Recomendado)

**Vantagens:**
- Modelos FREE disponíveis (sem custo!)
- Resiliência se uma API cair
- Escalabilidade natural

**Ação:**
1. Habilitar `openrouter` na tabela `provider_keys`
2. Cadastrar 3-5 modelos free como fallback
3. Usar `~anthropic/claude-sonnet-latest` como principal

```sql
-- Habilitar openrouter
UPDATE provider_keys SET enabled = TRUE WHERE provider = 'openrouter';

-- Adicionar modelos free
INSERT INTO provider_keys (provider, encrypted_key, base_url, enabled) VALUES
('anthropic', 'FREE', 'openrouter', TRUE),
('openai', 'FREE', 'openrouter', TRUE);
```

### Opção 2: CHAVE ÚNICA (Simples)

**Vantagens:**
- Menos complexidade
- Mais fácil monitorar
- Menos pontos de falha

**Desvantagens:**
- Sem resiliência
- Limite de rate limit

---

## 🔧 Próximos Passos Sugeridos

### Para restaurar arquitetura multi-key:

```bash
# 1. Habilitar openrouter
ssh root@187.77.37.72 "sudo -u postgres psql -p 5433 -d fralib_db -c \"UPDATE provider_keys SET enabled = TRUE WHERE provider = 'openrouter';\`"

# 2. Testar
curl -s https://openrouter.ai/api/v1/models -H "Authorization: Bearer <SUA_KEY>"

# 3. Verificar seLiteLLM pode ser substituído pelo openrouter diretamente
```

### Alternativa: Usar só OpenRouter

Substituir `LITELLM_API_KEY` pelo OpenRouter, que é mais barato e tem mais modelos.

---

## 📈 Estimativa de Custo

| Cenário | Leads/Mês | Custo Estimado |
|---------|-----------|----------------|
| Todos free | 1000 | **$0** |
| Mix free + Sonnet | 1000 | **~$0.50-2** |
| Usando LiteLLM (atual) | 1000 | **~$5-15** |

---

## �Decision Matrix

| Critério | Multi-Key | Única Key |
|----------|-----------|-----------|
| Custo | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Complexidade | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Confiabilidade | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Manutenção | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recomendação Final: Manter arquitetura multi-key, usar OpenRouter como proxy.**

---

*Gerado em: 2026-06-19*
