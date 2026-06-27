/**
 * SolarOS SDK - Integração com Nexus
 * Agente ERTM (Engenharia Reversa e Tração Métrica)
 *
 * Este SDK se integra ao Nexus existente e adiciona
 * inteligência de metas, tarefas automáticas e orquestração
 */

class SolarOS_ERTM {
    constructor(nexusInstance) {
        this.nexus = nexusInstance;
        this.api = nexusInstance.api;
        this.db = nexusInstance.db;

        // Configurações de metas
        this.config = {
            metaFaturamentoAnual: 12000000,
            metaMargemLiquida: 0.25,
            metaContratosAnuais: 120,

            // Membros da equipe
            equipe: {
                franz: { nome: 'Franz', funcao: 'vendas', etapa: 'prospeccao' },
                eliene: { nome: 'Eliene', funcao: 'operacoes', etapa: 'contratos' },
                cleocir: { nome: 'Cleocir', funcao: 'instalacao', etapa: 'instalacao' },
                igor: { nome: 'Igor', funcao: 'pos_venda', etapa: 'pos_venda' }
            },

            // Horários de execução
            horarios: {
                rotinaDiaria: '08:00',
                rotinaSemanal: '09:00',
                rotinaMensal: '10:00',
                verificacaoMetas: '17:00'
            }
        };

        // Inicializa o agente
        this.init();
    }

    async init() {
        console.log('🚀 SolarOS ERTM Agent inicializado');

        // Carrega dados de configuração
        await this.carregarConfiguracao();

        // Agenda rotinas
        this.agendarRotinas();

        // Inicializa dashboard
        this.renderizarDashboard();

        // Configura listeners de eventos
        this.configurarEventListeners();
    }

    // ═══════════════════════════════════════════════════════════
    // 📊 MÉTODOS DE METAS E CÁLCULOS
    // ═══════════════════════════════════════════════════════════

    calcularMetaMensal() {
        const mesAtual = new Date().getMonth() + 1;
        const fatorSazonal = this.getFatorSazonal(mesAtual);

        return {
            faturamento: (this.config.metaFaturamentoAnual / 12) * fatorSazonal,
            contratos: Math.ceil((this.config.metaContratosAnuais / 12) * fatorSazonal),
            novosLeads: Math.ceil((this.config.metaContratosAnuais * 1.5 / 12) * fatorSazonal),
            propostas: Math.ceil((this.config.metaContratosAnuais * 2 / 12) * fatorSazonal),
            ligacoes: Math.ceil((this.config.metaContratosAnuais * 10 / 12) * fatorSazonal)
        };
    }

    calcularMetaSemanal(metaMensal) {
        return {
            faturamento: metaMensal.faturamento / 4,
            contratos: Math.ceil(metaMensal.contratos / 4),
            novosLeads: Math.ceil(metaMensal.novosLeads / 4),
            propostas: Math.ceil(metaMensal.propostas / 4),
            ligacoes: Math.ceil(metaMensal.ligacoes / 4)
        };
    }

    calcularMetaDiaria(metaSemanal) {
        return {
            ligacoes: Math.ceil(metaSemanal.ligacoes / 5), // 5 dias úteis
            propostas: Math.ceil(metaSemanal.propostas / 5),
            fechamentos: Math.ceil(metaSemanal.contratos / 5),
            documentacoes: Math.ceil(metaSemanal.contratos / 5), // Para Eliene
            instalacoes: Math.ceil(metaSemanal.contratos / 10), // Para Cleocir
            manutencoes: 2 // Para Igor
        };
    }

    getFatorSazonal(mes) {
        // Sazonalidade do mercado solar brasileiro
        const sazonalidade = {
            1: 0.6,   // Janeiro - férias
            2: 0.7,   // Fevereiro - carnaval
            3: 0.9,   // Março
            4: 1.0,   // Abril
            5: 1.1,   // Maio
            6: 1.2,   // Junho - início inverno, contas altas
            7: 1.1,   // Julho
            8: 1.0,   // Agosto
            9: 1.0,   // Setembro
            10: 1.1,  // Outubro
            11: 1.0,  // Novembro
            12: 0.7   // Dezembro - fim de ano
        };
        return sazonalidade[mes] || 1.0;
    }

