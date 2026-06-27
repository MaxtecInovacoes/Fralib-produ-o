# 🔄 SolarOS - Adaptação ao Nexus Marketing Brain

## 📊 ANÁLISE DO QUE JÁ EXISTE

### Marketing Brain - O que tem hoje:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MARKETING BRAIN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🤖 AGENTES EXISTENTES                                                   │
│  ├── Orchestrator (Orquestrador)                                         │
│  ├── Meta Traffic (Meta Ads)                                              │
│  ├── CRM Quality (CRM Nexus)                                              │
│  ├── Creative Strategy (Criativos)                                        │
│  ├── Market Research (Pesquisa)                                           │
│  └── Governance (Governança)                                              │
│                                                                             │
│  📋 FUNCIONALIDADES                                                      │
│  ├── Dashboard com métricas                                                │
│  ├── Kanban operacional (todo/doing/review/blocked/done)                  │
│  ├── Planos (daily/weekly/monthly)                                        │
│  ├── Memória estratégica                                                  │
│  ├── Aprovações pendentes                                                 │
│  ├── Chat com agentes                                                     │
│  ├── Playbook diário                                                      │
│  └── Scheduler automático                                                 │
│                                                                             │
│  💾 DADOS                                                                │
│  ├── Teams                                                                │
│  ├── Agents                                                               │
│  ├── Plans                                                                │
│  ├── Tasks                                                                │
│  ├── Decisions                                                            │
│  ├── Approvals                                                            │
│  └── Memory                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 O QUE PRECISA SER ADICIONADO/ADAPTADO

### Comparativo: Desenhado vs Existente

```
┌─────────────────────────────────────┬────────────────┬──────────────────┐
│ FUNCIONALIDADE                     │ DESENHADO      │ EXISTE NO BRAIN  │
├─────────────────────────────────────┼────────────────┼──────────────────┤
│ Cadastro Colaboradores (humanos)    │ ✅ Completo    │ ❌ Não tem      │
│ Setores com Donos                  │ ✅ Completo    │ ⚠️ Parcial     │
│ Troca de Responsável               │ ✅ Completo    │ ❌ Não tem      │
│ Permissões Granulares              │ ✅ Completo    │ ❌ Não tem      │
│ Fluxo Leads (Prospecção→Contrato)  │ ✅ Completo    │ ⚠️ Só Marketing │
│ Controle Financeiro (custos/receita)│ ✅ Completo    │ ⚠️ Parcial     │
│ KPIs por Setor                     │ ✅ Completo    │ ❌ Não tem      │
│ Kanban Operacional                 │ ✅ Completo    │ ✅ Existe       │
│ Planos (daily/weekly/monthly)      │ ✅ Completo    │ ✅ Existe       │
│ Memória Estratégica                │ ✅ Completo    │ ✅ Existe       │
│ Aprovações                        │ ✅ Completo    │ ✅ Existe       │
│ Chat com Agentes                  │ ✅ Completo    │ ✅ Existe       │
│ Equipe de Agentes                 │ ✅ Completo    │ ✅ Existe       │
│ Checklist por Etapa                │ ✅ Completo    │ ❌ Não tem      │
│ Visitas Técnicas                   │ ✅ Completo    │ ❌ Não tem      │
│ Instalações                        │ ✅ Completo    │ ❌ Não tem      │
│ Homologações                       │ ✅ Completo    │ ❌ Não tem      │
│ Manutenção Pós-Venda               │ ✅ Completo    │ ❌ Não tem      │
│ Controle de Veículos               │ ✅ Completo    │ ❌ Não tem      │
│ Controle de Combustível            │ ✅ Completo    │ ❌ Não tem      │
└─────────────────────────────────────┴────────────────┴──────────────────┘

✅ = Tem completo    ⚠️ = Tem parcial    ❌ = Não tem
```

---

## 🔧 PLANO DE ADAPTAÇÃO

