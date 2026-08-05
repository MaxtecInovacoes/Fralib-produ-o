# FraLib — Contexto Rápido

## Stack
- Backend: FastAPI + Python 3.13 | PM2 id=5 (fralib) | porta 8000
- DB: PostgreSQL localhost:5433 | user=postgres | db=fralib_db | pw=fralib2024
- Sites: /var/www/fralib/sites/{tenant_id}/{slug}/index.html
- VPS: root@187.77.37.72

## Pipeline (ordem de execução)
1. Hunter — captura lead do Google Maps
2. Caio — qualifica lead (PREMIUM/STANDARD/BASIC)
3. Theo — gera briefing estratégico (~13k chars)
4. Jina AI — insights de mercado (cache por segmento+cidade)
5. Unsplash — fotos por nicho (substitui fotos reais do Google)
6. Keyword Research — Google Suggest (cache 30 dias no PostgreSQL)
7. Arquiteto — gera PRD em 2 blocos:
   - Bloco 1: estrutura + direção criativa (3000 tokens)
   - Bloco 2: copy por seção com reviews reais (6000 tokens)
8. Liam — gera HTML por seção em paralelo (8 seções, modelo opus)
9. Liz — audita HTML (score mínimo 70)
10. Franz — gera mensagem WhatsApp

## Agentes principais
| Arquivo | Função |
|---|---|
| arquiteto_mestre.py | PRD em 2 blocos, tokens OKLch, direção visual |
| liam.py | HTML por seção paralela, Tailwind, CSS vars |
| liz.py | Auditoria HTML (técnica + semântica) |
| Franz.py | Mensagem WhatsApp personalizada |
| caio.py | Qualificação do lead |
| theo.py | Briefing estratégico |
| craft_rules.py | Anti-slop, tipografia, cor, animação, UX laws |
| design_context.py | Tokens OKLch por nicho, 5 direções visuais |
| seo_context.py | SEO por nicho + cidade |
| unsplash_fetcher.py | Fotos por nicho via Unsplash API |
| keyword_research.py | Google Suggest + cache PostgreSQL |

## 5 Direções Visuais (Open Design)
| ID | Nome | Accent | Font Heading |
|---|---|---|---|
| editorial | Editorial Monocle | oklch(58% 0.16 35) rust | Iowan Old Style, serif |
| modern_minimal | Modern Minimal | oklch(58% 0.18 255) cobalt | system-ui |
| warm_soft | Warm Soft | oklch(64% 0.13 28) terracotta | Lora, serif |
| tech_utility | Tech Utility | oklch(58% 0.16 145) signal green | Inter |
| brutalist | Brutalist Experimental | oklch(60% 0.22 25) hot red | Times New Roman, serif |

## Direção por nicho
academia=brutalist | barbearia=editorial | restaurante=warm_soft
clinica=modern_minimal | odontologia=modern_minimal | estetica=editorial
nutricionista=warm_soft | advocacia=editorial | farmacia=tech_utility
imobiliaria=modern_minimal | pet_shop=warm_soft | pizzaria=warm_soft

## Open Design integrado
- craft_rules.py: Anti-slop + Typography + Typography Hierarchy + Color + Animation + Laws of UX
- design_context.py: 5 direções com tokens OKLch exatos + posture cues
- Liam SYSTEM: Anti-slop + Hierarquia tipográfica + Laws of UX + Autocrítica 5D
- Arquiteto: recebe get_craft_rules() + get_design_context_prompt() + get_seo_context()

## Liz — heurísticas
- Telefone: verifica telefone real do lead no HTML
- Endereço: verifica cidade real do lead no HTML
- H1: verifica se tem 5+ chars de conteúdo
- Placeholder: ignora atributos de input/textarea
- Score mínimo: 70

## Endpoints principais
POST /api/pipeline/iniciar — novo pipeline
POST /api/pipeline/reprocessar/{lead_id} — reprocessar lead existente
GET  /api/pipeline/status — status atual
GET  /api/logs/stream — SSE logs em tempo real

## Caches
- Jina: /root/fralib/backend/agents/jina_cache/jina_{hash}.txt
- Unsplash: /root/fralib/backend/agents/unsplash_cache/
- Keywords: tabela keyword_cache no PostgreSQL (30 dias)

## Problemas conhecidos resolvidos
- SSE pg_notify: usar %s não  (sse_endpoints.py)
- Arquiteto JSON truncado: 2 blocos menores em vez de 1 grande
- Segmento errado: guard de inferência pelo nome do lead
- Fotos reais: Unsplash substitui em ambos os fluxos (pipeline + reprocessar)
