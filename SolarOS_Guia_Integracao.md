# SolarOS - Guia de Integração Completa

## 📋 Visão Geral do Sistema

O SolarOS é um módulo inteligente que se integra ao Nexus existente, adicionando:

1. **ERTM Agent** - Agente orquestrador que mede, planeja e executa
2. **Dashboard Central** - KPIs em tempo real para todos os setores
3. **Automação de Tarefas** - Tarefas diárias/semanais/mensais automáticas
4. **Sistema de Alertas** - Notificações proativas de gargalos
5. **Integração WhatsApp** - Comunicação automática com a equipe

## 🏗️ Arquitetura de Integração

```
┌─────────────────────────────────────────────────────────────────┐
│                         NEXUS EXISTENTE                          │
├─────────────────────────────────────────────────────────────────┤
│  Leads │ Clientes │ Contratos │ Instalação │ Pós-Venda         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SOLAROS SDK (JavaScript)                    │
├─────────────────────────────────────────────────────────────────┤
│  ERTM_Agent │ SolarOS_ERTM │ API Nexus │ WhatsApp Integration  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD SOLAROS (React)                     │
├─────────────────────────────────────────────────────────────────┤
│  KPIs │ Tarefas │ Kanban │ Heatmap │ Alertas │ Equipe          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Instalação Passo a Passo

### 1. Preparar o Ambiente

```bash
# Acessar o diretório do Nexus
cd /c/fralib

# Criar pasta para SolarOS
mkdir -p frontend/solaros
```

### 2. Copiar Arquivos

Copie os seguintes arquivos para o Nexus:

```
frontend/
├── solaros/
│   ├── solados-sdk.js          # SDK JavaScript principal
│   ├── solados-components.jsx   # Componentes React
│   └── solados-styles.css      # Estilos (criar)
├── landing_nova.html           # Landing page existente
└── ...
```

### 3. Configurar Banco de Dados

Execute o SQL no banco do Nexus:

```sql
-- Arquivo: SolarOS_BancoDeDados.sql
-- Execute no MySQL/PostgreSQL do Nexus
```

### 4. Integrar SDK JavaScript

Adicione ao arquivo principal do Nexus (ex: `index.html` ou `app.js`):

```html
<!-- Antes do fechamento do body -->
<script src="frontend/solaros/solaros-sdk.js"></script>

<script>
  // Inicializa SolarOS com a instância do Nexus
  document.addEventListener('DOMContentLoaded', () => {
    if (window.nexus) {
      window.solarOS = new SolarOS_ERTM(window.nexus);
    }
  });
</script>
```

### 5. Integrar Componentes React

```jsx
// No seu App.jsx ou página principal
import { SolarOSDashboard, FunilKanban, StatusEquipe } from './solaros/solaros-components';

// Adicionar rota ou página
<Route path="/solaros" element={<SolarOSDashboard />} />
```

### 6. Configurar WhatsApp

```javascript
// No arquivo de configuração do Nexus
const config = {
  whatsapp: {
    apiKey: 'sua_api_key_whatsapp',
    phoneId: 'seu_phone_id'
  }
};
```

## 📊 Estrutura de Dados

### Tabelas Necessárias

| Tabela | Descrição |
|--------|-----------|
| `metas_anuais` | Metas do ano (faturamento, contratos) |
| `metas_mensais` | Metas mensais desdobradas |
| `metas_semanais` | Metas da semana |
| `tarefas_diarias` | Tarefas automáticas do dia |
| `kpis_por_etapa` | KPIs por membro e etapa |
| `gargalos_identificados` | Gargalos detectados |
| `alertas_sistema` | Alertas e notificações |

### Campos Obrigatórios por Etapa

```
LEAD (Franz)
├── nome, telefone, email
├── origem (facebook, trafego_pago, indicacao)
├── etapa (prospeccao, qualificacao, proposta, contrato)
├── consumo_medio_kwh
├── tipo_padrao (mono, bi, trifasico)
├── potencia_solicitada
├── valor_proposta
├── payback_estimado
└── tir_estimada

CONTRATO (Eliene)
├── cliente_id
├── potencia_instalada
├── inversor, modulos
├── valor_total
├── forma_pagamento
├── status (homologacao, compra, instalacao, concluido)
├── documentacao_checklist
└── data_entrada, data_prevista

INSTALAÇÃO (Cleocir)
├── contrato_id
├── data_agendada, data_realizada
├── equipe_alocada
├── materiais_utilizados
├── fotos (antes, durante, depois)
├── relatorio_vistoria
└── checklist_seguranca

