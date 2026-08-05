# PLANO DE MELHORIAS FRALIB OS

> Gerado em: 2026-05-08
> Base de código analisada: server.py, sse_endpoints.py, pipeline_endpoints.py, Franz.py, liam.py, liz.py, caio.py, theo.py, _scripts.html, _view-uti.html, _modals.html

---

## SPRINT 1 — Backend Crítico

### ITEM 1.1 — SSE logs em tempo real via PostgreSQL LISTEN/NOTIFY

**Problema:**
O sistema atual usa uma `deque` em memória (`log_queue = deque(maxlen=500)` em `sse_endpoints.py` linha 10). Quando o servidor tem múltiplos workers (PM2 com cluster mode) ou reinicia, a fila é perdida e os logs de um worker não chegam ao cliente conectado em outro worker. O endpoint `/api/logs/stream` (linha 12-35) faz polling da deque a cada 0.3s — ineficiente e não escala.

**Solução:**
Substituir a deque em memória por PostgreSQL LISTEN/NOTIFY:
1. Criar função `pg_notify('fralib_logs', payload::text)` chamada a cada `adicionar_log()`
2. No `event_generator()`, abrir conexão asyncpg e fazer `LISTEN fralib_logs`
3. Aguardar notificações com `await conn.wait_for_notify()` em vez de sleep(0.3)
4. Manter a deque apenas como buffer de fallback para reconexão (últimos 50 logs)
5. Adicionar coluna `logs` na tabela existente ou criar tabela `pipeline_logs(id, evento, mensagem, ts, user_id)` para persistência opcional

**Arquivos:**
- `/root/fralib/backend/endpoints/sse_endpoints.py` — reescrever `event_generator()` e `adicionar_log()`
- `/root/fralib/backend/database.py` — verificar se asyncpg já está disponível ou adicionar dependência
- `requirements.txt` — adicionar `asyncpg` se ausente

**Teste:**
1. Iniciar pipeline em background
2. Abrir admin, verificar que logs aparecem em tempo real no terminal mágico
3. Reiniciar servidor com `pm2 restart fralib` e confirmar que novo cliente recebe logs do pipeline em andamento
4. Verificar dot verde no `#sse-dot` (linha 2340 de `_scripts.html`)

**Risco:** médio — requer asyncpg e mudança na lógica de conexão; testar com PM2 em modo fork antes de cluster

---

### ITEM 1.2 — Franz SDR: estado sempre "intro", histórico e max_tokens

**Problema:**
Em `Franz.py` linha 254, após cada execução bem-sucedida, o estado é sempre salvo como `"estado": "intro"` — nunca avança na state machine `ESTADOS_SDR` (linhas 68-77). Isso significa que todo contato subsequente com o mesmo lead repete a mensagem de introdução em vez de avançar para `proof`, `link`, `value`, etc.

Além disso, na linha 228, `max_tokens=4000` é excessivo para uma mensagem de WhatsApp de máximo 500 caracteres (definido em `MensagemWhatsApp` linha 55). O LLM gasta tokens desnecessários.

A memória é carregada corretamente (linha 180-187) mas o `ultimo_estado` nunca é usado para selecionar o próximo estado da sequência — o prompt na linha 206 passa `ESTADO ATUAL: {ultimo_estado}` mas o LLM não tem instrução explícita de qual estado gerar em seguida.

**Solução:**
1. Criar função `proximo_estado(estado_atual: str) -> str` que avança na lista `ESTADOS_SDR`
2. No `salvar_memoria()` (linha 250-257), salvar `"estado": proximo_estado(ultimo_estado)` em vez de hardcoded `"intro"`
3. Adicionar ao `franz_INSTRUCTIONS` uma seção `## ESTADO ATUAL` que instrui o LLM a gerar mensagem adequada para o estado recebido
4. Reduzir `max_tokens=4000` para `max_tokens=600` na linha 228
5. No prompt (linha 196+), incluir histórico das últimas mensagens da memória para contexto

**Arquivos:**
- `/root/fralib/backend/agents/Franz.py` — linhas 228, 250-257, 196-213

**Teste:**
1. Executar pipeline completo para um lead
2. Verificar no banco que `sdr_stage` avança de `intro` para `proof` na segunda execução
3. Confirmar que `max_tokens=600` não trunca a mensagem (500 chars + JSON overhead)
4. Medir redução de custo de tokens via logs do `call_claude()`

**Risco:** médio — mudança no comportamento do SDR; testar com `franz_TEST_NUMBER` configurado antes de produção

---

### ITEM 1.3 — Liz: verificação Google Maps aceitar OpenStreetMap

