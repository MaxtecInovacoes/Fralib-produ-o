"""
TESTE CONTROLADO DO AGENTE SDR BRYAN/FRANZ
Versão standalone (sem DB) - analisa prompts e simula comportamento

Uso:
    python scripts/test_sdr_bryan.py --analisar-prompt
    python scripts/test_sdr_bryan.py --cenario intro
    python scripts/test_sdr_bryan.py --cenario todos
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Setup paths
FRALIB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FRALIB_ROOT))
sys.path.insert(0, str(FRALIB_ROOT / "backend"))

# ─────────────────────────────────────────────────────────────
# ANALISADOR DE PROMPT DO SDR
# ─────────────────────────────────────────────────────────────

class SDRPromptAnalyzer:
    """Analisa os prompts e RAGs do agente SDR"""

    def __init__(self):
        self.rag_dir = FRALIB_ROOT / "backend" / "agents" / "rag_knowledge"
        self.bryan_py = FRALIB_ROOT / "backend" / "agents" / "bryan.py"

    def carregar_rag(self, nome):
        """Carrega arquivo RAG"""
        caminho = self.rag_dir / f"{nome}.md"
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def extrair_system_prompt_bryan(self):
        """Extrai o system prompt do arquivo bryan.py"""

        if not self.bryan_py.exists():
            return "bryan.py não encontrado"

        with open(self.bryan_py, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Encontrar a função _get_bryan_system
        match = re.search(r'def _get_bryan_system\(.*?\).*?return\s+"""(.*?)"""', conteudo, re.DOTALL)
        if match:
            return match.group(1)

        return "System prompt não encontrado"

    def analisar_conflitos_rag(self):
        """Verifica conflitos entre franz.md e bryan.md"""

        franz = self.carregar_rag("franz")
        bryan = self.carregar_rag("bryan")

        conflitos = []

        # Verificar se têm instruções diferentes sobre stages
        stages_franz = re.findall(r'### STAGE: (\w+)', franz)
        stages_bryan = re.findall(r'STAGE: (\w+)', bryan)

        if stages_franz != stages_bryan:
            conflitos.append(f"Stages diferentes: franz.md={stages_franz}, bryan.md={stages_bryan}")

        # Verificar se têm instruções diferentes sobre intro
        if "NUNCA revelar" in bryan and "NUNCA" not in franz[:500]:
            conflitos.append("Regra de ouro (NUNCA revelar site) só existe em bryan.md")

        # Verificar guardrails
        guardrails_bryan = re.findall(r'G\d+: (.*)', bryan)
        if len(guardrails_bryan) > 13:
            conflitos.append(f"Mais de 13 guardrails definidos: {len(guardrails_bryan)}")

        return {
            "franz_chars": len(franz),
            "bryan_chars": len(bryan),
            "conflitos": conflitos,
            "stages_franz": stages_franz,
            "stages_bryan": stages_bryan,
        }

    def analisar_system_prompt(self):
        """Analisa o system prompt em detalhes"""

        system = self.extrair_system_prompt_bryan()

        # Extrair seções
        secoes = {
            "persona": [],
            "regras": [],
            "stages": [],
            "guardrails": [],
        }

        linhas = system.split("\n")
        secao_atual = None

        for linha in linhas:
            if "##" in linha or "###" in linha:
                titulo = linha.lower()
                if "persona" in titulo or "identidade" in titulo:
                    secao_atual = "persona"
                elif "regras" in titulo or "comportamento" in titulo:
                    secao_atual = "regras"
                elif "stage" in titulo or "funil" in titulo:
                    secao_atual = "stages"
                elif "guardrail" in titulo:
                    secao_atual = "guardrails"

            if secao_atual and linha.strip():
                secoes[secao_atual].append(linha.strip())

        return {
            "system_chars": len(system),
            "secoes": {k: len(v) for k, v in secoes.items()},
            "primeiras_linhas": system[:1000],
        }

    def diagnosticar_problemas(self):
        """Diagnostica problemas conhecidos no agente"""

        problemas = []

        # 1. Modelo usado
        problemas.append({
            "tipo": "MODEL",
            "severidade": "🔴 CRÍTICO",
            "desc": "Bryan/Franz usa Haiku para tarefa complexa de SDR",
            "impacto": "Haiku não mantém contexto suficiente para conversas longas",
            "sugestao": "Trocar para Sonnet para melhor compreensão contextual",
        })

        # 2. Conflitos RAG
        conflitos = self.analisar_conflitos_rag()
        if conflitos["conflitos"]:
            problemas.append({
                "tipo": "RAG_CONFLICT",
                "severidade": "🔴 CRÍTICO",
                "desc": f"2 arquivos RAG com {len(conflitos['conflitos'])} conflitos",
                "impacto": "LLM recebe instruções contraditórias",
                "sugestao": "Unificar franz.md e bryan.md em um único arquivo",
                "conflitos": conflitos["conflitos"],
            })

        # 3. Guardrails aplicados pós-resposta
        problemas.append({
            "tipo": "GUARDRAIL_TIMING",
            "severidade": "🟡 MÉDIO",
            "desc": "Guardrails são aplicados DEPOIS que LLM já respondeu",
            "impacto": "Respostas podem ficar truncadas/incoerentes",
            "sugestao": "Mover restrições para o system prompt",
        })

        # 4. Detecção de intent por regex
        problemas.append({
            "tipo": "INTENT_DETECTION",
            "severidade": "🟡 MÉDIO",
            "desc": "detectar_intent() usa regex simples (não LLM)",
            "impacto": "Classifica 'sim, mas quero pensar' como acceptance",
            "sugestao": "Usar LLM para detectar intent com exemplos",
        })

        # 5. Memória não estruturada
        problemas.append({
            "tipo": "MEMORY_STRUCTURE",
            "severidade": "🟡 MÉDIO",
            "desc": "Memória do lead é dict livre sem validação de schema",
            "impacto": "Pode perder dados importantes entre chamadas",
            "sugestao": "Usar Pydantic model para memória estruturada",
        })

        return problemas

# ─────────────────────────────────────────────────────────────
# SIMULADOR DE CONVERSA (sem DB)
# ─────────────────────────────────────────────────────────────

class SDRConversationSimulator:
    """Simula conversas para testar comportamento do agente"""

    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.system = analyzer.extrair_system_prompt_bryan()
        self.franz_rag = analyzer.carregar_rag("franz")
        self.bryan_rag = analyzer.carregar_rag("bryan")

    def analisar_resposta(self, resposta, contexto):
        """Analisa uma resposta do SDR (simulada)"""

        issues = []
        score = 100

        # 1. Tamanho
        linhas = resposta.count("\n") + 1
        if linhas > 4:
            issues.append(f"⚠️ Mensagem longa: {linhas} linhas (ideal: <=3)")

        # 2. Uma pergunta
        perguntas = resposta.count("?")
        if perguntas == 0:
            issues.append("⚠️ Sem pergunta")
        elif perguntas > 1:
            issues.append(f"⚠️ {perguntas} perguntas (ideal: 1)")

        # 3. Stage
        stage = contexto.get("stage", "hook")
        # Simular que SDR recommends next stage based on rules

        # 4. Segmento
        segmento = contexto.get("segmento", "")
        palavras_problematicas = {
            "academia": ["delivery", "comida", "restaurante", "ifood"],
            "restaurante": ["musculação", "treino", "personal", "crossfit"],
        }

        if segmento in palavras_problematicas:
            for palavra in palavras_problematicas[segmento]:
                if palavra in resposta.lower():
                    issues.append(f"🚨 Segmento contaminado: '{palavra}' em contexto de {segmento}")

        # 5. Preço cedo
        if any(p in resposta.lower() for p in ["r$", "reais", "1500", "2000", "preço"]):
            if stage in ["hook", "qualify", "pain"]:
                issues.append("🚨 Preço revelado cedo demais")

        return {"score": max(0, score - len(issues) * 10), "issues": issues}

    def simular_cenarios(self):
        """Simula cenários de teste e mostra o que aconteceria"""

        cenarios = [
            {
                "nome": "intro_primeira_mensagem",
                "contexto": {"stage": "hook", "segmento": "academia", "rating": 4.2},
                "mensagem_lead": "oi",
                "resposta_esperada": "Curta, uma pergunta, sem revelar site",
                "comportamento_real": "❓ Depende do modelo + prompt + RAG",
            },
            {
                "nome": "objection_price",
                "contexto": {"stage": "proof", "segmento": "restaurante", "price_tier": 1},
                "mensagem_lead": "muito caro",
                "resposta_esperada": "Defender valor, não ceder preço",
                "comportamento_real": "❓ Haiku pode ceder cedo",
            },
            {
                "nome": "off_topic_delivery",
                "contexto": {"stage": "hook", "segmento": "academia"},
                "mensagem_lead": "vocês fazem delivery?",
                "resposta_esperada": "Redirecionar para nicho, não falar de delivery",
                "comportamento_real": "🚨 G12 pode falhar e falar de delivery",
            },
        ]

        return cenarios

# ─────────────────────────────────────────────────────────────
# RELATÓRIO FINAL
# ─────────────────────────────────────────────────────────────

def gerar_relatorio(analyzer, simulator):
    """Gera relatório completo do diagnóstico"""

    conflitos = analyzer.analisar_conflitos_rag()
    problemas = analyzer.diagnosticar_problemas()

    relatorio = f"""
