# FraLib - Resumo Operacional

Leia sempre nesta ordem antes de agir:
1. `AGENTS.md`
2. `README.md`
3. `docs/HANDOFF_PIPELINE_2026-08-14.md`

## Regra Principal
Siga sempre o fluxo oficial. Não recomece do zero, não crie caminho paralelo e não recrie o que já existe.

## Fluxo de Trabalho
1. Identifique o arquivo oficial e o runtime real.
2. Prove que ele é usado por import, rota, worker, serviço ou log.
3. Ache o problema em banco, logs e estado real.
4. Faça a menor correção possível.
5. Teste localmente.
6. Commit.
7. Push.
8. Valide em produção real.
9. Documente o que foi feito e o que falta.

## Como Resolver
- Corrija a causa raiz, não o sintoma.
- Preserve o fluxo oficial.
- Se algo já existe e funciona, não recrie.
- Se houver duplicado ou morto, remova.
- Se o arquivo virou monólito, simplifique antes de mexer.

## Como Testar
- Teste local mínimo.
- Teste unitário ou integrado do trecho alterado.
- Validação real na VPS quando envolver pipeline, admin, OpenUI ou deploy.
- Confirmação final no banco e na URL.

## Proibições
- Não criar renderer, FSM, worker ou admin novos.
- Não usar `backend/_arquivo/` em produção.
- Não mexer no banco direto se existir rota oficial para o mesmo objetivo.
- Não editar a VPS como caminho principal.
- Não inventar fluxo novo.

## Caminho Real
`Admin/API -> jobs.pipeline_lead -> worker.py -> backend/agents/manager/agent.py -> Hunter -> Caio -> Nicho -> Design Director -> Variação -> Arquiteto -> Builder/OpenUI -> Safe Post -> Quality Gates -> Deploy -> Franz`

## Runtime Real
- VPS: `104.243.41.166`
- Domínio: `https://app.seunegociofralib.site`
- API: `fralib-api.service`
- Worker: `fralib-worker-1`
- OpenUI: `fralib-openui.service`
- Sites: `/var/www/fralib/sites/`

## Se Travar
Pare e responda com:
- qual arquivo oficial está em uso
- qual rota/import prova isso
- qual é o menor ajuste
- quais testes vai rodar

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
