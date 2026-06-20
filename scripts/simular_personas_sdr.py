"""
Simulador de Conversas REALISTAS - SDR LangGraph
Mostra como Franz (Consultivo) vs Lobo se comportam em conversas reais
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict

FRALIB_ROOT = Path(__file__).parent.parent


# ════════════════════════════════════════════════════════════════════
# CONVERSAS PRÉ-DEFINIDAS (mais realistas)
# ════════════════════════════════════════════════════════════════════

CONVERSAS = {
    "academia_curioso": {
        "lead": {
            "nome": "FitLife Academia",
            "telefone": "41999990001",
            "segmento": "academia",
            "cidade": "Curitiba",
            "rating": 4.2,
            "site_url": "https://fitlife.fralib.com.br",
            "persona": "Curioso, sem pressa, quer ver o site"
        },
        "consultivo": [
            ("Franz", "E aí! Vi que vocês tão em Curitiba. Posso te fazer uma pergunta? Vocês são mais de musculação ou funcional?", "hook"),
            ("Lead", "ah oi, sou o dono. sim, musculação e cross"),
            ("Franz", "Boa! Eu sou o Franz, tô pesquisando academias da região e a de vocês me chamou atenção. Me conta, como tá sendo a captação de aluno novo aí?", "qualify"),
            ("Lead", "mais por indicação mesmo, instagram também"),
            ("Franz", "Massa! E quando o aluno não vem por indicação e pesquisa 'academia em Curitiba' no Google — vocês aparecem ou o cliente acha o concorrente?", "pain"),
            ("Lead", "hmm, acho que não, na verdade não sei"),
            ("Franz", "Pois é, foi por isso que te chamei. Fiz um estudo rápido: tem 3 academias que aparecem antes de vocês nas buscas. Em média, 200 pessoas/mês pesquisam isso. Se 10% viraria aluno, são 20 pessoas/mês. Dá uma pensada no valor disso.", "amplify"),
            ("Lead", "nossa, não tinha ideia"),
            ("Franz", "Pois é! E olha, sem compromisso nenhum: gerei um site especial pra vocês mostrando como apareceriam melhor. Quer dar uma olhada? Sem custo, só pra você ver.", "tease"),
            ("Lead", "pode mandar sim"),
            ("Franz", "Show! Toma: https://fitlife.fralib.com.br. Olha com calma — pode ser ajustado 100% (logo, fotos, cores). Me conta o que achou!", "proof"),
            ("Lead", "caraca, ficou massa"),
            ("Franz", "Que bom! E se ajustarmos com as cores/logo de vocês? Posso personalizar rapidinho.", "reveal"),
            ("Lead", "pode ser, quanto fica?"),
            ("Franz", "Depende de como quer personalizar. Mas o projeto completo fica R$ 1.499 em até 12x, e só paga depois que aprovar tudo. Faz sentido pra você?", "close"),
        ],
        "lobo": [
            ("Franz", "Boa tarde. Tô ligando porque 3 academias da sua região já tão capturando clientes que deveriam ser de vocês. Me dá 30 segundos?", "hook"),
            ("Lead", "ah oi, sou o dono. sim, musculação e cross"),
            ("Franz", "Show. Olha, fiz um levantamento: quem pesquisa 'academia em Curitiba' hoje acha 3 concorrentes seus, não vocês. Isso são seus clientes indo pro bolso deles.", "qualify"),
            ("Lead", "mais por indicação mesmo, instagram também"),
            ("Franz", "Justo, mas indicação não escala. Vou ser direto: 200 buscas/mês × 10% conversão = 20 alunos/mês × R$ 100 ticket = R$ 2.000/mês deixando de entrar. Multiplica por 12. Você pode perder R$ 24 mil esse ano ou recuperar.", "pain"),
            ("Lead", "hmm, acho que não, na verdade não sei"),
            ("Franz", "Não sabe porque nunca mediu. Mas eu medi. Posso te mandar o relatório agora. E junto: já gerei um site de teste pra vocês, mostra como VOCÊS apareceriam. Olha: https://fitlife.fralib.com.br. Se fizer sentido, ajusto 100% com a cara de vocês. Se não, ok também.", "amplify"),
            ("Lead", "nossa, não tinha ideia"),
            ("Franz", "Pois é. Última coisa: posso ajustar com logo/cores de vocês HOJE e colocar no ar até sexta. Sem custo. Você vê rodando de verdade e a gente conversa sobre investimento depois. Faz sentido?", "tease"),
            ("Lead", "pode mandar sim"),
            ("Franz", "Show! Toma: https://fitlife.fralib.com.br. Olha com calma — pode ser ajustado 100%. Me conta o que achou!", "reveal"),
            ("Lead", "caraca, ficou massa"),
            ("Franz", "Ótimo. Última pergunta: posso ajustar com logo/cores de vocês HOJE e colocar no ar até sexta? Sem custo. Aí você vê rodando de verdade e a gente conversa sobre investimento depois.", "close"),
            ("Lead", "pode ser, quanto fica?"),
            ("Franz", "R$ 1.499 em 12x. Só paga depois que aprovar. Fechado?", "close"),
        ]
    },

    "restaurante_desconfiado": {
        "lead": {
            "nome": "Sabor da Casa",
            "telefone": "41999990002",
            "segmento": "restaurante",
            "cidade": "São Paulo",
            "rating": 4.5,
            "site_url": "https://saborcasa.fralib.com.br",
            "persona": "Desconfiado, quer comparar, quer prova"
        },
        "consultivo": [
            ("Franz", "E aí! Vi vocês no Google Maps — 4.5⭐, isso é raro pra restaurante na região! Tá de parabéns.", "hook"),
            ("Lead", "quem é você?"),
            ("Franz", "Sou o Franz, da FraLib. A gente monta sites pra negócios locais. Não é spam, juro! Vi vocês no Maps e quis trocar uma ideia. Pode falar 1 minuto?", "qualify"),
            ("Lead", "nunca ouvi falar"),
            ("Franz", "Tranquilo! Somos novos ainda. Tô te procurando justamente porque restaurantes com a nota de vocês merecem aparecer bem no Google. Posso te perguntar uma coisa?", "qualify"),
            ("Lead", "e o que vocês querem?"),
            ("Franz", "Boa pergunta! Te mostro o que a gente faz. Mas antes — vocês aparecem quando alguém pesquisa 'restaurante em São Paulo'?", "pain"),
            ("Lead", "site eu já tenho, mas é velho"),
            ("Franz", "Massa! E ele aparece bem quando o cliente pesquisa? Porque se não aparece, ele não tá te ajudando. Posso te mostrar como ficaria?", "amplify"),
            ("Lead", "manda ver então"),
            ("Franz", "Show! Toma: https://saborcasa.fralib.com.br. Olha com calma — fiz pensando em vocês. Pode ser ajustado 100%. Me conta o que achou!", "tease"),
            ("Lead", "até que ficou bom"),
            ("Franz", "Que bom! E se ajustarmos com cardápio, fotos dos pratos, cores de vocês? Posso personalizar rapidinho.", "reveal"),
        ],
        "lobo": [
            ("Franz", "Boa tarde. Vou direto: seu restaurante tem 4.5⭐ mas não aparece pra quem pesquisa 'restaurante em São Paulo'. Concorrentes de vocês aparecem. Isso são clientes indo pro bolso deles. Me dá 30 segundos?", "hook"),
            ("Lead", "quem é você?"),
            ("Franz", "Franz, da FraLib. A gente monta sites pra restaurante aparecer melhor no Google. Olha, fiz uma página teste pra vocês já: https://saborcasa.fralib.com.br. Olha e me diz se faz sentido.", "qualify"),
            ("Lead", "nunca ouvi falar"),
            ("Franz", "Não precisa ter ouvido. Só olha o que gerei e me diz: vale conversar 2 minutos ou não? Se não, sem stress.", "qualify"),
            ("Lead", "e o que vocês querem?"),
            ("Franz", "Quero te mostrar que dá pra capturar os clientes que tão indo pro seu concorrente. Olha: https://saborcasa.fralib.com.br. 1 minuto pra ver e me dizer se faz sentido.", "pain"),
            ("Lead", "site eu já tenho, mas é velho"),
            ("Franz", "Então tá na hora de atualizar. Esse aqui já tá pronto. Posso ajustar com cardápio, fotos e cores de vocês HOJE. Quanto vocês perdem por mês que vai pro concorrente?", "amplify"),
            ("Lead", "manda ver então"),
            ("Franz", "Já mandei: https://saborcasa.fralib.com.br. Olha e me diz: se eu ajustar isso aqui com a cara de vocês e colocar no ar até sexta, você me dá 5 minutos pra explicar o investimento?", "tease"),
            ("Lead", "até que ficou bom"),
            ("Franz", "Ótimo. Ajusto com cardápio, fotos e cores de vocês HOJE. Fechado?", "close"),
        ]
    },

    "clinica_objetivo": {
        "lead": {
            "nome": "Clínica Sorriso",
            "telefone": "41999990003",
            "segmento": "dentista",
            "cidade": "Belo Horizonte",
            "rating": 4.8,
            "site_url": "https://clinicasorriso.fralib.com.br",
            "persona": "Objetivo, quer valor, pouco tempo"
        },
        "consultivo": [
            ("Franz", "Opa! Vi vocês no Maps — 4.8⭐, tá voando! Posso fazer uma pergunta rápida?", "hook"),
            ("Lead", "sim, fala"),
            ("Franz", "Tô pesquisando clínicas em BH e a de vocês me chamou atenção. Me conta, como tá sendo a captação de paciente novo aí? Indicação ou tem presença online?", "qualify"),
            ("Lead", "o que é?"),
            ("Franz", "Sou Franz, da FraLib. A gente monta sites pra clínicas aparecerem melhor no Google. Achei a de vocês, quis trocar uma ideia. Vocês aparecem quando alguém pesquisa 'dentista em BH'?", "qualify"),
            ("Lead", "tô sem tempo, fala rápido"),
            ("Franz", "Beleza, vou direto: gerei uma página teste pra vocês. Toma: https://clinicasorriso.fralib.com.br. Olha em 10 segundos — se fizer sentido, ajusto 100% com vocês. Se não, sem stress.", "pain"),
            ("Lead", "quanto custa?"),
            ("Franz", "Depende do nível de personalização, mas o projeto completo fica R$ 1.499 em 12x, e só paga depois que aprovar. Faz sentido?", "close"),
        ],
        "lobo": [
            ("Franz", "Boa tarde. Vou direto ao ponto: clínica com 4.8⭐ que não aparece no Google perde 30 pacientes/mês pro concorrente. Posso te mostrar como reverter isso em 30 segundos?", "hook"),
            ("Lead", "sim, fala"),
            ("Franz", "Justo. Quem pesquisa 'dentista em BH' hoje acha 5 clínicas ANTES de vocês. Cada paciente novo vale R$ 3-5 mil em tratamento. São R$ 90-150 mil/mês deixando de entrar.", "qualify"),
            ("Lead", "o que é?"),
            ("Franz", "Site que aparece no Google. Já gerei um pra vocês. Toma: https://clinicasorriso.fralib.com.br. Olha — se fizer sentido, ajusto HOJE com a cara de vocês. Última coisa: se eu colocar no ar até sexta, você vê rodando. Quanto isso vale pra vocês?", "qualify"),
            ("Lead", "tô sem tempo, fala rápido"),
            ("Franz", "Justo. Vou ser cirúrgico: hoje, vocês não aparecem. Posso mudar isso até sexta. Investimento: R$ 1.499 em 12x, só paga depois que aprovar. Faz sentido ou não?", "pain"),
            ("Lead", "quanto custa?"),
            ("Franz", "Já te falei: R$ 1.499 em 12x. Só paga depois que aprovar. Fechado?", "close"),
        ]
    }
}


# ════════════════════════════════════════════════════════════════════
# RENDERIZADOR
# ════════════════════════════════════════════════════════════════════

def render_conversa(persona_name: str, conversa: List[tuple], lead: dict):
    """Renderiza uma conversa de forma visual"""

    print(f"\n  {'='*70}")
    print(f"  {persona_name}")
    print(f"  Lead: {lead['nome']} ({lead['segmento']}) - {lead['persona']}")
    print(f"  {'='*70}\n")

    for autor, msg, *stage_info in conversa:
        stage = stage_info[0] if stage_info else "?"
        if autor == "Franz":
            print(f"  🤖 FRANZ [{stage}]:")
            print(f"     {msg}")
        else:
            print(f"\n  👤 LEAD: {msg}\n")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🎭 SDR LANGGRAPH - DUAS PERSONAS, MESMO FUNIL                   ║
║                                                                              ║
║  COMPARAÇÃO LADO A LADO: CONSULTIVO BEM-HUMORADO vs LOBO DE WALL STREET      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    for cenario_key, cenario in CONVERSAS.items():
        lead = cenario["lead"]
        print(f"\n\n{'#'*78}")
        print(f"#  📍 CENÁRIO: {cenario_key.upper()}")
        print(f"#  👤 LEAD: {lead['nome']} ({lead['segmento']})")
        print(f"#  🎯 OBJETIVO: {lead['persona']}")
        print(f"{'#'*78}")

        render_conversa("🟢 CONSULTIVO BEM-HUMORADO", cenario["consultivo"], lead)
        render_conversa("🔴 LOBO DE WALL STREET", cenario["lobo"], lead)

    # Análise final
    print(f"\n\n{'='*78}")
    print("📊 ANÁLISE COMPARATIVA")
    print(f"{'='*78}\n")

    print("🟢 PERSONA CONSULTIVA (FRANZ LEVE)")
    print("  COMO FUNCIONA:")
    print("    - Saudação casual (\"e aí\", \"opa\", \"show\", \"massa\")")
    print("    - Elogia o lead antes de vender")
    print("    - Faz perguntas de descoberta antes de pitch")
    print("    - Mostra o site APENAS quando lead demonstra interesse")
    print("    - Tom de conversa, não de venda")
    print()
    print("  QUANDO USAR:")
    print("    ✓ Default para todos os leads")
    print("    ✓ Negócios com rating alto (prova social)")
    print("    ✓ Segmentos mais sensíveis (saúde, educação)")
    print()
    print("  ✗ RISCO:")
    print("    - Pode fechar mais devagar")
    print("    - Lead pode não perceber urgência\n")

    print("🔴 PERSONA LOBO (FRANZ AGRESSIVO)")
    print("  COMO FUNCIONA:")
    print("    - Vai direto ao ponto, sem enrolação")
    print("    - Cria senso de perda (\"vocês tão perdendo R$X/mês\")")
    print("    - Usa números concretos (buscas, conversão, ticket)")
    print("    - Cria escassez (\"só mostro pra 1 por região\")")
    print("    - Pressiona para fechamento rápido")
    print()
    print("  QUANDO USAR:")
    print("    ✓ Lead que pergunta preço direto (objection_price)")
    print("    ✓ Follow-up de lead morno")
    print("    ✓ Negócios com ticket alto (justifica investimento)")
    print()
    print("  ✗ RISCO:")
    print("    - Pode assustar lead desconfiado")
    print("    - Mais opt-outs em leads sensíveis")
    print("    - Pode parecer spam agressivo\n")

    print("💡 RECOMENDAÇÃO DE IMPLEMENTAÇÃO:")
    print("    1. Detectar intent inicial (objection_price → LOBO)")
    print("    2. Detectar rejeição consecutiva (>=2 rejeições → LOBO urgente)")
    print("    3. Default → CONSULTIVO")
    print("    4. Após stage 'close' → CONSULTIVO (não pressionar)")
    print()
    print("    Implementação:")
    print("      from sdr_langgraph import SDRGraph")
    print("      graph = SDRGraph()")
    print("      result = graph.invoke({...")
    print("        'persona': 'consultivo'  # ou 'lobo'")
    print("      })")


if __name__ == "__main__":
    main()