**Problema:**
Em `liz.py` linha 190, a verificação de embed de mapa é:
```python
has_maps = "maps.google" in html or "google.com/maps" in html
```
Sites gerados pelo Liam que usam OpenStreetMap (`openstreetmap.org`, `leafletjs.com`) ou outros provedores de mapa são penalizados com `-5` no score (linha 193) mesmo tendo mapa válido. Isso causa reprovações desnecessárias.

**Solução:**
Expandir a verificação para aceitar múltiplos provedores:
```python
has_maps = any(p in html for p in [
    "maps.google", "google.com/maps",
    "openstreetmap.org", "leafletjs.com",
    "mapbox.com", "maps.googleapis.com",
    "iframe.*map", "embed.*map"
])
```
Também aceitar qualquer `<iframe>` com `src` contendo "map" via regex.

**Arquivos:**
- `/root/fralib/backend/agents/liz.py` — linhas 189-193

**Teste:**
1. Gerar site com Liam que use OpenStreetMap
2. Rodar `auditoria_tecnica(html)` e confirmar que não penaliza por mapa ausente
3. Confirmar que site sem nenhum mapa ainda recebe penalidade corretamente

**Risco:** baixo — mudança isolada em uma condição de validação

---

### ITEM 1.4 — Jina AI: adicionar API key no header das requests

**Problema:**
Em `theo.py` linhas 146 e 169, as requests para a API Jina AI são feitas sem autenticação:
```python
headers_search = {"X-Return-Format": "markdown", "X-Timeout": "15"}
headers_site   = {"X-Return-Format": "markdown", "X-Timeout": "15"}
```
Sem API key, o Jina AI usa o tier gratuito com rate limit severo (429 frequente, visto nos logs). Com API key no header `Authorization: Bearer <token>`, o rate limit é muito maior e a qualidade das respostas melhora.

**Solução:**
1. Adicionar `JINA_API_KEY` ao `.env`
2. Nos dois dicionários de headers (linhas 146 e 169), adicionar:
   ```python
   if jina_key := os.getenv("JINA_API_KEY"):
       headers_search["Authorization"] = f"Bearer {jina_key}"
       headers_site["Authorization"]   = f"Bearer {jina_key}"
   ```
3. Documentar no `.env.example`

**Arquivos:**
- `/root/fralib/backend/agents/theo.py` — linhas 144-147 e 168-170
- `/root/fralib/.env` — adicionar `JINA_API_KEY=`
- `/root/fralib/.env.example` — documentar variável

**Teste:**
1. Configurar `JINA_API_KEY` válida
2. Executar `pesquisar_referencias_jina("academia")` e confirmar status 200 sem 429
3. Verificar nos logs `[Jina AI] OK: X chars` com conteúdo maior que sem key

**Risco:** baixo — adição de header opcional; sem key o comportamento atual é mantido

---

### ITEM 1.5 — Liam: chamar fix_white_text() dentro de _sanitizar_fontes()

**Problema:**
Em `liam.py`, a função `_sanitizar_fontes()` (linha 67) define internamente a função `fix_white_text()` nas linhas 108-113, mas nunca a chama. A função termina na linha 115 com `return html` sem aplicar a correção de texto branco hardcoded (`color: #fff`, `color: #ffffff`). Isso faz com que textos brancos fixos sobrevivam ao pós-processamento e fiquem invisíveis no modo claro (light mode) do toggle dia/noite.

A função `_sanitizar_cores_light()` (linha 118) faz parte do trabalho, mas é uma função separada e pode não ser chamada no mesmo fluxo. A correção de `#fff` inline em tags de texto precisa acontecer dentro de `_sanitizar_fontes()` que é o pós-processador principal.

**Solução:**
Antes do `return html` na linha 115, adicionar a chamada que aplica `fix_white_text` via regex nas tags de texto:
```python
html = _re.sub(
    r'(<(?:p|span|li|td|th|label|small|em|strong)[^>]+style="[^"]*color\s*:\s*#(?:fff|ffffff)[^"]*"[^>]*>)',
    fix_white_text, html, flags=_re.IGNORECASE
)
return html
```

**Arquivos:**
- `/root/fralib/backend/agents/liam.py` — linha 115 (antes do `return html` em `_sanitizar_fontes()`)

**Teste:**
1. Gerar site com Liam para qualquer segmento
2. Inspecionar HTML gerado e buscar por `color: #fff` ou `color: #ffffff` em tags `<p>`, `<span>`, `<li>`
3. Confirmar que foram substituídos por `var(--color-text)`
4. Abrir site no browser, alternar entre dark/light mode e verificar que textos ficam visíveis em ambos

**Risco:** baixo — correção de pós-processamento; não afeta lógica de geração

---

### ITEM 1.6 — SSE endpoint: adicionar autenticação JWT

