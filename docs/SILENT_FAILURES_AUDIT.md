# Auditoria de Silent Failures - FraLib

**Data:** 2026-06-19
**Metodo:** skill ECC silent-failure-hunter
**Escopo:** `C:\fralib\backend\` (todos os arquivos .py)

---

## Resumo Executivo

| Categoria           | Quantidade |
|---------------------|------------|
| Total de try/except | 67         |
| CRITICOS            | 11         |
| IMPORTANTES         | 18         |
| INFORMATIVOS/OK     | 38         |

---

## Top 10 Problemas Criticos (priorizados por impacto)

### 1. `services/llm_router.py:341-344` - RESPOSTA DO LLM DESCARTADA SEM ALERTA
**Impacto:** Quando a API Gemini retorna resposta mal-formada, `text_out` fica string vazia. O chamador recebe `""` sem saber que houve problema de parsing. O pipeline pode avancar com HTML/site vazio sem qualquer indicacao de falha. **Perda de dado de output do LLM.**
```python
try:
    text_out = data["candidates"][0]["content"]["parts"][0]["text"]
except (KeyError, IndexError):
    pass   # text_out fica ""
```
**Fix:** Lancar RuntimeError no except, nao fazer pass.

---

### 2. `pipeline_orchestrator_service.py:562-563` - KEYWORD RESEARCH SILENCIADA
**Impacto:** Se `pesquisar_keywords_nicho()` lancAr qualquer excecao (API externa, timeout, bug), ela e mascarada. O site gerado tera SEO incompleto sem qualquer log. **Dado de SEO perdido.**
```python
except:
    state.keyword_research = ""
```
**Fix:** logger.error() antes de state.keyword_research = "".

---

### 3. `pipeline_orchestrator_service.py:1352-1354` - JINA INSIGHTS DESCARTADA + VARIAVEL ERRADA
**Impacto:** A variavel `e` referenced sem ter sido definida causa `NameError` em runtime. Alem disso, a excecao e totalmente silenciada. **Bug de regressao + silent data loss.**
```python
except:
    state.jina_insights = ""
logger.warning(f"[Pipeline] Jina Intel erro: {e}")   # "e" NAO existe aqui!
```
**Fix:** usar `except Exception as e:` com `logger.warning()` DENTRO do except.

---

### 4. `pipeline_orchestrator_service.py:2707-2708` - DADOS DO LEAD PERDIDOS
**Impacto:** Se `json.loads(dados)` falhar (dados_completos corrompidos no banco), fotos, reviews e total de avaliacoes sao totalmente perdidos. O site sera gerado sem reviews de clientes. **Perda de conteudo do lead.**
```python
except:
    dados = {}
```
**Fix:** usar `except (json.JSONDecodeError, TypeError)` com log.

---

### 5. `prd_cache.py:109-110` - ESCRITA DE CACHE SEM TRATAMENTO
**Impacto:** Sem try/except. Disco cheio, permissao ou diretorio invalido lancam excecao irrecuperavel. O pipeline pode continuar sem saber que o cache falhou. **Cache nunca e gravado e nao ha evidencia de falha.**
```python
with open(_cache_path(key), "w", encoding="utf-8") as f:
    json.dump(cache_entry, f, ensure_ascii=False, indent=2)
```
**Fix:** envolver em `try/except (OSError, IOError)` com `logger.warning()`.

---

### 6. `prd_cache.py:213-214` - QUALITY SCORE NUNCA E ATUALIZADO
**Impacto:** Se a leitura ou escrita do JSON falhar, o quality score nunca e atualizado. Templates ruins continuarao sendo servidos. **Feedback loop de qualidade quebrado.**
```python
except Exception:
    pass
```
**Fix:** usar `except (OSError, json.JSONDecodeError)` com log.

---

### 7. `agent_memory.py:76-80` - MEMORIA AGENTE NUNCA E PERSISTIDA
**Impacto:** Sem try/except. Qualquer erro de escrita (disco cheio, corrupcao, permissao) sube sem tratamento. O processo pode continuar achando que salvou, perdendo toda a memoria acumulada. **Perda da memoria de aprendizado do agente.**
```python
def _salvar(self):
    with open(CORE_FILE, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in self.entries], f, ensure_ascii=False, indent=2)