╔══════════════════════════════════════════════════════════════════════╗
║          🔬 DIAGNÓSTICO COMPLETO DO AGENTE SDR BRYAN/FRANZ           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
║  Arquivo principal: backend/agents/bryan.py
║  RAGs: franz.md ({conflitos['franz_chars']} chars), bryan.md ({conflitos['bryan_chars']} chars)
╚══════════════════════════════════════════════════════════════════════╝

{'='*76}
📊 PROBLEMAS IDENTIFICADOS
{'='*76}
"""

    for i, p in enumerate(problemas, 1):
        relatorio += f"""
{i}. {p['severidade']} {p['tipo']}
   Problema: {p['desc']}
   Impacto: {p['impacto']}
   Sugestão: {p['sugestao']}
"""
        if "conflitos" in p:
            for c in p["conflitos"]:
                relatorio += f"   → Conflito: {c}\n"

    relatorio += f"""
{'='*76}
📋 CONFLITOS ENTRE RAGs
{'='*76}
"""

    if conflitos["conflitos"]:
        for c in conflitos["conflitos"]:
            relatorio += f"  🚨 {c}\n"
    else:
        relatorio += "  ✅ Sem conflitos óbvios\n"

    relatorio += f"""
  Stages em franz.md: {conflitos['stages_franz']}
  Stages em bryan.md: {conflitos['stages_bryan']}
