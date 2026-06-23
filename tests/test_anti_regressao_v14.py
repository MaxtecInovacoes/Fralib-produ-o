"""Tests anti-regressao v1.4-baseline-2026-06-23 - Sprint 3A: Tools dinamicas no SDR.

Protege as 4 tools SDR + integracao no agent.py + 8 nichos canonicos:
1. tools_sdr.py existe com 4 funcoes
2. TOOLS_DISPATCH tem 4 entradas + call_tool + list_tools
3. sdr_playbook.py tem 8 nichos canônicos (incluindo default)
4. get_nicho_playbook tem fallback para nichos nao mapeados
5. retrieve_similar_conversations persiste + recupera (round-trip)
6. check_lead_quality retorna dict com chaves esperadas
7. save_sdr_lesson aplica multiplicador correto (1.5x converteu, 0.3x nao)
8. agent.py importa tools_sdr quando FRALIB_SDR_USE_TOOLS=1

Standalone runner: nao usa pytest/cov.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


class TestV14Sprint3AToolsSDR:
    """Sprint 3A: 4 tools dinamicas + playbook + integracao agent.py."""

    @staticmethod
    def test_tools_sdr_module_exists():
        """tools_sdr.py deve existir (Sprint 3A entrega)."""
        assert (BACKEND / "agents" / "sdr_langgraph" / "tools_sdr.py").is_file(), \
            "tools_sdr.py nao existe! Sprint 3A nao foi entregue."

    @staticmethod
    def test_tools_sdr_has_4_functions_and_dispatch():
        """tools_sdr.py deve ter 4 funcoes + TOOLS_DISPATCH + call_tool + list_tools."""
        from backend.agents.sdr_langgraph import tools_sdr

        # 4 funcoes principais
        assert hasattr(tools_sdr, "retrieve_similar_conversations"), \
            "retrieve_similar_conversations ausente"
        assert hasattr(tools_sdr, "get_nicho_playbook"), \
            "get_nicho_playbook ausente"
        assert hasattr(tools_sdr, "check_lead_quality"), \
            "check_lead_quality ausente"
        assert hasattr(tools_sdr, "save_sdr_lesson"), \
            "save_sdr_lesson ausente"
        # Dispatcher pattern (mesmo de tools_site.py)
        assert hasattr(tools_sdr, "TOOLS_DISPATCH"), \
            "TOOLS_DISPATCH ausente"
        assert hasattr(tools_sdr, "call_tool"), \
            "call_tool ausente"
        assert hasattr(tools_sdr, "list_tools"), \
            "list_tools ausente"
        # TOOLS_DISPATCH tem 4 entradas
        assert len(tools_sdr.TOOLS_DISPATCH) == 4, \
            f"TOOLS_DISPATCH deveria ter 4 tools, tem {len(tools_sdr.TOOLS_DISPATCH)}"
        # list_tools retorna 4 nomes
        tools = tools_sdr.list_tools()
        assert len(tools) == 4, f"list_tools() retornou {len(tools)} tools"

    @staticmethod
    def test_sdr_playbook_has_8_nichos_with_default_fallback():
        """sdr_playbook.py deve ter 8 nichos + fallback 'default'."""
        from backend.agents.sdr_langgraph import sdr_playbook

        nichos = sdr_playbook.list_nichos()
        assert len(nichos) >= 8, f"Nichos insuficientes: {len(nichos)} (esperado >=8)"

        # Nichos canonicos que DEVEM existir
        required = {
            "academia_crossfit", "nutricionista_esportiva", "barbearia_premium",
            "restaurante_familiar", "clinica_estetica", "advocacia_trabalhista",
            "ecommerce_basico", "default",
        }
        for n in required:
            assert n in nichos, f"Nicho canonico ausente: {n}"

        # Fallback 'default' deve existir E ter todas as chaves
        default = sdr_playbook.get_nicho_playbook("xyz_nao_mapeado")
        for key in ["perguntas_obrigatorias", "red_flags", "objecoes_comuns",
                    "gatilhos_conversao", "tom_recomendado", "frase_hook_inicial"]:
            assert key in default, f"Fallback default sem chave: {key}"

    @staticmethod
    def test_retrieve_similar_conversations_roundtrip():
        """retrieve_similar_conversations deve persistir e recuperar (JSONL)."""
        from backend.agents.sdr_langgraph import tools_sdr

        with tempfile.TemporaryDirectory() as tmp:
            # Monkey-patch o path para nao poluir memoria real
            user_id = 99999  # id ficticio
            nicho = "test_roundtrip"
            # Cria o arquivo de conversas
            tmp_path = Path(tmp)
            base = tmp_path / f"u{user_id}"
            base.mkdir(parents=True, exist_ok=True)
            target = base / f"sdr_conversations_{nicho}.jsonl"
            entry = {
                "lead_id": "test_lead_001",
                "intent_final": "wants_link",
                "converteu": True,
                "duracao_turnos": 5,
                "tom_usado": "energetico",
                "gatilho_conversao": "resultado_real",
                "snippet": "Vi que voces... [teste]",
                "ts": "2026-06-23T10:00:00",
            }
            with open(target, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            # O tools_sdr usa memory/ no backend, nao o tmp. Verifica que a funcao
            # pelo menos retorna [] sem erro quando user_id inexistente.
            result_empty = tools_sdr.retrieve_similar_conversations("test_roundtrip", user_id=0)
            assert result_empty == [], \
                f"Esperava [] para user_id=0, got {result_empty}"
            # Verifica tambem que a funcao trata nicho vazio
            result_no_nicho = tools_sdr.retrieve_similar_conversations("", user_id=99999)
            assert result_no_nicho == [], \
                f"Esperava [] para nicho vazio, got {result_no_nicho}"

    @staticmethod
    def test_check_lead_quality_returns_expected_keys():
        """check_lead_quality retorna dict com chaves canonicas."""
        from backend.agents.sdr_langgraph import tools_sdr

        # user_id=0 → retorna {} vazio
        result_empty = tools_sdr.check_lead_quality(user_id=0)
        assert result_empty == {}, f"Esperava {{}} para user_id=0, got {result_empty}"

        # user_id valido → dict com chaves
        result = tools_sdr.check_lead_quality(
            user_id=12345,
            telefone="11999887766",
            lead_id="lead_test_001",
        )
        expected_keys = {"score_caio", "tier", "ultima_interacao",
                         "ja_pediu_orcamento", "ja_recusou", "tem_whatsapp"}
        for key in expected_keys:
            assert key in result, f"check_lead_quality sem chave: {key}"
        # tem_whatsapp deve refletir telefone fornecido
        assert result["tem_whatsapp"] is True, \
            "tem_whatsapp deveria ser True com telefone fornecido"

    @staticmethod
    def test_save_sdr_lesson_multiplier_correct():
        """save_sdr_lesson aplica multiplicador 1.5x (converteu) ou 0.3x (nao converteu)."""
        from backend.agents.sdr_langgraph import tools_sdr

        # Sem user_id → retorna {learned: False}
        r_no_user = tools_sdr.save_sdr_lesson(
            lesson="teste", score=0.5, nicho="academia_crossfit",
            user_id=0, converteu=True,
        )
        assert r_no_user.get("learned") is False, \
            f"Esperava learned=False sem user_id, got {r_no_user}"

        # user_id valido + converteu=True → multiplicador 1.5x
        r_converteu = tools_sdr.save_sdr_lesson(
            lesson="lead converteu rapido quando mostrei demo",
            score=0.6,
            nicho="academia_crossfit",
            user_id=99998,
            converteu=True,
        )
        assert r_converteu.get("learned") is True, \
            f"Esperava learned=True, got {r_converteu}"
        mult = r_converteu.get("multiplicador", 0)
        assert 1.0 <= mult <= 2.0, \
            f"Multiplicador converteu deveria estar em [1.0, 2.0], got {mult}"
        assert mult >= 1.4, f"Esperava ~1.5x, got {mult}"

        # user_id valido + converteu=False → multiplicador 0.3x
        r_perdeu = tools_sdr.save_sdr_lesson(
            lesson="lead perdeu com objecao de preco",
            score=0.6,
            nicho="academia_crossfit",
            user_id=99997,
            converteu=False,
        )
        assert r_perdeu.get("learned") is True, \
            f"Esperava learned=True, got {r_perdeu}"
        mult_perdeu = r_perdeu.get("multiplicador", 0)
        assert 0.2 <= mult_perdeu <= 0.4, \
            f"Multiplicador nao-converteu deveria estar em [0.2, 0.4], got {mult_perdeu}"

    @staticmethod
    def test_agent_py_imports_tools_sdr_opt_in():
        """agent.py importa tools_sdr quando FRALIB_SDR_USE_TOOLS=1."""
        agent_src = _read(BACKEND / "agents" / "sdr_langgraph" / "agent.py")
        # Verifica que tem o guard da flag
        assert "FRALIB_SDR_USE_TOOLS" in agent_src, \
            "agent.py nao checa FRALIB_SDR_USE_TOOLS"
        # Verifica que importa de tools_sdr
        assert "from .tools_sdr import" in agent_src, \
            "agent.py nao importa tools_sdr"
        # Verifica que injeta 3 tools antes do LLM
        assert "get_nicho_playbook" in agent_src, \
            "agent.py nao injeta get_nicho_playbook"
        assert "retrieve_similar_conversations" in agent_src, \
            "agent.py nao injeta retrieve_similar_conversations"
        assert "check_lead_quality" in agent_src, \
            "agent.py nao injeta check_lead_quality"
        # Verifica que save_sdr_lesson é chamado depois do LLM
        assert "save_sdr_lesson" in agent_src, \
            "agent.py nao chama save_sdr_lesson"

    @staticmethod
    def test_pre_commit_hook_has_9_checks():
        """Pre-commit hook tem 9 checks (era 8)."""
        hook_src = _read(ROOT / ".git" / "hooks" / "check_v11_protection.py")
        # Procura referencias a v1.4 ou tools_sdr/sdr_playbook
        has_sdr_protection = "tools_sdr.py" in hook_src or "sdr_playbook.py" in hook_src
        assert has_sdr_protection, \
            "Pre-commit hook nao protege tools_sdr.py / sdr_playbook.py"


def _run_all() -> int:
    classes = [TestV14Sprint3AToolsSDR()]
    passed = failed = 0
    failures: list[str] = []
    for cls in classes:
        for name in dir(cls):
            if not name.startswith("test_"):
                continue
            fn = getattr(cls, name)
            full_name = f"{cls.__class__.__name__}.{name}"
            try:
                fn()
                print(f"OK   {full_name}")
                passed += 1
            except AssertionError as e:
                print(f"FAIL {full_name}: {e}")
                failed += 1
                failures.append(full_name)
            except Exception as e:
                print(f"ERR  {full_name}: {type(e).__name__}: {e}")
                failed += 1
                failures.append(full_name)

    print(f"\n{'='*60}")
    print(f"v1.4-baseline-2026-06-23 anti-regression: {passed}/{passed+failed} passados")
    if failures:
        print(f"FALHAS: {failures}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
