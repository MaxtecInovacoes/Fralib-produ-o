# 📋 PLANO LOCAL: FraLib Premium Upgrade

**Data:** 2026-06-19
**Executor:** LOCAL (sem mexer na VPS)
**VPS:** apenas auditoria read-only no final
**Score Atual:** 5.4/10 → **Meta: 8.5/10**

---

## 🎯 O QUE VOU FAZER (LOCAL APENAS)

### FASE A: Spec + Scripts [15 min]
- [ ] A1: Criar este SPEC ✅
- [ ] A2: Criar `scripts/fix_imports.sh` (automatiza correções)
- [ ] A3: Criar `scripts/check_agents_alive.sh` (detecta código morto)
- [ ] A4: Criar `scripts/audit_vps.sh` (auditoria VPS read-only)

### FASE B: Corrigir imports quebrados [30 min]
- [ ] B1: Rodar `fix_imports.sh --dry-run` (preview)
- [ ] B2: Aplicar correções
- [ ] B3: Validar com `verify_all.sh`

### FASE C: Ativar Quality Gate [10 min]
- [ ] C1: Editar `backend/services/pipeline_flow_config.py`
- [ ] C2: Remover lógica que pula Gate por padrão

### FASE D: Atualizar Vite prompt [20 min]
- [ ] D1: Adicionar LANGUAGE (PT-BR)
- [ ] D2: Adicionar ACCESSIBILITY
- [ ] D3: Adicionar SEO
- [ ] D4: Adicionar LGPD
- [ ] D5: Adicionar MOTION (GSAP, Lenis, parallax)

### FASE E: Deletar código morto [10 min]
- [ ] E1: Rodar `check_agents_alive.sh` para confirmar
- [ ] E2: Deletar: `bloco_prd_compacto.py`, `brain.py`, `creative_build_brief.py`, `html_sanitizer.py`

### FASE F: Criar Design Director [30 min]
- [ ] F1: Criar `backend/agents/design_director.py`
- [ ] F2: System prompt + fallback

### FASE G: Atualizar verify_all [10 min]
- [ ] G1: Adicionar testes para novos critérios (PT-BR, A11Y, etc)
- [ ] G2: Adicionar teste para Design Director

### FASE H: Auditoria VPS [20 min]
- [ ] H1: `git fetch origin` na VPS (read-only)
- [ ] H2: Comparar commits
- [ ] H3: Diff de arquivos principais
- [ ] H4: Confirmar que VPS está sincronizada com GitHub
- [ ] H5: Listar divergências (commits locais não commitados)

### FASE I: Commit LOCAL (SEM PUSH) [10 min]
- [ ] I1: `git add -A`
- [ ] I2: `git commit -m "feat: premium upgrade local"`
- [ ] I3: NÃO FAZER PUSH (você decide quando)

---

## 🚫 FORA DO ESCOPO

- ❌ Push para GitHub (você decide quando)
- ❌ Pull na VPS (você decide quando)
- ❌ Editar arquivos na VPS
- ❌ Reiniciar serviços na VPS
- ❌ Mexer em arquivos monolíticos grandes (vite_react_renderer.py, html_quality_gate.py, etc)
- ❌ Deletar arquivos que ainda são usados

---

## ✅ CRITÉRIOS DE ACEITE

| # | Critério | Como verificar |
|---|----------|----------------|
| 1 | 0 imports quebrados | `grep -rE "from (core\|services\|agents) " backend --include="*.py" \| grep -v backend\.\|wc -l` = 0 |
| 2 | Vite prompt tem PT-BR | `grep "Brazilian Portuguese" backend/services/vite_prompts.py` |
| 3 | Vite prompt tem A11Y | `grep "ACCESSIBILITY" backend/services/vite_prompts.py` |
| 4 | Vite prompt tem SEO | `grep "SEO" backend/services/vite_prompts.py` |
| 5 | Vite prompt tem LGPD | `grep "LGPD" backend/services/vite_prompts.py` |
| 6 | Vite prompt tem Motion | `grep "MOTION" backend/services/vite_prompts.py` |
| 7 | Quality Gate sempre ativo | `grep "skip_html_quality_gate" backend/services/pipeline_flow_config.py` não tem `is_prompt_agent_flow` |
| 8 | Design Director existe | `[ -f backend/agents/design_director.py ]` |
| 9 | 4 arquivos mortos deletados | `ls backend/agents/{bloco_prd_compacto,brain,creative_build_brief,html_sanitizer}.py 2>&1 \| grep "No such"` |
| 10 | VPS auditada | `docs/VPS_AUDIT_v_LOCAL.md` criado |

---

## 📊 COMPARAÇÃO COM VPS

**Local (596992f):** Estado anterior, antes do premium upgrade
**VPS (08d3038):** Tem TUDO o que eu fiz (commits já estão lá)
**Diferença:** VPS está 1 commit A FRENTE do local (revertido)

Quando você decidir fazer push, a VPS vai precisar de `git pull` para pegar tudo.

---

## 🚀 EXECUÇÃO

Vou executar **UMA FASE POR VEZ** e mostrar o resultado antes de continuar.

Começando pela **FASE A**.
