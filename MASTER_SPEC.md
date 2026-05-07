# MASTER_SPEC.md - FraLib OS
## Documento de Arquitetura e Roadmap de Qualidade
**Versao:** 1.0 | **Data:** 2026-04-30 | **Status:** PLANEJAMENTO

---

## Visao Geral

FraLib OS e um SaaS de geracao automatica de sites para negocios locais.
Pipeline: Hunter -> Caio -> Alex -> Theo -> Designer PRD -> Liam -> Liz -> Bryan
Backend: FastAPI + PostgreSQL | Frontend: dashboard.html monolitico (3356 linhas)

**Prioridade de execucao:**
1. SEGURANCA (bloqueia producao se ignorada)
2. TESTES (garante que correcoes nao quebram nada)
3. REFATORACAO FRONTEND (qualidade e manutenibilidade)

---

## MISSAO 1 - SEGURANCA

### Vulnerabilidades identificadas

#### ALTA - Bloquear antes de qualquer deploy

**SEC-01: Token JWT logado em plaintext**
- Arquivo: /root/fralib/backend/core/auth.py linha 14
- Problema: print com token JWT expoe credencial nos logs
- Risco: Qualquer pessoa com acesso aos logs consegue se autenticar como qualquer usuario
- Correcao: Remover o print ou substituir por [REDACTED]

**SEC-02: Stripe keys sem validacao obrigatoria**
- Arquivo: /root/fralib/backend/endpoints/credits_endpoints.py linhas 22-23
- Problema: stripe.api_key usa fallback silencioso se .env nao configurado
- Risco: Stripe usa chave invalida silenciosamente em producao
- Correcao: Remover fallback, levantar ValueError se chave nao configurada

**SEC-03: STRIPE_PAYMENT_LINK hardcoded no codigo**
- Arquivo: /root/fralib/backend/endpoints/credits_endpoints.py linha 25
- Problema: URL de pagamento hardcoded no codigo-fonte
- Risco: Exposicao de link de pagamento no repositorio
- Correcao: Mover para .env como STRIPE_PAYMENT_LINK

**SEC-04: Content-Security-Policy permissiva no dashboard**
- Arquivo: /root/fralib/frontend/dashboard.html linha 6
- Problema: connect-src permite ws:// (sem TLS) e IP direto exposto
- Risco: WebSocket sem criptografia, IP da VPS exposto no HTML publico
- Correcao: Usar wss:// e substituir IP por dominio

#### MEDIA - Corrigir antes de escalar

**SEC-05: Ausencia de validacao de webhook Stripe**
- Arquivo: /root/fralib/backend/endpoints/credits_endpoints.py
- Problema: Nao ha verificacao de assinatura do webhook
- Risco: Qualquer pessoa pode simular um pagamento bem-sucedido via POST
- Correcao: Implementar stripe.Webhook.construct_event com STRIPE_WEBHOOK_SECRET

**SEC-06: SQL via text() sem parametrizacao em alguns pontos**
- Arquivo: /root/fralib/backend/endpoints/pipeline_endpoints.py
- Problema: Alguns campos do lead podem ser interpolados diretamente em queries
- Risco: SQL injection se dados do Hunter nao forem sanitizados
- Correcao: Garantir que TODOS os valores passem como parametros {:param}

**SEC-07: Ausencia de rate limiting no endpoint de pipeline**
- Arquivo: /root/fralib/backend/endpoints/pipeline_endpoints.py
- Problema: POST /api/pipeline/iniciar nao tem rate limiting
- Risco: Usuario pode disparar centenas de pipelines e estourar creditos/API
- Correcao: Adicionar rate limiting (5 pipelines por minuto por usuario)

