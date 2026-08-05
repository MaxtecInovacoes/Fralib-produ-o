#!/usr/bin/env python3
"""Atualiza CLAUDE.md com a pipeline correta de junho 2026."""

path = "CLAUDE.md"
with open(path, 'r') as f:
    content = f.read()

old_section = """## Pipeline de Agentes (ordem de execucao)

Fonte autoritativa: PLAYBOOK_PIPELINE_VALIDADA.md na VPS (/opt/fralib/docs/)

### Cadeia completa (8 estagios)
```
[1] BANCO       Carrega lead direto do Postgres
[2] HUNTER      Valida lead_data
[3] CAIO        Qualificacao (tier=MORNO/STANDARD/PREMIUM, score 0-100)
[4] ARQUITETO   PRD com secoes, paleta OKLch, animacoes (~35s via LLM)
[5] BUILDER     HTML via OpenUI chunked (4 chunks LLM, ~200s)
[6] QA v2       Vision QA score 7.9/10 PASSED (~111s)
[7] DEPLOY      Site salvo em /var/www/fralib/sites/...
[8] FRANZ       Lead marcado para outreach WhatsApp
```

### Agentes
| # | Agente | Funcao | max_tokens |
|---|--------|--------|------------|
| 1 | Theo | Estrategista / PRD | 6000 (PRD), 4000 (briefing) |
| 2 | Designer PRD | Arquiteto visual | 8000 |
| 3 | Arquiteto Mestre | Funde Theo + Designer em PRD unico | 8000 |
| 4 | Builder (OpenUI) | Gerador HTML chunked | 64000 total (4x 18000) |
| 5 | Liz | Revisora codigo | 4000 / 8000 |
| 6 | Caio | Otimizador | 2000 |
| 7 | Franz | Finalizador / SDR WhatsApp | 4000 |"""

new_section = """## Pipeline de Agentes (ordem de execucao)

Fonte autoritativa: `docs/RESTORE_JUNHO22_REFERENCE.md`
Commit referencia: `a9030deb` (22 junho 2026 ~18:22)

### Cadeia completa (11 fases)
```
FASE 1  HUNTER           → Hunter captura leads (utils/agente1_hunter_v2.py)
FASE 2  CURADORIA/CAIO   → Qualifica lead — tier MORNO/STANDARD/PREMIUM (agents/caio.py)
FASE 3  JINA             → Pesquisa de mercado Jina AI (agents/jina_research.py)
FASE 4  INTELIGENCIA     → Análise de concorrência
FASE 5  FOTOS            → Download de fotos (agents/unsplash_fetcher.py)
FASE 6  NICHO            → Análise de nicho (agents/agente_nicho.py)
FASE 7  VARIACAO         → Variação estrutural (agents/agente_variacao.py)
FASE 8  ARQUITETO        → Gera DesignerPRD (agents/arquiteto_mestre.py)
FASE 9  BUILDER          → HTML via OpenUI (services/openui_renderer.py)
FASE 10 DEPLOY           → Site salvo em /var/www/fralib/sites/...
FASE 11 FRANZ            → SDR outreach WhatsApp (agents/sdr_langgraph/)

Orquestrador: backend/services/pipeline_executors.py
Estado: backend/services/pipeline_phases.py (FraLibState com 15+ campos)
```

### Agentes
| Fase | Agente | Funcao |
|------|--------|--------|
| 1 | Hunter | Captura leads no Google Maps |
| 2 | Caio | Qualifica lead (tier, score, paleta) |
| 3 | Jina | Pesquisa de mercado (Jina AI) |
| 4 | Inteligencia | Análise de concorrência |
| 5 | Fotos | Download de fotos Unsplash/Pexels |
| 6 | Nicho | Análise de nicho do segmento |
| 7 | Variacao | Variação estrutural do site |
| 8 | Arquiteto Mestre | Gera DesignerPRD via LLM (seções, paleta OKLch, animações) |
| 9 | Builder (OpenUI) | Gera HTML completo via OpenUI com contratos (SEO/LGPD/motion) |
| 10 | Deploy | Publica site em /var/www/fralib/sites/ |
| 11 | Franz | SDR outreach WhatsApp (FSM + Orchestrator) |

**Nota:** Theo, Designer PRD, Liam, Liz são agentes LEGADO. O Arquiteto Mestre funde Theo + Designer em PRD único.
**Builder:** usa `services/openui_renderer.py` (não `agents/builder/agent.py`)."""

if old_section not in content:
    print('ERRO: texto antigo nao encontrado')
    import sys
    sys.exit(1)

content = content.replace(old_section, new_section)

with open(path, 'w') as f:
    f.write(content)

print('CLAUDE.md atualizado com pipeline correta')
