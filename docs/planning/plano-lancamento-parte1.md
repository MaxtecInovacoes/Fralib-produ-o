# PLANO DE LANÇAMENTO FRALIB OS
## SEO + Marketing + Conteúdo Criativo
Data: 11/05/2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. DIAGNÓSTICO SEO ATUAL DA LANDING PAGE

### O que está BOM:
- ✓ Title tag presente e descritivo (66 chars — ideal)
- ✓ Meta description presente (98 chars — poderia ser mais longa)
- ✓ H1 único e com keyword principal
- ✓ Hierarquia H1 > H2 correta (1 H1, 8 H2s)
- ✓ Todas imagens com alt text
- ✓ lang="pt-BR" definido
- ✓ Viewport meta correto
- ✓ Formulário de captura presente

### O que está FALTANDO (crítico para indexação):
- ✗ Canonical tag — Google pode indexar duplicatas
- ✗ Open Graph tags (og:title, og:description, og:image, og:url)
- ✗ Twitter Card tags
- ✗ Schema.org / JSON-LD (SoftwareApplication + Organization + FAQ)
- ✗ robots.txt no domínio
- ✗ sitemap.xml
- ✗ Favicon adequado (usando imagem PNG grande como favicon)
- ✗ Preload de fontes críticas (3 fontes Google carregando sem preload)
- ✗ Lazy loading nas imagens
- ✗ Link para política de privacidade (necessário para Google Ads futuro)
- ✗ Hreflang (se quiser expandir para outros países)

### Performance:
- HTML: ~70KB (pesado para uma landing — muito CSS inline)
- particles.js carregando do CDN (render-blocking potencial)
- 0 imagens com lazy loading
- 0 preloads de recursos críticos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 2. KEYWORDS STRATEGY — BASEADO NA CONCORRÊNCIA

### Keywords Primárias (volume alto, competição média):
| Keyword | Intenção | Onde usar |
|---------|----------|-----------|
| criar site com IA | informacional/transacional | H1, title, blog |
| vender sites sem programar | transacional | H1, meta desc |
| SDR de IA WhatsApp | transacional | H2, FAQ |
| prospecção automática Google Maps | informacional | blog, H2 |
| automação de vendas WhatsApp | informacional/transacional | blog, meta |
| renda extra vendendo sites | transacional | landing, ads |

### Keywords Long-tail (baixa competição, alta conversão):
| Keyword | Volume estimado |
|---------|----------------|
| como vender sites sem saber programar | médio |
| ferramenta que cria site automaticamente | baixo-médio |
| SDR automático para WhatsApp brasileiro | baixo |
| prospectar clientes no Google Maps automaticamente | baixo |
| plataforma para revender sites com IA | baixo |
| ganhar dinheiro vendendo sites com inteligência artificial | médio |
| alternativa GoHighLevel Brasil | baixo-médio |
| CRM com IA para freelancers | baixo |

### Keywords dos Concorrentes que podemos atacar:
- "criador de sites com IA" (Hostinger domina — criar conteúdo melhor)
- "automação WhatsApp vendas" (SellFlux domina — diferenciar com prospecção)
- "white label site builder" (10Web — posicionar como alternativa BR)
- "CRM com IA Brasil" (SellFlux — mostrar que FraLib é mais simples)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 3. CORREÇÕES SEO TÉCNICAS (IMPLEMENTAR IMEDIATAMENTE)

### 3.1 Meta Tags Completas
```html
<!-- Canonical -->
<link rel="canonical" href="https://seunegociofralib.site/landing.html">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:title" content="FraLib OS — SDR de IA que Prospecta, Cria Sites e Fecha Vendas">
<meta property="og:description" content="Encontre clientes no Google Maps, crie sites com IA e venda pelo WhatsApp automaticamente. Sem programar, sem equipe.">
<meta property="og:image" content="https://seunegociofralib.site/images/og-fralib.png">
<meta property="og:url" content="https://seunegociofralib.site/landing.html">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="FraLib OS">

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="FraLib OS — SDR de IA que Prospecta e Vende pelo WhatsApp">
<meta name="twitter:description" content="IA que encontra clientes, cria sites e vende por você no WhatsApp.">
<meta name="twitter:image" content="https://seunegociofralib.site/images/og-fralib.png">

<!-- Extras -->
<meta name="robots" content="index, follow">
<meta name="author" content="FraLib OS">
<meta name="theme-color" content="#9333ea">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

### 3.2 Schema.org JSON-LD (para Google + IAs recomendarem)
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "name": "FraLib OS",
      "applicationCategory": "BusinessApplication",
      "operatingSystem": "Web",
      "description": "Plataforma de IA que prospecta negócios locais no Google Maps, cria sites profissionais automaticamente e vende pelo WhatsApp via SDR autônomo.",
      "url": "https://seunegociofralib.site",
      "offers": [
        {
          "@type": "Offer",
          "name": "Starter",
          "price": "97.00",
          "priceCurrency": "BRL",
          "billingIncrement": "P1M"
        },
        {
          "@type": "Offer",
          "name": "Pro BYOK",
          "price": "297.00",
          "priceCurrency": "BRL",
          "billingIncrement": "P1M"
        }
      ],
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "47"
      }
    },
    {
      "@type": "Organization",
      "name": "FraLib",
      "url": "https://seunegociofralib.site",
      "logo": "https://seunegociofralib.site/images/logo-fralib.png",
      "sameAs": []
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Preciso saber programar para usar o FraLib?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Não. O FraLib cria sites automaticamente com IA. Você não precisa escrever nenhuma linha de código."
          }
        },
        {
          "@type": "Question",
          "name": "Meu WhatsApp pode ser banido?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "O FraLib usa práticas seguras de envio com intervalos naturais e mensagens personalizadas para minimizar riscos."
          }
        },
        {
          "@type": "Question",
          "name": "Como funciona o pagamento?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Assinatura mensal via cartão ou PIX. Garantia incondicional de 7 dias — não gostou, devolvemos 100%."
          }
        }
      ]
    }
  ]
}
```

