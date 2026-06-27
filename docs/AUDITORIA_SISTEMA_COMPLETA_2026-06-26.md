# AUDITORIA COMPLETA: Fluxo de Dados do Sistema FraLib

**Data:** 2026-06-26  
**Status:** 🔍 ANÁLISE COMPLETA  
**Versão:** 2.0 (após correções de cores)

---

## DIAGRAMA DE FLUXO

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FORMULÁRIO (admin.html)                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Dados capturados:                                                          │  │
│  │ • nome_empresa, segmento, cidade, telefone                                  │  │
│  │ • nicho, tipo_negocio, publico_alvo                                         │  │
│  │ • cores (campo livre: "cores roxo e branco")                              │  │
│  │ • oferta_principal, proposta_valor, diferencial                            │  │
│  │ • redes_sociais,証       • urgencia, proof_social                           │  │
│  │ • email, whatsapp                                                        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: dados do formulário HTML                                                │
│  OUTPUT: POST /api/pipeline → nicho_briefing                                   │
│  LOST: - Preferências de fonte (se campo existir)                             │
│        - Animações preferidas                                                   │
│        - Layout preferences                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AGENTE NICHO (agente_nicho.py)                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Função: parse_colors_from_briefing_text()                                  │  │
│  │ Input: texto livre "cores roxo e branco"                                  │  │
│  │ Output: {"primary": "#800080", "secondary": "#FFFFFF"}                    │  │
│  │ Processa: nicho, cidade → archetype                                       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: nicho_briefing (texto)                                                  │
│  OUTPUT: NichoBriefing com paleta_cores                                        │
│  LOST: - Tom de voz especificado                                              │
│        - Referências visuais (ex: "como Apple")                                │
│        - Exemplos de sites que gosta                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ARQUITETO MESTRE (arquiteto_mestre.py)                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ ✅ CORRIGIDO (Sprint 14.x):                                                │  │
│  │ • Prioriza nicho_briefing.paleta_cores sobre design_dna.tokens           │  │
│  │ • Se paleta_cores existe → usa cores do usuário                          │  │
│  │ • Se não existe → usa design_dna determinístico (fallback)              │  │
│  │                                                                             │  │
│  │ Gera: DesignPRD com sections, color_palette, typography                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: nicho_briefing + design_dna + archetype                               │
│  OUTPUT: DesignerPRD (dict)                                                    │
│  LOST: - Briefing original do usuário (texto livre completo)                  │
│        - Preferências de animação específicas                                   │
│        - Hierarquia de prioridades visuais                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DESIGNER PRD (designer_prd.py)                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ Modelo Pydantic: ColorPalette, SectionSpec, DesignerPRD                   │  │
│  │ Normaliza campos e gera estrutura de seções                                │  │
│  │ ⚠️ PROBLEMA: pode gerar color_palette diferente do paleta_cores          │  │
│  │              do usuário, especialmente se o LLM interpreta mal             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: DesignerPRD (dict)                                                     │
│  OUTPUT: DesignerPRD normalizado                                               │
│  LOST: - Intent original do usuário sobre cores                                │
│        - Nuances de preferência (ex: "roxo escuro", "branco fosco")            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       BUILDER WORKER (builder_worker.py)                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ • Cria manifest de job para o builder                                      │  │
│  │ • Injeta paleta_cores no prompt_agent_payload                             │  │
│  │ • Define engine: vite_react (padrão)                                      │  │
│  │ • Gera workspace, output_dir                                              │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: DesignerPRD, tenant_id, job_id                                        │
│  OUTPUT: builder_job_manifest                                                  │
│  LOST: - Histórico de versões anteriores                                       │
│        - Feedback de iterations passadas                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    VITE REACT RENDERER (vite_react_renderer.py)                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ PRIORIDADE DE CORES (linhas 3442-3456):                                  │  │
│  │ 1. color_palette do DesignerPRD (LLM generated)                         │  │
│  │ 2. paleta_cores do NichoBriefing (do briefing livre) ← CORRIGIDO        │  │
│  │ 3. design_dna.tokens (fallback determinístico)                           │  │
│  │ 4. archetype fixo (último fallback)                                      │  │
│  │                                                                             │  │
│  │ Gera arquivos React: index.html, App.tsx, etc.                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: builder_job_manifest + facts                                            │
│  OUTPUT: Arquivos do site em /dist                                             │
│  LOST: - Meta descriptions customizadas                                        │
│        - Open Graph images específicos                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VITE PROMPTS (vite_prompts.py)                          │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ ✅ CORRIGIDO (Sprint 14.x):                                                │  │
│  │ • _build_lead_briefing_block() agora inclui paleta_cores                 │  │
│  │ • Instruções claras: "ESSAS CORES FORAM SOLICITADAS PELO USUÁRIO"        │  │
│  │ • Blindagem contra LLM ignorando cores                                     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: facts (business, paleta_cores, etc.)                                   │
│  OUTPUT: builder_prompt (string)                                                │
│  LOST: - Contexto de marca do usuário ( além de cores)                         │
│        - Referências estéticas não-textuais                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         WHATSAPP SDR (sdr_gateway.py)                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ • Gerencia estágios de qualificação (hook → qualify → ... → won/lost)   │  │
│  │ • Usa: lead_name, lead_segment, site_url, stage                          │  │
│  │ • Contém guardrails contra contaminação de segmento                      │  │
│  │ • NÃO usa: paleta_cores, color_palette, design_dna                        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│  INPUT: lead_data, stage, message_history                                      │
│  OUTPUT: Resposta SDR + next_stage                                             │
│  LOST: - Cor da marca para mensagens personalizadas                             │
│        - Tom visual consistente com o site                                     │
│        - Identidade visual nas mensagens WhatsApp                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                              SITE FINAL
         (cores do usuário preservadas após correções)