**Problema:**
O endpoint `GET /api/logs/stream` em `sse_endpoints.py` linha 12-13 não tem nenhuma autenticação:
```python
@router.get("/stream")
async def stream_logs():
```
Qualquer pessoa com acesso à URL pode consumir os logs do pipeline em tempo real, incluindo dados de leads (nomes, cidades, segmentos) e informações internas do sistema. O frontend em `_scripts.html` linha 2323 conecta via `new EventSource('/api/logs/stream')` sem enviar token.

**Solução:**
1. Aceitar token JWT via query param `?token=` (EventSource não suporta headers customizados):
   ```python
   @router.get("/stream")
   async def stream_logs(token: str = Query(...)):
       payload = verificar_jwt(token)  # reutilizar função de auth.py
       if not payload:
           raise HTTPException(401, "Token inválido")
   ```
2. No frontend `_scripts.html` linha 2323, passar o token:
   ```javascript
   var tok = localStorage.getItem('fralib_token');
   eventSource = new EventSource('/api/logs/stream?token=' + encodeURIComponent(tok));
   ```
3. No futuro, filtrar logs por `user_id` do token para multi-tenant

**Arquivos:**
- `/root/fralib/backend/endpoints/sse_endpoints.py` — linha 12-13
- `/root/fralib/frontend/partials/admin/_scripts.html` — linha 2323

**Teste:**
1. Tentar acessar `/api/logs/stream` sem token — deve retornar 401
2. Acessar com token válido — deve conectar e receber logs normalmente
3. Verificar que o dot verde aparece no admin após conexão autenticada

**Risco:** médio — EventSource com query param expõe token na URL/logs do servidor; aceitável para uso interno, mas documentar limitação

---

### ITEM 1.7 — Caio: timeout de validação de site de 10s para 3s

**Problema:**
Em `caio.py` linha 93, a validação de site usa `timeout=10`:
```python
response = requests.head(url, timeout=10, allow_redirects=True)
```
Com múltiplos leads sendo processados em paralelo (Caio e Alex rodam juntos via `ThreadPoolExecutor` em `pipeline_endpoints.py` linha 225), um site lento pode bloquear a thread por até 10 segundos. Com 50 leads por ciclo, isso pode adicionar minutos ao tempo total do pipeline.

**Solução:**
Reduzir para `timeout=3` e adicionar tratamento específico para `requests.exceptions.Timeout`:
```python
try:
    response = requests.head(url, timeout=3, allow_redirects=True)
    ...
except requests.exceptions.Timeout:
    return False, "Site muito lento (timeout 3s)"
except requests.exceptions.ConnectionError:
    return False, "Site inacessível"
```

**Arquivos:**
- `/root/fralib/backend/agents/caio.py` — linha 93

**Teste:**
1. Chamar `validar_site("https://httpstat.us/200?sleep=5000")` — deve retornar `False, "Site muito lento"` em ~3s
2. Chamar `validar_site("https://google.com")` — deve retornar `True, "Site valido"` normalmente
3. Medir tempo total de um ciclo de pipeline antes e depois

**Risco:** baixo — sites legítimos respondem em menos de 3s; sites lentos provavelmente têm problemas de qualquer forma

---

### ITEM 1.8 — CSRF: remover middleware vazio e endpoint /api/csrf-token

**Problema:**
Em `server.py` linhas 123-127, existe um middleware CSRF completamente vazio que não faz nada:
```python
# CSRF Middleware - desabilitado (JWT já protege todos os endpoints)
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    response = await call_next(request)
    return response
```
Este middleware adiciona overhead desnecessário a cada request. Além disso, o endpoint `GET /api/csrf-token` (linhas 151-164) gera e seta um cookie CSRF que nunca é verificado por nenhum middleware. O frontend em `_scripts.html` linhas 57-69 busca esse token e o envia no header `X-CSRF-Token` (linha 80), mas nenhum backend verifica esse header.

Todo esse código é dead code — JWT já protege os endpoints via `Depends(get_current_user)`.

**Solução:**
1. Remover o `csrf_middleware` (linhas 123-127 de `server.py`)
2. Remover o endpoint `GET /api/csrf-token` (linhas 150-164 de `server.py`)
3. Remover as funções `generate_csrf_token()` e `verify_csrf_token()` (linhas 34-40)
4. Remover as variáveis `CSRF_SECRET_KEY`, `secrets`, `hmac`, `hashlib` dos imports (linhas 12-14, 32)
5. No frontend `_scripts.html`, remover `_getCsrfToken()` (linhas 57-69) e a chamada ao CSRF no `authFetch()` (linhas 78-81)

**Arquivos:**
- `/root/fralib/server.py` — linhas 12-14, 32-40, 123-127, 150-164
- `/root/fralib/frontend/partials/admin/_scripts.html` — linhas 54-81

