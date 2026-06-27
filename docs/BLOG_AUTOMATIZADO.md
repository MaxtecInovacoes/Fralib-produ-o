# 📰 Blog Automatizado FraLib

Sistema automatizado de blog que gera posts diários sobre tendências do mercado.

## 🎯 Objetivo

Trazer tráfego orgânico para `https://seunegociofralib.site/blog/` através de:
- Posts diários sobre tendências (Google Trends, Twitter, Reddit)
- SEO otimizado (Schema Article, Open Graph, keywords)
- CTA para FraLib em cada post
- Auto-atualização do index.html

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────┐
│        FONTE DE TENDÊNCIAS              │
│   Google Trends + LLM (OpenRouter)      │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│       ROBÔ DE BUSCA (cron_blog)         │
│   - Roda todo dia às 8h                │
│   - Seleciona top 3 tendências         │
│   - Verifica duplicatas                │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│       GERADOR DE POST (LLM)            │
│   - LLM gera 500-700 palavras          │
│   - HTML otimizado com Schema          │
│   - Categorizado e taggeado            │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│       PUBLICADOR                       │
│   - Salva em frontend/blog/posts/      │
│   - Atualiza index.html               │
│   - Regenera sitemap.xml              │
└──────────────────────────────────────────┘
```

## 📁 Estrutura

```
frontend/blog/
├── index.html              # Lista de posts (auto-gerado)
└── posts/                  # Posts individuais
    ├── automacao-com-ia-para-pmes.html
    ├── whatsapp-business-api-2024.html
    └── ...

scripts/
├── cron_blog_automation.py  # Pipeline principal
└── cron_blog_setup.sh       # Setup do cron
```

## ⚙️ Configuração

### 1. Variável de ambiente (opcional)

```bash
# Para geração via LLM (recomendado)
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Sem essa variável, o sistema gera conteúdo fallback (template-based).

### 2. Cron job (Linux/VPS)

```bash
# Editar crontab
crontab -e

# Adicionar linha (todo dia 8h)
0 8 * * * /bin/bash /opt/fralib/scripts/cron_blog_setup.sh
```

### 3. Manual (teste local)

```bash
cd /opt/fralib
python3 scripts/cron_blog_automation.py
```

## 📊 Métricas

| Métrica | Meta | Tracking |
|---------|------|----------|
| Posts publicados/semana | 21+ | `ls posts/*.html \| wc -l` |
| Tráfego orgânico/dia | +10% semana | Clarity + Google Analytics |
| CTR blog → signup | > 5% | UTM `utm_source=blog` |
| Tempo na página | > 2min | Clarity heatmap |
| Bounce rate | < 60% | GA4 |

## 🎯 Categorias

```python
CATEGORIES = {
    "marketing":   "Marketing",         # Roxo
    "ia":          "IA & Automação",     # Verde neon
    "vendas":      "Vendas",             # Amarelo
    "freelancer":  "Freelancer",         # Roxo claro
    "tech":        "Tecnologia",         # Lilás
    "negócios":    "Negócios",           # Verde
}
```

## ✍️ SEO

Cada post gerado inclui:

- ✅ `<title>` otimizado com keyword
- ✅ `<meta description>` 150-160 chars
- ✅ `<meta keywords>` 5-7 keywords
- ✅ Canonical URL
- ✅ Open Graph tags (Facebook, LinkedIn)
- ✅ Twitter Card tags
- ✅ Schema.org JSON-LD (Article)
- ✅ Breadcrumb navigation
- ✅ Sitemap inclusion

## 📈 Estratégia de Conteúdo

Cada post segue o template:

1. **H1:** Tópico da tendência
2. **H2 - O que é:** Definição clara
3. **H2 - Por que importa:** Contexto de mercado
4. **H2 - Como aplicar:** 3 caminhos práticos
5. **H2 - Caso FraLib:** Como o FraLib resolve
6. **H2 - Conclusão:** CTA suave para FraLib
7. **CTA Box:** "Testa 7 dias grátis"

**Tom:** Conversa, direto, sem jargão.

## 🔄 Tópicos Atuais

Lista de tópicos que o robô busca (rotacionados diariamente):

- Automação com IA para PMEs
- WhatsApp Business API
- Gerador de sites com IA
- Prospecção B2B automatizada
- Marketing digital para freelancers
- SDR de IA vendendo no WhatsApp
- Google Maps como fonte de leads
- Como cobrar por site

## 🚀 Próximos Passos

- [ ] Integrar Google Trends API real (substituir tópicos hardcoded)
- [ ] Adicionar Twitter Trending
- [ ] RSS feeds de portais brasileiros
- [ ] Geração de thumbnail automático (DALL-E)
- [ ] Cross-posting para LinkedIn
- [ ] Newsletter semanal com top posts
- [ ] Backlinks internos entre posts
