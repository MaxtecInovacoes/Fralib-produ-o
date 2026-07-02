# AUDITORIA COMPLETA: Pipeline FraLib e Construção de Sites

## ÍNDICE
1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Pipeline CI/CD (GitHub Actions)](#2-pipeline-cicd-github-actions)
3. [Pipeline de Geração de Sites (11 Fases)](#3-pipeline-de-geração-de-sites-11-fases)
4. [Construção do Frontend](#4-construção-do-frontend)
5. [Stack de Serviços](#5-stack-de-serviços)
6. [Fluxo Completo: Requisição → Site Público](#6-fluxo-completo-requisição--site-público)

---

## 1. VISÃO GERAL DA ARQUITETURA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRA LIB - ARQUITETURA                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USUÁRIO                                                                  │
│      │                                                                    │
│      ▼                                                                    │
│   ┌──────────────┐                                                        │
│   │   FRONTEND   │ ◄── HTML estático (landing.html, dashboard.html)       │
│   │   (Nginx)    │ ◄── Vite React Build (dist/)                          │
│   └──────┬───────┘                                                        │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │                    FASTAPI SERVER (server.py)                     │    │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │    │
│   │  │ Pipeline │ │  Leads   │ │  Sites   │ │  Auth    │            │    │
│   │  │Endpoints │ │Endpoints │ │Endpoints │ │Endpoints │            │    │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │    │
│   └──────────────────────────────────────────────────────────────────┘    │
│          │                                                                 │
│          ▼                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │  POSTGRESQL  │    │    REDIS     │    │    WORKERS   │              │
│   │  (Dados)     │    │  (Filas)     │    │  (Async Jobs)│              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PIPELINE CI/CD (GITHUB ACTIONS)

### 2.1 Arquivos de Configuração
- `.github/workflows/ci.yml` - Pipeline de integração contínua
- `.github/workflows/deploy.yml` - Pipeline de deploy produção
- `docker-compose.yml` - Stack de serviços local
- `Dockerfile` - Imagem container da aplicação

### 2.2 Fluxo CI (a cada push/PR)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE CI EXECUÇÃO                         │
└─────────────────────────────────────────────────────────────────┘

   PUSH/PR em main/master
          │
          ▼
   ┌──────────────────┐
   │ 1. LINT & SECURITY│
   │ - ruff check      │
   │ - bandit (security)│
   │ - safety check    │
   └────────┬──────────┘
            │
            ▼
   ┌──────────────────┐
   │ 2. UNIT TESTS    │
   │ - PostgreSQL (mock)│
   │ - pytest tests/   │
   │ - Coverage XML   │
   └────────┬──────────┘
            │
            ▼
   ┌──────────────────┐
   │ 3. FRONTEND BUILD│
   │ - verify_canonical│
   │ - check_landing   │
   └────────┬──────────┘
            │
            ▼
   ┌──────────────────┐
   │ 4. MIGRATIONS    │
   │ - Alembic dry-run│
   └────────┬──────────┘
            │
            ▼
   ┌──────────────────┐
   │ 5. DEPLOY STAGING│
   │ (só em master)   │
   └────────┬──────────┘
            │
            ▼
   ┌──────────────────┐
   │ 6. SECURITY SCAN │
   │ - Trivy scanner  │
   └──────────────────┘
```

### 2.3 Deploy Produção (Manual)

```
┌─────────────────────────────────────────────────────────────────┐
│                  DEPLOY PRODUÇÃO (workflow_dispatch)            │
└─────────────────────────────────────────────────────────────────┘

   GitHub UI → Actions → "Deploy Production" → Workflow Dispatch
          │
          ▼
   ┌──────────────────────────┐
   │ PRE-DEPLOY VALIDATION    │
   │ - Ruff lint check        │
   │ - verify_frontend_canonical│
   │ - pipeline.py smoke       │
   └───────────┬──────────────┘
               │ (todos OK)
               ▼
   ┌──────────────────────────┐
   │ SSH para PROD server      │
   │ git push prod master      │
   └───────────┬──────────────┘
               │
               ▼
   ┌──────────────────────────┐
   │ POST-RECEIVE HOOK        │
   │ 1. git pull              │
   │ 2. Validar frontend      │
   │ 3. npm install           │
   │ 4. Build frontend        │
   │ 5. PM2 restart           │
   └───────────┬──────────────┘
               │
               ▼
         HEALTH CHECK
```

---

## 3. PIPELINE DE GERAÇÃO DE SITES (11 FASES)

### 3.1 Mapa das Fases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE GERAÇÃO DE SITE                               │
│                        11 FASES EXECUÇÃO                                    │
└─────────────────────────────────────────────────────────────────────────────┘

   INÍCIO ───►
               │
               ▼
   ┌─────────────────┐
   │ FASE 1: HUNTER  │ ◄── Busca leads no Google Maps
   │ hunter_kw       │     + Pesquisa de keywords
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 2: CAIO   │ ◄── Qualificação do lead (score 0-100)
   │ caio            │     Rejeita scores < 45
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 3: JINA    │ ◄── Pesquisa de mercado (Jina AI)
   │ jina            │     Extrai insights do nicho
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 4: INTELIG.│ ◄── Análise concorrência
   │ inteligencia    │     Identifica oportunidades
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 5: FOTOS  │ ◄── Download de fotos do negócio
   │ fotos           │     Seleção automática
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 6: NICHO   │ ◄── Agente especializado
   │ agente_nicho    │     Define subnicho
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 7: VARIAÇÃO│ ◄── Define variação estrutural
   │ agente_variacao │     DNA visual do site
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 8: ARQUIT. │ ◄── Arquiteto de sites
   │ arquiteto_mestre│     Gera PRD (Product Requirements)
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 9: BUILDER │ ◄── GERA O CÓDIGO DO SITE
   │ builder_renderer│     Vite + React + TypeScript
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 10: DEPLOY │ ◄── Publica site
   │ deploy          │     Copia para /var/www/fralib/sites
   └────────┬────────┘
            │
            ▼
   ┌─────────────────┐
   │ FASE 11: FRANZ  │ ◄── Envio WhatsApp
   │ franz           │     Notifica cliente
   └─────────────────┘
               │
               ▼
            FIM ✓
```

### 3.2 Detalhamento de Cada Fase

#### FASE 1: HUNTER + KEYWORD
```python
# backend/services/pipeline_executors.py
async def executar_fase1_hunter(state, config, ...):
    # 1. Keyword Research (ThreadPoolExecutor paralelo)
    keywords = pesquisar_keywords_nicho(segmento, cidade)
    
    # 2. Busca leads Google Maps
    leads = await buscar_leads_google_maps(
        cidade=state.cidade,
        segmento=state.segmento,
        limite=config.get("_candidate_pool_limit", 10),
        ...
    )
    return leads
```
**Output:** Lista de leads + keywords do nicho

---

#### FASE 2: CAIO (Qualificação)
```python
# Qualificação por IA
caio_input = CaioInput(
    nome=lead.nome,
    cidade=lead.cidade,
    segmento=lead.segmento,
    rating=lead.rating,
    reviews_count=lead.total_avaliacoes,
    fotos=lead.fotos,
)
qualificacao = await qualificar_lead(caio_input)

# Score < 45 = REJEITADO
if qualificacao.score < 45:
    qualificacao.qualificado = False
    qualificacao.tier = "REJEITADO"
```
**Output:** `{qualificado: bool, score: int, tier: str, motivo: str}`

---

#### FASE 3: JINA (Inteligência de Mercado)
```python
# Pesquisa com Jina AI
jina_insights = await buscar_inteligencia_jina(
    segmento=segmento,
    cidade=cidade,
    lead_data=lead
)
```
**Output:** Insights de mercado, tendências, oportunidades

---

#### FASE 4: INTELIGÊNCIA (Concorrência)
```python
# Análise competitiva
concorrentes = await analisar_concorrencia(segmento, cidade)
oportunidades = identificar_oportunidades(concorrentes)
```
**Output:** Análise de concorrência e gaps de mercado

---

#### FASE 5: FOTOS
```python
# Download e curadoria de fotos
fotos = await baixar_fotos(lead.fotos)
fotos_selecionadas = selecionar_melhores_fotos(fotos, limite=5)
```
**Output:** Array de URLs de fotos otimizadas

---

#### FASE 6: NICHO (Subnicho)
```python
# Derivar subnicho específico
subniche = derive_subniche(
    segmento,
    services=lead.servicos,
    reviews=lead.reviews,
    keywords=keyword_research,
    business_name=lead.nome
)
```
**Output:** `subniche: str` (ex: "academia-feminina", "restaurante-japones")

---

#### FASE 7: VARIAÇÃO (DNA Visual)
```python
# Define variação estrutural do site
variacao = definir_variacao_estrutural(
    subniche=subniche,
    negocio=lead,
    referencias=insights
)
```
**Output:** `{layout: str, estilo: str, cores: {...}, componentes: [...]}`

---

#### FASE 8: ARQUITETO (PRD)
```python
# Gera Product Requirements Document
prd = build_skill_fast_prd(state)
# Inclui:
# - business_name, segmento, cidade
# - visual_direction, visual_dna
# - requirements_contract
# - visual_contract
# - site_build_plan
# - layout_blueprint
```
**Output:** PRD completo com todos os dados do negócio

---

#### FASE 9: BUILDER (Geração Vite+React)
```python
# ORQUESTRADOR PRINCIPAL - backend/services/vite_react_renderer.py

# 1. Prepara prompts para LLM
prompt = _build_vite_react_system_prompt_with_facts(prd)
user_prompt = _compose_vite_user_prompt(prd)

# 2. Envia para LLM (Claude/Sonnet)
codigo = await llm_router.generate(prompt, user_prompt)

# 3. Extrai arquivos do código gerado
arquivos = extract_vite_project_files(codigo)

# 4. Escreve arquivos no workspace
workspace = /tmp/fralib_builder/{tenant_id}/{job_id}/
for arquivo in arquivos:
    escrever(workspace / arquivo.path, arquivo.conteudo)

# 5. Instala dependências
npm install

# 6. Build Vite
npm run build  # → dist/

# 7. Valida output
validate_vite_dist(workspace / "dist")
```
**Output:** Pasta `dist/` com site compilado

---

#### FASE 10: DEPLOY (Publicação)
```python
# Copia site para diretório público
destino = /var/www/fralib/sites/{tenant_id}/{slug}/
copiar(workspace/dist, destino)

# Atualiza banco
atualizar_site_url(pipeline_id, site_url)

# Health check
verificar_site(site_url)
```
**Output:** Site público em `https://{slug}.fralib.com`

---

#### FASE 11: FRANZ (Notificação)
```python
# Envia WhatsApp para cliente
await franz_service.enviar_mensagem(
    telefone=lead.whatsapp,
    mensagem=f"Olá! Seu site está pronto: {site_url}"
)
```
**Output:** Notificação enviada

---

## 4. CONSTRUÇÃO DO FRONTEND

### 4.1 Estrutura de Arquivos

```
frontend/
├── landing.html           # Landing page principal (149KB)
├── dashboard.html         # Painel admin (156KB)
├── admin.html            # Superadmin
├── studio.html           # Editor de sites
├── login.html            # Autenticação
├── planos.html           # Planos e preços
├── oferta.html           # Página de oferta
├── onboarding.html       # onboarding
├── blog/
│   └── index.html
├── docs/
│   └── index.html
├── partials/             # Blocos reutilizáveis
│   ├── landing/
│   │   ├── _head.html
│   │   ├── _nav.html
│   │   ├── _hero.html
│   │   ├── _offer.html
│   │   ├── _produto.html
│   │   └── ...
│   └── dashboard/
│       ├── _head.html
│       ├── _sidebar.html
│       └── ...
├── css/
├── js/
├── static/
└── build.py              # Script de build (concatena partials)
```

### 4.2 Build Process (build.py)

```python
# frontend/build.py
def build(name, partials_order):
    chunks = []
    for partial in partials_order:
        with open(f'partials/{name}/{partial}') as f:
            chunks.append(f.read())
    
    with open(f'{name}.html', 'w') as f:
        f.write('\n'.join(chunks))

# LANDING_ORDER define a ordem dos blocos:
LANDING_ORDER = [
    '_head.html',           # Meta tags, CSS
    '_nav.html',            # Navegação
    '_hero.html',           # Banner principal
    '_opportunity-simulator.html',
    '_offer.html',          # Oferta
    '_produto.html',       # Produto
    '_before-after.html',
    '_como-funciona.html',
    '_whatsapp-mockup.html',
    '_funcionalidades.html',
    '_beta-proof.html',
    '_planos.html',        # Preços
    '_guarantee.html',
    '_nichos.html',
    '_para-quem.html',
    '_faq.html',
    '_beta-form.html',
    '_footer.html',
    '_whatsapp-float.html', # WhatsApp flutuante
    '_sticky-cta.html',
    '_scripts.html',
]
```

### 4.3 Landing Page - Seções Principais

```
┌─────────────────────────────────────────┐
│            LANDING PAGE                 │
├─────────────────────────────────────────┤
│ _nav.html: Navbar com logo e menu       │
├─────────────────────────────────────────┤
│ _hero.html:                            │
│   - Headline principal                  │
│   - Subheadline                        │
│   - CTA button                         │
│   - Imagem do produto                  │
├─────────────────────────────────────────┤
│ _opportunity-simulator.html:           │
│   - Calculadora de oportunidade        │
├─────────────────────────────────────────┤
│ _offer.html:                           │
│   - Oferta principal                   │
│   - Preço                              │
│   - Bônus                              │
├─────────────────────────────────────────┤
│ _produto.html:                         │
│   - Descrição do produto/SaaS          │
├─────────────────────────────────────────┤
│ _funcionalidades.html:                 │
│   - Lista de features                  │
├─────────────────────────────────────────┤
│ _planos.html:                          │
│   - Tabela de planos                   │
├─────────────────────────────────────────┤
│ _faq.html: Perguntas frequentes         │
├─────────────────────────────────────────┤
│ _footer.html:                          │
│   - Links                              │
│   - Redes sociais                      │
├─────────────────────────────────────────┤
│ _whatsapp-float.html: Botão WA fixo    │
└─────────────────────────────────────────┘
```

---

## 5. STACK DE SERVIÇOS

### 5.1 Docker Compose Services

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["127.0.0.1:15433:5432"]
    volumes: [fralib-postgres:/var/lib/postgresql/data]
    
  redis:
    image: redis:7-alpine
    ports: ["127.0.0.1:16379:6379"]
    volumes: [fralib-redis:/data]
    
  app:
    build: .
    ports: ["127.0.0.1:18000:8000"]
    command: ["python", "server.py"]
    depends_on: [postgres, redis]
    
  worker:
    build: .
    command: ["python", "worker.py"]
    # Jobs: pipeline_lead, pipeline_multiplos, lead_supply_hunter
    
  bryan-worker:
    build: .
    command: ["python", "worker.py"]
    # Jobs: bryan_outreach (SDR)
```

### 5.2 Endpoints Principais (server.py)

```python
# Imports de routers
import auth_endpoints
import dashboard_endpoints
import pipeline_endpoints
import pipeline_status_endpoints
import pipeline_start_endpoints
import leads_endpoints
import users_endpoints
import whatsapp_endpoints
import llm_endpoints
import superadmin_endpoints
import site_editor_endpoints
import lead_supply_endpoints
import analytics_endpoints
# ... 100+ endpoints
```

---

## 6. FLUXO COMPLETO: REQUISIÇÃO → SITE PÚBLICO

### 6.1 Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      FLUXO COMPLETO: USUÁRIO → SITE PÚBLICO                     │
└─────────────────────────────────────────────────────────────────────────────────┘

   1. USUÁRIO ACESSA FRONTEND
   │
   │   Browser → GET /landing.html
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 2. NGINX/FILESYSTEM                                             │
   │    Serve arquivos estáticos de frontend/                         │
   │    - landing.html                                               │
   │    - dashboard.html                                             │
   │    - css/*.css                                                  │
   │    - js/*.js                                                    │
   └─────────────────────────────────────────────────────────────────┘
   │
   │   (se API) → GET /api/pipeline/start
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 3. FASTAPI (server.py:8000)                                     │
   │    Recebe requisição → Routing                                   │
   └─────────────────────────────────────────────────────────────────┘
   │
   │   Pipeline endpoints em: backend/endpoints/pipeline_*.py
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 4. PIPELINE ORCHESTRATOR (pipeline_builders.py)                │
   │    Coordena as 11 fases em sequência                            │
   │                                                                 │
   │    for fase in range(1, 12):                                   │
   │        executar_fase[fase](state)                               │
   │        salvar_checkpoint(state)                                 │
   │        emitir_sse_progress(fase)                                │
   └─────────────────────────────────────────────────────────────────┘
   │
   │   (Fase 9: Builder)
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 5. VITE REACT RENDERER (vite_react_renderer.py)                │
   │                                                                 │
   │    a) Preparar PRD                                              │
   │       prd = build_skill_fast_prd(state)                        │
   │                                                                 │
   │    b) Gerar código com LLM                                      │
   │       codigo = llm_router.generate(prompt, prd)                 │
   │                                                                 │
   │    c) Extrair arquivos                                          │
   │       arquivos = extract_vite_project_files(codigo)            │
   │                                                                 │
   │    d) Escrever workspace                                        │
   │       workspace = /tmp/fralib_builder/{tenant}/{job}/          │
   │       for arq in arquivos:                                      │
   │           write(workspace/arq.path, arq.conteudo)               │
   │                                                                 │
   │    e) Build Vite                                                │
   │       subprocess.run(["npm", "install"])                        │
   │       subprocess.run(["npm", "run", "build"])                   │
   │       # Output: workspace/dist/                                │
   │                                                                 │
   │    f) Validar                                                   │
   │       validate_vite_dist(workspace/dist)                        │
   └─────────────────────────────────────────────────────────────────┘
   │
   │   (Fase 10: Deploy)
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 6. PUBLICAÇÃO (publicar.py)                                    │
   │                                                                 │
   │    destino = /var/www/fralib/sites/{tenant}/{slug}/           │
   │    copiar(workspace/dist, destino)                             │
   │                                                                 │
   │    # Atualiza nginx config se necessário                        │
   │    recarregar_nginx()                                          │
   │                                                                 │
   │    site_url = https://{slug}.fralib.com                        │
   └─────────────────────────────────────────────────────────────────┘
   │
   │   (Fase 11: Franz)
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 7. NOTIFICAÇÃO (whatsapp_automation_service.py)               │
   │                                                                 │
   │    await whatsapp.enviar_mensagem(                             │
   │        telefone=lead.whatsapp,                                  │
   │        mensagem=f"Seu site está pronto: {site_url}"            │
   │    )                                                            │
   └─────────────────────────────────────────────────────────────────┘
   │
   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │ 8. SITE PÚBLICO ACESSÍVEL                                      │
   │                                                                 │
   │    https://{slug}.fralib.com                                   │
   │    ou                                                          │
   │    https://fralib.com/sites/{tenant}/{slug}/                  │
   └─────────────────────────────────────────────────────────────────┘
```

### 6.2 Dados que Viajam pelo Pipeline

```python
# State que é passado entre fases
@dataclass
class FraLibState:
    segmento: str              # "Academia", "Restaurante", etc.
    cidade: str                # "São Paulo", "Rio de Janeiro"
    pipeline_id: str           # ID único do pipeline
    tenant_id: int             # ID do tenant/usuário
    
    # Dados do lead
    lead_raw_data: dict        # Dados brutos do Google Maps
    lead_obj: Lead             # Objeto Lead do banco
    lead_nome: str             # Nome do negócio
    lead_slug: str             # Slug para URL
    
    # Outputs das fases
    keyword_research: str      # F1: Keywords do nicho
    qualificacao_caio: dict    # F2: Score e qualificação
    jina_insights: str         # F3: Insights de mercado
    alex_result: dict          # F4: Análise concorrência
    
    # PRD e Build
    prd_arquiteto: dict        # F8: Product Requirements
    builder_output_dir: str     # F9: Diretório do build
    html_sections: List[str]   # F9: Seções HTML
    html_final: str            # F9: HTML final
    
    # Output final
    site_url: str              # F10: URL pública
```

---

## 7. VALIDAÇÕES E QUALITY GATES

### 7.1 Quality Gate do Builder

```python
# vite_validator.py - Validações antes de publicar

def _validate_studio_project(workspace):
    """Valida projeto Vite React"""
    # 1. Verifica arquivos obrigatórios
    # 2. Verifica imports válidos
    # 3. Verifica dependências
    pass

def _validate_hero_first_viewport(workspace):
    """Hero deve estar no primeiro viewport"""
    # Verifica CSS do hero
    pass

def _validate_mobile_navbar(workspace):
    """Navbar responsiva"""
    # Verifica media queries
    pass

def validate_vite_dist(dist_path):
    """Valida output do build"""
    # 1. index.html existe
    # 2. assets/ com JS/CSS
    # 3. Sem erros de build
    pass
```

### 7.2 Pipeline Smoke Tests

```bash
# Verificações pré-deploy
python pipeline.py smoke --dry-run
```

---

## 8. RESUMO EXECUTIVO

| Aspecto | Detalhe |
|---------|---------|
| **CI/CD** | GitHub Actions (6 jobs em paralelo) |
| **Backend** | FastAPI + PostgreSQL + Redis |
| **Workers** | Processos Python assíncronos |
| **Frontend** | HTML estático (partials concatenados) |
| **Builder Sites** | Vite + React + TypeScript |
| **Pipeline Fases** | 11 fases sequenciais |
| **Tempo Estimado** | ~5-10 minutos por site |
| **Deploy** | Git push → post-receive hook |

---

*Documento gerado em: 2026-07-01*
*Versão: FraLib v2.0.0*
