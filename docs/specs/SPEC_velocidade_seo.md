# SPEC: Aceleração de Velocidade + SEO

**Status:** Draft
**Data:** 2026-06-19
**Baseado em:** Validação ECC + análise do código FraLib

---

## 🎯 OBJETIVO

Acelerar o pipeline FraLib (25min → ~5min) e melhorar SEO/loading (score 70 → 90+) **SEM** migrar para Next.js.

---

## 📊 DIAGNÓSTICO ATUAL

| Etapa | Tempo atual | Gargalo |
|-------|-------------|----------|
| Caio + Jina + Nicho (sequenciais) | ~10 min | 3 calls LLM |
| LLM gera código (Vite+React) | ~15 min | Streaming não implementado |
| npm install | 30-180s | Sem cache |
| Vite build | 10-120s | OK |
| Deploy | ~5s | OK |

---

## ✅ MUDANÇAS (em ordem de impacto)

### 1. **Cache de node_modules** (1h)
- Salvar `/var/cache/fralib/node_modules_v6.tar.gz` após primeiro build
- Antes de cada build: extrair cache → economiza 30-180s
- **Ganho:** ~3-5min → ~10s por site

### 2. **Paralelizar Caio + Jina** (1h)
- Hoje: `pipeline_phase_helpers.py` executa sequencial
- Novo: `asyncio.gather()` rodar Caio e Jina em paralelo
- Nicho depois (depende dos dois)
- **Ganho:** ~10min → ~3min

### 3. **Streaming do Builder** (30min)
- Hoje: espera resposta completa do LLM (até 60s)
- Novo: começar a escrever arquivos enquanto LLM ainda gera
- **Ganho:** perceived latency -50%

### 4. **Pre-render com vite-plugin-prerender** (1h)
- Adicionar plugin que gera HTML estático no build
- Google vê HTML completo (não SPA vazio)
- **Ganho SEO:** indexação +30%

### 5. **Cache de Design Director** (30min)
- Hoje: 1 call LLM por site
- Novo: cache por nicho/cidade (24h TTL)
- **Ganho:** 5s → 0.5s em cache hit

### 6. **Compressão + Cache HTTP** (já tem Nginx?)
- Verificar gzip/brotli no Nginx
- Adicionar headers Cache-Control para assets
- **Ganho:** -30% tempo de carregamento

### 7. **Lazy load de imagens** (já tem?)
- Verificar se `loading="lazy"` está em todas as `<img>`
- **Ganho:** First contentful paint -20%

---

## 📈 RESULTADO ESPERADO

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tempo por site | 25 min | **~5 min** |
| SEO indexação | 70-85 | **90+** |
| Lighthouse score | 70-85 | **90+** |
| First contentful paint | 2-3s | **0.8-1.2s** |
| Tempo de carregamento | 2-3s | **<1s** |

---

## 🎯 PRIORIDADE

| # | Ação | Esforço | Ganho | Prioridade |
|---|------|---------|-------|------------|
| 1 | Cache node_modules | 1h | 3-5min | 🔴 ALTA |
| 2 | Paralelizar Caio+Jina | 1h | 7min | 🔴 ALTA |
| 3 | Pre-render Vite | 1h | SEO 30% | 🟡 MÉDIA |
| 4 | Cache Design Director | 30min | 5s | 🟡 MÉDIA |
| 5 | Streaming Builder | 30min | UX | 🟢 BAIXA |
| 6 | Lazy load imagens | 30min | 20% | 🟢 BAIXA |
| 7 | Compressão Nginx | 30min | 30% | 🟢 BAIXA |

**Total:** ~5 horas de trabalho
**Ganho total:** 25min → ~5min (5x speedup)

---

## 🚫 FORA DE ESCOPO

- ❌ Migrar para Next.js (não vale a pena)
- ❌ SSR (não precisamos para landing pages)
- ❌ Mudança de LLM provider
- ❌ Mudança de banco de dados

---

## ✅ CRITÉRIOS DE ACEITE

- [ ] Tempo de build < 5min (medido com benchmark)
- [ ] Cache de node_modules funcional (segundo build < 30s)
- [ ] Paralelização sem race conditions
- [ ] Pre-render gera HTML completo
- [ ] Lighthouse score > 90
- [ ] verify_all.sh continua 🟢
- [ ] VPS com mesma performance

---

## 🛡️ SEGURANÇA

- Cada mudança testada com 1 lead antes
- Backup do pipeline atual antes de mudar
- Rollback plan documentado
- Monitorar nas primeiras 24h

---

## 📋 VALIDAÇÃO FINAL

```bash
# Medir tempo ANTES
time python -m backend.scripts.benchmark_pipeline

# Aplicar mudanças
# Medir tempo DEPOIS
time python -m backend.scripts.benchmark_pipeline

# Lighthouse no site gerado
lighthouse https://seusite.com --view
```

---

*Atualizado em: 2026-06-19*