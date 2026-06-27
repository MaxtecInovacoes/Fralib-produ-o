# 👥 Sistema de Gestão de Equipe e Responsáveis

## VISÃO GERAL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GESTÃO DE EQUIPE SOLAROS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  👔 ADMINISTRAÇÃO (Franz - Dono do Sistema)                              │
│  ┌───────────┬───────────┬───────────┬───────────┬─────────────────────┐  │
│  │ Cadastro  │Permissões │ Metas     │ Relatórios│ Configurações       │  │
│  │ Equipe    │Acessos   │ Sistema  │ Consolidados│ Sistema           │  │
│  └───────────┴───────────┴───────────┴───────────┴─────────────────────┘  │
│                                                                             │
│  👥 EQUIPE                                                                │
│  ┌───────────┬───────────┬───────────┬───────────┬─────────────────────┐  │
│  │ Comercial │Financeiro │Orçamento  │Produção   │ Pós-Venda           │  │
│  │ Franz     │Eliene    │Eliene    │Cleocir    │ Igor                │  │
│  └───────────┴───────────┴───────────┴───────────┴─────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ CADASTRO DE COLABORADORES

### 1.1 Dados Pessoais
```
👤 DADOS PESSOAIS
├── Identificação
│   ├── Nome completo *
│   ├── Nome social (se diferente)
│   ├── CPF *
│   ├── RG
│   ├── Data de nascimento *
│   ├── Naturalidade
│   ├── Nacionalidade
│   ├── Estado civil
│   ├── Gênero
│   └── Foto (upload)
│
├── Contato
│   ├── Telefone principal *
│   ├── Telefone secundário
│   ├── WhatsApp *
│   ├── E-mail pessoal *
│   ├── E-mail corporativo
│   └── Redes sociais
│       ├── LinkedIn
│       ├── Instagram
│       └── Facebook
│
├── Endereço
│   ├── CEP *
│   ├── Logradouro *
│   ├── Número *
│   ├── Complemento
│   ├── Bairro *
│   ├── Cidade *
│   ├── Estado *
│   └── Ponto de referência
│
└── Dados Familiares
    ├── Nome conjuge
    ├── CPF conjuge
    ├── Data nascimento conjuge
    ├── Quantidade filhos
    └── Contato emergência
```

### 1.2 Dados Profissionais
```
💼 DADOS PROFISSIONAIS
├── Cargo e Função
│   ├── Cargo *
│   │   ├── Proprietário/Sócio
│   │   ├── Gerente Comercial
│   │   ├── Vendedor
│   │   ├── Técnico Comercial
│   │   ├── Coordenador de Operações
│   │   ├── Engenheiro
│   │   ├── Projetista
│   │   ├── Coordenador de Instalações
│   │   ├── Instalador
│   │   ├── Coordenador Pós-Venda
│   │   ├── Técnico de Manutenção
│   │   ├── Analista Financeiro
│   │   ├── Assistente Administrativo
│   │   └── Outros
│   ├── Função atual *
│   ├── Departamento *
│   │   ├── Comercial
│   │   ├── Financeiro
│   │   ├── Operações
│   │   ├── Engenharia
│   │   ├── Produção
│   │   ├── Pós-Venda
│   │   └── Administrativo
│   ├── Cargo de referência
│   └── Data de admissão *
│
├── Formação
│   ├── Escolaridade
│   │   ├── Fundamental
│   │   ├── Médio
│   │   ├── Técnico
│   │   ├── Superior completo
│   │   ├── Superior cursando
│   │   └── Pós/Pós-MBA/Mestrado/Doutorado
│   ├── Curso principal
│   ├── Instituição
│   ├── Ano conclusão
│   └── Certificações
│       ├── NR-10 (Segurança Elétrica)
│       ├── NR-35 (Trabalho em Altura)
│       ├── CREA
│       ├── CERTIFICADOS FABRICANTES
│       └── Other certificações
│
├── Experiência
│   ├── Tempo de experiência no setor solar
│   ├── Empresas anteriores
│   ├── Funções anteriores
│   └── Projetos relevantes
│
└── Salário e Benefícios
    ├── Salário base (R$)
    ├── Vale transporte
    ├── Vale refeição
    ├── Plano de saúde
    ├── Plano odontológico
    ├── VR/VA
    ├── Bonificação/Comissão (%)
    ├── PRP
    └── Outros benefícios
```

