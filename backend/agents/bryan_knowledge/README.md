# Bryan Knowledge (Legacy)

## Status: LEGACY - Manutenção mínima

Este diretório contém knowledge base usada pelo **dreamer.py** para consolidar lessons cross-tenant.

## Arquivos

| Arquivo | Uso | Status |
|---------|-----|--------|
| `global_lessons.json` | Gerado por dreamer.py | Runtime |
| `winning_patterns.md` | RAG para Franz |ativo |
| `objection_handling.md` | RAG para Franz | ativo |
| `segment_insights.json` | Insights por segmento | ativo |
| `ab_results.json` | Resultados A/B | ativo |

## Ciclo de vida

1. **dreamer.py** roda todas as noites (3h BRT)
2. Consolida `backend/memory/u*/franz_lead_*.json` de todos tenants
3. Gera/atualiza `global_lessons.json`
4. Atualiza `rag_knowledge/sdr_agents/*.md`

## Histórico

- Sprint 9: Criado para SDR Franz RAG
- Sprint 13+: Extendido para cross-tenant via dreamer

## Não é fallback

Este diretório contém knowledge base estática para RAG, não é fallback de produto.
