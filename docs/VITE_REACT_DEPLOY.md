# Vite/React Deploy Guide (Sprint 12.9+)

> **Sprint 12.9 mudou o engine padrão de OpenUI para Vite/React.**
> Este doc explica a arquitetura nova, como debugar, e como voltar para
> OpenUI se algo der errado.

## O que mudou

| Antes (até Sprint 12.8) | Depois (Sprint 12.9+) |
|---|---|
| Engine: `openui` (HTML estático) | Engine: `vite_react` (componentes TSX) |
| OpenUI fallback se LLM falha | Vite/React tenta LLM, cai para **studio-fallback** se tudo falhar |
| 1 arquivo HTML | Vite projeto completo (10+ TSX) |
| Tailwind CDN inline | Tailwind v4 com build |
| shadcn/ui ❌ | shadcn/ui ✅ |
| GSAP/Lenis ❌ | GSAP/Lenis ✅ |
| Cross-contamination: tudo passa | **Studio fallback com 26 segmentos** |

## Arquivos novos / modificados

| Arquivo | Mudança |
|---|---|
| `backend/services/vite_react_renderer.py` | **Engine principal** (era secundário) |
| `backend/services/vite_prompts.py` | Caroço rico com 7 contratos |
| `backend/services/vite_templates.py` | 10+ templates TSX (shadcn, modal, etc) |
| `backend/services/builder_worker.py` | `_builder_engine()` retorna `vite_react` por padrão |
| `scripts/builder_worker_job.py` | `agent=vite_react` por padrão |
| `tests/test_anti_regressao_v114.py` | **8 testes novos** validando caroço |
| `tests/_v1143_summary.json` | Smoke v15h validado Playwright |

## Como funciona o pipeline

```
1. builder_worker.py recebe PRD
2. build_builder_job_manifest() cria manifest
3. render_site_with_builder(prd) é chamado
4. engine = "vite_react" (default)
5. render_vite_react_site() tenta LLM (cascata Opus→Sonnet→Haiku)
6. Se TODOS falharem → studio fallback (determinístico, 26 segmentos)
7. Build Vite real (npm run build)
8. Publica /var/www/fralib/sites/2/<slug>/dist/
```

## Studio fallback (26 segmentos)

Quando o LLM falha, o `_generate_studio_fallback_files()` produz
um projeto Vite/React completo baseado no `business.segmento` do lead.

**Mapa segment-aware** (26 nichos cobertos):

```python
# backend/services/vite_react_renderer.py linha ~1918
if "barbearia" in segment: ...
elif "academia" in segment: ...
elif "restaurante" in segment: ...
# ... até 26 segmentos
```

**Bug CRÍTICO corrigido no Sprint 12.19**: template strings do fallback
usavam `"""` ao invés de `f"""`, fazendo `{var}` virar literal.
Fix via post-process `_interpolate_studio_placeholders()`.

## Como debugar

### Site mostra tela preta

```bash
# 1. Verificar se o build Vite rodou
ls /tmp/fralib_builder/tenant-2/job-X/dist/
# Esperado: index.html, assets/

# 2. Verificar se o JS bundle tem o nome do lead
ssh root@100.101.18.1 "grep 'Fio' /var/www/fralib/sites/2/X/assets/index-*.js"
# Esperado: 1+ matches

# 3. Verificar erros no console
# Usar Playwright:
python scripts/_investigate_v15d_v2.py
# Se "ReferenceError" → bug no template literal (fix já deployado)
```

### LLM retorna 401/429

```bash
# Verificar API keys
grep ANTHROPIC .env
# Fallback automático para studio (mesmo que render_vite_react falhe)
```

### Lead name não aparece

```bash
# Verificar manifest:
python3 -c "
import json
m = json.load(open('/root/fralib/logs/builder_manifests/tenant-2__job-X.json'))
biz = m['prompt_agent']['context']['business']
print(biz.get('name'), biz.get('segmento'))
"
# Esperado: Barbearia Fio Nobre Pinhais barbearia
```

## Voltar para OpenUI (se necessário)

```bash
# Local
echo "FRALIB_BUILDER_ENGINE=openui" >> .env
git add .env && git commit -m "fix: revert to openui engine"
git push origin master

# VPS
ssh root@100.101.18.1 "cd /root/repos/fralib && git pull"
pm2 restart fralib
```

## Métricas esperadas

| Métrica | Vite/React (Sprint 12.19) | OpenUI legado |
|---|---|---|
| Tempo de build | 30s (LLM) ou 5ms (fallback) | 10s |
| Tamanho do bundle | 150KB JS + 50KB CSS | 30KB HTML |
| First Paint | 1.2s | 0.5s |
| Tailwind | build real | CDN |
| Componentes React | 10+ | 1 (HTML) |
| GSAP/Lenis | sim | não |
| shadcn/ui | sim | não |
| Tela preta possível? | NÃO (post-process) | n/a |

## Tags v1.14.x

Todas as tags estão em `2026-06-25`:
- `v1.14.0-baseline` / `v1.14.0-lockpoint`
- `v1.14.1-baseline` / `v1.14.1-lockpoint`
- `v1.14.2-baseline` / `v1.14.2-lockpoint`
- `v1.14.3-baseline` / `v1.14.3-lockpoint`
- `v1.14.4-baseline` / `v1.14.4-lockpoint` ← **ATUAL**

Rollback para qualquer tag: `git checkout v1.14.0-baseline && pm2 restart fralib`.
