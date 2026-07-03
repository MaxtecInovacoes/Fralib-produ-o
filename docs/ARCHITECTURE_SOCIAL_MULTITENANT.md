# Arquitetura: Sistema de Auto-Post Multi-Tenant (Redes Sociais)

> **Objetivo**: Permitir que a FraLib atenda múltiplos clientes/perfis, cada um com seu próprio:
> - Nicho e estratégia de conteúdo
> - Credenciais Meta (Page Token, Instagram Business ID)
> - Calendário editorial
> - Scheduler de postagem
> - Logs e métricas
>
> **Base**: Segue o padrão multi-tenant existente da FraLib (`tenant_id` em toda query, `FERNET_KEY` para segredos).

---

## 1. Estrutura de Diretórios

```
/root/fralib/
├── projects/                          # ←NOVO: diretório raiz de projetos
│   ├── fralib/                      # Projeto 1: FraLib (negócios digitais)
│   │   ├── config.env               # Variáveis específicas do projeto
│   │   ├── content/
│   │   │   ├── calendar.json         # Calendário editorial (30 dias)
│   │   │   ├── posts/               # Posts gerados
│   │   │   └── assets/              # Imagens/vídeos gerados
│   │   ├── logs/
│   │   │   └── social-post.log
│   │   └── analysis/
│   │       ├── viral_patterns.json   # Padrões de viralização do nicho
│   │       └── competitors.json      # Análise de concorrentes
│   │
│   ├── energia_solar/                # Projeto 2: Energia Solar
│   │   ├── config.env
│   │   ├── content/
│   │   │   ├── calendar.json
│   │   │   ├── posts/
│   │   │   └── assets/
│   │   ├── logs/
│   │   └── analysis/
│   │
│   └── [outro_projeto]/             # Novo cliente = nova pasta
│       ├── config.env
│       └── ...
│
├── scripts/
│   ├── auto_post_social.py           # ←ADAPTAR: aceita --project argument
│   ├── cron_social_post.sh           # ←ADAPTAR: varre todos os projects
│   ├── gerar_post.py                 # ←ADAPTAR: aceita --project
│   └── gerar_imagens.py              # ←ADAPTAR: aceita --project
│
└── backend/
    ├── models/
    │   └── social_project.py         # ←NOVO: modelo SQLAlchemy
    ├── services/
    │   ├── social_project_service.py  # ←NOVO: CRUD de projetos
    │   └── content_generator.py      # ←ADAPTAR: suporte a project_context
```

---

## 2. Banco de Dados (Schema)

