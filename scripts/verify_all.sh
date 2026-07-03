#!/bin/bash
# =============================================================================
# verify_all.sh - O "VERDE" do FraLib
# =============================================================================
# Este script é a FONTE DA VERDADE sobre se o FraLib está funcionando.
# Se este script exit code 0 = pode fazer deploy / commit.
# Se exit code != 0 = NÃO pode, tem que consertar.
#
# Spec + Loop: este é o juiz que o loop persegue.
# =============================================================================

set +e

# Detectar diretório raiz do projeto (sobe até achar AGENTS.md ou pyproject.toml)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SEARCH_ROOT="$SCRIPT_DIR"
while [ "$SEARCH_ROOT" != "/" ]; do
    if [ -f "$SEARCH_ROOT/AGENTS.md" ] || [ -f "$SEARCH_ROOT/pyproject.toml" ]; then
        PROJECT_ROOT="$SEARCH_ROOT"
        break
    fi
    SEARCH_ROOT="$(dirname "$SEARCH_ROOT")"
done
cd "$PROJECT_ROOT"
echo "📁 Projeto: $PROJECT_ROOT"

PROJECT_ROOT_NATIVE="$PROJECT_ROOT"
if command -v cygpath >/dev/null 2>&1; then
    PROJECT_ROOT_NATIVE="$(cygpath -w "$PROJECT_ROOT")"
fi

if [ -z "${PYTHON_BIN:-}" ]; then
    if command -v python.exe >/dev/null 2>&1; then
        PYTHON_BIN="python.exe"
    else
        PYTHON_BIN="python3"
    fi
fi

VERIFY_STRICT="${FRALIB_VERIFY_STRICT:-0}"
if [ "${CI:-}" = "true" ] || [ -d "/root/fralib" ]; then
    VERIFY_STRICT=1
fi

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

ok()    { echo -e "${GREEN}✅ $1${NC}"; PASS=$((PASS+1)); }
fail()  { echo -e "${RED}❌ $1${NC}"; FAIL=$((FAIL+1)); }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; WARN=$((WARN+1)); }

echo "==========================================="
echo "  FraLib VERDE Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "==========================================="
echo ""

# Carregar .env se existir (exporta variáveis para o script)
ENV_FILE="$PROJECT_ROOT/.env"

# === 1. PYTHON IMPORTS ===
echo "📦 [1/7] Imports Python críticos..."

# Usar env para carregar .env junto com o comando python
run_py() {
    if [ -f "$ENV_FILE" ]; then
        # Pega todos os argumentos exceto o primeiro (-c)
        shift
        PYTHON_CODE="$*"
        # Executa setup e o comando no mesmo processo Python.
        FRALIB_PROJECT_ROOT="$PROJECT_ROOT_NATIVE" "$PYTHON_BIN" -c "
import os, sys
root = os.environ['FRALIB_PROJECT_ROOT']
sys.path.insert(0, os.path.join(root, 'backend', 'endpoints'))
sys.path.insert(0, os.path.join(root, 'backend'))
from dotenv import dotenv_values
env = dotenv_values(os.path.join(root, '.env'))
for k, v in env.items():
    if v:
        os.environ[k] = v
os.environ.setdefault('DATABASE_URL', 'postgresql://x:x@x/x')
os.environ.setdefault('JWT_SECRET_KEY', 'x' * 32)
os.environ.setdefault('FERNET_KEY', 'x' * 32)
$PYTHON_CODE
"
    else
        DATABASE_URL="${DATABASE_URL:-postgresql://x:x@x/x}" "$PYTHON_BIN" "$@"
    fi
}

run_py -c "from backend.agents import llm_direct" 2>/dev/null && ok "llm_direct" || fail "llm_direct quebrado"
run_py -c "from backend.services import vite_react_renderer" 2>/dev/null && ok "vite_react_renderer" || fail "vite_react_renderer quebrado"
run_py -c "from backend.services import llm_router" 2>/dev/null && ok "llm_router" || fail "llm_router quebrado"
run_py -c "from backend.endpoints import pipeline_orchestrator_service" 2>/dev/null && ok "pipeline_orchestrator_service" || fail "pipeline quebrado"
run_py -c "from backend.services import lead_providers" 2>/dev/null && ok "lead_providers" || fail "lead_providers quebrado"
run_py -c "from backend.agents import design_director" 2>/dev/null && ok "design_director (novo)" || fail "design_director quebrado"
echo ""

