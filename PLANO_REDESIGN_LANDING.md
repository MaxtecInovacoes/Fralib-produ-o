# Plano de Redesign Baseado em Dados

## Contexto
- User rejeitou landing2.html por ter "muita animação"
- Quer: estilo openclaw.ai (limpo, geométrico, minimal) + reordenar blocos por psicologia de conversão
- Precisamos primeiro entender ONDE os usuários saem para não fazer o mesmo erro

## O que Descobrimos

### 1. Tracking Atual (Gap Analysis)
✅ **O que existe**:
- `fralib-tracker.js` com eventos básicos: pageview, click, form submit
- Meta Pixel, Google Analytics IDs no .env
- Eventos em landing2.html: CTA clicks, form submissions, plan clicks

❌ **O que falta (CRÍTICO)**:
- **Scroll depth tracking**: Não sabemos onde os usuários abandonam!
- **Heatmap**: Não sabemos onde eles clicam/olham
- **Eventos de saída por seção**: Não sabemos qual seção faz mais gente sair
- **Funil de conversão**: Não temos dados de: visit → scroll → CTA → form submit → payment
- **Backend endpoint**: `/api/track/landing` não existe

### 2. Eye-Tracking Insights
- **Padrão Z**: Topo-esquerda → topo-direita → diagonal baixo-esquerda → baixo-direita
- **50% rolam até a metade, 25% chegam ao final**
- **Abandono crítico**: 50-75% scroll (metade até 3/4 da página)
- **H1**: Topo-esquerdo (2-3x mais atenção)
- **CTA primário**: Final do caminho Z (acima da dobra)
- **Pricing**: Acima da dobra converte 12-18% melhor

### 3. Psicologia de Cores
- **FraLib palette**: Roxo (#7B5CFF - CTA), Ciano (superfícies), Ouro (decorativo)
- **Regra 60-30-10**: 60% fundo neutro, 30% secundário, 10% acento
- **Contraste WCAG**: CTA precisa de 3:1 vs fundo, 4.5:1 vs texto
- **Cores brasileiras**: Verde/amarelo evocam identidade nacional

## Plano de Ação (3 Fases)

### Fase 1: Implementar Tracking COMPLETO (1 dia)
**Objetivo**: Saber EXATAMENTE onde os usuários saem

1. **Adicionar scroll depth tracking**
   - Monitorar: 25%, 50%, 75%, 90% scroll
   - Evento: `scroll_depth_{percentage}`
   - Saber qual seção está no viewport quando abandonam

2. **Implementar heatmap via Hotjar/Clarity**
   - Verificar se já tem conta
   - Se não, criar conta free
   - Adicionar script em landing2.html

3. **Adicionar eventos de saída por seção**
   - Quando usuário sai, registrar qual seção estava visível
   - Evento: `exit_from_section_{section_id}`

4. **Criar endpoint backend `/api/track/landing`**
   - Receber eventos do fralib-tracker.js
   - Logar em arquivo para análise

5. **Deployar e coletar dados por 7 dias**
   - Rodar landing2.html no ar com novo tracking
   - Esperar 100+ visitors para ter amostra significativa

### Fase 2: Redesign Baseado em Dados (2-3 dias)
**Objetivo**: Remodelar landing2 com base nos dados da Fase 1

1. **Analisar onde os usuários saem**
   - Se 50% saem antes do pricing → mover pricing para cima
   - Se 75% não chegam ao FAQ → remover ou condensar FAQ
   - Se abandonam no "Como Funciona" → simplificar essa seção

2. **Reordenar blocos pelo padrão Z + conversão**
   ```
   Nova ordem proposta:
   1. Nav
   2. Hero (H1 topo-esquerda)
   3. Prova social (logo após CTA hero)
   4. **Pricing (acima da dobra!)**
   5. Problema (2 colunas, não 4)
   6. Como Funciona (4-1 simplificado)
   7. Nichos
   8. Stack/Features (2x3 grid)
   9. 5 Fontes de Receita
   10. Demo Video
   11. Depoimentos (reais + números)
   12. Comparação visual
   13. Timeline 7 dias
   14. Quem está por trás
   15. FAQ (condensado)
   16. CTA Final + Beta Form
   17. Footer
   ```

3. **Implementar estilo openclaw.ai**
   - Remover: particles, orbs, snake-card, parallax, glassmorphism, scroll-teller, shimmer, rainbow border, mesh-bg, blur reveal, pulsing glows, gradient text
   - Manter: FraLib palette, copy v3, design tokens
   - Adicionar: tipografia maior (H1 64px), mais whitespace, cards simples com bordas finas

4. **Aplicar psicologia de cores**
   - CTA primário: roxo com contraste 4.5:1
   - Superfícies: ciano (30% da viewport)
   - Destaques: ouro (gradientes sutis, não sobreusados)

### Fase 3: Teste A/B e Otimização (1 semana)
**Objetivo**: Validar se o novo layout converte melhor

1. **Criar versão B (versão atual com tracking)**
   - Manter landing2.html como versão B
   - Versão A: nova landing com tracking

2. **Rodar teste A/B com Google Optimize**
   - 50% para versão A, 50% para B
   - Medir: bounce rate, scroll depth, CTA clicks, form submissions

3. **Analisar resultados**
   - Se versão A converte 15%+ melhor → manter
   - Se versão B ainda converte melhor → voltar ao desenho anterior

4. **Iterar com base nos dados**
   - Otimizar elementos que não performaram
   - Aumentar CTA se necessário

## Recursos Necessários
- Hotjar/Clarity account (free tier ok)
- Google Optimize (gratuito)
- 7 dias para coleta de dados
- 1-2 dias para implementação

## Próximos Passos Imediatos
1. **Criar endpoint backend de tracking**
2. **Adicionar scroll depth tracking ao fralib-tracker.js**
3. **Implementar Hotjar/Clarity**
4. **Deployar e esperar dados**
5. **Só depois: começar o redesign**

## Checklist de Risco
- [ ] Se não tivermos dados em 7 dias → estender coleta
- [ ] Se Hotjar não der dados → tentar Clarity
- [ ] Se endpoint backend falhar → usar arquivo de log local
- [ ] Se teste A/B não for significativo → aumentar amostra