```sql
-- Tabela principal de projetos sociais
CREATE TABLE social_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_slug VARCHAR(100) NOT NULL,  -- ex: 'fralib', 'energia_solar'
    project_name VARCHAR(255) NOT NULL,  -- ex: 'FraLib - Negócios Digitais'
    
    -- Credenciais (criptografadas com FERNET_KEY)
    facebook_page_token_encrypted TEXT,
    facebook_page_id_encrypted TEXT,
    instagram_business_id_encrypted TEXT,
    linkedin_access_token_encrypted TEXT,
    twitter_bearer_token_encrypted TEXT,
    twitter_api_key_encrypted TEXT,
    twitter_api_secret_encrypted TEXT,
    twitter_access_token_encrypted TEXT,
    twitter_access_secret_encrypted TEXT,
    
    -- Configurações
    is_active BOOLEAN DEFAULT true,
    post_frequency_per_day INTEGER DEFAULT 1,
    preferred_post_time TIME DEFAULT '10:00:00',  -- horário BRT
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    
    -- Estratégia de conteúdo
    content_niche VARCHAR(100),        -- ex: 'negocios_digitais', 'energia_solar'
    content_tone VARCHAR(50),         -- ex: 'aggressive', 'friendly', 'professional'
    content_formats TEXT[],            -- ARRAY['reels', 'carousel', 'static']
    content_hooks TEXT[],             -- ARRAY de hooks que funcionam no nicho
    content_ctas TEXT[],              -- ARRAY de CTAs do nicho
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_post_at TIMESTAMP,
    
    UNIQUE(tenant_id, project_slug)
);

-- Log de postagens por projeto
CREATE TABLE social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,
    
    platform VARCHAR(20) NOT NULL,    -- 'facebook', 'instagram', 'linkedin', 'twitter'
    post_type VARCHAR(20) NOT NULL,  -- 'reel', 'carousel', 'static', 'story'
    content_text TEXT,
    media_urls TEXT[],               -- URLs das mídias postadas
    media_local_paths TEXT[],        -- Paths locais (se geração própria)
    
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'published', 'failed'
    external_post_id VARCHAR(255),    -- ID returned by Meta/LinkedIn/Twitter
    published_at TIMESTAMP,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Calendário editorial por projeto
CREATE TABLE content_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,
    
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    platform VARCHAR(20) NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    topic VARCHAR(255),
    hook VARCHAR(500),
    caption_template TEXT,
    media_brief TEXT,               -- Brief pro gerador de imagem/vídeo
    status VARCHAR(20) DEFAULT 'draft',  -- 'draft', 'generated', 'ready', 'published'
    
    post_id UUID REFERENCES social_posts(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, scheduled_date, platform)
);

-- Análise de viralização por nicho
CREATE TABLE niche_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES social_projects(id) ON DELETE CASCADE,
    
    competitor_username VARCHAR(255),
    platform VARCHAR(20),
    total_followers INTEGER,
    avg_engagement_rate NUMERIC(5,2),
    top_posts JSONB,                -- Array de posts mais engajados
    top_hooks JSONB,               -- Hooks que mais funcionaram
    content_patterns JSONB,         -- Padrões identificados
    analyzed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. Variáveis de Ambiente (por projeto)

Cada projeto em `/projects/[slug]/config.env`:

```bash
# Projeto: energia_solar
# ============

# Identificação
PROJECT_SLUG=energia_solar
PROJECT_NAME="SolarTech - Energia Solar Residencial"
TENANT_ID=uuid-do-cliente-aqui

# Credenciais Meta (criptografadas)
FACEBOOK_PAGE_TOKEN=ENC:fernet_encrypted_string_aqui
FACEBOOK_PAGE_ID=ENC:fernet_encrypted_string_aqui
INSTAGRAM_BUSINESS_ID=ENC:fernet_encrypted_string_aqui

# Outras redes (opcional)
LINKEDIN_ACCESS_TOKEN=ENC:fernet_encrypted_string_aqui
TWITTER_BEARER_TOKEN=ENC:fernet_encrypted_string_aqui
# ...

# Configurações
POST_FREQUENCY_PER_DAY=2
PREFERRED_POST_TIME=10:30
TIMEZONE=America/Sao_Paulo

# Nicho
CONTENT_NICHE=energia_solar
CONTENT_TONE=professional
CONTENT_FORMATS=["reels","carousel","static"]
CONTENT_HOOKS=["pergunta","lista","depoimento","perigo","promessa"]
CONTENT_CTAS=["link_na_bio","whatsapp","link_artigo"]

# Caminhos
CONTENT_DIR=/root/fralib/projects/energia_solar/content
ASSETS_DIR=/root/fralib/projects/energia_solar/assets
LOG_DIR=/root/fralib/projects/energia_solar/logs
```

---

## 4. Scripts Adaptados

### 4.1 `auto_post_social.py` — aceita `--project`

```bash
# Uso
python scripts/auto_post_social.py --project energia_solar
python scripts/auto_post_social.py --project fralib
python scripts/auto_post_social.py --all  # roda todos os projetos ativos
```

Internamente:
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--project', type=str, help='Slug do projeto (ex: fralib, energia_solar)')
parser.add_argument('--all', action='store_true', help='Roda todos os projetos ativos')
args = parser.parse_args()

# Carrega config do projeto
if args.project:
    load_project_config(args.project)
elif args.all:
    projects = get_all_active_projects()
    for project in projects:
        load_project_config(project.slug)
        run_auto_post()
```