### Fase 1: Ampliar Marketing Brain para SolarOS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MARKETING BRAIN → SOLAROS BRAIN                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ANTES (Marketing Brain):                                                  │
│  ├── Agentes: Meta Traffic, CRM, Criativos, Pesquisa, Governança           │
│  └── Foco: Marketing e Campaigns                                            │
│                                                                             │
│  DEPOIS (SolarOS Brain):                                                   │
│  ├── Agentes Originais (mantidos)                                           │
│  │   ├── Meta Traffic                                                       │
│  │   ├── CRM Quality                                                        │
│  │   ├── Creative Strategy                                                  │
│  │   ├── Market Research                                                    │
│  │   └── Governance                                                         │
│  │                                                                         │
│  ├── Novos Agentes (adicionar)                                              │
│  │   ├── Sales Agent (Franz) - Comercial                                    │
│  │   ├── Finance Agent (Eliene) - Financeiro                                │
│  │   ├── Operations Agent (Eliene/Cleocir) - Operações                     │
│  │   ├── Installation Agent (Cleocir) - Produção                            │
│  │   ├── PostSale Agent (Igor) - Pós-Venda                                  │
│  │   └── ERTM Agent - Métricas e Metas                                     │
│  │                                                                         │
│  └── Foco: TODO o ciclo solar                                               │
│      ├── Marketing → Comercial → Financeiro → Operações                     │
│      ├── Produção → Instalação → Homologação → Pós-Venda                   │
│      └── Métricas → Metas → Alertas → Recomendações                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ ESTRUTURA PROPOSTA

### 1. AMPLIAR AGENTES EXISTENTES

```
📋 AGENTE CRM QUALITY (expandir)

ANTES:
├── Monitora leads
├── Verifica dados
└── Sugere qualificação

DEPOIS:
├── Monitora leads (mantido)
├── Verifica dados (mantido)
├── Qualificação comercial (novo)
│   ├── Verifica ICP
│   ├── Valida contato
│   └── Classifica (hot/morno/frio)
├── Dados financeiros (novo)
│   ├── Verifica conta de luz
│   ├── Valida CPF/CNPJ
│   └── Analisa score
└── Projetos (novo)
    ├── Acompanha documentação
    ├── Verifica prazos
    └── Alerta atrasos
```

```
📋 NOVO: SALES AGENT (Franz)

MISSÃO: "Gerenciar todo o ciclo comercial desde a prospecção até o contrato"

AGENTES SUBORDINADOS:
├── Prospection Agent
│   ├── Fontes: Facebook, Site, WhatsApp
│   ├── Qualification Agent
│   └── Proposal Agent

RESPONSABILIDADES:
├── Prospecção ativa
├── Qualificação de leads
├── Elaboração de propostas
├── Negociação
├── Fechamento de contratos
└── Acompanhamento

KANBAN ASSOCIADO:
├── new (novos leads)
├── contacted (contatados)
├── qualifying (qualificação)
├── proposal (proposta)
├── negotiation (negociação)
├── won (ganhos)
└── lost (perdidos)

TAREFAS DIÁRIAS:
├── Ligar para X leads
├── Enviar Y propostas
├── Acompanhar Z propostas pendentes
└── Fechar W contratos
```

```
📋 NOVO: FINANCE AGENT (Eliene)

MISSÃO: "Gerenciar toda a parte financeira desde a análise de crédito até o pagamento final"

RESPONSABILIDADES:
├── Análise de crédito
├── Processamento de financiamento
├── Liberação de pagamentos
├── Controle de recebimentos
├── Commissionamento
└── Fluxo de caixa

KANBAN ASSOCIADO:
├── credit_analysis (análise crédito)
├── financing (financiamento)
├── payment_pending (pagamento pendente)
├── payment_received (pagamento recebido)
└── paid (pago)
```

```
📋 NOVO: OPERATIONS AGENT (Eliene)

MISSÃO: "Coordenar orçamentos, projetos e compras de materiais"

RESPONSABILIDADES:
├── Visitas técnicas
├── Projetos 3D/SENGER
├── Listas de materiais
├── Compras de equipamentos
├── Acompanhamento de entregas
└── Controle de estoque

KANBAN ASSOCIADO:
├── technical_visit (visita técnica)
├── project_design (projeto/design)
├── materials_list (lista materiais)
├── purchase_order (pedido compra)
├── awaiting_delivery (aguardando entrega)
└── delivered (entregue)
```

