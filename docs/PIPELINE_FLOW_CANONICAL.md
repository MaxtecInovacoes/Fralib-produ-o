# Pipeline Flow Canonical

> Última atualização: 06/jul/2026.
> Este documento descreve o único fluxo canônico da FraLib.

## Visão geral

Pipeline processa 1 lead do funil SDR até a publicação do site em **11 fases sequenciais**.
O motor de geração oficial é **Vite/React**.

## As 11 fases

| # | Fase | Módulo | Função | LLM? |
|---|---|---|---|---|
| 1 | Hunter | `utils/agente1_hunter_v2.py` | Busca leads | Não |
| 2 | Caio | `agents/caio.py` | Qualifica lead | Não |
| 3 | Jina | `utils/jina_intelligence.py` | Pesquisa de mercado | Sim |
| 4 | SDR (Franz) | `agents/sdr_langgraph/` | Conversa WhatsApp e qualifica | Sim |
| 5 | Consolidação | serviços da pipeline | Junta dados e contratos | Não |
| 6 | Nicho | `agents/agente_nicho.py` | Briefing do nicho | Sim |
| 7 | Variação | `agents/agente_variacao.py` | Define variação estrutural | Sim ou template canônico |
| 8 | Arquiteto | `agents/arquiteto_mestre.py` | Orquestra copy e estrutura | Sim |
| 9 | Renderização | `services/vite_react_renderer.py` | Gera o projeto React/Vite | Sim, conforme policy |
| 9b | Quality Gate | `agents/html_quality_gate.py` | Valida o artefato publicado | Não |
| 10 | Deploy | `services/builder_worker.py` | Publica o site | Não |
| 11 | Franz | `agents/sdr_langgraph/agent.py` | Envio de contato | Sim |

## Fluxo do renderizador

```text
PRD
  ↓
builder_worker.py
  ↓
render_vite_react_site()
  ↓
FRALIB_VITE_LLM_POLICY
  ↓
Studio React determinístico
  ↓
Quality Gate
  ↓
Deploy
```

## LLM por lead

| Etapa | Função |
|---|---|
| Jina | Pesquisa externa e síntese |
| Nicho | Briefing do nicho |
| Variação | Escolha da estrutura |
| Arquiteto | Construção do plano de página |
| Renderização | Direção criativa ou copy curta, dependendo da policy |
| SDR | Conversa e qualificação |

## Verificação

```bash
python pipeline.py smoke --dry-run
pytest tests/test_regression_patches.py
```

## Arquivos centrais

- `backend/services/vite_react_renderer.py`
- `backend/services/builder_worker.py`
- `backend/endpoints/pipeline_orchestrator_service.py`
- `backend/services/pipeline_phases.py`
- `backend/core/job_queue.py`
- `backend/agents/html_quality_gate.py`