### 4.2 `cron_social_post.sh` — varre todos

```bash
#!/bin/bash
# Roda todos os projetos ativos, um por um

PROJECTS_DIR="/root/fralib/projects"

for project_dir in $PROJECTS_DIR/*/; do
    PROJECT_SLUG=$(basename "$project_dir")
    
    # Pula se não tem config.env
    if [ ! -f "$project_dir/config.env" ]; then
        continue
    fi
    
    echo "=== Processando projeto: $PROJECT_SLUG ==="
    
    # Carrega config
    set -a
    source "$project_dir/config.env"
    set +a
    
    # Executa auto-post
    cd /root/fralib
    source .venv/bin/activate
    python3 scripts/auto_post_social.py --project "$PROJECT_SLUG" \
        >> "$project_dir/logs/social-post.log" 2>&1
done
```

---

## 5. API Endpoints (FastAPI)

```python
# backend/endpoints/social_projects.py

@router.get("/social-projects")
def list_social_projects(tenant_id: UUID = Depends(get_current_tenant)):
    """Lista todos os projetos sociais do tenant."""
    return db.query(SocialProject).filter(
        SocialProject.tenant_id == tenant_id,
        SocialProject.is_active == True
    ).all()

@router.post("/social-projects")
def create_social_project(
    project: SocialProjectCreate,
    tenant_id: UUID = Depends(get_current_tenant)
):
    """Cria novo projeto social (cliente)."""
    # Cria diretório, config.env, etc.
    # Insere no banco
    
@router.get("/social-projects/{project_id}/calendar")
def get_project_calendar(
    project_id: UUID,
    start_date: date,
    end_date: date
):
    """Retorna calendário editorial do projeto."""
    
@router.post("/social-projects/{project_id}/generate-posts")
def generate_posts_for_project(
    project_id: UUID,
    topics: List[str],
    count: int = 3
):
    """Gera posts baseados em tendências do nicho."""
    
@router.post("/social-projects/{project_id}/publish")
def publish_post(
    project_id: UUID,
    post_id: UUID
):
    """Publica um post específico."""
```

---

## 6. Scheduler (Cron)

```bash
# /etc/cron.d/fralib-social-post

# Rode todo dia às 10:00 BRT (depois do blog)
0 10 * * * root /bin/bash /root/fralib/scripts/cron_social_post.sh >> /var/log/fralib/cron_social.log 2>&1
```

O `cron_social_post.sh` varre todos os projetos em `/projects/*/`, carrega cada `config.env`, e executa o auto-post individual.

---

## 7. Geração de Imagens/Vídeos (ComfyUI)

Cada projeto pode ter seu próprio workflow ComfyUI:

```
projects/
├── fralib/
│   └── workflows/
│       └── blog_post.json      # Workflow para posts de blog
├── energia_solar/
│   └── workflows/
│       ├── reel_solar.json    # Reels sobre economia de energia
│       └── carousel_solar.json # Carrossel educativo
```

O gerador de imagem (`gerar_imagens.py`) aceita `--project` e carrega o workflow específico do nicho.

---

## 8. Fluxo de Trabalho (Execução)

```
[cron - 10:00 BRT]
    │
    ├─→ cron_social_post.sh
    │       │
    │       ├─→ Projeto 1: fralib
    │       │       └─→ auto_post_social.py --project fralib
    │       │               │
    │       │               ├─→ Buscar tendências do nicho (Fralib)
    │       │               ├─→ Gerar copy (via LLM + prompt do nicho)
    │       │               ├─→ Gerar mídia (ComfyUI + workflow do nicho)
    │       │               ├─→ Postar em FB + IG + LinkedIn + Twitter
    │       │               └─→ Salvar log em projects/fralib/logs/
    │       │
    │       ├─→ Projeto 2: energia_solar
    │       │       └─→ auto_post_social.py --project energia_solar
    │       │               │
    │       │               ├─→ Buscar tendências do nicho (energia solar)
    │       │               ├─→ Gerar copy (tom técnico/professional)
    │       │               ├─→ Gerar mídia (ComfyUI + workflow solar)
    │       │               ├─→ Postar em FB + IG + LinkedIn + Twitter
    │       │               └─→ Salvar log em projects/energia_solar/logs/
    │       │
    │       └─→ ... (outros projetos)
    │
    └─→ Logs agregados em /var/log/fralib/social-post.log
```