```
📋 NOVO: INSTALLATION AGENT (Cleocir)

MISSÃO: "Gerenciar instalações desde a logística até a vistoria final"

RESPONSABILIDADES:
├── Programação de equipes
├── Logística de materiais
├── Instalações
├── Vistorias
├── Homologações
└── Controle de veículos

KANBAN ASSOCIADO:
├── scheduled (agendada)
├── logistics (em logística)
├── installation (em instalação)
├── inspection (vistoria)
├── homologation (homologação)
├── completed (concluída)
└── issues (com problemas)
```

```
📋 NOVO: POSTSALE AGENT (Igor)

MISSÃO: "Gerenciar pós-venda, manutenção e monitoramento"

RESPONSABILIDADES:
├── Cadastro em portais
├── Manutenções preventivas
├── Manutenções corretivas
├── Monitoramento de geração
├── Relatórios mensais
├── Indicações e expansões

KANBAN ASSOCIADO:
├── onboarding (cadastro)
├── monitoring (monitoramento)
├── preventive_maintenance (manutenção preventiva)
├── corrective_maintenance (manutenção corretiva)
├── reports (relatórios)
└── expansion (expansão/indicação)
```

```
📋 NOVO: ERTM AGENT (Métricas)

MISSÃO: "Calcular metas, diagnosticar gargalos e criar planos de ação"

RESPONSABILIDADES:
├── Cálculo de metas (anual/mensal/semanal/diário)
├── Diagnóstico de gargalos
├── Geração de tarefas automáticas
├── Alertas proativos
├── Recomendações de ação
└── Relatórios consolidados

DASHBOARD:
├── Metas do dia
├── Progresso semanal
├── Status mensal
├── Tendências
└── Comparativos
```

---