**SEC-08: Arquivos .backup expostos na pasta de producao**
- Arquivos: /root/fralib/backend/agents/*.backup*, /root/fralib/backend/endpoints/*.backup*
- Problema: Arquivos de backup acessiveis no servidor de producao
- Risco: Exposicao de logica de negocio e possiveis credenciais em versoes antigas
- Correcao: Mover para /root/fralib/backups/ fora do diretorio servido

---

## MISSAO 2 - TESTES

### Estrategia

Nao ha nenhum teste automatizado no projeto. Adotar pytest com cobertura minima de 80% nos modulos criticos.

### Suites de teste a criar

**TEST-01: Testes unitarios dos agentes**
- Pasta: /root/fralib/tests/test_agents/
- Escopo: Cada agente testado isoladamente com mock do call_claude
- Prioridade: Liz (logica de auditoria), Alex (mapeamento de paleta), Theo (dark/light mode)
- Framework: pytest + unittest.mock

**TEST-02: Testes de integracao do pipeline**
- Pasta: /root/fralib/tests/test_pipeline/
- Escopo: Pipeline completo com dados mockados (sem chamar API Claude real)
- Verificar: Checkpoint funciona, retomada de onde parou, fallbacks nao quebram
- Framework: pytest + httpx

**TEST-03: Testes de seguranca**
- Pasta: /root/fralib/tests/test_security/
- Escopo: Auth (token expirado, invalido, sem token), rate limiting, SQL injection basico
- Framework: pytest + httpx

**TEST-04: Testes de contrato dos agentes**
- Pasta: /root/fralib/tests/test_contracts/
- Escopo: Verificar que cada agente retorna o schema Pydantic correto
- Framework: pytest + pydantic

### Estrutura de pastas

/root/fralib/tests/
  conftest.py
  test_agents/
    test_alex.py, test_theo.py, test_designer_prd.py, test_liam.py, test_liz.py
  test_pipeline/
    test_checkpoint.py, test_pipeline_flow.py
  test_security/
    test_auth.py, test_rate_limit.py
  test_contracts/
    test_agent_schemas.py

---

## MISSAO 3 - REFATORACAO FRONTEND

### Problema atual

dashboard.html tem 3356 linhas com CSS inline, JS inline e HTML misturados.
Impossivel de manter, testar ou reutilizar componentes.

### Arquitetura alvo

/root/fralib/frontend/
  dashboard.html          (apenas estrutura HTML, sem CSS/JS inline)
  css/
    dashboard.css         (variaveis CSS, layout base, sidebar, header)
    components.css        (cards, botoes, badges, modais)
    pipeline.css          (logs SSE, kanban, pipeline UI)
    animations.css        (transicoes, keyframes)
  js/
    dashboard.js          (inicializacao, roteamento de views)
    pipeline.js           (logica do pipeline, SSE listener)
    kanban.js             (drag-and-drop, cards de leads)
    charts.js             (graficos Chart.js)
    auth-helper.js, csrf-helper.js, socket-client.js, toast.js (ja existem - manter)

### Regras de refatoracao

- Nao alterar comportamento visual - apenas separar codigo
- Manter todas as variaveis CSS em :root no dashboard.css
- Cada arquivo JS com responsabilidade unica
- Nenhum script inline no HTML (exceto configuracao minima)
- Testar no browser apos cada arquivo extraido

---

## Issues Atomicas - Ordem de Execucao

### Fase 1 - Seguranca (executar PRIMEIRO)

| Issue  | Arquivo                                 | Acao                                     |
|--------|-----------------------------------------|------------------------------------------|
| SEC-01 | backend/core/auth.py                    | Remover print com token JWT              |
| SEC-02 | backend/endpoints/credits_endpoints.py | Remover fallback Stripe keys             |
| SEC-03 | backend/endpoints/credits_endpoints.py | Mover PAYMENT_LINK para .env             |
| SEC-04 | frontend/dashboard.html                 | Corrigir CSP: ws->wss, IP->dominio       |
| SEC-05 | backend/endpoints/credits_endpoints.py | Implementar verificacao webhook Stripe   |
| SEC-06 | backend/endpoints/pipeline_endpoints.py| Auditar queries SQL com f-string         |
| SEC-07 | backend/endpoints/pipeline_endpoints.py| Adicionar rate limiting no pipeline      |
| SEC-08 | backend/agents/*.backup*               | Mover backups para /root/fralib/backups/ |

### Fase 2 - Testes (executar SEGUNDO)

| Issue   | Arquivo               | Acao                                 |
|---------|-----------------------|--------------------------------------|
| TEST-01 | tests/conftest.py     | Criar estrutura de testes + fixtures |
| TEST-02 | tests/test_agents/    | Testes unitarios dos agentes         |
| TEST-03 | tests/test_pipeline/  | Testes de integracao do pipeline     |
| TEST-04 | tests/test_security/  | Testes de seguranca                  |
| TEST-05 | tests/test_contracts/ | Testes de contrato dos schemas       |

### Fase 3 - Refatoracao Frontend (executar TERCEIRO)

| Issue | Arquivo                    | Acao                                     |
|-------|----------------------------|------------------------------------------|
| FE-01 | frontend/css/dashboard.css | Extrair variaveis CSS e layout base      |
| FE-02 | frontend/css/components.css| Extrair CSS de componentes               |
| FE-03 | frontend/css/pipeline.css  | Extrair CSS do pipeline/kanban           |
| FE-04 | frontend/js/dashboard.js   | Extrair JS de inicializacao              |
| FE-05 | frontend/js/pipeline.js    | Extrair JS do pipeline/SSE               |
| FE-06 | frontend/js/kanban.js      | Extrair JS do kanban                     |
| FE-07 | frontend/js/charts.js      | Extrair JS dos graficos                  |
| FE-08 | frontend/dashboard.html    | Validar que ficou apenas HTML estrutural |

---

## Regras do Protocolo DUCK

- PLANEJAMENTO APENAS neste documento - nenhum codigo alterado ainda
- Cada Issue e atomica: uma mudanca, um arquivo, um objetivo
- Antes de executar qualquer Issue: revisar este documento juntos
- Apos cada Issue: testar que nada quebrou antes de avancar
- NUNCA pular para Fase 2 sem Fase 1 concluida
- NUNCA pular para Fase 3 sem Fase 2 concluida

---

**Proximo passo:** Revisar este documento com o Senhor e aprovar antes de iniciar Issue SEC-01