**Teste:**
1. Fazer POST em qualquer endpoint autenticado (ex: `/api/pipeline/iniciar`) e confirmar que funciona sem header `X-CSRF-Token`
2. Confirmar que `GET /api/csrf-token` retorna 404
3. Medir redução de latência média por request (deve ser marginal mas mensurável)

**Risco:** baixo — o middleware já estava desabilitado; remoção é limpeza de código morto

---

## SPRINT 2 — Frontend

### ITEM 2.1 — Fila: leads não qualificados/incompletos para revisão manual

**Problema:**
Leads rejeitados pelo Caio vão para a aba "DESCARTADOS PELO CAIO" na view UTI (`_view-uti.html` linha 36-44), mas não existe um fluxo claro de "aprovar para pipeline" com um único clique. O botão atual é "ENRIQUECER" que abre um formulário inline (`_scripts.html` linha 853), mas após salvar os dados enriquecidos não há botão "Aprovar para pipeline" — o usuário precisa ir manualmente iniciar o pipeline de novo.

Além disso, leads com status `capturado` (qualificados pelo Caio mas ainda não processados pelo pipeline completo) não têm uma fila visual dedicada — ficam invisíveis no admin.

**Solução:**
1. Na aba "DESCARTADOS" da view UTI, adicionar botão "✓ APROVAR PARA PIPELINE" ao lado de "ENRIQUECER"
2. Esse botão chama `POST /api/leads/{id}/aprovar-pipeline` que muda status para `capturado` e força score mínimo
3. Criar nova aba "FILA DE APROVAÇÃO" na view UTI para leads com status `incompleto` ou `descartado` que foram enriquecidos manualmente
4. Backend: novo endpoint `POST /api/leads/{id}/aprovar-pipeline` em `leads_endpoints.py`

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_view-uti.html` — adicionar aba e botão
- `/root/fralib/frontend/partials/admin/_scripts.html` — função `aprovarParaPipeline(id)`
- `/root/fralib/backend/endpoints/leads_endpoints.py` — novo endpoint

**Teste:**
1. Criar lead com status `descartado` no banco
2. Clicar em "APROVAR PARA PIPELINE" — lead deve aparecer na fila de capturados
3. Iniciar pipeline — lead deve ser processado normalmente

**Risco:** médio — requer novo endpoint e mudança de status; validar que Caio não rejeita novamente

---

### ITEM 2.2 — Fila: leads qualificados aguardando pipeline com ordem e status

**Problema:**
Quando o pipeline retorna `status: "fila_pendente"` (detectado em `pipeline_endpoints.py` linha 632-638), o frontend em `admin.html` linha 3492 mostra apenas um toast: "Há X lead(s) na fila. Processe-os primeiro." Não existe uma view que mostre quais leads estão na fila, em que ordem serão processados, e qual o status atual de cada um (capturado, em processamento, concluído).

**Solução:**
1. Criar nova seção "FILA DO PIPELINE" na view admin (entre o dashboard e a UTI)
2. Listar leads com `status IN ('capturado', 'processando')` ordenados por `criado_em ASC`
3. Mostrar: posição na fila, nome, nicho, cidade, score, status com badge colorido
4. Botão "▶ PROCESSAR AGORA" que inicia pipeline para aquele lead específico
5. Polling a cada 5s para atualizar status em tempo real
6. Backend: endpoint `GET /api/pipeline/fila` retornando leads ordenados

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_view-uti.html` — nova seção ou nova view
- `/root/fralib/frontend/partials/admin/_scripts.html` — função `carregarFilaPipeline()`
- `/root/fralib/backend/endpoints/pipeline_endpoints.py` — endpoint `GET /api/pipeline/fila`

**Teste:**
1. Capturar 3 leads sem processar
2. Abrir admin e verificar que aparecem na fila com posição 1, 2, 3
3. Clicar "PROCESSAR AGORA" no lead 2 — deve iniciar pipeline para ele
4. Verificar que status atualiza em tempo real via polling

**Risco:** baixo — feature aditiva, não altera fluxo existente

---

### ITEM 2.3 — Frontend: botão deletar lead com confirmação

**Problema:**
Não existe botão para deletar um lead no modal de lead (`_modals.html`). O modal tem botões SALVAR, REPROCESSAR, WHATSAPP e FECHAR VENDA (linhas 70-74), mas nenhum para exclusão. Usuários que querem remover leads duplicados ou inválidos precisam acessar o banco diretamente.

