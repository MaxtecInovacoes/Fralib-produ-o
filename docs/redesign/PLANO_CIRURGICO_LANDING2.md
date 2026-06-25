# PLANO CIRÚRGICO — landing2.html (FraLib)

**Baseado em dados reais coletados do banco (commit `971579e` deployado em produção)**

---

## 📊 DIAGNÓSTICO (dados de 17-24/06, 458 sessões únicas)

| Métrica | Valor | Benchmark mercado |
|---------|-------|-------------------|
| Bounce | 12.4% | 44-48% ✅ MUITO BOM |
| **Exit no HERO** | **70%** das saídas | ❌ CRÍTICO |
| Scroll 25% | 5% | 50-60% ❌ |
| Scroll 100% | 4% | ~10% ❌ |
| Cliques Hero CTA | 5 (1%) | 3-8% ❌ |
| **Conversões** | **0** | 3.8% ❌ CRÍTICO |

**Sections com baixíssima view (3 ou menos):**
- cta-final, depoimentos, video-demo, comparacao, para-quem, social-proof, problema

**Sections invisíveis para 95% dos usuários:**
- PLANOS está na posição #8 (só 6 views em 458 sessões)

---

## 🎯 5 MUDANÇAS CIRÚRGICAS (sem mexer em design/layout/cores/fontes)

### Mudança #1 — Adicionar seção PLANOS na posição #3