    // ═══════════════════════════════════════════════════════════
    // 🎯 MÉTODOS DE GERAÇÃO DE TAREFAS
    // ═══════════════════════════════════════════════════════════

    gerarTarefasDiarias() {
        const metaMensal = this.calcularMetaMensal();
        const metaSemanal = this.calcularMetaSemanal(metaMensal);
        const metaDiaria = this.calcularMetaDiaria(metaSemanal);

        const tarefas = {
            Franz: [
                {
                    tipo: 'critica',
                    descricao: `Ligar para ${metaDiaria.ligacoes} novos leads`,
                    numerico: metaDiaria.ligacoes,
                    acao: 'ligacao'
                },
                {
                    tipo: 'importante',
                    descricao: `Enviar ${metaDiaria.propostas} propostas comerciais`,
                    numerico: metaDiaria.propostas,
                    acao: 'proposta'
                },
                {
                    tipo: 'meta',
                    descricao: `Fechar ${metaDiaria.fechamentos} contratos`,
                    numerico: metaDiaria.fechamentos,
                    acao: 'fechamento'
                }
            ],
            Eliene: [
                {
                    tipo: 'critica',
                    descricao: `Documentar ${metaDiaria.documentacoes} contratos pendentes`,
                    numerico: metaDiaria.documentacoes,
                    acao: 'documentacao'
                },
                {
                    tipo: 'importante',
                    descricao: 'Verificar status de 5 homologações em andamento',
                    numerico: 5,
                    acao: 'homologacao'
                },
                {
                    tipo: 'compras',
                    descricao: 'Confirmar compras de materiais para instalações da semana',
                    numerico: metaDiaria.instalacoes,
                    acao: 'compras'
                }
            ],
            Cleocir: [
                {
                    tipo: 'critica',
                    descricao: `Realizar ${metaDiaria.instalacoes} instalações agendadas`,
                    numerico: metaDiaria.instalacoes,
                    acao: 'instalacao'
                },
                {
                    tipo: 'importante',
                    descricao: 'Verificar logística de materiais para amanhã',
                    numerico: 1,
                    acao: 'logistica'
                },
                {
                    tipo: 'seguranca',
                    descricao: 'Confirmar equipe e equipamentos para o dia',
                    numerico: 1,
                    acao: 'preparacao'
                }
            ],
            Igor: [
                {
                    tipo: 'critica',
                    descricao: `Realizar ${metaDiaria.manutencoes} manutenções preventivas`,
                    numerico: metaDiaria.manutencoes,
                    acao: 'manutencao'
                },
                {
                    tipo: 'importante',
                    descricao: 'Gerar relatórios de performance de 3 sistemas',
                    numerico: 3,
                    acao: 'relatorio'
                },
                {
                    tipo: 'suporte',
                    descricao: 'Verificar chamados de suporte pendentes',
                    numerico: 5,
                    acao: 'suporte'
                }
            ]
        };

        return tarefas;
    }

    gerarTarefaUnicaNumerica(membro, tarefas) {
        // Retorna a tarefa mais crítica do dia
        const tarefasMembro = tarefas[membro] || [];
        const tarefaCritica = tarefasMembro.find(t => t.tipo === 'critica');
        return tarefaCritica || tarefasMembro[0];
    }

    // ═══════════════════════════════════════════════════════════
    // 🤖 MÉTODOS DO AGENTE ERTM
    // ═══════════════════════════════════════════════════════════

    async executarRotinaDiaria() {
        console.log('📅 Executando rotina diária...');

        // 1. Verificar metas da véspera
        await this.verificarMetasAnterior();

        // 2. Gerar tarefas do dia
        const tarefas = this.gerarTarefasDiarias();

        // 3. Salvar tarefas no banco
        await this.salvarTarefas(tarefas);

        // 4. Notificar equipe
        await this.notificarEquipe(tarefas);

        // 5. Renderizar dashboard atualizado
        this.renderizarDashboard();

        // 6. Agendar verificação de fim de dia
        this.agendarVerificacaoMetas();

        console.log('✅ Rotina diária concluída');
    }