**Solução:**
1. Adicionar botão "🗑 DELETAR" no modal de dados do lead (`_modals.html` linha 69-74)
2. Ao clicar, mostrar `confirm()` com texto: "Deletar [nome do lead]? Esta ação não pode ser desfeita."
3. Se confirmado, chamar `DELETE /api/leads/{id}` e fechar modal, recarregar lista
4. Backend: verificar se endpoint DELETE já existe em `leads_endpoints.py`; se não, criar
5. Estilizar botão com cor vermelha/danger para indicar ação destrutiva

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_modals.html` — linha 69-74, adicionar botão
- `/root/fralib/frontend/partials/admin/_scripts.html` — função `deletarLead(id)`
- `/root/fralib/backend/endpoints/leads_endpoints.py` — verificar/criar `DELETE /api/leads/{id}`

**Teste:**
1. Abrir modal de qualquer lead
2. Clicar "DELETAR" — deve aparecer confirmação com nome do lead
3. Confirmar — lead deve sumir da lista e modal fechar
4. Cancelar — nada deve acontecer

**Risco:** médio — ação destrutiva; garantir que o endpoint DELETE verifica `user_id` para evitar que usuário delete lead de outro tenant

---

### ITEM 2.4 — Frontend: editar dados manualmente em lead incompleto

**Problema:**
O modal de lead (`_modals.html`) tem campos editáveis apenas para WhatsApp, Observações e Valor de Venda (linhas 51-67). Campos críticos como Nome, Cidade, Segmento e Telefone são somente leitura (exibidos como `briefing-value` nas linhas 33-47). Para leads incompletos ou com dados errados do Google Maps, não há como corrigir esses campos pelo admin.

**Solução:**
1. Na aba "DADOS" do modal, converter os campos Nome, Cidade, Segmento e Telefone de `<div class="briefing-value">` para `<input>` editáveis quando o lead tem status `descartado`, `incompleto` ou `capturado`
2. Adicionar lógica no `switchTab('dados')` para detectar o status e habilitar/desabilitar edição
3. O botão "SALVAR" existente (linha 70) já chama `salvarDadosLead()` — expandir o payload para incluir os novos campos
4. Backend: expandir `PUT /api/leads/{id}` para aceitar nome, cidade, segmento, telefone

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_modals.html` — linhas 31-47, converter para inputs condicionais
- `/root/fralib/frontend/partials/admin/_scripts.html` — função `salvarDadosLead()` e `abrirModal()`
- `/root/fralib/backend/endpoints/leads_endpoints.py` — expandir PUT endpoint

**Teste:**
1. Abrir modal de lead com status `descartado`
2. Verificar que campos Nome, Cidade, Segmento são editáveis
3. Alterar nome, salvar — verificar no banco que foi atualizado
4. Abrir modal de lead com status `concluido` — campos devem ser somente leitura

**Risco:** baixo — feature aditiva com controle por status

---

### ITEM 2.5 — Frontend: identificar e corrigir mensagem "unds..."

**Problema:**
Uma mensagem truncada "unds..." aparece na interface ao atualizar a página. A busca no código não encontrou a string literal "unds" nos arquivos HTML/JS do admin, sugerindo que é gerada dinamicamente — provavelmente um valor `undefined` sendo concatenado com uma string, resultando em "undefineds..." ou similar. Candidatos prováveis: função `carregarKPIs()` em `_scripts.html` linha 115 ao acessar propriedades inexistentes do objeto `status` ou `analytics`, ou o toast de `fila_pendente` em `admin.html` linha 3492 com `data.leads_na_fila` undefined.

**Solução:**
1. Adicionar `console.log` temporário em `carregarKPIs()` para logar os objetos `status` e `analytics` completos
2. Verificar se `status.cicloAtual`, `status.totalLeads` etc. podem ser `undefined` e adicionar fallback `|| 0`
3. Verificar o toast de `fila_pendente` — se `data.leads_na_fila` for undefined, o texto fica "Há undefined lead(s)"
4. Buscar no código por concatenações de string com propriedades de objeto sem verificação de null
5. Adicionar função utilitária `safeNum(val, fallback=0)` para todas as exibições numéricas

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_scripts.html` — linhas 115-157 (carregarKPIs) e linha 3492 (admin.html)
- `/root/fralib/frontend/admin.html` — linha 3490-3492

**Teste:**
1. Abrir admin com banco vazio (sem leads, sem ciclos)
2. Verificar que nenhum KPI mostra "undefined", "NaN" ou "unds"
3. Atualizar página 5 vezes e confirmar ausência da mensagem
4. Testar com pipeline em estado `fila_pendente`

**Risco:** baixo — correção defensiva de exibição

---

### ITEM 2.6 — Frontend: fix mensagem "precisa logar WhatsApp" mesmo já logado

**Problema:**
A função `verificarStatusWhatsApp()` em `_scripts.html` linha 1606 consulta `GET /api/whatsapp/status` que por sua vez chama `_get_session()` em `whatsapp_endpoints.py` linha 21. Se o serviço MeoWhats (`http://localhost:3001`) estiver lento ou retornar erro, a função retorna `{"status": "disconnected"}` (linha 36) mesmo que o WhatsApp esteja conectado. O frontend então exibe o status como DESCONECTADO.

