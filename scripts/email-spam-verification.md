# Verificacao de Spam - Servico de Email FraLib

## Resumo da Configuracao

| Variavel       | Valor                        |
|----------------|------------------------------|
| API            | Resend (api.resend.com)      |
| RESEND_API_KEY | `re_ACo3NmiA_...` (presente) |
| FROM_EMAIL     | noreply@seunegociofralib.site |

O `email_service.py` (`backend/services/email_service.py`) le ambas as
variaveis via `load_dotenv()` na inicializacao.

---

## 1. Envio de Email de Teste

### Bash (Linux/Mac/WSL)

```bash
cd scripts
chmod +x test_email_send.sh
./test_email_send.sh                          # usa mail-tester.com
./test_email_send.sh "seu@email.com"          # destinatario especifico
```

### Python (async)

```python
import asyncio
from backend.services.email_service import enviar_email_confirmacao

async def teste():
    ok = await enviar_email_confirmacao(
        email="teste@exemplo.com",
        nome="Teste",
        token="token-fake-123"
    )
    print("Enviado:", ok)

asyncio.run(teste())
```

### curl direto

```bash
curl -X POST "https://api.resend.com/emails" \
  -H "Authorization: Bearer $RESEND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "FraLib <noreply@seunegociofralib.site>",
    "to": ["destinatario@exemplo.com"],
    "subject": "Teste FraLib",
    "html": "<h1>Funciona!</h1>"
  }'
```

---

## 2. Verificar Score de Spam (mail-tester.com)

1. Acesse https://mail-tester.com
2. Clique em **"Create a new test"** — receba um endereco unico
   (ex: `test-abc123@mail-tester.com`, valido por 1 hora)
3. Envie o email de teste para esse endereco:
   ```bash
   ./test_email_send.sh "test-abc123@mail-tester.com"
   ```
4. Volte ao mail-tester.com e clique **"Score your email"**
5. Score esperado: **8/10 ou mais**

### Itens que o mail-tester verifica

| Item                      | Pontos |
|---------------------------|--------|
| Autenticacao SPF          | +2     |
| Autenticacao DKIM         | +2     |
| Autenticacao DMARC        | +2     |
| Conteudo HTML bem formado | +1     |
| Links faceis de rastrear  | +1     |
| Sem palavras de spam      | +1     |
| Reputacao do dominio      | +1     |

---

## 3. Verificar no Gmail

### Checklist Gmail

1. **Abra o email e verifique o cabecalho**
   - Clique nos 3 pontos > **Mostrar original**
   - Confirme as secoes `Authentication-Results`:

   ```
   ARC-Seal: i=1; a=rsa-sha256; ...
   ARC-Message-Signature: ...
   ARC-Authentication-Results: ...
     spf=pass (google.com: ...)
     dkim=pass (...)
     dmarc=pass action=none ...)
   ```

2. **Nao caiu no spam?**
   - Se `dmarc=pass` e `dkim=pass` -> configuracao correta
   - Se `dmarc=fail` -> dominio nao tem DMARC configurado

3. **Anexar a caixa de entrada**
   - Apos varios envios para o mesmo destinatario, o Gmail
     aprende que o dominio nao e spam

### Acoes se o email for para spam

1. Clique em **"Nao e spam"** no Gmail
2. Marque o remetente como **"Importante"**
3. Crie um filtro para nunca enviar para spam

---

## 4. Verificar Registros DNS (SPF/DKIM/DMARC)

### Com dig

```bash
# SPF
dig TXT seunegociofralib.site +short | grep -i spf

# DKIM (Resend adiciona automaticamente apos configuracao no painel)
dig TXT resend._domainkey.seunegociofralib.site +short

# DMARC
dig TXT _dmarc.seunegociofralib.site +short
```

### Configuracoes recomendadas

**SPF** (autoriza Resend a enviar em nome do dominio):
```
v=spf1 include:resend.com ~all
```

**DKIM**: Configurado automaticamente pelo Resend apos
adicionar o dominio no painel (https://resend.com/domains).

**DMARC** (recomendado):
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@seunegociofralib.site; pct=100
```
Troque `quarantine` por `reject` apos validar que tudo funciona.

---

## 5. Links Uteis

| Servico                 | URL                              |
|-------------------------|----------------------------------|
| Painel Resend           | https://resend.com/emails        |
| Dominios Resend         | https://resend.com/domains       |
| Mail-tester             | https://www.mail-tester.com      |
| Verificador DNS         | https://toolbox.googleapps.com/apps/dig/ |
| Google Postmaster Tools | https://postmaster.google.com    |

---

## 6. Checklist de Producao

- [ ] `RESEND_API_KEY` definida no .env
- [ ] `FROM_EMAIL` aponta para dominio verificado no Resend
- [ ] Registro **SPF** adicionado ao DNS
- [ ] **DKIM** verificado no painel do Resend
- [ ] **DMARC** criado (p=quarantine)
- [ ] Email de teste enviado para mail-tester.com (score >= 8)
- [ ] Email de teste enviado para Gmail e verificado (caixa de entrada)
- [ ] Testar fluxo real: cadastrar usuario no app -> email de confirmacao chega