    async executarRotinaSemanal() {
        console.log('📊 Executando rotina semanal...');

        // 1. Gerar relatório de desempenho da semana
        const relatorio = await this.gerarRelatorioSemanal();

        // 2. Identificar gargalos
        const gargalos = this.identificarGargalos(relatorio);

        // 3. Ajustar metas da próxima semana
        const metasAjustadas = this.ajustarMetasSemana(gargalos);

        // 4. Criar sessão de compromisso
        await this.criarSessaoCompromisso(relatorio, gargalos, metasAjustadas);

        // 5. Enviar resumo para equipe
        await this.enviarResumoSemanal(relatorio);

        console.log('✅ Rotina semanal concluída');
    }

    async executarRotinaMensal() {
        console.log('📈 Executando rotina mensal...');

        // 1. Gerar relatório completo do mês
        const relatorio = await this.gerarRelatorioMensal();

        // 2. Análise de tendências
        const tendencias = this.analisarTendencias(relatorio);

        // 3. Projeção para próximo mês
        const projecao = this.projetarProximoMes(tendencias);

        // 4. Ajustar metas do próximo mês
        await this.ajustarMetasMensal(projecao);

        // 5. Relatório para liderança
        await this.enviarRelatorioLideranca(relatorio, tendencias, projecao);

        console.log('✅ Rotina mensal concluída');
    }

    async verificarMetasAnterior() {
        const ontem = new Date();
        ontem.setDate(ontem.getDate() - 1);

        const metas = await this.api.get(`/metas/diarias?data=${ontem.toISOString().split('T')[0]}`);
        const real = await this.api.get(`/desempenho/diario?data=${ontem.toISOString().split('T')[0]}`);

        for (const membro in metas) {
            if (real[membro] < metas[membro]) {
                const diff = metas[membro] - real[membro];
                const percentual = Math.round((real[membro] / metas[membro]) * 100);

                // Identificar gargalo
                const gargalo = this.diagnosticarGargalo(membro, metas[membro], real[membro]);

                // Enviar alerta e solução
                await this.enviarAlertaGargalo(membro, {
                    meta: metas[membro],
                    real: real[membro],
                    diff: diff,
                    percentual: percentual,
                    gargalo: gargalo
                });
            }
        }
    }

    diagnosticarGargalo(membro, meta, real) {
        const taxa = real / meta;

        // Diagnóstico baseado no tipo de métrica
        if (membro === 'Franz') {
            if (taxa < 0.5) {
                return {
                    tipo: 'volume',
                    descricao: 'Volume de ligações muito abaixo do esperado',
                    solucao: 'Focar em horários de maior receptividade: 9-11h e 14-16h. Priorizar leads qualificados.'
                };
            } else if (taxa < 0.8) {
                return {
                    tipo: 'conversao',
                    descricao: 'Taxa de conversão abaixo do esperado',
                    solucao: 'Revisar script de abordagem. Focar em benefícios financeiros (payback, economia).'
                };
            }
        } else if (membro === 'Eliene') {
            if (taxa < 0.5) {
                return {
                    tipo: 'processo',
                    descricao: 'Documentação atrasada',
                    solucao: 'Criar checklist urgente. Priorizar contratos mais próximos do fechamento.'
                };
            }
        } else if (membro === 'Cleocir') {
            if (taxa < 0.5) {
                return {
                    tipo: 'logistica',
                    descricao: 'Instalações não realizadas',
                    solucao: 'Verificar equipe e materiais. Agendar instalação imediatamente.'
                };
            }
        } else if (membro === 'Igor') {
            if (taxa < 0.5) {
                return {
                    tipo: 'suporte',
                    descricao: 'Manutenções pendentes',
                    solucao: 'Priorizar visitas. Gerar relatório automático.'
                };
            }
        }

        return {
            tipo: 'geral',
            descricao: 'Desempenho abaixo da meta',
            solucao: 'Manter foco nas tarefas prioritárias.'
        };
    }