### 1.3 Documentos
```
📄 DOCUMENTOS
├── Documentos Pessoais
│   ├── CPF (frente e verso)
│   ├── RG (frente e verso)
│   ├── CNH (se aplicável)
│   ├── Título de eleitor
│   ├── Certidão militar (homens)
│   └── Comprovante de escolaridade
│
├── Endereço
│   ├── Comprovante de residência
│   └── Conta de luz/água/gás
│
├── Trabalhistas
│   ├── CTPS (página foto e verso)
│   ├── Carteira de trabalho
│   ├── PIS/PASEP
│   ├── Reservista (homens)
│   └── Declaração de dependents
│
├── Financeiros
│   ├── Dados bancários
│   │   ├── Banco
│   │   ├── Agência
│   │   ├── Conta
│   │   └── Tipo (corrente/poupança)
│   └── Declaração IRRF
│
└── Contratuais
    ├── Contrato de trabalho
    ├── Acordo de confidencialidade
    ├── Termo de posse de equipamentos
    └── Termo de uso de veículo (se aplicável)
```

### 1.4 Equipamentos Cedidos
```
📱 EQUIPAMENTOS CEDIDOS
├── Equipamentos de Trabalho
│   ├── Notebook
│   │   ├── Marca/Modelo
│   │   ├── Número de série
│   │   ├── Patrimônio
│   │   ├── Data entrega
│   │   └── Status
│   ├── Celular
│   │   ├── Marca/Modelo
│   │   ├── IMEI
│   │   ├── Número linha
│   │   ├── Chip
│   │   ├── Data entrega
│   │   └── Status
│   ├── Tablet (se aplicável)
│   ├── Crachá
│   └── Outros equipamentos
│
├── Veículos (se aplicável)
│   ├── Marca/Modelo
│   ├── Placa
│   ├── Ano
│   ├── Chassi
│   ├── Combustível
│   ├── Km atual
│   ├── Data entrega
│   ├── Responsável manutenção
│   └── Status
│
└── Ferramentas/EPIs
    ├── Ferramentas manuais
    ├── EPIs (capacete, cinto, luvas, etc)
    ├── Equipamentos de medição
    └── Outros
```

---

## 2️⃣ ESTRUTURA ORGANIZACIONAL

### 2.1 Hierarquia
```
🏢 ESTRUTURA ORGANIZACIONAL

                    ┌─────────────────┐
                    │    FRANZ        │
                    │   Proprietário  │
                    │  Dono do Sistema│
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │  ELIENE   │    │  CLEOCIR  │    │   IGOR    │
    │ Coordenação│    │ Coordenação│    │ Coordenação│
    │ Operações │    │Produção  │    │ Pós-Venda │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
          │                │                │
    ┌─────┴─────┐    ┌─────┴─────┐    ┌─────┴─────┐
    │           │    │           │    │           │
    ▼           ▼    ▼           ▼    ▼           ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Vended.│ │Finance│ │Instal.│ │Técnico│ │Suporte│
│Auxiliar│ │Ass Adm│ │Auxiliar│ │Manut.│
└───────┘ └───────┘ └───────┘ └───────┘ └───────┘
```

