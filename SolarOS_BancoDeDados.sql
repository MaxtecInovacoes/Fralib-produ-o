# SolarOS - Estrutura de Banco de Dados para Nexus

## 📊 Esquema de Tabelas

### 1. Tabela: METAS_ANUAIS
```sql
CREATE TABLE metas_anuais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    faturamento DECIMAL(15,2) NOT NULL,
    margem_liquida DECIMAL(5,4) NOT NULL,
    contratos INTEGER NOT NULL,
    clientes_novos INTEGER NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exemplo
INSERT INTO metas_anuais (ano, faturamento, margem_liquida, contratos, clientes_novos) VALUES
(2026, 12000000, 0.25, 120, 150);
```

### 2. Tabela: METAS_MENSAL
```sql
CREATE TABLE metas_mensais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    faturamento DECIMAL(15,2) NOT NULL,
    contratos INTEGER NOT NULL,
    novos_leads INTEGER NOT NULL,
    propostas_enviadas INTEGER NOT NULL,
    ligacoes_prospeccao INTEGER NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ano, mes) REFERENCES metas_anuais(ano, ano)
);

-- Exemplo
INSERT INTO metas_mensais (ano, mes, faturamento, contratos, novos_leads, propostas_enviadas, ligacoes_prospeccao) VALUES
(2026, 1, 1000000, 10, 50, 30, 100);
```

### 3. Tabela: METAS_SEMANAIS
```sql
CREATE TABLE metas_semanais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    faturamento DECIMAL(15,2),
    contratos INTEGER,
    novos_leads INTEGER,
    propostas_enviadas INTEGER,
    ligacoes_prospeccao INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Tabela: TAREFAS_DIARIAS
```sql
CREATE TABLE tarefas_diarias (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    membro VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    prioridade VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',
    concluida BOOLEAN DEFAULT FALSE,
    concluida_em TIMESTAMP,
    FOREIGN KEY (membro) REFERENCES usuarios(nome)
);

-- Exemplo
INSERT INTO tarefas_diarias (data, membro, tipo, descricao, prioridade) VALUES
(CURRENT_DATE, 'Franz', 'venda', 'Ligar para 20 novos leads', 'alta'),
(CURRENT_DATE, 'Franz', 'venda', 'Enviar 5 propostas comerciais', 'media'),
(CURRENT_DATE, 'Eliene', 'operacao', 'Documentar 3 contratos', 'alta');
```

### 5. Tabela: TAREFAS_SEMANAIS
```sql
CREATE TABLE tarefas_semanais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    semana INTEGER NOT NULL,
    membro VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',
    concluida BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (membro) REFERENCES usuarios(nome)
);
```

### 6. Tabela: TAREFAS_MENSAL
```sql
CREATE TABLE tarefas_mensais (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    membro VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',
    concluida BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (membro) REFERENCES usuarios(nome)
);
```

### 7. Tabela: KPIs_POR_ETAPA
```sql
CREATE TABLE kpis_por_etapa (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    etapa VARCHAR(50) NOT NULL,
    membro VARCHAR(50) NOT NULL,
    metrica VARCHAR(50) NOT NULL,
    valor DECIMAL(15,2) NOT NULL,
    meta DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    FOREIGN KEY (membro) REFERENCES usuarios(nome)
);

