"""Testes anti-regressao v1.12 - Sprint 9 (Edge Cases + Production Hardening).

Valida:
- edge_cases.py existe e tem 6 funcoes principais
- safe_normalize_text lida com None/vazio/unicode
- safe_jsonl_iter pula linhas malformadas (com warn)
- db_retry succeed apos exceptions transientes
- assert_tenant_access bloqueia acesso cross-tenant
- safe_write_file trata disk-full (mock)
- with_timeout retorna fallback se exceder
- tracing.get_stats usa safe_jsonl_iter (tolera malformed)
- Modulo edge_cases e importavel sem side-effects

Suite consolidada deve manter 22+8*8+10 (v1.0 + v1.1..v1.8 + v1.11 + v1.12).
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Diretorio temporario para nao poluir o repo durante testes
_TMP = Path(tempfile.mkdtemp(prefix="fralib_v112_"))
os.environ["FRALIB_TRACING"] = "0"  # tracing OFF durante testes
os.environ["FRALIB_IDEMPOTENCY_DIR"] = str(_TMP / "_idempotency")
os.environ["FRALIB_TRACES_DIR"] = str(_TMP / "_traces")
os.environ["FRALIB_PROMPTS_V2_DIR"] = str(_TMP / "_prompts_v2")


# ════════════════════════════════════════════════════════════════════
# TESTES
# ════════════════════════════════════════════════════════════════════

def test_1_safe_normalize_handles_none_empty():
    """safe_normalize_text lida com None, vazio, whitespace."""
    print("[TESTE 1/10] safe_normalize_text - None/vazio/whitespace...")
    from backend.services.edge_cases import safe_normalize_text

    # None -> string vazia
    assert safe_normalize_text(None) == ""

    # String vazia -> string vazia
    assert safe_normalize_text("") == ""

    # Whitespace only -> string vazia
    assert safe_normalize_text("   ") == ""
    assert safe_normalize_text("\t\n\r") == ""

    # String normal -> strip aplicada
    assert safe_normalize_text("  hello  ") == "hello"

    # Control chars removidos (mantem tab/newline)
    assert safe_normalize_text("ab\x00\x01cd") == "abcd"
    assert safe_normalize_text("a\tb\nc") == "a\tb\nc"  # tab/newline preservados

    # Tipo nao-str -> convertido (best-effort)
    assert safe_normalize_text(123) == "123"
    assert safe_normalize_text(True) == "True"

    print("  OK None/vazio/whitespace tratados")
    print("  OK Control chars removidos (tab/newline preservados)")
    print("  OK Tipos nao-str convertidos com seguranca")


def test_2_safe_normalize_handles_unicode():
    """safe_normalize_text normaliza unicode (NFC)."""
    print("\n[TESTE 2/10] safe_normalize_text - Unicode...")
    from backend.services.edge_cases import safe_normalize_text

    # NFD (decomposed) -> NFC (composed)
    nfd = "Café"  # Cafe + combining acute
    nfc = "Café"  # placeholder, replaced below
    nfc_correct = "Café"
    # Note: both nfd and the composed form should normalize to the same NFC
    assert safe_normalize_text(nfd) == nfc_correct, \
        f"NFD nao normalizado: {safe_normalize_text(nfd)!r}"

    # Acentos comuns em PT-BR
    assert safe_normalize_text("  ação  ") == "ação"
    assert safe_normalize_text("São Paulo") == "São Paulo"
    assert safe_normalize_text("Não") == "Não"

    # Emojis (NFD nao muda, mas strip ok)
    assert "🚀" in safe_normalize_text("  🚀 launch  ")

    # Caractere chines
    assert safe_normalize_text("你好") == "你好"

    print("  OK Unicode NFD -> NFC normalizado")
    print("  OK Acentos PT-BR preservados (ação, São, Não)")
    print("  OK Emojis + chines preservados")


def test_3_safe_jsonl_skips_malformed():
    """safe_jsonl_iter pula linhas malformadas (com warn)."""
    print("\n[TESTE 3/10] safe_jsonl_iter - malformed skip...")
    from backend.services.edge_cases import safe_jsonl_iter

    # Cria arquivo com mix de valido + invalido
    jsonl_path = _TMP / "mixed.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        f.write('{"a": 1, "agent": "nicho"}\n')
        f.write("\n")  # linha vazia
        f.write('LINHA QUEBRADA SEM JSON\n')
        f.write('{"b": 2, "agent": "arquiteto"}\n')
        f.write('{"c": 3}\n')
        f.write('[1,2,3]\n')  # nao e dict
        f.write('{"d": 4, "agent": "nicho"}\n')

    results = list(safe_jsonl_iter(jsonl_path))
    assert len(results) == 4, f"Esperado 4 dicts validos, obtido {len(results)}"
    assert results[0] == {"a": 1, "agent": "nicho"}
    assert results[1] == {"b": 2, "agent": "arquiteto"}
    assert results[2] == {"c": 3}
    assert results[3] == {"d": 4, "agent": "nicho"}

    # Arquivo inexistente -> iterator vazio
    empty = list(safe_jsonl_iter(_TMP / "nao_existe.jsonl"))
    assert empty == [], "Arquivo inexistente deve retornar iterator vazio"

    print("  OK 4 dicts validos parseados (linhas quebradas puladas)")
    print("  OK Linha vazia pulada silenciosamente")
    print("  OK [1,2,3] (nao-dict) pulado")
    print("  OK Arquivo inexistente -> iterator vazio")


def test_4_db_retry_succeeds():
    """db_retry succeed apos exceptions transientes."""
    print("\n[TESTE 4/10] db_retry - retry ate succeed...")
    from backend.services.edge_cases import db_retry

    call_count = {"n": 0}

    @db_retry(max_attempts=3, backoff=1.1)
    def flaky_func() -> str:
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise ConnectionError("DB unreachable")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert call_count["n"] == 2, f"Esperado 2 tentativas, obtido {call_count['n']}"

    # Exceder max_attempts -> propaga ultima excecao
    @db_retry(max_attempts=2, backoff=1.0)
    def always_fail() -> None:
        raise ConnectionError("DB ainda down")

    try:
        always_fail()
        assert False, "Deveria ter levantado ConnectionError"
    except ConnectionError:
        pass

    # Excecao nao-transiente -> propaga imediatamente sem retry
    call_count2 = {"n": 0}

    @db_retry(max_attempts=5, backoff=1.0)
    def non_transient() -> None:
        call_count2["n"] += 1
        raise ValueError("Erro de logica, nao transiente")

    try:
        non_transient()
        assert False
    except ValueError:
        pass
    assert call_count2["n"] == 1, "Nao-transiente nao deve retentar"

    print("  OK Retry succeed em 2 tentativas (1 ConnectionError + 1 ok)")
    print("  OK Exceder max_attempts propaga ConnectionError")
    print("  OK Excecao nao-transiente NAO retry (propaga imediato)")


def test_5_assert_tenant_access_blocks_cross():
    """assert_tenant_access bloqueia cross-tenant, permite mesmo tenant."""
    print("\n[TESTE 5/10] assert_tenant_access - cross-tenant block...")
    from backend.services.edge_cases import assert_tenant_access, TenantAccessError

    # Mesmo user_id -> OK (sem raise)
    assert_tenant_access(42, 42)
    assert_tenant_access("user_1", "user_1")
    # int vs str (mesmo valor) -> OK (compara como string)
    assert_tenant_access(42, "42")

    # Cross-tenant -> TenantAccessError
    try:
        assert_tenant_access(42, 99)
        assert False, "Deveria ter levantado TenantAccessError"
    except TenantAccessError as e:
        assert e.user_id == 42
        assert e.resource_user_id == 99
        assert "Cross-tenant" in str(e)

    # None em qualquer lado -> TenantAccessError
    try:
        assert_tenant_access(None, 42)
        assert False
    except TenantAccessError:
        pass

    try:
        assert_tenant_access(42, None)
        assert False
    except TenantAccessError:
        pass

    print("  OK Mesmo user_id (mesmo tenant) permitido")
    print("  OK int vs str (mesmo valor) permitido")
    print("  OK Cross-tenant bloqueado com TenantAccessError")
    print("  OK None em qualquer lado -> raise")


def test_6_concurrent_jobs_idempotent():
    """is_idempotent_action + register_action simulam jobs concorrentes."""
    print("\n[TESTE 6/10] Idempotencia - concurrent jobs...")
    from backend.services.edge_cases import is_idempotent_action, register_action

    # Limpa locks antigos
    lock_dir = Path(os.environ["FRALIB_IDEMPOTENCY_DIR"])
    if lock_dir.exists():
        for f in lock_dir.glob("*.lock"):
            f.unlink()

    action_key = "job:12345:render:openui"

    # Primeira vez -> NAO idempotente (pode executar)
    assert is_idempotent_action(action_key, ttl_seconds=60) is False

    # Registra
    assert register_action(action_key) is True

    # Segunda vez (imediatamente) -> idempotente (pula)
    assert is_idempotent_action(action_key, ttl_seconds=60) is True

    # Apos TTL expirar (simulado) -> pode executar de novo
    lock_path = lock_dir / "job_12345_render_openui.lock"
    if lock_path.exists():
        # Set mtime para 100s atras (TTL=60s)
        old_time = time.time() - 100
        os.utime(lock_path, (old_time, old_time))

    assert is_idempotent_action(action_key, ttl_seconds=60) is False, \
        "Apos TTL expirar deve permitir re-execucao"

    # Keys diferentes sao independentes
    assert is_idempotent_action("job:9999:render:openui", ttl_seconds=60) is False

    print("  OK 1a chamada: is_idempotent=False (pode executar)")
    print("  OK register_action registra lock")
    print("  OK 2a chamada: is_idempotent=True (pula)")
    print("  OK Apos TTL expirar: is_idempotent=False (re-executa)")
    print("  OK Keys diferentes sao independentes")


def test_7_safe_write_file_handles_disk_full():
    """safe_write_file retorna False em OSError (disk full simulado)."""
    print("\n[TESTE 7/10] safe_write_file - disk full mock...")
    from backend.services.edge_cases import safe_write_file

    target = _TMP / "disk_full_test.txt"
    target_content = "conteudo de teste"

    # Caso normal: escreve OK
    assert safe_write_file(target, target_content) is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == target_content

    # Mock OSError "No space left" no os.replace (atomic rename)
    target2 = _TMP / "disk_full_test2.txt"
    with patch("os.replace", side_effect=OSError(28, "No space left on device")):
        result = safe_write_file(target2, "x")
        assert result is False, "Deve retornar False em ENOSPC"

    # Mock PermissionError
    target3 = _TMP / "perm_test.txt"
    with patch("builtins.open", side_effect=PermissionError("denied")):
        result = safe_write_file(target3, "y")
        assert result is False, "Deve retornar False em PermissionError"

    # Path em dir invalido -> cria parent automaticamente
    deep = _TMP / "a" / "b" / "c" / "deep.txt"
    assert safe_write_file(deep, "deep content") is True
    assert deep.exists()

    print("  OK Escrita normal retorna True")
    print("  OK Mock OSError ENOSPC -> False (atomic write protege)")
    print("  OK Mock PermissionError -> False")
    print("  OK Diretorios pai criados automaticamente")


def test_8_with_timeout_returns_fallback():
    """with_timeout retorna fallback se funcao exceder limite."""
    print("\n[TESTE 8/10] with_timeout - fallback on timeout...")
    from backend.services.edge_cases import with_timeout

    # Funcao rapida -> retorna resultado real
    @with_timeout(seconds=1.0, fallback="FALLBACK_OK")
    def fast() -> str:
        return "RESULT_OK"

    assert fast() == "RESULT_OK"

    # Funcao lenta -> retorna fallback
    @with_timeout(seconds=0.2, fallback="FALLBACK_OK")
    def slow() -> str:
        time.sleep(1.5)  # excede timeout
        return "NUNCA_CHEGA"

    start = time.time()
    result = slow()
    elapsed = time.time() - start

    assert result == "FALLBACK_OK", f"Esperado FALLBACK_OK, obtido {result}"
    assert elapsed < 1.0, f"Deveria retornar rapido (~0.2s), levou {elapsed:.2f}s"

    # Funcao que levanta excecao -> propaga (NAO timeout)
    @with_timeout(seconds=2.0, fallback="FB")
    def raises() -> None:
        raise RuntimeError("erro de logica")

    try:
        raises()
        assert False
    except RuntimeError as e:
        assert "erro de logica" in str(e)

    # Fallback None
    @with_timeout(seconds=0.1, fallback=None)
    def slow_none() -> str:
        time.sleep(0.5)
        return "X"

    assert slow_none() is None

    print("  OK Funcao rapida retorna resultado real")
    print("  OK Funcao lenta retorna fallback em ~0.2s (nao espera 1.5s)")
    print("  OK Excecao normal propaga (NAO trata como timeout)")
    print("  OK fallback=None respeitado")


def test_9_tracing_get_stats_tolerates_malformed():
    """tracing.get_stats usa safe_jsonl_iter (tolera linhas malformadas)."""
    print("\n[TESTE 9/10] tracing.get_stats - malformed tolerance...")
    from backend.services import tracing

    # Force-enable para teste
    original_enabled = tracing.TRACING_ENABLED
    original_traces_dir = tracing.TRACES_DIR
    tracing.TRACING_ENABLED = True
    tracing.TRACES_DIR = Path(os.environ["FRALIB_TRACES_DIR"])

    try:
        # Cria arquivo de trace com linha quebrada para HOJE
        import datetime as _dt
        today = _dt.datetime.now().strftime("%Y-%m-%d")
        trace_path = tracing.TRACES_DIR / f"traces_{today}.jsonl"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "agent": "nicho", "success": True, "latency_ms": 100,
                "cost_usd": 0.01, "input_tokens": 50, "output_tokens": 25
            }) + "\n")
            f.write("LINHA_INVALIDA_JSON\n")  # quebra proposital
            f.write('{"agent":"nicho","success":true,"latency_ms":50,"cost_usd":0.005}\n')

        # get_stats NAO deve crashar com linha quebrada (days=1 = so hoje)
        stats = tracing.get_stats(agent="nicho", days=1)

        # safe_jsonl_iter pulou a linha quebrada + parseou 2 validas
        assert stats["count"] == 2, f"Esperado count=2, obtido {stats['count']}"
        assert stats["errors"] == 0
        assert stats["total_latency_ms"] == 150
    finally:
        tracing.TRACING_ENABLED = original_enabled
        tracing.TRACES_DIR = original_traces_dir

    # Cleanup
    if trace_path.exists():
        trace_path.unlink()

    print("  OK Arquivo com linha JSON quebrada NAO crasha get_stats")
    print("  OK safe_jsonl_iter pulou a linha + parseou 2 validas")
    print("  OK Stats agregadas corretas (count=2, latency=150ms)")


def test_10_edge_cases_module_importable():
    """edge_cases.py importavel sem side-effects + 6 funcoes principais."""
    print("\n[TESTE 10/10] edge_cases module importable...")
    from backend.services import edge_cases

    # 6 funcoes principais
    required = [
        "safe_normalize_text",
        "safe_jsonl_iter",
        "db_retry",
        "assert_tenant_access",
        "safe_write_file",
        "with_timeout",
    ]
    for name in required:
        assert hasattr(edge_cases, name), f"Funcao {name} nao encontrada"
        assert callable(getattr(edge_cases, name)), f"{name} nao e callable"

    # Helpers bonus (idempotencia)
    assert hasattr(edge_cases, "is_idempotent_action")
    assert hasattr(edge_cases, "register_action")
    assert hasattr(edge_cases, "TenantAccessError")

    # Verifica docstrings em todas as funcoes
    for name in required + ["is_idempotent_action", "register_action"]:
        fn = getattr(edge_cases, name)
        assert fn.__doc__, f"{name} deve ter docstring"
        assert "Example" in fn.__doc__ or ">>>" in fn.__doc__, \
            f"{name} deve ter exemplo de uso no docstring"

    print("  OK 6 funcoes principais: safe_normalize/jsonl_iter/db_retry/assert_tenant/safe_write/with_timeout")
    print("  OK Helpers bonus: is_idempotent_action, register_action, TenantAccessError")
    print("  OK Docstrings + exemplos presentes em todas as funcoes")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSAO v1.12 - Sprint 9 (Edge Cases + Production Hardening)")
    print("=" * 80)

    test_1_safe_normalize_handles_none_empty()
    test_2_safe_normalize_handles_unicode()
    test_3_safe_jsonl_skips_malformed()
    test_4_db_retry_succeeds()
    test_5_assert_tenant_access_blocks_cross()
    test_6_concurrent_jobs_idempotent()
    test_7_safe_write_file_handles_disk_full()
    test_8_with_timeout_returns_fallback()
    test_9_tracing_get_stats_tolerates_malformed()
    test_10_edge_cases_module_importable()

    print("\n" + "=" * 80)
    print("TODOS OS TESTES PASSARAM (10/10)")
    print("Sprint 9 (v1.12) - Edge Cases + Production Hardening integrado com sucesso")
    print("=" * 80)