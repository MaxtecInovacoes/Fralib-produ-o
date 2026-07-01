# Segurança de Variáveis de Ambiente — FraLib

> Documento obrigatório antes de mexer em `.env`, `.env.example` ou deploy em produção.

## 🎯 Arquitetura (2 arquivos, 2 vidas)

| Arquivo | Onde existe | O que tem | Vai pro git? |
|---|---|---|---|
| **`.env`** | Servidor VPS (`/root/fralib/.env`) + máquina local dev | **Tokens reais** (MP, Anthropic, Jina, JWT, DB) | ❌ **NUNCA** |
| **`.env.example`** | Raiz do repo | **Template** (placeholders vazios) | ✅ **SIM** (exceção) |

## 🛡️ Camadas de proteção

### 1. `.gitignore` (camada 1)
```gitignore
.env       # ignora
.env.*     # ignora tudo
!.env.example   # EXCEÇÃO: .env.example PODE subir
```
- `.env` é ignorado desde o primeiro commit
- Mesmo se você fizer `git add .env`, nada vai pra stage

### 2. `scripts/scan_secrets.sh` (camada 2 — pre-commit hook)
Roda automaticamente em **todo `git commit`**. Detecta:
- ✅ Stripe live/test (`sk_live_`, `pk_live_`)
- ✅ Anthropic (`sk-ant-` com 40+ chars)
- ✅ OpenAI (`sk-` com 40+ chars)
- ✅ AWS Access Keys (`AKIA...`)
- ✅ GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`)
- ✅ Google API (`AIza...`)
- ✅ Slack (`xoxb-`, `xoxp-`, `xoxr-`, `xoxs-`, `xoxa-`)
- ✅ **Mercado Pago (`APP_USR-` com 40+ chars, `TEST-` com 40+)**
- ✅ **Stripe webhook secrets (`whsec_`)**
- ✅ **Mercado Pago webhook com valor**
- ✅ Private keys (formato PEM real, não exemplo)
- ✅ Bloqueia arquivos `.env`, `.env.local`, `.pem`, `.key`

### 3. `.env.example` versionado (camada 3)
- Existe APENAS como template público
- Todos os valores são placeholders (`GERE_COM_python_secrets_token_urlsafe_64`)
- Quando você criar um novo campo em `.env`, **adicione também no `.env.example`** com placeholder

## 📋 Workflow correto

### Setup local novo (dev)
```bash
git clone <repo>
cp .env.example .env
# Editar .env com suas chaves reais
```

### Adicionar nova chave
```bash
# 1. Editar .env (local) com valor real
echo "NOVA_CHAVE=seu_valor_real" >> .env

# 2. Editar .env.example com placeholder
echo "NOVA_CHAVE=GERE_SUA_CHAVE_AQUI" >> .env.example

# 3. Commitar
git add .env.example
git commit -m "feat(env): adiciona NOVA_CHAVE"
# O scanner vai validar antes do push
```

### Deploy em produção
```bash
# Via SSH direto no servidor
ssh root@187.77.37.72
cp /root/.env.backup-2026-07-01 /root/fralib/.env  # restaurar se necessário
echo "MERCADOPAGO_ACCESS_TOKEN=APP_USR-novo-token" >> /root/fralib/.env
pm2 restart all
```

## 🚨 Se um secret VAZAR (commitou errado / push indevido)

### 1. **RODAR** o token imediatamente
- Mercado Pago: painel → Suas integrações → **Resetar credenciais**
- Anthropic: console.anthropic.com → Settings → API Keys → **Revoke**
- Stripe: dashboard.stripe.com → Developers → API keys → **Roll**
- GitHub: settings → Tokens → **Delete**
- AWS: IAM → Users → Access keys → **Delete**

### 2. **Limpar do histórico git**
```bash
# APAGA o arquivo de TODOS os commits
git filter-repo --invert-paths --path .env

# Force push (CUIDADO!)
git push --force
```

### 3. **Atualizar produção**
```bash
ssh root@187.77.37.72
# Atualizar .env com o NOVO token
pm2 restart all
```

### 4. **Auditar uso do token vazado**
- MP: ver logs de webhook → `webhook_logs` table
- Stripe: logs de transações
- AWS: CloudTrail

## 🛑 O que NUNCA fazer

- ❌ `git add .env` (gitignore protege, mas não confie)
- ❌ `git commit --no-verify` (pula o scanner)
- ❌ `git push --force` sem motivo (pode quebrar time)
- ❌ Colocar tokens em **comments** dentro de código
- ❌ Hardcodar tokens em `frontend/js/*` ou HTML
- ❌ Compartilhar `.env` via Slack/Discord/email
- ❌ Usar **mesmo token** em dev e produção
- ❌ Versionar `.env.backup` (também é ignorado, mas fica na máquina)

## ✅ Boas práticas

- ✅ Cada dev tem **suas próprias chaves** de teste
- ✅ Tokens de produção **só no servidor VPS**
- ✅ Rotação a cada 90 dias para tokens críticos
- ✅ Usar `MERCADOPAGO_ACCESS_TOKEN` de **produção** apenas em produção
- ✅ Usar `TEST-...` em desenvolvimento
- ✅ Logs nunca devem imprimir tokens (`logger.info(f"Token: {token[:4]}...")`)

## 🔍 Verificar se há secrets no histórico

```bash
# Procurar todos os tokens já commitados (mesmo que revertidos)
git log --all -p | grep -E "(APP_USR-[A-Za-z0-9-]{20,}|sk_live_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})"

# Se aparecer algo: RODE O TOKEN IMEDIATAMENTE
```

## 📞 Onde conseguir suporte

- **GitHub Secrets leaks**: https://github.com/settings/security
- **Mercado Pago**: https://www.mercadopago.com.br/developers/panel/notifications
- **Anthropic**: https://console.anthropic.com/settings/privacy