PÓS-VENDA (Igor)
├── cliente_id
├── data_ultima_manutencao
├── data_proxima_manutencao
├── tipo (preventiva, corretiva, limpeza)
├── historico_servicos
└── status_geracao
```

## 🔄 Fluxos de Automação

### Fluxo 1: Entrada de Lead
```
Facebook/Tráfego → Lead no Nexus
       ↓
ERTM Agent detecta novo lead
       ↓
Franz recebe tarefa: "Ligar para lead X"
       ↓
Franz atualiza status
       ↓
Lead Qualified → Franz recebe: "Enviar proposta"
       ↓
Proposta enviada → Franz recebe: "Fechar contrato"
       ↓
Contrato fechado → Eliene recebe: "Documentar contrato"
       ↓
Documentação OK → Eliene recebe: "Dar entrada na homologação"
       ↓
Homologação OK → Cleocir recebe: "Agendar instalação"
       ↓
Instalação OK → Igor recebe: "Cadastrar manutenção"
```

### Fluxo 2: Tarefas Diárias (8h)
```
8:00 - ERTM Agent executa
       ↓
Calcula metas do dia
       ↓
Gera tarefas para cada membro
       ↓
Envia via WhatsApp
       ↓
Franz: "Ligar para 20 leads, Enviar 5 propostas"
       ↓
Eliene: "Documentar 3 contratos, Verificar 5 homologações"
       ↓
Cleocir: "Instalar em 1 cliente, Verificar logística"
       ↓
Igor: "Realizar 2 manutenções, Gerar 3 relatórios"
```

### Fluxo 3: Alertas de Gargalo (17h)
```
17:00 - Verificação de metas
       ↓
Franz fechou 15/20 ligações (75%)
       ↓
Alerta: "🔴 Volume abaixo! Faltam 5 ligações"
       ↓
Sugestão: "Focar 14-16h, leads qualificados"
       ↓
Se < 50%: "Agendar ligação agora!"
```

## 👥 Permissões por Usuário

### Franz (Vendas/Comercial)
```
✅ Ver: Dashboard Geral
✅ Ver: Leads e Prospecção
✅ Editar: Propostas e Contratos
✅ Ver: Métricas de Vendas
✅ Receber: Tarefas diárias de vendas
✅ Receber: Alertas de prospecção
```

### Eliene (Contratos/Operações)
```
✅ Ver: Dashboard Operações
✅ Editar: Contratos e Documentação
✅ Editar: Homologações
✅ Editar: Compras de Materiais
✅ Ver: status de Instalação
✅ Receber: Tarefas de documentação
✅ Receber: Alertas de prazos
```

### Cleocir (Instalação)
```
✅ Ver: Dashboard Instalação
✅ Editar: Ordens de Serviço
✅ Editar: Status de Instalação
✅ Ver: Agenda de Instalações
✅ Receber: Tarefas de instalação
✅ Receber: Alertas de logística
```

### Igor (Pós-Venda)
```
✅ Ver: Dashboard Pós-Venda
✅ Editar: Manutenções
✅ Gerar: Relatórios de Performance
✅ Ver: Histórico de Clientes
✅ Receber: Tarefas de manutenção
✅ Receber: Alertas de geração
```

### Franz (Admin - Visão Geral)
```
✅ Ver: TODOS os dashboards
✅ Ver: TODAS as métricas
✅ Ver: TODOS os gargalos
✅ Editar: Metas anuais/mensais
✅ Receber: Relatório executivo
✅ Acessar: Configurações do sistema
```

## 📈 KPIs por Setor

### Franz - Vendas
| KPI | Meta | Frequência |
|-----|------|------------|
| Ligações de prospecção | 100/semana | Diário |
| Propostas enviadas | 25/semana | Diário |
| Taxa de conversão | 15% | Semanal |
| Contratos fechados | 10/mês | Mensal |
| Ticket médio | R$ 45.000 | Mensal |
| Tempo resposta | < 2h | Diário |

### Eliene - Operações
| KPI | Meta | Frequência |
|-----|------|------------|
| Contratos documentados | 15/semana | Diário |
| Tempo documentação | < 2 dias | Semanal |
| Homologações aprovadas | 10/mês | Mensal |
| Compras realizadas | 10/mês | Mensal |
| Status atualizado | 100% | Diário |

### Cleocir - Instalação
| KPI | Meta | Frequência |
|-----|------|------------|
| Instalações concluídas | 10/mês | Diário |
| Tempo instalação | < 2 dias | Semanal |
| Vistorias realizadas | 100% | Diário |
| Satisfação cliente | > 95% | Mensal |
| Retrabalho | < 2% | Mensal |

### Igor - Pós-Venda
| KPI | Meta | Frequência |
|-----|------|------------|
| Manutenções preventivas | 8/mês | Diário |
| Relatórios gerados | 30/mês | Diário |
| Performance sistemas | > 90% | Semanal |
| Chamados resolvidos | < 24h | Diário |
| Satisfação | > 98% | Mensal |

## 🔔 Tipos de Alertas

### 🚨 Alerta de Atraso (Prioridade Alta)
- Meta diária não atingida
- Prazo de homologação vencendo
- Instalação atrasada
- **Ação**: Notificação imediata + sugestão

### 💡 Alerta de Oportunidade (Prioridade Média)
- Lead com alta intenção
- Melhor horário para ligação
- Sazonalidade positiva
- **Ação**: Sugestão de ação

### ⚠️ Alerta de Risco (Prioridade Alta)
- Contrato prestes a ser perdido
- Cliente insatisfeito
- Sistema com performance baixa
- **Ação**: Intervenção imediata

### 📊 Alerta de Meta (Prioridade Média)
- Meta semanal quase batida
- Tendência positiva/negativa
- Ranking da equipe
- **Ação**: Reconhecimento ou incentivo

## 📱 Formato das Mensagens WhatsApp

### Template: Tarefas Diárias
```
📅 Tarefas do dia - [Membro]

