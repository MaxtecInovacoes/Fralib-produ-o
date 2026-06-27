# 📐 GUIA TÉCNICO DE IMPLEMENTAÇÃO - SolarOS

## 1. ARQUITETURA DO SISTEMA

### 1.1 Estrutura de Diretórios
```
nexus-agents/
├── frontend/src/
│   ├── pages/
│   │   ├── SolarOS.tsx                    ← Dashboard principal
│   │   ├── solaros/
│   │   │   ├── Dashboard.tsx             ← Overview consolidado
│   │   │   ├── Commercial.tsx            ← Comercial (Franz)
│   │   │   ├── Finance.tsx               ← Financeiro (Eliene)
│   │   │   ├── Operations.tsx            ← Operações (Eliene)
│   │   │   ├── Production.tsx            ← Produção (Cleocir)
│   │   │   ├── PostSale.tsx              ← Pós-Venda (Igor)
│   │   │   ├── Team.tsx                  ← Gestão de equipe
│   │   │   ├── Metrics.tsx              ← Métricas e KPIs
│   │   │   └── Settings.tsx              ← Configurações
│   │   └── MarketingBrain.tsx            ← Já existe
│   ├── components/
│   │   └── solaros/
│   │       ├── Kanban.tsx                ← Componente reutilizável
│   │       ├── KPICard.tsx               ← Card de métrica
│   │       ├── TeamMember.tsx             ← Membro da equipe
│   │       ├── TaskCard.tsx              ← Card de tarefa
│   │       ├── Checklist.tsx             ← Checklist
│   │       ├── AlertBanner.tsx           ← Banner de alerta
│   │       └── MetricChart.tsx           ← Gráficos
│   ├── services/
│   │   ├── api.ts                        ← API client (já existe)
│   │   └── solarosApi.ts                ← Endpoints SolarOS
│   ├── stores/
│   │   └── solarosStore.ts              ← Zustand/Redux store
│   ├── hooks/
│   │   └── useSolarOS.ts                ← Hooks personalizados
│   └── types/
│       └── solaros.ts                   ← TypeScript types
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── solaros.py            ← API principal SolarOS
│   │   │       ├── solaros_commercial.py ← Comercial
│   │   │       ├── solaros_finance.py    ← Financeiro
│   │   │       ├── solaros_operations.py ← Operações
│   │   │       ├── solaros_production.py ← Produção
│   │   │       ├── solaros_post_sale.py  ← Pós-Venda
│   │   │       ├── solaros_team.py       ← Equipe
│   │   │       └── solaros_metrics.py    ← Métricas
│   │   ├── services/
│   │   │   ├── solaros_service.py        ← Serviço principal
│   │   │   ├── ertm_service.py           ← Cálculo de metas
│   │   │   ├── commercial_service.py     ← Lógica comercial
│   │   │   ├── finance_service.py       ← Lógica financeira
│   │   │   ├── operations_service.py     ← Lógica operações
│   │   │   ├── production_service.py     ← Lógica produção
│   │   │   ├── post_sale_service.py     ← Lógica pós-venda
│   │   │   └── notification_service.py   ← Notificações
│   │   ├── models/
│   │   │   ├── solaros_lead.py          ← Modelo Lead Solar
│   │   │   ├── solaros_operation.py     ← Modelo Operação
│   │   │   ├── solaros_team.py          ← Modelo Equipe
│   │   │   ├── solaros_task.py           ← Modelo Tarefa
│   │   │   ├── solaros_metric.py         ← Modelo Métrica
│   │   │   └── solaros_cost.py          ← Modelo Custo
│   │   └── main.py                       ← Registrar rotas
│   └── data/
│       └── nexus.db                      ← SQLite (já existe)
```

---

## 2. MODELAGEM DO BANCO DE DADOS

### 2.1 Tabela: team_members (Colaboradores)
```sql
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    whatsapp VARCHAR(20),
    role VARCHAR(100) NOT NULL,          -- 'owner', 'manager', 'technician', 'sales'
    department_key VARCHAR(50) NOT NULL,  -- 'commercial', 'finance', 'operations', 'production', 'post_sale'
    is_active BOOLEAN DEFAULT TRUE,
    hire_date DATE,
    salary DECIMAL(12,2),
    commission_rate DECIMAL(5,2),        -- Percentual de comissão
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_team_members_department ON team_members(department_key);
CREATE INDEX idx_team_members_active ON team_members(is_active);
```

### 2.2 Tabela: department_ownership (Responsáveis por Setor)
```sql
CREATE TABLE department_ownership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_key VARCHAR(50) NOT NULL,
    owner_id UUID REFERENCES team_members(id),
    substitute_id UUID REFERENCES team_members(id),
    effective_from DATE NOT NULL,
    effective_until DATE,
    reason VARCHAR(200),
    approved_by UUID REFERENCES team_members(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(department_key, effective_from)
);

CREATE INDEX idx_department_ownership_current ON department_ownership(department_key)
    WHERE effective_until IS NULL;
```