### 2.2 Setores e Responsáveis
```
📊 SETORES E RESPONSAVEIS

┌─────────────────────────────────────────────────────────────────────────┐
│ SETOR              │ DONO ATUAL │ DONO ANTERIOR │ SUBSTITUTO TEMPORÁRIO│
├────────────────────┼────────────┼────────────────┼─────────────────────┤
│ Comercial          │ Franz      │ -              │ -                   │
│ Financeiro         │ Franz      │ -              │ -                   │
│ Operações          │ Eliene     │ -              │ -                   │
│ Projetos          │ Eliene     │ -              │ -                   │
│ Compras           │ Eliene     │ -              │ -                   │
│ Instalações       │ Cleocir    │ -              │ -                   │
│ Qualidade/Vistoria│ Cleocir    │ -              │ -                   │
│ Pós-Venda         │ Igor       │ -              │ -                   │
│ Manutenção        │ Igor       │ -              │ -                   │
│ Marketing         │ Franz      │ -              │ -                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ GESTÃO DE RESPONSÁVEIS

### 3.1 Cadastro de Setor
```
📋 CADASTRO DE SETOR
├── Identificação
│   ├── Nome do setor *
│   ├── Código interno
│   ├── Descrição
│   ├── Missão do setor
│   └── Objetivos principais
│
├── Dono (Owner)
│   ├── Responsável atual *
│   ├── Data início responsabilidade
│   ├── E-mail
│   ├── Telefone
│   ├── Foto
│   └── Slack/WhatsApp
│
├── Substituto
│   ├── Nome *
│   ├── Função
│   ├── E-mail
│   ├── Telefone
│   └── Data designação
│
├── Hierarquia
│   ├── Setor pai
│   ├── Setores subordinados
│   └── Relação com outros setores
│
├── Responsabilidades
│   ├── Lista de responsabilidades
│   ├── KPIs do setor
│   ├── SLAs internos
│   └── Metas definidas
│
├── Recursos
│   ├── Orcamento atribuído
│   ├── headcount
│   ├── Ferramentas/sistemas
│   └── Outros recursos
│
└── Metadados
    ├── Data criação
    ├── Criado por
    ├── Data última alteração
    └── Alterado por
```

### 3.2 Troca de Responsável
```
🔄 TROCA DE RESPONSÁVEL

┌─────────────────────────────────────────────────────────────────────┐
│ FORMULÁRIO DE TROCA DE RESPONSÁVEL                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Setor: [Dropdown com setores]                                       │
│                                                                      │
│ Responsável Atual:                                                   │
│ ├── Nome: João Silva                                                │
│ ├── Função: Coordenador                                            │
│ ├── E-mail: joao@empresa.com                                       │
│ ├── Data início: 01/01/2024                                        │
│ └── Motivo saída: Promoção / Demissão / Férias / Outro            │
│                                                                      │
│ Novo Responsável:                                                    │
│ ├── Nome: [Dropdown / busca]                                        │
│ ├── Função: [Auto-preenchido]                                      │
│ ├── E-mail: [Auto-preenchido]                                       │
│ └── Data início: [Date picker]                                       │
│                                                                      │
│ Substituto temporário (se necessário):                               │
│ ├── Nome: [Dropdown]                                                │
│ ├── Período: De ___ até ___                                         │
│ └── Motivo: Férias / Licença / Outro                               │
│                                                                      │
│ Transição:                                                          │
│ ├── [ ] Reunião de passagem de cargo realizada                     │
│ ├── [ ] Documentação transferida                                    │
│ ├── [ ] Acesso aos sistemas configurados                           │
│ ├── [ ] Equipe informada                                            │
│ ├── [ ] Clientes/parceiros avisados                                 │
│ └── Observações: _______________                                    │
│                                                                      │
│ Aprovação:                                                          │
│ ├── Aprovado por: Franz                                             │
│ └── Data aprovação: ___/___/______                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Histórico de Responsáveis
```
📜 HISTÓRICO DE RESPONSÁVEIS

Setor: Instalações

┌─────────────────────────────────────────────────────────────────────┐
│ Data       │ Responsável    │ Motivo           │ Aprovado por      │
├────────────┼───────────────┼──────────────────┼────────────────────┤
│ 01/01/2024│ Cleocir       │ Início do setor  │ Franz              │
│ 15/03/2024│ Cleocir       │ Férias (Cleocir) │ Franz              │
│           │ Temporário:    │                  │                    │
│           │ Pedro         │                  │                    │
├────────────┼───────────────┼──────────────────┼────────────────────┤
│ 01/06/2024│ Cleocir       │ Retorno férias   │ Franz              │
├────────────┼───────────────┼──────────────────┼────────────────────┤
│ 15/09/2024│ Cleocir       │ Promoção Cleocir │ Franz              │
│           │ Novo: Marcos  │                  │                    │
│           │ Temporário:   │                  │                    │
│           │ Cleocir subs. │                  │                    │
└────────────┴───────────────┴──────────────────┴────────────────────┘
```

---

## 4️⃣ PERMISSÕES E ACESSOS

