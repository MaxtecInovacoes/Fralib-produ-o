# Conhecimento RAG - Designer PRD (Product Requirements Document)

## Missao
Criar PRDs detalhados que garantam sites premium, nao genericos.
O PRD e o blueprint do site - define tudo que o Liam vai construir.

## Guardrails Obrigatorios

- NUNCA incluir precos, valores, mensalidades ou tabelas de preco no PRD
- Usar sempre CTAs: Consulte valores, Solicite orcamento, Fale conosco
- NUNCA usar paleta generica (azul #3b82f6) - usar SEMPRE paleta do Alex
- NUNCA recomendar animacoes genericas - especificar por segmento
- SEMPRE incluir Schema.org LocalBusiness completo
- SEMPRE incluir banner LGPD (cookies) como secao obrigatoria

## Estrutura de Secoes Obrigatoria

1. Hero (H1 unico: Nome + Segmento + Cidade)
2. Sobre (H2: historia, diferenciais, missao)
3. Servicos (H2: lista com H3 para cada servico - SEM PRECOS)
4. Depoimentos (H2: reviews reais do Google Maps)
5. Galeria (H2: fotos reais do negocio)
6. Localizacao (H2: mapa + endereco + horarios)
7. Contato (H2: WhatsApp CTA principal)
8. Footer (links, LGPD, copyright)

## Animacoes por Tipo de Negocio

### Dark Mode Premium (Academia, Barbearia, Bar)
- parallax-3d-hero: hero com profundidade 3D
- card-flip-3d: cards com flip no hover
- magnetic-cta: botoes com efeito magnetico
- counter-animated: numeros animados (anos, clientes, avaliacoes)
- stagger-reveal: entrada em cascata das secoes
- scroll-progress: barra de progresso no topo
- image-zoom-parallax: fotos com zoom + parallax
- text-split-reveal: titulos com letras animadas

### Light Mode Saude (Clinica, Farmacia, Estetica)
- fade-in-elegant: entrada suave e profissional
- card-elevation: elevacao sutil no hover
- stagger-reveal: entrada em cascata
- scroll-progress: barra de progresso
- image-reveal: fotos com reveal suave
- cta-pulse: CTA com pulse discreto

## Tipografia por Segmento

### Premium/Dark
- Heading: Montserrat Bold ou Bebas Neue
- Body: Inter ou DM Sans
- Accent: Playfair Display (para detalhes)

### Saude/Light
- Heading: Nunito ou Poppins
- Body: Open Sans ou Lato
- Accent: Merriweather (para citacoes)

### Alimentacao
- Heading: Playfair Display ou Lora
- Body: Source Sans Pro
- Accent: Dancing Script (para detalhes especiais)

## SEO Local Obrigatorio

### Schema.org
- @type: LocalBusiness (ou subtipo especifico: MedicalBusiness, FoodEstablishment, etc.)
- name: nome exato do negocio
- address: PostalAddress com addressLocality
- telephone: numero formatado
- aggregateRating: ratingValue + reviewCount
- openingHours: horarios de funcionamento

### Meta Tags
- title: Nome - Segmento em Cidade
- description: 150-160 chars com cidade e segmento
- og:title, og:description, og:image
- canonical URL

## LGPD Obrigatorio

Incluir no PRD como secao obrigatoria:
- Banner de cookies (aceitar/rejeitar)
- Link para politica de privacidade no footer
- Link para termos de uso no footer


---

## MAPA SEO LOCAL OBRIGATÓRIO

Todo site gerado DEVE seguir esta estrutura:

### H1 (ÚNICO por página)
- SEMPRE: Nome do Negócio + Serviço Principal + Cidade
- CORRETO: "Exclusiva Fitness - Academia Feminina em Campina Grande do Sul"
- ERRADO: "Seu corpo. Sua força." (copy criativo vai no subtítulo H2/parágrafo)

### Hierarquia H2/H3 obrigatória
- H2: Principais Serviços → H3: Serviço 1 + Cidade, Serviço 2 + Cidade, Serviço 3 + Cidade
- H2: Diferenciais e Benefícios → H3: Garantia de Qualidade, Equipe Especializada, Resultados Comprovados
- H2: Prova Social → H3: Depoimentos de clientes, Avaliações reais, Casos de sucesso
- H2: CTA Local → H3: Ligue agora, WhatsApp, Como chegar

### meta_title
Serviço Principal em Localidade | Nome da Empresa

### meta_description (150-160 chars)
Encontre o melhor [Serviço] em [Cidade] com [diferencial]. Ligue ou WhatsApp agora!

### Elementos globais obrigatórios em TODAS as seções
- Botão WhatsApp (wa.me) visível above-the-fold no mobile
- Botão ligar (tel:) clicável
- NAP: Nome, Endereço, Telefone consistentes
- Avaliações/Prova social visível sem scroll
- Horário de funcionamento

### Schema.org JSON-LD obrigatório
LocalBusiness + Organization + Review + FAQ

### FAQ (mínimo 3 perguntas do nicho)
Aumenta visibilidade em buscas por IA (ChatGPT, Gemini, Perplexity)

### Critérios de IA
- Mencionar cidade em múltiplos pontos do conteúdo
- NAP consistente e visível
- Responder perguntas que o usuário faria ao Google/ChatGPT
- Textos claros, linguagem natural, bem segmentados

