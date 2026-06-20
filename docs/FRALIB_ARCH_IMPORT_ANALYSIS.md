<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib Architecture Import Analysis

Data: 2026-06-02

## Objetivo

Avaliar quais ideias do projeto `C:\Users\JESUS TE AMA\saas-fralib-wpp-main`
podem fortalecer a FraLib sem atrapalhar a pipeline ativa. Este documento nao
autoriza migracao de runtime, deploy manual, edicao direta na VPS ou troca de
agentes canonicos.

## Regra De Execucao

Qualquer importacao deve seguir:

1. POC isolada em script, migration proposta ou doc.
2. Nenhuma chamada ao pipeline real durante a POC.
3. Nenhuma alteracao em `/root/fralib` ou `/var/www/fralib`.
4. Nenhuma troca de Hunter, Caio, Jina, Arquiteto Mestre ou Builder Renderer.
5. Smoke dry-run antes de evoluir para codigo de produto.
6. Pre-release gate antes de qualquer release.

## Resumo Executivo

O outro projeto e mais moderno como blueprint de infraestrutura: Docker Swarm,
Traefik, Redis, Celery, PostgreSQL com pgvector e bridge WhatsApp em Go. A
FraLib atual e mais madura no fluxo operacional: pipeline real, gates,
deploy por Git, worker com heartbeat, timeout controlado, contratos Hermes e
observabilidade por tenant.

Conclusao: importar ideias, nao migrar arquitetura. A ordem correta e endurecer
garantias da FraLib e so depois escalar.

## Comparativo Por Quesito

### Multi-tenant

O outro projeto usa `tenant_id` nos modelos e endpoints e extrai tenant do JWT.
Isso e bom como desenho. Entretanto, a evidencia analisada indica que o
isolamento ainda depende de filtros em codigo: havia funcao para `SET
app.current_tenant`, mas nao foi encontrado uso efetivo de RLS com `ENABLE ROW
LEVEL SECURITY` e `CREATE POLICY`. Tambem havia webhook consultando lead por
telefone sem escopo direto de tenant, o que pode misturar eventos se dois tenants
tiverem o mesmo numero ou payload ambiguo.

Na FraLib, o isolamento tambem nao deve ser tratado como resolvido de forma
absoluta, mas ja existem tenant audit, testes IDOR, jobs tenant-aware, caminhos
`/sites/{tenant_id}/{slug}` e contrato no pre-release gate.

Decisao: prioridade alta para hardening multi-tenant na FraLib. Avaliar RLS
PostgreSQL depois de testes cross-tenant e indices compostos.

### Escalabilidade Horizontal

O outro projeto declara tres replicas de backend com Traefik e rede overlay.
Isso e uma boa direcao para SaaS. O risco e que replicas web nao podem executar
listeners, background jobs ou consumidores de eventos de forma duplicada sem
coordenacao. A evidencia analisada mostrou listener iniciado no startup do
backend e campanha ativada com `BackgroundTasks`, o que nao e ideal para tres
replicas.

Na FraLib, a arquitetura atual e mais simples: PM2, worker dedicado e fila. Nao
e horizontalmente escalada, mas tem menos risco de duplicar consumidores por
engano.

Decisao: nao escalar backend antes de separar claramente web, worker e listeners.
Escala horizontal deve vir depois de idempotencia, locks e limites por tenant.

### Processamento Assincrono

O outro projeto tem Celery/Redis, mas parte central da campanha analisada roda
em `BackgroundTasks` do FastAPI. Alem disso, a configuracao Celery vista tinha
`task_time_limit=300` e `worker_pool="solo"`, inadequado para pipeline FraLib
com fases longas de renderer e LLM.

Na FraLib, a fila atual ja possui worker, heartbeat em thread real, timeout por
job de 1800s e recuperacao via `recover-runtime`. O ponto fraco e evoluir
controle de concorrencia, idempotencia obrigatoria e melhor visibilidade de
fase.

Decisao: manter fila atual por enquanto. Criar POC de Redis/Celery apenas para
tarefas pequenas e independentes, nao para substituir o pipeline principal.

### WhatsApp Gateway

