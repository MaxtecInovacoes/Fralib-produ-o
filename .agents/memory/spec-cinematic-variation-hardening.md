# Spec — Cinematic Variation Hardening

## Purpose
Endurecer o builder Vite/React cinematográfico para que a pipeline oficial gere
sites variados, legíveis e consistentes sem depender de fallback OpenUI.

## Non-Goals
- Não trocar a esteira canônica de produção.
- Não reintroduzir renderers legados.
- Não aumentar chamadas LLM no renderer.

## Decisions
- Separar a lógica de tema legível em um módulo dedicado.
- Separar a escolha determinística de blocos/ordem em um registry dedicado.
- Variar seções por plano determinístico, não por código livre do LLM.
- Garantir contraste automático em superfícies de destaque.

## Acceptance Criteria
- THE SYSTEM SHALL resolver um tema cinematográfico a partir do briefing com
  fallback seguro e contraste coerente.
- THE SYSTEM SHALL resolver um block plan determinístico com ordem, navegação e
  variantes de seção.
- THE SYSTEM SHALL renderizar pelo menos variantes distintas de serviços/FAQ
  sem dependências extras de runtime.
- THE SYSTEM SHALL passar em testes unitários e build real do projeto gerado.
- THE SYSTEM SHALL manter `FRALIB_BUILDER_ENGINE=vite_react`,
  `FRALIB_VITE_LLM_POLICY=copy_only`, `FRALIB_ALLOW_OPENUI_FALLBACK=0`.

## Test Plan
- pytest focado em `tests/test_variation_seed.py`
- build real do projeto Vite gerado em pasta temporária
- checagem de imports/arquivos gerados para block plan e theme guard
