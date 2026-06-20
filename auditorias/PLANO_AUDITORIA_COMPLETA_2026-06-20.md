# PLANO DE AUDITORIA COMPLETA — FraLib
## Versão 1.0 | Data: 2026-06-20

---

## 🎯 OBJETIVO DA AUDITORIA

Auditoria completa do sistema FraLib para verificar se a produção está funcionando conforme especificado, identificando:
1. **Paridade Local ↔ VPS** — código, configurações e artefatos são idênticos?
2. **Qualidade de Entrega** — sites saem cinematográficos, animados, com motion real?
3. **Execução de Agentes** — cada agente cumpre seu papel no pipeline?
4. **Skills e Design System** — estão sendo chamadas corretamente?
5. **SEO Local** — keywords reais baseadas em volume de pesquisa regional?
6. **Performance** — tempo de geração compare com promessa (< 8min, < tokens)?
7. **Segurança** — vulnerabilidades, multi-tenancy, proteção de dados?
8. **Escalabilidade** — capacidade de receber múltiplos usuários simultâneos?

---

## 📋 ESTRUTURA DA AUDITORIA

### FASE 1: Auditoria de Infraestrutura e Runtime
### FASE 2: Auditoria de Pipeline e Agentes
### FASE 3: Auditoria de Design e Entrega Visual
### FASE 4: Auditoria de SEO Local
### FASE 5: Auditoria de Performance e Escalabilidade
### FASE 6: Auditoria de Segurança
### FASE 7: Auditoria de Contratos e Specs

---

## 🔍 FASE 1: AUDITORIA DE INFRAESTRUTURA E RUNTIME

### 1.1 Paridade Local ↔ VPS

| # | Item de Verificação | Como Auditar | Critério de Sucesso |
|---|---------------------|--------------|---------------------|
| 1.1.1 | Comparar commits locais com deploy na VPS | `git log --oneline -10` local vs `git log` na VPS | Commits idênticos |
| 1.1.2 | Verificar se há arquivos diferentes | `diff -r` local vs `/root/fralib` na VPS | 0 diferenças |
| 1.1.3 | Comparar variáveis de ambiente | `env \| sort` local vs VPS | Diferenças documentadas |
| 1.1.4 | Verificar packages Python | `pip freeze` local vs VPS | Versões idênticas |
| 1.1.5 | Verificar node_modules | `npm ls` local vs VPS | Mesmos packages |

### 1.2 Status dos Serviços

| # | Item de Verificação | Como Auditar | Critério de Sucesso |
|---|---------------------|--------------|---------------------|
| 1.2.1 | PM2 status | `pm2 list` na VPS | Todos os processos "online" |
| 1.2.2 | fralib (porta 8000) | Health check `/api/health` | 200 OK |
| 1.2.3 | fralib-worker | Verificar se processa jobs | Jobs sendo consumidos |
| 1.2.4 | fralib-franz-worker | Verificar SDR ativo | Mensagens sendo enviadas |
| 1.2.5 | meowhats (porta 3001) | Verificar conexão WhatsApp | WhatsApp conectado |
| 1.2.6 | PostgreSQL | `pg_isready` ou query de teste | Conexão OK |

### 1.3 Logs e Monitoramento

| # | Item de Verificação | Como Auditar | Critério de Sucesso |
|---|---------------------|--------------|---------------------|
| 1.3.1 | Logs de erro recentes | `pm2 logs --err --lines 100` | 0 erros críticos |
| 1.3.2 | Jobs falhados | Query no banco: `pipeline_queue WHERE status='failed'` | < 5% de falha |
| 1.3.3 | Health checks | Verificar `/api/health` retornando dados corretos | Tempo < 200ms |

---

## 🔍 FASE 2: AUDITORIA DE PIPELINE E AGENTES

### 2.1 Pipeline Completo — Fluxo de Execução

