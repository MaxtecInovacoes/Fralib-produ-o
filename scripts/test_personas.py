"""
Testa seleção automática de persona
"""

import sys
from pathlib import Path

FRALIB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(FRALIB_ROOT))
sys.path.insert(0, str(FRALIB_ROOT / "backend"))

from agents.sdr_langgraph.prompts import should_use_lobo, get_prompt_for_persona, PERSONAS


# ════════════════════════════════════════════════════════════════════
# TESTES
# ════════════════════════════════════════════════════════════════════

print("=" * 70)
print("TESTE: SELEÇÃO AUTOMÁTICA DE PERSONA")
print("=" * 70)

testes = [
    # (intent, rejection_count, esperado, descrição)
    ("objection_price", 0, True, "Lead perguntou preço → LOBO"),
    ("objection_price", 1, True, "Lead perguntou preço (1 rejeição) → LOBO"),
    ("rejection", 2, True, "2 rejeições → LOBO"),
    ("rejection", 0, False, "1 rejeição normal → CONSULTIVO"),
    ("objection_trust", 0, False, "Desconfiança → CONSULTIVO (ganha confiança)"),
    ("gatekeeper", 0, False, "Gatekeeper → CONSULTIVO (torna aliado)"),
    ("acceptance", 0, False, "Aceitação → CONSULTIVO (fecha leve)"),
    ("wants_link", 0, False, "Quer ver site → CONSULTIVO (não pressiona)"),
    ("schedule", 0, False, "Agendar → CONSULTIVO (não pressiona)"),
    ("other", 0, False, "Outro → CONSULTIVO (default)"),
]

print()
passed = 0
for intent, rej_count, esperado, desc in testes:
    result = should_use_lobo(intent, rej_count)
    status = "OK" if result == esperado else "FALHA"
    if result == esperado:
        passed += 1
    persona = "LOBO 🐺" if result else "CONSULTIVO 🟢"
    print(f"  {status}  intent={intent:20} rej={rej_count} → {persona:18} | {desc}")

print(f"\n  {passed}/{len(testes)} testes passaram")

# Teste de prompts
print("\n" + "=" * 70)
print("TESTE: PROMPTS POR PERSONA")
print("=" * 70)

for stage in ["hook", "qualify", "pain", "amplify", "tease", "proof", "feedback", "close"]:
    p_consultivo = get_prompt_for_persona("consultivo", stage)
    p_lobo = get_prompt_for_persona("lobo", stage)

    print(f"\n  📍 Stage: {stage}")
    print(f"     🟢 Consultivo: {len(p_consultivo)} chars")
    print(f"        Preview: {p_consultivo.strip()[:100]}...")
    print(f"     🔴 Lobo: {len(p_lobo)} chars")
    print(f"        Preview: {p_lobo.strip()[:100]}...")

# Comparação visual
print("\n" + "=" * 70)
print("COMPARAÇÃO HOOK (primeira mensagem)")
print("=" * 70)

print("\n  🟢 CONSULTIVO:")
print("     'E aí! Vocês são de musculação ou funcional também?'")
print("     → Casual, pergunta sobre o negócio")

print("\n  🔴 LOBO:")
print("     'Boa tarde. Tô te procurando porque 3 concorrentes seus já tão")
print("      capturando os clientes que deveriam ser de vocês. Me dá 30 segundos?'")
print("     → Direto, senso de perda, escassez de tempo")

print("\n" + "=" * 70)
print("CONCLUSÃO")
print("=" * 70)
print()
print("  → CONSULTIVO é o default (maioria dos leads)")
print("  → LOBO é ativado quando:")
print("     - Lead pergunta preço direto (objection_price)")
print("     - Lead rejeitou 2+ vezes")
print()
print("  → Isso evita o LOBO de assustar leads sensíveis")
print("  → E permite fechar mais rápido leads prontos para comprar")
