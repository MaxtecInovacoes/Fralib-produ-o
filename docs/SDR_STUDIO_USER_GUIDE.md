# SDR Studio — Guia do Usuário (SuperAdmin)

> Como usar o painel **SDR Studio** dentro do `/superadmin` para editar os
> prompts do Franz SDR em tempo real.

---

## 1. O que é o SDR Studio

É uma interface visual (dentro do SuperAdmin) que permite:

1. **Ver e editar** os 3 arquivos de prompt que definem a personalidade do Franz
2. **Testar** as mudanças num chat de teste antes de irem para produção
3. **Versionar** cada save (rollback em 1 clique)
4. **Publicar** com audit log

---

## 2. Como acessar

1. Acesse `https://seunegociofralib.site/superadmin`
2. Logue com o email superadmin (`dezigpi@gmail.com`)
3. Clique na aba **SDR Studio** (entre Playground e Alertas)

Você verá:

- **Esquerda:** chat de teste (stage / segmento / cidade / modelo + log)
- **Direita:** editor com 3 abas (Design System / User System / RAG)

No topo do editor, uma **badge** indica o modo atual:

- 🟢 **ESPELHO ATIVO** — mudanças no Studio refletem no WhatsApp real
- 🟡 **MODO RASCUNHO** — mudanças NÃO afetam o WhatsApp real

---

## 3. As 3 camadas de prompt

### Design System (`FRANZ_PERSONA.md`)

**Quem é o Franz.** Identidade, tom, regras de linguagem, política comercial.
Exemplo de conteúdo:
- "Você é Franz, o SDR consultativo da FraLib"
- "Responda sempre em português brasileiro"
- "Máx 3 linhas, 1 pergunta, 1 emoji"

**Quando editar:** quando quiser mudar **quem o Franz é** (tom, postura,
limites, regras comerciais como preço).

### User System (`FRANZ_PLAYBOOK.md`)

**O que o Franz faz em cada stage** (hook, qualify, pain, amplify, tease,
proof, reveal, feedback, close). Cada stage tem goal + rules + exemplo.