🕐 Data: [DD/MM/AAAA]

🎯 SUA ÚNICA COISA NUMÉRICA DE HOJE:
[Ligar para 20 novos leads]

📋 Outras tarefas:
1. Enviar 5 propostas comerciais
2. Fechar 1 contrato

⏰ Meta diária até às 17h
💪 Vamos executar!
```

### Template: Meta Batida
```
🏆 Meta Batida!

Parabéns [Membro]!

📊 Seu desempenho:
• Meta: 20 ligações
• Realizado: 22 ligações
• Performance: 110% 🎉

Continue assim! 🚀
```

### Template: Alerta de Gargalo
```
🚨 Alerta de Meta

Membro: Franz
Meta: 20 ligações
Realizado: 10 ligações
Faltou: 10 (50%)

🔍 Diagnóstico:
Volume de ligações muito abaixo

💡 Sugestão:
Focar em horários de maior receptividade:
9-11h e 14-16h

⏰ Ainda dá de recuperar!
```

## ⚙️ Configuração do ERTM

```javascript
const ERTM_CONFIG = {
  // Metas Anuais
  metaFaturamentoAnual: 12000000,  // R$ 12 milhões
  metaMargemLiquida: 0.25,         // 25%
  metaContratosAnuais: 120,

  // Equipe
  equipe: {
    franz: { nome: 'Franz', funcao: 'vendas' },
    eliene: { nome: 'Eliene', funcao: 'operacoes' },
    cleocir: { nome: 'Cleocir', funcao: 'instalacao' },
    igor: { nome: 'Igor', funcao: 'pos_venda' }
  },

  // Horários
  horarios: {
    rotinaDiaria: '08:00',
    rotinaSemanal: '09:00',  // Segunda-feira
    rotinaMensal: '10:00',   // Dia 1
    verificacaoMetas: '17:00'
  },

  // Sazonalidade
  sazonalidade: {
    alto: [4, 5, 6, 10],     // Meses de alta temporada
    baixo: [1, 2, 12]        // Meses de baixa temporada
  }
};
```

## 🎯 OKRs do SolarOS

### Objetivo 1: Crescimento Sustentável
```
Key Results:
- KR1: Faturar R$ 12M até Dez/2026 (+20% vs 2025)
- KR2: Fechar 120 contratos (+25% vs 2025)
- KR3: Aumentar ticket médio para R$ 50.000 (+11%)
```

### Objetivo 2: Eficiência Operacional
```
Key Results:
- KR1: Reduzir ciclo de venda para 45 dias (-30%)
- KR2: Atingir 98% de satisfação do cliente
- KR3: Reduzir retrabalho para < 1%
```

### Objetivo 3: Escalabilidade
```
Key Results:
- KR1: Documentar 100% dos processos
- KR2: Treinar 2 novos vendedores
- KR3: Implementar 3 novas regiões
```

## 📞 Suporte e Evolução

Para dúvidas ou sugestões de melhoria:

1. Documente o problema/sugestão
2. Identifique qual módulo afeta
3. Proponha uma solução
4. Teste antes de implementar

---

**SolarOS v1.0** - Construído com ERTM ⚡
