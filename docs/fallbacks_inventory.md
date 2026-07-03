# Inventário dos 28 Fallbacks Hardcoded — FraLib

Auditoria do pipeline. Cada entrada tem: agente/arquivo:linha → string usada → tratamento novo.

## Regras

- SEM fallback silencioso. Campo faltando = erro explícito ou string vazia (não inventar dado).
- Para campos críticos (nome, cidade, segmento, contato): levantar `DadosIncompletosError`.
- Para campos opcionais: string vazia (`""`) para o componente renderizar sem dado.

## Tabela de fallbacks

| # | Local | String / Padrão | Tratamento novo |
|---|-------|-----------------|-----------------|
| 1 | `agente_nicho.py:118` | `return "default"` (import quebrado) | Remover fallback, deixar import propagar erro |
| 2 | `agente_nicho.py:207` | `dados_lead.get("nome", "")` | BriefingParser já valida; remover get default |
| 3 | `agente_nicho.py:208` | `dados_lead.get("rating", 0)` | Aceitar 0 (não exibir se 0) |
| 4 | `agente_nicho.py:215` | `dados_lead.get("faixa_preco", "")` | Aceitar string vazia |
| 5 | `agente_nicho.py:377` | `tom_de_voz="profissional"` default | Propagar erro se LLM não retornou |
| 6 | `agente_variacao.py:404-414` | `"default": {template_estrutura: corporate, ...}` | SubnichoNaoMapeadoError se não estiver em SUB_NICHO_TEMPLATES |
| 7 | `vite_template_factual_footer.py:90` | `or "Negócio local"` | **FEITO (A4)** — DadosIncompletosError |
| 8 | `vite_template_factual_footer.py:96` | `or "sua cidade"` | **FEITO (A4)** |
| 9 | `vite_template_factual_footer.py:103` | `or "atendimento local"` | **FEITO (A4)** |
| 10 | `vite_template_factual_footer.py:115` | `whatsapp_href = ... "#contato"` | **FEITO (A4)** — string vazia |
| 11 | `vite_template_factual_footer.py:43` | `return "#contato"` | **FEITO (A4)** — string vazia |
| 12 | `vite_react_renderer.py:4369` | `if FACTUAL_FOOTER_AVAILABLE` (silencioso) | Trocar para warning se indisponível |
| 13 | `agente_nicho.py:368` | `nicho=_dados.get("nicho", segmento)` | Aceitar segmento se LLM não retornou nicho específico |
| 14 | `arquiteto_mestre.py:120` | `_design_dict.get("direction", "default")` | Aceitar "default" mas logar |
| 15 | `arquiteto_mestre.py:367-378` | Fallbacks hex `#ffffff`, `#09130f`, `#f8faf7` | Aceitar (paleta base mínima) |
| 16 | `arquiteto_mestre.py:446-447` | `"Inter"` font fallback | Aceitar mas marcar como is_default_font |
| 17 | `pipeline_orchestrator_service.py:1412` | `nicho="negocio local"` | Aceitar (substituído por BriefingParser validado) |
| 18 | `pipeline_orchestrator_service.py:1550` | `nicho="negocio local"` (fast-path) | **FEITO (B2)** — marcar dados_incompletos=True |
| 19 | `pipeline_orchestrator_service.py:1773` | `_seg = ... or "negocio local"` | Aceitar (substituído por BriefingParser validado) |
| 20 | `pipeline_orchestrator_service.py:2137` | `nicho=state.segmento or "default"` | Aceitar "default" no lesson persist |
| 21 | `pipeline_orchestrator_service.py:2197` | `_dc_cache.get("direction", "default")` | Aceitar (cache miss) |
| 22 | `site_orchestrator.py:285` | `_nicho = state.segmento or "default"` | Aceitar |
| 23 | `site_orchestrator.py:401` | `nicho=state.segmento or "default"` | Aceitar (lesson persist) |
| 24 | `agente_nicho.py:346-351` | `dados_ausentes`, `fallback_fields` | Já populado; **B2** marca explicitamente |
| 25 | `pipeline_orchestrator_service.py:1466-1469` | Router falha → fallback modelos default | Logar warning + continuar |
| 26 | `pipeline_orchestrator_service.py:1440-1442` | DesignDirector falha → state.direcao_criativa=None | Aceitar None (builder usa defaults) |
| 27 | `pipeline_orchestrator_service.py:624` | Keyword research falha | Warning + continuar sem SEO |
| 28 | `pipeline_orchestrator_service.py:1821-1822` | Checkpoint PRD falha | Warning + continuar |

## Status

- **FEITO** (A4): #7-11 (vite_template_factual_footer)
- **FEITO** (B2): #18 (pipeline orchestrator fast-path)
- **FEITO** (A3, C1-C6): retry helpers aplicados

## Pendente

- #1-6: agente_nicho/variacao fallbacks a remover com `DadosIncompletosError` ou string vazia
- #13-23: vários fallbacks de string genérica em campos opcionais — manter mas logar
- #25-28: try/except silenciosos no orchestrator — alvo da FASE E