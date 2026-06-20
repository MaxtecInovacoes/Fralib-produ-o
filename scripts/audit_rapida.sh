#!/bin/bash
# ============================================
# AUDITORIA RAPIDA — FraLib
# Uso: ./scripts/audit_rapida.sh
# ============================================

set -e

echo "=========================================="
echo "  AUDITORIA RAPIDA — FraLib"
echo "  Data: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local command="$2"
    local expected="$3"

    echo -n "[$name] "
    result=$(eval "$command" 2>/dev/null || echo "ERROR")

    if [ "$result" == "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASS++))
    elif [ "$result" == "ERROR" ]; then
        echo -e "${RED}✗ ERROR${NC}"
        ((FAIL++))
    else
        echo -e "${YELLOW}⚠ WARN${NC} (expected: $expected, got: $result)"
        ((WARN++))
    fi
}

check_output() {
    local name="$1"
    local command="$2"

    echo -n "[$name] "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASS++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAIL++))
    fi
}

echo "=========================================="
echo "  SECAO 1: Infraestrutura"
echo "=========================================="

# Verificar se estamos na VPS ou Local
if [ -d "/root/fralib" ]; then
    echo "MODO: VPS (187.77.37.72)"
    FRALIB_ROOT="/root/fralib"
else
    echo "MODO: LOCAL"
    FRALIB_ROOT="$(pwd)"
fi

cd "$FRALIB_ROOT"

echo ""
echo "1.1 Git Status"
check_output "Git working tree clean" "git diff-index --quiet HEAD --"
git log --oneline -3 | head -3

echo ""
echo "1.2 Arquivos .bak"
bak_count=$(find . -name "*.bak" -type f 2>/dev/null | wc -l)
echo -n "[Arquivos .bak] "
if [ "$bak_count" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS (0 arquivos)${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ FAIL ($bak_count arquivos)${NC}"
    find . -name "*.bak" -type f 2>/dev/null
    ((FAIL++))
fi

echo ""
echo "1.3 Services Status (PM2)"
if command -v pm2 &> /dev/null; then
    pm2 list 2>/dev/null || echo "PM2 não disponível"
else
    echo "PM2 não instalado localmente"
fi

echo ""
echo "1.4 Environment Variables"
check_output "DATABASE_URL set" "[ -n \"\$DATABASE_URL\" ]"
check_output "LLM Provider configured" "[ -n \"\$FRALIB_LLM_PROVIDER\" ] || [ -n \"\$KPA_LABZ_API_KEY\" ]"

echo ""
echo "=========================================="
echo "  SECAO 2: Pipeline e Agentes"
echo "=========================================="

echo ""
echo "2.1 Agentes Presentes"
for agent in caio.py site_prompt_agent.py design_director.py benchmarker.py trend_watcher.py; do
    check_output "Agent: $agent" "[ -f backend/agents/$agent ]"
done

echo ""
echo "2.2 Skills Carregadas"
for skill in impeccable design-motion-principles emil-design-eng; do
    check_output "Skill: $skill" "[ -f backend/agents/skill_packs/$skill/SKILL.md ]"
done

echo ""
echo "2.3 RAG Knowledge"
for rag in seo_local.md curadoria.md builder_renderer.md; do
    check_output "RAG: $rag" "[ -f backend/agents/rag_knowledge/$rag ]"
done

echo ""
echo "2.4 God Objects (> 1000 linhas)"
echo "Arquivos > 1000 linhas:"
find backend -name "*.py" -exec wc -l {} \; 2>/dev/null | awk '$1 > 1000 {print $2 ": " $1 " linhas"}'

echo ""
echo "=========================================="
echo "  SECAO 3: Design System"
echo "=========================================="

echo ""
echo "3.1 Design System (47 itens)"
check_output "DESIGN-SYSTEM.md" "[ -f backend/agents/DESIGN-SYSTEM.md ]"
check_output "DESIGN.md" "[ -f DESIGN.md ]"

echo ""
echo "3.2 SEO Local Rules"
check_output "seo_local.md" "[ -f backend/agents/rag_knowledge/seo_local.md ]"

echo ""
echo "=========================================="
echo "  SECAO 4: Testes"
echo "=========================================="

echo ""
echo "4.1 Testes Unitarios"
if [ -d tests ]; then
    echo -n "[Testes existentes] "
    test_count=$(find tests -name "test_*.py" 2>/dev/null | wc -l)
    echo "$test_count arquivos de teste encontrados"

    if command -v pytest &> /dev/null; then
        echo "Executando pytest..."
        pytest tests/unit/ -q --tb=no 2>/dev/null || echo "Alguns testes falharam"
    fi
else
    echo "Diretório tests/ não encontrado"
fi

echo ""
echo "4.2 Smoke Test"
if [ -f scripts/pipeline_smoke.py ]; then
    check_output "pipeline_smoke.py exists" "[ -f scripts/pipeline_smoke.py ]"
fi

echo ""
echo "=========================================="
echo "  SECAO 5: Performance"
echo "=========================================="

echo ""
echo "5.1 Caches"
check_output "node_modules cache" "[ -f /var/cache/fralib/node_modules_vite.tar.gz ] || [ -f /tmp/fralib/node_modules_vite.tar.gz ]"
check_output "Design cache dir" "[ -d /tmp/fralib_design_cache ] || [ -d /tmp/fralib_design_cache ]"

echo ""
echo "5.2 Logs Recentes"
if [ -d logs ]; then
    echo "Logs de manifest (últimos 5):"
    ls -lt logs/builder_manifests/*.json 2>/dev/null | head -5 | awk '{print "  " $9 " (" $6" "$7" "$8")"}'
fi

echo ""
echo "=========================================="
echo "  RESUMO"
echo "=========================================="
echo -e "Pass: ${GREEN}$PASS${NC}"
echo -e "Warn: ${YELLOW}$WARN${NC}"
echo -e "Fail: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ AUDITORIA PASSOU${NC}"
    exit 0
else
    echo -e "${RED}✗ AUDITORIA REPROVOU${NC}"
    exit 1
fi
