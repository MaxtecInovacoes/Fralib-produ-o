# SPEC: Quebrar html_quality_gate.py

**Status:** Draft → Aprovada
**Data:** 2026-06-19
**Skill ECC:** `refactor-cleaner` + `silent-failure-hunter`

---

## 🎯 OBJETIVO

Quebrar `backend/agents/html_quality_gate.py` (1675 linhas, 1 monolito) em **5 módulos coesos** < 400 linhas cada, sem mudar comportamento, identificando todos os `try/except` silenciosos.

---

## ✅ CRITÉRIOS DE ACEITE

| # | Critério | Métrica |
|---|----------|---------|
| 1 | html_quality_gate.py vira wrapper | < 100 linhas |
| 2 | 5 módulos criados | cada um < 400 linhas |
| 3 | Zero imports quebrados | `bash scripts/fix_imports.sh --dry-run` = 0 |
| 4 | verify_all.sh continua 🟡/🟢 | sem regressão |
| 5 | Silent failures documentados | lista de TODOS try/except engolindo erro |

---

## 🚫 FORA DE ESCOPO

- ❌ Mudar comportamento de QUALQUER função
- ❌ Reescrever lógica de validação
- ❌ Adicionar features novas
- ❌ Mudar API pública

---

## 🏗️ RESTRIÇÕES

- Constitution: < 800 linhas por arquivo
- Wrappers de compatibilidade
- Manter try/except (mesmo silenciosos) - mas DOCUMENTAR

---

## 📦 MÓDULOS PROPOSTOS

| Módulo | LOC estimada | Responsabilidade |
|--------|--------------|------------------|
| `html_quality_injectors.py` | ~400 | Injeção de fonts, meta, OG, LGPD, CSS |
| `html_quality_validators.py` | ~350 | Validação de estrutura HTML |
| `html_quality_seo.py` | ~250 | SEO, canonical, sitemap |
| `html_quality_motion.py` | ~250 | GSAP, Lenis, scroll effects |
| `html_quality_gate.py` | ~50 | Wrapper de compatibilidade |

---

## 📋 TASKS

### Task 1: Auditar silent failures
- [ ] Listar TODOS os try/except do arquivo
- [ ] Categorizar: crítico / informativo / silencioso
- [ ] Documentar em `docs/HTML_QUALITY_SILENT_FAILURES.md`

### Task 2: Criar html_quality_injectors.py
- [ ] Extrair funções de injeção
- [ ] Criar wrapper

### Task 3: Criar html_quality_validators.py
- [ ] Extrair funções de validação
- [ ] Criar wrapper

### Task 4: Criar html_quality_seo.py
- [ ] Extrair funções SEO
- [ ] Criar wrapper

### Task 5: Criar html_quality_motion.py
- [ ] Extrair funções de motion
- [ ] Criar wrapper

### Task 6: Transformar html_quality_gate.py em wrapper
- [ ] Re-exportar tudo
- [ ] Validar verify_all

---

## 🛡️ VALIDAÇÃO

- `bash scripts/verify_all.sh` 🟡/🟢
- `bash scripts/check_agents_alive.sh` sem novos órfãos
- `git diff` mostra apenas movimentação de código