Além disso, o status é verificado apenas no carregamento da página — se o WhatsApp desconectar e reconectar durante a sessão, o indicador não atualiza automaticamente.

**Solução:**
1. Em `whatsapp_endpoints.py`, adicionar retry com 2 tentativas antes de retornar `disconnected`
2. Aumentar timeout de `httpx.AsyncClient(timeout=5)` para `timeout=8` na linha 22
3. No frontend, adicionar polling a cada 30s para `verificarStatusWhatsApp()` em vez de verificar só no load
4. Adicionar cache de 10s no backend para evitar spam de requests ao MeoWhats
5. Distinguir entre "desconectado" (sessão não existe) e "erro de conexão" (MeoWhats inacessível) — mostrar mensagens diferentes no frontend

**Arquivos:**
- `/root/fralib/backend/endpoints/whatsapp_endpoints.py` — linhas 21-28, 34-42
- `/root/fralib/frontend/partials/admin/_scripts.html` — função `verificarStatusWhatsApp()` e DOMContentLoaded

**Teste:**
1. Com WhatsApp conectado, reiniciar MeoWhats brevemente — status não deve mudar para DESCONECTADO imediatamente
2. Desconectar WhatsApp de verdade — status deve mudar para DESCONECTADO em até 30s
3. Reconectar — status deve voltar para CONECTADO automaticamente

**Risco:** baixo — melhoria de UX sem alterar lógica de negócio

---

### ITEM 2.7 — Design system: auditar e unificar fontes, botões e cores

**Problema:**
O projeto tem três páginas principais (`landing.html`, `login.html`, `admin.html`) que foram desenvolvidas em momentos diferentes e usam estilos inconsistentes. O admin usa variáveis CSS `--fl-*` (ex: `--fl-font-brand`, `--fl-purple`), mas landing e login podem usar valores hardcoded. Botões têm estilos inline espalhados pelo código (ex: `_modals.html` linhas 70-74 com `background:rgba(16,185,129,0.15);border:1px solid #10b981`).

