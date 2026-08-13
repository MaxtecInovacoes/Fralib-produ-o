# Pipeline de Pesquisa, Mídia e Diversidade Visual

## Objetivo

Garantir que cada site FraLib seja orientado ao público real do lead, use pesquisa local e imagens contextuais, cumpra contratos de conteúdo e metadata e seja visualmente distinto dos sites já publicados, inclusive dentro do mesmo nicho e subnicho. O QA Vision permanece temporariamente em pass-through.

## Escopo

- Corrigir a integração da pesquisa no FSM oficial em `backend/agents/manager/`.
- Usar Jina Search/Reader como fonte primária.
- Usar Playwright como fallback quando a Jina responder com limite, indisponibilidade, timeout ou conteúdo insuficiente.
- Buscar imagens antes do Arquiteto e transportar as URLs até o OpenUI.
- Usar `backend/agents/DESIGN-SYSTEM.md`, Design Context, Design Reference Packs e Visual DNA como curadoria visual.
- Tornar obrigatórios os contratos de estrutura, SEO, GEO, OG, favicon, JSON-LD, FAQ, footer e LGPD antes do Builder.
- Impedir emojis e conteúdo factual inventado por validação determinística anterior ao deploy.
- Comparar a identidade proposta com o histórico publicado e selecionar nova combinação quando houver colisão.

## Fora do Escopo

- Reativar ou modificar o QA Vision v2.
- Alterar o comportamento pass-through atual de `step_quality_gate.py`.
- Criar um segundo pipeline ou substituir o FSM oficial.
- Inventar avaliações, preços, métricas, horários ou diferenciais não confirmados.

## Fluxo

1. Hunter valida o lead.
2. Pesquisa primária usa Jina para encontrar e ler concorrentes locais.
3. Em erro de quota, HTTP 429/402/403, timeout, indisponibilidade ou resposta insuficiente, a pesquisa usa Playwright headless para pesquisar e ler páginas renderizadas.
4. A pesquisa entrega fontes, intenção, público, linguagem, keywords locais, FAQ e padrões visuais observados.
5. A etapa de mídia busca no mínimo três imagens contextuais e estáveis, priorizando fotos reais do lead e usando Unsplash como complemento.
6. O Arquiteto recebe pesquisa, mídia, subnicho, dados factuais e histórico visual recente.
7. O Arquiteto produz PRD completo e uma assinatura visual exclusiva.
8. Um validador determinístico rejeita PRD incompleto antes do Builder.
9. O Builder envia ao OpenUI o PRD, as imagens e todos os contratos.
10. O HTML passa por validações determinísticas de contrato e segue pelo QA temporariamente desativado.
11. O Deploy publica somente HTML contratualmente completo.

## Contrato de Pesquisa

A pesquisa deve retornar:

- `provider`: `jina` ou `playwright`;
- URLs efetivamente analisadas;
- público-alvo e intenção predominante;
- linguagem e dores observadas;
- keywords locais e long-tail, sem alegar volume numérico quando nenhuma fonte de volume estiver disponível;
- perguntas frequentes observadas;
- seções e padrões visuais comuns;
- oportunidades de diferenciação, sem transformá-las em fatos sobre o lead.

Falhas da Jina que ativam fallback: limite de uso, autenticação/quota, HTTP 429, 402, 403, 5xx, timeout, falha de rede ou menos de 200 caracteres úteis.

## Contrato de Mídia

- Prioridade 1: fotos reais confirmadas do lead.
- Prioridade 2: fotos editoriais da API Unsplash.
- Prioridade 3: fallback curado e estável do nicho.
- Cada site deve receber seleção determinística pelo `lead_id`, evitando repetir exatamente o mesmo conjunto em leads distintos.
- O PRD deve exigir no mínimo três mídias quando houver URLs disponíveis.
- Hero deve usar ao menos uma imagem; outras imagens devem apoiar seções relevantes.