| # | Fase | Agente Responsável | O Que Verificar | Critério de Sucesso |
|---|------|-------------------|-----------------|---------------------|
| 2.1.1 | FASE 1 | Hunter | Keywords pesquisadas, leads encontrados | Leads com nicho+cidade |
| 2.1.2 | FASE 2 | Caio | Qualificação do lead, score | Score > 0, nicho válido |
| 2.1.3 | FASE 2.5 | Design Director | design_context.get_design_context() | Arquétipo + paleta gerados |
| 2.1.4 | FASE 3 | Jina | Inteligência de mercado, market_voice | market_voice preenchido |
| 2.1.5 | FASE 4 | Unsplash/Pexels | Fotos baixadas, formato WebP | Imagens em assets_dir |
| 2.1.6 | FASE 5 | Agente de Nicho | Conteúdo específico do nicho | Texto relevante |
| 2.1.7 | FASE 6 | Agente de Variação | Variações geradas | Múltiplas opções |
| 2.1.8 | FASE 7 | DesignerPRD (Arquiteto) | PRD estruturado, 10 seções | PRD com seções obrigatórias |
| 2.1.9 | FASE 8 | Skill Renderer | HTML gerado via skill | `dist/index.html` existe |
| 2.1.10 | FASE 9 | Quality Gate | Validação de contrato | Gate passou |
| 2.1.11 | FASE 10 | Deploy | Site publicado | URL retornada |
| 2.1.12 | FASE 11 | Franz/SDR | Mensagem WhatsApp enviada | Reply recebido |

### 2.2 Contrato de Cada Agente

#### 2.2.1 DesignerPRD (Arquiteto Mestre)
**Spec:** `backend/agents/rag_knowledge/builder_renderer.md`
```
VERIFICAR:
□ PRD contém 10 seções: hero, prova, contexto, servicos, midia, depoimentos, seo, localizacao, contato, footer
□ Cada seção tem "intent" definido
□ Fatos do negócio são imutáveis (nome, telefone, endereço, cidade)
□ NÃO há "não inventar" para dados ausentes (resolver com texto neutro)
```

#### 2.2.2 Skill Renderer (Builder)
**Spec:** `backend/agents/rag_knowledge/builder_renderer.md`
```
VERIFICAR:
□ Recebe PRD completo (não regras antigas)
□ Gera `dist/index.html` publicável
□ NÃO adiciona regras escondidas de design
□ Segue contrato de construção
```

#### 2.2.3 Design Director
**Spec:** `DESIGN.md` + skill packs
```
VERIFICAR:
□ design_context.get_design_context() retorna:
  - arquétipo visual
  - paleta de cores (primária, secundária, acento)
  - tipografia
  - motion principles
□ Cache funciona (TTL 24h)
□ Usa dados do negócio (não genérico)
```

### 2.3 Skills Carregadas

| # | Skill | Arquivo | Quando Usar | Verificar |
|---|-------|---------|-------------|-----------|
| 2.3.1 | impeccable | `backend/agents/skill_packs/impeccable/SKILL.md` | Análise visual | Está sendo injetado no prompt? |
| 2.3.2 | design-motion | `backend/agents/skill_packs/design-motion-principles/SKILL.md` | Animações | GSAP, ScrollTrigger, Lenis presentes? |
| 2.3.3 | emil-design-eng | `backend/agents/skill_packs/emil-design-eng/SKILL.md` | Motion engineering | data-reveal, data-stagger funcionando? |

---

## 🔍 FASE 3: AUDITORIA DE DESIGN E ENTREGA VISUAL

### 3.1 Design System — 47 Itens Obrigatórios

#### SEO LOCAL (10 itens)
| # | Item | Verificar no HTML Gerado | Critério |
|---|------|---------------------------|----------|
| 3.1.1 | `title_com_cidade` | `<title>.*em.*Cidade.*\|.*</title>` | Presente |
| 3.1.2 | `meta_description_com_cidade` | `<meta name="description" content=".*Cidade.*">` | Presente |
| 3.1.3 | `schema_local_business` | JSON-LD `@type: LocalBusiness` | Válido |
| 3.1.4 | `google_business_profile_link` | Link para g.page ou maps | Presente |
| 3.1.5 | `backlinks_diretorios_locais` | Links para Guia Mais, Apontador | Presente |
| 3.1.6 | `faq_schema` | JSON-LD `@type: FAQPage` | Presente |
| 3.1.7 | `long_tail_keywords` | Keywords no conteúdo | Cidade + serviço |
| 3.1.8 | `alt_text_com_cidade` | `alt=".*em.*Cidade.*"` | Presente |
| 3.1.9 | `nap_consistency` | Nome, Endereço, Telefone | Idênticos |
| 3.1.10 | `google_maps_embed` | iframe maps | Presente |