**Solução:**
1. Criar arquivo `/root/fralib/frontend/css/design-tokens.css` com todas as variáveis CSS do sistema
2. Auditar `landing.html`, `login.html` e `admin.html` — listar todas as fontes, cores e tamanhos de botão usados
3. Criar classes utilitárias `.btn-primary`, `.btn-danger`, `.btn-ghost` no design-tokens.css
4. Substituir estilos inline de botões nos modais por classes
5. Garantir que as três páginas importam o mesmo `design-tokens.css`
6. Documentar paleta: primary (#9333ea), accent (#a855f7), success (#10b981), danger (#ef4444), warning (#f59e0b)

**Arquivos:**
- `/root/fralib/frontend/css/design-tokens.css` — criar
- `/root/fralib/frontend/landing.html` — auditar e atualizar imports
- `/root/fralib/frontend/login.html` — auditar e atualizar imports
- `/root/fralib/frontend/partials/admin/_modals.html` — substituir estilos inline por classes

**Teste:**
1. Abrir as três páginas e verificar visualmente que fontes e botões são consistentes
2. Alternar entre dark/light mode no admin e confirmar que variáveis funcionam
3. Validar no Chrome DevTools que não há estilos inline conflitantes

**Risco:** baixo — mudança visual; fazer em branch separado e revisar antes de merge

---

### ITEM 2.8 — Onboarding: tour interativo para novos usuários (5 passos)

**Problema:**
Novos usuários que acessam o admin pela primeira vez não têm orientação sobre como usar o sistema. A função `verificarOnboarding()` já existe (chamada na linha 1601 de `_scripts.html`), mas não foi implementada — é apenas um placeholder. Sem onboarding, usuários ficam perdidos e não descobrem funcionalidades como o terminal mágico, a UTI, ou como iniciar o pipeline.

**Solução:**
Implementar tour de 5 passos usando highlight + tooltip posicionado:
1. Passo 1: "Configure seu nicho e cidade aqui" → aponta para os campos de configuração do pipeline
2. Passo 2: "Clique em INICIAR para rodar o pipeline completo" → aponta para botão INICIAR
3. Passo 3: "Acompanhe os logs em tempo real aqui" → aponta para o terminal mágico
4. Passo 4: "Leads com problemas ficam na UTI" → aponta para aba UTI
5. Passo 5: "Clique em qualquer lead para ver detalhes e conversa" → aponta para tabela de leads

Implementar em JS puro (sem biblioteca externa) com overlay escuro e tooltip posicionado via `getBoundingClientRect()`. Salvar `onboarding_completo: true` no `localStorage` para não repetir.

**Arquivos:**
- `/root/fralib/frontend/partials/admin/_scripts.html` — implementar `verificarOnboarding()` e `iniciarTour()`
- `/root/fralib/frontend/css/admin.css` ou inline — estilos do tour

**Teste:**
1. Limpar localStorage e abrir admin — tour deve iniciar automaticamente
2. Navegar pelos 5 passos — cada tooltip deve apontar para o elemento correto
3. Fechar tour no meio — não deve reiniciar no próximo acesso
4. Testar em mobile (320px) — tooltips não devem sair da tela

**Risco:** baixo — feature aditiva em JS puro; não afeta funcionalidade existente

---

## SPRINT 3 — Inteligência e Qualidade

### ITEM 3.1 — Brain/feedback: salvar o que funcionou e Franz consultar sdr_learning

**Problema:**
Quando um lead converte (status muda para `vendido` via botão "FECHAR VENDA" no modal), nenhuma informação sobre o que funcionou é salva para aprendizado futuro. O Franz sempre gera mensagens do zero sem considerar padrões de sucesso anteriores. O módulo `brain.py` já tem uma função `feedback_cliente` importada em `Franz.py` linha 13, mas não é chamada em nenhum lugar do fluxo de conversão.

**Solução:**
1. Criar tabela `sdr_learning` no banco:
   ```sql
   CREATE TABLE sdr_learning (
     id TEXT PRIMARY KEY,
     lead_segmento TEXT,
     lead_tier TEXT,
     estrategia TEXT,
     mensagem_texto TEXT,
     estado_conversao TEXT,
     converteu BOOLEAN,
     criado_em TEXT
   );
   ```
2. No endpoint `POST /api/leads/{id}/fechar-venda` (ou onde o status muda para `vendido`), chamar `salvar_aprendizado(lead, mensagem_usada, converteu=True)`
3. Quando um lead é descartado/perdido, chamar `salvar_aprendizado(lead, mensagem_usada, converteu=False)`
4. Em `Franz.py`, antes de montar o prompt (linha 196), consultar `sdr_learning` para o mesmo `segmento` e `tier` e incluir os 3 melhores exemplos no contexto
5. Implementar `brain.py` com funções `salvar_aprendizado()` e `buscar_exemplos_sucesso(segmento, tier, limit=3)`

**Arquivos:**
- `/root/fralib/backend/agents/brain.py` — implementar funções de aprendizado
- `/root/fralib/backend/agents/Franz.py` — linha 196, adicionar consulta ao sdr_learning
- `/root/fralib/backend/endpoints/leads_endpoints.py` — chamar salvar_aprendizado no fechar-venda
- `/root/fralib/backend/database.py` — criar tabela sdr_learning no `inicializar_database()`

**Teste:**
1. Fechar venda de um lead — verificar que registro aparece em `sdr_learning` com `converteu=True`
2. Executar Franz para lead do mesmo segmento — verificar que o prompt inclui exemplos de sucesso
3. Verificar que mensagens geradas para segmentos com histórico são diferentes das sem histórico

**Risco:** médio — requer nova tabela e mudança no fluxo de conversão; testar que não quebra o pipeline existente

---

### ITEM 3.2 — Fila persistente: tabela pipeline_queue e retomar jobs no startup

**Problema:**
Quando o servidor reinicia (PM2 restart, deploy, crash), todos os pipelines em execução são perdidos. O `lifespan` em `server.py` linha 57-68 apenas reseta `rodando=false` e `pausado=false` na tabela `pipeline_state`, mas não retoma os jobs interrompidos. Leads que estavam sendo processados ficam com status `processando` ou `capturado` para sempre, sem nunca serem concluídos.

**Solução:**
1. Criar tabela `pipeline_queue`:
   ```sql
   CREATE TABLE pipeline_queue (
     id TEXT PRIMARY KEY,
     user_id INTEGER,
     config TEXT,  -- JSON com segmento, cidade, quantidade
     status TEXT DEFAULT 'pendente',  -- pendente, rodando, concluido, erro
     criado_em TEXT,
     iniciado_em TEXT,
     concluido_em TEXT,
     erro TEXT
   );
   ```
2. No `POST /api/pipeline/iniciar`, inserir registro na `pipeline_queue` antes de iniciar o background task
3. No `lifespan` de `server.py`, após resetar `pipeline_state`, buscar jobs com `status='rodando'` na `pipeline_queue` e recolocá-los em background tasks
4. Ao concluir ou falhar o pipeline, atualizar o status na `pipeline_queue`
5. Expor `GET /api/pipeline/queue` para o frontend mostrar histórico de execuções

**Arquivos:**
- `/root/fralib/backend/database.py` — criar tabela `pipeline_queue`
- `/root/fralib/server.py` — lifespan (linhas 57-68), adicionar retomada de jobs
- `/root/fralib/backend/endpoints/pipeline_endpoints.py` — inserir/atualizar na queue, novo endpoint GET

**Teste:**
1. Iniciar pipeline, matar servidor no meio (`pm2 restart fralib`)
2. Verificar que ao reiniciar, o pipeline retoma automaticamente
3. Verificar que `pipeline_queue` tem registro com status atualizado
4. Testar que dois pipelines simultâneos não são iniciados para o mesmo usuário

**Risco:** alto — mudança no startup do servidor; testar exaustivamente em staging antes de produção; garantir idempotência (não processar lead já concluído)

---

### ITEM 3.3 — Leads reservados: UI mostrando quais leads pertencem a qual usuário

**Problema:**
O sistema é multi-tenant (cada usuário tem seu `user_id` nos leads), mas não existe nenhuma UI que mostre essa informação. Em um cenário com múltiplos usuários no mesmo plano ou conta compartilhada, não é possível saber quais leads foram capturados por qual usuário. Além disso, não existe mecanismo de "reserva" — dois usuários poderiam capturar o mesmo lead simultaneamente.

**Solução:**
1. Adicionar coluna `reservado_por` (user_id) e `reservado_em` (timestamp) na tabela `leads`
2. No início do pipeline (fase Hunter), marcar o lead como reservado para o `user_id` atual por 30 minutos
3. No admin, na tabela de leads, adicionar coluna "Usuário" mostrando o email/nome do dono do lead
4. Para admins (plano `admin`), mostrar todos os leads com indicação do usuário dono
5. Criar endpoint `GET /api/admin/leads-por-usuario` que retorna leads agrupados por usuário
6. Na view de leads, adicionar filtro "Meus leads" / "Todos os leads" (visível apenas para admins)

**Arquivos:**
- `/root/fralib/backend/database.py` — adicionar colunas `reservado_por`, `reservado_em`
- `/root/fralib/backend/endpoints/pipeline_endpoints.py` — marcar reserva no início do Hunter
- `/root/fralib/backend/endpoints/leads_endpoints.py` — novo endpoint admin
- `/root/fralib/frontend/partials/admin/_scripts.html` — adicionar coluna usuário na tabela de leads e filtro admin

**Teste:**
1. Criar dois usuários e executar pipeline com cada um
2. Verificar que leads aparecem com o usuário correto na tabela
3. Verificar que usuário A não vê leads do usuário B (a menos que seja admin)
4. Testar reserva: iniciar pipeline com usuário A para "Academia em SP" — usuário B não deve capturar o mesmo lead por 30 minutos

**Risco:** médio — requer migração de schema (adicionar colunas); usar `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para compatibilidade com banco existente

---

## RESUMO DE PRIORIDADES

| Item | Impacto | Esforço | Prioridade |
|------|---------|---------|------------|
| 1.2 Franz estado/tokens | Alto | Baixo | URGENTE |
| 1.7 Caio timeout 3s | Alto | Baixo | URGENTE |
| 1.5 Liam fix_white_text | Alto | Baixo | URGENTE |
| 1.3 Liz OpenStreetMap | Médio | Baixo | ALTA |
| 1.4 Jina API key | Médio | Baixo | ALTA |
| 1.8 CSRF cleanup | Baixo | Baixo | ALTA |
| 1.1 SSE PostgreSQL | Alto | Alto | MÉDIA |
| 1.6 SSE auth JWT | Médio | Médio | MÉDIA |
| 2.3 Deletar lead | Médio | Baixo | ALTA |
| 2.5 Fix "unds..." | Médio | Baixo | ALTA |
| 2.6 Fix WhatsApp status | Médio | Baixo | ALTA |
| 2.4 Editar lead incompleto | Alto | Médio | MÉDIA |
| 2.1 Fila aprovação | Alto | Médio | MÉDIA |
| 2.2 Fila visual | Alto | Médio | MÉDIA |
| 2.7 Design system | Baixo | Alto | BAIXA |
| 2.8 Onboarding tour | Médio | Médio | BAIXA |
| 3.2 Fila persistente | Alto | Alto | MÉDIA |
| 3.1 Brain/feedback | Alto | Alto | BAIXA |
| 3.3 Leads reservados | Médio | Alto | BAIXA |

## ORDEM DE EXECUÇÃO RECOMENDADA

Sprint 1 (semana 1): 1.8 → 1.7 → 1.5 → 1.3 → 1.4 → 1.2 → 1.6 → 1.1

Sprint 2 (semana 2): 2.5 → 2.6 → 2.3 → 2.4 → 2.1 → 2.2 → 2.7 → 2.8

Sprint 3 (semana 3): 3.2 → 3.1 → 3.3
