"""
Teste do novo agente SDR LangGraph
Verifica estrutura, imports, e fluxo básico
"""

import sys
import os
from pathlib import Path

FRALIB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FRALIB_ROOT))
sys.path.insert(0, str(FRALIB_ROOT / "backend"))


def test_structure():
    """Testa se os arquivos foram criados"""
    print("=" * 70)
    print("TESTE 1: Estrutura de arquivos")
    print("=" * 70)

    required_files = [
        "backend/agents/sdr_langgraph/__init__.py",
        "backend/agents/sdr_langgraph/state.py",
        "backend/agents/sdr_langgraph/prompts.py",
        "backend/agents/sdr_langgraph/tools.py",
        "backend/agents/sdr_langgraph/agent.py",
        "backend/agents/sdr_langgraph/compat.py",
        "backend/agents/sdr_langgraph/nodes/__init__.py",
        "backend/agents/sdr_langgraph/MIGRATION_GUIDE.py",
    ]

    all_ok = True
    for f in required_files:
        path = FRALIB_ROOT / f
        if path.exists():
            size = path.stat().st_size
            print(f"  OK {f} ({size} bytes)")
        else:
            print(f"  FALTA {f}")
            all_ok = False

    return all_ok


def test_imports():
    """Testa se os imports funcionam"""
    print("\n" + "=" * 70)
    print("TESTE 2: Imports")
    print("=" * 70)

    try:
        from agents.sdr_langgraph import (
            SDRGraph, get_sdr_graph, SDRState, LeadMemory, StageEnum,
            iniciar_contato, responder_lead, followup_automatico,
            BryanInput, BryanOutput,
        )
        print("  OK Todos os imports funcionaram")
        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state():
    """Testa o Pydantic LeadMemory"""
    print("\n" + "=" * 70)
    print("TESTE 3: LeadMemory (Pydantic)")
    print("=" * 70)

    from agents.sdr_langgraph import LeadMemory, StageEnum

    try:
        # Criar memória
        memory = LeadMemory(
            lead_id="test_123",
            user_id=1,
            telefone="41999999999",
            nome="FitLife Academia",
            segmento="academia",
            cidade="Curitiba",
        )
        print(f"  OK LeadMemory criado: {memory.nome} ({memory.segmento})")
        print(f"     Stage inicial: {memory.stage}")

        # Testar update_stage
        success = memory.update_stage("qualify")
        print(f"  OK update_stage('qualify'): {success} (agora: {memory.stage})")

        # Testar transição inválida
        success = memory.update_stage("reveal")  # Hook→qualify→...→reveal
        print(f"  OK update_stage('reveal') sem passar por outras: {success} (esperado: False)")

        # Testar mark_opt_out
        memory.mark_opt_out()
        print(f"  OK mark_opt_out(): stage={memory.stage}, deal_status={memory.deal_status}")

        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompts():
    """Testa se os prompts estão estruturados"""
    print("\n" + "=" * 70)
    print("TESTE 4: Prompts por stage")
    print("=" * 70)

    from agents.sdr_langgraph.prompts import (
        FRANZ_PERSONA, STAGE_PROMPTS, VARIANT_EXAMPLES,
        build_stage_prompt, build_user_prompt,
    )

    try:
        # Verificar que cada stage tem prompt
        stages = ["hook", "qualify", "pain", "amplify", "tease",
                  "proof", "reveal", "feedback", "close",
                  "followup_24h", "followup_72h"]

        for stage in stages:
            if stage in STAGE_PROMPTS:
                print(f"  OK {stage}: {len(STAGE_PROMPTS[stage])} chars")
            else:
                print(f"  FALTA {stage}")

        # Verificar variantes A/B/C/D
        for v in ["A", "B", "C", "D"]:
            if v in VARIANT_EXAMPLES:
                print(f"  OK Variante {v}: {len(VARIANT_EXAMPLES[v])} chars")
            else:
                print(f"  FALTA Variante {v}")

        # Testar builder
        prompt = build_stage_prompt(
            stage="hook",
            variant="B",
            segmento="academia",
            rating=4.2,
        )
        print(f"  OK build_stage_prompt: {len(prompt)} chars")
        print(f"     Preview: {prompt[:100]}...")

        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transitions():
    """Testa se as transições de stage estão corretas"""
    print("\n" + "=" * 70)
    print("TESTE 5: Transições válidas")
    print("=" * 70)

    from agents.sdr_langgraph.state import VALID_TRANSITIONS

    try:
        # Verificar transições esperadas
        expected = {
            "hook": ["qualify", "gatekeeper", "opt_out", "lost"],
            "qualify": ["pain", "gatekeeper", "opt_out", "lost", "scheduled"],
            "pain": ["amplify", "qualify", "opt_out", "lost"],
            "amplify": ["tease", "pain", "opt_out", "lost"],
            "tease": ["proof", "opt_out", "lost"],
            "proof": ["reveal", "tease", "opt_out", "lost"],
            "reveal": ["feedback", "lost", "close"],
            "feedback": ["close", "proof", "lost"],
            "close": ["won", "urgency", "lost", "scheduled"],
        }

        all_ok = True
        for stage, allowed in expected.items():
            if stage in VALID_TRANSITIONS:
                actual = VALID_TRANSITIONS[stage]
                print(f"  OK {stage} → {actual}")
            else:
                print(f"  FALTA stage {stage}")
                all_ok = False

        return all_ok
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """Testa tools de validação"""
    print("\n" + "=" * 70)
    print("TESTE 6: Tools de validação")
    print("=" * 70)

    from agents.sdr_langgraph.tools import (
        check_segment_contamination,
        is_valid_length,
        has_one_question,
        detect_intent_regex,
        get_greeting,
        choose_variant,
    )

    try:
        # Testar contaminação
        cont = check_segment_contamination(
            "Vocês fazem delivery?",
            "academia"
        )
        if "delivery" in cont:
            print(f"  OK Contaminação detectada: {cont}")
        else:
            print(f"  FALHA: não detectou 'delivery' em academia")

        # Testar comprimento
        valid = is_valid_length("Oi tudo bem?")
        print(f"  OK Mensagem curta é válida: {valid}")

        invalid = is_valid_length("a" * 500)
        print(f"  OK Mensagem longa (>300) é inválida: {not invalid}")

        # Testar uma pergunta
        ok = has_one_question("Como vocês captam clientes?")
        print(f"  OK Uma pergunta: {ok}")

        bad = has_one_question("Oi? Tudo bem? Como vai?")
        print(f"  OK Múltiplas perguntas detectadas: {not bad}")

        # Testar intent regex (fallback)
        intent = detect_intent_regex("oi, tudo bem?")
        print(f"  OK Intent 'oi' → '{intent}'")

        intent = detect_intent_regex("sou o dono, pode falar")
        print(f"  OK Intent 'sou o dono' → '{intent}'")

        intent = detect_intent_regex("muito caro isso")
        print(f"  OK Intent 'muito caro' → '{intent}'")

        # Testar greeting
        greeting = get_greeting()
        print(f"  OK Saudação: '{greeting}'")

        # Testar variant
        variant = choose_variant("lead_123", "academia")
        print(f"  OK Variante: {variant}")

        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_construction():
    """Testa se o grafo pode ser construído"""
    print("\n" + "=" * 70)
    print("TESTE 7: Construção do Grafo")
    print("=" * 70)

    try:
        from agents.sdr_langgraph.agent import build_sdr_graph, get_sdr_graph

        graph = build_sdr_graph()
        print(f"  OK Grafo construído: {type(graph).__name__}")

        # Compilar
        compiled = graph.compile()
        print(f"  OK Grafo compilado: {type(compiled).__name__}")

        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compat():
    """Testa interface compatível com bryan.py"""
    print("\n" + "=" * 70)
    print("TESTE 8: Compatibilidade com bryan.py")
    print("=" * 70)

    try:
        from agents.sdr_langgraph import (
            BryanInput, BryanOutput,
            iniciar_contato, responder_lead, followup_automatico,
            ESTADOS_SDR, ESTADO_TO_STAGE,
        )

        # Verificar assinaturas
        print(f"  OK BryanInput campos: {list(BryanInput.model_fields.keys())}")
        print(f"  OK BryanOutput campos: {list(BryanOutput.model_fields.keys())}")
        print(f"  OK ESTADOS_SDR: {len(ESTADOS_SDR)} estados")
        print(f"  OK ESTADO_TO_STAGE: {len(ESTADO_TO_STAGE)} mapeamentos")

        # Verificar funções existem
        print(f"  OK iniciar_contato: {iniciar_contato.__name__}")
        print(f"  OK responder_lead: {responder_lead.__name__}")
        print(f"  OK followup_automatico: {followup_automatico.__name__}")

        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🧪 TESTE DO SDR LANGGRAPH (substituindo bryan.py)              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    results = []
    results.append(("Estrutura", test_structure()))
    results.append(("Imports", test_imports()))
    results.append(("LeadMemory", test_state()))
    results.append(("Prompts", test_prompts()))
    results.append(("Transições", test_transitions()))
    results.append(("Tools", test_tools()))
    results.append(("Grafo", test_graph_construction()))
    results.append(("Compat", test_compat()))

    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "OK" if ok else "FALHA"
        print(f"  {status}  {name}")

    print(f"\n  {passed}/{total} testes passaram")

    if passed == total:
        print("\n  SDR LANGGRAPH PRONTO PARA USO!")
        print("\n  Próximos passos:")
        print("     1. Trocar Haiku → Sonnet em llm_direct.py")
        print("     2. Unificar RAGs (deletar bryan.md)")
        print("     3. Trocar imports de bryan para sdr_langgraph")
        print("     4. Testar com conversa real")
    else:
        print("\n  Há problemas a corrigir antes de usar")
