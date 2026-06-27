"""
Teste de unificacao: verifica que nao ha mais httpx.post direto para /send
nos arquivos de endpoints SDR (exceto fila outbound).

Executar: python -m pytest scripts/test_unified_send.py -v
"""
import ast
import re
import sys
from pathlib import Path


# Arquivos que devem usar send_text_parts ou enqueue_outbound
ARQUIVOS_SDR = [
    "backend/endpoints/cron_endpoints.py",
    "backend/endpoints/leads_crud_sdr.py",
]

# Padrao que indica chamada direta httpx.post para /send
# (exceto fila outbound que usa /api/sessions/default/send)
PATTERN_DIRECT_SEND = re.compile(
    r"httpx\.Async?Client.*?\.post\s*\(\s*"
    r"f?[\"'].*/api/sessions/\{?[\w_]+\}?/send[\"']",
    re.DOTALL | re.IGNORECASE
)

# Padrao para identificar uso de send_text_parts
PATTERN_SEND_TEXT_PARTS = re.compile(
    r"send_text_parts\s*\(",
    re.IGNORECASE
)

# Padrao para identificar uso de enqueue_outbound
PATTERN_ENQUEUE = re.compile(
    r"enqueue_outbound\s*\(",
    re.IGNORECASE
)


def extract_httpx_calls(filepath: str) -> list[tuple[int, str]]:
    """Extrai todas as chamadas httpx.post() de um arquivo."""
    calls = []
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
        for i, line in enumerate(content.splitlines(), 1):
            # Verificar se a linha contem httpx.post para /send
            if "httpx" in line.lower() and ".post(" in line.lower():
                # Verificar se e uma chamada direta para /send (nao outbound queue)
                if "/send" in line and "default" not in line.lower():
                    calls.append((i, line.strip()))
    return calls


def test_no_direct_httpx_send_in_sdr_endpoints():
    """Verifica que cron_endpoints.py e leads_crud_sdr.py nao usam httpx.post direto para /send."""
    erros = []

    for arquivo in ARQUIVOS_SDR:
        path = Path(arquivo)
        if not path.exists():
            erros.append(f"ARQUIVO NAO ENCONTRADO: {arquivo}")
            continue

        calls = extract_httpx_calls(arquivo)
        if calls:
            for linha, codigo in calls:
                erros.append(f"{arquivo}:{linha} - httpx.post direto para /send:\n  {codigo}")

    assert not erros, "Encontradas chamadas diretas httpx.post para /send:\n" + "\n".join(erros)


def test_send_text_parts_is_imported():
    """Verifica que send_text_parts esta importado nos arquivos SDR."""
    erros = []

    for arquivo in ARQUIVOS_SDR:
        path = Path(arquivo)
        if not path.exists():
            erros.append(f"ARQUIVO NAO ENCONTRADO: {arquivo}")
            continue

        with open(arquivo, encoding="utf-8") as f:
            content = f.read()

        if "send_text_parts" not in content and "enqueue_outbound" not in content:
            erros.append(f"{arquivo} - nao importa send_text_parts nem enqueue_outbound")

    assert not erros, "Arquivos sem import de funcao de envio unificada:\n" + "\n".join(erros)


def test_save_interaction_comes_from_single_source():
    """Verifica que _salvar_interacao vem de whatsapp_listener (unica fonte canonica)."""
    erros = []

    for arquivo in ARQUIVOS_SDR:
        path = Path(arquivo)
        if not path.exists():
            continue

        with open(arquivo, encoding="utf-8") as f:
            content = f.read()

        # Verificar imports
        if "_salvar_interacao" in content:
            # Deve vir de whatsapp_listener
            if "from backend.whatsapp_listener import" in content:
                if "_salvar_interacao" in content.split("from backend.whatsapp_listener import")[1].split("\n")[0]:
                    continue  # OK
            erros.append(f"{arquivo} - _salvar_interacao pode nao vir de whatsapp_listener")

    assert not erros, "Problemas com origem de _salvar_interacao:\n" + "\n".join(erros)


def test_send_text_parts_signature():
    """Verifica que send_text_parts existe e tem a assinatura correta."""
    sender_path = Path("backend/whatsapp/sender.py")
    assert sender_path.exists(), "sender.py nao encontrado"

    with open(sender_path, encoding="utf-8") as f:
        content = f.read()

    assert "def send_text_parts" in content, "send_text_parts nao definido em sender.py"

    # Verificar assinatura: send_text_parts(http_client, base_url, api_key, tenant_id, jid, parts, ...)
    sig_pattern = re.compile(
        r"def send_text_parts\s*\([^)]*http_client[^)]*base_url[^)]*api_key[^)]*tenant_id[^)]*jid[^)]*parts",
        re.IGNORECASE | re.DOTALL
    )
    assert sig_pattern.search(content), "Assinatura de send_text_parts incorreta"


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE: Unificacao de save_interaction e envio WhatsApp")
    print("=" * 60)

    # Testes via pytest
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))