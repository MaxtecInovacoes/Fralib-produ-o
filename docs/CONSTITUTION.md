# FraLib Constitution

> Baseado em [GitHub Spec Kit](https://github.com/github/spec-kit). Esta constitution é o conjunto de princípios inegociáveis que guiam todas as decisões técnicas do FraLib.

**Version**: 1.0.0 | **Ratified**: 2026-06-19 | **Last Amended**: 2026-06-19

---

## Core Principles

### I. Verde Antes de Tudo (NON-NEGOTIABLE)
**Princípio**: Nada é considerado "pronto" sem passar por `bash scripts/verify_all.sh` retornando 🟢 VERDE.

- Toda mudança DEVE rodar `verify_all.sh` antes de commit
- CI/CD falha se 🟢 não for atingido
- Refatorações preservam comportamento (zero regressões em testes)
- Sem "achismo" - tudo é verificado programaticamente

### II. Sem Código Morto (NON-NEGOTIABLE)
**Princípio**: Se um módulo existe, ele é usado. Se não é usado, é deletado.

- `scripts/check_agents_alive.sh` roda em CI
- Módulos sem chamadas → candidatos a deleção
- Cobertura de testes: cada módulo público tem teste
- Documentação de "intenção futura" via SPEC, não código órfão

### III. Spec → Loop → Verde (NON-NEGOTIABLE)
**Princípio**: Toda mudança significativa começa com uma Spec, segue um Loop de implementação, e termina Verde.

- Mudanças > 100 linhas → SPEC em `docs/specs/` ANTES
- Loop: implementa → testa → lê erro → conserta → repete (máx 10 iterações)
- Tarefas pequenas e testáveis individualmente
- Critérios de aceite explícitos

### IV. PT-BR por Padrão, Código em Inglês
**Princípio**: Copy user-facing em Português Brasileiro, código/técnico em Inglês.

- Todos os textos visíveis em sites/apps: PT-BR
- Nomes de variáveis, funções, classes: inglês
- Comentários no código: inglês
- System prompts de LLM: podem ser em inglês mas output em PT-BR

### V. Modular > Monolítico
**Princípio**: Arquivos < 800 linhas. Se passou, quebre em módulos.

- Cada módulo tem responsabilidade única
- Testes isolados por módulo
- Imports claros (sem `from X import Y` sem prefixo `backend.`)
- Wrappers de compatibilidade para não quebrar código existente

---

## Technical Constraints

### Stack
- **Backend**: Python 3.13, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend builder**: Vite + React + TypeScript + Tailwind v4
- **LLM**: kpalabz (`https://api.kpalabz.com/v1`), modelos `claude-sonnet-4-6` / `claude-haiku-4-5`
- **WhatsApp**: whatsmeow (Go) com keepalive 30s
- **Banco**: PostgreSQL multi-tenant (`fralib_db` porta 5433)

### Code Standards
- Imports: sempre `from backend.X.Y import Z` (nunca absoluto)
- Type hints obrigatórios em funções públicas
- Docstrings em funções core
- Sem `print()` em produção (usar `logger`)
- Sem `except Exception:` genérico (sempre específico)

### Test Standards
- Testes para toda função pública
- E2E tests com lead fake (3 segmentos: restaurante, nutricionista, academia)
- Benchmark antes/depois para detectar regressões
- Cobertura mínima: 80% para módulos core

---

## Development Workflow

### Antes de Qualquer Mudança
1. Criar/atualizar SPEC em `docs/specs/SPEC_<nome>.md`
2. Listar critérios de aceite mensuráveis
3. Identificar arquivos afetados

### Durante Implementação
1. **UMA extração por vez** (não mexer em 5 arquivos simultaneamente)
2. Rodar `verify_all.sh` após CADA extração
3. 1 commit por extração (rollback fácil)
4. Wrappers de compatibilidade para preservar código existente

### Antes de Commit
- [ ] `verify_all.sh` retorna 🟢 ou 🟡
- [ ] `check_agents_alive.sh` não detecta novos órfãos
- [ ] Documentação atualizada (se mudou comportamento)
- [ ] Mensagem de commit descritiva

### Antes de Push para Produção
- [ ] Benchmark antes/depois (se mudou performance)
- [ ] VPS pull + restart de serviços
- [ ] Monitorar logs por 30 min

---

## Governance

### Esta Constitution:
- **Supersede** todas as outras práticas
- **Amendments** requerem: documentação + aprovação + plano de migração
- **Compliance** verificado em todo PR/review

### Regras Operacionais:
1. Se uma prática conflitar com Constitution → Constituição vence
2. Complexidade DEVE ser justificada
3. Não criar código "para o futuro" sem SPEC
4. Refatorações só com testes verdes antes

---

## Tools e Scripts Oficiais

| Script | Função | Status |
|--------|--------|--------|
| `scripts/verify_all.sh` | Juiz verde (VERDE/AMARELO/VERMELHO) | ✅ Ativo |
| `scripts/check_agents_alive.sh` | Detecta código morto | ✅ Ativo |
| `scripts/fix_imports.sh` | Corrige imports quebrados | ✅ Ativo |
| `scripts/audit_vps.sh` | Audita VPS sem mexer | ✅ Ativo |
| `scripts/benchmark_pipeline.py` | Detecta regressões | ✅ Ativo |

## Skills ECC Instaladas (Auxiliares)
- `silent-failure-hunter` - achar try/except silenciosos
- `refactor-cleaner` - quebrar monolitos
- `tdd-guide` - forçar testes antes
- `fastapi-reviewer` - revisar FastAPI
- `verification-loop` - garantir verde

---

*Esta constitution é viva. Evolui conforme o projeto cresce, sempre por consenso e com plano de migração.*
