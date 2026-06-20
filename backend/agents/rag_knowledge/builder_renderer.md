# Builder Renderer RAG

## Papel
Builder Renderer e apenas o executor final do prompt produzido pelo Agente de
Prompt. Ele recebe um pedido completo, cria o projeto em sandbox isolado e gera
`dist/index.html`.

## Contrato
- Nao receber regras antigas de PRD, SEO, verdade, foto, hero, footer ou gate.
- Nao receber skills/RAG de design como instrucao oculta.
- Trabalhar dentro do workspace informado pelo Builder Worker.
- Entregar um documento HTML publicavel em `dist/index.html`.