### 4.1 Níveis de Permissão
```
🔐 NÍVEIS DE PERMISSÃO

┌─────────────────────────────────────────────────────────────────────┐
│ NÍVEL  │ DESCRIÇÃO                │ EXEMPLO                       │
├────────┼───────────────────────────┼─────────────────────────────── │
│ 1      │ Somente leitura          │ Estagiário                    │
│ 2      │ Leitura + Criar          │ Auxiliar administrativo        │
│ 3      │ Leitura + Criar + Editar │ Vendedor / Técnico            │
│ 4      │ Leitura + Criar + Editar │ Coordenador de setor          │
│        │ + Excluir (próprio)      │                               │
│ 5      │ Tudo + Excluir (todos)   │ Dono do setor                 │
│ 6      │ Tudo + Gerenciar equipe   │ Gerente / Diretor            │
│ 7      │ ADMIN TOTAL               │ Proprietário (Franz)          │
└────────┴───────────────────────────┴───────────────────────────────┘
```

### 4.2 Permissões por Setor
```
🔑 PERMISSÕES POR SETOR

┌──────────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ RECURSO      │ COMERCIAL│ FINANCEIRO│ORÇAMENTO│PRODUÇÃO │PÓS-VENDA│
├──────────────┼─────────┼─────────┼─────────┼─────────┼─────────┤
│ Leads        │ CRUD    │ Read    │ Read    │ Read    │ Read    │
│ Propostas    │ CRUD    │ Read    │ CRUD    │ Read    │ Read    │
│ Contratos    │ CRUD    │ CRUD    │ Read    │ Read    │ Read    │
│ Financeiro   │ Read    │ CRUD    │ Read    │ Read    │ Read    │
│ Projetos     │ Read    │ Read    │ CRUD    │ Read    │ Read    │
│ Compras      │ -       │ CRUD    │ CRUD    │ Read    │ -       │
│ Instalações  │ Read    │ Read    │ Read    │ CRUD    │ Read    │
│ Vistorias    │ Read    │ Read    │ Read    │ CRUD    │ Read    │
│ Homologações │ Read    │ Read    │ Read    │ CRUD    │ -       │
│ Manutenção   │ Read    │ Read    │ Read    │ Read    │ CRUD    │
│ Relatórios   │ Own     │ All     │ Own     │ Own     │ Own     │
│ Equipe       │ Own     │ Own     │ Own     │ Own     │ Own     │
│ Config       │ -       │ -       │ -       │ -       │ -       │
└──────────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

CRUD = Create, Read, Update, Delete
Read = Apenas visualização
Own = Apenas dados próprios
All = Todos os dados do setor
- = Sem acesso
```

### 4.3 Matriz de Acesso
```
📊 MATRIZ DE ACESSO

┌─────────────────────────────────────────────────────────────────────────┐
│ USUÁRIO     │ LEADS │ PROPOSTAS │ CONTRATOS │ FINANCEIRO │ PROJETOS │
├─────────────┼───────┼───────────┼───────────┼────────────┼──────────┤
│ Franz       │  ALL  │    ALL    │    ALL    │    ALL     │   ALL    │
│ Eliene      │ READ  │   CRUD    │    CRUD   │    CRUD    │   CRUD   │
│ Cleocir     │ READ  │   READ    │    READ   │    READ    │   READ   │
│ Igor        │ READ  │   READ    │    READ   │    READ    │   READ   │
│ Vendedor 2  │ CRUD  │   CRUD    │    -      │    -       │   -      │
│ Instalador  │ READ  │   READ    │    READ   │    -       │   READ   │
└─────────────┴───────┴───────────┴───────────┴────────────┴──────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ USUÁRIO     │ COMPRAS │INSTALAÇÕES│VISTORIAS │MANUTENÇÃO│ RELATÓRIOS │
├─────────────┼─────────┼───────────┼──────────┼──────────┼────────────┤
│ Franz       │   ALL   │    ALL    │   ALL    │   ALL    │    ALL     │
│ Eliene      │  CRUD   │    READ   │   READ   │   READ   │    ALL     │
│ Cleocir     │  READ   │   CRUD    │   CRUD   │   READ   │    OWN     │
│ Igor        │   -     │    READ   │   READ   │   CRUD   │    OWN     │
│ Vendedor 2  │   -     │    -     │   -      │   -      │    OWN     │
│ Instalador  │   -     │   CRUD   │   READ   │   CRUD   │    -       │
└─────────────┴─────────┴───────────┴──────────┴──────────┴────────────┘
```

