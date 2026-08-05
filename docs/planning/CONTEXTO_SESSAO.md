# Contexto do Pipeline FraLib — Para Proximas Sessoes

## Arquitetura Atual

Pipeline sequencial de agentes IA: briefing de texto -> landing page HTML completa.

## Fluxo de dados

Usuario (briefing)
    -> [Theo] PRD + briefing estrategico
    -> [Designer PRD] especificacao visual
    -> [Liam] HTML por secao (bloco a bloco)
    -> [Liz] HTML revisado e corrigido
    -> [Alex] pagina integrada
    -> [Caio] pagina otimizada
    -> [Franz] entrega final ao usuario

## O que cada agente faz, carrega e passa adiante

### Theo (theo.py — 723 linhas)
- Recebe: briefing bruto do usuario
- Carrega: RAG 4.206 chars + skills brand+design (25.332 chars)
- Faz: gera PRD completo (max_tokens=6000) + briefing estrategico (max_tokens=4000)
- Passa: PRD estruturado para o Designer PRD

### Designer PRD (designer_prd.py — 543 linhas)
- Recebe: PRD do Theo
- Faz: especificacao visual detalhada (max_tokens=8000)
- Passa: spec visual para o Liam

### Liam (liam.py — 519 linhas)
- Recebe: spec visual do Designer PRD
- Carrega: RAG 18.645 chars + 5 skills (77.064 chars) = ~95.709 chars total (~23.927 tokens)
- Skills: ui-ux-pro-max, design, design-taste-frontend, design-system, ui-styling
- Faz: gera HTML secao por secao (max_tokens=8000 por bloco)
- Passa: HTML bruto para o Liz

### Liz (liz.py — 491 linhas)
- Recebe: HTML do Liam
- Carrega: skill design-system (9.576 chars)
- Faz: revisa e corrige HTML (max_tokens=4000 / 8000)
- Passa: HTML revisado para o Alex

### Alex (alex.py — 1028 linhas)
- Recebe: HTML revisado do Liz
- Carrega: RAG 2.222 chars
- Faz: integra todas as secoes em pagina unica
- Passa: pagina integrada para o Caio

### Caio (caio.py — 476 linhas)
- Recebe: pagina integrada do Alex
- Carrega: RAG 1.894 chars
- Faz: otimiza performance e codigo (max_tokens=2000)
- Passa: pagina otimizada para o Franz

### Franz (Franz.py — 424 linhas)
- Recebe: pagina otimizada do Caio
- Carrega: RAG 3.437 chars
- Faz: finaliza e entrega (max_tokens=4000 x2)
- Passa: resultado final ao usuario

## Sistemas de Suporte

### agent_rag.py
- Carrega contexto RAG especifico por agente
- Busca em /root/fralib/backend/rag/[agente]/

### skill_loader.py
- Carrega skills por agente via get_skills_agente(nome)
- Skills ficam em /root/fralib/backend/skills/

### color_enforcer.py
- Garante consistencia de cores no HTML gerado

### animation_injector.py
- Injeta animacoes CSS/JS no HTML gerado

## Problemas Conhecidos e Resolvidos

### Resolvidos em 2026-05-02
- max_tokens insuficiente no Liam (3000 -> 8000): HTML truncado em secoes ricas
- max_tokens insuficiente no Theo PRD (3000 -> 6000): PRD incompleto
- max_tokens insuficiente no Theo briefing (2000 -> 4000): briefing cortado

### Problemas abertos
- alex.py com 1028 linhas (acima do limite de 800) — refatoracao pendente
- PM2 com 179 restarts acumulados — monitorar

## O que ainda falta fazer

1. Refatorar alex.py (dividir em modulos menores)
2. Testar pipeline completo end-to-end com os novos max_tokens
3. Avaliar se caio.py precisa de mais tokens
4. Monitorar qualidade dos outputs do Liam com max_tokens=8000

## Comandos de diagnostico rapido

cd /root/fralib/backend/agents
python3 -c "import liam, theo, liz, alex, caio, Franz, designer_prd, agent_rag, skill_loader, color_enforcer, animation_injector; print('TODOS OK')"

pm2 status fralib
pm2 logs fralib --lines 30