## Contrato Estrutural

O PRD deve conter, no mínimo:

1. Hero contextual ao público e cidade.
2. Sobre/diferenciais factuais.
3. Serviços, modalidades ou oferta.
4. Prova social real ou bloco de confiança sem depoimentos inventados.
5. FAQ orientado à intenção local.
6. Localização e contato.
7. Footer completo.

O documento deve conter title, description, canonical, Open Graph, favicon, JSON-LD LocalBusiness, FAQPage quando houver FAQ, GEO/NAP e controles LGPD.

## Diversidade Visual

Cada geração deve produzir uma assinatura contendo:

- arquétipo;
- paleta e estratégia cromática;
- dupla tipográfica;
- variante do hero;
- ordem e variantes das seções;
- tratamento de imagem;
- grid e densidade;
- direção de motion.

Antes do Builder, a assinatura deve ser comparada com sites recentes do tenant e, prioritariamente, do mesmo nicho/subnicho. Uma nova combinação deve ser escolhida quando coincidirem simultaneamente hero, dupla tipográfica, família cromática e ordem estrutural. A seleção deve permanecer determinística para o mesmo lead e mudar para leads diferentes.

## Regras de Conteúdo

- Não usar emojis no HTML visível, metadata ou JSON-LD.
- Não inventar métricas, avaliações, depoimentos, preços, certificações ou horários.
- Copy deve refletir público, cidade, intenção e pesquisa do lead.
- Keywords devem ser utilizadas naturalmente; não realizar keyword stuffing.
- Quando volume real não estiver disponível, registrar intenção e relevância, nunca fabricar volume.

## Tratamento de Falhas

- Jina indisponível: usar Playwright e registrar o provider.
- Jina e Playwright indisponíveis: falhar a pesquisa de forma estruturada; não gerar copy fingindo pesquisa.
- Nenhuma imagem: falhar antes do Arquiteto após esgotar fontes real, API e fallback curado.
- PRD incompleto ou contratos vazios: falhar no Arquiteto.
- Colisão visual persistente: avançar deterministicamente para outra combinação e registrar as assinaturas comparadas.
- HTML sem contrato obrigatório: falhar antes do QA pass-through.

## Critérios de Aceitação

- QUANDO a Jina retornar limite ou indisponibilidade, O SISTEMA DEVE concluir pesquisa com Playwright e registrar `provider=playwright`.
- QUANDO a Jina funcionar, O SISTEMA DEVE registrar `provider=jina` e não iniciar navegador desnecessariamente.
- PARA cada lead processado, O SISTEMA DEVE entregar pelo menos três URLs de mídia válidas ao Arquiteto.
- PARA cada PRD, O SISTEMA DEVE conter as sete famílias estruturais obrigatórias e os três contratos não vazios.
- PARA cada HTML, O SISTEMA DEVE conter imagem, FAQ, footer, metadata social, favicon, JSON-LD e LGPD.
- PARA cada HTML, O SISTEMA NÃO DEVE conter emojis nem métricas ou depoimentos não confirmados.
- DADOS dois leads distintos do mesmo nicho, O SISTEMA DEVE produzir assinaturas diferentes em pelo menos quatro dimensões, incluindo obrigatoriamente hero e uma entre paleta ou tipografia.
- O QA DEVE permanecer em `pass-through-temporary` durante esta entrega.

## Plano de Testes

- Teste unitário do classificador de falhas Jina e fallback Playwright.
- Teste unitário da seleção de mídia por lead.
- Teste unitário do contrato mínimo do PRD.
- Teste unitário da assinatura e resolução de colisão visual.
- Teste do payload Builder/OpenUI contendo pesquisa, imagens e contratos.
- Teste de dois leads sintéticos do mesmo nicho para diversidade determinística.
- Teste real com dois leads do tenant 2, comparando HTML, metadata, mídia e assinatura.
