# PRD Snapshot — High Fitness Academia

Data: 2026-05-27
Pipeline ID: `u2-high-fitness-academia-academia-campina-grande-do-sul-0afe72f469`
URL: `https://seunegociofralib.site/sites/2/high-fitness-academia/`

## Fonte de Verdade

Negócio: High Fitness Academia
Segmento: Academia
Cidade: Campina Grande do Sul
Telefone/WhatsApp: (41) 99111-4140
Endereço: ausente no lead capturado
Avaliação: 4.6
Reviews: 89
Horários:
- domingo: Fechado
- segunda-feira: 06:00-22:00
- terça-feira: 06:00-22:00
- quarta-feira: 06:00-22:00
- quinta-feira: 06:00-22:00
- sexta-feira: 06:00-22:00
- sábado: 09:00-13:00

## Regra Arquitetural Atual

FraLib deve entregar apenas PRD, fatos, reviews, mídia de apoio e contrato de verdade.
Open Design decide layout, composição, mídia visual, motion, footer e acabamento.
Depois do Open Design, FraLib só publica o `index.html` retornado e aciona Bryan.

## Pedido Enviado ao Open Design

Objetivo: gerar site demonstrativo vendável para conversão via WhatsApp.

Autoridade:
- Arquiteto Mestre controla seções, intenção de copy, fatos e SEO.
- Open Design controla composição, interação e acabamento visual.

Modelo de trabalho:
- Pensar como React/Next: árvore de componentes, seções reutilizáveis, interações sem estado pesado e responsividade.
- Exportar o resultado final como um único `index.html` self-contained.

Visual:
- Design system: neobrutalism.
- Direção: premium inspirado em Nike.
- Paleta: fundo escuro OKLch, texto claro, acento vermelho.
- Tipografia: Oswald para heading, Inter para corpo.
- Hero: split, forte, com mídia acima da dobra.
- Motion: scroll reveal, microinterações e animação visível.
- Footer: deve usar o mesmo sistema visual da página e ano atual, ou omitir ano.

## Seções Aprovadas

1. Hero
H1: Academia em Campina Grande do Sul - High Fitness Academia
Subtítulo: Equipamentos robustos, professores dedicados e um ambiente preparado para o seu progresso em Campina Grande do Sul.
CTA: Agendar Aula Experimental

2. Sobre
H2: Sobre a High Fitness
Copy: A galera que chega às 10h na manhã são sempre nota 10. Os aparelhos, embora não sejam os tops de linha, atendem perfeitamente quem busca treino consistente. Temos dança para a mulherada e o professor Godoy, que corrige e aperfeiçoa com precisão cirúrgica. Sempre bem atendido pela equipe.
CTA: Ver Horários

3. Serviços
H2: Especialidades
Copy: Foco em musculação e dança com acompanhamento personalizado.
Itens: Musculação | Dança | Personal Trainer
CTA: Ver Planos

4. Contato
H2: Contato
Copy: (41) 99111-4140
CTA: Chamar no WhatsApp

5. Depoimentos
H2: O que dizem os alunos
Copy baseada somente em reviews reais capturados.

6. Planos
H2: Planos
CTA: Fale Conosco
Observação: não inventar preços.

7. FAQ
H2: Perguntas Frequentes
Perguntas: Qual a mensalidade? Tem aula experimental? Qual o horário?

8. Footer
Layout: footer-3col
CTA: Fale Conosco
Regra: dados reais, mesma linguagem visual do site, sem ano antigo.

## O Que Foi Entregue no Teste 240

O Open Design gerou HTML novo, mas visualmente fraco e com footer genérico.
O HTML do próprio OD já continha `© 2024`, antes de qualquer deploy.
FraLib ainda injetava schema e uma galeria `fralib-media-guard` após o footer; isso foi identificado como interferência indevida e removido do fluxo.

## Correção de Direção

O próximo teste deve avaliar o Open Design puro:
- sem Validador FraLib após OD;
- sem BeautifulSoup auto-healing;
- sem schema injection;
- sem galeria/contact/location guard;
- sem canonical/pixel rewrite;
- sem health check bloqueante;
- sem reuse de HTML antigo antes de rodar OD.

Se o site sair ruim, a falha fica claramente no PRD enviado ou no uso do Open Design, não em remendos pós-geração.
