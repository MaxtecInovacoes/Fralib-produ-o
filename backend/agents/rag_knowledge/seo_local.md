# SEO Local — Mapa Obrigatório

Todo site gerado DEVE seguir esta estrutura de SEO local.

## HOME (página principal)

**H1:** Serviço Principal + Localidade
Ex: Academia Feminina em Campina Grande do Sul

**meta_title:** Serviço Principal em Localidade | Nome da Empresa
Ex: Academia Feminina em Campina Grande do Sul | Exclusiva Fitness

**meta_description:** 150-160 chars com serviço + localidade + CTA
Ex: Encontre a melhor academia feminina em Campina Grande do Sul com equipamentos modernos, equipe qualificada e ambiente exclusivo. Ligue ou WhatsApp agora!

**Hierarquia H2/H3:**
- H2: Principais Serviços → H3: Serviço 1 + Localidade, Serviço 2 + Localidade, Serviço 3 + Localidade
- H2: Diferenciais e Benefícios → H3: Garantia de Qualidade, Equipe Especializada, Projetos Comprovados
- H2: Prova Social → H3: Depoimentos de clientes, Avaliações reais, Casos de sucesso
- H2: CTA Local → H3: Ligue agora, WhatsApp, Como chegar

**Schema.org:** LocalBusiness, Organization, Review, FAQ

## SEÇÃO SERVIÇOS

**H1:** Serviço + Localidade
**H2/H3:**
- Tipos/Variações → Opção A, Opção B, Opção C
- Benefícios/Diferenciais → Qualidade garantida, Entrega rápida, Equipe experiente
- FAQ Local → Quanto custa? Qual o prazo? Como funciona?
- CTA Local → Solicite orçamento, WhatsApp, Ligue agora

**Schema.org:** Service, LocalBusiness, Review, FAQ

## SEÇÃO SOBRE

**H1:** Quem Somos em Localidade
**H2:** História e experiência, Missão e valores, Equipe e certificações, Projetos/Cases, Depoimentos
**Schema.org:** Organization, LocalBusiness, Review

## SEÇÃO CONTATO

**H1:** Contato em Localidade
**H2:** Endereço completo + Mapa, Telefone/WhatsApp, Horário de atendimento, Formulário de contato
**Schema.org:** LocalBusiness, ContactPoint

## Elementos Globais Obrigatórios (em TODAS as seções)

- Botão ligar (tel:)
- Botão WhatsApp (wa.me)
- NAP visível: Nome, Endereço, Telefone consistentes
- Avaliações/Prova social
- Horário de funcionamento
- Menu principal otimizado

## SEO Técnico Obrigatório

- Mobile-first / Responsivo
- HTTPS (já garantido pelo servidor)
- Canonical URL
- URLs amigáveis (/servico-localidade/)
- Dados estruturados: LocalBusiness, Service, Review, FAQ
- Imagens otimizadas: ALT descritivo, loading=lazy, WebP
- Core Web Vitals: Google Fonts com display=swap, GSAP com defer, lazy load

## Critérios de IA (para ranquear em buscas por IA)

- Conteúdo local relevante e específico (mencionar cidade em múltiplos pontos)
- NAP consistente e visível em todas as seções
- Schema estruturado em todas as páginas
- Prova social visível (reviews reais do Google Maps)
- Hierarquia clara H1/H2/H3
- Textos claros, bem segmentados e linguagem natural
- Responder perguntas que o usuário faria ao Google/ChatGPT

## Regras de H1

- APENAS 1 H1 por página
- SEMPRE: Nome do Negócio + Serviço Principal + Cidade
- Ex correto: "Exclusiva Fitness - Academia Feminina em Campina Grande do Sul"
- Ex ERRADO: "Seu corpo. Sua força. Seu espaço." (copy criativo vai no subtítulo H2 ou parágrafo)

## Regras de H2

- MÍNIMO 4 H2 por página (Serviços, Diferenciais, Prova Social, CTA)
- Cada H2 deve conter a localidade quando relevante
- Ex: "Musculação e Cardio em Campina Grande do Sul"

## Regras de H3

- MÍNIMO 2 H3 por H2
- H3 de serviços SEMPRE com localidade
- Ex: "Musculação Feminina em Campina Grande do Sul"

## Schema.org JSON-LD Obrigatório

`json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Nome do Negócio",
  "description": "Descrição com serviço + cidade",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Endereço completo",
    "addressLocality": "Cidade",
    "addressRegion": "Estado",
    "addressCountry": "BR"
  },
  "telephone": "+55XXXXXXXXXXX",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "120"
  },
  "openingHours": "Mo-Fr 06:00-22:00",
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "-25.xxx",
    "longitude": "-49.xxx"
  }
}
`

## FAQ Schema (aumenta visibilidade em buscas)

Incluir pelo menos 3 perguntas frequentes do nicho:
- "Qual o horário de funcionamento?"
- "Como agendar uma aula experimental?"
- "Quais modalidades estão disponíveis?"
