# Guia: Configurar Meta Graph API para Auto-Post (Facebook + Instagram)

> **Objetivo**: gerar Page Token de longa duração (60 dias) + Instagram Business Account ID
> para que `scripts/auto_post_social.py` consiga postar automaticamente.
>
> **Pré-requisitos**:
> - Conta Facebook com Página criada (você já tem — Meta Pixel ID `1022692323751129` está no blog)
> - Conta Instagram **Business ou Creator** (não pessoal) — conversão gratuita
> - Conta em [developers.facebook.com](https://developers.facebook.com)

---

## 1. Conta Instagram precisa ser Business/Creator

Se sua conta pessoal ainda não é Business:

1. Abra o app do Instagram no celular
2. Vá em **Configurações** → **Conta** → **Mudar para conta profissional**
3. Escolha **Business** (não Creator, a menos que você seja influencer)
4. Conecte à sua Página do Facebook (selecione a mesma Página do Pixel ID `1022692323751129`)

**Por que precisa disso**: a Graph API só consegue postar em contas Business/Creator conectadas a uma Página. Contas pessoais são bloqueadas pela Meta desde 2018.

---

## 2. Criar App no Meta for Developers

1. Acesse [developers.facebook.com](https://developers.facebook.com) e faça login
2. **Meus apps** → **Criar app**
3. Tipo: **Outro** → **Avançado** (ou "Negócios" se aparecer)
4. Nome do app: `FraLib AutoPost` (ou o que preferir)
5. Email de contato: seu email
6. **Empresa**: selecione sua empresa se tiver Business Manager; se não, pule

---

## 3. Adicionar produtos ao App

No painel do app recém-criado, clique em **Adicionar produto** e adicione:

| Produto | Para quê serve |
|---|---|
| **Instagram Graph API** | Postar no Instagram |
| **Facebook Login for Business** | Gerar token de usuário |
| **Pages API** | Ler/escrever na sua Página |

---

## 4. Configurar permissões (Login do Facebook)

1. No menu lateral: **Facebook Login for Business** → **Configurações**
2. Adicione o OAuth Redirect URI: `https://localhost/` (placeholder — não usaremos de fato)
3. Em **Configurações do app** → **Básico**:
   - **Domínios do app**: adicione `seunegociofralib.site` e `localhost`
   - **URL da política de privacidade**: `https://seunegociofralib.site/privacidade`
   - **Categoria do app**: "Business and Pages"
4. Salve

---

## 5. Solicitar permissões avançadas

Em **Casos de uso** (novo painel da Meta) ou **Permissões e recursos**:

Solicite (não são todas que precisam de aprovação, mas peça logo):
- `pages_show_list` — listar suas páginas
- `pages_manage_posts` — postar na página ✅ (aprovação automática)
- `pages_read_engagement` — ler métricas
- `instagram_basic` — ler perfil IG ✅ (automática)
- `instagram_content_publish` — postar no IG ⚠️ (requer aprovação de uso comercial)
- `business_management` — acessar Business Manager

**Sobre a aprovação**: a Meta aprova `instagram_content_publish` se você descrever o caso de uso claramente. Vá em **Uso de dados** → descreva:

> "Auto-post de conteúdo do blog FraLib em Página do Facebook e conta Instagram Business. Posts são agendados e distribuídos automaticamente para aumentar alcance orgânico do conteúdo educacional sobre automação e marketing para freelancers brasileiros."

Aprovação leva de 1 a 5 dias úteis. Para uso pessoal/teste, funciona em modo "desenvolvimento" sem aprovação, mas com limite de usuários (só você consegue usar).

---

## 6. Gerar Page Token de LONGA duração (60 dias)

> **Importante**: token de curta duração (1-2h) só serve pra teste. Pra produção,
> você PRECISA trocar por Long-Lived Token.

### Passo A: Token de curta duração

1. Em **Ferramentas** → **Graph API Explorer** (ou [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer))
2. Selecione seu app **FraLib AutoPost**
3. Clique em **Gerar token de acesso**
4. Autorize todas as permissões listadas acima
5. Copie o token curto (parece com `EAA...`)

### Passo B: Trocar por Long-Lived User Token (60 dias)

```bash
curl "https://graph.facebook.com/v18.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=SEU_APP_ID&\
client_secret=SEU_APP_SECRET&\
fb_exchange_token=TOKEN_CURTO_AQUI"
```

Resposta vem com `access_token` (60 dias) e `expires_in`. **Guarde esse token**.

> **APP_ID** e **APP_SECRET** estão em **Configurações do app** → **Básico**.

### Passo C: Pegar Page Token (vinculado à sua página)

```bash
curl "https://graph.facebook.com/v18.0/me/accounts?access_token=TOKEN_LONGO_AQUI"
```

A resposta lista suas páginas com `access_token` próprio de cada uma. Esse é o **Page Token** que você vai usar. Ele vale enquanto o User Token for válido (60 dias). **Copie o `access_token` da sua página do blog**.

### Passo D: Pegar Instagram Business Account ID

```bash
# Primeiro pegue o Page ID
curl "https://graph.facebook.com/v18.0/me/accounts?access_token=PAGE_TOKEN_AQUI"

# Depois, com o PAGE_ID:
curl "https://graph.facebook.com/v18.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_TOKEN_AQUI"
```

Resposta:
```json
{
  "instagram_business_account": {
    "id": "17841234567890123"   ← ESSE É O INSTAGRAM_BUSINESS_ID
  }
}
```

---

## 7. Adicionar no `.env` da VPS (criptografado)

⚠️ **NUNCA** coloque token em texto plano. A Fralib já tem `FERNET_KEY` configurado.

### Passo 1: Gerar helper para criptografar

Já existe um helper em `backend/utils/secrets_crypto.py`. Use ele:

```bash
cd /root/fralib
source .venv/bin/activate

# Criptografar cada token
python -c "
from backend.utils.secrets_crypto import encrypt_secret
print('FB_TOKEN:', encrypt_secret('SEU_PAGE_TOKEN_AQUI'))
print('IG_ID:',   encrypt_secret('SEU_INSTAGRAM_BUSINESS_ID_AQUI'))
"
```

### Passo 2: Adicionar variáveis no `.env`

```bash
sudo nano /etc/fralib/fralib.env
# ou
nano /root/fralib/.env
```

Adicione:

```bash
# Meta Graph API (auto-post social)
FACEBOOK_PAGE_TOKEN=ENC:SEU_TOKEN_CRIPTOGRAFADO_AQUI
FACEBOOK_PAGE_ID=ENC:SEU_PAGE_ID_CRIPTOGRAFADO_AQUI
INSTAGRAM_BUSINESS_ID=ENC:SEU_IG_BUSINESS_ID_CRIPTOGRAFADO_AQUI
```

> **Por que `ENC:`?** É o prefixo que `secrets_crypto.py` reconhece pra descriptografar
> automaticamente antes de usar. Variáveis sem esse prefixo ficam em texto plano.

### Passo 3: Validar

```bash
# Testar se o token funciona
curl "https://graph.facebook.com/v18.0/me?access_token=$(python -c 'from backend.utils.secrets_crypto import decrypt_secret; print(decrypt_secret(open(\".env\").read().split(\"FACEBOOK_PAGE_TOKEN=\")[1].split(\"\\n\")[0].replace(\"ENC:\",\"\")))')"
```

Se retornar JSON com seu nome e ID, tá vivo.

---

## 8. Renovação automática (a cada 60 dias)

Como o Long-Lived Token expira em 60 dias, crie um cron que renova:

```bash
# Adicionar ao crontab (roda 1x por mês)
(crontab -l 2>/dev/null; echo "0 3 1 * * /usr/bin/python3 -c 'import requests; r=requests.get(\"https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=TOKEN_ATUAL\"); print(r.json())' >> /var/log/fralib/token_renew.log 2>&1") | crontab -
```

(Na prática, salve o User Token em arquivo separado e leia dele.)

---

## 9. Variáveis finais no `.env` da Fralib

| Variável | Onde fica | Para que serve |
|---|---|---|
| `FACEBOOK_PAGE_TOKEN` | `.env` (criptografado) | Token pra postar no Facebook Page |
| `FACEBOOK_PAGE_ID` | `.env` (criptografado) | ID da sua página |
| `INSTAGRAM_BUSINESS_ID` | `.env` (criptografado) | ID da conta IG Business |
| `LINKEDIN_ACCESS_TOKEN` | `.env` (texto plano) | Já existe — LinkedIn |
| `TWITTER_*` | `.env` (texto plano) | Já existem — Twitter/X |

---

## 10. Teste manual antes de agendar

```bash
cd /root/fralib
source .venv/bin/activate

# Rodar com .env carregado
set -a; source .env; set +a
python3 scripts/auto_post_social.py
```

Saída esperada:
```
[2026-07-02 10:30:00] Iniciando auto-post em redes sociais...
  Processando: <título do post>
    [OK] LinkedIn
    [OK] Twitter
    [OK] Facebook
    [OK] Instagram    ← só aparece se FACEBOOK_PAGE_TOKEN + INSTAGRAM_BUSINESS_ID estão setados

  RESUMO:
    LinkedIn:  1 posts
    Twitter:   1 posts
    Facebook:  1 posts
    Instagram: 1 posts
```

Se aparecer `Instagram skip: faltam INSTAGRAM_BUSINESS_ID ou FACEBOOK_PAGE_TOKEN`, revise o `.env`.

---

## ⚠️ Checklist final antes de agendar

- [ ] Conta Instagram é Business/Creator (não pessoal)
- [ ] Página do Facebook conecta a conta IG
- [ ] App criado no Meta for Developers
- [ ] Permissões solicitadas (`pages_manage_posts`, `instagram_content_publish`)
- [ ] Page Token Long-Lived (60 dias) gerado
- [ ] Instagram Business Account ID capturado
- [ ] Variáveis adicionadas no `.env` com prefixo `ENC:` (criptografado)
- [ ] Teste manual rodou com sucesso em todas as 4 redes

---

## 🆘 Problemas comuns

| Erro | Causa | Solução |
|---|---|---|
| `(#100) Tried accessing nonexisting field` | Token sem permissão | Reautorize com permissões corretas |
| `Invalid OAuth access token` | Token expirado ou inválido | Gere novo Long-Lived Token |
| `Instagram container error 400` | Imagem não é HTTPS pública | Use URL absoluta, sem localhost |
| `Instagram skip: exige image_url pública` | Post sem imagem | Adicione imagem ao post do blog |
| `Permission denied for instagram_content_publish` | App não aprovado | Modo dev só funciona pra admins |
| `(#10) Application does not have permission` | App não está conectado à Página | Vá em **Funções** no Business Manager → adicionar app à Página |

---

*Última atualização: 2026-07-02 — escrito por Claude após descobrir que a Fralib já tinha
auto_post_social.py funcional para 3 redes, faltando apenas Instagram.*