---

## 5️⃣ FLUXO DE APROVAÇÕES

### 5.1 Tipos de Aprovação
```
✅ TIPOS DE APROVAÇÃO

┌─────────────────────────────────────────────────────────────────────┐
│ TIPO                │ APROVADOR PRINCIPAL │ SUBSTITUTO              │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ Proposta > R$50k    │ Franz               │ Eliene                  │
│ Proposta > R$100k   │ Franz               │ Franz (direto)           │
│ Contrato            │ Franz               │ Franz (direto)           │
│ Desconto > 5%       │ Franz               │ Eliene (até 10%)         │
│ Desconto > 10%     │ Franz               │ -                        │
│ Compra > R$10k      │ Eliene              │ Franz                    │
│ Compra > R$50k      │ Franz               │ -                        │
│ Adiantamento        │ Eliene              │ Franz                    │
│ Despesa extra      │ Franz               │ -                        │
│ Férias/Licença     │ Dono do setor       │ Dono do setor pai        │
│ Nova contratação    │ Franz               │ -                        │
│ Demissão            │ Franz               │ -                        │
│ Veículo novo       │ Franz               │ -                        │
│ Equipamento > R$5k │ Eliene              │ Franz                    │
└─────────────────────┴─────────────────────┴─────────────────────────┘
```

### 5.2 Fluxo de Aprovação de Proposta
```
📄 FLUXO APROVAÇÃO PROPOSTA

[Franz cria] ──► [Eliene verifica financials] ──► [Franz aprova]
     │                  │                        │
     ▼                  ▼                        ▼
  Draft          Análise Técnica          Aprovado
                                    │
                                    ▼
                             [Cliente assina]
                                    │
                                    ▼
                              [Eliene processa]
```

### 5.3 Fluxo de Troca de Responsável
```
🔄 FLUXO TROCA RESPONSÁVEL

[Solicitação] ──► [Franz aprova] ──► [Transição]
     │                  │                  │
     ▼                  ▼                  ▼
  Draft         Aprovado/Rejeitado   Novo dono assume
                                        │
                                        ▼
                                  [Comunicação]
                                        │
                                        ▼
                                  [Atualização SIS]
```

---

## 6️⃣ DASHBOARD DE GESTÃO

### 6.1 Visão Geral Equipe
```
📊 DASHBOARD - VISÃO GERAL

┌─────────────────────────────────────────────────────────────────────┐
│ EQUIPE SOLAROS                          [Franz - Admin] [⚙️ Config] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  👥 EQUIPE TOTAL: 4                                                 │
│  ├── Ativos: 4                                                      │
│  ├── Em férias: 0                                                   │
│  └── De licença: 0                                                  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ SETOR          │ DONO      │ STATUS │ TAREFAS │ ATENDIMENTO │    │
│  ├───────────────┼───────────┼────────┼─────────┼─────────────┤    │
│  │ Comercial     │ Franz     │ 🟢 OK  │   12    │    95%      │    │
│  │ Financeiro    │ Eliene    │ 🟢 OK  │    8    │   100%      │    │
│  │ Operações     │ Eliene    │ 🟢 OK  │    5    │    98%      │    │
│  │ Instalações   │ Cleocir   │ 🟡 Atenção│   3    │    85%      │    │
│  │ Pós-Venda    │ Igor      │ 🟢 OK  │   10    │    92%      │    │
│  └───────────────┴───────────┴────────┴─────────┴─────────────┘    │
│                                                                      │
│  ⚠️ ALERTAS:                                                        │
│  ├── Cleocir com 3 instalações atrasadas                             │
│  └── Igor com 2 manutenções pendentes                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Detalhamento por Setor
```
📊 DETALHAMENTO SETOR - INSTALAÇÕES

Setor: Instalações
Dono Atual: Cleocir
Substituto: Pedro (até 30/06)

Membros: 3
├── Cleocir (Coordenador)
├── João (Instalador Sênior)
└── Pedro (Instalador Jr.)

