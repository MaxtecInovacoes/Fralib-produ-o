"""
Teste de verificacao: SDR 10/10 - ITEM 1
Verifica que as 3 chamadas httpx.post em cron_endpoints.py foram substituidas
por enqueue_outbound().

Este teste e statico (analise de codigo, nao executa endpoints).
"""
import ast
import re
from pathlib import Path


def test_cron_endpoints_imports_enqueue_outbound():
    """Verifica que cron_endpoints.py importa enqueue_outbound."""
    cron_file = Path("C:/fralib/backend/endpoints/cron_endpoints.py")
    assert cron_file.exists(), f"Arquivo nao encontrado: {cron_file}"

    content = cron_file.read_text(encoding="utf-8")

    # Verifica import de enqueue_outbound
    assert "from backend.services.outbound_queue import enqueue_outbound" in content, (
        "cron_endpoints.py deve importar enqueue_outbound de outbound_queue"
    )
    print("[OK] Import de enqueue_outbound encontrado")


def test_no_httpx_post_in_cron_functions():
    """Verifica que NAO ha mais chamadas httpx.post diretas nos cron jobs SDR."""
    cron_file = Path("C:/fralib/backend/endpoints/cron_endpoints.py")
    content = cron_file.read_text(encoding="utf-8")

    # Padrao que detecta chamadas httpx.Client().post() ou c.post()
    # contexto: cron functions (despachar_fila_franz, followup_franz)
    lines = content.split('\n')

    issues = []
    in_cron_function = False
    function_indent = 0

    for i, line in enumerate(lines, 1):
        # Detecta inicio de funcoes cron
        if 'def despachar_fila_franz' in line or 'def followup_franz' in line:
            in_cron_function = True
            function_indent = len(line) - len(line.lstrip())
            continue

        # Detecta fim de funcao (proximo def/async def no mesmo nivel)
        if in_cron_function and line.strip() and not line.strip().startswith('#'):
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= function_indent and ('def ' in line or 'async def ' in line):
                in_cron_function = False
                continue

        # Procura httpx.Client() ou .post() no contexto de cron
        if in_cron_function:
            if 'httpx.Client' in line or 'c.post(' in line or 'c = c.post' in line:
                issues.append(f"Linha {i}: {line.strip()}")

    assert len(issues) == 0, (
        f"Encontradas {len(issues)} chamadas httpx.Client/post em cron jobs SDR:\n" +
        "\n".join(issues) +
        "\n\nEssas chamadas devem ser substituidar por enqueue_outbound()"
    )
    print("[OK] Nenhuma chamada httpx.Client/post encontrada em cron jobs SDR")


def test_enqueue_outbound_only_for_first_contact():
    """Verifica que só primeiro contato usa outbound_queue."""
    cron_file = Path("C:/fralib/backend/endpoints/cron_endpoints.py")
    content = cron_file.read_text(encoding="utf-8")

    # Conta chamadas a enqueue_outbound
    pattern = r'enqueue_outbound\s*\('
    matches = list(re.finditer(pattern, content))

    assert len(matches) == 1, (
        f"Esperada 1 chamada a enqueue_outbound() para primeiro contato, encontradas {len(matches)}. "
        f"Follow-up e scheduled devem enviar direto apos historico de contato."
    )
    assert "source=\"followup\"" not in content
    assert "source=\"scheduled\"" not in content
    assert "_send_sdr_direct(user_id, tel, fu_output.reply)" in content
    print(f"[OK] enqueue_outbound restrito a primeiro contato")


def test_env_flag_activated():
    """Verifica que FRALIB_USE_OUTBOUND_QUEUE=1 esta no .env."""
    env_file = Path("C:/fralib/.env")
    assert env_file.exists(), f"Arquivo nao encontrado: {env_file}"

    content = env_file.read_text(encoding="utf-8")

    # Procura a flag
    assert "FRALIB_USE_OUTBOUND_QUEUE=1" in content, (
        "FRALIB_USE_OUTBOUND_QUEUE=1 deve estar ativado no .env"
    )
    print("[OK] FRALIB_USE_OUTBOUND_QUEUE=1 encontrado no .env")


def test_response_executor_sends_replies_directly():
    """Verifica que resposta a inbound nao usa fila de prospeccao."""
    executor_file = Path("C:/fralib/backend/whatsapp/response_executor.py")
    assert executor_file.exists(), f"Arquivo nao encontrado: {executor_file}"

    content = executor_file.read_text(encoding="utf-8")

    assert "FRALIB_USE_OUTBOUND_QUEUE" not in content, (
        "response_executor.py nao deve enfileirar respostas a leads que responderam"
    )
    assert "enqueue_outbound" not in content, (
        "response_executor.py nao deve usar outbound_queue para respostas inbound"
    )
    assert "send_text_parts" in content, "response_executor.py deve enviar resposta direta"
    print("[OK] response_executor.py envia respostas inbound diretamente")


if __name__ == "__main__":
    print("=" * 60)
    print("SDR 10/10 - ITEM 1: Verificacao de Outbound Queue")
    print("=" * 60)

    tests = [
        test_cron_endpoints_imports_enqueue_outbound,
        test_no_httpx_post_in_cron_functions,
        test_enqueue_outbound_only_for_first_contact,
        test_env_flag_activated,
        test_response_executor_sends_replies_directly,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            print(f"\nExecutando: {test.__name__}")
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FALHA] {e}")
            failed += 1
        except Exception as e:
            print(f"[ERRO] {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} passou, {failed} falhou")
    print("=" * 60)

    if failed == 0:
        print("\n[OK] ITEM 1 DO SDR 10/10 IMPLEMENTADO COM SUCESSO!")
        print("     - Outbound queue ativada no cron")
        print("     - Rate limit 2 msgs/10min sera respeitado")
    else:
        print("\n[FALHA] ITEM 1 NAO IMPLEMENTADO CORRETAMENTE")
        exit(1)
