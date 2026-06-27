# ERTM SDK - Agente Orquestrador para Nexus

## 🎯 Classe Principal: ERTM_Agent

```python
class ERTM_Agent:
    """
    Agente inteligente que orquestra operações solares com base no método
    Engenharia Reversa e Tração Métrica (ERTM)
    """

    def __init__(self, nexus_api):
        self.nexus = nexus_api
        self.db = nexus_api.db
        self.whatsapp = nexus_api.whatsapp
        self.calendar = nexus_api.calendar

        # Metas anuais
        self.meta_faturamento_anual = 12000000  # R$ 12 milhões
        self.meta_margem_liquida = 0.25  # 25%
        self.meta_contratos_anuais = 120

        # Diferenciação de Indicadores
        self.lag_indicators = {
            'faturamento_mensal': 0,
            'contratos_fechados': 0,
            'satisfacao_cliente': 0
        }

        self.lead_indicators = {
            'novos_leads': 0,
            'ligacoes_prospeccao': 0,
            'propostas_enviadas': 0,
            'documentacoes_recebidas': 0
        }

        # Histórico de aprendizado
        self.learning_data = {
            'taxa_conversao': {},
            'tempo_etapa': {},
            'melhores_horarios': {}
        }

    def executar_rotina_diaria(self):
        """Executa a rotina diária de tração métrica"""

        # 1. Verificação de metas da véspera
        self._verificar_meta_anterior()

        # 2. Geração de tarefas diárias
        tarefas = self._gerar_tarefas_diarias()

        # 3. Distribuição para equipe
        self._distribuir_tarefas(tarefas)

        # 4. Agendamento de alertas
        self._agendar_alertas()

    def _verificar_meta_anterior(self):
        """Verifica se metas anteriores foram batidas"""
        ontem = date.today() - timedelta(days=1)

        # Verifica cada membro da equipe
        for membro in ['Franz', 'Eliene', 'Cleocir', 'Igor']:
            meta = self._get_meta_diaria(membro, ontem)
            real = self._get_real_diario(membro, ontem)

            if real < meta:
                # Alerta de meta não batida
                self._enviar_alerta(
                    f"Meta não batida ontem por {membro}: {real}/{meta}",
                    tipo='atraso'
                )

                # Análise do gargalo
                gargalo = self._identificar_gargalo(membro, ontem)
                self._enviar_solucao(gargalo)

    def _gerar_tarefas_diarias(self):
        """Gera tarefas diárias baseadas em metas e comportamento"""
        tarefas = {}

        # Franz - Vendas
        meta_franz = self._calcular_meta_franz()
        tarefas['Franz'] = [
            f"Ligar para {meta_franz['ligacoes']} novos leads",
            f"Enviar {meta_franz['propostas']} propostas comerciais",
            f"Fechar {meta_franz['fechamentos']} contratos"
        ]

        # Eliene - Contratos/Operações
        meta_eliane = self._calcular_meta_eliane()
        tarefas['Eliene'] = [
            f"Documentar {meta_eliane['documentacoes']} contratos",
            f"Comprar materiais para {meta_eliane['compras']} instalações",
            f"Acompanhar {meta_eliane['homologacoes']} homologações"
        ]

        # Cleocir - Instalação
        meta_cleocir = self._calcular_meta_cleocir()
        tarefas['Cleocir'] = [
            f"Instalar em {meta_cleocir['instalacoes']} clientes",
            f"Realizar vistoria em {meta_cleocir['vistorias']} obras",
            f"Agendar {meta_cleocir['agendamentos']} novas instalações"
        ]

        # Igor - Pós-Venda
        meta_igor = self._calcular_meta_igor()
        tarefas['Igor'] = [
            f"Realizar {meta_igor['manutencoes']} manutenções preventivas",
            f"Gerar {meta_igor['relatorios']} relatórios de performance",
            f"Contatar {meta_igor['suporte']} clientes com suporte"
        ]

        return tarefas

    def _distribuir_tarefas(self, tarefas):
        """Distribui tarefas para a equipe via WhatsApp"""
        for membro, tarefas_membro in tarefas.items():
            mensagem = f"📅 *Tarefas do dia para {membro}*\n\n"
            mensagem += "Sua única coisa numérica de hoje:\n\n"

            # Pega a tarefa mais crítica
            tarefa_critica = self._identificar_tarefa_critica(membro)
            mensagem += f"🎯 {tarefa_critica}\n\n"

            # Adiciona outras tarefas
            for i, tarefa in enumerate(tarefas_membro, 1):
                mensagem += f"{i}. {tarefa}\n"

            # Adiciona lembrete
            mensagem += f"\n⏰ Lembre-se: meta diária deve ser batida até às 17h"

            self.whatsapp.enviar_mensagem(membro, mensagem)

    def _agendar_alertas(self):
        """Agenda alertas para o dia"""
        # Alerta de metas
        self.calendar.agendar_evento(
            "Verificação de Metas Diárias",
            datetime.now().replace(hour=17, minute=0),
            participantes=['Franz', 'Eliene', 'Cleocir', 'Igor'],
            tipo='meta'
        )

        # Alerta de gargalos
        self._agendar_alerta_gargalos()

    def _identificar_gargalo(self, membro, data):
        """Identifica gargalo no desempenho do membro"""
        # Analisa histórico de desempenho
        historico = self.db.get_desempenho(membro, data)

        # Identifica padrões
        if historico['ligacoes'] < 20:
            return "Volume de ligações abaixo do esperado"
        elif historico['conversao'] < 0.15:
            return "Taxa de conversão baixa"
        elif historico['tempo_resposta'] > 24:
            return "Tempo de resposta lento"

        return "Sem gargalo identificado"

    def _enviar_solucao(self, gargalo):
        """Envia sugestão de solução para o gargalo"""
        solucoes = {
            "Volume de ligações abaixo do esperado": "Focar em horários de maior receptividade: 9-11h e 14-16h",
            "Taxa de conversão baixa": "Revisar script de abordagem e focar em benefícios financeiros",
            "Tempo de resposta lento": "Configurar respostas automáticas para horários não comerciais",
            "Sem gargalo identificado": "Manter rotina atual"
        }

        mensagem = f"💡 *Solução para gargalo*\n\n{solucoes.get(gargalo, 'Analisar caso específico')}"
        self.whatsapp.enviar_mensagem_equipe(mensagem)

    def executar_rotina_semanal(self):
        """Executa rotina semanal de compromissos"""
        # Sessão de compromisso
        compromissos = self._definir_compromissos_semanais()

        mensagem = "🗓️ *Sessão de Compromimento Semanal*\n\n"
        mensagem += "Compromissos da semana:\n\n"

        for membro, comp in compromissos.items():
            mensagem += f"👤 {membro}:\n"
            for c in comp:
                mensagem += f"  • {c}\n"
            mensagem += "\n"

        self.whatsapp.enviar_mensagem_equipe(mensagem)

        # Agendamento da próxima sessão
        proxima_segunda = self._proxima_segunda()
        self.calendar.agendar_evento(
            "Sessão de Compromisso",
            proxima_segunda,
            participantes=['Franz', 'Eliene', 'Cleocir', 'Igor'],
            duracao=20
        )

    def executar_rotina_mensal(self):
        """Executa rotina mensal de análise"""
        # Análise de desempenho mensal
        relatorio = self._gerar_relatorio_mensal()

        # Ajuste de metas
        novas_metas = self._ajustar_metas(relatorio)

        # Plano de ação
        plano_acao = self._criar_plano_acao(novas_metas)

        # Envio da liderança
        self._enviar_relatorio_lideranca(relatorio, novas_metas, plano_acao)

    def aprender_com_dados(self):
        """Aprende com o comportamento da equipe"""
        # Atualiza taxas de conversão
        self._atualizar_taxas_conversao()

        # Identifica melhores horários
        self._identificar_melhores_horarios()

        # Prediz tendências
        self._predizer_tendencias()
```