Métricas:
├── Instalações semana: 5/6
├── No prazo: 4
├── Atrasadas: 1
├── Vistorias: 4/5
└── Reaprovação: 0

Tarefas em Andamento:
├── OS #1234 - Cliente Silva - Agostinho - 50%
├── OS #1235 - Cliente Santos - Pinheiros - 75%
└── OS #1236 - Cliente Oliveira - Centro - 10%

Pendências:
├── 1 vistoria aguardando distribuidora
├── 2 homologações em análise
└── 1 material em atraso

⚠️ Alerta: Cleocir com 1 instalação atrasada (vencida ontem)
```

---

## 7️⃣ FORMULÁRIOS COMPLETOS

### 7.1 Cadastro de Colaborador
```
📝 FORMULÁRIO CADASTRO COLABORADOR

DADOS PESSOAIS
═══════════════════════════════════════════════════════════════
Nome completo: [________________________________] *
CPF: [_______________] *        Data nasc: [___/___/_____] *
RG: [_______________]          Expedição: [___/___/_____]   
Estado civil: [Dropdown]       Gênero: [Dropdown]            
Naturalidade: [________________________________]              
Nacionalidade: [Brasileira____________________]              
═══════════════════════════════════════════════════════════════

CONTATO
═══════════════════════════════════════════════════════════════
Tel. principal: [(__) ____-____] *   WhatsApp: [(__) ____-____] *
Tel. secundário: [(__) ____-____]                              
E-mail pessoal: [________________________________] *           
E-mail corporativo: [________________________________]         
═══════════════════════════════════════════════════════════════

ENDEREÇO
═══════════════════════════════════════════════════════════════
CEP: [__________] *  [Buscar]                                    
Logradouro: [________________________________________________] *
Número: [____] *    Complemento: [________________________]    
Bairro: [____________________] *                               
Cidade: [____________________] *    Estado: [Dropdown] *        
═══════════════════════════════════════════════════════════════

DADOS PROFISSIONAIS
═══════════════════════════════════════════════════════════════
Cargo: [Dropdown] *           Função: [________________________] *
Departamento: [Dropdown] *                                        
Data admissão: [___/___/_____] *                                
Salário base: [R$ ____________]                                 
Comissão (%): [_____%]                                          
═══════════════════════════════════════════════════════════════

FORMAÇÃO
═══════════════════════════════════════════════════════════════
Escolaridade: [Dropdown]                                        
Curso: [________________________________________________]       
Instituição: [________________________________________________]   
Conclusão: [______]                                            
═══════════════════════════════════════════════════════════════

CERTIFICAÇÕES
═══════════════════════════════════════════════════════════════
[ ] NR-10 (Segurança Elétrica)   Validade: [___/___/_____]    
[ ] NR-35 (Trabalho em Altura)    Validade: [___/___/_____]    
[ ] CREA                           Número: [_______________]      
[ ] Outro: [________________]     Validade: [___/___/_____]    
═══════════════════════════════════════════════════════════════

DADOS BANCÁRIOS
═══════════════════════════════════════════════════════════════
Banco: [Dropdown]               Agência: [_________]              
Conta: [_______________]        Tipo: [Corrente] [Poupança]     
═══════════════════════════════════════════════════════════════

                    [ ] Salvar como rascunho
                    [x] Salvar e ativar
                    [ ] Cancelar
```

### 7.2 Cadastro de Setor
```
📝 FORMULÁRIO CADASTRO DE SETOR

IDENTIFICAÇÃO
═══════════════════════════════════════════════════════════════
Nome do setor: [________________________] *                     
Código: [____]                                                 
Descrição: [__________________________________________________]  
Missão: [______________________________________________________
         ______________________________________________________]
═══════════════════════════════════════════════════════════════

RESPONSÁVEL ATUAL
═══════════════════════════════════════════════════════════════
Dono: [Dropdown colaboradores] *                                
E-mail: [Auto]                                                 
Telefone: [Auto]                                               
Data início: [___/___/_____]                                   
═══════════════════════════════════════════════════════════════

SUBSTITUTO
═══════════════════════════════════════════════════════════════
Nome: [Dropdown colaboradores]                                  
E-mail: [Auto]                                                 
Telefone: [Auto]                                               
═══════════════════════════════════════════════════════════════

