# Vite/React Deploy Guide

> Documento canônico do motor oficial de geração da FraLib.
> O único caminho de publicação de sites é `vite_react`.

## O que é o motor canônico

- `backend/services/vite_react_renderer.py` é o renderer oficial.
- O builder gera um projeto React/Vite completo.
- A LLM participa apenas dentro do contrato `FRALIB_VITE_LLM_POLICY`.
- A publicação falha fechado se o artefato final não estiver marcado como `vite_react`.

## Fluxo oficial

1. `backend/services/builder_worker.py` recebe o PRD.
2. `render_vite_react_site()` monta o contrato do lead.
3. `FRALIB_VITE_LLM_POLICY` define o nível de participação da LLM.
4. O Studio React determinístico materializa hero, seções, mídia, SEO e LGPD.
5. O Quality Gate valida o HTML e o contrato factual.
6. O deploy publica em `/var/www/fralib/sites/<tenant>/<slug>/`.

## Políticas do renderer

| Policy | Comportamento |
|---|---|
| `creative_plan` | LLM retorna direção criativa curta em JSON; o Studio monta o React determinístico. |
| `copy_only` | LLM retorna apenas copy e slots de conteúdo. |
| `none` | Nenhuma chamada de LLM; tudo vem de fatos confirmados e regras canônicas. |
| `full_code` | LLM codifica mais, mas continua submetida ao mesmo Quality Gate. |

```bash
FRALIB_VITE_LLM_POLICY=creative_plan
FRALIB_VITE_LLM_POLICY=copy_only
FRALIB_VITE_LLM_POLICY=none
FRALIB_VITE_LLM_POLICY=full_code
```

## Contratos aplicados no build

- SEO por nicho e intenção local.
- Design System com variação de geometria, tipografia e superfícies.
- Motion Contract com GSAP / ScrollTrigger / Lenis quando o tema pede.
- A11y Contract com skip link, contraste e prefers-reduced-motion.
- LGPD personalizado por segmento.
- Deploy Rules com links `wa.me:` / `tel:` e sem iframes indevidos.

## Como debugar

### Tela preta

```bash
ls /tmp/fralib_builder/tenant-2/job-X/dist/
```

### Bundle não contém o lead

```bash
grep -R "Nome do Lead" /var/www/fralib/sites/2/X/assets/index-*.js
```

### LLM indisponível

```bash
# Corrigir a chave ou o provedor. O job deve falhar claramente.
```

### Lead não aparece no site

Verifique o manifest do builder e o contrato factual do PRD.

## Guard de publicação

Em produção:

```bash
FRALIB_ENV=prod
FRALIB_STRICT_CANONICAL_PUBLISH=1
```

Se o artefato não estiver marcado como `vite_react`, o deploy falha.

## Smoke e validação

```bash
pytest tests/test_regression_patches.py
python3 scripts/test_regression.py --tenant-id 2 --lead-id test-tenant2-academia-20260622193321
```

