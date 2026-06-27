# NOVA HERO MOBILE-FIRST — FraLib OS

## Copy Validada pelos Especialistas

### HEADLINE (máximo 7 palavras)
```
Você fecha.
A FraLib faz o resto.
```

### SUBHEADLINE (máximo 20 palavras)
```
A IA encontra empresas que precisam de site.
Cria o site. Manda no WhatsApp delas.
Você só fecha quem já quer contratar.
```

### CTA PRIMÁRIO
```
QUERO VER COMO FUNCIONA
```
(Leva para WhatsApp direto, não para login)

### PROVA SOCIAL (acima da dobra)
```
+2.400 leads encontrados | +180 sites criados | 97% abre mensagem
```

---

## MUDANÇAS TÉCNICAS

### 1. HERO MOBILE-FIRST
- Headline: 2 linhas curtas, máxima legibilidade
- Prova social: visível SEM scroll
- CTA WhatsApp: primeiro botão, não segundo
- Remove contraste "VOCÊ HOJE" que confunde

### 2. FORM SIMPLIFICADO
- Remove campo EMAIL (só nome + WhatsApp)
- Redireciona para WhatsApp direto após captura
- Placeholder com exemplo: "(11) 99999-9999"

### 3. WIDGET WHATSAPP FLUTUANTE
- Adiciona botão WhatsApp fixo no canto inferior direito
- Permite clique direto sem preencher form

### 4. EVENTOS PIXEL
```javascript
fbq('track', 'Lead');           // form submission
fbq('track', 'WhatsAppClick'); // botão flutuante
fbq('track', 'ViewContent');   // scroll 50%
```

---

## COMPARATIVO

| Antes | Depois |
|-------|--------|
| Headline: 11 palavras | Headline: 6 palavras |
| CTA: leva para login | CTA: WhatsApp direto |
| Form: 3 campos | Form: 2 campos |
| Prova social: embaixo | Prova social: no topo |
| Sem widget WPP | Widget WPP flutuante |
| Pixel: só PageView | Pixel: Lead + WhatsAppClick |

---

## IMPLEMENTAÇÃO

1. Modificar `hero-title` em landing.html
2. Simplificar `betaForm` (remover email)
3. Adicionar widget WhatsApp flutuante
4. Adicionar eventos pixel de conversão

---

## RESULTADO ESPERADO

| Métrica | Antes | Depois (meta) |
|---------|-------|---------------|
| Bounce | 84% | <50% |
| Scroll 50%+ | 3% | >20% |
| CTAs clicados | 0 | >5 |