### 2.3 Tabela: solar_leads (Leads Solares - estende Lead existente)
```sql
CREATE TABLE solar_leads (
    id UUID PRIMARY KEY REFERENCES leads(id),  -- Herda de leads padrão
    team_id UUID REFERENCES teams(id),

    -- Dados do Cliente
    cpf VARCHAR(14),
    cnpj VARCHAR(18),
    address TEXT,
    address_city VARCHAR(100),
    address_state VARCHAR(2),
    property_type VARCHAR(50),              -- 'residential', 'commercial', 'rural'
    roof_type VARCHAR(50),                  -- 'ceramic', 'fiber_cement', 'metal', 'slab'
    has_shade BOOLEAN DEFAULT FALSE,

    -- Dados de Consumo
    average_consumption_kwh DECIMAL(10,2),  -- Consumo médio kWh
    average_bill DECIMAL(12,2),             -- Conta média R$
    tariff_type VARCHAR(50),                -- 'monophasic', 'biphasic', 'triphasic'
    panel_capacity_amps DECIMAL(6,2),        -- Capacidade do disjuntor
    roof_area_sqm DECIMAL(10,2),            -- Área do telhado m²
    roof_orientation VARCHAR(20),            -- 'N', 'S', 'L', 'O', etc
    distance_to_panel_meters DECIMAL(8,2),  -- Distância do padrão

    -- Classificação
    lead_score VARCHAR(20) DEFAULT 'cold',   -- 'hot', 'warm', 'cold'
    qualification_status VARCHAR(50),       -- 'qualified', 'disqualified', 'pending'
    qualification_notes TEXT,

    -- Sistema Proposto
    proposed_system_kwp DECIMAL(8,2),
    proposed_panels_qty INTEGER,
    proposed_inverter_qty INTEGER,
    estimated_payback_months INTEGER,
    estimated_irr DECIMAL(5,2),

    -- Dados Comerciais
    proposal_value DECIMAL(12,2),
    proposal_sent_at TIMESTAMP,
    contract_value DECIMAL(12,2),
    contract_signed_at TIMESTAMP,

    -- Origem
    source_detail VARCHAR(100),             -- 'facebook_lead_ads', 'google_ads', 'referral'
    campaign_id UUID REFERENCES campaigns(id),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.4 Tabela: solar_operations (Operações - estende SolarOperationRecord)
```sql
CREATE TABLE solar_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES solar_leads(id),

    department_key VARCHAR(50) NOT NULL,
    stage_key VARCHAR(50) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,  -- 'contact', 'qualification', 'visit', 'proposal', etc

    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open',      -- 'open', 'in_progress', 'review', 'done', 'blocked'
    priority VARCHAR(30) DEFAULT 'normal',  -- 'critical', 'high', 'normal', 'low'

    assigned_to UUID REFERENCES team_members(id),
    due_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Campos específicos por tipo
    amount DECIMAL(12,2),                  -- Valor financeiro
    notes TEXT,
    checklist JSONB DEFAULT '[]',         -- Array de {id, label, checked}
    attachments JSONB DEFAULT '[]',       -- URLs de anexos
    data JSONB DEFAULT '{}',               -- Dados extras flexíveis

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_solar_ops_department ON solar_operations(department_key);
CREATE INDEX idx_solar_ops_stage ON solar_operations(stage_key);
CREATE INDEX idx_solar_ops_status ON solar_operations(status);
CREATE INDEX idx_solar_ops_assigned ON solar_operations(assigned_to);
CREATE INDEX idx_solar_ops_due ON solar_operations(due_at) WHERE status != 'done';
```

### 2.5 Tabela: solar_costs (Custos)
```sql
CREATE TABLE solar_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES solar_leads(id),

    cost_type VARCHAR(50) NOT NULL,        -- 'fixed', 'variable', 'commission', 'material', etc
    category VARCHAR(100) NOT NULL,        -- 'salary', 'rent', 'marketing', 'material', etc
    subcategory VARCHAR(100),

    description VARCHAR(200),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',

    department_key VARCHAR(50),            -- Qual departamento gerou o custo
    operation_id UUID REFERENCES solar_operations(id),

    incurred_at DATE NOT NULL,
    paid_at TIMESTAMP,
    payment_method VARCHAR(50),            -- 'pix', 'boleto', 'transfer', 'cash'

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_solar_costs_type ON solar_costs(cost_type);
CREATE INDEX idx_solar_costs_category ON solar_costs(category);
CREATE INDEX idx_solar_costs_incurred ON solar_costs(incurred_at);
CREATE INDEX idx_solar_costs_department ON solar_costs(department_key);
```

### 2.6 Tabela: solar_revenues (Receitas)
```sql
CREATE TABLE solar_revenues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES solar_leads(id),

    revenue_type VARCHAR(50) NOT NULL,     -- 'contract', 'installment', 'commission', etc
    description VARCHAR(200),

    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',

    received_at DATE,
    payment_method VARCHAR(50),

    installment_number INTEGER,            -- Se for parcela
    total_installments INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_solar_revenues_received ON solar_revenues(received_at);
CREATE INDEX idx_solar_revenues_type ON solar_revenues(revenue_type);
```

### 2.7 Tabela: solar_metrics (Métricas Diárias)
```sql
CREATE TABLE solar_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    department_key VARCHAR(50) NOT NULL,

    metric_date DATE NOT NULL,

    -- Volume
    leads_new INTEGER DEFAULT 0,
    leads_contacted INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0,
    proposals_sent INTEGER DEFAULT 0,
    contracts_closed INTEGER DEFAULT 0,

    -- Financeiro
    revenue DECIMAL(14,2) DEFAULT 0,
    costs DECIMAL(14,2) DEFAULT 0,
    profit DECIMAL(14,2) DEFAULT 0,

    -- Conversão
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    avg_deal_size DECIMAL(12,2) DEFAULT 0,

    -- Operacional
    installations_completed INTEGER DEFAULT 0,
    inspections_passed INTEGER DEFAULT 0,
    homologations_approved INTEGER DEFAULT 0,
    maintenance_done INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, department_key, metric_date)
);

CREATE INDEX idx_solar_metrics_date ON solar_metrics(metric_date);
CREATE INDEX idx_solar_metrics_dept ON solar_metrics(department_key);
```

---

## 3. API ENDPOINTS

### 3.1 Rotas Principais (solaros.py)
```python
# backend/app/api/routes/solaros.py

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, date
from uuid import UUID