#### CONVERSÃO (8 itens)
| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 3.2.1 | `prova_social` | Reviews/depoimentos | Visíveis |
| 3.2.2 | `urgencia_escassez` | "Vagas limitadas" etc | Presente |
| 3.2.3 | `lead_magnet` | Oferta gratuita | Presente |
| 3.2.4 | `cta_primario_hero` | CTA no hero | Presente |
| 3.2.5 | `cta_repetido_3x` | CTAs na página | ≥ 3 CTAs |
| 3.2.6 | `whatsapp_flutuante` | Botão WhatsApp fixo | Presente |
| 3.2.7 | `notificacoes_conversao` | "X pessoas viram" | Presente |
| 3.2.8 | `visto_por_x_pessoas` | Contador | Presente |

#### PERFORMANCE (10 itens)
| # | Item | Ferramenta | Critério |
|---|------|-----------|----------|
| 3.3.1 | `imagens_webp` | Verificar extensão | 100% WebP |
| 3.3.2 | `lazy_loading` | `loading="lazy"` | Presente |
| 3.3.3 | `preconnect_fontes` | `<link rel="preconnect">` | Presente |
| 3.3.4 | `css_critico_inline` | No `<head>` | Presente |
| 3.3.5 | `minificacao` | CSS/JS minificados | Tamanho < limiar |
| 3.3.6 | `lcp_menor_2_5s` | Lighthouse | LCP < 2.5s |
| 3.3.7 | `prefetch_paginas` | `<link rel="prefetch">` | Se necessário |
| 3.3.8 | `srcset_responsivo` | srcset nas imagens | Presente |
| 3.3.9 | `aspect_ratio` | aspect-ratio CSS | Presente |
| 3.3.10 | `placeholder_blur` | blur placeholder | Presente |

#### ACESSIBILIDADE (6 itens)
| # | Item | Ferramenta | Critério |
|---|------|-----------|----------|
| 3.4.1 | `contraste_wcag_aa` | axe-devtools | Ratio ≥ 4.5:1 |
| 3.4.2 | `alt_text_todas_imagens` | Verificar alt | 100% imagens |
| 3.4.3 | `navegacao_teclado` | Tab/Enter | Funcional |
| 3.4.4 | `aria_labels` | aria-label | Presente |
| 3.4.5 | `prefers_reduced_motion` | @media query | Presente |
| 3.4.6 | `skip_links` | `<a href="#main">` | Presente |

#### MOBILE (4 itens)
| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 3.5.1 | `mobile_first` | Responsivo | Mobile-first |
| 3.5.2 | `touch_targets_48px` | Botões | ≥ 48x48px |
| 3.5.3 | `menu_hamburger` | Mobile menu | Presente |
| 3.5.4 | `viewport_meta_tag` | `<meta name="viewport">` | Presente |

#### SEGURANÇA (4 itens)
| # | Item | Header | Critério |
|---|------|--------|----------|
| 3.6.1 | `https_ssl` | HTTPS | Ativo |
| 3.6.2 | `content_security_policy` | CSP header | Presente |
| 3.6.3 | `x_frame_options` | X-Frame-Options | SAMEORIGIN |
| 3.6.4 | `x_content_type_options` | X-Content-Type | nosniff |

### 3.2 Motion e Animações

| # | Item | Especificação | Verificar |
|---|------|--------------|-----------|
| 3.7.1 | GSAP | `gsap.min.js` | Presente |
| 3.7.2 | ScrollTrigger | Scroll animations | data-scroll |
| 3.7.3 | Lenis | Smooth scroll | Presente |
| 3.7.4 | data-reveal | Entrance animations | Presente |
| 3.7.5 | data-stagger | Stagger animations | Presente |
| 3.7.6 | data-parallax | Parallax effects | Presente |
| 3.7.7 | prefers-reduced-motion | Desabilitar animações | Funcional |
| 3.7.8 | Duração máxima | 0.8s | Respeitado |

### 3.3 Tipografia

| # | Item | Valor | Verificar |
|---|------|-------|-----------|
| 3.8.1 | Heading Font | Playfair Display/Syne/Cormorant | Carregada |
| 3.8.2 | Body Font | Inter/DM Sans/Plus Jakarta | Carregada |
| 3.8.3 | Accent Font | Montserrat/Space Grotesk | Se usado |
| 3.8.4 | Body size | ≥ 16px | Respeitado |
| 3.8.5 | Line-height | ≥ 1.6 | Respeitado |

---

## 🔍 FASE 4: AUDITORIA DE SEO LOCAL

### 4.1 SEO Local — Regras Obrigatórias

**Spec:** `backend/agents/rag_knowledge/seo_local.md`

