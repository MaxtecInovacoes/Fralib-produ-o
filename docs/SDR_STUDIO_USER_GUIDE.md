# SDR Studio - Guia do Usuario (SuperAdmin)

> Como usar o painel **SDR Studio** dentro do `/superadmin` para editar os
> prompts do Franz SDR em tempo real.

---

## 1. O que e o SDR Studio

E uma interface visual (dentro do SuperAdmin) que permite:

1. **Ver e editar** os 3 arquivos de prompt que definem a personalidade do Franz
2. **Testar** as mudancas num chat de teste antes de irem para producao
3. **Versionar** cada save (rollback em 1 clique)
4. **Publicar** com audit log

---

## 2. Como acessar

1. Acesse `https://seunegociofralib.site/superadmin`
2. Logue com o email superadmin (`dezigpi@gmail.com`)
3. Clique na aba **SDR Studio** (entre Playground e Alertas)

Voce vera:

- **Esquerda:** chat de teste (stage / segmento / cidade / modelo + log)
- **Direita:** editor com 3 abas (Design System / User System / RAG)

No topo do editor, uma **badge** indica o modo atual:

- ESPELHO ATIVO - mudancas no Studio refletem no WhatsApp real
- MODO RASCUNHO - mudancas NAO afetam o WhatsApp real

---

## 3. As 3 camadas de prompt

### Design System (`FRANZ_PERSONA.md`)

**Quem e o Franz.** Identidade, tom, regras de linguagem, politica comercial.
Exemplo de conteudo:
- "Voce e Franz, o SDR consultativo da FraLib"
- "Responda sempre em portugues brasileiro"
- "Max 3 linhas, 1 pergunta, 1 emoji"

**Quando editar:** quando quiser mudar **quem o Franz e** (tom, postura,
limites, regras comerciais como preço).

### User System (`FRANZ_PLAYBOOK.md`)

**O que o Franz faz em cada stage** (hook, qualify, pain, amplify, tease,
proof, reveal, feedback, close). Cada stage tem goal + rules + exemplo.

