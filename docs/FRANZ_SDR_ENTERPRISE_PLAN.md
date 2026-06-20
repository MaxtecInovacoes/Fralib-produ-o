# Franz SDR v2 - plano enterprise

Data: 2026-06-04

## Decisao

O SDR da FraLib nao deve ser apenas um prompt que gera texto. O modelo correto
para producao e um orquestrador de atendimento com estado, politicas,
ferramentas, memoria, handoff humano, ledger de envios e avaliacoes.

O modulo atual Bryan/Franz pode continuar operando, mas deve ficar atras de uma
camada de controle. A troca para um SDR novo so deve acontecer depois que esta
camada estiver pronta, porque ela e a parte que evita envio fora de ordem,
link antes da apresentacao, follow-up sem historico e consumo de tentativa por
condicao externa.

## Problema confirmado

O erro observado no WhatsApp nao foi falta de LLM melhor. Foi falha de controle
de estado:

- lead frio estava em stage de follow-up;
- nao havia historico de saida comprovando apresentacao anterior;
- o cron/worker podia tratar resposta vazia como sucesso operacional;
- a mensagem com link foi liberada antes do fluxo minimo de apresentacao.

## Referencias de arquitetura

Padroes pesquisados em fontes oficiais:

- OpenAI Agents SDK: agentes em producao precisam de orquestracao, ferramentas,
  handoffs, estado, guardrails e observabilidade.
- OpenAI Agent Builder Safety: inputs devem passar por guardrails, acoes
  arriscadas precisam de aprovacao ou regra deterministica, e traces/evals
  devem medir aderencia.
- Anthropic Building Effective Agents: ferramentas e contratos de ferramenta
  merecem engenharia tao forte quanto prompts; simplicidade e workflows
  testaveis vencem prompts gigantes.
- Salesforce Agentforce: agentes enterprise sao compostos por subagentes,
  instrucoes, regras e acoes; a logica deterministica roda antes do LLM.
- Intercom Fin: atendimento precisa de identidade configurada, historico,
  canal, politicas, handoff humano e workflows reutilizaveis.
- Google Vertex Grounding: respostas devem ser aterradas em fontes de dados
  verificaveis quando dependerem de fatos.

## Revalidacao externa de stack

Pesquisa complementar em docs oficiais, comunidades e foruns fora do GitHub:

- Chatwoot e a melhor camada visual/inbox. AgentBot recebe webhooks, usa API
  para responder e abre handoff humano mudando a conversa para `open`.
- LangGraph e o melhor nucleo para FraLib porque e Python, baixo nivel, com
  execucao duravel, persistencia, memoria, human-in-the-loop e testes por
  grafo.
- Rasa CALM e a melhor referencia conceitual para atendimento controlado:
  LLM entende a mensagem, mas fluxos executam a logica de negocio.
- Dify e Flowise ajudam em prototipo visual/RAG, mas adicionam outra plataforma
  e nao resolvem bem o mesmo fio de conversa + handoff sem middleware.
- CrewAI e hubs de exemplos servem para tarefas internas multiagente, nao para
  atendimento conversacional com estado e WhatsApp.
- Forum/reddit reforcam o mesmo padrao pratico: agentes em producao falham por
  falta de estado duravel, retries com saida, human-in-the-loop real, evals,
  observabilidade e interface de acao deterministica.

Decisao aprovada:

```text
Chatwoot = tela operacional, inbox, historico e handoff.
FraLib SDR Gateway = seguranca, tenant, plano, horario, cooldown e ledger.
LangGraph = grafo de decisao conversacional e estado duravel.
Rasa CALM = referencia de desenho dos fluxos, nao dependencia inicial.
Bryan/Franz atual = composer legado atras dos guards ate Franz v2 assumir.
```

Nao instalar agora:

- Rasa em producao: bom conceito, mas mais pesado e menos aderente ao stack
  Python ja existente da FraLib.
- Dify/Flowise: bom demo, risco de virar plataforma paralela.
- Botpress: menos controle sobre regras multi-tenant internas.
- mp-agente-whatsapp/ai-agents-hub: exemplos, nao base de producao.

## Arquitetura alvo

```text
Chatwoot Webhook / Evento WhatsApp / Job SDR
  -> SdrConversationLedger
  -> SdrPolicyEngine
  -> LangGraph SdrStateMachine
  -> SdrRetrievalContext
  -> SdrActionPlanner
  -> SdrMessageComposer
  -> SdrOutputGuard
  -> SdrSendGateway / Chatwoot API
  -> SdrTraceAndEval
```

## Responsabilidades

### SdrConversationLedger

Fonte unica da conversa. Registra toda entrada, saida, tentativa, bloqueio,
handoff, erro, motivo de adiamento e proximo horario. Nenhum follow-up roda sem
saida anterior confirmada.