| # | Regra | Verificar | Critério |
|---|-------|-----------|----------|
| 4.1.1 | H1 único | 1 H1 por página | ✓ |
| 4.1.2 | H1 = Nome + Serviço + Cidade | `H1` content | Presente |
| 4.1.3 | Mínimo 4 H2 por página | Contar H2s | ≥ 4 |
| 4.1.4 | Cada H2 com cidade quando relevante | H2 content | Presente |
| 4.1.5 | Mínimo 2 H3 por H2 | H3s por H2 | ≥ 2 |
| 4.1.6 | H3 com cidade | H3 content | Presente |

### 4.2 Schema.org Obrigatório

| # | Schema | @type | Verificar |
|---|--------|-------|-----------|
| 4.2.1 | LocalBusiness | `@type: LocalBusiness` | Válido |
| 4.2.2 | PostalAddress | addressLocality | Cidade correta |
| 4.2.3 | GeoCoordinates | geo | Se disponível |
| 4.2.4 | AggregateRating | ratingValue, reviewCount | Presente |
| 4.2.5 | OpeningHours | openingHours | Formato correto |
| 4.2.6 | FAQPage | mainEntity | ≥ 3 FAQs |

### 4.3 Keywords e Volume de Pesquisa

| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 4.3.1 | Keywords com cidade | Termos incluem cidade | ✓ |
| 4.3.2 | Keywords de cauda longa | 3-5 palavras | ✓ |
| 4.3.3 | Intent de busca | local/comercial | ✓ |
| 4.3.4 | Volume de pesquisa | Keywords com volume | Documentado? |

---

## 🔍 FASE 5: AUDITORIA DE PERFORMANCE E ESCALABILIDADE

### 5.1 Tempo de Geração

| # | Métrica | Meta Original | Meta Atual | Verificar |
|---|---------|--------------|------------|-----------|----------|
| 5.1.1 | Tempo total pipeline | 27 min | < 8 min | Cronometrar |
| 5.1.2 | Tokens consumidos | Alto | = AI Studio/Lovable | Comparar |
| 5.1.3 | Cache de node_modules | - | `/var/cache/fralib/node_modules_vite.tar.gz` | Existe |
| 5.1.4 | Cache design director | TTL 24h | `/tmp/fralib_design_cache` | Funciona |

### 5.2 Concorrência

| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 5.2.1 | Workers simultâneos | `pm2 list` + processos ativos | ≥ 2 workers |
| 5.2.2 | Lock por job | `SELECT FOR UPDATE SKIP LOCKED` | Não há duplicação |
| 5.2.3 | Jobs em fila | `pipeline_queue` | Jobs processando |
| 5.2.4 | Concorrência de deploy | Testar 2 jobs simultâneos | Ambos succeed |

### 5.3 Resource Usage

| # | Recurso | Como Medir | Limiar |
|---|---------|-----------|--------|
| 5.3.1 | CPU | `top` ou `htop` | < 80% |
| 5.3.2 | Memória | `free -m` | < 80% |
| 5.3.3 | Disco | `df -h` | < 85% |
| 5.3.4 | Database connections | Query `pg_stat_activity` | < max_connections |

---

## 🔍 FASE 6: AUDITORIA DE SEGURANÇA

### 6.1 Autenticação e Autorização

| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 6.1.1 | JWT tokens | Assinatura, expiração | Válido |
| 6.1.2 | RBAC | Papéis corretos | Sem escalação |
| 6.1.3 | Tenant isolation | Query entre tenants | Bloqueado |
| 6.1.4 | IDOR protection | Acesso a recursos | Apenas dono |

### 6.2 Proteção de Dados

| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 6.2.1 | LGPD consent | `fralib_lgpd_consent_v1` | Presente |
| 6.2.2 | Dados sensíveis | Telefone, email | Criptografados |
| 6.2.3 | Logs | Sem dados sensíveis | Máscarados |

### 6.3 API Security

| # | Item | Verificar | Critério |
|---|------|-----------|----------|
| 6.3.1 | Rate limiting | `@limiter.limit` | Ativo |
| 6.3.2 | CORS | Origens permitidas | Documentado |
| 6.3.3 | Input validation | Pydantic schemas | Válido |
| 6.3.4 | SQL injection | ORM, não SQL string | Protegido |

### 6.4 OWASP Top 10

