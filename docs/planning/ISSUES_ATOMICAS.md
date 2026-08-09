# ISSUES ATÔMICAS - FraLib OS Rebuild

**Data:** 2026-04-29  
**Baseado em:** MASTER_SPEC.md v1.0  
**Total de Issues:** 24  
**Tempo Total Estimado:** 36-48 horas (5-6 dias)

---

## 🔴 FASE 1: SEGURANÇA (12 Issues - 12h)

### **DIA 1 - VULNERABILIDADES CRÍTICAS (4 Issues - 4h)**

#### Issue #1: Corrigir SQL Injection em database.py
**Prioridade:** 🔴 CRÍTICA  
**Tempo:** 30 min  
**Bloqueante:** Sim

**Objetivo:**
Validar nomes de colunas contra whitelist antes de usar em queries dinâmicas

**Arquivos afetados:**
- `/opt/fralib/backend/core/database.py` (linhas 145, 151)

**Critérios de Aceitação:**
- [ ] Criar whitelist de colunas permitidas
- [ ] Validar keys antes de usar em `set_clause`
- [ ] Lançar exceção se coluna inválida
- [ ] Testar com coluna válida e inválida

**Testes:**
- [ ] Teste manual: Tentar atualizar com coluna inválida (deve falhar)
- [ ] Teste automatizado: `pytest tests/unit/test_database.py::test_sql_injection`

---

#### Issue #2: Corrigir XSS em dashboard.html (Parte 1 - Linhas 1296, 1624, 1661)
**Prioridade:** 🔴 CRÍTICA  
**Tempo:** 45 min  
**Bloqueante:** Sim

**Objetivo:**
Substituir innerHTML por textContent nas primeiras 3 ocorrências de XSS

**Arquivos afetados:**
- `/opt/fralib/frontend/dashboard.html` (linhas 1296, 1624, 1661)

**Critérios de Aceitação:**
- [ ] Linha 1296: Usar textContent em vez de innerHTML
- [ ] Linha 1624: Usar textContent em vez de innerHTML
- [ ] Linha 1661: Usar textContent em vez de innerHTML
- [ ] Testar que mensagens aparecem corretamente

**Testes:**
- [ ] Teste manual: Inserir `<script>alert('XSS')</script>` em campo (não deve executar)
- [ ] Teste E2E: `playwright tests/e2e/test_xss_protection.py`

---

#### Issue #3: Corrigir XSS em dashboard.html (Parte 2 - Linhas 1699, 1730, 1739)
**Prioridade:** 🔴 CRÍTICA  
**Tempo:** 45 min  
**Bloqueante:** Sim

**Objetivo:**
Substituir innerHTML por textContent nas próximas 3 ocorrências de XSS

**Arquivos afetados:**
- `/opt/fralib/frontend/dashboard.html` (linhas 1699, 1730, 1739)

**Critérios de Aceitação:**
- [ ] Linha 1699: Usar textContent em vez de innerHTML
- [ ] Linha 1730: Usar textContent em vez de innerHTML
- [ ] Linha 1739: Usar textContent em vez de innerHTML
- [ ] Testar que dados aparecem corretamente

**Testes:**
- [ ] Teste manual: Inserir HTML malicioso (não deve renderizar)
- [ ] Teste E2E: `playwright tests/e2e/test_xss_protection.py`

---

#### Issue #4: Corrigir XSS em dashboard.html (Parte 3 - Linhas 1810, 1832, 2307)
**Prioridade:** 🔴 CRÍTICA  
**Tempo:** 45 min  
**Bloqueante:** Sim

**Objetivo:**
Substituir innerHTML por textContent nas últimas 3 ocorrências de XSS

**Arquivos afetados:**
- `/opt/fralib/frontend/dashboard.html` (linhas 1810, 1832, 2307)

**Critérios de Aceitação:**
- [ ] Linha 1810: Usar textContent em vez de innerHTML
- [ ] Linha 1832: Usar textContent em vez de innerHTML
- [ ] Linha 2307: Usar textContent em vez de innerHTML (MAIS CRÍTICO)
- [ ] Testar que logs aparecem corretamente

**Testes:**
- [ ] Teste manual: Inserir script em log (não deve executar)
- [ ] Teste E2E: `playwright tests/e2e/test_xss_protection.py`

---

### **DIA 2 - VULNERABILIDADES ALTAS (4 Issues - 4h)**

