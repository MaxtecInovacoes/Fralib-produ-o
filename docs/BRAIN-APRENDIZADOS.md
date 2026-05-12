# Brain Aprendizados — FraLib OS
> Base de conhecimento viva. Atualizar sempre que descobrir algo novo.

## Agentes — O que aprendemos

### Liam (gerador HTML)
- System prompt tem ~24k tokens — prompt caching economiza 80% nas chamadas repetidas
- Gera seção por seção sequencialmente — paralelizar reduziria tempo de 5min para ~1min
- max_tokens=8000 por bloco (aumentado de 3000 em 2026-05-02)
- Maior consumidor de tokens: ~60-80k por lead

### Theo (estrategista)
- max_tokens: 6000 PRD + 4000 briefing (aumentado de 3000/2000 em 2026-05-02)
- Funções corretas: gerar_briefing_estrategico + gerar_prd (não "arquiteto")
- ~8k tokens por lead

### Bryan (SDR WhatsApp)
- BUG CONHECIDO: estado sempre salvo como "intro" — nunca avança na state machine
- max_tokens=4000 excessivo para mensagem WhatsApp de 500 chars
- Fix: criar proximo_estado() e salvar estado correto após cada execução

### Arquiteto (Designer PRD)
- Usa Opus — mais lento. Sonnet 3.5 gera PRD igualmente bom em metade do tempo
- ~15k tokens por lead

### Hunter (scraper Google Maps)
- Fix aplicado: &&hl → ?hl + detecção redirect direto
- Requests síncronos — paralelizar reduziria de 2-3min para ~30s

## Pipeline — Lições

### Tempo por lead: ~12-15 minutos
- Hunter: 2-3min
- Caio+Alex (paralelo): 1-2min
- Jina AI: 30s
- Theo: 1-2min
- Arquiteto: 2-3min
- Liam: 3-5min (maior gargalo)
- Bryan: 30s

### Custo por lead: ~90-100k tokens
- Liam: 60-80k (dominante)
- Arquiteto: 15k
- Theo: 8k
- Bryan: 3k

### Reprocessar
- Implementado: executar_pipeline_lead_existente + _executar_pipeline_a_partir_fase2
- Arquivo: pipeline_endpoints.py
- /reprocessar/{id} dispara pipeline real

## Infraestrutura — Quirks

### Nginx
- SEMPRE usar 127.0.0.1 — localhost causa 502 por IPv6

### PostgreSQL
- Porta 5433 (não 5432)
- Conectar via DATABASE_URL do .env com venv

### PM2
- Nome: fralib, id: 0
- 179 restarts acumulados — monitorar

### VPS
- Scripts Python: escrever em /root/script.py, executar com /root/fralib/venv/bin/python3
- Sites HTML: /var/www/fralib/sites/{slug}/index.html (não campo html_gerado no banco)
- Tabela leads: coluna de data é criado_em (tipo text, cast ::timestamp necessário)

### SSE Logs
- Atual: deque em memória (perde logs ao reiniciar)
- Ideal: PostgreSQL LISTEN/NOTIFY (pendente implementar)

## Frontend

### Admin
- NUNCA editar admin.html diretamente
- Editar partials em frontend/partials/admin/
- Build: cd /root/fralib && venv/bin/python3 frontend/build_admin.py

### Kanban
- Salva sdr_stage no banco via PATCH /api/leads/{id}/campos ao arrastar card

## Modelo de IA
- Proxy: aibee.cloud (não API Anthropic direta)
- Default: claude-sonnet-4-5
- Opus: só para tarefas complexas
- Roteamento automático por agente em llm_direct.py