-- Exemplo
INSERT INTO kpis_por_etapa (data, etapa, membro, metrica, valor, meta, status) VALUES
(CURRENT_DATE, 'prospeccao', 'Franz', 'ligacoes', 15, 20, 'atraso'),
(CURRENT_DATE, 'prospeccao', 'Franz', 'propostas', 2, 5, 'atraso'),
(CURRENT_DATE, 'contratos', 'Eliene', 'documentacoes', 1, 3, 'atraso');
```

### 8. Tabela: CLIENTES_SOLAR
```sql
CREATE TABLE clientes_solares (
    id SERIAL PRIMARY KEY,
    nexus_id VARCHAR(50) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    origem VARCHAR(50) NOT NULL, -- facebook, trafego_pago, indicacao
    etapa_atual VARCHAR(50) NOT NULL, -- prospecto, qualificado, proposta, contrato, instalacao, pos_venda
    responsavel VARCHAR(50),
    consumo_medio DECIMAL(10,2),
    potencia_solicitada DECIMAL(10,2),
    valor_proposta DECIMAL(15,2),
    payback_estimado DECIMAL(5,2),
    tir_estimada DECIMAL(5,2),
    vpl_estimado DECIMAL(15,2),
    contrato_id VARCHAR(50),
    contrato_assinado BOOLEAN DEFAULT FALSE,
    contrato_data DATE,
    data_entrada DATE,
    endereco_completo TEXT,
    observacoes TEXT,
    status_lead BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 9. Tabela: CONTRATOS_SOLAR
```sql
CREATE TABLE contratos_solares (
    id SERIAL PRIMARY KEY,
    contrato_id VARCHAR(50) UNIQUE NOT NULL,
    cliente_id INTEGER REFERENCES clientes_solares(id),
    nome_cliente VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    endereco_completo TEXT NOT NULL,
    potencia_instalada DECIMAL(10,2) NOT NULL,
    inversor VARCHAR(100),
    modulos VARCHAR(100),
    valor_total DECIMAL(15,2) NOT NULL,
    forma_pagamento VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL, -- homologacao, compra, instalacao, concluido
    data_assinatura DATE,
    data_entrada DATE,
    data_prevista_instalacao DATE,
    data_real_instalacao DATE,
    documentacao_recebida BOOLEAN DEFAULT FALSE,
    checklist_completo BOOLEAN DEFAULT FALSE,
    homologacao_parecer TEXT,
    homologacao_data DATE,
    homologacao_status VARCHAR(50),
    responsavel_operacao VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 10. Tabela: INSTALACOES
```sql
CREATE TABLE instalacoes (
    id SERIAL PRIMARY KEY,
    os_id VARCHAR(50) UNIQUE NOT NULL,
    contrato_id INTEGER REFERENCES contratos_solares(id),
    cliente_id INTEGER REFERENCES clientes_solares(id),
    nome_cliente VARCHAR(100) NOT NULL,
    endereco_completo TEXT NOT NULL,
    data_agendada DATE,
    data_realizada DATE,
    equipe_alocada VARCHAR(100),
    equipe_integrantes TEXT,
    materiais_utilizados TEXT,
    fotos_anterior TEXT,
    fotos_instalacao TEXT,
    fotos_pos TEXT,
    relatorio_vistoria TEXT,
    checklist_seguranca TEXT,
    status VARCHAR(50) NOT NULL, -- agendado, em_andamento, concluido, revisao
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 11. Tabela: MANUTENCOES_POS_VENDA
```sql
CREATE TABLE mantencoes_pos_venda (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes_solares(id),
    contrato_id INTEGER REFERENCES contratos_solares(id),
    nome_cliente VARCHAR(100) NOT NULL,
    instalacao_id INTEGER REFERENCES instalacoes(id),
    data_ultima_manutencao DATE,
    data_proxima_manutencao DATE,
    tipo VARCHAR(50) NOT NULL, -- preventiva, corretiva, limpeza
    descricao TEXT,
    status VARCHAR(50) NOT NULL, -- agendado, realizado, pendente
    responsavel VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 12. Tabela: RELATORIOS_GENERADOS
```sql
CREATE TABLE relatorios_generados (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes_solares(id),
    instalacao_id INTEGER REFERENCES instalacoes(id),
    tipo_relatorio VARCHAR(50) NOT NULL, -- performance, faturamento, manutencao
    data_geracao DATE NOT NULL,
    arquivo_url TEXT,
    status VARCHAR(50) DEFAULT 'gerado',
    responsavel VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 13. Tabela: GARGALOS_IDENTIFICADOS
```sql
CREATE TABLE gargalos_identificados (
    id SERIAL PRIMARY KEY,
    membro VARCHAR(50) NOT NULL,
    etapa VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    impacto VARCHAR(50) NOT NULL,
    sugerido VARCHAR(200),
    status VARCHAR(50) DEFAULT 'aberto',
    data_identificacao DATE NOT NULL,
    data_resolucao DATE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 14. Tabela: ALERTAS_SISTEMA
```sql
CREATE TABLE alertas_sistema (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- atraso, oportunidade, risco, meta
    prioridade VARCHAR(20) NOT NULL, -- alta, media, baixa
    destinatario VARCHAR(50) NOT NULL,
    mensagem TEXT NOT NULL,
    lido BOOLEAN DEFAULT FALSE,
    lido_em TIMESTAMP,
    acao_requerida TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 15. Tabela: HISTORICO_METRICAS
```sql
CREATE TABLE historico_metricas (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    membro VARCHAR(50) NOT NULL,
    etapa VARCHAR(50) NOT NULL,
    metrica VARCHAR(50) NOT NULL,
    valor DECIMAL(15,2) NOT NULL,
    meta DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 16. Tabela: USUARIOS_EQUIPE
```sql
CREATE TABLE usuarios_equipe (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    funcao VARCHAR(50) NOT NULL, -- vendedor, operacoes, instalacao, pos_venda
    whatsapp VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ativo',
    meta_diaria DECIMAL(15,2),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exemplo
INSERT INTO usuarios_equipe (nome, funcao, whatsapp) VALUES
('Franz', 'vendedor', '+5511999999999'),
('Eliene', 'operacoes', '+5511999999998'),
('Cleocir', 'instalacao', '+5511999999997'),
('Igor', 'pos_venda', '+5511999999996');
```

## 🔄 Fluxos de Automação

### Fluxo 1: Transferência de Lead entre Etapas
```
Lead Novo (Franz)
    ↓ [48h sem contato]
Alerta de não contato
    ↓ [Qualificação feita]
Lead Qualificado (Franz)
    ↓ [Proposta enviada]
Proposta Enviada (Franz)
    ↓ [Contrato assinado]
Contrato Realizado (Franz)
    ↓ [Eliene valida]
Homologação (Eliene)
    ↓ [Compras feitas]
Instalação Agendada (Eliene)
    ↓ [Instalação realizada]
Pos-Venda (Igor)
```

### Fluxo 2: Geração Automática de Tarefas
```
Data Atual
    ↓
ERTM Agent calcula metas diárias
    ↓
Tarefas criadas para cada membro
    ↓
Enviadas via WhatsApp
    ↓
Membros atualizam status
    ↓
Agente verifica progresso
    ↓
Alertas se necessário
```

### Fluxo 3: Lembretes Automáticos
```
Data de Manutenção (7 dias antes)
    ↓
Alerta enviado para Igor
    ↓
Igor agenda visita
    ↓
Igor registra visita
    ↓
Data atualizada para +6 meses
```

## 📈 Índices para Performance

```sql
-- Índices para busca rápida
CREATE INDEX idx_kpis_data_membro ON kpis_por_etapa(data, membro);
CREATE INDEX idx_clientes_etapa ON clientes_solares(etapa_atual, status_lead);
CREATE INDEX idx_contratos_status ON contratos_solares(status);
CREATE INDEX idx_instalacoes_status ON instalacoes(status);
CREATE INDEX idx_alertas_destinatario ON alertas_sistema(destinatario, lido);
CREATE INDEX idx_tarefas_data_membro ON tarefas_diarias(data, membro);
CREATE INDEX idx_tarefas_status ON tarefas_diarias(status);

-- Índices para relatórios
CREATE INDEX idx_metricas_historico ON historico_metricas(data, membro, metrica);
CREATE INDEX idx_gargalos_status ON gargalos_identificados(status);
```

## 🚀 Inicialização do Sistema

```sql
-- Inicializa metas anuais
INSERT INTO metas_anuais (ano, faturamento, margem_liquida, contratos, clientes_novos)
SELECT 2026, 12000000, 0.25, 120, 150
WHERE NOT EXISTS (SELECT 1 FROM metas_anuais WHERE ano = 2026);

-- Inicializa metas mensais para os próximos 12 meses
INSERT INTO metas_mensais (ano, mes, faturamento, contratos, novos_leads, propostas_enviadas, ligacoes_prospeccao)
SELECT
    2026,
    m.mes,
    (SELECT faturamento FROM metas_anuais WHERE ano = 2026) / 12,
    (SELECT contratos FROM metas_anuais WHERE ano = 2026) / 12,
    (SELECT clientes_novos FROM metas_anuais WHERE ano = 2026) / 12,
    (SELECT clientes_novos FROM metas_anuais WHERE ano = 2026) / 4,
    (SELECT clientes_novos FROM metas_anuais WHERE ano = 2026)
FROM generate_series(1, 12) AS m(mes)
WHERE NOT EXISTS (
    SELECT 1 FROM metas_mensais WHERE ano = 2026 AND mes = m.mes
);

-- Inicializa usuários da equipe
INSERT INTO usuarios_equipe (nome, funcao, whatsapp) VALUES
('Franz', 'vendedor', '+5511999999999'),
('Eliene', 'operacoes', '+5511999999998'),
('Cleocir', 'instalacao', '+5511999999997'),
('Igor', 'pos_venda', '+5511999999996')
ON CONFLICT (nome) DO NOTHING;
```

## 📋 Views de KPIs

```sql
-- View de KPIs diários
CREATE VIEW kpis_diarios AS
SELECT
    m.nome AS membro,
    m.funcao,
    k.metrica,
    k.valor,
    k.meta,
    ROUND((k.valor / k.meta * 100), 2) AS percentual,
    k.status,
    k.data
FROM kpis_por_etapa k
JOIN usuarios_equipe m ON k.membro = m.nome
WHERE k.data = CURRENT_DATE;

-- View de tendências mensais
CREATE VIEW tendencias_mensais AS
SELECT
    membro,
    etapa,
    metrica,
    AVG(valor) AS media_mes,
    SUM(valor) AS total_mes,
    COUNT(*) AS registros
FROM historico_metricas
WHERE data >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
GROUP BY membro, etapa, metrica;

-- View de gargalos ativos
CREATE VIEW gargalos_ativos AS
SELECT
    g.id,
    g.membro,
    g.etapa,
    g.descricao,
    g.impacto,
    g.status,
    COUNT(*) OVER (PARTITION BY g.membro) AS qtd_gargalos
FROM gargalos_identificados g
WHERE g.status = 'aberto'
  AND g.data_identificacao >= CURRENT_DATE - INTERVAL '7 days';
```

Este esquema de banco de dados fornece:
- **Controle completo** de todas as etapas do ciclo solar
- **Métricas em tempo real** para cada membro
- **Gargalos identificados automaticamente**
- **Lembretes e alertas** proativos
- **Histórico completo** para análise
- **Views dinâmicas** para dashboard