| # | Vulnerabilidade | Verificar | Status |
|---|-----------------|-----------|--------|
| 6.4.1 | A01 Broken Access | Test IDOR | - |
| 6.4.2 | A02 Cryptographic Failures | Keys expostas | - |
| 6.4.3 | A03 Injection | Input validation | - |
| 6.4.4 | A04 Insecure Design | Business logic | - |
| 6.4.5 | A05 Security Misconfiguration | Headers, CORS | - |
| 6.4.6 | A06 Vulnerable Components | Dependencies | - |
| 6.4.7 | A07 Auth Failures | JWT, sessions | - |
| 6.4.8 | A08 Data Integrity | Backup, integridade | - |

---

## 🔍 FASE 7: AUDITORIA DE CONTRATOS E SPECS

### 7.1 Arquitetura — God Objects

**Auditoria prévia:** `auditorias/2025-06-20/01_FINDINGS/COMP_001_god_objects.md`

| # | Arquivo | Linhas | Meta | Status |
|---|---------|-------|------|--------|
| 7.1.1 | `pipeline_orchestrator_service.py` | 3142 | < 500 | ⚠️ CRÍTICO |
| 7.1.2 | `vite_react_renderer.py` | 3813 | < 500 | ⚠️ CRÍTICO |
| 7.1.3 | `leads_crud.py` | 633 | < 500 | ⚠️ ALTO |
| 7.1.4 | `superadmin_endpoints.py` | 805 | < 500 | ⚠️ ALTO |
| 7.1.5 | `worker.py` | 845 | < 500 | ⚠️ ALTO |

### 7.2 Padrões de Código

| # | Padrão | Avaliação | Verificar |
|---|--------|-----------|-----------|
| 7.2.1 | Agent Routing/Strategy | BOM | Implementado |
| 7.2.2 | Circuit Breaker | EXCELENTE | Completo |
| 7.2.3 | Cache Service | BOM | Redis + fallback |
| 7.2.4 | Retry Pattern | BOM | Backoff + jitter |
| 7.2.5 | Thread-Local → ContextVar | CORRIGIDO | Async-safe |

### 7.3 Testes

| # | Área | Cobertura Atual | Meta | Status |
|---|------|----------------|------|--------|
| 7.3.1 | Unit tests | 14% | > 80% | ⚠️ CRÍTICO |
| 7.3.2 | Integration tests | - | Críticos | - |
| 7.3.3 | E2E tests | - | Happy path | - |

### 7.4 Specs Atualizados

| # | Documento | Última Atualização | Verificar Consistência |
|---|-----------|-------------------|----------------------|
| 7.4.1 | AGENTS.md | ? | = CLAUDE.md = README.md |
| 7.4.2 | CLAUDE.md | ? | Pipeline atual |
| 7.4.3 | DESIGN.md | 2026-05-31 | Design System |
| 7.4.4 | PRODUCT.md | ? | Propósito do produto |

---

## 📊 MATRIZ DE RESPONSABILIDADES

| Dimensão | Auditor | Tempo Estimado | Prioridade |
|----------|---------|----------------|------------|
| Infraestrutura | DevOps | 2h | ALTA |
| Pipeline/Agentes | Backend | 4h | CRÍTICA |
| Design/Visual | Frontend | 3h | CRÍTICA |
| SEO Local | Marketing | 2h | ALTA |
| Performance | DevOps | 2h | ALTA |
| Segurança | Security | 3h | CRÍTICA |
| Contratos/Specs | Tech Lead | 2h | MÉDIA |

---

## 📝 CRITÉRIOS DE SUCESSO

### ✅ Auditoria Aprovada se:
1. **Paridade Local↔VPS**: 100% de correspondência
2. **Pipeline**: 100% das fases executando corretamente
3. **Design System**: ≥ 90% dos 47 itens presentes
4. **SEO Local**: 100% das regras de keywords obedecidas
5. **Performance**: Pipeline < 8 min, LCP < 2.5s
6. **Segurança**: 0 vulnerabilidades críticas
7. **Contratos**: Specs consistentes entre si

### ❌ Auditoria Reprovada se:
1. Commits locais ≠ VPS
2. Qualquer fase do pipeline falhando silenciosamente
3. Design System < 80% de conformidade
4. SEO não seguindo regras de cidade
5. Pipeline > 15 min (muito acima da meta)
6. Qualquer vulnerabilidade crítica aberta

---

## 🚀 PRÓXIMOS PASSOS

1. [ ] Criar tasks para cada fase
2. [ ] Executar auditoria fase por fase
3. [ ] Documentar findings em `auditorias/2026-06-20/`
4. [ ] Criar plano de correção
5. [ ] Implementar correções
6. [ ] Re-auditar após correções

---

**Documento base para auditoria FraLib**
*Versão 1.0 — 2026-06-20*
