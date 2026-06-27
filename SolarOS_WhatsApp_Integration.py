# SolarOS - Dashboard Central e Integração WhatsApp

## 📊 Dashboard Principal (HTML/CSS/JS)

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SolarOS - Dashboard Central</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #1a73e8;
            --success-color: #34a853;
            --warning-color: #fbbc04;
            --danger-color: #ea4335;
            --dark-color: #202124;
        }

        body {
            background-color: #f8f9fa;
            font-family: 'Roboto', sans-serif;
        }

        .metric-card {
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-2px);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .metric-label {
            color: #5f6368;
            font-size: 0.9rem;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }

        .status-atraso { background-color: var(--danger-color); }
        .status-normal { background-color: var(--success-color); }
        .status-alerta { background-color: var(--warning-color); }

        .kanban-column {
            min-height: 400px;
            background: #f1f3f4;
            border-radius: 8px;
            padding: 12px;
        }

        .kanban-item {
            background: white;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: move;
        }

        .heat-map {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 4px;
            margin-top: 20px;
        }

        .heat-cell {
            aspect-ratio: 1;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: bold;
            color: white;
        }

        .heat-low { background-color: #81c784; }
        .heat-medium { background-color: #ffb74d; }
        .heat-high { background-color: #e57373; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-solar-panel"></i> SolarOS
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text">
                    <i class="fas fa-user-circle"></i> Franz
                </span>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- KPIs Principais -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <div class="metric-value text-primary">R$ 850k</div>
                        <div class="metric-label">Faturamento Mês</div>
                        <small class="text-success">↑ 15% vs mês anterior</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <div class="metric-value text-success">8</div>
                        <div class="metric-label">Contratos Fechados</div>
                        <small class="text-success">Meta: 10</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <div class="metric-value text-warning">45</div>
                        <div class="metric-label">Novos Leads</div>
                        <small class="text-danger">↓ 20% vs meta</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <div class="metric-value text-info">92%</div>
                        <div class="metric-label">Satisfação</div>
                        <small class="text-success">↑ 5% vs média</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Status da Equipe -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-users"></i> Status da Equipe</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Membro</th>
                                        <th>Função</th>
                                        <th>Meta Diária</th>
                                        <th>Realizado</th>
                                        <th>Status</th>
                                        <th>Última Atualização</th>
                                    </tr>
                                </thead>
                                <tbody id="equipe-status">
                                    <!-- Dados dinâmicos -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Kanban Visual -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-columns"></i> Fluxo de Trabalho</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3">
                                <h6>📋 Prospecção</h6>
                                <div class="kanban-column" id="col-prospeccao">
                                    <!-- Items dinâmicos -->
                                </div>
                            </div>
                            <div class="col-md-3">
                                <h6>📄 Contratos</h6>
                                <div class="kanban-column" id="col-contratos">
                                    <!-- Items dinâmicos -->
                                </div>
                            </div>
                            <div class="col-md-3">
                                <h6>🔧 Instalação</h6>
                                <div class="kanban-column" id="col-instalacao">
                                    <!-- Items dinâmicos -->
                                </div>
                            </div>
                            <div class="col-md-3">
                                <h6>🛠️ Pós-Venda</h6>
                                <div class="kanban-column" id="col-posvenda">
                                    <!-- Items dinâmicos -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Mapa de Calor de Gargalos -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-fire"></i> Mapa de Calor - Gargalos</h5>
                    </div>
                    <div class="card-body">
                        <div class="heat-map" id="heatmap-gargalos">
                            <!-- Células dinâmicas -->
                        </div>
                        <div class="mt-3">
                            <span class="heat-cell heat-low" style="width: 50px;">Baixo</span>
                            <span class="heat-cell heat-medium" style="width: 50px;">Médio</span>
                            <span class="heat-cell heat-high" style="width: 50px;">Alto</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Gráficos de Tendência -->
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Tendência de Vendas</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="chart-vendas"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-pie"></i> Distribuição por Etapa</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="chart-etapas"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal de Tarefa -->
    <div class="modal fade" id="modalTarefa" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Detalhes da Tarefa</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="detalhes-tarefa">
                        <!-- Conteúdo dinâmico -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Funções de atualização do dashboard
        function atualizarDashboard() {
            // Atualiza status da equipe
            fetch('/api/equipe/status')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('equipe-status');
                    tbody.innerHTML = data.map(membro => `
                        <tr>
                            <td>${membro.nome}</td>
                            <td>${membro.funcao}</td>
                            <td>${membro.meta}</td>
                            <td>${membro.realizado}</td>
                            <td>
                                <span class="status-indicator status-${membro.status}"></span>
                                ${membro.status}
                            </td>
                            <td>${membro.ultima_atualizacao}</td>
                        </tr>
                    `).join('');
                });

            // Atualiza Kanban
            atualizarKanban();

            // Atualiza mapa de calor
            atualizarHeatmap();

            // Atualiza gráficos
            atualizarGraficos();
        }

        function atualizarKanban() {
            // Implementação para buscar e atualizar os kanbans
        }

        function atualizarHeatmap() {
            // Implementação para atualizar mapa de calor
        }

        function atualizarGraficos() {
            // Implementação para atualizar gráficos
        }

        // Atualiza a cada 5 minutos
        setInterval(atualizarDashboard, 300000);
        atualizarDashboard();
    </script>
</body>
</html>
```

## 📱 Integração WhatsApp com SolarOS

```python
# WhatsApp_Integration.py
import requests
from datetime import datetime, timedelta
import json

class WhatsAppIntegration:
    """Integração SolarOS com WhatsApp Business API"""

    def __init__(self, api_key, phone_id):
        self.api_key = api_key
        self.phone_id = phone_id
        self.base_url = "https://graph.facebook.com/v18.0"

    def enviar_mensagem(self, destinatario, mensagem, tipo='texto'):
        """Envia mensagem via WhatsApp"""
        url = f"{self.base_url}/{self.phone_id}/messages"

        if tipo == 'texto':
            data = {
                "messaging_product": "whatsapp",
                "to": destinatario,
                "text": {"body": mensagem}
            }
        elif tipo == 'template':
            data = {
                "messaging_product": "whatsapp",
                "to": destinatario,
                "template": {
                    "name": "nome_template",
                    "language": {"code": "pt_BR"}
                }
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=data, headers=headers)
        return response.json()

    def enviar_mensagem_equipe(self, mensagem):
        """Envia mensagem para toda a equipe"""
        equipe = ['Franz', 'Eliene', 'Cleocir', 'Igor']

        for membro in equipe:
            telefone = self.get_telefone(membro)
            if telefone:
                self.enviar_mensagem(telefone, mensagem)

    def enviar_alerta_meta(self, membro, meta, real):
        """Envia alerta de meta não batida"""
        mensagem = f"📊 *Alerta de Meta*\n\n"
        mensagem += f"Membro: {membro}\n"
        mensagem += f"Meta: {meta}\n"
        mensagem += f"Realizado: {real}\n"
        mensagem += f"Faltou: {meta - real}\n\n"
        mensagem += "⏰ Ainda dá de recuperar no dia!"

        telefone = self.get_telefone(membro)
        if telefone:
            self.enviar_mensagem(telefone, mensagem)

    def enviar_tarefa_diaria(self, membro, tarefas):
        """Envia tarefas diárias"""
        mensagem = f"📅 *Tarefas do dia para {membro}*\n\n"

        # Tarefa principal
        tarefa_principal = tarefas[0]
        mensagem += f"🎯 *Sua única coisa numérica de hoje:*\n"
        mensagem += f"{tarefa_principal}\n\n"

        # Outras tarefas
        mensagem += "*Outras tarefas:*\n"
        for i, tarefa in enumerate(tarefas[1:], 1):
            mensagem += f"{i}. {tarefa}\n"

        # Lembrete
        mensagem += f"\n⏰ Meta diária até às 17h"

        telefone = self.get_telefone(membro)
        if telefone:
            self.enviar_mensagem(telefone, mensagem)

    def enviar_lembrete_manutencao(self, cliente):
        """Envia lembrete de manutenção"""
        mensagem = f"🔧 *Lembrete de Manutenção*\n\n"
        mensagem += f"Cliente: {cliente['nome']}\n"
        mensagem += f"Instalação: {cliente['potencia']} kWp\n"
        mensagem += f"Próxima manutenção: {cliente['proxima_manutencao']}\n\n"
        mensagem += "Por favor, agendar visita técnica."

        self.enviar_mensagem('Igor', mensagem)

    def enviar_notificacao_transferencia(self, cliente, etapa_anterior, nova_etapa):
        """Notifica transferência entre etapas"""
        mensagem = f"📋 *Nova Tarefa - {nova_etapa}*\n\n"
        mensagem += f"Cliente: {cliente['nome']}\n"
        mensagem += f"Telefone: {cliente['telefone']}\n"
        mensagem += f"Origem: {cliente['origem']}\n"

        if nova_etapa == 'contratos':
            mensagem += f"\n📄 *Informações do Contrato:*\n"
            mensagem += f"Potência: {cliente['potencia']} kWp\n"
            mensagem += f"Valor: R$ {cliente['valor_proposta']:,}\n"
            mensagem += f"Payback: {cliente['payback_estimado']} meses\n"

        mensagem += f"\nPor favor, acesse o Nexus para detalhes."

        responsavel = self.get_responsavel_etapa(nova_etapa)
        if responsavel:
            telefone = self.get_telefone(responsavel)
            if telefone:
                self.enviar_mensagem(telefone, mensagem)

    def enviar_resumo_semanal(self, dados):
        """Envia resumo semanal"""
        mensagem = f"📊 *Resumo Semanal*\n\n"

        for membro, stats in dados.items():
            mensagem += f"👤 {membro}:\n"
            mensagem += f"  • Contratos fechados: {stats['contratos']}\n"
            mensagem += f"  • Meta semanal: {stats['meta']}\n"
            mensagem += f"  • Performance: {stats['performance']}%\n\n"

        mensagem += "🎯 *Meta da semana:* Fechar mais contratos!"

        self.enviar_mensagem_equipe(mensagem)

    def get_telefone(self, membro):
        """Busca telefone do membro no banco"""
        # Implementação de busca no banco
        return None

    def get_responsavel_etapa(self, etapa):
        """Busca responsável por etapa"""
        responsaveis = {
            'prospeccao': 'Franz',
            'contratos': 'Eliene',
            'instalacao': 'Cleocir',
            'pos_venda': 'Igor'
        }
        return responsaveis.get(etapa)

    def criar_grupo_whatsapp(self, clientes):
        """Cria grupo de comunicação"""
        grupo_nome = f"SolarOS - {datetime.now().strftime('%Y-%m-%d')}"

        # Implementação de criação de grupo
        # Retorna ID do grupo

        # Envia mensagem de boas-vindas
        mensagem = f"👋 *Bem-vindo ao grupo {grupo_nome}*\n\n"
        mensagem += "Este grupo será usado para atualizações de cada etapa do processo.\n\n"
        mensagem += "📌 Regras:\n"
        mensagem += "1. Atualizar progresso\n"
        mensagem += "2. Reportar gargalos\n"
        mensagem += "3. Comemorar conquistas\n"

        return grupo_nome

    def enviar_atualizacao_grupo(self, grupo_id, mensagem):
        """Envia atualização para grupo"""
        # Implementação de envio para grupo
        pass
```

## 🔄 Fluxos de Automação

### 1. Fluxo de Tarefas Diárias
```python
# Executa todo dia às 8h
def executar_fluxo_diario():
    # 1. Verifica metas da véspera
    verificar_metas_anteriores()

    # 2. Gera tarefas diárias
    tarefas = gerar_tarefas_diarias()

    # 3. Envia tarefas para equipe
    for membro, lista_tarefas in tarefas.items():
        whatsapp.enviar_tarefa_diaria(membro, lista_tarefas)

    # 4. Agenda alertas
    agendar_alertas()
```

### 2. Fluxo de Transferência entre Etapas
```python
def transferir_etapa(cliente, nova_etapa):
    # 1. Atualiza status no banco
    atualizar_status_cliente(cliente, nova_etapa)

    # 2. Notifica responsável
    whatsapp.enviar_notificacao_transferencia(
        cliente,
        cliente['etapa_atual'],
        nova_etapa
    )

    # 3. Cria tarefa para novo responsável
    criar_tarefa_etapa(cliente, nova_etapa)

    # 4. Se for pós-venda, agenda manutenção
    if nova_etapa == 'pos_venda':
        agendar_manutencao(cliente)
```

### 3. Fluxo de Alertas Proativos
```python
def verificar_gargalos():
    # Verifica cada membro
    for membro in ['Franz', 'Eliene', 'Cleocir', 'Igor']:
        # Verifica metas diárias
        meta = get_meta_diaria(membro)
        real = get_real_diario(membro)

        if real < meta * 0.8:  # 80% da meta
            whatsapp.enviar_alerta_meta(membro, meta, real)

        # Verifica gargalos específicos
        if membro == 'Franz' and real < meta * 0.5:
            whatsapp.enviar_mensagem(
                membro,
                "💡 *Dica:* Focar em horários de maior receptividade (9-11h e 14-16h)"
            )
```

## 📱 Templates de Mensagens

### Template de Boas-Vindas
```
🎉 *Bem-vindo ao SolarOS!*

Seu sistema inteligente de gestão solar está ativo.

📊 Você receberá:
• Tarefas diárias às 8h
• Alertas de metas
• Notificações de novas tarefas
• Resumo semanal

🎯 Meta do dia: [Meta específica]

Boa sorte! 💪
```

### Template de Meta Batida
```
🏆 *Meta Batida!*

Parabéns por atingir sua meta diária!

📊 Seu desempenho:
• Meta: [Meta]
• Realizado: [Realizado]
• Performance: [Performance]%

Continue assim! 🚀
```

### Template de Alerta de Urgência
```
🚨 *Alerta de Urgência*

Você está com [X%] atrasado na meta diária.

⏰ Ainda dá de recuperar!
Foque em: [Tarefa crítica]

Precisa de ajuda? 💬
```

Este sistema integra:
- **Dashboard visual** com KPIs em tempo real
- **Notificações inteligentes** via WhatsApp
- **Automações proativas** para prevenir gargalos
- **Comunicação integrada** entre equipes
- **Monitoramento contínuo** de metas e desempenho