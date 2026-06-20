# OpenSpec no FraLib

## Veredito

OpenSpec e valido para o FraLib como camada leve de especificacao antes de
mudancas grandes de seguranca, infra, billing, auth, SDR e Builder. Nao deve ser
runtime, gate de deploy, nem substituto de testes.

Fontes consultadas:
- https://openspec.dev/
- https://github.com/Fission-AI/OpenSpec

## Onde ajuda

- Registrar requisito antes da implementacao: proposta, design, tasks e delta de spec.
- Evitar que agentes mudem comportamento critico sem contrato revisavel.
- Manter contexto entre Codex, OpenCode, Claude Code, Cursor e outros agentes.
- Revisar intencao, nao apenas diff de codigo.

## Onde nao deve entrar

- Nao instalar como dependencia do app Docker/PM2.
- Nao bloquear deploy de producao enquanto nao houver piloto validado.
- Nao substituir `pytest`, `pipeline.py pre-release-gate`, `check_secret_hygiene.py`,
  `tenant_scope_audit.py` ou contratos E2E.

## Piloto recomendado

1. Instalar apenas na maquina de dev: `npm install -g @fission-ai/openspec@latest`.
2. Rodar `openspec init` em branch propria.
3. Criar primeiro change para `security-hardening-auth-metrics-editor`.
4. Versionar somente `openspec/` e instrucoes, sem tocar runtime.
5. Aprovar uso continuo somente se o fluxo reduzir retrabalho e nao duplicar docs.

## Regra FraLib

Mudancas grandes devem poder responder:

- Qual requisito muda?
- Qual risco reduz?
- Qual teste prova?
- Qual rollback existe?
- Qual impacto em tenant, custo, pipeline e VPS?