### SdrPolicyEngine

Decide se pode agir antes do LLM:

- plano permite SDR;
- WhatsApp conectado;
- horario de abordagem respeitado;
- limite diario/mensal;
- cooldown;
- opt-out;
- humano assumiu;
- tenant correto;
- lead tem site pronto;
- existe historico minimo para follow-up.

### SdrStateMachine

Controla transicoes permitidas:

```text
new -> intro -> qualify -> pain -> proof -> reveal -> feedback -> close
    -> scheduled -> followup
    -> handoff | won | lost | opt_out
```

Transicao proibida: `new -> reveal`.

### SdrRetrievalContext

Monta contexto com RAG nativo, configuracao do tenant, historico do lead,
produto/plano atual, site gerado e fatos do negocio. O LLM recebe somente
campos estruturados e textos confiaveis.

### SdrActionPlanner

Decide a acao antes da mensagem:

- send_message;
- ask_clarifying_question;
- schedule_followup;
- handoff_human;
- stop_due_policy;
- retry_later;
- mark_lost/won.

### SdrMessageComposer

Gera a mensagem curta e humana dentro da acao aprovada. Ele nao decide sozinho
se pode mandar link, cobrar, prometer desconto, responder 24h ou chamar humano.

### SdrOutputGuard

Bloqueia mensagem se violar contrato:

- link antes de `reveal`;
- "aqui de novo" sem saida anterior;
- promessa nao documentada;
- preco inventado;
- mensagem longa demais;
- tom agressivo;
- resposta fora do horario de abordagem;
- envio apos humano assumir.

### SdrSendGateway

Unico ponto que envia WhatsApp. So envia depois do guard aprovado e grava
interacao de saida apenas quando a API confirma sucesso.

### SdrTraceAndEval

Todo atendimento gera trace com estado anterior, decisao, ferramenta usada,
mensagem final, motivo de bloqueio e custo. Evals devem simular:

- lead frio;
- lead responde "quem e?";
- lead pede humano;
- lead pede para voltar depois;
- WhatsApp desconectado;
- horario fechado;
- starter sem SDR;
- lead ja recebeu link;
- follow-up sem historico.

## Roadmap seguro

### Fase 0 - Sem risco em producao

1. Saneamento dos leads antigos: todo follow-up sem saida registrada volta para
   fila inicial controlada.
2. Criar `SdrOutputGuard` e testes de contrato antes de qualquer envio real.
3. Criar simulador de conversa com fixtures por tenant/plano/stage.

### Fase 1 - Gateway proprio

1. Criar `backend/services/sdr_gateway.py`.
2. Centralizar plano, horario, WPP, cooldown, humano assumiu, opt-out e lead
   pronto antes do composer.
3. Gravar ledger estruturado antes/depois do envio.
4. Manter Bryan/Franz atual apenas como `SdrMessageComposer` legado.

### Fase 2 - LangGraph local

1. Instalar LangGraph localmente, sem alterar deploy ate passar nos testes.
2. Modelar estados: `new`, `intro`, `qualify`, `pain`, `proof`, `reveal`,
   `feedback`, `close`, `scheduled`, `handoff`, `won`, `lost`, `opt_out`.
3. Fazer cada transicao chamar ferramentas deterministicas da FraLib.
4. Persistir checkpoint por `tenant_id + lead_id + conversation_id`.

### Fase 3 - Chatwoot isolado

1. Subir Chatwoot separado em Docker, fora da pipeline de sites.
2. Criar inbox por tenant ou mapeamento seguro tenant/inbox.
3. Conectar AgentBot ao webhook da FraLib.
4. Mostrar link para conversa na dashboard FraLib.
5. Handoff: quando lead pedir humano, Chatwoot muda conversa para `open` e
   FraLib trava o bot para aquele lead.

### Fase 4 - Corte controlado

1. Rodar shadow mode: Franz v2 decide, mas Bryan envia por uma janela curta.
2. Comparar decisao v2 vs envio real em trace/eval.
3. Liberar v2 para um tenant de teste.
4. Liberar por plano: trial/pro/ilimitado.
5. Remover o caminho Bryan antigo quando os testes reais passarem.

## Criterios para vender

- Nenhum envio sem tenant, plano e WhatsApp validados.
- Nenhum follow-up sem saida anterior registrada.
- Nenhum link antes da apresentacao/contexto minimo.
- Nenhum job some por horario fechado ou WPP desconectado.
- Todo envio tem ledger, trace e custo.
- Todo handoff humano para o bot.
- Starter bloqueia SDR, Trial permite experiencia completa, Pro/Ilimitado
  liberam conforme contrato comercial.