RESPONSABILIDADES
═══════════════════════════════════════════════════════════════
1. [__________________________________________________________]
2. [__________________________________________________________]
3. [__________________________________________________________]
4. [__________________________________________________________]
5. [__________________________________________________________]
═══════════════════════════════════════════════════════════════

KPIs DO SETOR
═══════════════════════════════════════════════════════════════
KPI 1: [________________________]   Meta: [________]             
KPI 2: [________________________]   Meta: [________]             
KPI 3: [________________________]   Meta: [________]             
═══════════════════════════════════════════════════════════════

RECURSOS
═══════════════════════════════════════════════════════════════
Orçamento mensal: [R$ ____________]                              
Headcount: [___]                                               
Sistemas: [__________________________________________________]
═══════════════════════════════════════════════════════════════

                    [ ] Salvar
                    [ ] Cancelar
```

### 7.3 Troca de Responsável
```
📝 FORMULÁRIO TROCA DE RESPONSÁVEL

SETOR
═══════════════════════════════════════════════════════════════
Selecione o setor: [Dropdown] *                                
═══════════════════════════════════════════════════════════════

RESPONSÁVEL ATUAL
═══════════════════════════════════════════════════════════════
Nome: [Auto]                                                   
Função: [Auto]                                                 
E-mail: [Auto]                                                 
Data início: [Auto]                                            
Motivo da saída: [Dropdown] *                                   
├── Aposentadoria
├── Desligamento
├── Promoção/Transferência
├── Férias (> 15 dias)
├── Licença médica
├── Licença maternidade/paternidade
└── Outro: [_____________]
═══════════════════════════════════════════════════════════════

NOVO RESPONSÁVEL
═══════════════════════════════════════════════════════════════
Nome: [Dropdown / Busca] *                                      
Função: [Auto]                                                  
E-mail: [Auto]                                                  
Data início: [Date picker] *                                    
═══════════════════════════════════════════════════════════════

SUBSTITUTO TEMPORÁRIO (opcional)
═══════════════════════════════════════════════════════════════
Nome: [Dropdown]                                                
Período: De [___/___/_____] até [___/___/_____]               
Motivo: [Dropdown]                                              
═══════════════════════════════════════════════════════════════

CHECKLIST DE TRANSIÇÃO
═══════════════════════════════════════════════════════════════
[ ] Reunião de passagem de cargo realizada                     
    Data: [___/___/_____]                                       
    Duração: [___] minutos                                      
                                                             
[ ] Pasta de documentos transferida                            
[ ] Acesso aos sistemas configurados                           
    ├── Sistema 1: [OK]                                       
    ├── Sistema 2: [Pendente]                                  
    └── Sistema 3: [OK]                                        
                                                             
[ ] Equipe informada                                           
    Data comunicação: [___/___/_____]                           
                                                             
[ ] Clientes/parceiros-chave avisados (se aplicável)          
    Quantos: [___]                                             
                                                             
[ ] Relatório de transição elaborado                           
═══════════════════════════════════════════════════════════════

OBSERVAÇÕES
═══════════════════════════════════════════════════════════════
[______________________________________________________________
 _____________________________________________________________]
═══════════════════════════════════════════════════════════════

APROVAÇÃO
═══════════════════════════════════════════════════════════════
Solicitante: [Auto]                                            
Aprovado por: [Dropdown] *                                     
Data aprovação: [___/___/_____]                                 
Assinatura: [________________________]                          
═══════════════════════════════════════════════════════════════

              [ ] Salvar rascunho
              [x] Executar troca
              [ ] Cancelar
```

---

## 8️⃣ RELATÓRIOS

### 8.1 Relatório de Equipe
```
📊 RELATÓRIO DE EQUIPE

Período: [___/___/_____] a [___/___/_____]

RESUMO
═══════════════════════════════════════════════════════════════
Total colaboradores: 4
Ativos: 4
Férias: 0
Licença: 0
Desligados: 0
Novos admits: 0
═══════════════════════════════════════════════════════════════

