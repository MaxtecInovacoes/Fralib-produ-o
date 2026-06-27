"""
Teste de consolidacao ESTADO_TO_STAGE - ITEM 2 do plano SDR 10/10

VERIFICA:
1. connection_tracker.py define ESTADO_TO_STAGE (fonte unica)
2. compat.py importa ESTADO_TO_STAGE de connection_tracker
3. O dicionario tem todas as chaves esperadas
"""
import ast
import sys
import os

# Setup path - adicionar backend como raiz
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.dirname(__file__))  # scripts dir

# Importar ESTADO_TO_STAGE diretamente do arquivo para evitar problemas de import
_tracker_path = os.path.join(BACKEND_DIR, 'whatsapp', 'connection_tracker.py')
_exec_globals = {'__file__': _tracker_path, '__name__': '__main__'}
with open(_tracker_path, 'r', encoding='utf-8') as f:
    exec(compile(f.read(), _tracker_path, 'exec'), _exec_globals)
ESTADO_TO_STAGE = _exec_globals['ESTADO_TO_STAGE']

def test_estado_to_stage_defined_in_connection_tracker():
    """Verifica que connection_tracker.py define ESTADO_TO_STAGE"""
    path = os.path.join(BACKEND_DIR, 'whatsapp', 'connection_tracker.py')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'ESTADO_TO_STAGE' in content, "connection_tracker.py deve definir ESTADO_TO_STAGE"

    # Verifica que e uma definicao de dicionario
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'ESTADO_TO_STAGE':
                    assert isinstance(node.value, ast.Dict), "ESTADO_TO_STAGE deve ser um dict"
                    return

    raise AssertionError("ESTADO_TO_STAGE nao encontrado como definicao em connection_tracker.py")