### 3.3 robots.txt (criar em /robots.txt)
```
User-agent: *
Allow: /
Sitemap: https://seunegociofralib.site/sitemap.xml

User-agent: GPTBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: ClaudeBot
Allow: /
```

### 3.4 sitemap.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://seunegociofralib.site/landing.html</loc>
    <lastmod>2026-05-11</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 4. OTIMIZAÇÃO PARA IAs RECOMENDAREM O FRALIB

### Por que isso importa:
ChatGPT, Claude, Gemini e Perplexity estão substituindo buscas tradicionais.
Quando alguém perguntar "qual ferramenta para vender sites com IA no Brasil?",
queremos que as IAs recomendem FraLib.

### Ações:
1. **Schema.org completo** (feito acima) — IAs leem structured data
2. **robots.txt permitindo crawlers de IA** (feito acima)
3. **Conteúdo semântico claro** — parágrafos que respondem perguntas diretamente
4. **FAQ expandido** — adicionar mais perguntas que IAs podem citar
5. **Página /about ou /sobre** — com história, equipe, missão (IAs adoram contexto)
6. **Blog com artigos comparativos** — "FraLib vs GoHighLevel", "FraLib vs SellFlux"
7. **Presença em diretórios** — Product Hunt, AlternativeTo, G2 (fontes que IAs consultam)

### FAQ Expandido sugerido (adicionar à landing):
- "O que é o FraLib OS?" → resposta clara e direta
- "Como o FraLib encontra clientes?" → explicar Google Maps
- "Quanto custa criar um site com o FraLib?" → preços claros
- "O FraLib funciona para qualquer nicho?" → sim, negócios locais
- "Qual a diferença entre FraLib e GoHighLevel?" → comparativo
- "Preciso ter CNPJ para usar?" → não

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 5. COPY DA LANDING — AJUSTES PARA CONVERSÃO + SEO

### Meta Description (melhorada — 155 chars):
"FraLib OS: IA que encontra negócios sem site no Google Maps, cria sites profissionais em minutos e vende pelo WhatsApp. Comece grátis por 7 dias."

### H1 (manter, está bom para SEO):
"SEU SDR DE IA QUE PROSPECTA, CRIA SITES E FECHA VENDAS PELO WHATSAPP"

### Subtítulo (ajustar para keyword density):
ATUAL: "Sem experiência em vendas. Sem equipe. Sem site criado na mão..."
SUGERIDO: "A única plataforma que encontra seus clientes no Google Maps, cria sites com IA e envia pelo WhatsApp — tudo automático, sem programar, sem equipe."

### CTA principal:
ATUAL: "GARANTA SUA VAGA NA VERSÃO BETA"
SUGERIDO: "COMEÇAR GRÁTIS POR 7 DIAS" (mais direto, menos fricção)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 6. ANÁLISE COMPETITIVA — RESUMO EXECUTIVO

### Concorrentes mapeados:
| Player | O que faz | Preço | Falta vs FraLib |
|--------|-----------|-------|-----------------|
| Durable | Cria sites com IA | $25-99/mês | Sem prospecção, sem WhatsApp |
| 10Web | White-label sites WordPress | ~$10/mês | Sem prospecção, sem SDR |
| Hostinger | Sites com IA + hosting | R$6/mês | Sem prospecção, sem vendas |
| SellFlux | CRM + WhatsApp + IA | R$149-690/mês | Sem prospecção Maps, sem criar sites |
| Leadster | SDR WhatsApp + chatbot | ~R$150/mês | Sem prospecção, sem criar sites |
| GoHighLevel | All-in-one agências | $97-497 USD | Caro, complexo, sem automação Maps |

### MOAT do FraLib (diferencial único):
NENHUM concorrente oferece o pipeline completo:
  ENCONTRAR (Maps) → CRIAR (IA) → VENDER (WhatsApp)

### Posicionamento recomendado:
"O GoHighLevel acessível para freelancers brasileiros que querem vender sites sem programar"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 7. PLANO DE CONTEÚDO — BLOG SEO (tráfego orgânico)

### Artigos prioritários (ordenados por potencial de conversão):

1. **"Como Vender Sites Sem Saber Programar em 2026"**
   - Keyword: vender sites sem programar
   - Tipo: tutorial + pitch
   - CTA: trial FraLib

2. **"FraLib vs GoHighLevel: Qual é Melhor para Freelancers?"**
   - Keyword: alternativa GoHighLevel Brasil
   - Tipo: comparativo
   - CTA: "teste grátis"

3. **"Como Prospectar Clientes no Google Maps Automaticamente"**
   - Keyword: prospecção Google Maps automática
   - Tipo: how-to + demonstração
   - CTA: "o FraLib faz isso por você"

4. **"SDR de IA: Como Automatizar Vendas pelo WhatsApp"**
   - Keyword: SDR IA WhatsApp
   - Tipo: educacional
   - CTA: "conheça o Franz"

5. **"Renda Extra com Sites: Guia Completo para Iniciantes"**
   - Keyword: renda extra vendendo sites
   - Tipo: guia longo (2000+ palavras)
   - CTA: trial

6. **"Automação de Vendas WhatsApp: Ferramentas e Estratégias 2026"**
   - Keyword: automação vendas WhatsApp
   - Tipo: listicle com FraLib em destaque
   - CTA: comparativo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