O outro projeto tem uma bridge WhatsApp dedicada em Go. A ideia e boa: separar
gateway, sessoes, status, WebSocket/API e autenticacao por chave. A FraLib ja
tem WhatsApp separado via `meowhats` na porta 3001, mas pode ganhar robustez com
um contrato mais claro de status, reconnect, webhooks, tenant session e circuit
breaker.

Decisao: comparar bridge Go contra `meowhats` em POC isolada. Nao trocar o
gateway em producao sem teste controlado por tenant e sem compatibilidade com
`fralib_user_{tenant_id}`.

### RAG Com pgvector

O outro projeto tem direcao correta: pgvector, embeddings e indice HNSW. A
evidencia analisada tambem mostrou risco de schema: migration de knowledge base
usando `campaign_id UUID` enquanto a tabela de campanhas usava id inteiro. Isso
indica que a ideia e boa, mas a implementacao ainda precisa de revisao.

Na FraLib, `pipeline_learning` e token tracker ja guardam sucesso/erro e custo.
O pgvector pode complementar isso com memoria semantica para leads, nichos,
rejeicoes, causas de falha e exemplos de sites aprovados.

Decisao: POC de pgvector deve ser append-only, tenant-aware e fora do caminho
principal. Nao usar pgvector para decidir pipeline ate provar ganho.

## Ordem Recomendada

### Fase 0 - Sem Codigo De Produto

- Documentar matriz de importacao.
- Criar checklist de riscos por componente.
- Definir criterios de aceite por POC.

### Fase 1 - Multi-tenant E Idempotencia

- Ampliar testes cross-tenant para leads, jobs, assets, sites e WhatsApp.
- Tornar idempotency key obrigatoria nos jobs de pipeline.
- Criar indices compostos por tenant/status/data.
- Avaliar RLS com migration de laboratorio.

### Fase 2 - POC pgvector

- Criar tabela experimental tenant-aware, por exemplo `pipeline_memory_vectors`.
- Inserir apenas eventos ja conhecidos e nao sensiveis.
- Buscar similaridade para diagnostico, nao para decisao automatica.
- Medir custo, latencia e qualidade da recuperacao.

### Fase 3 - POC WhatsApp Gateway

- Rodar bridge em ambiente isolado.
- Validar connect/status/send/webhook por tenant.
- Comparar estabilidade com `meowhats`.
- Definir contrato unico para FraLib antes de qualquer migracao.

### Fase 4 - Fila Externa Opcional

- Avaliar Redis/Celery ou alternativa somente para tarefas pequenas.
- Nao mover Builder Renderer ou pipeline principal sem benchmark.
- Garantir retry, timeout por fase, checkpoint e tenant scope.

### Fase 5 - Escala Horizontal

- Separar processo web, worker, listener e scheduler.
- Garantir que consumidores nao dupliquem eventos.
- Definir locks distribuidos e limites globais/por tenant.
- So entao avaliar replicas de backend.

## O Que Nao Fazer

- Nao substituir a pipeline por Celery de uma vez.
- Nao migrar WhatsApp em producao por comparacao teorica.
- Nao adicionar pgvector no caminho de decisao do pipeline sem POC.
- Nao rodar Docker Swarm como solucao para bugs de tenant ou idempotencia.
- Nao usar claims de arquitetura como prova de estabilidade.
- Nao editar VPS fora do fluxo Git.

## POCs Seguras Sugeridas

1. `docs/FRALIB_ARCH_IMPORT_ANALYSIS.md`: este documento, sem impacto runtime.
2. `scripts/tenant_scope_audit.py`: ampliar checks estaticos ja existentes.
3. Migration draft de RLS em arquivo separado, sem aplicar automaticamente.
4. Script local de pgvector com banco temporario ou ambiente controlado.
5. Contrato HTTP para WhatsApp gateway, sem trocar provider atual.

## Criterios De Aceite Para Qualquer Evolucao

- `python pipeline.py smoke --dry-run` passa.
- `python pipeline.py pre-release-gate` passa antes de release.
- Nenhum fluxo novo chama LLM, Hunter real, deploy ou WhatsApp durante smoke.
- Nenhuma query de cliente perde `tenant_id/user_id`.
- Nenhum componente novo substitui Builder Renderer ou worker sem flag e POC.
- Nenhum deploy acontece sem commit.