#### Issue #5: Adicionar Rate Limiting com slowapi
**Prioridade:** 🟠 ALTA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Instalar slowapi e adicionar rate limiting em endpoints críticos

**Arquivos afetados:**
- `/opt/fralib/backend/requirements.txt`
- `/opt/fralib/backend/endpoints/auth_endpoints.py`
- `/opt/fralib/backend/endpoints/credits_endpoints.py`
- `/opt/fralib/server.py`

**Critérios de Aceitação:**
- [ ] Instalar slowapi: `pip install slowapi`
- [ ] Adicionar limiter no server.py
- [ ] Limitar /api/auth/login: 5 req/min
- [ ] Limitar /api/credits/payment-link: 10 req/min
- [ ] Testar que 6ª requisição retorna 429

**Testes:**
- [ ] Teste manual: Fazer 6 logins em 1 min (6º deve falhar)
- [ ] Teste automatizado: `pytest tests/integration/test_rate_limiting.py`

---

#### Issue #6: Implementar CSRF Protection
**Prioridade:** 🟠 ALTA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Adicionar tokens CSRF em todos endpoints POST/PUT/DELETE

**Arquivos afetados:**
- `/opt/fralib/backend/requirements.txt`
- `/opt/fralib/server.py`
- `/opt/fralib/frontend/js/csrf-helper.js` (já existe, validar)

**Critérios de Aceitação:**
- [ ] Instalar fastapi-csrf-protect: `pip install fastapi-csrf-protect`
- [ ] Configurar middleware CSRF no server.py
- [ ] Validar que csrf-helper.js funciona
- [ ] Testar que POST sem token retorna 403

**Testes:**
- [ ] Teste manual: POST sem token CSRF (deve falhar)
- [ ] Teste automatizado: `pytest tests/integration/test_csrf.py`

---

#### Issue #7: Corrigir Logs Sensíveis
**Prioridade:** 🟠 ALTA  
**Tempo:** 15 min  
**Bloqueante:** Não

**Objetivo:**
Remover email dos logs, logar apenas user_id

**Arquivos afetados:**
- `/opt/fralib/backend/endpoints/pipeline_endpoints.py` (linha 52)

**Critérios de Aceitação:**
- [ ] Substituir `usuario["email"]` por `usuario["id"]`
- [ ] Verificar outros arquivos com grep "logger.*email"
- [ ] Testar que logs não mostram email

**Testes:**
- [ ] Teste manual: Iniciar pipeline, verificar logs (não deve ter email)
- [ ] Teste automatizado: `pytest tests/unit/test_logging.py`

---

#### Issue #8: Corrigir Estado Global do Pipeline
**Prioridade:** 🟠 ALTA  
**Tempo:** 60 min  
**Bloqueante:** Sim (multi-tenant quebrado)

**Objetivo:**
Mover estado do pipeline de variável global para banco de dados

**Arquivos afetados:**
- `/opt/fralib/backend/endpoints/pipeline_endpoints.py` (linhas 14-18)
- `/opt/fralib/backend/core/database.py` (adicionar tabela pipeline_state)

**Critérios de Aceitação:**
- [ ] Criar tabela `pipeline_state` (tenant_id, rodando, pausado, config, updated_at)
- [ ] Remover variável global `pipeline_state`
- [ ] Ler/escrever estado do banco filtrado por tenant_id
- [ ] Testar que 2 tenants não compartilham estado

**Testes:**
- [ ] Teste manual: Iniciar pipeline em 2 contas diferentes (devem ser independentes)
- [ ] Teste automatizado: `pytest tests/integration/test_pipeline_isolation.py`

---

### **DIA 3 - VULNERABILIDADES MÉDIAS (4 Issues - 4h)**

#### Issue #9: Configurar Nginx com HTTPS Redirect
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Instalar Nginx e configurar redirect HTTP→HTTPS

**Arquivos afetados:**
- `/etc/nginx/sites-available/fralib` (novo)
- `/etc/nginx/sites-enabled/fralib` (symlink)

**Critérios de Aceitação:**
- [ ] Instalar Nginx: `apt install nginx`
- [ ] Criar config com redirect HTTP→HTTPS
- [ ] Configurar proxy_pass para :8000
- [ ] Testar que http:// redireciona para https://

**Testes:**
- [ ] Teste manual: Acessar http://187.77.37.72 (deve redirecionar para https://)
- [ ] Teste automatizado: `curl -I http://187.77.37.72 | grep 301`