```

---

## ANÁLISE POR BLOCO

### 1. FORMULÁRIO (admin.html)

| Atributo | Descrição |
|----------|-----------|
| **Input** | Campos do formulário HTML: nome_empresa, segmento, nicho, cidade, telefone, email, whatsapp, cores, oferta_principal, proposta_valor, diferencial, redes_sociais, urgencia, proof_social |
| **Output** | POST /api/pipeline → nicho_briefing |
| **Perda de Dados** | - Preferências de tipografia não são capturadas<br>- Preferências de animação não são capturadas<br>- Layout preferences não são capturadas<br>- Referências visuais (ex: "quero algo como Nubank") |
| **Transformação** | Texto livre → estrutura de dados |
| **Por Que Perde** | Formulário não tem campos dedicados para preferências visuais avançadas |
| **Impacto** | Médio — usuário pode não conseguir especificar exatamente o que quer visualmente |

---

### 2. AGENTE NICHO (agente_nicho.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | nicho_briefing (texto), segmento, cidade |
| **Output** | NichoBriefing com paleta_cores, archetype, nicho |
| **Perda de Dados** | - Tom de voz especificado<br>- Referências visuais ("quero algo moderno")<br>- Exemplos de sites favoritos |
| **Transformação** | Texto livre → cores extraídas + archetype inferido |
| **Por Que Perde** | parse_colors_from_briefing_text() só extrai cores nominais; ignora outros dados |
| **Impacto** | Baixo — cores são o principal determinante visual |

---

### 3. ARQUITETO MESTRE (arquiteto_mestre.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | nicho_briefing (com paleta_cores), design_dna, archetype |
| **Output** | DesignerPRD (sections, color_palette, typography) |
| **Perda de Dados** | - Briefing original completo do usuário<br>- Preferências de animação específicas<br>- Hierarquia de prioridades visuais |
| **Transformação** | dados estruturados → PRD para builder |
| **Por Que Perde** | LLM gera PRD baseado em dados estruturados, não no texto original |
| **Impacto** | ⚠️ **ALTO (era)** — agora CORRIGIDO: paleta_cores tem prioridade sobre design_dna |

---

### 4. DESIGNER PRD (designer_prd.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | DesignerPRD (dict) |
| **Output** | DesignerPRD normalizado (Pydantic) |
| **Perda de Dados** | - Intent original sobre cores<br>- Nuances ("roxo escuro" vs "roxo claro") |
| **Transformação** | Validação e normalização de schema |
| **Por Que Perde** | ColorPalette tem defaults que podem sobrescrever |
| **Impacto** | Médio — LLM pode gerar paleta diferente do solicitado |

---

### 5. BUILDER WORKER (builder_worker.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | DesignerPRD, tenant_id, job_id |
| **Output** | builder_job_manifest |
| **Perda de Dados** | - Histórico de versões anteriores<br>- Feedback de iterations passadas |
| **Transformação** | Gera contrato de job para o builder |
| **Por Que Perde** | Cada job é isolado; não mantém estado de versões anteriores |
| **Impacto** | Baixo — funciona como esperado |

---

### 6. VITE REACT RENDERER (vite_react_renderer.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | builder_job_manifest, facts |
| **Output** | Arquivos do site em /dist |
| **Perda de Dados** | - Meta descriptions customizadas<br>- Open Graph images específicos |
| **Transformação** | facts → componentes React |
| **Por Que Perde** | Geração automática; usuário não customiza meta |
| **Impacto** | Médio — afeta SEO e compartilhamento |

---

### 7. VITE PROMPTS (vite_prompts.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | facts (business, paleta_cores, etc.) |
| **Output** | builder_prompt |
| **Perda de Dados** | - Contexto de marca além de cores<br>- Referências estéticas não-textuais |
| **Transformação** | dados → prompt otimizado para LLM |
| **Por Que Perde** | Prompt tem tamanho limitado; prioriza informações críticas |
| **Impacto** | ⚠️ **ALTO (era)** — agora CORRIGIDO: paleta_cores incluída explicitamente |

---

### 8. WHATSAPP SDR (sdr_gateway.py)

| Atributo | Descrição |
|----------|-----------|
| **Input** | lead_data, stage, message_history |
| **Output** | Resposta SDR, next_stage |
| **Perda de Dados** | - Cor da marca para mensagens personalizadas<br>- Tom visual consistente com o site<br>- Identidade visual nas mensagens |
| **Transformação** | Stage → mensagem apropriada |
| **Por Que Perde** | SDR usa texto; não tem acesso a design tokens |
| **Impacto** | ⚠️ **ALTO** — marca não é consistente no WhatsApp |

---

## TOP 5 PERDAS DE DADOS

### 🥇 1. IDENTIDADE VISUAL NO WHATSAPP SDR
**Bloco:** WhatsApp SDR  
**Dado perdido:** Paleta de cores, tipografia, identidade visual  
**Impacto:** Mensagens WhatsApp não refletem o site — experiência fragmentada  
**Solução:** SDR deveria receber paleta_cores e usar cores ANSI/Unicode para destacar mensagens

### 🥈 2. REFERÊNCIAS VISUAIS DO USUÁRIO
**Bloco:** Formulário + Agente Nicho  
**Dado perdido:** "Quero algo como Nubank", "estilo Apple", "minimalista"  
**Impacto:** Usuário não consegue comunicar sua visão visual completa  
**Solução:** Adicionar campo "referencias_visuais" no formulário + agente de extração

### 🥉 3. PREFERÊNCIAS DE TIPOGRAFIA
**Bloco:** Formulário  
**Dado perdido:** Família de fontes preferida, tamanhos, pesos  
**Impacto:** Site usa fontes genéricas em vez das preferidas pelo usuário  
**Solução:** Adicionar campo "fontes_preferidas" ou integração com Google Fonts

### 4. ANIMAÇÕES PREFERIDAS
**Bloco:** Formulário  
**Dado perdido:** "Quero animações suaves", "sem efeitos", "transições rápidas"  
**Impacto:** Animações podem não agradar usuário  
**Solução:** Adicionar seletor de intensidade de animação

### 5. BRIEFING COMPLETO ORIGINAL
**Bloco:** Arquiteto Mestre  
**Dado perdido:** Texto original do usuário sobre seu negócio  
**Impacto:** Contexto rico é perdido durante estruturação  
**Solução:** Manter briefing original como contexto no PRD

---

## TOP 5 TRANSFORMAÇÕES INCORRETAS

### 🥇 1. CORES DO USUÁRIO IGNORADAS (CORRIGIDO ✅)
**Bloco:** Arquiteto Mestre → Designer PRD  
**Transformação incorreta:** Usava design_dna em vez de paleta_cores  
**Agora:** paleta_cores tem prioridade máxima  
**Status:** ✅ CORRIGIDO em 2026-06-26

### 🥈 2. PROMPT VITE SEM CORES (CORRIGIDO ✅)
**Bloco:** Vite Prompts  
**Transformação incorreta:** Não incluía paleta_cores no prompt  
**Agora:** Bloco de cores incluído com instruções "OBRIGATÓRIO"  
**Status:** ✅ CORRIGIDO em 2026-06-26

### 🥉 3. PRIORIDADE DE CORES INVERTIDA (CORRIGIDO ✅)
**Bloco:** Vite React Renderer  
**Transformação incorreta:** color_palette (LLM) tinha prioridade sobre paleta_cores  
**Agora:** ordem: color_palette → paleta_cores → design_dna → archetype  
**Status:** ✅ CORRIGIDO em 2026-06-26

### 4. SDR SEM ACESSO A DESIGN TOKENS
**Bloco:** SDR Gateway  
**Transformação incorreta:** SDR não recebe paleta_cores para personalizar mensagens  
**Impacto:** WhatsApp não reflete identidade visual do site  
**Solução:** Passar paleta_cores para sdr_playbook.py

### 5. COLORPALETTE COM DEFAULTS RIGIDORS
**Bloco:** Designer PRD  
**Transformação incorreta:** ColorPalette tem defaults (#374151, #f9fafb)  
**Impacto:** LLM pode não gerar paleta se não for instruído  
**Solução:** Blindar prompt para sempre gerar color_palette

---

## LISTA DE PRIORIDADES

### 🔴 CRÍTICAS (Resolver imediatamente)

1. **SDR com identidade visual** — Passar paleta_cores para WhatsApp SDR
   - Arquivo: `backend/agents/sdr_langgraph/sdr_playbook.py`
   - Impacto: Marca consistente em todos os canais

### 🟠 ALTAS (Resolver esta semana)

2. **Campo referências visuais** — Adicionar no formulário
   - Arquivo: `frontend/admin.html`
   - Impacto: Usuário comunica visão visual

3. **Campo fontes preferidas** — Adicionar no formulário
   - Arquivo: `frontend/admin.html`
   - Impacto: Tipografia personalizada

### 🟡 MÉDIAS (Resolver este sprint)

4. **Blindar prompt DesignerPRD** — Garantir que LLM sempre gere color_palette
   - Arquivo: `backend/agents/arquiteto_mestre.py`
   - Impacto: Evita palette default

5. **Preservar briefing original** — Manter como contexto no PRD
   - Arquivo: `backend/agents/arquiteto_mestre.py`
   - Impacto: Contexto rico preservado

6. **Meta descriptions customizadas** — Permitir input do usuário
   - Arquivo: `frontend/admin.html`
   - Impacto: SEO otimizado

---

## RESUMO DO ESTADO ATUAL

| Componente | Status | Notas |
|------------|--------|-------|
| Extração de cores | ✅ OK | agente_nicho extrai corretamente |
| Armazenamento paleta_cores | ✅ OK | NichoBriefing.paleta_cores |
| Prioridade Arquiteto | ✅ CORRIGIDO | paleta_cores > design_dna |
| Prompt Vite | ✅ CORRIGIDO | inclui paleta_cores |
| Prioridade Renderer | ✅ OK | ordem correta |
| SDR Visual | 🔴 FALTA | sem acesso a cores |
| Campos formulário | 🟡 INCOMPLETO | falta refs visuais e fontes |
| Briefing preservado | 🟡 FALTA | contexto perdido |

---

## PRÓXIMOS PASSOS

1. [ ] Auditoria de SDR com Design Tokens
2. [ ] Adicionar campo "referencias_visuais" no admin.html
3. [ ] Adicionar campo "fontes_preferidas" no admin.html
4. [ ] Blindar prompt DesignerPRD para paleta_cores
5. [ ] Testes de integração completos

---

*Documento gerado automaticamente - FraLib System Audit 2026-06-26*