router = APIRouter(prefix="/api/solaros", tags=["solaros"])

# ============== TEAM MEMBERS ==============

@router.get("/team/members")
async def list_team_members(
    department_key: Optional[str] = None,
    is_active: bool = True
):
    """Lista membros da equipe com filtros"""
    pass

@router.post("/team/members")
async def create_team_member(payload: TeamMemberPayload):
    """Cria novo membro da equipe"""
    pass

@router.get("/team/members/{member_id}")
async def get_team_member(member_id: UUID):
    """Retorna detalhes de um membro"""
    pass

@router.put("/team/members/{member_id}")
async def update_team_member(member_id: UUID, payload: TeamMemberPayload):
    """Atualiza membro da equipe"""
    pass

@router.delete("/team/members/{member_id}")
async def deactivate_team_member(member_id: UUID):
    """Desativa membro (soft delete)"""
    pass

# ============== DEPARTMENT OWNERSHIP ==============

@router.get("/departments/ownership")
async def list_department_ownership():
    """Lista todos os setores com seus donos atuais"""
    pass

@router.post("/departments/ownership/transfer")
async def transfer_department_ownership(payload: TransferPayload):
    """Transfere responsabilidade de um setor"""
    pass

@router.get("/departments/ownership/history/{department_key}")
async def get_ownership_history(department_key: str):
    """Retorna histórico de trocas de responsável"""
    pass

# ============== OPERATIONS ==============

