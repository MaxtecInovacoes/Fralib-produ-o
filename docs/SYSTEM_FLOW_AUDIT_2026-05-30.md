<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib — Auditoria do Fluxo Atual

Data: 2026-05-30 America/Sao_Paulo.
Escopo: codigo local canonico em `C:\fralib`. A VPS nao foi revalidada nesta rodada porque o SSH recusou autenticacao.

## Entrada Operacional

O fluxo normal entra em `POST /api/pipeline/iniciar`.

1. `pipeline_start_endpoints.py` valida usuario, plano, cooldown, lock e configuracao.
2. Grava uma linha em `pipeline_queue`.
3. Enfileira um job em `jobs` via `job_queue.enqueue`.
4. `worker.py` pega o job com `SELECT FOR UPDATE SKIP LOCKED`, atualiza heartbeat e executa o pipeline.
5. Falhas retriable voltam para `pending` com backoff; falhas permanentes vao para `pipeline_failures`.

O request HTTP nao deve gerar site diretamente. A execucao longa pertence ao worker.

## Pipeline Principal

1. Hunter + Keyword Research
   - Recebe: segmento, cidade, quantidade e score minimo.
   - Faz: captura leads Google Maps e, em paralelo, pesquisa keywords transacionais com cache.
   - Entrega: lead bruto, pool de candidatos e contexto de busca para Caio/Arquiteto.

2. Caio
   - Recebe: lead bruto do Hunter.
   - Faz: qualificacao deterministica, sem LLM.
   - Entrega: score, tier, motivo e decisao de seguir ou buscar outro lead.

3. Jina Intelligence
   - Recebe: segmento, cidade, negocio e concorrentes quando disponiveis.
   - Faz: pesquisa web, referencias, palavras de mercado e contexto de nicho.
   - Entrega: `jina_insights` e dict estruturado para inteligencia/Arquiteto.

4. Inteligencia de Mercado
   - Recebe: reviews, atributos do Maps, concorrencia e PAA.
   - Faz: mapeia servicos confirmados, SEO local, padroes de mercado e insights de reviews.
   - Entrega: pacote `inteligencia` para Arquiteto e Agente de Nicho.

5. Unsplash + Pexels
   - Recebe: segmento, nome, cidade e arquétipo visual.
   - Faz: busca midia editorial opcional por mood.
   - Entrega: `fotos`, `videos` e `logo_url=None` ao PRD/renderer.

6. Agente de Nicho
   - Recebe: Hunter, segmento, cidade e Jina.
   - Faz: gera `NichoBriefing` com publico, USP, objeções, tom e restricoes.
   - Entrega: briefing tipado para Agente de Variacao.

7. Agente de Variacao
   - Recebe: `NichoBriefing` e concorrencia resumida.
   - Faz: decide ritmo, hero, CTA, ordem e angulo estrutural.
   - Entrega: `VariacaoEstrutural` para Arquiteto Mestre.

8. Arquiteto Mestre
   - Recebe: Hunter, Caio, Jina, keywords, inteligencia, briefing, variacao e design context.
   - Faz: delega estrutura para `bloco_estrutura.py`, copy para `bloco_copy.py`, junta tudo em `DesignerPRD`.
   - Entrega: PRD factual com direcao criativa compacta.

9. Liam Renderer
   - Recebe: `DesignerPRD`, midia, RAG Liam e skill compacta.
   - Faz: gera HTML completo com estilo, motion, schema, mapa, footer e CTAs.
   - Entrega: `index.html` para quality gate.

10. Quality Gate
    - Recebe: HTML + PRD.
    - Faz: normaliza HTML, bloqueia placeholders, emoji, claims sem prova, footer ruim, falta de motion e dados obrigatorios.
    - Entrega: HTML aprovado ou erro exato de reparo para Liam.

11. Deploy
    - Recebe: HTML aprovado.
    - Faz: publica em `/var/www/fralib/sites/{tenant_id}/{slug}/index.html`.
    - Entrega: URL publica do site.

12. Bryan
    - Recebe: URL, lead, telefone, score Caio e proof.
    - Faz: job separado de SDR/WhatsApp.
    - Entrega: mensagem pelo Meowhats ou status pendente se WhatsApp nao estiver conectado.

## Persistencia E Retomada

- `pipeline_id`: calculado por lead + segmento para checkpoint.
- Checkpoints: Jina, Agente de Nicho, Agente de Variacao, Arquiteto e Renderer.
- `pipeline_queue`: status visivel do processamento.
- `jobs`: fila tecnica com heartbeat, retries e recuperacao.
- `pipeline_executions`/spans: observabilidade por fase.
- Cold run/reprocessamento: invalida checkpoint/Jina/KW/leads/Unsplash/Pexels e propaga erro ao worker.

## Residuos Legados No Estado

- `alex_result`, `briefing_theo` e `liz_aprovado` ainda existem por compatibilidade.
- Alex, Theo antigo e Liz nao fazem parte do caminho padrao.
- OD runtime e Validador LLM aparecem em documentos/codigo legado, mas Skill Renderer + quality gate sao o caminho padrao.

## Pontos A Auditar Depois Na VPS

1. PM2 env real: `FRALIB_SKILLS_DIRS`, `FRALIB_LIAM_FULL_SKILLS`, `WORKER_JOB_TYPES`.
2. Se `/root/.claude/skills` ou `/root/.agents/skills` contem as skills esperadas pelo runtime.
3. Logs reais contendo `[LLM Direct] RAG ativado` e `[Skills] OK Skill`.
4. Se sites recentes foram gerados por Skill Renderer sem fallback de renderer.
