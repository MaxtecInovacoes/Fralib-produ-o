# Politica de Privacidade e LGPD FraLib

Versao: `fralib-privacidade-v1-2026-06-08`

Esta politica explica como a FraLib trata dados pessoais e dados operacionais no uso da plataforma de prospeccao, geracao de sites, publicacao, IA, Lead Supply e SDR/WhatsApp. Ela complementa os Termos de Uso FraLib.

Este documento deve ser revisado por advogado antes de uso comercial definitivo. O sistema ja exige aceite versionado no cadastro.

## 1. Papeis LGPD

Em geral:

- A FraLib atua como controladora dos dados da conta, seguranca, pagamento, suporte, uso do painel, logs de auditoria e prevencao a abuso.
- A FraLib pode atuar como operadora dos dados de leads, clientes finais e conteudos que o usuario insere, importa, coleta ou processa dentro do tenant.
- O usuario pode ser controlador dos dados de leads e clientes que decide prospectar, contatar, enriquecer, publicar ou vender.

Se o usuario usa a FraLib para atender terceiros, ele deve ter base legal, contrato e autorizacao para tratar dados desses terceiros e de seus leads.

## 2. Dados que podemos tratar

Dados de conta:

- nome, email, telefone, senha com hash, status, plano, creditos, tenant, role e historico de acesso;
- aceite de Termos/Privacidade com versao, data e IP;
- dados de suporte, comunicacoes e preferencias.

Dados operacionais:

- nicho, cidade, pipeline, leads aprovados/rejeitados, status, score, telefone/WhatsApp quando coletado, site, endereco, observacoes e historico comercial;
- sites gerados, HTML publicado, manifests, contratos visuais, logs de Builder, imagens, metadados SEO e tracking essencial;
- configuracoes do WhatsApp/SDR, mensagens, opt-out, estagios e memoria operacional quando habilitado;
- logs de jobs, filas, spans, ledger de tokens, provider alerts, auditoria de seguranca e metricas.

Dados de chaves e integracoes:

- provider keys e chaves de IA criptografadas quando o usuario cadastra chave propria;
- identificadores de pagamento, plano, status de assinatura, eventos de webhook e dados minimos retornados pelo Mercado Pago;
- tokens de sessao, cookies essenciais e CSRF.

Nao queremos receber dados sensiveis desnecessarios. O usuario nao deve inserir documentos, prontuarios, dados de criancas, saude, biometria, origem racial, religiao, politica, vida sexual ou dados financeiros de terceiros sem base legal, necessidade e medidas adicionais.

## 3. Finalidades

Tratamos dados para:

- criar e proteger contas;
- entregar Lead Supply, qualificacao, pesquisa, Builder, publicacao, editor e SDR;
- aplicar limites, creditos, cooldowns e planos;
- gerar, revisar e publicar sites;
- manter historico, auditoria, logs e suporte;
- detectar abuso, spam, fraude, invasao, uso entre tenants e vazamento de chaves;
- processar pagamentos e inadimplencia;
- cumprir lei, ordem de autoridade, defesa judicial ou regulatoria;
- melhorar performance, qualidade e seguranca com metricas agregadas ou anonimizadas quando possivel.

## 4. Bases legais

As bases podem incluir execucao de contrato, cumprimento de obrigacao legal/regulatoria, legitimo interesse para seguranca/prevenção a fraude/melhoria do servico, exercicio regular de direitos e consentimento quando exigido.

Para leads e clientes finais, o usuario deve definir e documentar sua propria base legal. A FraLib pode bloquear uso quando houver indício de coleta sem autorizacao, spam ou violacao de direitos.

## 5. Compartilhamento

Podemos compartilhar dados estritamente necessarios com:

- provedores de infraestrutura, banco, email, hospedagem, observabilidade e seguranca;
- provedores LLM/IA configurados pela FraLib ou pelo usuario;
- Mercado Pago para processamento de assinaturas, recargas, PIX e cartao;
- APIs externas usadas para pesquisa, imagens, mapas, comunicacao ou WhatsApp;
- autoridades, bancos, parceiros antifraude, vitimas ou provedores quando necessario para conter abuso, cumprir lei ou defender direitos.

Nao vendemos dados pessoais de usuarios ou leads como base independente. Dados agregados e anonimizados podem ser usados para analise de produto e capacidade.

## 6. Retencao

Mantemos dados enquanto a conta estiver ativa, enquanto forem necessarios para entregar o servico, cumprir obrigações legais, auditar seguranca, resolver disputa, prevenir fraude ou respeitar prazos de defesa.

O usuario pode solicitar exportacao, correcao ou exclusao conforme a lei. Algumas informacoes podem permanecer em backups, logs de seguranca, trilhas de auditoria e registros fiscais/pagamento pelo prazo necessario.

## 7. Direitos do titular

Titulares podem solicitar confirmacao de tratamento, acesso, correcao, anonimizacao, bloqueio, eliminacao, portabilidade, informacao sobre compartilhamento, revisao de decisoes automatizadas quando aplicavel e revogacao de consentimento.

Quando a FraLib atuar como operadora para dados de leads do usuario, podemos direcionar a solicitacao ao usuario controlador.

## 8. Seguranca

A FraLib usa medidas como:

- senha com hash;
- JWT com segredo minimo em producao;
- cookie HttpOnly e CSRF para nova sessao web;
- criptografia Fernet para provider keys;
- RBAC/superadmin em endpoints sensiveis;
- mascaramento de chaves;
- auditorias de tenant scope;
- gates contra codigo gerado com fetch/env/cookies/storage/eval;
- logs e alertas de providers;
- rate limit e Redis quando configurado;
- isolamento multi-tenant por `tenant_id/user_id`.

Riscos ainda exigem disciplina operacional: `FRALIB_ENV=prod`, Redis ativo, HTTPS, rotacao de chaves, 2FA obrigatorio, backups testados e monitoramento de incidentes.

## 9. Cookies e sessao

Usamos cookies essenciais para sessao, CSRF e seguranca. Sites gerados podem usar banner LGPD e storage de consentimento essencial. Cookies de marketing, pixels e analytics devem respeitar a legislacao e a configuracao do usuario/tenant.

## 10. Incidentes

Se houver incidente de seguranca com risco relevante, a FraLib avaliara escopo, impacto, medidas de contencao, comunicacao a titulares/controladores, ANPD ou autoridades quando exigido, e preservacao de evidencias.

## 11. Responsabilidades do usuario

O usuario deve:

- ter base legal para leads e contatos;
- respeitar opt-out;
- nao importar dados proibidos;
- revisar sites/mensagens antes de publicar/enviar;
- proteger acessos e chaves;
- configurar corretamente WhatsApp, dominios, tracking e pagamentos;
- responder titulares quando for controlador.

## 12. Contato

Solicitacoes de privacidade, seguranca, exclusao, exportacao ou abuso devem ser enviadas pelo canal oficial de suporte da FraLib informado no painel ou no site.