POR SETOR
═══════════════════════════════════════════════════════════════
┌────────────┬────────┬──────┬───────┬───────┬────────────┐
│ Setor      │ Dono   │ Membros│ Tarefas│ Atrasos│ Performance│
├────────────┼────────┼───────┼────────┼────────┼────────────┤
│ Comercial  │ Franz  │   2   │   45   │    2   │    95.5%   │
│ Operações  │ Eliene │   1   │   28   │    0   │   100.0%   │
│ Instalações│ Cleocir│   3   │   35   │    3   │    85.7%   │
│ Pós-Venda  │ Igor   │   2   │   22   │    1   │    95.5%   │
└────────────┴────────┴───────┴────────┴────────┴────────────┘

MÉTRICAS GERAIS
═══════════════════════════════════════════════════════════════
Tasks concluídas: 130
Tasks atrasadas: 6
Taxa conclusão: 95.6%
Tempo médio resposta: 2.3h
Satisfação interna: 4.5/5.0
═══════════════════════════════════════════════════════════════
```

### 8.2 Relatório de Responsáveis
```
📊 RELATÓRIO DE RESPONSÁVEIS

┌────────────┬─────────────┬─────────────┬─────────────┬─────────┐
│ Setor      │ Dono atual  │ Desde       │ Substituto  │ Status  │
├────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ Comercial  │ Franz       │ 01/01/2020  │ -           │ 🟢 OK   │
│ Financeiro │ Franz       │ 01/01/2020  │ -           │ 🟢 OK   │
│ Operações  │ Eliene      │ 15/03/2022  │ -           │ 🟢 OK   │
│ Projetos   │ Eliene      │ 15/03/2022  │ -           │ 🟢 OK   │
│ Compras    │ Eliene      │ 01/06/2023  │ -           │ 🟢 OK   │
│ Instalações│ Cleocir     │ 01/08/2021  │ Pedro       │ 🟡 Atenção│
│ Pós-Venda  │ Igor        │ 01/01/2023  │ -           │ 🟢 OK   │
└────────────┴─────────────┴─────────────┴─────────────┴─────────┘

TROCAS NO PERÍODO
═══════════════════════════════════════════════════════════════
Não houve trocas no período selecionado.
═══════════════════════════════════════════════════════════════
```

---

## 9️⃣ CONFIGURAÇÕES DO SISTEMA

### 9.1 Configurações Gerais
```
⚙️ CONFIGURAÇÕES - EQUIPE

GERAL
═══════════════════════════════════════════════════════════════
Empresa: [Solar Energia Ltda____]
CNPJ: [__.___.___/____-__]
Logo: [Upload]

ADMINISTRADORES
═══════════════════════════════════════════════════════════════
Usuários com acesso total:
├── Franz (proprietário)
└── [Adicionar mais]

DIRETÓRIOS
═══════════════════════════════════════════════════════════════
├── Comercial: /commercial
├── Financeiro: /financial
├── Operações: /operations
├── Projetos: /projects
├── Instalações: /installations
└── Pós-Venda: /post-sale

NOTIFICAÇÕES
═══════════════════════════════════════════════════════════════
[ ] Notificar troca de responsável por e-mail
[ ] Notificar troca de responsável por Slack
[x] Notificar troca de responsável por WhatsApp
[x] Notificar tarefas pendentes por WhatsApp
[x] Alertas de atrasos por WhatsApp

RETENÇÃO DE DADOS
═══════════════════════════════════════════════════════════════
[x] Manter histórico de trocas: Indefinido
[x] Manter logs de acesso: 12 meses
[ ] Permitir exclusão de colaboradores
═══════════════════════════════════════════════════════════════
```

---

Este documento complementa o **Mapa Mental SolarOS** com toda a estrutura necessária para:

1. ✅ **Cadastro completo** de colaboradores
2. ✅ **Gestão de setores** com donos e substitutos
3. ✅ **Troca de responsáveis** com workflow de aprovação
4. ✅ **Permissões granulares** por setor e recurso
5. ✅ **Fluxos de aprovação** configuráveis
6. ✅ **Dashboards** de acompanhamento
7. ✅ **Relatórios** gerenciais
8. ✅ **Configurações** do sistema

Juntos, os dois documentos (**SolarOS_Mapas_Mentais.md** e **SolarOS_Equipe_Gestao.md**) formam a especificação completa para implementação do sistema.