---

#### Issue #10: Adicionar Content Security Policy Headers
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 30 min  
**Bloqueante:** Não

**Objetivo:**
Adicionar CSP headers para prevenir XSS externo

**Arquivos afetados:**
- `/opt/fralib/server.py`

**Critérios de Aceitação:**
- [ ] Adicionar middleware CSP
- [ ] Header: `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'`
- [ ] Testar que scripts externos não carregam

**Testes:**
- [ ] Teste manual: Inspecionar headers no DevTools (deve ter CSP)
- [ ] Teste automatizado: `pytest tests/integration/test_csp_headers.py`

---

#### Issue #11: Implementar Alembic Migrations
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 90 min  
**Bloqueante:** Não

**Objetivo:**
Configurar Alembic para versionamento de schema

**Arquivos afetados:**
- `/opt/fralib/alembic.ini` (novo)
- `/opt/fralib/alembic/` (pasta nova)
- `/opt/fralib/backend/requirements.txt`

**Critérios de Aceitação:**
- [ ] Instalar Alembic: `pip install alembic`
- [ ] Inicializar: `alembic init alembic`
- [ ] Configurar connection string no alembic.ini
- [ ] Criar migration inicial: `alembic revision --autogenerate -m "initial"`
- [ ] Testar: `alembic upgrade head`

**Testes:**
- [ ] Teste manual: Rodar migration (deve criar tabelas)
- [ ] Teste automatizado: `pytest tests/integration/test_migrations.py`

---

#### Issue #12: Configurar Bcrypt Salt Rounds
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 15 min  
**Bloqueante:** Não

**Objetivo:**
Adicionar salt rounds explícito no bcrypt

**Arquivos afetados:**
- `/opt/fralib/backend/endpoints/auth_endpoints.py` (linha 28)

**Critérios de Aceitação:**
- [ ] Adicionar `bcrypt.gensalt(rounds=12)` ao criar senha
- [ ] Testar que senhas novas usam 12 rounds
- [ ] Senhas antigas continuam funcionando

**Testes:**
- [ ] Teste manual: Criar novo usuário, verificar hash (deve ter 12 rounds)
- [ ] Teste automatizado: `pytest tests/unit/test_bcrypt_rounds.py`

---

## 🧪 FASE 2: TESTES (8 Issues - 8h)

### **DIA 4 - SETUP + UNIT TESTS (4 Issues - 4h)**

#### Issue #13: Setup Infraestrutura de Testes
**Prioridade:** 🟠 ALTA  
**Tempo:** 30 min  
**Bloqueante:** Sim (para outros testes)

**Objetivo:**
Instalar pytest, criar estrutura de pastas, configurar fixtures

**Arquivos afetados:**
- `/opt/fralib/backend/requirements.txt`
- `/opt/fralib/tests/conftest.py` (novo)
- `/opt/fralib/tests/unit/` (pasta nova)
- `/opt/fralib/tests/integration/` (pasta nova)
- `/opt/fralib/tests/e2e/` (pasta nova)

**Critérios de Aceitação:**
- [ ] Instalar: `pip install pytest pytest-asyncio httpx`
- [ ] Criar estrutura de pastas
- [ ] Criar conftest.py com fixtures (db_session, test_client)
- [ ] Testar: `pytest --collect-only` (deve encontrar 0 testes)

**Testes:**
- [ ] Teste manual: Rodar `pytest` (deve passar sem erros)

---

#### Issue #14: Testes Unitários - Auth
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Escrever testes unitários para auth.py e auth_endpoints.py

**Arquivos afetados:**
- `/opt/fralib/tests/unit/test_auth.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar create_access_token (token válido)
- [ ] Testar verify_password (senha correta/incorreta)
- [ ] Testar login com credenciais válidas
- [ ] Testar login com credenciais inválidas
- [ ] Cobertura ≥ 80% em auth.py

**Testes:**
- [ ] Teste automatizado: `pytest tests/unit/test_auth.py -v`

---

#### Issue #15: Testes Unitários - Database
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Escrever testes unitários para database.py

**Arquivos afetados:**
- `/opt/fralib/tests/unit/test_database.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar criar_schema_tenant (schema criado)
- [ ] Testar SQL injection (deve falhar com coluna inválida)
- [ ] Testar get_db (retorna sessão válida)
- [ ] Cobertura ≥ 80% em database.py