**Quando editar:** quando quiser mudar **como o Franz conduz a conversa**
(ex: "no hook, mencionar o Google Maps antes de perguntar" ou "no close,
oferecer 12x sem perguntar").

### RAG (`FRANZ_RAG.md`)

**Conhecimento, padroes de mercado, objeções, winning patterns.** Vem de
`backend/agents/rag_knowledge/*.md` + `bryan_knowledge/*.md`.

**Quando editar:** quando quiser ensinar o Franz sobre **novos padroes de
mercado, objeções comuns, ou casos especificos** (ex: "Academia em cidade
pequena (<50k habitantes) tem ticket medio 30% menor").

---

## 4. Workflow recomendado

### 4.1 Editar um prompt

1. Clique na aba correspondente (ex: **User System**)
2. **Edite** o texto da textarea (canto inferior direito da aba)
3. Clica **Aplicar**
4. Vera toast "Aplicado: user_system"
5. Badge "nao salvo" some

### 4.2 Testar antes de publicar

1. Na coluna esquerda (chat), configure:
   - **Stage**: hook, qualify, pain, etc
   - **Segmento**: academia, restaurante, loja, etc
   - **Cidade**: nome da cidade
   - **Modelo**: sonnet (recomendado) ou opus (mais inteligente, mais caro)
2. Digite a mensagem do lead no input (ex: "oi, td bem?")
3. Clique **Enviar** (resposta unica) ou **Stream** (efeito de digitacao)
4. Verifique:
   - Tom: parece humano?
   - Tamanho: ate 3 linhas?
   - 1 pergunta por mensagem?
   - Sem revelar preço antes de qualify?
5. Se precisar de mais rounds, continue conversando

### 4.3 Publicar (vai para producao)

1. Apos validar, clique **Publicar**
2. Confirma no modal
3. Toast: "Publicado - auditoria registrada"
4. A proxima mensagem real de lead no WhatsApp ja usa o novo prompt

**Importante:** Publicar salva o estado em `audit_log` mas NAO forca o
worker `fralib-franz` a recarregar o modulo Python. Em producao, o WhatsApp
real so pega o novo prompt se:
- O flag `FRALIB_SDR_PROMPTS_FROM_MD=1` esta setado na VPS
- O worker `fralib-franz` e reiniciado, OU o modulo do Franz e
  reimportado (acontece automaticamente a cada N minutos via watchdog)

### 4.4 Rollback (desfazer mudancas)

1. Clique **Historico** no canto inferior direito
2. Modal abre com lista de versoes (data, autor, nota)
3. Clique **Restaurar** na versao desejada
4. Confirma - o estado atual vira uma nova versao (backup)
5. A versao escolhida e restaurada no arquivo

---

## 5. Cenarios comuns

### "O Franz ta respondendo de forma robotica"

-> Vai em **Design System** -> aumenta enfase em tom humano
-> Exemplo: "Tom de WhatsApp real, com girias leves. NUNCA pareca chatbot"

### "O Franz nao ta perguntando sobre captacao"

-> Vai em **User System** -> aba **STAGE: qualify**
-> Adiciona regra: "SEMPRE pergunte: 'Como voces captam clientes hoje?'"

### "O Franz revela preco logo de cara"

-> Vai em **User System** -> **STAGE: hook** ou **qualify**
-> Adiciona regra: "NUNCA revele preco antes de stage=close"

### "O Franz fala coisa errada sobre [segmento]"

-> Vai em **RAG** -> adicione a verdade factual
-> Exemplo: "Academia pequena tem 30-50 alunos. Media 100-300. Grande 500+"

### "O Franz nao avanca stage mesmo com lead engajado"

-> **NAO EDITE O STUDIO.** Isso e bug. Vai em `/docs/SDR_BUGS_FIXED.md`
-> Bug #1 (stage-loop) ja foi corrigido. Se voltou, e regressao.

---

## 6. Limites e cuidados

- **100KB** por camada (validado backend)
- **Sem preview de mobile** - chat e desktop-only
- **Botao "Stream"** exige WebKit/Chromium recente (Chrome, Edge, Safari 14+)
- **Backup automatico:** antes de cada save, o estado atual vira versao
- **Nao edite 2 abas ao mesmo tempo** sem salvar - pode perder mudancas

---

## 7. FAQ

**P: Posso deletar uma versao antiga do historico?**
R: Nao diretamente pela UI. Via SQL:
```sql
DELETE FROM sdr_studio_versions WHERE id = <N>;
```

**P: Como sei se minha mudanca esta em producao?**
R: Va em `https://seunegociofralib.site/superadmin` -> **API Keys** ->
procure por `FRALIB_SDR_PROMPTS_FROM_MD` na secao env. Se `1`, esta ativo.

**P: O Franz continua com o prompt antigo mesmo apos Publicar. Por que?**
R: Worker `fralib-franz` tem cache do modulo Python. Reinicie:
```bash
ssh root@187.77.37.72 "systemctl restart fralib-franz"
```

**P: Posso ter 2 superadmins editando ao mesmo tempo?**
R: Sim, mas o ultimo que clica Aplicar ganha (sem lock). O auto-backup
garante que voce nao perde trabalho de outro admin.

---

## 8. Suporte

- Documentacao tecnica: `docs/SDR_STUDIO_10_10.md`
- Bugs corrigidos: `docs/SDR_BUGS_FIXED.md`
- Testes: `scripts/test_sdr_fsm.py`
- Plano original: `docs/FRANZ_SDR_ENTERPRISE_PLAN.md`

Para issues urgentes, checar logs:
```bash
ssh root@187.77.37.72 "journalctl -u fralib-api --since '10 minutes ago' --no-pager | tail -30"
```