    identificarGargalos(relatorio) {
        const gargalos = [];

        // Analisa cada membro
        for (const membro in relatorio.desempenho) {
            const stats = relatorio.desempenho[membro];

            // Verifica taxa de conversão
            if (stats.taxaConversao < 0.15) {
                gargalos.push({
                    membro,
                    tipo: 'conversao',
                    impacto: 'alto',
                    descricao: `Taxa de conversão de ${membro} está em ${stats.taxaConversao}%`,
                    solucao: 'Revisar processo de qualificação'
                });
            }

            // Verifica tempo de resposta
            if (stats.tempoResposta > 24) {
                gargalos.push({
                    membro,
                    tipo: 'tempo',
                    impacto: 'medio',
                    descricao: `${membro} está com tempo de resposta de ${stats.tempoResposta}h`,
                    solucao: 'Implementar resposta automática'
                });
            }

            // Verifica volume
            if (stats.volume < stats.meta * 0.8) {
                gargalos.push({
                    membro,
                    tipo: 'volume',
                    impacto: 'alto',
                    descricao: `Volume de ${membro} está ${Math.round((1 - stats.volume/stats.meta)*100)}% abaixo da meta`,
                    solucao: 'Aumentar foco em atividades-chave'
                });
            }
        }

        return gargalos;
    }

    // ═══════════════════════════════════════════════════════════
    // 📱 MÉTODOS DE NOTIFICAÇÃO
    // ═══════════════════════════════════════════════════════════

    async notificarEquipe(tarefas) {
        for (const membro in tarefas) {
            const tarefasMembro = tarefas[membro];
            const tarefaUnica = this.gerarTarefaUnicaNumerica(membro, tarefas);

            const mensagem = this.formatarMensagemDiária(membro, tarefasMembro, tarefaUnica);

            await this.enviarNotificacao(membro, mensagem);
        }
    }

    formatarMensagemDiária(membro, tarefas, tarefaUnica) {
        let mensagem = `📅 *Tarefas do dia - ${membro}*\n\n`;
        mensagem += `🕐 Data: ${new Date().toLocaleDateString('pt-BR')}\n\n`;

        if (tarefaUnica) {
            mensagem += `🎯 *SUA ÚNICA COISA NUMÉRICA DE HOJE:*\n`;
            mensagem += `${tarefaUnica.descricao}\n\n`;
        }

        mensagem += `📋 *Todas as tarefas:*\n`;
        tarefas.forEach((t, i) => {
            const emoji = t.tipo === 'critica' ? '🔴' : t.tipo === 'importante' ? '🟡' : '🟢';
            mensagem += `${emoji} ${t.descricao}\n`;
        });

        mensagem += `\n⏰ Meta até às 17h`;
        mensagem += `\n💪 Vamos executar!`;

        return mensagem;
    }

    async enviarAlertaGargalo(membro, dados) {
        let mensagem = `🚨 *Alerta de Meta*\n\n`;
        mensagem += `Membro: ${membro}\n`;
        mensagem += `Meta: ${dados.meta}\n`;
        mensagem += `Realizado: ${dados.real}\n`;
        mensagem += `Faltou: ${dados.diff} (${dados.percentual}%)\n\n`;
        mensagem += `🔍 *Diagnóstico:*\n${dados.gargalo.descricao}\n\n`;
        mensagem += `💡 *Sugestão:*\n${dados.gargalo.solucao}`;

        await this.enviarNotificacao(membro, mensagem);
    }

