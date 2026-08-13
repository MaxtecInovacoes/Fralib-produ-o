# FraLib — Entrada Rápida para Claude/Agentes

Fonte de verdade: `README.md` e `AGENTS.md`.

Se você é uma IA abrindo esta pasta:

1. Leia `README.md`.
2. Leia `AGENTS.md`.
3. Não crie arquivos paralelos.
4. Não use docs antigos em `docs/` como fonte de verdade se contradisserem `README.md`.
5. Não edite a VPS direto; edite localmente, teste, commit, push.

## Caminho Real

```text
Admin/API
→ jobs.pipeline_lead
→ worker.py
→ backend/agents/manager/agent.py
→ Hunter
→ Caio
→ Nicho
→ Design Director
→ Variação
→ Arquiteto
→ Builder/OpenUI
→ Safe Post
→ Quality Gates
→ Deploy
→ Franz
```

## Produção

- VPS: `104.243.41.166`
- Domínio: `https://app.seunegociofralib.site`
- API: `fralib-api.service`
- Worker: Docker `fralib-worker-1`
- OpenUI: `fralib-openui.service`, porta `7878`
- Sites: `/var/www/fralib/sites/`

## Legado

Arquivos em `backend/_arquivo/` são histórico. Não importe.

## Último E2E Verde

Lead `Legacy Centro de Treinamento`, tenant `2`, job `480`, URL:

```text
https://app.seunegociofralib.site/sites/2/legacy-centro-de-treinamento-b0b7a7c0/
```