**Testes:**
- [ ] Teste automatizado: `pytest tests/unit/test_database.py -v`

---

#### Issue #16: Testes Unitários - Utils
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Escrever testes unitários para utils críticos (brain, memory, validation_enforcer)

**Arquivos afetados:**
- `/opt/fralib/tests/unit/test_utils.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar brain.py (funções principais)
- [ ] Testar memory.py (salvar/carregar)
- [ ] Testar validation_enforcer.py (validações)
- [ ] Cobertura ≥ 70% em utils/

**Testes:**
- [ ] Teste automatizado: `pytest tests/unit/test_utils.py -v`

---

### **DIA 5 - INTEGRATION + E2E (4 Issues - 4h)**

#### Issue #17: Testes de Integração - API Auth
**Prioridade:** 🟠 ALTA  
**Tempo:** 45 min  
**Bloqueante:** Não

**Objetivo:**
Testar endpoints de autenticação end-to-end

**Arquivos afetados:**
- `/opt/fralib/tests/integration/test_api_auth.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar POST /api/auth/login (sucesso)
- [ ] Testar POST /api/auth/login (falha - senha errada)
- [ ] Testar GET /api/auth/me (com token válido)
- [ ] Testar GET /api/auth/me (sem token - 401)

**Testes:**
- [ ] Teste automatizado: `pytest tests/integration/test_api_auth.py -v`

---

#### Issue #18: Testes de Integração - API Pipeline
**Prioridade:** 🟠 ALTA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Testar endpoints do pipeline end-to-end

