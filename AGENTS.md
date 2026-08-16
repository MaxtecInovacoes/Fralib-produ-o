# FraLib - Instruções Obrigatórias para IAs

Este arquivo é a regra operacional principal do projeto. Se houver conflito com docs antigos, siga este arquivo e o `README.md`.

Leia também:
- `README.md`
- `docs/HANDOFF_PIPELINE_2026-08-14.md`

## Regra de Ouro
1. Não crie caminho paralelo.
2. Não recomece do zero.
3. Não recrie módulo que já existe.
4. Não use `backend/_arquivo/` em produção.
5. Não edite a VPS como fluxo principal.
6. Não invente pipeline, admin, worker ou renderer novo.

## Fonte da Verdade
Use sempre, nesta ordem:
1. `AGENTS.md`
2. `README.md`
3. `docs/HANDOFF_PIPELINE_2026-08-14.md`
4. docs antigos só se não contradisserem os três acima

## Como Trabalhar
Siga sempre este ciclo:
1. achar o arquivo oficial
2. provar que ele está em runtime por import, rota, worker, serviço ou log
3. entender o problema em banco, logs e comportamento real
4. fazer a menor correção possível
5. testar localmente
6. commit
7. push
8. validar em produção real
9. documentar o que foi feito e o que falta

## Como Encontrar o Problema
Antes de mexer em qualquer coisa:
- veja o sintoma real
- descubra o ponto de entrada real
- localize o arquivo oficial
- confirme o runtime real
- compare banco, logs e saída pública
- descubra exatamente onde o estado quebra
- só então corrija a causa raiz

## Como Resolver
1. Corrija a causa raiz, não o sintoma.
2. Altere o mínimo possível.
3. Preserve o fluxo oficial.
4. Remova duplicado, morto e monólito desnecessário.
5. Não faça enfeite, refactor cosmético ou reescrita sem ganho.
6. Se algo já existe e funciona, não recrie.
7. Se houver legado, não reative legado.

## Regra de Limpeza
Antes de tocar código:
- identifique monólitos
- separe apenas o necessário
- remova código morto
- remova duplicação
- mantenha o comportamento oficial

Objetivo:
- código menor
- mais claro
- mais previsível
- mais fácil de testar

## Ordem de Preferência
1. Endpoint oficial
2. Botão oficial do admin
3. Worker oficial
4. Arquivo oficial da pipeline
5. Banco apenas se necessário e com justificativa explícita

## Banco de Dados
Só mexa direto no banco quando:
- eu autorizar explicitamente
- não existir rota oficial equivalente
- for diagnóstico ou teste de laboratório

## Teste e Validação
Sempre que alterar pipeline, admin, OpenUI, deploy ou validação:
- rode teste local mínimo
- verifique o comportamento real
- valide em produção real
- confirme resultado no banco e na URL final

## Deploy Correto
```powershell
git status
pytest tests/unit/test_builder_prd_spec.py tests/unit/test_manager_intent_pipeline.py tests/unit/test_openui_handoff_safe_post.py tests/unit/test_visual_fingerprint_quality_gates.py -q
git add -A
git commit -m "mensagem objetiva"
git push github master
git push vps master
```

## Validação Obrigatória
Depois do deploy:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
systemctl is-active fralib-api.service
systemctl is-active fralib-openui.service
curl -I https://app.seunegociofralib.site/health
```

Se tocou pipeline:
1. use o admin ou `POST /api/pipeline/reprocessar/{lead_id}`
2. monitore `jobs`
3. confirme site HTTP `200`
4. confirme `leads.status='concluido'`
5. confirme `leads.erro_pipeline` vazio

## Como Continuar
Quando eu pedir continuidade:
1. leia o handoff mais recente
2. identifique o último ponto concluído
3. não recomece a investigação
4. continue do ponto exato
5. preserve decisões já tomadas

## Resposta Final
No final, sempre informe:
- o que foi feito
- quais arquivos mudaram
- como foi testado
- como foi validado
- o que ainda falta

## PROTOCOLO ANTI-DESVIO OBRIGATÓRIO

Antes de qualquer ação, eu devo responder mentalmente:

1. Qual é o objetivo exato do usuário?
2. Qual é o arquivo/serviço/tabela oficial envolvido?
3. Essa ação aproxima diretamente do objetivo?
4. Essa ação altera estado?
5. O usuário autorizou essa alteração específica?

Se qualquer resposta for "não sei", eu paro e pergunto.

### Regra de Escopo
Eu só posso mexer no que o usuário pediu explicitamente.

Proibido:
- corrigir bug lateral
- limpar arquivo lateral
- refatorar por oportunidade
- criar endpoint novo
- criar banco novo
- criar branch nova
- alterar `.env`
- mexer em frontend se a tarefa é backend
- mexer em pipeline se a tarefa é admin
- mexer em banco direto se existe endpoint oficial

### Regra de Progresso
A cada 3 comandos, eu devo parar e escrever:
- O que descobri
- O que isso prova
- Próxima ação exata
- Por que essa ação é necessária

### Regra de Mudança de Rota
Se eu perceber outro problema, eu NÃO corrijo.
Eu apenas registro:
"Encontrei um problema lateral: [descrição]. Deseja que eu corrija agora ou mantenho foco na tarefa original?"

### Regra de Estado
Antes de alterar qualquer coisa, eu devo mostrar:
- arquivo/tabela/serviço que será alterado
- motivo
- comando exato
- risco
- validação depois

Sem isso, não altero.

### Regra FraLib
Para FraLib:
- pasta oficial: `C:\fralib`
- branch oficial: `master`
- VPS oficial: `104.243.41.166`
- banco único: `fralib-postgres-1 / fralib_db / fralib_user`
- admin oficial: `frontend/admin.html`
- API oficial: `fralib-api.service`
- worker oficial: `fralib-worker-1`
- OpenUI oficial: `fralib-openui.service`

Nunca criar:
- outro banco
- outro container
- outro worker
- outro renderer
- outro admin
- outro pipeline
- outra branch sem autorização

### Frase de foco
> Não caia em caça ao tesouro. Siga o alvo original até concluir ou provar o bloqueio.

> Pista lateral não vira tarefa. Pista lateral vira anotação.

## Caminho Real
`Admin/API -> jobs.pipeline_lead -> worker.py -> backend/agents/manager/agent.py -> Hunter -> Caio -> Nicho -> Design Director -> Variação -> Arquiteto -> Builder/OpenUI -> Safe Post -> Quality Gates -> Deploy -> Franz`

## Runtime Real
- API: `server.py` via `fralib-api.service`
- Worker: `worker.py` via Docker `fralib-worker-1`
- OpenUI: `/opt/fralib/openui-wandb/backend/openui/generate.py`
- Sites: `/var/www/fralib/sites/`
- Banco: `fralib-postgres-1`
- Redis: `fralib-redis-1`
- Admin: `frontend/admin.html`

## Se Estiver em Dúvida
Pare e responda:
- qual arquivo oficial encontrou
- qual import/rota prova que ele é usado
- qual mudança mínima propõe
- quais testes vai rodar
