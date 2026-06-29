# 🚀 Novos Recursos: Competitive Intelligence, LinkedIn Outreach & CRM Integration

Este documento explica os novos recursos implementados para FraLib SDR.

---

## 📊 Sumário

1. [Competitive Intelligence](#competitive-intelligence) - Análise de Concorrentes
2. [LinkedIn Outreach](#linkedin-outreach) - Prospecção Ativa
3. [CRM Integration](#crm-integration) - Sincronização com CRMs
4. [Setup](#setup) - Como instalar
5. [Uso](#uso) - Como usar

---

## 🎯 Competitive Intelligence

### O que é?
Armazena e gerencia inteligência competitiva por segmento/nicho.

### Acesso
- **SuperAdmin** → Inteligência → Concorrentes
- **Não exposto aos usuários finais**

### Features
- ✅ Lista de concorrentes por segmento
- ✅ Battle cards (scripts de objection handling)
- ✅ Análise de pontos fortes/fracos
- ✅ Importação manual ou automática

### Endpoints
```bash
# Listar concorrentes
GET /api/intel/competitors

# Adicionar concorrente
POST /api/intel/competitors

# Battle cards
GET /api/intel/competitors/battle-cards/summary
```

### Exemplo de Battle Card
```json
{
  "segmento": "academia",
  "concorrentes": [
    {
      "nome": "Academia Forte",
      "pricing": "R$ 199/mês",
      "strengths": "Localização central",
      "weaknesses": "Site antigo"
    }
  ],
  "scripts": {
    "preco": "Entendo a preocupação com preço. Nosso modelo é diferente: você só paga depois de aprovar o site."
  }
}
```

---

## 🌐 LinkedIn Outreach

### O que é?
Sistema de prospecção ativa via LinkedIn.

### Acesso
- **SuperAdmin** → Inteligência → LinkedIn

### Features
- ✅ Gerenciamento de prospects
- ✅ Templates de InMail personalizados
- ✅ Métricas de resposta
- ✅ Exportação CSV/JSON

### Endpoints
```bash
# Listar prospects
GET /api/intel/linkedin/prospects

# Adicionar prospect
POST /api/intel/linkedin/prospects

# Templates
GET /api/intel/linkedin/templates

# Métricas
GET /api/intel/linkedin/metrics
```

### Status dos Prospects
- `new` - Novo
- `contacted` - Contactado
- `responded` - Respondeu
- `converted` - Convertido

---

## 🤝 CRM Integration

### O que é?
Sincroniza leads com Salesforce ou HubSpot.

### Acesso
- **SuperAdmin** → Configuração CRM
- **Admin** → Botão "Exportar para CRM"

### CRMs Suportados
- ✅ Salesforce (REST API)
- ✅ HubSpot (API v3)

### Features
- ✅ Autenticação segura (tokens criptografados)
- ✅ Criação/atualização de leads
- ✅ Histórico de sincronizações
- ✅ Estatísticas de sucesso

### Endpoints
```bash
# Configuração
GET /api/crm/config
POST /api/crm/config

# Sincronização
POST /api/crm/sync/{lead_id}

# Histórico
GET /api/crm/sync/history
GET /api/crm/sync/stats

# Teste de conexão
POST /api/crm/test
```

### Mapeamento de Estágios
| FraLib | Salesforce | HubSpot |
|--------|-----------|---------|
| hook | New | NEW |
| qualify | Working | IN_PROGRESS |
| close | Closed - Won | CLOSED_WON |
| lost | Closed - Lost | CLOSED_LOST |

---

## 🔧 Setup

### 1. Rodar o script de setup
```bash
cd /c/fralib
python setup_new_features.py
```

### 2. Adicionar variáveis de ambiente
No seu `.env`:
```env
FRALIB_CRM_ENCRYPTION_KEY=seu_chave_aqui
```

### 3. Rodar migrações
```bash
cd /c/fralib/backend
alembic upgrade head
```

### 4. Reiniciar servidor
```bash
python server.py
```

---

## 📱 Uso

### SuperAdmin - Competitive Intelligence
1. Acesse "SuperAdmin"
2. Vá para "Inteligência → Concorrentes"
3. Adicione concorrentes manualmente
4. Configure battle cards

### SuperAdmin - LinkedIn Outreach
1. Acesse "SuperAdmin"
2. Vá para "Inteligência → LinkedIn"
3. Adicione prospects
4. Use templates para enviar InMails
5. Acompanhe métricas

### Admin - CRM Sync
1. Acesse "Admin"
2. Vá para "CRM / Leads"
3. Clique em "Exportar para CRM"
4. Verifique histórico em "Histórico de Sincronização"

### SuperAdmin - CRM Config
1. Acesse "SuperAdmin"
2. Vá para "Configuração CRM"
3. Configure Salesforce ou HubSpot
4. Teste conexão

---

## 📊 Estrutura de Dados (Multi-Tenant)

### Tabela: competitor_intel
```sql
- id (UUID)
- tenant_id (INT)  -- Isolamento!
- segmento (VARCHAR)
- nome (VARCHAR)
- site_url (VARCHAR)
- pricing (VARCHAR)
- strengths (TEXT)
- weaknesses (TEXT)
- battle_card (TEXT)
```

### Tabela: linkedin_prospects
```sql
- id (UUID)
- tenant_id (INT)  -- Isolamento!
- nome (VARCHAR)
- empresa (VARCHAR)
- status (VARCHAR)
- last_contacted_at (TIMESTAMP)
```

### Tabela: crm_configs
```sql
- tenant_id (INT)  -- Isolamento!
- crm_type (VARCHAR)
- api_key_encrypted (TEXT)
- access_token_encrypted (TEXT)
```

---

## 🔐 Segurança

- ✅ **Multi-tenant**: Dados isolados por tenant
- ✅ **Criptografia**: Chaves de API criptografadas
- ✅ **Autenticação**: Tokens OAuth2 para Salesforce/HubSpot
- ✅ **Permissões**: SuperAdmin só para operações internas

---

## 🚀 Próximos Passos

1. **Automatização**: Webhooks para atualizações de CRM
2. **IA**: Análise automática de concorrentes via web scraping
3. **Templates**: Mais templates de InMail
4. **Integração**: HubSpot Webhooks, Zapier

---

## 📞 Suporte

- **Problemas técnicos**: Verifique logs do servidor
- **Setup**: Execute `python setup_new_features.py`
- **API**: Consulte os endpoints acima

---

🎉 **Pronto para usar!**