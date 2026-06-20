# Auditoria de Constraints Visuais - 2026-05-31

## Escopo
Auditoria dos agentes e prompts que afetam spacing, cores, seções,
diagramação, fontes, bordas, mapa, mídia e fallback visual no pipeline FraLib.

## Ferramentas
- `gstack` atualizado para 1.55.0.0.
- GStack Browser aberto em modo headed na porta 34567.
- `find-skills` consultado para skills de design/spacing/contraste.
- `design-consultation` aplicado via criação do `DESIGN.md`.

## Fontes Externas Consultadas
- Carbon Design System: spacing como tokens e escala consistente.
- Material Design: layout responsivo por grid, margens e breakpoints.
- Tailwind CSS: breakpoints, spacing utilitário e composição mobile-first.
- WCAG 2.2: contraste mínimo 4.5:1 para texto normal.

## Mapa de Agentes e Prompts
- Hunter/Keyword/Jina: coletam fatos, mídia e contexto; não devem decidir layout.
- Caio: qualificação determinística; não deve alterar visual.
- Agente de Nicho: gera briefing factual de nicho; não deve inventar serviços.
- Agente de Variação: sugere ritmo/conteúdo; não deve impor paleta final.
- Bloco Estrutura: escolhe arquitetura e seções. Agora serviços só entram quando
  confirmados; sem isso, consulta fica em contato/sobre.
- Bloco Copy: escreve copy factual. Agora fallback de serviço é `omitir:true`.
- Arquiteto Mestre: monta DesignerPRD e direção compacta; não deve duplicar mapa.
- Liam/Skill Renderer: dono do HTML final; recebe regras de spacing, mapa único e
  fallback proibido como seção visual.
- OD fallback: mantém truth-contract, mas não deve criar banner de serviço legado.
- Visual Polish: injeta CSS determinístico de spacing, contraste, mobile e motion.
- HTML Quality Gate: normaliza mapa único, remove fallback visual legado e rejeita
  duplicidade antes de publicar.

## Problemas Encontrados
1. Liam ainda instruía uso de bloco curto `atividades sob consulta`.
2. Quality gate reinjetava `fralib-service-fallback` antes do footer.
3. Skill renderer adicionava `fralib-map-section` mesmo quando o HTML já tinha mapa.
4. Bloco Copy e PRD compacto empurravam seção `servicos` sem serviços confirmados.
5. OD fallback reescrevia copy para o mesmo padrão legado.
6. CSS de polish não blindava contraste em cards claros nem min-height exagerado em
   seções internas.

## Decisões
- Fallback de serviço deixa de ser componente visual.
- Localização passa a ser seção canônica única quando existe endereço/cidade.
- CSS global usa `clamp()` para spacing e limita blank space gerado por min-height.
- Superfícies claras forçam texto escuro para evitar texto branco em card branco.
- O modelo padrão de Liam passa para `opus` com 16k tokens para qualidade máxima.

## Arquivos Alterados
- `DESIGN.md`
- `backend/agents/site_skill_pack.py`
- `backend/agents/liam_renderer.py`
- `backend/agents/skill_based_renderer.py`
- `backend/agents/html_quality_gate.py`
- `backend/agents/visual_polish.py`
- `backend/agents/prompts_arquiteto.py`
- `backend/agents/bloco_estrutura.py`
- `backend/agents/bloco_copy.py`
- `backend/agents/bloco_prd_compacto.py`
- `tests/unit/test_html_quality_gate.py`
