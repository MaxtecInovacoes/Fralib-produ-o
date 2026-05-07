# SEO Local e Componentes — Liam RAG

## Comentarios de Secao Obrigatorios

Cada secao DEVE ter comentarios para permitir edicao cirurgica:
  <!-- SECTION:hero --> ... <!-- /SECTION:hero -->
  <!-- SECTION:sobre --> ... <!-- /SECTION:sobre -->
  <!-- SECTION:servicos --> ... <!-- /SECTION:servicos -->
  <!-- SECTION:depoimentos --> ... <!-- /SECTION:depoimentos -->
  <!-- SECTION:galeria --> ... <!-- /SECTION:galeria -->
  <!-- SECTION:localizacao --> ... <!-- /SECTION:localizacao -->
  <!-- SECTION:contato --> ... <!-- /SECTION:contato -->
  <!-- SECTION:footer --> ... <!-- /SECTION:footer -->
  <!-- SECTION:lgpd --> ... <!-- /SECTION:lgpd -->

## SEO Local Obrigatorio

- H1 unico: Nome - Segmento em Cidade
- Schema.org LocalBusiness com name, address, telephone, aggregateRating
- meta description: 150-160 chars com cidade e segmento
- og:title, og:description, og:image
- canonical URL

## LGPD Obrigatorio

Banner de cookies com dois botoes: Aceitar e Rejeitar.
Salvar preferencia em localStorage.
Link para politica de privacidade no footer.
Banner deve aparecer apenas se usuario ainda nao escolheu.

## Fotos e Assets

- Usar caminhos absolutos: /sites/{slug}/assets/foto_1.webp
- NUNCA usar URLs externas se assets_dir estiver disponivel
- Adicionar loading=lazy em todas as imagens
- Usar aspect-ratio para containers de imagem

## Tamanho Minimo

- HTML deve ter NO MINIMO 40.000 caracteres (40KB)
- Cada secao com conteudo rico e detalhado
- Copy nichada e especifica para o segmento e cidade
- Usar dados reais do lead (nome, cidade, rating, reviews, telefone)


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


---