"""

    relatorio += f"""
{'='*76}
🔍 SYSTEM PROMPT (primeiras linhas)
{'='*76}
"""

    system = analyzer.extrair_system_prompt_bryan()
    relatorio += system[:1500] + "\n..."

    relatorio += f"""
{'='*76}
📝 CENÁRIOS SIMULADOS
{'='*76}
"""

    for c in simulator.simular_cenarios():
        relatorio += f"""
  🎯 {c['nome']}
     Contexto: {c['contexto']}
     Lead diz: "{c['mensagem_lead']}"
     Esperado: {c['resposta_esperada']}
     Real: {c['comportamento_real']}
"""

    relatorio += f"""
{'='*76}
💡 RECOMENDAÇÕES DE CORREÇÃO
{'='*76}

  1. [🔴 CRÍTICO] Unificar RAGs
     - Mesclar franz.md e bryan.md em um único arquivo
     - Eliminar contradições entre eles

  2. [🔴 CRÍTICO] Trocar modelo para Sonnet
     - Haiku não mantém contexto suficiente
     - Sonnet tem melhor compreensão contextual

  3. [🟡 MÉDIO] Refatorar guardrails
     - Mover restrições do pós-processamento para o system prompt
     - Evitar respostas truncadas/corrompidas

  4. [🟡 MÉDIO] Melhorar detecção de intent
     - Substituir regex por classificação LLM
     - Usar exemplos com diferentes nuances

  5. [🟢 BAIXO] Estruturar memória
     - Usar Pydantic model para dados do lead
     - Validar schema antes de salvar

{'='*76}
📈 PRÓXIMOS PASSOS SUGERIDOS
{'='*76}

  OPÇÃO A (Rápido - 2h):
  → Corrigir G12 de segmentação
  → Trocar modelo para Sonnet
  → Unificar RAGs manualmente

  OPÇÃO B (Completo - 1-2 dias):
  → Reescrever system prompt com exemplos claros
  → Refatorar arquitetura para stages explícitos
  → Adicionar testes automatizados

  OPÇÃO C (Rebase - 3-5 dias):
  → Recriar agente do zero com arquitetura limpa
  → Usar tool_use para forçar JSON estruturado
  → Implementar testes E2E completos

╚══════════════════════════════════════════════════════════════════════╝
"""

    return relatorio

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Teste controlado do SDR Bryan/Franz")
    parser.add_argument("--cenario", "-c", choices=["intro", "objection", "off_topic", "todos"],
                        default="todos", help="Cenário a testar")
    parser.add_argument("--analisar-prompt", "-a", action="store_true", help="Analisar apenas o prompt")
    parser.add_argument("--relatorio", "-r", action="store_true", help="Gerar relatório completo")

    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         🔬 DIAGNÓSTICO DO AGENTE SDR BRYAN/FRANZ                    ║
║                                                                  ║
║  Analisa prompts, RAGs e comportamento do agente                   ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    analyzer = SDRPromptAnalyzer()
    simulator = SDRConversationSimulator(analyzer)

    if args.analisar_prompt or args.relatorio:
        # Mostrar análise do prompt
        print("\n📋 Carregando arquivos...")

        conflitos = analyzer.analisar_conflitos_rag()
        print(f"   franz.md: {conflitos['franz_chars']} chars")
        print(f"   bryan.md: {conflitos['bryan_chars']} chars")

        problemas = analyzer.diagnosticar_problemas()
        print(f"\n🔴 Problemas encontrados: {len(problemas)}")

        for p in problemas:
            print(f"   • {p['severidade']} {p['tipo']}: {p['desc']}")

        print("\n" + "="*76)
        print("💡 SUGESTÕES DE CORREÇÃO")
        print("="*76)

        for p in problemas:
            print(f"\n  [{p['tipo']}]")
            print(f"  {p['sugestao']}")

    else:
        # Gerar relatório completo
        relatorio = gerar_relatorio(analyzer, simulator)
        print(relatorio)

if __name__ == "__main__":
    main()