### 2. ESTRUTURA DE DEPARTAMENTOS EXPANDIDA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPARTAMENTOS NO SOLAROS BRAIN                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  department_key: "commercial"                                             │
│  ├── label: "Comercial"                                                    │
│  ├── owner: "Franz"                                                        │
│  ├── agents: ["sales_agent", "prospection_agent", "crm_quality"]           │
│  ├── stages: ["new", "contacted", "qualifying", "proposal",                 │
│  │           "negotiation", "won", "lost"]                                  │
│  └── description: "Prospecção, qualificação, proposta, negociação,          │
│                   contrato"                                                │
│                                                                             │
│  department_key: "finance"                                                 │
│  ├── label: "Financeiro"                                                   │
│  ├── owner: "Eliene"                                                      │
│  ├── agents: ["finance_agent"]                                             │
│  ├── stages: ["credit_analysis", "financing", "payment_pending",          │
│  │           "payment_received", "paid"]                                   │
│  └── description: "Crédito, financiamento, pagamentos, repasses"           │
│                                                                             │
│  department_key: "budgets"                                                 │
│  ├── label: "Orçamentos"                                                   │
│  ├── owner: "Eliene"                                                      │
│  ├── agents: ["operations_agent"]                                           │
│  ├── stages: ["technical_visit", "project_design", "materials_list",       │
│  │           "purchase_order", "awaiting_delivery", "delivered"]           │
│  └── description: "Visitas técnicas, projetos, listas, compras"          │
│                                                                             │
│  department_key: "production"                                               │
│  ├── label: "Produção"                                                     │
│  ├── owner: "Cleocir"                                                     │
│  ├── agents: ["installation_agent"]                                        │
│  ├── stages: ["scheduled", "logistics", "installation", "inspection",      │
│  │           "homologation", "completed", "issues"]                       │
│  └── description: "Logística, instalação, vistoria, homologação"          │
│                                                                             │
│  department_key: "post_sale"                                                │
│  ├── label: "Pós-Venda"                                                   │
│  ├── owner: "Igor"                                                        │
│  ├── agents: ["postsale_agent"]                                            │
│  ├── stages: ["onboarding", "monitoring", "preventive_maintenance",        │
│  │           "corrective_maintenance", "reports", "expansion"]             │
│  └── description: "Cadastro, manutenção, monitoramento, relatórios"       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3. TIPOS DE TAREFAS POR DEPARTAMENTO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TAREFAS POR DEPARTAMENTO                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📞 COMERCIAL (Franz)                                                      │
│  ├── type: "contact"                                                        │
│  │   ├── title: "Ligar para lead"                                          │
│  │   ├── fields: [telefone, horario, resultado]                            │
│  │   └── priority: based_on_lead_score                                     │
│  ├── type: "qualification"                                                 │
│  │   ├── title: "Qualificar lead"                                         │
│  │   ├── fields: [consumo_kwh, tipo_padrao, interesse]                    │
│  │   └── checklist: [verificou_conta, verificou_telhado]                  │
│  ├── type: "proposal"                                                       │
│  │   ├── title: "Enviar proposta"                                          │
│  │   ├── fields: [valor, payback, tir]                                    │
│  │   └── checklist: [projeto_anexado, analise_financeira]                 │
│  └── type: "contract"                                                       │
│      ├── title: "Fechar contrato"                                          │
│      ├── fields: [valor_final, forma_pagamento]                           │
│      └── checklist: [contrato_assinado, entrada_recebida]                  │
│                                                                             │
│  💰 FINANCEIRO (Eliene)                                                    │
│  ├── type: "credit_analysis"                                                │
│  │   ├── title: "Analisar crédito"                                       │
│  │   └── fields: [score, renda, restricao]                                │
│  ├── type: "financing"                                                      │
│  │   ├── title: "Processar financiamento"                                 │
│  │   └── fields: [banco, taxa, prazo, valor]                             │
│  ├── type: "payment"                                                        │
│  │   ├── title: "Registrar pagamento"                                     │
│  │   └── fields: [valor, forma, data, comprovante]                        │
│  └── type: "commission"                                                     │
│      ├── title: "Calcular comissão"                                        │
│      └── fields: [vendedor, valor_venda, percentual, comissao]            │
│                                                                             │
│  📋 ORÇAMENTOS (Eliene)                                                    │
│  ├── type: "technical_visit"                                                │
│  │   ├── title: "Realizar visita técnica"                                 │
│  │   ├── fields: [endereco, data, responsavel]                           │
│  │   ├── checklist: [fotos_telhado, medidas, sombreamento, padrao]       │
│  │   └── attachments: [fotos, video]                                      │
│  ├── type: "project"                                                        │
│  │   ├── title: "Elaborar projeto"                                        │
│  │   ├── fields: [potencia_kwp, modulos, inversores]                      │
│  │   └── attachments: [projeto_3d, unifilar, lista_materiais]            │
│  ├── type: "purchase"                                                       │
│  │   ├── title: "Comprar materiais"                                        │
│  │   ├── fields: [fornecedor, valor, prazo_entrega]                      │
│  │   └── checklist: [pedido_enviado, confirmacao_recebida]                 │
│  └── type: "delivery"                                                       │
│      ├── title: "Confirmar entrega"                                        │
│      └── fields: [nota_fiscal, itens_conferidos]                          │
│                                                                             │
│  🔧 PRODUÇÃO (Cleocir)                                                     │
│  ├── type: "installation_schedule"                                          │
│  │   ├── title: "Agendar instalação"                                      │
│  │   └── fields: [data, equipe, veiculo, materiais]                       │
│  ├── type: "installation"                                                   │
│  │   ├── title: "Instalar sistema"                                        │
│  │   ├── checklist: [estrutura_ok, modulos_ok, inversor_ok, cabos_ok]     │
│  │   └── photos: [antes, durante, depois]                                 │
│  ├── type: "inspection"                                                      │
│  │   ├── title: "Realizar vistoria"                                       │
│  │   └── checklist: [estrutura, eletrico, qualidade, documentacao]         │
│  └── type: "homologation"                                                   │
│      ├── title: "Acompanhar homologação"                                   │
│      └── fields: [distribuidora, protocolo, status, prazo]                │
│                                                                             │
│  🛠️ PÓS-VENDA (Igor)                                                      │
│  ├── type: "onboarding"                                                     │
│  │   ├── title: "Cadastrar cliente"                                       │
│  │   └── checklist: [portal_fabricante, portal_distribuidora, manual]      │
│  ├── type: "preventive_maintenance"                                        │
│  │   ├── title: "Manutenção preventiva"                                   │
│  │   ├── fields: [data, tipo, observacoes]                               │
│  │   └── checklist: [limpeza_modulos, conexoes, inversor]                  │
│  ├── type: "corrective_maintenance"                                         │
│  │   ├── title: "Manutenção corretiva"                                    │
│  │   └── fields: [problema, solucao, pecas_trocadas]                     │
│  ├── type: "report"                                                         │
│  │   ├── title: "Gerar relatório mensal"                                  │
│  │   └── fields: [geracao_kwh, economia_r, performance]                  │
│  └── type: "expansion"                                                      │
│      ├── title: "Acompanhar expansão"                                      │
│      └── fields: [potencia_adicional, orcamento, status]                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4. MÉTRICAS E KPIs POR DEPARTAMENTO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KPIs POR DEPARTAMENTO                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📞 COMERCIAL (Franz)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ LEAD (Volume)           │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Contacts/dia            │ 15      │ 20      │ 75%   │ 🟡           │  │
│  │ Propostas/dia           │ 4       │ 5       │ 80%   │ 🟡           │  │
│  │ Fechamentos/dia        │ 0.2     │ 0.5     │ 40%   │ 🔴           │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ TAXA DE CONVERSÃO       │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Contato→Qualificação    │ 50%     │ 60%     │ 83%   │ 🟢           │  │
│  │ Qualificação→Proposta   │ 30%     │ 40%     │ 75%   │ 🟡           │  │
│  │ Proposta→Contrato       │ 25%     │ 35%     │ 71%   │ 🟡           │  │
│  │ Global                  │ 3.8%    │ 8.4%    │ 45%   │ 🔴           │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ FINANCEIRO              │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Faturamento mensal      │ R$145K  │ R$200K  │ 72.5% │ 🟡           │  │
│  │ Contratos fechados      │ 4       │ 6       │ 67%   │ 🟡           │  │
│  │ Ticket médio            │ R$42K   │ R$40K   │ 105%  │ 🟢           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  💰 FINANCEIRO (Eliene)                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ INDICADOR               │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Análises crédito/dia     │ 3       │ 4       │ 75%   │ 🟡           │  │
│  │ Financiamentos processados│ 8      │ 10      │ 80%   │ 🟡           │  │
│  │ Pagamentos recebidos     │ R$180K  │ R$200K  │ 90%   │ 🟢           │  │
│  │ Inadimplência           │ 2%      │ <5%     │ OK    │ 🟢           │  │
│  │ Commissões pagas         │ R$15K   │ R$20K   │ 75%   │ 🟡           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  📋 ORÇAMENTOS (Eliene)                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ INDICADOR               │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Visitas técnicas/dia     │ 2       │ 3       │ 67%   │ 🟡           │  │
│  │ Projetos elaborados/dia  │ 2       │ 2       │ 100%  │ 🟢           │  │
│  │ Tempo médio projeto      │ 3 dias  │ 2 dias  │ 67%   │ 🟡           │  │
│  │ Compras no prazo        │ 90%     │ 95%     │ 95%   │ 🟢           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  🔧 PRODUÇÃO (Cleocir)                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ INDICADOR               │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Instalações/mês         │ 8       │ 10      │ 80%   │ 🟡           │  │
│  │ Instalações no prazo    │ 90%     │ 95%     │ 95%   │ 🟢           │  │
│  │ Vistorias aprovadas    │ 100%    │ 98%     │ 102%  │ 🟢           │  │
│  │ Homologações/mês       │ 6       │ 8       │ 75%   │ 🟡           │  │
│  │ Homologações no prazo   │ 85%     │ 90%     │ 94%   │ 🟢           │  │
│  │ Km rodados/mês         │ 2.500   │ 3.000   │ 83%   │ 🟡           │  │
│  │ Combustível (R$/mês)   │ R$2K    │ R$2.5K  │ 80%   │ 🟡           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  🛠️ PÓS-VENDA (Igor)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ INDICADOR               │ REAL    │ META    │ %     │ STATUS        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ Manutenções preventivas │ 6       │ 8       │ 75%   │ 🟡           │  │
│  │ Manutenções corretivas  │ 3       │ 5       │ 60%   │ 🔴           │  │
│  │ Tickets resolvidos      │ 95%     │ 98%     │ 97%   │ 🟢           │  │
│  │ Tempo resolução (h)     │ 18h     │ <24h    │ OK    │ 🟢           │  │
│  │ Relatórios gerados      │ 25      │ 30      │ 83%   │ 🟡           │  │
│  │ NPS (satisfação)        │ 85      │ 90      │ 94%   │ 🟢           │  │
│  │ Geração acumulada (MWh) │ 45      │ 50      │ 90%   │ 🟢           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5. FINANCEIRO CONSOLIDADO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD FINANCEIRO                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  💵 RESUMO FINANCEIRO - JUNHO 2026                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ RECEITA                                                              │  │
│  │ ├── Contratos fechados: 5 × R$42K = R$210.000                       │  │
│  │ ├── Entradas recebidas: R$65.000                                    │  │
│  │ ├── Parcelas recebidas: R$80.000                                    │  │
│  │ └── TOTAL RECEITA: R$145.000                                        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ CUSTOS                                                               │  │
│  │ ├── Custo fixo: R$15.000                                            │  │
│  │ │   ├── Aluguel: R$5.000                                           │  │
│  │ │   ├── Salários: R$8.000                                          │  │
│  │ │   └── Outros: R$2.000                                             │  │
│  │ ├── Custo variável: R$85.000                                        │  │
│  │ │   ├── Materiais: R$65.000                                        │  │
│  │ │   ├── Mão de obra: R$12.000                                      │  │
│  │ │   ├── Logística: R$5.000                                          │  │
│  │ │   └── Comissões: R$3.000                                          │  │
│  │ └── TOTAL CUSTOS: R$100.000                                        │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ RESULTADO                                                            │  │
│  │ ├── RECEITA: R$145.000                                              │  │
│  │ ├── CUSTOS: R$100.000                                               │  │
│  │ ├── LUCRO: R$45.000                                                 │  │
│  │ └── MARGEM: 31%                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  📊 CUSTOS POR SETOR                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ SETOR          │ CUSTO FIXO │ CUSTO VAR │ TOTAL    │ % RECEITA    │  │
│  ├────────────────┼────────────┼────────────┼──────────┼──────────────┤  │
│  │ Comercial      │ R$3.000    │ R$8.000    │ R$11.000 │ 7.6%         │  │
│  │ Financeiro     │ R$2.000    │ R$1.000    │ R$3.000  │ 2.1%         │  │
│  │ Orçamentos     │ R$3.000    │ R$2.000    │ R$5.000  │ 3.4%         │  │
│  │ Produção       │ R$5.000    │ R$70.000   │ R$75.000 │ 51.7%        │  │
│  │ Pós-Venda      │ R$2.000    │ R$4.000    │ R$6.000  │ 4.1%         │  │
│  ├────────────────┼────────────┼────────────┼──────────┼──────────────┤  │
│  │ TOTAL          │ R$15.000   │ R$85.000   │ R$100.000│ 69.0%        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  📈 PROJEÇÃO TRIMESTRAL                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ MÊS      │ RECEITA  │ CUSTOS   │ LUCRO   │ MARGEM  │ META   │ %   │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┼────────┼─────┤  │
│  │ Abril    │ R$180K   │ R$95K    │ R$85K   │ 47.2%   │ R$80K  │ 106%│  │
│  │ Maio     │ R$190K   │ R$100K   │ R$90K   │ 47.4%   │ R$85K  │ 106%│  │
│  │ Junho    │ R$145K   │ R$100K   │ R$45K   │ 31.0%   │ R$80K  │ 56% │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┼────────┼─────┤  │
│  │ TOTAL Q2 │ R$515K   │ R$295K   │ R$220K   │ 42.7%   │ R$245K │ 90% │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6. ERTM - METAS E ALERTAS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ERTM - ENGENHARIA REVERSA                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🎯 META ANUAL: R$ 2.400.000                                              │
│                                                                             │
│  DESDOBRAMENTO MENSAL:                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ MÊS      │ FATOR │ META      │ REAL     │ %     │ STATUS          │  │
│  ├──────────┼───────┼───────────┼──────────┼───────┼──────────────────┤  │
│  │ Janeiro   │ 0.6   │ R$120K   │ R$115K  │ 96%   │ 🟢              │  │
│  │ Fevereiro │ 0.7   │ R$140K   │ R$138K  │ 99%   │ 🟢              │  │
│  │ Março     │ 0.9   │ R$180K   │ R$175K  │ 97%   │ 🟢              │  │
│  │ Abril     │ 1.0   │ R$200K   │ R$180K  │ 90%   │ 🟡              │  │
│  │ Maio      │ 1.1   │ R$220K   │ R$190K  │ 86%   │ 🟡              │  │
│  │ Junho     │ 1.2   │ R$240K   │ R$145K  │ 60%   │ 🔴 ATRASADO     │  │
│  ├──────────┼───────┼───────────┼──────────┼───────┼──────────────────┤  │
│  │ ACUMULADO│ -     │ R$1.100K  │ R$943K  │ 86%   │ 🟡              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  📊 DIAGNÓSTICO DE GARGALO:                                                │
│                                                                             │
│  🔴 JUNHO ESTÁ COM 60% DA META - ATRASADO!                                │
│                                                                             │
│  ANÁLISE:                                                                  │
│  ├── Contratos fechados: 4 de 6 (67%)                                    │
│  ├── Leads qualificados: 25 de 30 (83%)                                  │
│  ├── Propostas enviadas: 22 de 28 (79%)                                  │
│  └── Taxa conversão global: 4/110 = 3.6% (meta: 8%)                      │
│                                                                             │
│  DIAGNÓSTICO:                                                              │
│  ├── Volume de propostas OK (79%)                                          │
│  ├── Qualificação OK (83%)                                                │
│  ├── 🔴 Taxa fechamento BAIXA (3.6% vs 8% meta)                           │
│  └── 🔴 Problema na NEGOCIAÇÃO/FECHAMENTO                                 │
│                                                                             │
│  💡 RECOMENDAÇÕES:                                                         │
│  1. Franz deve focar em fechar os 22 proposals pendentes                 │
│  2. Oferecer condições especiais de pagamento                             │
│  3. Priorizar leads HOT com maior intenção                                 │
│  4. Agendar calls de follow-up nas próximas 48h                           │
│                                                                             │
│  ⏰ PRAZO PARA RECUPERAR:                                                  │
│  ├── 10 dias úteis restantes em Junho                                     │
│  ├── Necessário: R$95K adicionais (4 contratos)                          │
│  ├── Estratégia: Fechar 1 contrato/dia útil                              │
│  └── Status: POSSÍVEL com ação imediata                                   │
│                                                                             │
│  📅 AÇÕES AUTOMÁTICAS GERADAS:                                              │
│  ├── Tarefa: Franz - Ligar para 5 proposals pendentes HOJE              │
│  ├── Tarefa: Franz - Agendar 3 calls de fechamento AMANHÃ             │
│  ├── Alerta: Eliene - Preparar documentação extra para fechamentos       │
│  └── Notificação: WhatsApp grupo com diagnóstico completo                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 TELAS PROPOSTAS