**Por quê:** 95% dos usuários nunca chega no pricing (posição #8).

**Onde:** Logo após `</section>` da seção Social Proof (linha ~1225).

**O que adicionar (copie o bloco abaixo INTEIRO entre a seção Social Proof e a próxima seção):**

```html
<!-- ===== SEÇÃO 3 — PLANOS (movido para cima: 95% dos users nunca chega no #8) ===== -->
<section class="planos" id="planos" data-section-id="planos" style="background:transparent;padding:80px 0;">
  <div class="container">
    <h2 class="section-title reveal">ESCOLHA COMO QUER COMEÇAR</h2>
    <p class="section-sub reveal" style="text-align:center;margin:0 auto 48px;max-width:680px;color:var(--fl-text-muted);font-size:15px;">
      1 pipeline grátis para testar. Os outros 3 planos existem pra quando você estiver ganhando e quiser escalar.
    </p>
    <div class="planos-grid">
      <div class="plano-card reveal">
        <div class="plano-name">TRIAL</div>
        <div class="plano-price">R$ 0</div>
        <div class="plano-period" style="font-size:12px;margin-bottom:16px;color:var(--fl-text-muted);">7 dias grátis · sem cartão</div>
        <ul class="plano-features">
          <li>1 site gerado</li>
          <li>Prospecção básica</li>
          <li>SDR Franz (1 abordagem)</li>
        </ul>
        <a href="/login?signup=1&amp;plano=trial" class="btn btn-outline" style="margin-top:20px;width:100%;">COMEÇAR GRÁTIS</a>
      </div>
      <div class="plano-card destaque reveal">
        <div class="plano-name">PRO</div>
        <div class="plano-price">R$ 97<span style="font-size:14px;color:var(--fl-text-muted);">/mês</span></div>
        <div class="plano-period" style="font-size:12px;margin-bottom:16px;color:var(--fl-text-muted);">Para quem fechou pelo menos 1 venda</div>
        <ul class="plano-features">
          <li>Tudo do Trial +</li>
          <li>5 sites ativos</li>
          <li>SDR ilimitado</li>
          <li>Suporte prioritário</li>
        </ul>
        <a href="/login?signup=1&amp;plano=pro" class="btn btn-primary" style="margin-top:20px;width:100%;">ASSINAR PRO</a>
      </div>
      <div class="plano-card reveal">
        <div class="plano-name">SCALE</div>
        <div class="plano-price">R$ 197<span style="font-size:14px;color:var(--fl-text-muted);">/mês</span></div>
        <div class="plano-period" style="font-size:12px;margin-bottom:16px;color:var(--fl-text-muted);">Para quem quer escalar prospecção</div>
        <ul class="plano-features">
          <li>Tudo do Pro +</li>
          <li>20 sites ativos</li>
          <li>Multi-usuário (até 3)</li>
          <li>API de integração</li>
        </ul>
        <a href="/login?signup=1&amp;plano=scale" class="btn btn-outline" style="margin-top:20px;width:100%;">ASSINAR SCALE</a>
      </div>
      <div class="plano-card reveal">
        <div class="plano-name">AGENCY</div>
        <div class="plano-price">R$ 497<span style="font-size:14px;color:var(--fl-text-muted);">/mês</span></div>
        <div class="plano-period" style="font-size:12px;margin-bottom:16px;color:var(--fl-text-muted);">Para agências e times</div>
        <ul class="plano-features">
          <li>Tudo do Scale +</li>
          <li>Sites ilimitados</li>
          <li>White-label completo</li>
          <li>Onboarding VIP</li>
        </ul>
        <a href="/login?signup=1&amp;plano=agency" class="btn btn-outline" style="margin-top:20px;width:100%;">FALAR COM COMERCIAL</a>
      </div>
    </div>
    <p class="section-sub reveal" style="text-align:center;margin:32px auto 0;max-width:720px;font-size:13px;color:var(--fl-text-muted);">
      Pagamento seguro via Mercado Pago · PIX e cartão · Cancele quando quiser
    </p>
  </div>
</section>
```

**Nota importante:** Esta seção DUPLICA a lógica da seção PLANOS original (#8). NÃO remova a original ainda — primeiro meça o impacto. Se pricing em #3 gerar conversão, depois remova a #8.

---

### Mudança #2 — Reforçar texto do Hero CTA

**Problema atual:** "COMEÇAR COM 1 PIPELINE GRÁTIS" — só 5 cliques em 458 sessões (1%).

**Benchmark:** CTAs com verbo + benefício claro têm 2-3x mais cliques.

**Onde:** Dentro da seção `.hero`, no botão CTA principal.

**Localizar:** `<a href="/login?signup=1" class="btn ..."` ou similar (procure por "COMEÇAR COM 1 PIPELINE GRÁTIS").

**Mudar o texto de:**
```
COMEÇAR COM 1 PIPELINE GRÁTIS
```

**Para:**
```
QUERO MEU PRIMEIRO SITE GRÁTIS
```

(Ou mantenha o original se preferir — esse é mais específico pro problema do freelancer.)

---

### Mudança #3 — Adicionar scroll indicator no Hero

**Por quê:** 70% saem no hero — eles não sabem se há mais conteúdo embaixo.

**Onde:** Logo antes do `</section>` do hero (final do hero).

**Adicionar:**
```html
<div style="text-align:center;margin-top:48px;opacity:0.6;">
  <span style="display:inline-block;animation:bounce-down 2s infinite;color:var(--fl-text-muted);font-size:11px;letter-spacing:2px;font-family:var(--fl-font-mono);">↓ role para ver como funciona</span>
</div>
<style>
@keyframes bounce-down{0%,100%{transform:translateY(0);opacity:0.6}50%{transform:translateY(8px);opacity:1}}
</style>
```

---

### Mudança #4 — Adicionar micro-CTA no final do FAQ

**Problema atual:** FAQ tem só 6 views — quem chega lá pode estar pronto pra comprar, mas não tem CTA perto.

**Onde:** Logo após `</div></div>` da última pergunta do FAQ (final da seção).

**Adicionar:**
```html
<div style="text-align:center;margin-top:48px;">
  <p style="color:var(--fl-text-muted);font-size:14px;margin-bottom:16px;">Ainda tem dúvida?</p>
  <a href="/login?signup=1" class="btn btn-primary">COMEÇAR COM 1 PIPELINE GRÁTIS</a>
</div>
```

---

### Mudança #5 — CTAs repetidos nas seções de baixa view

**Seções que precisam de CTA adicional:**
- `depoimentos` (3 views)
- `comparacao` (3 views)
- `cta-final` (3 views)

**Ação:** Adicionar `<a href="/login?signup=1" class="btn btn-primary">...</a>` antes do `</section>` dessas seções.

**Onde:** Procure pelos comentários `<!-- ===== SEÇÃO 12` (depoimentos), `<!-- ===== SEÇÃO 13` (comparacao), `<!-- ===== SEÇÃO 14` (cta-final).

**Texto sugerido:**
```html
<div style="text-align:center;margin-top:32px;">
  <a href="/login?signup=1" class="btn btn-primary" style="font-family:var(--fl-font-brand);font-size:11px;">QUERO TESTAR GRÁTIS</a>
</div>
```

---

## 📋 WORKFLOW DE COMMIT

**Cada mudança = 1 commit separado:**

```bash
git add frontend/landing2.html
git commit -m "feat(landing2): adicionar seção PLANOS na posição #3 (dados: 95% não chega no pricing atual)"
# → auto-deploy
```

---

## 📏 COMO MEDIR DEPOIS (7 dias)

Rodar query SQL:
```sql
SELECT valor_extra, COUNT(*) 
FROM landing_analytics 
WHERE evento = 'section_view' 
  AND criado_em > NOW() - INTERVAL '7 days'
GROUP BY valor_extra
ORDER BY 2 DESC;
```

**Esperado:**
- `planos` subir de 6 → 50+ views (8x mais)
- Cliques Hero CTA subir de 5 → 15+ (3x)
- Conversões: 0 → pelo menos 1-2

Se melhorar, **remova a seção PLANOS duplicada** (linha original #8) num commit separado.

---

## ⚠️ REGRAS

1. **NÃO mexa em CSS** — as classes `.plano-card`, `.planos-grid`, `.btn` já existem
2. **NÃO remova seções** — apenas adicione
3. **Faça commit separado por mudança** para fácil rollback
4. **Teste visual**: `curl http://187.77.37.72/landing2.html | head -50`
5. **Confirme com o usuário após cada mudança**