## 📊 Classes de Suporte

### 1. Metricas
```python
class Metricas:
    """Gerenciamento de métricas e KPIs"""

    def __init__(self):
        self.kpis = {
            'vendas': {
                'taxa_conversao': 0.0,
                'ticket_medio': 0.0,
                'tempo_fechamento': 0.0
            },
            'operacoes': {
                'tempo_documentacao': 0.0,
                'taxa_aprovacao': 0.0,
                'custo_instalacao': 0.0
            },
            'instalacao': {
                'tempo_instalacao': 0.0,
                'satisfacao_cliente': 0.0,
                'retrabalho': 0.0
            },
            'pos_venda': {
                'manutencoes_prev': 0.0,
                'performance_sistema': 0.0,
                'churn_rate': 0.0
            }
        }

    def calcular_kpi(self, area, kpi):
        """Calcula KPI específico"""
        # Implementação cálculo
        pass
```

### 2. Alertas
```python
class Alertas:
    """Sistema de alertas inteligentes"""

    def __init__(self, whatsapp):
        self.whatsapp = whatsapp
        self.tipos_alerta = {
            'atraso': {'prioridade': 'alta', 'acao': 'notificar'},
            'oportunidade': {'prioridade': 'media', 'acao': 'sugerir'},
            'risco': {'prioridade': 'alta', 'acao': 'alertar'},
            'meta': {'prioridade': 'media', 'acao': 'lembrar'}
        }

    def enviar_alerta(self, mensagem, tipo, destinatario=None):
        """Envia alerta com base no tipo"""
        config = self.tipos_alerta.get(tipo, {})

        if config['prioridade'] == 'alta':
            self.whatsapp.enviar_mensagem_emergencia(destinatario or 'equipe', mensagem)
        else:
            self.whatsapp.enviar_mensagem(destinatario or 'equipe', mensagem)
```