def test_compat_imports_from_connection_tracker_data():
    """Verifica que compat.py importa ESTADO_TO_STAGE de connection_tracker"""
    global ESTADO_TO_STAGE

    # Carrega compat.py e verifica que tem o import correto
    compat_path = os.path.join(BACKEND_DIR, 'agents', 'sdr_langgraph', 'compat.py')
    with open(compat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verifica que tem o import de ESTADO_TO_STAGE
    assert 'from backend.whatsapp.connection_tracker import ESTADO_TO_STAGE' in content, \
        "compat.py deve importar ESTADO_TO_STAGE de backend.whatsapp.connection_tracker"

    # Executa compat.py em namespace isolado e verifica que define ESTADO_TO_STAGE
    compat_globals = {'ESTADO_TO_STAGE': ESTADO_TO_STAGE}  # Mock the import
    # Mas na verdade, o compat.py NAO deve definir localmente - verifica isso
    lines = content.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Ignora comentarios e imports
        if stripped.startswith('#') or stripped.startswith('from ') or stripped.startswith('import '):
            continue
        # Verifica se e uma definicao de variavel (nao comentariosInline)
        if 'ESTADO_TO_STAGE' in line and '=' in line and not '==' in line:
            # Extrai o nome da variavel antes do =
            var_part = line.split('=')[0].strip()
            if var_part == 'ESTADO_TO_STAGE':
                raise AssertionError(
                    f"compat.py define ESTADO_TO_STAGE localmente na linha {i+1} - "
                    "deve importar de connection_tracker"
                )


def test_estado_to_stage_has_expected_keys():
    """Verifica que ESTADO_TO_STAGE tem todas as chaves esperadas"""
    global ESTADO_TO_STAGE

    # Chaves esperadas (todas as que estavam em algum dos dois dicionarios originais)
    expected_keys = {
        # Stages novos (Franz prompt v2)
        "intro", "qualify", "proof", "link", "value", "price", "negotiate", "close", "won", "lost",
        # Stages legados
        "hook", "pain", "amplify", "tease", "reveal", "feedback", "urgency",
        "followup1", "followup2", "rapport", "education", "negotiation", "offer",
        "qualificado", "handoff", "scheduled",
        # Estagios extras do compat.py
        "opt_out", "followup_24h", "followup_72h",
    }

    actual_keys = set(ESTADO_TO_STAGE.keys())
    missing = expected_keys - actual_keys

    assert not missing, f"ESTADO_TO_STAGE esta faltando chaves: {missing}"

    # Verifica que todos os valores sao strings
    for key, value in ESTADO_TO_STAGE.items():
        assert isinstance(value, str), f"Valor de '{key}' deve ser string, got {type(value)}"
        assert isinstance(key, str), f"Chave '{key}' deve ser string"


def test_estado_to_stage_values_are_valid_stages():
    """Verifica que todos os valores mapeiam para stages validos"""
    global ESTADO_TO_STAGE

    valid_stages = {
        "intro", "followup1", "followup2", "negociacao",
        "ganhos", "perdidos", "qualificados"
    }

    for key, stage in ESTADO_TO_STAGE.items():
        assert stage in valid_stages, f"'{key}' -> '{stage}' nao e um stage valido"


def test_compat_uses_imported_constant():
    """Verifica que compat.py tem import correto de ESTADO_TO_STAGE"""
    global ESTADO_TO_STAGE

    # Carrega compat.py e verifica o import
    compat_path = os.path.join(BACKEND_DIR, 'agents', 'sdr_langgraph', 'compat.py')
    with open(compat_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verifica que tem o import correto
    assert 'from backend.whatsapp.connection_tracker import ESTADO_TO_STAGE' in content, \
        "compat.py deve importar ESTADO_TO_STAGE de backend.whatsapp.connection_tracker"

    # Verifica que o import esta no topo do arquivo (antes de qualquer uso)
    lines = content.split('\n')
    import_line_idx = None
    for i, line in enumerate(lines):
        if 'from backend.whatsapp.connection_tracker import ESTADO_TO_STAGE' in line:
            import_line_idx = i
            break

    assert import_line_idx is not None, "Import deve estar presente"
    assert import_line_idx < 30, f"Import deve estar no topo do arquivo (linha {import_line_idx+1})"


def test_no_other_files_define_estado_to_stage():
    """Verifica que nenhum outro arquivo define ESTADO_TO_STAGE"""
    backend_dir = BACKEND_DIR

    files_with_definition = []

    for root, dirs, files in os.walk(backend_dir):
        # Pula diretorios de terceiros ou caches
        if any(x in root for x in ['__pycache__', '.git', 'venv', 'node_modules']):
            continue

        for file in files:
            if not file.endswith('.py'):
                continue

            path = os.path.join(root, file)

            # Pula connection_tracker.py (e a fonte)
            if 'connection_tracker.py' in path:
                continue

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Procura definicao local de ESTADO_TO_STAGE (nao import)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Ignora comentarios e imports
                if stripped.startswith('#'):
                    continue
                if 'from ' in stripped or 'import ' in stripped:
                    continue
                # Procura definicao
                if 'ESTADO_TO_STAGE' in line and '=' in line and not '==' in line:
                    var_name = line.split('=')[0].strip()
                    if var_name == 'ESTADO_TO_STAGE':
                        rel_path = os.path.relpath(path, backend_dir)
                        files_with_definition.append(f"{rel_path}:{i+1}")

    assert not files_with_definition, \
        f"ESTADO_TO_STAGE definido em outros arquivos (deve ser apenas connection_tracker.py): {files_with_definition}"


if __name__ == '__main__':
    print("Executando testes de consolidacao ESTADO_TO_STAGE...")
    print()

    tests = [
        test_estado_to_stage_defined_in_connection_tracker,
        test_compat_imports_from_connection_tracker_data,
        test_estado_to_stage_has_expected_keys,
        test_estado_to_stage_values_are_valid_stages,
        test_compat_uses_imported_constant,
        test_no_other_files_define_estado_to_stage,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}")
            print(f"        {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}")
            print(f"        {e}")
            failed += 1

    print()
    print(f"Resultados: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
