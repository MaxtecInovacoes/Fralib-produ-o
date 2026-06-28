# Auditoria de Variacao Cinematica - 2026-06-28

## Escopo auditado

Fluxo completo:

1. `backend/agents/caio.py`
2. `backend/agents/agente_nicho.py`
3. `backend/agents/agente_variacao.py`
4. `backend/agents/arquiteto_mestre.py`
5. `backend/agents/designer_prd.py`
6. `backend/services/pipeline_builders.py`
7. `backend/services/builder_worker.py`
8. `backend/services/vite_prompts.py`
9. `backend/services/vite_react_renderer.py`
10. publicacao e handoff para SDR

## Diagnostico

### O que NAO era a causa principal

- `agente_nicho.py` ja extrai `paleta_cores` do briefing livre.
- `arquiteto_mestre.py` ja prioriza `paleta_cores` do briefing acima de `design_dna`.
- `builder_worker.py` ja empurra o caminho canonico Vite/React copy-only com studio cinematografico.

Conclusao: o problema principal nao era "cor do briefing perdida".

### Causa raiz real

O sistema carregava dados suficientes, mas a variabilidade visual era comprimida em duas camadas:

1. `variation_seed.py`
   - variava so `hero_layout`, `motion_style`, `copy_voice`, `color_emphasis`
   - isso gerava poucas combinacoes profundas

2. `vite_react_renderer.py`
   - o studio cinematografico principal ainda montava a pagina com poucas secoes fixas
   - `section_order` e variacoes estruturais chegavam na pipeline, mas eram pouco consumidos
   - o repertorio publicado era menor do que o repertorio disponivel no pipeline

### Gargalos encontrados

- `agente_variacao.py`: espaco de templates pequeno
- `archetype_resolver.py`: ordem base existia, mas sem rotacao narrativa suficiente
- `vite_react_renderer.py`: pouco uso de `about`, `reviews`, `location`
- `_generate_cinematic_secondary_components()`: repertorio cinematografico incompleto
- `designer_prd.py`: defaults existem, mas nao explicam a repeticao observada

## Correcoes executadas nesta sprint

### 1. Vetor de variacao ampliado

Arquivo: `backend/services/variation_seed.py`

Novas dimensoes:

- `section_order_style`
- `proof_style`
- `surface_style`

Efeito:

- mais variacao sem aumentar chamadas LLM
- combinatoria estrutural maior por lead e por subnicho

### 2. Ordem narrativa rotacionada de forma deterministica

Arquivo: `backend/services/archetype_resolver.py`

Adicionado:

- `_rotate_section_order(...)`

Agora a ordem da pagina varia por estilo narrativo:

- `credibility_first`
- `visual_first`
- `offer_first`
- `story_first`

Mantendo fixos:

- `navbar`
- `hero`
- `footer`

### 3. Payload de variacao propagado de ponta a ponta

Arquivo: `backend/services/pipeline_builders.py`

Novos campos enviados ao renderer:

- `color_emphasis`
- `section_order_style`
- `proof_style`
- `surface_style`
- `section_order`

### 4. Studio cinematografico passou a consumir a ordem real de secoes

Arquivo: `backend/services/vite_react_renderer.py`

Adicionado:

- normalizacao de aliases de secao
- resolucao da ordem cinematografica final
- imports e markup dinamicos em `Index.tsx`
- navegacao dinamica no `Navbar`

Resultado:

- a composicao publicada deixa de ser fixa
- a ordem da pagina agora responde a variacao upstream

### 5. Repertorio de secoes cinematograficas ampliado

Arquivo: `backend/services/vite_react_renderer.py`

`_generate_cinematic_secondary_components()` agora inclui e usa:

- `AboutSection`
- `ReviewsSection`
- `LocationSection`

Essas secoes foram integradas com:

- paleta via CSS vars
- prova social variavel
- CTA/local SEO com estrutura coerente

## Biblioteca externa auditada e decisao final

Bibliotecas auditadas:

- `motion-primitives`
- `aceternity-ui`
- primitives estilo `shadcn`

Decisao final desta sprint:

- nao publicar nenhuma dessas bibliotecas como dependencia obrigatoria do site gerado
- usar essas libs como referencia de repertorio
- internalizar apenas primitives minimos no proprio builder quando o ganho visual justificar

Motivo:

- reduz custo de manutencao no runtime da pipeline
- evita quebra por resolucao de tipos e dependencias opcionais no build Vite
- preserva o objetivo principal: variar mais com menos LLM e com build deterministico

Aplicacao concreta nesta entrega:

- `Avatar`, `Separator` e `Accordion` foram integrados como componentes locais gerados pelo builder
- o renderer nao depende desses pacotes externos para compilar
- a variacao cinematografica aumentou sem introduzir mais um caminho fragil na publicacao

## O que ainda falta

1. ampliar o catalogo estrutural por secao
   - hero
   - services
   - proof
   - faq
   - cta

2. separar a biblioteca cinematografica do renderer monolitico
   - registry de blocos
   - contrato de props
   - escolha deterministica por variacao

3. validar por lote
   - 5 sites do mesmo subnicho
   - 5 sites de subnichos diferentes
   - comparacao de ordem, paleta, prova, superficies e composicao

## Verdade operacional

Depois desta mudanca, a repeticao residual deixa de estar concentrada em cor e passa a estar concentrada em repertorio de blocos.

Ou seja:

- o pipeline ja decide melhor
- agora o renderer publica melhor
- o proximo salto depende de um registry maior de secoes cinematograficas, nao de mais LLM