### Tela 1: Dashboard SolarOS Principal
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SolarOS                                              [🔔 3] [👤 Franz ▼]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SolarOS  │ Dashboard │ Comercial │ Financeiro │ Operações │ Pós-Venda  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DASHBOARD SOLAROS                              [⟳ Atualizar]       │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │ R$145K   │  │ R$100K   │  │ R$45K    │  │ 3.6%     │             │   │
│  │  │Receita   │  │ Custos   │  │ Lucro    │  │ Conversão│             │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │   │
│  │                                                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │ SETORES                            [Ver todos →]            │   │   │
│  │  ├──────────────────────────────────────────────────────────────┤   │   │
│  │  │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │   │   │
│  │  │ │COMERCIAL│ │FINANCEIRO│ │ORÇAMENT│ │PRODUÇÃO│ │PÓS-VENDA│   │   │
│  │  │ │Franz   │ │Eliene  │ │Eliene  │ │Cleocir │ │Igor    │        │   │
│  │  │ │🟢 80% │ │🟢 95% │ │🟡 85% │ │🟡 80% │ │🟢 90% │        │   │   │
│  │  │ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ ALERTAS 🚨                  │  │ METAS DO DIA 📅           │   │   │
│  │  ├─────────────────────────────┤  ├─────────────────────────────┤   │   │
│  │  │ 🔴 Junho 60% meta           │  │ Franz: 20 ligações (15/20) │   │   │
│  │  │ 🟡 Cleocir: 2 instalações  │  │ Franz: 5 propostas (4/5)   │   │   │
│  │  │ 🟡 Igor: 3 manutenções pen │  │ Eliene: 3 docs (3/3) ✓   │   │   │
│  │  │ 🟢 Tudo OK nos outros     │  │ Cleocir: 1 insta (1/1) ✓  │   │   │
│  │  └─────────────────────────────┘  └─────────────────────────────┘   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tela 2: Kanban por Departamento
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Comercial - Franz                                        [⚙️ Config]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [📊 KPIs] [📋 Kanban] [📈 Relatórios] [👥 Equipe] [⚙️ Config]           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ FILTROS: [Status ▼] [Dono ▼] [Prioridade ▼] [Data ▼] [🔍 Buscar]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │   NEW   │ │CONTACTED│ │QUALIF.  │ │PROPOSAL│ │NEGOTI. │ │   WON   │   │
│  │   (12)  │ │   (8)   │ │   (5)   │ │   (6)   │ │   (3)   │ │   (4)   │   │
│  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤   │
│  │ Maria S │ │ João A  │ │ Ana B   │ │ Carlos M│ │ Pedro R │ │ Lucia F│   │
│  │ SC      │ │ SP      │ │ RJ      │ │ MG      │ │ SP      │ │ R$45K  │   │
│  │ 🔴 HOT  │ │ 🟡 WARM │ │ 🟡 WARM │ │ 🟡 R$52K│ │ 🔴 R$38K│ │ ✅ PAGO │   │
│  │         │ │         │ │         │ │         │ │ ⏰ HOJE  │ │         │   │
│  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤   │
│  │ Roberto │ │ Teresa C│ │ Marcos O│ │ Fernanda│ │ Sofia L │ │ Roberto │   │
│  │ PR      │ │ RS      │ │ BA      │ │ PE      │ │ CE      │ │ R$42K  │   │
│  │ 🔴 HOT  │ │ 🔵 COLD │ │ 🟡 WARM │ │ 🟡 R$48K│ │ 🟡 R$55K│ │ ⏰ 05/07│   │
│  │         │ │         │ │         │ │ ⏰ HOJE  │ │         │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                             │
│  [+ Novo Lead]                      Total: 38 | Won: 4 | Lost: 2 | 76%    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 IMPLEMENTAÇÃO RECOMENDADA