# === 1.5 PROMPT E CONFIGURAÇÕES ===
echo "🎯 [1.5/7] Configurações críticas..."
# Vite prompt tem PT-BR?
grep -q "Brazilian Portuguese" backend/services/vite_prompts.py && ok "Vite prompt tem PT-BR" || fail "Vite prompt sem PT-BR"
# Vite prompt tem A11Y?
grep -q "ACCESSIBILITY" backend/services/vite_prompts.py && ok "Vite prompt tem A11Y" || fail "Vite prompt sem A11Y"
# Vite prompt tem SEO?
grep -q "SEO (MANDATORY)" backend/services/vite_prompts.py && ok "Vite prompt tem SEO" || fail "Vite prompt sem SEO"
# Vite prompt tem LGPD?
grep -q "LGPD" backend/services/vite_prompts.py && ok "Vite prompt tem LGPD" || fail "Vite prompt sem LGPD"
# Vite prompt tem Motion?
grep -q "MOTION" backend/services/vite_prompts.py && ok "Vite prompt tem Motion" || fail "Vite prompt sem Motion"
# Quality Gate ativo por padrão?
if grep -q "is_prompt_agent_flow" backend/services/pipeline_flow_config.py && ! grep -A3 "skip_html_quality_gate" backend/services/pipeline_flow_config.py | grep -q "is_prompt_agent_flow"; then
    ok "Quality Gate ativo por padrão"
else
    fail "Quality Gate ainda depende de is_prompt_agent_flow"
fi
# Sem imports quebrados?
BROKEN=$(grep -rE "^from (core|services|agents|endpoints|utils|database |auth |jwt_config |whatsapp_listener |sse_endpoints |config )" backend --include="*.py" 2>/dev/null | grep -v "backend\." | wc -l)
[ "$BROKEN" -eq 0 ] && ok "0 imports quebrados" || fail "$BROKEN imports quebrados"
echo ""

# === 2. SINTAXE GO (whatsmeow) ===
echo "🔧 [2/7] Compilação whatsmeow (Go)..."
if [ -d "/opt/whatsmeow_" ]; then
    cd /opt/whatsmeow_ && go build -o /tmp/meowhats_verify . 2>/dev/null && ok "whatsmeow compila" || fail "whatsmeow NÃO compila"
else
    warn "whatsmeow_ não está em /opt/whatsmeow_ (skip)"
fi
echo ""

# === 3. LINT (ruff) ===
echo "🧹 [3/7] Lint Python..."
if command -v ruff &> /dev/null; then
    ruff check backend/ --select F821 >/dev/null 2>&1 \
        && ok "Sem nomes Python indefinidos" \
        || fail "Lint F821 encontrou nomes indefinidos"

    RUFF_LOG="$(mktemp)"
    if ruff check backend/ >"$RUFF_LOG" 2>&1; then
        ok "Lint completo OK"
    else
        tail -12 "$RUFF_LOG"
        warn "Lint completo tem divida tecnica"
    fi
    rm -f "$RUFF_LOG"
else
    warn "ruff não instalado (skip)"
fi
echo ""

# === 4. TESTES UNITÁRIOS ===
echo "🧪 [4/7] Testes unitários..."
if [ -d "tests/unit" ]; then
    DB_TEST_FILES=(
        "tests/unit/test_auth_endpoints.py"
        "tests/unit/test_credits_manager.py"
        "tests/unit/test_database.py"
        "tests/unit/test_leads_endpoints.py"
        "tests/unit/test_superadmin_endpoints.py"
    )
    OFFLINE_IGNORES=()
    for test_file in "${DB_TEST_FILES[@]}"; do
        OFFLINE_IGNORES+=("--ignore=$test_file")
    done

    "$PYTHON_BIN" -m pytest tests/unit/ -x --tb=short -q \
        --confcutdir=tests/unit --no-cov \
        "${OFFLINE_IGNORES[@]}" 2>&1 | tail -12
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        ok "Testes offline passam"
    else
        fail "Testes offline falharam (ver acima)"
    fi

    TEST_DB_URL="$("$PYTHON_BIN" -c "
import os
from dotenv import dotenv_values
env = dotenv_values(os.path.join(os.environ.get('FRALIB_PROJECT_ROOT', '.'), '.env'))
print(os.getenv('TEST_DATABASE_URL') or env.get('TEST_DATABASE_URL') or 'postgresql://postgres@localhost:5433/fralib_test')
" 2>/dev/null)"

    FRALIB_PROJECT_ROOT="$PROJECT_ROOT_NATIVE" TEST_DATABASE_URL="$TEST_DB_URL" "$PYTHON_BIN" -c "
import os
from urllib.parse import urlsplit
import psycopg2
url = os.environ['TEST_DATABASE_URL']
parsed = urlsplit(url)
host = (parsed.hostname or '').lower()
db_name = parsed.path.rsplit('/', 1)[-1].lower()
if parsed.scheme not in {'postgres', 'postgresql'}:
    raise SystemExit(2)
if host not in {'', 'localhost', '127.0.0.1', '::1'} or 'test' not in db_name:
    raise SystemExit(3)
conn = psycopg2.connect(url, connect_timeout=2)
conn.close()
" >/dev/null 2>&1
    DB_PROBE_STATUS=$?

    if [ "$DB_PROBE_STATUS" -eq 0 ]; then
        TEST_DATABASE_URL="$TEST_DB_URL" "$PYTHON_BIN" -m pytest \
            "${DB_TEST_FILES[@]}" -x --tb=short -q --no-cov 2>&1 | tail -12
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            ok "Testes PostgreSQL passam"
        else
            fail "Testes PostgreSQL falharam (ver acima)"
        fi
    elif [ "$VERIFY_STRICT" = "1" ]; then
        fail "PostgreSQL de teste seguro indisponivel no modo strict"
    else
        warn "Suite PostgreSQL nao executada; use FRALIB_VERIFY_STRICT=1 no release"
    fi