@router.get("/operations")
async def list_operations(
    department_key: Optional[str] = None,
    stage_key: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Lista operações com filtros e paginação"""
    pass

@router.post("/operations")
async def create_operation(payload: OperationPayload):
    """Cria nova operação/tarefa"""
    pass

@router.get("/operations/{operation_id}")
async def get_operation(operation_id: UUID):
    """Retorna detalhes de uma operação"""
    pass

@router.put("/operations/{operation_id}")
async def update_operation(operation_id: UUID, payload: OperationPayload):
    """Atualiza operação"""
    pass

@router.post("/operations/{operation_id}/move")
async def move_operation(
    operation_id: UUID,
    stage_key: str,
    status: str = "open"
):
    """Move operação para outra etapa do kanban"""
    pass

@router.post("/operations/{operation_id}/complete")
async def complete_operation(operation_id: UUID):
    """Marca operação como concluída"""
    pass

@router.post("/operations/{operation_id}/checklist")
async def update_checklist_item(
    operation_id: UUID,
    item_id: str,
    checked: bool
):
    """Atualiza item do checklist"""
    pass

# ============== LEADS SOLAR ==============

@router.get("/leads")
async def list_solar_leads(
    department_key: Optional[str] = None,
    stage: Optional[str] = None,
    lead_score: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    """Lista leads solares com filtros"""
    pass

@router.post("/leads")
async def create_solar_lead(payload: SolarLeadPayload):
    """Cria novo lead solar"""
    pass

@router.get("/leads/{lead_id}")
async def get_solar_lead(lead_id: UUID):
    """Retorna detalhes de um lead solar"""
    pass

@router.put("/leads/{lead_id}")
async def update_solar_lead(lead_id: UUID, payload: SolarLeadPayload):
    """Atualiza lead solar"""
    pass

@router.post("/leads/{lead_id}/qualify")
async def qualify_lead(lead_id: UUID, payload: QualificationPayload):
    """Qualifica lead com dados de consumo"""
    pass

@router.post("/leads/{lead_id}/convert")
async def convert_to_proposal(lead_id: UUID, payload: ProposalPayload):
    """Converte lead em proposta"""
    pass

# ============== FINANCES ==============

@router.get("/finances/summary")
async def get_financial_summary(
    date_from: date,
    date_to: date,
    department_key: Optional[str] = None
):
    """Retorna resumo financeiro do período"""
    pass

@router.get("/finances/costs")
async def list_costs(
    cost_type: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """Lista custos com filtros"""
    pass

@router.post("/finances/costs")
async def create_cost(payload: CostPayload):
    """Registra novo custo"""
    pass

@router.get("/finances/revenues")
async def list_revenues(
    revenue_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """Lista receitas"""
    pass

@router.post("/finances/revenues")
async def create_revenue(payload: RevenuePayload):
    """Registra nova receita"""
    pass

@router.get("/finances/cashflow")
async def get_cashflow(
    months: int = Query(6, le=12)
):
    """Retorna projeção de fluxo de caixa"""
    pass

# ============== METRICS & KPIs ==============

@router.get("/metrics/dashboard")
async def get_metrics_dashboard():
    """Retorna métricas consolidadas do dashboard"""
    pass

@router.get("/metrics/department/{department_key}")
async def get_department_metrics(
    department_key: str,
    period: str = "month"  # 'day', 'week', 'month', 'year'
):
    """Retorna métricas de um departamento"""
    pass

@router.get("/metrics/kpis")
async def get_kpis():
    """Retorna KPIs principais"""
    pass

@router.get("/metrics/funnel")
async def get_funnel_metrics():
    """Retorna métricas do funil de vendas"""
    pass

@router.get("/metrics/heatmap")
async def get_performance_heatmap(
    days: int = Query(30, le=365)
):
    """Retorna mapa de calor de performance"""
    pass

# ============== ERTM (Metas) ==============

@router.get("/ertm/goals")
async def get_goals(
    year: int = Query(default=None),
    month: int = Query(default=None)
):
    """Retorna metas configuradas"""
    pass

@router.post("/ertm/goals")
async def set_goals(payload: GoalsPayload):
    """Define metas para período"""
    pass

@router.get("/ertm/daily-tasks")
async def get_daily_tasks(
    date: Optional[date] = None,
    member_id: Optional[UUID] = None
):
    """Retorna tarefas diárias automaticamente geradas"""
    pass

@router.get("/ertm/gaps")
async def diagnose_gaps():
    """Diagnostica gargalos e gera alertas"""
    pass

@router.post("/ertm/diagnose")
async def run_diagnosis():
    """Executa diagnóstico completo (ERTM)"""
    pass

# ============== CHECKLISTS ==============

@router.get("/checklists/templates")
async def get_checklist_templates(
    operation_type: str
):
    """Retorna templates de checklist por tipo de operação"""
    pass

@router.post("/checklists/templates")
async def create_checklist_template(
    operation_type: str,
    items: List[ChecklistItemPayload]
):
    """Cria template de checklist"""
    pass

# ============== ALERTS & NOTIFICATIONS ==============

@router.get("/alerts")
async def get_alerts(
    department_key: Optional[str] = None,
    status: Optional[str] = None
):
    """Retorna alertas pendentes"""
    pass

@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: UUID):
    """Dispensar alerta"""
    pass

@router.post("/alerts/{alert_id}/action")
async def take_alert_action(
    alert_id: UUID,
    action: str,
    payload: Optional[dict] = None
):
    """Executa ação recomendada pelo alerta"""
    pass
```

---

## 4. SERVIÇOS (LÓGICA DE NEGÓCIO)

### 4.1 ERTM Service (Cálculo de Metas)
```python
# backend/app/services/ertm_service.py

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

class ERTMService:
    """Engenharia Reversa e Tração Métrica"""

    # Metas base anuais
    ANNUAL_GOALS = {
        "revenue": 2_400_000,      # R$ 2.4M em 2026
        "contracts": 60,           # 60 contratos
        "avg_ticket": 40_000,      # R$ 40k ticket médio
    }

    # Fator sazonal brasileiro
    SEASONAL_FACTOR = {
        1: 0.6,   # Janeiro - férias
        2: 0.7,   # Fevereiro - carnaval
        3: 0.9,   # Março
        4: 1.0,   # Abril
        5: 1.1,   # Maio
        6: 1.2,   # Junho - contas altas
        7: 1.1,   # Julho
        8: 1.0,   # Agosto
        9: 1.0,   # Setembro
        10: 1.1,  # Outubro
        11: 1.0,  # Novembro
        12: 0.7   # Dezembro - fim ano
    }

    def calculate_monthly_goal(self, metric: str, month: int = None) -> float:
        """Calcula meta mensal com fator sazonal"""
        if month is None:
            month = date.today().month

        annual = self.ANNUAL_GOALS.get(metric, 0)
        seasonal = self.SEASONAL_FACTOR.get(month, 1.0)

        return annual * seasonal / 12

    def calculate_weekly_goal(self, metric: str) -> float:
        """Calcula meta semanal (mensal / 4)"""
        monthly = self.calculate_monthly_goal(metric)
        return monthly / 4

    def calculate_daily_goal(self, metric: str) -> float:
        """Calcula meta diária (semanal / 5 dias úteis)"""
        weekly = self.calculate_weekly_goal(metric)
        return weekly / 5

    def get_all_daily_goals(self) -> Dict[str, Dict]:
        """Retorna todas as metas diárias por membro"""
        return {
            "Franz": {
                "contacts": self.calculate_daily_goal("contacts"),
                "proposals": self.calculate_daily_goal("proposals"),
                "closes": self.calculate_daily_goal("contracts"),
            },
            "Eliene": {
                "documents": 2,
                "purchases": 1,
                "homologations": 1,
            },
            "Cleocir": {
                "installations": 1,
                "inspections": 2,
                "homologations": 1,
            },
            "Igor": {
                "maintenances": 2,
                "reports": 5,
                "onboardings": 1,
            }
        }

    def diagnose_gaps(self, current_metrics: Dict) -> List[Dict]:
        """Diagnostica gargalos comparando atual vs meta"""
        gaps = []

        month = date.today().month
        year = date.today().year
        days_passed = date.today().day
        days_total = (date(year + 1, 1, 1) - date(year, 1, 1)).days

        # Calcular esperado até hoje
        expected_progress = days_passed / days_total

        for metric, value in current_metrics.items():
            monthly_goal = self.calculate_monthly_goal(metric, month)
            expected = monthly_goal * expected_progress
            actual = value

            if actual < expected * 0.8:
                gaps.append({
                    "metric": metric,
                    "status": "critical",
                    "expected": expected,
                    "actual": actual,
                    "gap": expected - actual,
                    "gap_percent": ((expected - actual) / expected * 100) if expected > 0 else 0,
                    "recommendation": self._get_recommendation(metric, actual, expected)
                })
            elif actual < expected * 0.95:
                gaps.append({
                    "metric": metric,
                    "status": "warning",
                    "expected": expected,
                    "actual": actual,
                    "gap": expected - actual,
                    "gap_percent": ((expected - actual) / expected * 100) if expected > 0 else 0,
                    "recommendation": self._get_recommendation(metric, actual, expected)
                })

        return gaps

    def _get_recommendation(self, metric: str, actual: float, expected: float) -> str:
        """Gera recomendação baseada no gargalo identificado"""
        gap_percent = ((expected - actual) / expected) * 100

        recommendations = {
            "revenue": f"Focar em fechar contratos. Necessário R$ {expected - actual:,.0f} adicionais.",
            "contracts": f"Necessário {int(expected - actual)} contratos adicionais. Priorizar proposals pendentes.",
            "proposals": f"Enviar {int(expected - actual)} propostas extras esta semana.",
            "contacts": f"Aumentar volume de contatos em {int(gap_percent)}%.",
        }

        return recommendations.get(metric, "Revisar processo e identificar gargalo.")

    def generate_daily_tasks(self, member: str, current_metrics: Dict) -> List[Dict]:
        """Gera tarefas diárias automaticamente baseado nos gaps"""
        tasks = []
        gaps = self.diagnose_gaps(current_metrics)

        # Franz - focar no maior gargalo
        if member == "Franz":
            worst_gap = min(gaps, key=lambda x: x["gap_percent"], default=None)
            if worst_gap:
                tasks.append({
                    "type": "critical",
                    "title": f"Focar em {worst_gap['metric']}",
                    "description": worst_gap["recommendation"],
                    "metric": worst_gap["metric"],
                    "target": worst_gap["expected"]
                })

            # Tarefas padrão
            tasks.extend([
                {"type": "normal", "title": "Ligar para leads do dia", "contacts": 20},
                {"type": "normal", "title": "Enviar propostas pendentes", "proposals": 5},
                {"type": "normal", "title": "Follow-up proposals abertas", "followups": 10},
            ])

        # Eliene - operações
        elif member == "Eliene":
            tasks.extend([
                {"type": "critical", "title": "Processar documentações pendentes"},
                {"type": "normal", "title": "Verificar status homologações"},
                {"type": "normal", "title": "Confirmar entregas de materiais"},
            ])

        # Cleocir - produção
        elif member == "Cleocir":
            tasks.extend([
                {"type": "critical", "title": "Concluir instalação do dia"},
                {"type": "normal", "title": "Realizar vistorias agendadas"},
                {"type": "normal", "title": "Verificar logística amanhã"},
            ])

        # Igor - pós-venda
        elif member == "Igor":
            tasks.extend([
                {"type": "critical", "title": "Verificar alertas de monitoramento"},
                {"type": "normal", "title": "Manutenções preventivas do dia"},
                {"type": "normal", "title": "Gerar relatórios pendentes"},
            ])

        return tasks
```

### 4.2 Commercial Service (Lógica Comercial)
```python
# backend/app/services/commercial_service.py

class CommercialService:

    STAGES = ["new", "contacted", "qualifying", "proposal", "negotiation", "won", "lost"]

    STAGE_LABELS = {
        "new": "Novo Lead",
        "contacted": "Contatado",
        "qualifying": "Qualificação",
        "proposal": "Proposta",
        "negotiation": "Negociacao",
        "won": "Fechado",
        "lost": "Perdido"
    }

    def qualify_lead(self, lead_id: UUID, data: QualificationData) -> Dict:
        """Qualifica lead com dados de consumo"""

        # Calcular sistema proposto
        monthly_kwh = data.average_consumption_kwh

        # Regra: 1kWp gera ~150kWh/mês no Brasil
        system_kwp = monthly_kwh / 150

        # Arredondar para cima
        system_kwp = ceil(system_kwp * 10) / 10

        # Calcular payback
        avg_bill = data.average_bill
        monthly_savings = avg_bill * 0.9  # 90% de economia

        system_cost = system_kwp * 4000  # R$ 4k por kWp
        payback_months = system_cost / monthly_savings

        # Classificar lead
        if data.average_bill >= 500 and system_kwp >= 5:
            score = "hot"
        elif data.average_bill >= 300 or system_kwp >= 3:
            score = "warm"
        else:
            score = "cold"

        return {
            "proposed_system_kwp": system_kwp,
            "estimated_panels": int(system_kwp * 4),  # 4 painéis por kWp
            "estimated_inverter_kw": system_kwp,
            "estimated_payback_months": int(payback_months),
            "estimated_monthly_savings": monthly_savings,
            "estimated_irr": self._calculate_irr(payback_months),
            "lead_score": score,
            "qualified": True
        }

    def _calculate_irr(self, payback_months: int) -> float:
        """Calcula TIR estimada"""
        # Payback de 60 meses = ~20% IRR
        # Payback de 48 meses = ~25% IRR
        # Payback de 36 meses = ~35% IRR
        return 1200 / payback_months  # Aproximação simples

    def move_stage(self, lead_id: UUID, new_stage: str) -> Dict:
        """Move lead para nova etapa"""

        if new_stage not in self.STAGES:
            raise ValueError(f"Stage inválido: {new_stage}")

        # Lógica de transição
        if new_stage == "won":
            # Gerar tarefa para Eliene (financeiro)
            self._create_followup_task(lead_id, "finance", "processar_contrato")

        elif new_stage == "lost":
            # Registrar motivo da perda
            self._log_loss_reason(lead_id)

        # Criar timeline
        self._create_timeline_event(lead_id, "stage_change", {
            "from": self.lead.stage,
            "to": new_stage
        })

        return {"success": True, "new_stage": new_stage}
```

---

## 5. FRONTEND - COMPONENTES CHAVE

### 5.1 Kanban Board Reutilizável
```tsx
// frontend/src/components/solaros/Kanban.tsx

import { useState, useCallback } from 'react';
import { DndContext, DragEndEvent, closestCenter } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

interface KanbanColumn {
  id: string;
  title: string;
  color: string;
  items: KanbanItem[];
}

interface KanbanItem {
  id: string;
  title: string;
  subtitle?: string;
  priority?: 'critical' | 'high' | 'normal' | 'low';
  assignee?: string;
  dueDate?: string;
  amount?: number;
  tags?: string[];
  metadata?: Record<string, any>;
}

interface KanbanProps {
  columns: KanbanColumn[];
  onItemMove?: (itemId: string, fromColumn: string, toColumn: string) => void;
  onItemClick?: (item: KanbanItem) => void;
  onColumnFilter?: (columnId: string) => void;
}

export function Kanban({ columns, onItemMove, onItemClick, onColumnFilter }: KanbanProps) {
  const [localColumns, setLocalColumns] = useState(columns);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Encontrar coluna de origem e destino
    let sourceCol: string | null = null;
    let destCol: string | null = null;
    let sourceItems: KanbanItem[] = [];
    let destItems: KanbanItem[] = [];

    for (const col of localColumns) {
      if (col.items.find(i => i.id === activeId)) {
        sourceCol = col.id;
        sourceItems = col.items;
      }
      if (col.items.find(i => i.id === overId) || col.id === overId) {
        destCol = col.id;
        destItems = col.items;
      }
    }

    if (sourceCol && destCol && onItemMove) {
      onItemMove(activeId, sourceCol, destCol);
    }
  }, [localColumns, onItemMove]);

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {localColumns.map(column => (
          <div
            key={column.id}
            className="flex-shrink-0 w-80 rounded-lg border bg-dark-300"
            style={{ borderColor: column.color }}
          >
            {/* Column Header */}
            <div className="p-3 border-b" style={{ borderColor: column.color }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: column.color }} />
                  <h3 className="font-semibold">{column.title}</h3>
                </div>
                <span className="badge">{column.items.length}</span>
              </div>
            </div>

            {/* Column Items */}
            <div className="p-2 space-y-2 min-h-[400px]">
              <SortableContext items={column.items.map(i => i.id)} strategy={verticalListSortingStrategy}>
                {column.items.map(item => (
                  <KanbanCard
                    key={item.id}
                    item={item}
                    color={column.color}
                    onClick={() => onItemClick?.(item)}
                  />
                ))}
              </SortableContext>

              {column.items.length === 0 && (
                <div className="border-2 border-dashed border-gray-700 rounded-lg p-4 text-center text-gray-500">
                  Sem itens
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </DndContext>
  );
}

interface KanbanCardProps {
  item: KanbanItem;
  color: string;
  onClick?: () => void;
}

function KanbanCard({ item, color, onClick }: KanbanCardProps) {
  const priorityColors = {
    critical: 'border-l-red-500',
    high: 'border-l-orange-500',
    normal: 'border-l-gray-500',
    low: 'border-l-blue-500',
  };

  return (
    <div
      className={`rounded-lg border bg-dark-400 p-3 cursor-pointer hover:bg-dark-200 transition-colors border-l-4 ${priorityColors[item.priority || 'normal']}`}
      onClick={onClick}
    >
      {/* Priority Badge */}
      {item.priority && (
        <span className={`text-xs px-2 py-0.5 rounded ${
          item.priority === 'critical' ? 'bg-red-500' :
          item.priority === 'high' ? 'bg-orange-500' :
          'bg-gray-600'
        }`}>
          {item.priority === 'critical' ? 'CRÍTICA' : item.priority.toUpperCase()}
        </span>
      )}

      {/* Title */}
      <h4 className="font-medium mt-2">{item.title}</h4>

      {/* Subtitle */}
      {item.subtitle && (
        <p className="text-sm text-gray-400 mt-1">{item.subtitle}</p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          {item.assignee && <span>👤 {item.assignee}</span>}
          {item.dueDate && <span>📅 {item.dueDate}</span>}
        </div>
        {item.amount && <span className="font-medium">R$ {item.amount.toLocaleString()}</span>}
      </div>

      {/* Tags */}
      {item.tags && (
        <div className="flex gap-1 mt-2">
          {item.tags.map(tag => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded bg-primary-500/20 text-primary-300">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

### 5.2 KPI Card Component
```tsx
// frontend/src/components/solaros/KPICard.tsx

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KPICardProps {
  label: string;
  value: number | string;
  goal?: number;
  previousValue?: number;
  format?: 'currency' | 'number' | 'percent' | 'days';
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
}

export function KPICard({
  label,
  value,
  goal,
  previousValue,
  format = 'number',
  icon,
  trend,
  trendLabel
}: KPICardProps) {
  // Formatar valor
  const formattedValue = (() => {
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL',
          minimumFractionDigits: 0
        }).format(Number(value));
      case 'percent':
        return `${Number(value).toFixed(1)}%`;
      case 'days':
        return `${value} dias`;
      default:
        return Number(value).toLocaleString('pt-BR');
    }
  })();

  // Calcular progresso
  const progress = goal ? (Number(value) / goal) * 100 : null;

  // Calcular tendência
  const trendPercent = previousValue
    ? ((Number(value) - previousValue) / previousValue) * 100
    : null;

  // Cor baseada no progresso
  const progressColor = progress === null ? '' :
    progress >= 100 ? 'text-emerald-400' :
    progress >= 80 ? 'text-green-400' :
    progress >= 50 ? 'text-yellow-400' :
    'text-red-400';

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* Label */}
          <p className="text-sm text-gray-400 uppercase tracking-wide">{label}</p>

          {/* Value */}
          <p className={`text-3xl font-bold mt-2 ${progressColor}`}>
            {formattedValue}
          </p>

          {/* Goal */}
          {goal !== undefined && (
            <div className="mt-2">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Meta</span>
                <span>{format === 'currency'
                  ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 0 }).format(goal)
                  : goal}</span>
              </div>
              <div className="h-2 bg-dark-300 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    progress >= 100 ? 'bg-emerald-500' :
                    progress >= 80 ? 'bg-green-500' :
                    progress >= 50 ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {progress?.toFixed(0)}% atingido
              </p>
            </div>
          )}

          {/* Trend */}
          {trendPercent !== null && (
            <div className={`flex items-center gap-1 mt-2 ${trendColor}`}>
              <TrendIcon className="h-4 w-4" />
              <span className="text-sm">
                {trendPercent > 0 ? '+' : ''}{trendPercent.toFixed(1)}%
              </span>
              {trendLabel && <span className="text-gray-500 text-xs">({trendLabel})</span>}
            </div>
          )}
        </div>

        {/* Icon */}
        {icon && (
          <div className="p-2 rounded-lg bg-dark-300">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 5.3 Dashboard Hook
```tsx
// frontend/src/hooks/useSolarOS.ts

import { useState, useEffect, useCallback } from 'react';
import { solarosApi } from '@/services/api';
import type {
  TeamMember,
  Department,
  Operation,
  SolarLead,
  FinancialSummary,
  MetricDashboard,
  Alert,
  Goal
} from '@/types/solaros';

interface UseSolarOSReturn {
  // Data
  members: TeamMember[];
  departments: Department[];
  operations: Operation[];
  leads: SolarLead[];
  financials: FinancialSummary | null;
  metrics: MetricDashboard | null;
  alerts: Alert[];
  goals: Goal[];

  // Loading states
  loading: boolean;
  error: string | null;

  // Actions
  refresh: () => Promise<void>;
  createOperation: (data: Partial<Operation>) => Promise<void>;
  moveOperation: (id: string, stage: string) => Promise<void>;
  completeOperation: (id: string) => Promise<void>;
  transferOwnership: (departmentKey: string, newOwnerId: string) => Promise<void>;
  updateGoal: (goal: Goal) => Promise<void>;
  dismissAlert: (alertId: string) => Promise<void>;
}

export function useSolarOS(departmentKey?: string): UseSolarOSReturn {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [operations, setOperations] = useState<Operation[]>([]);
  const [leads, setLeads] = useState<SolarLead[]>([]);
  const [financials, setFinancials] = useState<FinancialSummary | null>(null);
  const [metrics, setMetrics] = useState<MetricDashboard | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [
        membersData,
        departmentsData,
        operationsData,
        leadsData,
        financialsData,
        metricsData,
        alertsData,
        goalsData
      ] = await Promise.all([
        solarosApi.teamMembers(),
        solarosApi.departments(),
        departmentKey ? solarosApi.operations({ department_key: departmentKey }) : Promise.resolve([]),
        departmentKey ? solarosApi.leads({ department_key: departmentKey }) : Promise.resolve([]),
        solarosApi.financialSummary(),
        solarosApi.metricsDashboard(),
        solarosApi.alerts(),
        solarosApi.goals()
      ]);

      setMembers(membersData);
      setDepartments(departmentsData);
      setOperations(operationsData);
      setLeads(leadsData);
      setFinancials(financialsData);
      setMetrics(metricsData);
      setAlerts(alertsData);
      setGoals(goalsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  }, [departmentKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Actions
  const createOperation = async (data: Partial<Operation>) => {
    await solarosApi.createOperation(data);
    await refresh();
  };

  const moveOperation = async (id: string, stage: string) => {
    await solarosApi.moveOperation(id, stage);
    await refresh();
  };

  const completeOperation = async (id: string) => {
    await solarosApi.completeOperation(id);
    await refresh();
  };

  const transferOwnership = async (departmentKey: string, newOwnerId: string) => {
    await solarosApi.transferOwnership({ department_key: departmentKey, new_owner_id: newOwnerId });
    await refresh();
  };

  const updateGoal = async (goal: Goal) => {
    await solarosApi.updateGoal(goal);
    await refresh();
  };

  const dismissAlert = async (alertId: string) => {
    await solarosApi.dismissAlert(alertId);
    setAlerts(alerts.filter(a => a.id !== alertId));
  };

  return {
    members,
    departments,
    operations,
    leads,
    financials,
    metrics,
    alerts,
    goals,
    loading,
    error,
    refresh,
    createOperation,
    moveOperation,
    completeOperation,
    transferOwnership,
    updateGoal,
    dismissAlert
  };
}
```

---

## 6. SCRIPT DE MIGRAÇÃO DO BANCO

```sql
-- migrations/001_solaros_baseline.sql

-- 1. Adicionar colunas à tabela leads existente
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_score VARCHAR(20) DEFAULT 'cold';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS average_consumption_kwh DECIMAL(10,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS average_bill DECIMAL(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tariff_type VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS proposed_system_kwp DECIMAL(8,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS estimated_payback_months INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS proposal_value DECIMAL(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS contract_value DECIMAL(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS contract_signed_at TIMESTAMP;

-- 2. Criar novas tabelas
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    whatsapp VARCHAR(20),
    role VARCHAR(100) NOT NULL,
    department_key VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    hire_date DATE,
    salary DECIMAL(12,2),
    commission_rate DECIMAL(5,2),
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS department_ownership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_key VARCHAR(50) NOT NULL,
    owner_id UUID REFERENCES team_members(id),
    substitute_id UUID REFERENCES team_members(id),
    effective_from DATE NOT NULL,
    effective_until DATE,
    reason VARCHAR(200),
    approved_by UUID REFERENCES team_members(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(department_key, effective_from)
);

CREATE TABLE IF NOT EXISTS solar_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES leads(id),
    department_key VARCHAR(50) NOT NULL,
    stage_key VARCHAR(50) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(30) DEFAULT 'normal',
    assigned_to UUID REFERENCES team_members(id),
    due_at TIMESTAMP,
    completed_at TIMESTAMP,
    amount DECIMAL(12,2),
    notes TEXT,
    checklist JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS solar_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES leads(id),
    cost_type VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    description VARCHAR(200),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    department_key VARCHAR(50),
    operation_id UUID REFERENCES solar_operations(id),
    incurred_at DATE NOT NULL,
    paid_at TIMESTAMP,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS solar_revenues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    lead_id UUID REFERENCES leads(id),
    revenue_type VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    received_at DATE,
    payment_method VARCHAR(50),
    installment_number INTEGER,
    total_installments INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS solar_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id),
    department_key VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    leads_new INTEGER DEFAULT 0,
    leads_contacted INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0,
    proposals_sent INTEGER DEFAULT 0,
    contracts_closed INTEGER DEFAULT 0,
    revenue DECIMAL(14,2) DEFAULT 0,
    costs DECIMAL(14,2) DEFAULT 0,
    profit DECIMAL(14,2) DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    avg_deal_size DECIMAL(12,2) DEFAULT 0,
    installations_completed INTEGER DEFAULT 0,
    inspections_passed INTEGER DEFAULT 0,
    homologations_approved INTEGER DEFAULT 0,
    maintenance_done INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, department_key, metric_date)
);

-- 3. Inserir dados iniciais (equipe)
INSERT INTO team_members (id, name, email, phone, whatsapp, role, department_key, is_active, hire_date, commission_rate) VALUES
    (gen_random_uuid(), 'Franz', 'franz@empresa.com', '(11) 99999-0001', '(11) 99999-0001', 'owner', 'commercial', true, '2020-01-01', 3.00),
    (gen_random_uuid(), 'Eliene', 'eliene@empresa.com', '(11) 99999-0002', '(11) 99999-0002', 'manager', 'finance', true, '2021-03-15', 1.50),
    (gen_random_uuid(), 'Cleocir', 'cleocir@empresa.com', '(11) 99999-0003', '(11) 99999-0003', 'coordinator', 'production', true, '2021-06-01', 1.00),
    (gen_random_uuid(), 'Igor', 'igor@empresa.com', '(11) 99999-0004', '(11) 99999-0004', 'coordinator', 'post_sale', true, '2022-01-10', 0.50);

-- 4. Inserir estrutura de departamentos
INSERT INTO department_ownership (department_key, owner_id, effective_from, reason) VALUES
    ('commercial', (SELECT id FROM team_members WHERE name = 'Franz'), '2020-01-01', 'Fundador'),
    ('finance', (SELECT id FROM team_members WHERE name = 'Eliene'), '2021-03-15', 'Promoção'),
    ('production', (SELECT id FROM team_members WHERE name = 'Cleocir'), '2021-06-01', 'Promoção'),
    ('post_sale', (SELECT id FROM team_members WHERE name = 'Igor'), '2022-01-10', 'Contratação');

-- 5. Criar índices
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score);
CREATE INDEX idx_leads_contract ON leads(contract_value) WHERE contract_value IS NOT NULL;
CREATE INDEX idx_solar_ops_department ON solar_operations(department_key);
CREATE INDEX idx_solar_ops_stage ON solar_operations(stage_key);
CREATE INDEX idx_solar_ops_status ON solar_operations(status);
CREATE INDEX idx_solar_ops_due ON solar_operations(due_at) WHERE status != 'done';
CREATE INDEX idx_solar_costs_type ON solar_costs(cost_type);
CREATE INDEX idx_solar_costs_incurred ON solar_costs(incurred_at);
CREATE INDEX idx_solar_metrics_date ON solar_metrics(metric_date);
```

---

## 7. SEQUÊNCIA DE IMPLEMENTAÇÃO

### Fase 1: Foundation (Semana 1-2)
```bash
# 1. Executar migração do banco
psql -h localhost -U postgres -d nexus -f migrations/001_solaros_baseline.sql

# 2. Backend - Criar modelos
backend/app/models/solaros_lead.py
backend/app/models/solaros_operation.py
backend/app/models/solaros_team.py
backend/app/models/solaros_cost.py

# 3. Backend - Criar rotas básicas
backend/app/api/routes/solaros.py
backend/app/api/routes/solaros_team.py

# 4. Backend - Criar serviços
backend/app/services/solaros_service.py

# 5. Frontend - Tipos TypeScript
frontend/src/types/solaros.ts

# 6. Frontend - API Client
frontend/src/services/solarosApi.ts
```

### Fase 2: Core (Semana 3-4)
```bash
# 1. Backend - CRUD completo
backend/app/api/routes/solaros_commercial.py
backend/app/api/routes/solaros_finance.py
backend/app/api/routes/solaros_operations.py

# 2. Frontend - Componentes base
frontend/src/components/solaros/KPICard.tsx
frontend/src/components/solaros/Kanban.tsx
frontend/src/components/solaros/AlertBanner.tsx

# 3. Frontend - Página Dashboard
frontend/src/pages/solaros/Dashboard.tsx
```

### Fase 3: Features (Semana 5-6)
```bash
# 1. Backend - ERTM
backend/app/services/ertm_service.py
backend/app/api/routes/solaros_metrics.py

# 2. Frontend - Páginas por departamento
frontend/src/pages/solaros/Commercial.tsx
frontend/src/pages/solaros/Finance.tsx
frontend/src/pages/solaros/Production.tsx
frontend/src/pages/solaros/PostSale.tsx

# 3. Frontend - Hook personalizado
frontend/src/hooks/useSolarOS.ts
```

### Fase 4: Polish (Semana 7-8)
```bash
# 1. Notificações
backend/app/services/notification_service.py
WhatsApp integration

# 2. Relatórios
backend/app/api/routes/solaros_reports.py
frontend/src/pages/solaros/Reports.tsx

# 3. Integração com Marketing Brain
frontend/src/pages/MarketingBrain.tsx (expandir)
```

---

## 8. DEPENDÊNCIAS A INSTALAR

```bash
# Backend
pip install fastapi pydantic sqlalchemy asyncpg python-dateutil

# Frontend
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
npm install recharts  # Para gráficos
npm install date-fns  # Para datas
npm install zustand   # Para estado (ou usar Context API existente)
```

---

Este guia técnico fornece toda a base para implementação do SolarOS no Nexus. Cada seção pode ser executada independentemente seguindo a ordem das fases.
