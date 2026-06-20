# 🔐 Credenciais do Projeto FraLib

Este documento lista todas as credenciais do projeto para referência e segurança.

---

## 📋 Índice
- [Credenciais Ativas](#-credenciais-ativas)
- [Credenciais do Sistema](#-credenciais-do-sistema)
- [Como Rotacionar](#-como-rotacionar)
- [Checklist de Segurança](#-checklist-de-segurança)

---

## 🔑 Credenciais Ativas

### 1. JWT_SECRET_KEY
| Propriedade | Valor |
|-------------|-------|
| **Variável** | `JWT_SECRET_KEY` ou `JWT_SECRET` |
| **Localização** | `.env`, `backend/core/auth.py`, `backend/core/jwt_config.py` |
| **Uso** | Assinar tokens de autenticação (login de usuários) |
| **Impacto se vazada** | Usuários podem ter tokens forjados |
| **Impacto se trocada** | TODOS os usuários precisam fazer login novamente |

### 2. FERNET_KEY
| Propriedade | Valor |
|-------------|-------|
| **Variável** | `FERNET_KEY` |
| **Localização** | `.env`, `backend/utils/secrets_crypto.py` |
| **Uso** | Criptografar segredos por tenant (ex: API keys do plano Pro/Business) |
| **Impacto se vazada** | API keys criptografadas podem ser descriptadas |
| **Impacto se trocada** | **CRÍTICO**: Todos os dados criptografados são PERDIDOS |

---

## 🏗️ Credenciais do Sistema

### Anthropic API Key
| Propriedade | Valor |
|-------------|-------|
| **Variável** | `ANTHROPIC_API_KEY` |
| **Uso** | Chamadas LLM (Claude) |
| **Localização** | `backend/services/ia_manager.py`, `backend/core/proxy_models.py` |
| **Rotação** | https://console.anthropic.com/settings/keys |

### LiteLLM (Proxy)
| Propriedade | Valor |
|-------------|-------|
| **Variável** | `LITELLM_API_KEY`, `LITELLM_BASE_URL` |
| **Uso** | Proxy para múltiplos providers LLM |
| **Localização** | `backend/services/llm_router.py` |

### MercadoPago
| Propriedade | Valor |
|-------------|-------|
| **Variável** | `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET` |
| **Uso** | Pagamentos (parceiros MercadoPago) |
| **Localização** | `backend/services/credits_manager.py` |

---

## 🔄 Como Rotacionar

### JWT_SECRET_KEY
```bash
# 1. Gere uma nova chave
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 2. Atualize no .env
JWT_SECRET_KEY=nova_chave_aqui

# 3. Todos os usuários precisarão fazer login novamente
```

### FERNET_KEY
```bash
# ⚠️ ATENÇÃO: Dados criptografados serão PERDIDOS

# 1. Gere uma nova chave
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Atualize no .env
FERNET_KEY=nova_chave_aqui

# 3. REDECRIPTOGRAFAR todos os dados ou RESETAR
# Se não tiver backup dos dados descriptados, serão PERMANENTEMENTE PERDIDOS
```

---

## ✅ Checklist de Segurança

### Ao fazer deploy em produção:
- [ ] `FRALIB_ENV=prod` configurado
- [ ] `JWT_SECRET_KEY` único (não padrão)
- [ ] `FERNET_KEY` configurado (não pode ser volátil em prod)
- [ ] `ANTHROPIC_API_KEY` configurado
- [ ] API keys do LiteLLM configuradas
- [ ] `.env` NO `.gitignore`

###，定期檢查 (Checklist periódico):
- [ ] Verificar se .env está no .gitignore
- [ ] Revogar chaves não usadas no console (Anthropic, etc.)
- [ ] Verificar logs por tentativas de acesso suspeitas
- [ ] Testar backup/restore de dados criptografados
- [ ] Revisar permissões de tenants

---

## 🚨 Emergência - Credenciais Vazadas

Se uma credencial foi vazada:

1. **Anthropic API Key**:
   - Revogar em: https://console.anthropic.com/settings/keys
   - Gerar nova
   - Atualizar no .env

2. **JWT_SECRET_KEY**:
   - Gerar nova
   - Todos os usuários farão logout

3. **FERNET_KEY**:
   - Gerar nova (dados criptografados serão PERDIDOS)
   - Redigitar segredos dos tenants manualmente

4. **MercadoPago**:
   - Revogar em: https://www.mercadopago.com.br/settings/account/credentials
   - Gerar novas credenciais

---

## 📞 Suporte

Para dúvidas sobre credenciais, consulte:
- Equipe de segurança: [seu-email@dominio.com]
- Documentação: [link-doc-interna]

---

*Última atualização: 2026-06-19*