else
    warn "Diretório tests/unit não encontrado"
fi
echo ""

# === 5. CONFIGURAÇÃO (.env) ===
echo "🔑 [5/7] Variáveis de ambiente críticas..."
ENV_FILE="$PROJECT_ROOT/.env"
[ -f "$ENV_FILE" ] && ok ".env existe" || fail ".env NÃO existe"

# ANTHROPIC_API_KEY configurada
grep -q "^ANTHROPIC_API_KEY=sk-" "$ENV_FILE" && ok "ANTHROPIC_API_KEY configurada" || fail "ANTHROPIC_API_KEY faltando"

# ANTHROPIC_BASE_URL apontando para kpalabz
grep -q "^ANTHROPIC_BASE_URL=https://api.kpalabz.com" "$ENV_FILE" && ok "kpalabz configurado" || fail "ANTHROPIC_BASE_URL não aponta para kpalabz"

# FERNET_KEY presente
grep -q "^FERNET_KEY=" "$ENV_FILE" && ok "FERNET_KEY presente" || warn "FERNET_KEY ausente"

# JWT_SECRET_KEY presente
grep -q "^JWT_SECRET_KEY=" "$ENV_FILE" && ok "JWT_SECRET_KEY presente" || warn "JWT_SECRET_KEY ausente"
echo ""

# === 6. SERVIÇOS (só roda na VPS) ===
echo "🚀 [6/7] Serviços (VPS)..."
if command -v pm2 &> /dev/null; then
    # Verifica se serviços estão online
    PM2_STATUS=$(pm2 jlist 2>/dev/null | "$PYTHON_BIN" -c "
import sys, json
try:
    procs = json.load(sys.stdin)
    online = sum(1 for p in procs if p.get('pm2_env', {}).get('status') == 'online')
    total = len(procs)
    print(f'{online}/{total}')
except: print('0/0')
" 2>/dev/null)
    PM2_STATUS="$(printf '%s' "$PM2_STATUS" | tr -d '\r\n ')"

    if [[ "$PM2_STATUS" == "5/5" ]]; then
        ok "PM2: todos os 5 serviços online"
    elif [[ "$PM2_STATUS" == "0/0" ]]; then
        warn "Não é VPS (PM2 vazio)"
    else
        fail "PM2: apenas $PM2_STATUS online"
    fi

    # Verifica whatsmeow (systemd)
    if systemctl is-active --quiet whatsmeow 2>/dev/null; then
        ok "whatsmeow systemd ativo"
    else
        warn "whatsmeow systemd não está ativo (pode ser local)"
    fi

    # Health check da API
    if curl -fsS http://127.0.0.1:8000/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://127.0.0.1:8000/health | "$PYTHON_BIN" -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
        if [ "$HEALTH" = "ok" ]; then
            ok "Health check: OK"
        else
            warn "Health check: $HEALTH"
        fi
    else
        warn "API não responde (não é VPS?)"
    fi
else
    warn "PM2 não instalado (não é VPS)"
fi
echo ""

# === 7. BANCO DE DADOS ===
echo "💾 [7/7] Banco de dados..."
if command -v psql &> /dev/null; then
    # Verifica falhas não resolvidas
    FALHAS=$(sudo -u postgres psql -p 5433 -d fralib_db -t -c "SELECT COUNT(*) FROM pipeline_failures WHERE resolvido = FALSE" 2>/dev/null | tr -d ' ')
    if [ -n "$FALHAS" ] && [ "$FALHAS" -gt 10 ]; then
        warn "$FALHAS falhas não resolvidas no banco"
    elif [ -n "$FALHAS" ]; then
        ok "Apenas $FALHAS falhas pendentes (< 10)"
    else
        warn "Não conseguiu consultar banco"
    fi
else
    warn "psql não disponível (não é VPS?)"
fi
echo ""

# === RESUMO ===
TOTAL=$((PASS+FAIL+WARN))
echo "==========================================="
echo "  RESUMO: $PASS ✅ / $FAIL ❌ / $WARN ⚠️"
echo "==========================================="

if [ $FAIL -eq 0 ] && [ "$VERIFY_STRICT" = "1" ]; then
    echo -e "${GREEN}🟢 VERDE RELEASE - testes offline e infraestrutura obrigatoria aprovados${NC}"
    exit 0
elif [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🟢 VERDE LOCAL - commit permitido; deploy exige FRALIB_VERIFY_STRICT=1${NC}"
    exit 0
elif [ $FAIL -le 2 ]; then
    echo -e "${YELLOW}🟡 AMARELO - deploy com cuidado${NC}"
    exit 1
else
    echo -e "${RED}🔴 VERMELHO - NÃO pode fazer deploy!${NC}"
    exit 2
fi