### Fase 1: Integração (1-2 semanas)
- [ ] Conectar SolarOS com Marketing Brain existente
- [ ] Reutilizar estrutura de Teams, Plans, Tasks
- [ ] Adicionar novos departments
- [ ] Configurar novos agentes

### Fase 2: Funcionalidades (2-4 semanas)
- [ ] Cadastro de colaboradores (humanos)
- [ ] Kanban por departamento
- [ ] Métricas e KPIs
- [ ] Alertas automáticos

### Fase 3: Financeiro (2 semanas)
- [ ] Controle de custos por setor
- [ ] Controle de receitas
- [ ] Commissionamento
- [ ] Fluxo de caixa

### Fase 4: Operacional (2-3 semanas)
- [ ] Checklist por tipo de tarefa
- [ ] Visitas técnicas
- [ ] Instalações
- [ ] Homologações
- [ ] Pós-venda

### Fase 5: ERTM (1-2 semanas)
- [ ] Cálculo de metas
- [ ] Diagnóstico de gargalos
- [ ] Tarefas automáticas
- [ ] Notificações

---

## 📋 RESUMO DA ADAPTAÇÃO

### O que fazer com o Marketing Brain existente:

| Componente | Ação | Descrição |
|-----------|------|-----------|
| Orchestrator | MANTER | Orquestra todos os agentes |
| Meta Traffic | MANTER | Continua gerenciando ads |
| CRM Quality | EXPANDIR | Adicionar campos solares |
| Creative Strategy | MANTER | Cria criativos |
| Market Research | MANTER | Pesquisa de mercado |
| Governance | MANTER | Governança e compliance |
| Sales Agent | **ADICIONAR** | Ciclo comercial completo |
| Finance Agent | **ADICIONAR** | Controle financeiro |
| Operations Agent | **ADICIONAR** | Orçamentos e projetos |
| Installation Agent | **ADICIONAR** | Instalações e vistorias |
| PostSale Agent | **ADICIONAR** | Pós-venda e manutenção |
| ERTM Agent | **ADICIONAR** | Métricas e metas |

---

**Este documento serve como guia para adaptar o SolarOS ao Marketing Brain existente no Nexus.**