---

## 9. isolated Environment (Opcional)

Cada projeto pode ter seu próprio ambiente Python isolado:

```
projects/fralib/
├── venv/                    # Ambiente virtual próprio (opcional)
├── requirements.txt
└── scripts/
```

Mas **não é necessário** — pode usar o venv global da FraLib. Depende do nível de isolamento que quiser.

---

## 10. Monitoramento e Métricas

### Dashboard por Projeto
- Posts publicados por dia/semana
- Engajamento médio por plataforma
- Taxa de erro por rede
- Próximo post agendado

### Logs Centralizados
```bash
# Ver logs de um projeto específico
tail -f /root/fralib/projects/energia_solar/logs/social-post.log

# Ver todos os projetos
tail -f /var/log/fralib/social-post.log
```

### Alertas
- Se `auto_post_social.py` retornar RC != 0 por 3 dias consecutivos
- Se taxa de erro > 20% em qualquer plataforma

---

## 11. Crescimento: Adicionar Novo Projeto

Passo a passo para adicionar um novo cliente/nicho:

```bash
# 1. Criar diretório
mkdir -p /root/fralib/projects/novo_nicho

# 2. Criar config.env (a partir do template)
cp /root/fralib/projects/template/config.env /root/fralib/projects/novo_nicho/config.env

# 3. Editar com as credenciais do cliente
nano /root/fralib/projects/novo_nicho/config.env

# 4. Criar no banco (via API ou migration)
# INSERT INTO social_projects (...) VALUES (...)

# 5. Criar diretórios de conteúdo
mkdir -p /root/fralib/projects/novo_nicho/content/{posts,assets}
mkdir -p /root/fralib/projects/novo_nicho/logs
mkdir -p /root/fralib/projects/novo_nicho/analysis

# 6. Primeira análise de nicho (opcional)
python scripts/analyze_niche.py --project novo_nicho
```

---

## 12. Resumo de Arquitetura

| Componente | Onde fica | Isolamento |
|---|---|---|
| Código dos scripts | `/root/fralib/scripts/` | Compartilhado |
| Config por projeto | `/root/fralib/projects/[slug]/config.env` | Isolado |
| Posts gerados | `/root/fralib/projects/[slug]/content/posts/` | Isolado |
| Mídias geradas | `/root/fralib/projects/[slug]/content/assets/` | Isolado |
| Logs | `/root/fralib/projects/[slug]/logs/` | Isolado |
| Análise de nicho | `/root/fralib/projects/[slug]/analysis/` | Isolado |
| Credenciais | Banco (criptografadas com FERNET_KEY) | Isolado |
| Banco de dados | Tabelas `social_projects`, `social_posts`, `content_calendar` | Por tenant_id |

---

## Próximos Passos de Implementação

1. Criar migrations do banco (`social_projects`, `social_posts`, `content_calendar`)
2. Adaptar `auto_post_social.py` para aceitar `--project`
3. Adaptar `cron_social_post.sh` para varrer todos os projetos
4. Criar template de `config.env` em `projects/template/`
5. Criar primeiro projeto de teste (FraLib) via API ou migration
6. Testar com 1 projeto
7. Testar com 2 projetos simultâneos
8. Adicionar análise de nicho automática

---

*Arquitetura projetada em 2026-07-02 para suportar múltiplos clientes/perfis como uma agência.*