**Arquivos afetados:**
- `/opt/fralib/tests/integration/test_api_pipeline.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar POST /api/pipeline/iniciar (sucesso)
- [ ] Testar POST /api/pipeline/pausar (sucesso)
- [ ] Testar POST /api/pipeline/parar (sucesso)
- [ ] Testar GET /api/pipeline/status (retorna estado correto)
- [ ] Testar isolamento multi-tenant (2 usuários diferentes)

**Testes:**
- [ ] Teste automatizado: `pytest tests/integration/test_api_pipeline.py -v`

---

#### Issue #19: Testes E2E - Login Flow
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Testar fluxo completo de login no navegador

**Arquivos afetados:**
- `/opt/fralib/tests/e2e/test_login_flow.py` (novo)
- `/opt/fralib/backend/requirements.txt` (adicionar playwright)

**Critérios de Aceitação:**
- [ ] Instalar Playwright: `pip install playwright && playwright install`
- [ ] Testar abrir /login
- [ ] Testar preencher email/senha
- [ ] Testar clicar em "Entrar"
- [ ] Testar redirect para /dashboard

**Testes:**
- [ ] Teste automatizado: `pytest tests/e2e/test_login_flow.py -v`

---

#### Issue #20: Testes E2E - Pipeline Flow
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Testar fluxo completo do pipeline no navegador

**Arquivos afetados:**
- `/opt/fralib/tests/e2e/test_pipeline_flow.py` (novo)

**Critérios de Aceitação:**
- [ ] Testar login
- [ ] Testar clicar em "Iniciar Pipeline"
- [ ] Testar que SSE conecta e recebe logs
- [ ] Testar clicar em "Pausar"
- [ ] Testar clicar em "Parar"

**Testes:**
- [ ] Teste automatizado: `pytest tests/e2e/test_pipeline_flow.py -v`

---

## 🎨 FASE 3: REFATORAÇÃO FRONTEND (4 Issues - 12h)

### **DIA 6-7 - MODULARIZAÇÃO (4 Issues - 12h)**

#### Issue #21: Criar Componentes Base (Web Components)
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 120 min  
**Bloqueante:** Sim (para refatoração)

**Objetivo:**
Criar Web Components reutilizáveis (sidebar, header, stats-card)

**Arquivos afetados:**
- `/opt/fralib/frontend/components/sidebar.js` (novo)
- `/opt/fralib/frontend/components/header.js` (novo)
- `/opt/fralib/frontend/components/stats-card.js` (novo)
- `/opt/fralib/frontend/components/pipeline-controls.js` (novo)

**Critérios de Aceitação:**
- [ ] Criar `<fl-sidebar>` component
- [ ] Criar `<fl-header>` component
- [ ] Criar `<fl-stats-card>` component
- [ ] Criar `<fl-pipeline-controls>` component
- [ ] Testar que componentes renderizam corretamente

**Testes:**
- [ ] Teste manual: Abrir test.html com componentes (devem renderizar)
- [ ] Teste E2E: `playwright tests/e2e/test_components.py`

---

#### Issue #22: Refatorar admin.html (Modularizar)
**Prioridade:** 🟠 ALTA  
**Tempo:** 180 min  
**Bloqueante:** Não

**Objetivo:**
Reduzir admin.html de 3.343 para < 500 linhas usando componentes

**Arquivos afetados:**
- `/opt/fralib/frontend/admin.html`
- `/opt/fralib/frontend/modules/admin.js` (novo)
- `/opt/fralib/frontend/modules/pipeline.js` (novo)
- `/opt/fralib/frontend/modules/credits.js` (novo)

**Critérios de Aceitação:**
- [ ] Substituir HTML inline por Web Components
- [ ] Mover lógica JavaScript para módulos separados
- [ ] Adicionar DOMPurify para sanitização
- [ ] admin.html < 500 linhas
- [ ] Testar que navegação funciona
- [ ] Testar que pipeline funciona

**Testes:**
- [ ] Teste manual: Navegar por todas as views (devem funcionar)
- [ ] Teste E2E: `playwright tests/e2e/test_admin_navigation.py`

---

#### Issue #23: Refatorar dashboard.html (Modularizar)
**Prioridade:** 🟠 ALTA  
**Tempo:** 180 min  
**Bloqueante:** Não

**Objetivo:**
Reduzir dashboard.html de 3.200 para < 500 linhas usando componentes

**Arquivos afetados:**
- `/opt/fralib/frontend/dashboard.html`
- `/opt/fralib/frontend/modules/dashboard.js` (novo)
- `/opt/fralib/frontend/modules/sse-client.js` (novo)

**Critérios de Aceitação:**
- [ ] Substituir HTML inline por Web Components
- [ ] Mover lógica JavaScript para módulos separados
- [ ] Adicionar DOMPurify para sanitização
- [ ] dashboard.html < 500 linhas
- [ ] Testar que SSE funciona
- [ ] Testar que gráficos funcionam

**Testes:**
- [ ] Teste manual: Abrir dashboard, verificar SSE e gráficos
- [ ] Teste E2E: `playwright tests/e2e/test_dashboard_sse.py`

---

#### Issue #24: Criar Design System CSS Modular
**Prioridade:** 🟡 MÉDIA  
**Tempo:** 60 min  
**Bloqueante:** Não

**Objetivo:**
Separar CSS em arquivos modulares (design-system, components, layouts)

**Arquivos afetados:**
- `/opt/fralib/frontend/css/design-system.css` (novo)
- `/opt/fralib/frontend/css/components.css` (novo)
- `/opt/fralib/frontend/css/layouts.css` (novo)

**Critérios de Aceitação:**
- [ ] Extrair variáveis CSS para design-system.css
- [ ] Extrair estilos de componentes para components.css
- [ ] Extrair layouts para layouts.css
- [ ] Testar que visual não mudou

**Testes:**
- [ ] Teste manual: Comparar visual antes/depois (deve ser idêntico)
- [ ] Teste E2E: `playwright tests/e2e/test_visual_regression.py`

---

## 📊 RESUMO

**Total de Issues:** 24  
**Tempo Total:** 36-48 horas (5-6 dias)

**Por Fase:**
- 🔴 **Segurança:** 12 issues (12h) - Dias 1-3
- 🧪 **Testes:** 8 issues (8h) - Dias 4-5
- 🎨 **Frontend:** 4 issues (12h) - Dias 6-7

**Por Prioridade:**
- 🔴 **CRÍTICA:** 4 issues (3h)
- 🟠 **ALTA:** 8 issues (8h)
- 🟡 **MÉDIA:** 12 issues (21h)

---

## 🎯 PRÓXIMA AÇÃO

**AGORA:** Apresentar este plano ao Senhor para aprovação

**Após aprovação:**
1. Criar CLAUDE.md do projeto (Issue #0 - pré-requisito)
2. Começar Issue #1 (SQL Injection)
3. Executar sequencialmente, task por task
4. Atualizar ESTADO-PROJETO.json após cada issue
5. Fazer commit no Obsidian após cada fase

---

**Status:** 🟡 AGUARDANDO APROVAÇÃO DO SENHOR
