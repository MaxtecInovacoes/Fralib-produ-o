# SPEC — UX Sprint 2 + 3 (Empty States + Onboarding)

**Status:** Aprovado para implementação
**Baseado em:** openspec/changes/admin-ux-onboarding/proposal.md
**Loop:** Implementa → Testa → Conserta → Repete (max 10 iter)

## 🎯 OBJETIVO
Reduzir fricção do primeiro uso: empty states honestos + wizard de 3 passos.

## 📦 ENTREGAS

### Sprint 2 — Empty states (P0)
- [ ] **2.1** Visão Geral: empty state com botão "CADASTRAR PRIMEIRO LEAD"
- [ ] **2.2** Sites: empty state com botão "LIGAR O MOTOR"
- [ ] **2.3** Estoque (linha de produção): empty state com botão "BUSCAR LEADS AGORA"

### Sprint 3 — Onboarding wizard (P1)
- [ ] **3.1** Partial `_onboarding-wizard.html` com 3 passos
- [ ] **3.2** CSS do wizard (overlay roxo, Press Start 2P)
- [ ] **3.3** JS `onboarding.js` (next, skip, concluir, localStorage)
- [ ] **3.4** Trigger automático na 1ª sessão (admin.html)

## 🧪 LOOP DE VALIDAÇÃO

```bash
# 1. Implementa
git add -A && git commit -m "UX Sprint X.Y: ..."

# 2. Valida (verde = prossegue)
./scripts/verify_all.sh

# 3. Testa localmente (curl no admin.html)
curl -s https://seunegociofralib.site/admin.html | grep -c "empty-state"

# 4. Se vermelho, conserta
git add -A && git commit -m "fix: ..."

# 5. Repete até verde (max 10 iter)
```

## ⚠️ NÃO-REGRESSÃO
- Visual/design system: INTOCADO
- Tour de 7 passos: INTOCADO
- Pixel Office: INTOCADO
- Kanban drag-and-drop: INTOCADO

## 📁 ARQUIVOS

### Modificar
- `frontend/partials/admin/_view-overview.html` (empty state)
- `frontend/partials/admin/_view-sites.html` (empty state)
- `frontend/partials/admin/_view-config.html` (empty state linha de produção)
- `frontend/admin.html` (incluir partial wizard + trigger)

### Criar
- `frontend/partials/admin/_onboarding-wizard.html`
- `frontend/js/admin/onboarding.js`

## ✅ DEFINITION OF DONE
- [ ] 3 empty states implementados e visíveis quando vazio
- [ ] Wizard aparece só na 1ª sessão (localStorage)
- [ ] Skip e Concluir funcionam
- [ ] Nenhuma regressão visual
- [ ] Push na VPS + curl valida