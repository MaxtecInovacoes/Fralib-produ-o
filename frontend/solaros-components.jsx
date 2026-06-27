/**
 * SolarOS React Components
 * Componentes React para integração com Nexus
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// ═══════════════════════════════════════════════════════════
// 📊 COMPONENTE: Dashboard SolarOS
// ═══════════════════════════════════════════════════════════

export const SolarOSDashboard = ({ user, onTaskComplete }) => {
  const [metas, setMetas] = useState(null);
  const [tarefas, setTarefas] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [metasRes, tarefasRes, kpisRes] = await Promise.all([
        axios.get('/api/metas/dashboard'),
        axios.get('/api/tarefas/dia'),
        axios.get('/api/kpis/atual')
      ]);

      setMetas(metasRes.data);
      setTarefas(tarefasRes.data);
      setKpis(kpisRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      setLoading(false);
    }
  };

  const handleConcluirTarefa = async (tarefaId) => {
    try {
      await axios.post(`/api/tarefas/${tarefaId}/concluir`);
      loadDashboardData();
      if (onTaskComplete) onTaskComplete();
    } catch (error) {
      console.error('Erro ao concluir tarefa:', error);
    }
  };

  if (loading) {
    return <div className="text-center p-5">Carregando SolarOS...</div>;
  }

  return (
    <div className="solaros-dashboard">
      {/* KPIs Principais */}
      <KPICards metas={metas} kpis={kpis} />

      {/* Tarefas do Dia */}
      <TarefasDoDia
        tarefas={tarefas}
        user={user}
        onConcluir={handleConcluirTarefa}
      />

      {/* Kanban de Funil */}
      <FunilKanban />

      {/* Mapa de Calor */}
      <MapaCalorGargalos />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 📊 COMPONENTE: Cards de KPIs
// ═══════════════════════════════════════════════════════════