**Quando editar:** quando quiser mudar **como o Franz conduz a conversa**
(ex: "no hook, mencionar o Google Maps antes de perguntar" ou "no close,
oferecer 12x sem perguntar").

### RAG (`FRANZ_RAG.md`)

**Conhecimento, padrões de mercado, objeções, winning patterns.** Vem de
`backend/agents/rag_knowledge/*.md` + `bryan_knowledge/*.md`.

**Quando editar:** quando quiser ensinar o Franz sobre **novos padrões de
mercado, objeções comuns, ou casos específicos** (ex: "Academia em cidade
pequena (<50k habitantes) tem ticket médio 30% menor").

---

## 4. Workflow recomendado

### 4.1 Editar um prompt

1. Clique na aba correspondente (ex: **User System**)
2. **Edite** o texto da textarea (canto inferior direito da aba)
3. Clica **💾 Aplicar**
4. Verá toast "Aplicado: user_system"
5. Badge "● não salvo" some

### 4.2 Testar antes de publicar

1. Na coluna esquerda (chat), configure:
   - **Stage**: hook, qualify, pain, etc
   - **Segmento**: academia, restaurante, loja, etc
   - **Cidade**: nome da cidade
   - **Modelo**: sonnet (recomendado) ou opus (mais inteligente, mais caro)
2. Digite a mensagem do lead no input (ex: "oi, td bem?")
3. Clique **▶ Enviar** (resposta única) ou **▶ Stream** (efeito de digitação)
4. Verifique:
   - Tom: parece humano?
   - Tamanho: ≤ 3 linhas?
   - 1 pergunta por mensagem?
   - Sem revelar preço antes de qualify?
5. Se precisar de mais rounds, continue conversando

### 4.3 Publicar (vai para produção)

1. Após validar, clique **✓ Publicar**
2. Confirma no modal
3. Toast: "Publicado — auditoria registrada"
4. A próxima mensagem real de lead no WhatsApp já usa o novo prompt

**Importante:** Publicar salva o estado em `audit_log` mas NÃO força o
worker `fralib-franz` a recarregar o módulo Python. Em produção, o WhatsApp
real só pega o novo prompt se:
- O flag `FRALIB_SDR_PROMPTS_FROM_MD=1` está setado na VPS
- O worker `fralib-franz` é reiniciado, OU o módulo do Franz é
  reimportado (acontece automaticamente a cada N minutos via watchdog)

### 4.4 Rollback (desfazer mudanças)

1. Clique **📜 Histórico** no canto inferior direito
2. Modal abre com lista de versões (data, autor, nota)
3. Clique **Restaurar** na versão desejada
4. Confirma — o estado atual vira uma nova versão (backup)
5. A versão escolhida é restaurada no arquivo

---

## 5. Cenários comuns

### "O Franz tá respondendo de forma robótica"

→ Vai em **Design System** → aumenta ênfase em tom humano
→ Exemplo: "Tom de WhatsApp real, com gírias leves. NUNCA pareça chatbot"

### "O Franz não tá perguntando sobre captação"

→ Vai em **User System** → aba **STAGE: qualify**
→ Adiciona regra: "SEMPRE pergunte: 'Como vocês captam clientes hoje?'"

### "O Franz revela preço logo de cara"

→ Vai em **User System** → **STAGE: hook** ou **qualify**
→ Adiciona regra: "NUNCA revele preço antes de stage=close"

### "O Franz fala coisa errada sobre [segmento]"

→ Vai em **RAG** → adicione a verdade factual
→ Exemplo: "Academia pequena tem 30-50 alunos. Média 100-300. Grande 500+"

### "O Franz não avança stage mesmo com lead engajado"

→ **NÃO EDITE O STUDIO.** Isso é bug. Vai em `/docs/SDR_BUGS_FIXED.md`
→ Bug #1 (stage-loop) já foi corrigido. Se voltou, é regressão.

---

## 6. Limites e cuidados

- **100KB** por camada (validado backend)
- **Sem preview de mobile** — chat é desktop-only
- **Botão "Stream"** exige WebKit/Chromium recente (Chrome, Edge, Safari 14+)
- **Backup automático:** antes de cada save, o estado atual vira versão
- **Não edite 2 abas ao mesmo tempo** sem salvar — pode perder mudanças

---

## 7. FAQ

**P: Posso deletar uma versão antiga do histórico?**
R: Não diretamente pela UI. Via SQL:
```sql
DELETE FROM sdr_studio_versions WHERE id = <N>;
```

**P: Como sei se minha mudança está em produção?**
R: Vá em `https://seunegociofralib.site/superadmin` → **API Keys** →
procure por `FRALIB_SDR_PROMPTS_FROM_MD` na seção env. Se `1`, está ativo.

**P: O Franz continua com o prompt antigo mesmo após Publicar. Por quê?**
R: Worker `fralib-franz` tem cache do módulo Python. Reinicie:
```bash
ssh root@187.77.37.72 "systemctl restart fralib-franz"
```

**P: Posso ter 2 superadmins editando ao mesmo tempo?**
R: Sim, mas o último que clica Aplicar ganha (sem lock). O auto-backup
garante que você não perde trabalho de outro admin.

---

## 8. Suporte

- Documentação técnica: `docs/SDR_STUDIO_10_10.md`
- Bugs corrigidos: `docs/SDR_BUGS_FIXED.md`
- Testes: `scripts/test_sdr_fsm.py`
- Plano original: `docs/FRANZ_SDR_ENTERPRISE_PLAN.md`

Para issues urgentes, checar logs:
```bash
ssh root@187.77.37.72 "journalctl -u fralib-api --since '10 minutes ago' --no-pager | tail -30"
```