```
**Fix:** envolver em `try/except (OSError, IOError)`.

---

### 8. `agent_memory.py:186-189` - MEMORIA WARM NUNCA E PERSISTIDA
**Impacto:** Mesmo problema do item 7 para a memoria por nicho. Sem try/except.
```python
def _salvar_nicho(self, nicho: str, entries: list):
    nicho_file = WARM_DIR / f"{nicho}.json"
    with open(nicho_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
```
**Fix:** envolver em `try/except (OSError, IOError)`.

---

### 9. `agent_memory.py:69-74` - MEMORIA PERMANENTE PERDIDA AO CARREGAR
**Impacto:** Se o arquivo de memoria do agente estiver corrompido, ele e descartado silenciosamente e retorna `[]`. Nao ha log, nao ha backup, nao ha alerta. Toda a memoria acumulada e perdida permanentemente. **Perda irreversivel de memoria do agente.**
```python
except (json.JSONDecodeError, Exception):
    return []
```
**Fix:** fazer backup de arquivo corrupto + log antes de `return []`.

---

### 10. `api_monitor.py:63-99` - DADOS DE USO DE API PERDIDOS
**Impacto:** `print()` nao e confiavel em ambiente de producao (stdout pode nao ser capturado). Falhas de snapshot de uso da API sao perdidas sem qualquer evidencia. **Dados de monitoramento de billing perdidos.**
```python
except Exception as e:
    print(f"[DB] Erro ao salvar: {e}")
```
**Fix:** trocar `print()` por `logger.error()`.

---

## Auditoria Completa

### CRITICOS (11) - Perdem dados

| # | Arquivo | Linha | Impacto |
|---|---------|-------|---------|
| 1 | `services/llm_router.py` | 341-344 | Resposta LLM vazia retornada como valida |
| 2 | `endpoints/pipeline_orchestrator_service.py` | 562-563 | SEO do site pode estar incompleto |
| 3 | `endpoints/pipeline_orchestrator_service.py` | 1352-1354 | NameError em runtime + silent swallow |
| 4 | `endpoints/pipeline_orchestrator_service.py` | 2707-2708 | Fotos/reviews do lead perdidos |
| 5 | `endpoints/pipeline_orchestrator_service.py` | 1838-1839 | Debugging do pipeline prejudicado |
| 6 | `prd_cache.py` | 109-110 | Cache nunca e gravado |
| 7 | `prd_cache.py` | 213-214 | Feedback loop de qualidade quebrado |
| 8 | `agent_memory.py` | 76-80 | Memoria do agente perdida |
| 9 | `agent_memory.py` | 186-189 | Memoria warm perdida |
| 10 | `agent_memory.py` | 69-74 | Memoria do agente perdida sem backup |
| 11 | `api_monitor.py` | 98-99 | Dados de monitoramento perdidos |

---

### IMPORTANTES (18) - Escondem bugs, podem causar efeitos colaterais

| # | Arquivo | Linha | O que falha silenciosamente |
|---|---------|-------|----------------------------|
| 12 | `utils/google_local_scraper.py` | 252-253 | Telefone/website/fotos de estabelecimentos |
| 13 | `utils/google_local_scraper.py` | 303-304 | Rating = 0.0 para todos invalidos |
| 14 | `utils/google_local_scraper.py` | 463-464 | Reviews de blocos principais descartados |
| 15 | `utils/google_local_scraper.py` | 503-504 | Reviews em destaque descartados |
| 16 | `utils/google_local_scraper.py` | 566-567 | Website nao capturado |
| 17 | `utils/google_local_scraper.py` | 578-579 | Telefone nao capturado |
| 18 | `utils/google_local_scraper.py` | 604-605 | Horarios nao clicados |
| 19 | `utils/google_local_scraper.py` | 681-682 | Endereco nao capturado |
| 20 | `utils/google_local_scraper.py` | 718-719 | Faixa de preco ausente |
| 21 | `utils/google_local_scraper.py` | 737-738 | Modais de review nao fechados |
| 22 | `utils/google_local_scraper.py` | 763-764 | Reviews da aba nao carregados |
| 23 | `utils/google_local_scraper.py` | 776-777 | Botoes "mais" nao clicados |
| 24 | `utils/google_local_scraper.py` | 805-806 | Navegacao overview falhada |
| 25 | `utils/google_local_scraper.py` | 859-860 | Reviews heuristica descartados |
| 26 | `whatsapp_listener.py` | 547-553 | wpp_jid nao persistido |
| 27 | `whatsapp_listener.py` | 243-252 | Config de ignore contacts falha silenciosamente |
| 28 | `prd_cache.py` | 39-44 | Cache miss silenciado sem alerta |

---

### INFORMATIVOS/OK (38) - Logging ou fallback seguro

Blockquoted como OK porque tem logging adequado, fallback explicito, ou input validation esperada:

- `whatsapp_listener.py:395-398` - `_salvar_interacao`: warning logado
- `whatsapp_listener.py:421-461` - `_notificar_handoff_humano`: erro logado
- `whatsapp_listener.py:465-724` - `_processar_mensagem`: erro logado com stack trace
- `whatsapp_listener.py:620-631` - historico SDR: warning logado
- `whatsapp_listener.py:750-821` - WebSocket reconnect logic
- `whatsapp_listener.py:782-794` - Alertar disconnect: exceto vazio em notification (OK)
- `endpoints/credits_endpoints.py:544-549` - mercadopago: erro logado + marcado
- `services/pipeline_executors.py:189-190` - Jina fallback: log ANTES do except (OK - o log acontece)
- `retry_helper.py:105-108` - `log_fn` fallback dentro de retry (OK - log interno)
- `prd_cache.py:190-192` - `adaptar_resposta`: fallback para base + log presente (OK)
- `api_monitor.py:98-99` - **NAO OK** - print() em vez de logger (ja no top 10)
- Todos os blocos de `utils/google_maps_gosom.py` - parsing robusto com pass (OK para scraping)
- Todos os blocos de parsing de env/int, rating, follow-up date - fallback seguro (OK)

---

## Plano de Correcao

### Fase 1: CRITICOS - Correcao Imediata (0-2 dias)

| # | Arquivo | Linha | Acao |
|---|---------|-------|------|
| 1 | `llm_router.py` | 341-344 | lancar RuntimeError no except |
| 2 | `pipeline_orchestrator_service.py` | 562-563 | `logger.error()` antes de `state.keyword_research = ""` |
| 3 | `pipeline_orchestrator_service.py` | 1352-1354 | `except Exception as e:` com `logger.warning()` DENTRO do except |
| 4 | `pipeline_orchestrator_service.py` | 2707-2708 | `except (json.JSONDecodeError, TypeError)` com log |
| 5 | `pipeline_orchestrator_service.py` | 1838-1839 | `logger.warning()` em vez de pass |
| 6 | `prd_cache.py` | 109 | try/except (OSError, IOError) com logger |
| 7 | `prd_cache.py` | 213 | except (OSError, json.JSONDecodeError) com log |
| 8 | `agent_memory.py` | 76 | try/except (OSError, IOError) no _salvar() |
| 9 | `agent_memory.py` | 186 | try/except (OSError, IOError) no _salvar_nicho() |
| 10 | `agent_memory.py` | 73 | backup + log antes de return [] |
| 11 | `api_monitor.py` | 98 | print() -> logger.error() |

### Fase 2: IMPORTANTES - Correcao em 1 semana

- `utils/google_local_scraper.py` - 14 bare `except: pass` em sequencia: adicionar `logger.warning()` em cada um
- `whatsapp_listener.py:243-252` - adicionar `logger.warning()` no fallback de ignore contacts
- `prd_cache.py:39-44` - `logger.debug()` para cache misses recorrentes

### Fase 3: Padroes de Codificacao (novos projetos)

- **Regra 1:** nunca use bare `except:`. Sempre use `except Exception as e:` ou `except (TypeError, ValueError) as e:`.
- **Regra 2:** se voce usa `pass` ou `return None/[]` em um except, SEMPRE tenha um log/warning antes.
- **Regra 3:** qualquer escrita em disco (`open(..., "w")`) ou banco de dados dentro de um try deve ter um except correspondente com logging de erro.
- **Regra 4:** em servicos de negocio (billing, credits, pipeline), erros nunca devem ser silenciados.

---

*Auditoria realizada por silent-failure-hunter agent em 2026-06-19.*