const KPICards = ({ metas, kpis }) => {
  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 0
    }).format(valor);
  };

  const calcularProgresso = (real, meta) => {
    if (!meta || meta === 0) return 0;
    return Math.min((real / meta) * 100, 100);
  };

  const cards = [
    {
      titulo: 'Faturamento Mensal',
      valor: formatarMoeda(kpis?.faturamentoMes || 0),
      meta: formatarMoeda(metas?.faturamento || 0),
      icone: '💰',
      cor: 'primary'
    },
    {
      titulo: 'Contratos Fechados',
      valor: kpis?.contratosFechados || 0,
      meta: metas?.contratos || 0,
      icone: '📄',
      cor: 'success'
    },
    {
      titulo: 'Novos Leads',
      valor: kpis?.novosLeads || 0,
      meta: metas?.novosLeads || 0,
      icone: '👥',
      cor: 'warning'
    },
    {
      titulo: 'Taxa de Conversão',
      valor: `${((kpis?.taxaConversao || 0) * 100).toFixed(1)}%`,
      meta: `${((metas?.taxaConversao || 0.15) * 100).toFixed(1)}%`,
      icone: '📈',
      cor: 'info'
    }
  ];

  return (
    <div className="row mb-4">
      {cards.map((card, index) => (
        <div className="col-md-3" key={index}>
          <div className={`card metric-card border-${card.cor}`}>
            <div className="card-body text-center">
              <div className="metric-icon">{card.icone}</div>
              <div className={`metric-value text-${card.cor}`}>{card.valor}</div>
              <div className="metric-label">{card.titulo}</div>
              <div className="progress mt-2" style={{ height: '8px' }}>
                <div
                  className={`progress-bar bg-${card.cor}`}
                  style={{ width: `${calcularProgresso(
                    parseFloat(card.valor),
                    parseFloat(card.meta)
                  )}%` }}
                />
              </div>
              <small className="text-muted">Meta: {card.meta}</small>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 📋 COMPONENTE: Tarefas do Dia
// ═══════════════════════════════════════════════════════════

const TarefasDoDia = ({ tarefas, user, onConcluir }) => {
  const tarefasUsuario = tarefas.filter(t => t.membro === user?.nome || t.membro === user);

  if (tarefasUsuario.length === 0) {
    return (
      <div className="card mb-4">
        <div className="card-body text-center text-muted">
          <p>Nenhuma tarefa para hoje! 🎉</p>
        </div>
      </div>
    );
  }

  const tarefaPrincipal = tarefasUsuario.find(t => t.tipo === 'critica') || tarefasUsuario[0];
  const outrasTarefas = tarefasUsuario.filter(t => t !== tarefaPrincipal);

  return (
    <div className="card mb-4">
      <div className="card-header bg-primary text-white">
        <h5 className="mb-0">📅 Tarefas de Hoje</h5>
      </div>
      <div className="card-body">
        {/* Tarefa Principal */}
        <div className="tarefa-principal p-3 mb-3 rounded bg-light">
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <span className="badge bg-danger me-2">🎯 PRINCIPAL</span>
              <h6 className="d-inline">{tarefaPrincipal?.descricao}</h6>
            </div>
            <button
              className="btn btn-success btn-sm"
              onClick={() => onConcluir(tarefaPrincipal?.id)}
            >
              ✓ Concluir
            </button>
          </div>
          <small className="text-muted">
            Responsável: {tarefaPrincipal?.membro}
          </small>
        </div>

        {/* Outras Tarefas */}
        <h6>📋 Outras Tarefas</h6>
        <div className="list-group">
          {outrasTarefas.map((tarefa) => (
            <div
              key={tarefa.id}
              className="list-group-item d-flex justify-content-between align-items-center"
            >
              <div>
                <span className={`badge me-2 ${
                  tarefa.tipo === 'importante' ? 'bg-warning' : 'bg-secondary'
                }`}>
                  {tarefa.tipo}
                </span>
                {tarefa.descricao}
              </div>
              <button
                className="btn btn-outline-success btn-sm"
                onClick={() => onConcluir(tarefa.id)}
              >
                ✓
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 🔄 COMPONENTE: Kanban de Funil
// ═══════════════════════════════════════════════════════════

export const FunilKanban = () => {
  const [funil, setFunil] = useState({});

  useEffect(() => {
    loadFunil();
  }, []);

  const loadFunil = async () => {
    try {
      const res = await axios.get('/api/funil/atual');
      setFunil(res.data);
    } catch (error) {
      console.error('Erro ao carregar funil:', error);
    }
  };

  const etapas = [
    { id: 'prospeccao', nome: '📋 Prospecção', cor: 'primary', responsavel: 'Franz' },
    { id: 'qualificacao', nome: '🔍 Qualificação', cor: 'info', responsavel: 'Franz' },
    { id: 'proposta', nome: '📄 Proposta', cor: 'warning', responsavel: 'Franz' },
    { id: 'contrato', nome: '✅ Contrato', cor: 'success', responsavel: 'Franz/Eliene' },
    { id: 'homologacao', nome: '📝 Homologação', cor: 'info', responsavel: 'Eliene' },
    { id: 'instalacao', nome: '🔧 Instalação', cor: 'warning', responsavel: 'Cleocir' },
    { id: 'posvenda', nome: '🛠️ Pós-Venda', cor: 'secondary', responsavel: 'Igor' }
  ];

  return (
    <div className="card mb-4">
      <div className="card-header">
        <h5 className="mb-0">🔄 Funil de Vendas</h5>
      </div>
      <div className="card-body">
        <div className="row">
          {etapas.map((etapa) => (
            <div className="col" key={etapa.id}>
              <div className={`kanban-column bg-${etapa.cor} bg-opacity-10 p-3 rounded`}>
                <h6 className={`text-${etapa.cor}`}>{etapa.nome}</h6>
                <div className="kanban-count fs-3 fw-bold text-center">
                  {funil[etapa.id] || 0}
                </div>
                <small className="text-muted">{etapa.responsavel}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 🔥 COMPONENTE: Mapa de Calor de Gargalos
// ═══════════════════════════════════════════════════════════

export const MapaCalorGargalos = () => {
  const [heatmap, setHeatmap] = useState([]);

  useEffect(() => {
    loadHeatmap();
  }, []);

  const loadHeatmap = async () => {
    try {
      const res = await axios.get('/api/heatmap/gargalos?dias=30');
      setHeatmap(res.data);
    } catch (error) {
      console.error('Erro ao carregar heatmap:', error);
    }
  };

  const getCor = (valor) => {
    if (valor >= 80) return 'bg-success';
    if (valor >= 50) return 'bg-warning';
    return 'bg-danger';
  };

  // Gera células para os últimos 30 dias
  const gerarCelulas = () => {
    const celulas = [];
    const hoje = new Date();

    for (let i = 29; i >= 0; i--) {
      const data = new Date(hoje);
      data.setDate(data.getDate() - i);
      const dataStr = data.toISOString().split('T')[0];
      const dia = heatmap.find(d => d.data === dataStr);

      celulas.push({
        data: dataStr,
        valor: dia?.valor || 0,
        diaSemana: data.toLocaleDateString('pt-BR', { weekday: 'short' })
      });
    }

    return celulas;
  };

  const celulas = gerarCelulas();

  return (
    <div className="card mb-4">
      <div className="card-header">
        <h5 className="mb-0">🔥 Mapa de Calor - 30 dias</h5>
      </div>
      <div className="card-body">
        <div className="heatmap-grid d-flex flex-wrap gap-1">
          {celulas.map((celula, index) => (
            <div
              key={index}
              className={`heatmap-cell ${getCor(celula.valor)}`}
              style={{ width: '30px', height: '30px' }}
              title={`${celula.data}: ${celula.valor}%`}
              data-bs-toggle="tooltip"
            >
              <small>{celula.diaSemana}</small>
            </div>
          ))}
        </div>
        <div className="mt-3 d-flex gap-3 justify-content-center">
          <span className="badge bg-success">🟢 Acima de 80%</span>
          <span className="badge bg-warning">🟡 50-80%</span>
          <span className="badge bg-danger">🔴 Abaixo de 50%</span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 👥 COMPONENTE: Status da Equipe
// ═══════════════════════════════════════════════════════════

export const StatusEquipe = () => {
  const [equipe, setEquipe] = useState([]);

  useEffect(() => {
    loadEquipe();
  }, []);

  const loadEquipe = async () => {
    try {
      const res = await axios.get('/api/equipe/status');
      setEquipe(res.data);
    } catch (error) {
      console.error('Erro ao carregar equipe:', error);
    }
  };

  const getStatusCor = (status) => {
    switch (status) {
      case 'no_prazo': return 'success';
      case 'atencao': return 'warning';
      case 'atrasado': return 'danger';
      default: return 'secondary';
    }
  };

  return (
    <div className="card mb-4">
      <div className="card-header">
        <h5 className="mb-0">👥 Status da Equipe</h5>
      </div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Membro</th>
                <th>Função</th>
                <th>Meta Diária</th>
                <th>Realizado</th>
                <th>Performance</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {equipe.map((membro) => (
                <tr key={membro.id}>
                  <td>
                    <span className={`status-dot bg-${getStatusCor(membro.status)}`} />
                    {membro.nome}
                  </td>
                  <td>{membro.funcao}</td>
                  <td>{membro.meta}</td>
                  <td>{membro.realizado}</td>
                  <td>
                    <div className="progress" style={{ width: '100px' }}>
                      <div
                        className={`progress-bar bg-${getStatusCor(membro.status)}`}
                        style={{ width: `${membro.performance}%` }}
                      />
                    </div>
                    <small>{membro.performance}%</small>
                  </td>
                  <td>
                    <span className={`badge bg-${getStatusCor(membro.status)}`}>
                      {membro.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 📈 COMPONENTE: Gráfico de Tendência
// ═══════════════════════════════════════════════════════════

export const GraficoTendencia = ({ tipo = 'vendas' }) => {
  const [dados, setDados] = useState([]);

  useEffect(() => {
    loadDados();
  }, [tipo]);

  const loadDados = async () => {
    try {
      const res = await axios.get(`/api/graficos/tendencia?tipo=${tipo}`);
      setDados(res.data);
    } catch (error) {
      console.error('Erro ao carregar gráfico:', error);
    }
  };

  // Implementar visualização com Chart.js ou similar
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">📈 Tendência de {tipo}</h5>
      </div>
      <div className="card-body">
        <div id={`chart-${tipo}`} style={{ height: '300px' }}>
          {/* Implementar Chart.js aqui */}
          <p className="text-center text-muted">Gráfico em carregamento...</p>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════
// 🔔 COMPONENTE: Lista de Alertas
// ═══════════════════════════════════════════════════════════

export const ListaAlertas = () => {
  const [alertas, setAlertas] = useState([]);

  useEffect(() => {
    loadAlertas();
  }, []);

  const loadAlertas = async () => {
    try {
      const res = await axios.get('/api/alertas');
      setAlertas(res.data);
    } catch (error) {
      console.error('Erro ao carregar alertas:', error);
    }
  };

  const marcarLido = async (id) => {
    try {
      await axios.put(`/api/alertas/${id}/lido`);
      loadAlertas();
    } catch (error) {
      console.error('Erro ao marcar alerta:', error);
    }
  };

  const getIconeAlerta = (tipo) => {
    switch (tipo) {
      case 'atraso': return '🚨';
      case 'oportunidade': return '💡';
      case 'meta': return '📊';
      case 'risco': return '⚠️';
      default: return '🔔';
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">🔔 Alertas Recentes</h5>
      </div>
      <div className="card-body">
        {alertas.length === 0 ? (
          <p className="text-center text-muted">Nenhum alerta pendente 🎉</p>
        ) : (
          <div className="list-group">
            {alertas.map((alerta) => (
              <div
                key={alerta.id}
                className={`list-group-item ${!alerta.lido ? 'fw-bold' : ''}`}
              >
                <div className="d-flex justify-content-between">
                  <div>
                    <span className="me-2">{getIconeAlerta(alerta.tipo)}</span>
                    {alerta.mensagem}
                  </div>
                  {!alerta.lido && (
                    <button
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => marcarLido(alerta.id)}
                    >
                      Marcar lido
                    </button>
                  )}
                </div>
                <small className="text-muted">
                  {new Date(alerta.criadoEm).toLocaleString('pt-BR')}
                </small>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SolarOSDashboard;
