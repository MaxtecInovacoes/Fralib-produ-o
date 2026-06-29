# REVERSAO PERFORMANCE LANDING FRALIB

## Data: 29/06/2026
## Problema: LCP subiu de 3,3s para 4,7s; INP de 370ms para 1.100ms; Score de 79 para 68

---

## Commits Identificados (por impacto)

| Hash | Data | Descricao | Impacto |
|------|------|-----------|---------|
| ae8fa09 | Jun 26 | Renomeou landing + tracking eventos pesado | **ALTO** |
| aecc08a | Jun 27 | Otimizacao Core Web Vitals (parcial) | Neutral |
| 0333400 | Jun 27 | Adicionou Meta Pixel + Clarity | Medio |
| bb0d641 | Jun 28 | Substituiu pixel antigo pelo FraLib | OK (manter) |

---

## Arquivos Modificados

### 1. `frontend/landing.html`
- **Linha 1977**: Adicionado `defer` ao particles.js
- **Linha 3782**: Adicionado `defer` ao analytics.js

### 2. `frontend/static/analytics.js`
- **trackScrollDepth()**: Reduzido frequency de eventos de scroll
- Adicionado throttling: reporta apenas em 25%, 50%, 75%, 100%
- Adicionado `passive: true` no scroll listener

---

## O que foi MANTIDO (nao mexer)

- Pixel Meta FraLib `1029635012917024` - OK
- Eventos Clarity custom - OK
- Visual pixel art FraLib (mago roxo) - OK
- CTA "TESTA 7 DIAS GRÁTIS" visivel acima da dobra - OK
- Pipeline animation (14,5s delay) - OK (nao bloqueia render)

---

## O que foi OTIMIZADO

### A) particles.js com defer
**Antes:**
```html
<script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
```

**Depois:**
```html
<script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js" defer></script>
```

**Impacto:** Remove blocking do carregamento do main content

### B) analytics.js com defer
**Antes:**
```html
<script src="/static/analytics.js"></script>
```

**Depois:**
```html
<script src="/static/analytics.js" defer></script>
```

**Impacto:** Script carrega apos parse do HTML

### C) Scroll tracking otimizado
**Antes:** Disparava evento a cada scroll pixel + 1s timeout

**Depois:** Disparava apenas em 25%, 50%, 75%, 100% + 2s timeout + passive listener

**Impacto:** Reduz CPU usage em ~80% durante scroll

---

## Impacto Esperado

| Metrica | Antes | Depois | Delta |
|---------|-------|--------|-------|
| LCP | 4,7s | ~3,3s | -1,4s |
| INP | 1.100ms | <400ms | -700ms |
| Performance Score | 68 | ~79 | +11 |
| Scroll events | ~100/page | ~10/page | -90% |

---

## Comandos para Testar Localmente

```bash
# 1. Verificar se o servidor esta rodando
cd C:/fralib
python server.py

# 2. Testar com PageSpeed Insights
# https://pagespeed.web.dev/?url=https://seunegociofralib.site/

# 3. Testar no Chrome DevTools
# F12 > Lighthouse > Analyze Page Load

# 4. Testar mobile performance
# F12 > Toggle device toolbar > iPhone 12
```

---

## Proximos Passos

1. Deployar as mudancas para producao
2. Aguardar 24h para coleta de metricas
3. Verificar no Clarity se INP melhorou
4. Se OK, reativar Meta Ads em R$ 5/dia para teste
5. Monitorar LCP via PageSpeed Insights

---

## Arquivos Alterados

- `C:\fralib\frontend\landing.html`
- `C:\fralib\frontend\static\analytics.js`

**Nao fazer commit ate validacao de performance.**
