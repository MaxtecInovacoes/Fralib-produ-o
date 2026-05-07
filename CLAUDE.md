# FraLib — CLAUDE.md

## Visao Geral do Projeto

FraLib e um SaaS de geracao de landing pages via pipeline de agentes IA.
O pipeline recebe um briefing e produz HTML completo, animado e responsivo.

## Pipeline de Agentes (ordem de execucao)

1. Theo — Estrategista / PRD
   RAG: 4.206 chars | Skills: brand, design (25.332 chars)
   max_tokens: 6000 (PRD), 4000 (briefing)

2. Designer PRD — Arquiteto visual
   max_tokens: 8000

3. Liam — Gerador de HTML
   RAG: 18.645 chars | Skills: 5 skills (77.064 chars)
   Input total ao LLM: ~95.709 chars (~23.927 tokens)
   max_tokens: 8000 por bloco

4. Liz — Revisora de codigo
   Skills: design-system (9.576 chars)
   max_tokens: 4000 / 8000

5. Alex — Integrador
   RAG: 2.222 chars

6. Caio — Otimizador
   RAG: 1.894 chars | max_tokens: 2000

7. Bryan — Finalizador / SDR
   RAG: 3.437 chars | max_tokens: 4000

## Arquivos Principais

liam.py          519 linhas  Gerador HTML principal
theo.py          723 linhas  Estrategista / PRD
liz.py           491 linhas  Revisora de codigo
alex.py         1028 linhas  Integrador (candidato a refatoracao)
caio.py          476 linhas  Otimizador
bryan.py         424 linhas  Finalizador
designer_prd.py  543 linhas  Arquiteto visual
pipeline_endpoints.py  891 linhas  Rotas do pipeline

## Infraestrutura

VPS: 187.77.37.72 (root)
Processo: PM2 (nome: fralib, id: 0)
Runtime: Python 3.13 + FastAPI
Banco: SQLite

## Estado do Sistema (ultima atualizacao: 2026-05-02)

Correcoes aplicadas:
- liam.py: max_tokens 3000 -> 8000
- theo.py PRD: max_tokens 3000 -> 6000
- theo.py briefing: max_tokens 2000 -> 4000

Status: todos imports OK, PM2 online (106.4mb RAM), RAG e skills funcionando.

## Alertas

- alex.py tem 1028 linhas — candidato a refatoracao (limite: 800)
- pipeline_endpoints.py tem 891 linhas — proximo do limite