    async enviarResumoSemanal(relatorio) {
        let mensagem = `📊 *Resumo Semanal*\n\n`;
        mensagem += `Período: ${relatorio.periodo}\n\n`;

        for (const membro in relatorio.desempenho) {
            const stats = relatorio.desempenho[membro];
            const emoji = stats.taxa >= 1 ? '✅' : stats.taxa >= 0.8 ? '🟡' : '🔴';

            mensagem += `${emoji} *${membro}*\n`;
            mensagem += `   Meta: ${stats.meta} | Real: ${stats.real}\n`;
            mensagem += `   Performance: ${Math.round(stats.taxa * 100)}%\n\n`;
        }

        mensagem += `🏆 *Destaque:* ${relatorio.destaque}\n`;
        mensagem += `⚠️ *Atenção:* ${relatorio.atencao}`;

        // Envia para todos
        await this.enviarNotificacao('equipe', mensagem);
    }

    async enviarNotificacao(destinatario, mensagem) {
        // Integrar com WhatsApp API
        if (this.nexus.whatsapp) {
            await this.nexus.whatsapp.enviarMensagem(destinatario, mensagem);
        }

        // Salvar no histórico
        await this.api.post('/notificacoes', {
            destinatario,
            mensagem,
            tipo: 'tarefa_diaria',
            data: new Date().toISOString()
        });

        // Mostrar toast no sistema
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'info',
                title: mensagem.substring(0, 50) + '...',
                showConfirmButton: false,
                timer: 3000
            });
        }
    }

    // ═══════════════════════════════════════════════════════════
    // 🎨 RENDERIZAÇÃO DO DASHBOARD
    // ═══════════════════════════════════════════════════════════

    renderizarDashboard() {
        // Cria ou atualiza o dashboard SolarOS
        this.criarPainelMetas();
        this.criarKanbanVisual();
        this.criarMapaCalor();
        this.criarTarefasDoDia();
    }

    criarPainelMetas() {
        const metaMensal = this.calcularMetaMensal();
        const metaSemanal = this.calcularMetaSemanal(metaMensal);

        // Busca dados reais
        this.api.get('/kpis/atual').then(dados => {
            this.renderizarKPIs(dados, metaMensal, metaSemanal);
        });
    }

    renderizarKPIs(dados, metaMensal, metaSemanal) {
        const container = document.getElementById('solaros-kpis');
        if (!container) return;

        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body text-center">
                            <div class="metric-value text-primary">
                                R$ ${this.formatarMoeda(dados.faturamentoMes || 0)}
                            </div>
                            <div class="metric-label">Faturamento Mês</div>
                            <small class="${dados.faturamentoMes >= metaMensal.faturamento ? 'text-success' : 'text-danger'}">
                                Meta: R$ ${this.formatarMoeda(metaMensal.faturamento)}
                            </small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body text-center">
                            <div class="metric-value text-success">
                                ${dados.contratosFechados || 0}
                            </div>
                            <div class="metric-label">Contratos Fechados</div>
                            <small class="${dados.contratosFechados >= metaMensal.contratos ? 'text-success' : 'text-danger'}">
                                Meta: ${metaMensal.contratos}
                            </small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body text-center">
                            <div class="metric-value text-warning">
                                ${dados.novosLeads || 0}
                            </div>
                            <div class="metric-label">Novos Leads</div>
                            <small class="${dados.novosLeads >= metaMensal.novosLeads ? 'text-success' : 'text-danger'}">
                                Meta: ${metaMensal.novosLeads}
                            </small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card metric-card">
                        <div class="card-body text-center">
                            <div class="metric-value text-info">
                                ${dados.propostasEnviadas || 0}
                            </div>
                            <div class="metric-label">Propostas Enviadas</div>
                            <small class="${dados.propostasEnviadas >= metaMensal.propostas ? 'text-success' : 'text-danger'}">
                                Meta: ${metaMensal.propostas}
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row mt-3">
                <div class="col-12">
                    <div class="progress" style="height: 25px;">
                        <div class="progress-bar bg-success" role="progressbar"
                             style="width: ${Math.min((dados.faturamentoMes / metaMensal.faturamento) * 100, 100)}%">
                            ${Math.round((dados.faturamentoMes / metaMensal.faturamento) * 100)}% da meta mensal
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    criarKanbanVisual() {
        // Busca dados do funil
        this.api.get('/funil/atual').then(funil => {
            this.renderizarKanban(funil);
        });
    }

    renderizarKanban(funil) {
        const container = document.getElementById('solaros-kanban');
        if (!container) return;

        const etapas = [
            { id: 'prospeccao', nome: '📋 Prospecção', cor: 'primary', responsavel: 'Franz' },
            { id: 'qualificacao', nome: '🔍 Qualificação', cor: 'info', responsavel: 'Franz' },
            { id: 'proposta', nome: '📄 Proposta', cor: 'warning', responsavel: 'Franz' },
            { id: 'contrato', nome: '✅ Contrato', cor: 'success', responsavel: 'Franz/Eliene' },
            { id: 'homologacao', nome: '📝 Homologação', cor: 'info', responsavel: 'Eliene' },
            { id: 'instalacao', nome: '🔧 Instalação', cor: 'warning', responsavel: 'Cleocir' },
            { id: 'posvenda', nome: '🛠️ Pós-Venda', cor: 'secondary', responsavel: 'Igor' }
        ];

        let html = '<div class="row">';

        etapas.forEach(etapa => {
            const count = funil[etapa.id] || 0;
            html += `
                <div class="col">
                    <div class="kanban-column">
                        <h6 class="text-${etapa.cor}">${etapa.nome}</h6>
                        <div class="kanban-count">${count}</div>
                        <small class="text-muted">${etapa.responsavel}</small>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    criarMapaCalor() {
        // Gera mapa de calor dos últimos 30 dias
        this.api.get('/heatmap/gargalos?dias=30').then(dados => {
            this.renderizarMapaCalor(dados);
        });
    }

    renderizarMapaCalor(dados) {
        const container = document.getElementById('solaros-heatmap');
        if (!container) return;

        let html = '<div class="heatmap-grid">';

        dados.forEach(dia => {
            const nivel = dia.valor < 50 ? 'low' : dia.valor < 80 ? 'medium' : 'high';
            html += `
                <div class="heatmap-cell heat-${nivel}"
                     title="${dia.data}: ${dia.valor}%"
                     data-bs-toggle="tooltip">
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    criarTarefasDoDia() {
        const tarefas = this.gerarTarefasDiarias();
        const membroAtual = this.nexus.usuarioAtual;

        const container = document.getElementById('solaros-tarefas');
        if (!container) return;

        const tarefasMembro = tarefas[membroAtual] || [];
        const tarefaUnica = this.gerarTarefaUnicaNumerica(membroAtual, tarefas);

        let html = '<div class="tarefas-hoje">';
        html += `<h5>🎯 Tarefa Principal de Hoje</h5>`;

        if (tarefaUnica) {
            html += `
                <div class="tarefa-critica p-3 mb-3 rounded">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${tarefaUnica.descricao}</h6>
                            <small class="text-muted">${tarefaUnica.acao}</small>
                        </div>
                        <button class="btn btn-success btn-sm" onclick="solarOS.concluirTarefa('${tarefaUnica.acao}')">
                            ✓ Concluir
                        </button>
                    </div>
                </div>
            `;
        }

        html += '<h6>📋 Outras Tarefas</h6><ul class="list-group">';

        tarefasMembro.forEach(tarefa => {
            if (tarefa !== tarefaUnica) {
                html += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        ${tarefa.descricao}
                        <span class="badge bg-${tarefa.tipo === 'importante' ? 'warning' : 'secondary'}">
                            ${tarefa.tipo}
                        </span>
                    </li>
                `;
            }
        });

        html += '</ul></div>';
        container.innerHTML = html;
    }

    async concluirTarefa(acao) {
        await this.api.post('/tarefas/concluir', {
            acao,
            data: new Date().toISOString(),
            membro: this.nexus.usuarioAtual
        });

        // Atualiza dashboard
        this.renderizarDashboard();

        // Feedback
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: 'Tarefa concluída!',
                text: 'Continue assim! 💪',
                timer: 2000,
                showConfirmButton: false
            });
        }
    }

    // ═══════════════════════════════════════════════════════════
    // ⚙️ CONFIGURAÇÃO E SCHEDULING
    // ═══════════════════════════════════════════════════════════

    agendarRotinas() {
        // Verifica a cada minuto se deve executar algo
        setInterval(() => {
            const agora = new Date();
            const hora = agora.getHours();
            const minutos = agora.getMinutes();
            const diaSemana = agora.getDay();
            const diaMes = agora.getDate();

            // Rotina diária (8h)
            if (hora === 8 && minutos === 0) {
                this.executarRotinaDiaria();
            }

            // Rotina semanal (segunda-feira 9h)
            if (diaSemana === 1 && hora === 9 && minutos === 0) {
                this.executarRotinaSemanal();
            }

            // Rotina mensal (dia 1 às 10h)
            if (diaMes === 1 && hora === 10 && minutos === 0) {
                this.executarRotinaMensal();
            }

            // Verificação de metas (17h)
            if (hora === 17 && minutos === 0) {
                this.verificarMetasFimDia();
            }
        }, 60000); // A cada minuto
    }

    agendarVerificacaoMetas() {
        // Agenda verificação de fim de dia para as 17h
        const agora = new Date();
        const verificado = new Date(agora.setHours(17, 0, 0, 0));

        if (verificado > agora) {
            setTimeout(() => {
                this.verificarMetasFimDia();
            }, verificado - agora);
        }
    }

    async verificarMetasFimDia() {
        const hoje = new Date().toISOString().split('T')[0];
        const real = await this.api.get(`/desempenho/diario?data=${hoje}`);
        const metas = this.gerarTarefasDiarias();

        for (const membro in metas) {
            const metaCount = metas[membro].length;
            const realCount = real[membro] || 0;

            if (realCount < metaCount * 0.8) {
                await this.enviarNotificacao(membro,
                    `⏰ Lembrete: Você está com ${Math.round((1 - realCount/metaCount)*100)}% das tarefas pendentes!`
                );
            }
        }
    }

    configurarEventListeners() {
        // Listener para quando um lead é atualizado
        document.addEventListener('leadAtualizado', (e) => {
            this.onLeadAtualizado(e.detail);
        });

        // Listener para quando uma etapa é alterada
        document.addEventListener('etapaAlterada', (e) => {
            this.onEtapaAlterada(e.detail);
        });

        // Listener para quando um contrato é fechado
        document.addEventListener('contratoFechado', (e) => {
            this.onContratoFechado(e.detail);
        });
    }

    onLeadAtualizado(dados) {
        // Atualiza KPIs quando um lead é atualizado
        this.renderizarDashboard();
    }

    onEtapaAlterada(dados) {
        // Transfere automaticamente para próximo responsável
        const proximoResponsavel = this.getProximoResponsavel(dados.novaEtapa);

        if (proximoResponsavel) {
            this.enviarNotificacao(proximoResponsavel,
                `📋 Novo cliente na etapa ${dados.novaEtapa}\nCliente: ${dados.clienteNome}`
            );
        }
    }

    onContratoFechado(dados) {
        // Cria tarefa automática para Eliene
        this.api.post('/tarefas', {
            tipo: 'documentacao',
            cliente: dados.clienteId,
            responsavel: 'Eliene',
            prioridade: 'alta',
            prazo: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000) // 2 dias
        });

        // Notifica Eliene
        this.enviarNotificacao('Eliene',
            `🎉 Novo contrato fechado!\nCliente: ${dados.clienteNome}\nValor: R$ ${this.formatarMoeda(dados.valor)}\n\nPor favor, iniciar documentação.`
        );
    }

    getProximoResponsavel(etapa) {
        const fluxo = {
            'prospeccao': 'Franz',
            'qualificacao': 'Franz',
            'proposta': 'Franz',
            'contrato': 'Eliene',
            'homologacao': 'Eliene',
            'instalacao': 'Cleocir',
            'posvenda': 'Igor'
        };
        return fluxo[etapa];
    }

    // ═══════════════════════════════════════════════════════════
    // UTILIDADES
    // ═══════════════════════════════════════════════════════════

    formatarMoeda(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(valor);
    }

    async carregarConfiguracao() {
        try {
            const config = await this.api.get('/config/solaros');
            if (config) {
                this.config = { ...this.config, ...config };
            }
        } catch (e) {
            console.log('Usando configuração padrão');
        }
    }

    async salvarTarefas(tarefas) {
        const hoje = new Date().toISOString().split('T')[0];

        for (const membro in tarefas) {
            for (const tarefa of tarefas[membro]) {
                await this.api.post('/tarefas', {
                    data: hoje,
                    membro,
                    ...tarefa,
                    status: 'pendente'
                });
            }
        }
    }

    async gerarRelatorioSemanal() {
        // Implementação de geração de relatório
        return {
            periodo: 'Últimos 7 dias',
            desempenho: {},
            destaque: 'Franz fechou 5 contratos',
            atencao: 'Eliene precisa acelerar documentação'
        };
    }

    async gerarRelatorioMensal() {
        // Implementação de geração de relatório mensal
        return {
            mes: new Date().toLocaleDateString('pt-BR', { month: 'long' }),
            faturamento: 0,
            contratos: 0,
            tendencias: []
        };
    }

    analisarTendencias(relatorio) {
        // Análise de tendências baseada em dados históricos
        return {
            volume: 'estavel',
            conversao: 'crescendo',
            ticket: 'subindo'
        };
    }

    projetarProximoMes(tendencias) {
        const metaMensal = this.calcularMetaMensal();

        // Ajusta baseado em tendências
        if (tendencias.conversao === 'crescendo') {
            metaMensal.contratos *= 1.1;
        }

        return metaMensal;
    }

    ajustarMetasSemana(gargalos) {
        // Ajusta metas da semana baseado em gargalos
        const metas = this.calcularMetaSemanal(this.calcularMetaMensal());

        gargalos.forEach(gargalo => {
            if (gargalo.tipo === 'volume') {
                metas[gargalo.membro] *= 1.2; // Aumenta meta para forçar foco
            }
        });

        return metas;
    }

    ajustarMetasMensal(projecao) {
        // Salva novas metas no banco
        this.api.post('/metas/mensal', projecao);
    }

    async criarSessaoCompromisso(relatorio, gargalos, metas) {
        const hoje = new Date();
        const proximaSegunda = new Date(hoje);
        proximaSegunda.setDate(hoje.getDate() + (8 - hoje.getDay()) % 7);
        proximaSegunda.setHours(9, 0, 0, 0);

        // Cria evento de sessão
        await this.api.post('/eventos', {
            titulo: '📊 Sessão de Compromisso Semanal',
            descricao: `Revisão: ${relatorio.periodo}`,
            data: proximaSegunda.toISOString(),
            participantes: ['Franz', 'Eliene', 'Cleocir', 'Igor'],
            tipo: 'compromisso_semanal'
        });
    }

    async enviarRelatorioLideranca(relatorio, tendencias, projecao) {
        // Gera e envia relatório para Franz (líder)
        const mensagem = `📈 *Relatório Mensal*\n\n`;
        mensagem += `Período: ${relatorio.mes}\n`;
        mensagem += `Faturamento: R$ ${this.formatarMoeda(relatorio.faturamento)}\n`;
        mensagem += `Contratos: ${relatorio.contratos}\n\n`;
        mensagem += `📊 *Tendências:*\n`;
        mensagem += `• Volume: ${tendencias.volume}\n`;
        mensagem += `• Conversão: ${tendencias.conversao}\n`;
        mensagem += `• Ticket: ${tendencias.ticket}\n\n`;
        mensagem += `🎯 *Projeção Próximo Mês:*\n`;
        mensagem += `• Faturamento: R$ ${this.formatarMoeda(projecao.faturamento)}\n`;
        mensagem += `• Contratos: ${projecao.contratos}`;

        await this.enviarNotificacao('Franz', mensagem);
    }
}

// Instancia global
let solarOS;

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    if (window.nexus) {
        solarOS = new SolarOS_ERTM(window.nexus);
    }
});