### 3. Automacoes
```python
class Automacoes:
    """Sistema de automações do Nexus"""

    def __init__(self, db, whatsapp):
        self.db = db
        self.whatsapp = whatsapp

    def automacao_transferencia_etapa(self, cliente, etapa_atual, proxima_etapa):
        """Transfere cliente entre etapas automaticamente"""
        # Atualiza status no banco
        self.db.update_cliente(cliente, {'etapa': proxima_etapa})

        # Notifica responsável
        responsavel = self.get_responsavel(proxima_etapa)
        mensagem = f"📋 *Novo cliente na fila {proxima_etapa}*\n\n"
        mensagem += f"Cliente: {cliente['nome']}\n"
        mensagem += f"Informações: {cliente['detalhes']}\n\n"
        mensagem += "Por favor, acesse o Nexus para detalhes."

        self.whatsapp.enviar_mensagem(responsavel, mensagem)

    def automacao_lembrete_manutencao(self, cliente):
        """Lembra de manutenção preventiva"""
        data_manutencao = cliente['proxima_manutencao']

        # Envia lembrete 7 dias antes
        if (data_manutencao - date.today()).days == 7:
            mensagem = f"🔧 *Lembrete de Manutenção*\n\n"
            mensagem += f"Cliente: {cliente['nome']}\n"
            mensagem += f"Data: {data_manutencao}\n"
            mensagem += f"Instalação: {cliente['potencia']} kWp\n\n"
            mensagem += "Por favor, agendar visita técnica."

            self.whatsapp.enviar_mensagem('Igor', mensagem)
```

## 🎯 Função Principal de Execução

```python
def executar_ertm(nexus_api):
    """
    Função principal que executa o agente ERTM
    """
    # Inicializa agente
    agente = ERTM_Agent(nexus_api)

    # Executa rotinas baseadas no horário
    agora = datetime.now()

    if agora.hour == 8 and agora.minute == 0:  # 8h da manhã
        agente.executar_rotina_diaria()

    elif agora.weekday() == 0 and agora.hour == 9 and agora.minute == 0:  # Segunda 9h
        agente.executar_rotina_semanal()

    elif agora.day == 1 and agora.hour == 10 and agora.minute == 0:  # Primeiro dia do mês 10h
        agente.executar_rotina_mensal()

    # Aprendizado contínuo
    agente.aprender_com_dados()
```

## 📋 Configuração do Agente

```python
# Configuração inicial do ERTM
config_ertm = {
    'meta_faturamento_anual': 12000000,
    'meta_margem_liquida': 0.25,
    'meta_contratos_anuais': 120,
    'horario_rotina_diaria': '08:00',
    'horario_rotina_semanal': '09:00',
    'horario_rotina_mensal': '10:00',
    'whatsapp_grupo': 'equipe-fralib-solar',
    'canal_alertas': 'nexus-alertas'
}
```

Este SDK inteligente vai transformar o Nexus em um sistema autônomo que:
1. **Mede tudo** - KPIs em tempo real
2. **Lembra da equipe** - Tarefas diárias específicas
3. **Aprende com o comportamento** - Ajusta estratégias
4. **Previne gargalos** - Alertas proativos
5. **Orquestra tudo** - Comunicação integrada via WhatsApp

O sistema vai evoluir conforme a equipe usa, aprendendo os padrões e sugerindo melhorias contínuas.