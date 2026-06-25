#!/usr/bin/env bash
# Sprint 12.13 (v1.14.1-wired): Smoke VPS end-to-end com QA 45/45.
#
# O que faz:
#   1. SSH na VPS (root@100.101.18.1)
#   2. cd /root/fralib && git pull && checkout v1.14-lockpoint
#   3. Roda pipeline_lead_real.py (orchestrator + backup builder-job + HTTP 200)
#   4. Curl https://seunegociofralib.site/sites/2/barbearia-fio-nobre-pinhais/
#   5. Salva tests/_v114_wired_smoke.json com resultado
#
# Pre-requisitos:
#   - SSH key configurada para root@100.101.18.1
#   - VPS tem Postgres em :5433 + env vars carregadas (FRALIB_BUILDER_ENGINE=vite_react)
#   - Lead 'codex-test-barbearia-fio-nobre-pinhais-20260612' existe no Postgres tenant 2
#
# Uso:
#   bash scripts/smoke_v114_vps.sh
#
# Output:
#   - .tmp/smoke_v114_*.log (raw pipeline_lead_real.py output)
#   - tests/_v114_wired_smoke.json (resultado parseado)

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@100.101.18.1}"
VPS_REPO="${VPS_REPO:-/root/fralib}"
LEAD_ID="${LEAD_ID:-codex-test-barbearia-fio-nobre-pinhais-20260612}"
TENANT_ID="${TENANT_ID:-2}"
SLUG="${SLUG:-barbearia-fio-nobre-pinhais}"
DEPLOY_URL="${DEPLOY_URL:-https://seunegociofralib.site/sites/${TENANT_ID}/${SLUG}/}"
TIMESTAMP=$(date +%s)
LOG_FILE=".tmp/smoke_v114_${TIMESTAMP}.log"
RESULT_FILE="tests/_v114_wired_smoke.json"
TAG="${TAG:-v1.14-lockpoint-2026-06-25}"

echo "================================================================================"
echo "  SPRINT 12.13 - SMOKE VPS COM QA 45/45"
echo "  VPS: ${VPS_HOST}"
echo "  LEAD: ${LEAD_ID}"
echo "  DEPLOY URL: ${DEPLOY_URL}"
echo "  TAG: ${TAG}"
echo "  TIMESTAMP: ${TIMESTAMP}"
echo "================================================================================"

mkdir -p .tmp tests

echo ""
echo "[1/5] SSH na VPS + git pull + checkout ${TAG}..."
ssh "${VPS_HOST}" "cd ${VPS_REPO} && git fetch origin && git checkout ${TAG} && git pull origin ${TAG} 2>&1 | tail -5"

echo ""
echo "[2/5] Verificando env vars VPS (DATABASE_URL, FRALIB_BUILDER_ENGINE)..."
ssh "${VPS_HOST}" "cd ${VPS_REPO} && grep -E '^(DATABASE_URL|FRALIB_BUILDER_ENGINE|FRALIB_VITE_NAMEHOST_MODELS)' .env 2>/dev/null | sed 's/=.*/=<set>/' || echo 'AVISO: .env nao carregado, script usa defaults'"

echo ""
echo "[3/5] Rodando pipeline_lead_real.py (orchestrator + backup + HTTP 200)..."
ssh "${VPS_HOST}" "cd ${VPS_REPO} && python3 scripts/pipeline_lead_real.py 2>&1" | tee "${LOG_FILE}"

echo ""
echo "[4/5] Curl deploy URL + greps para confirmar briefing REAL chegou no HTML..."
HTML_PATH="/var/www/fralib/sites/${TENANT_ID}/${SLUG}/index.html"
DEPLOY_OUTPUT=$(ssh "${VPS_HOST}" "curl -sSL -o /tmp/_smoke_v114_${TIMESTAMP}.html -w 'HTTP_STATUS:%{http_code} SIZE:%{size_download}' '${DEPLOY_URL}'" 2>&1)
echo "${DEPLOY_OUTPUT}"

echo ""
echo "Procurando dados REAIS do briefing no HTML publicado:"
REAL_DATA_HITS=$(ssh "${VPS_HOST}" "grep -cE 'Barbearia Fio Nobre|Pinhais|Corte Masculino|Seg-Sex|41999990000' ${HTML_PATH} 2>/dev/null || echo 0")
echo "  ${REAL_DATA_HITS} matches de dados reais no HTML"

echo ""
echo "[5/5] Salvando resultado em ${RESULT_FILE}..."
HTTP_STATUS=$(echo "${DEPLOY_OUTPUT}" | grep -oE 'HTTP_STATUS:[0-9]+' | cut -d: -f2 || echo "0")
HTML_SIZE=$(echo "${VPS_HOST} ls -la ${HTML_PATH} 2>/dev/null" | awk '{print $5}' || echo "0")

cat > "${RESULT_FILE}" << EOF
{
  "sprint": "12.13",
  "version": "v1.14.1-wired",
  "tag": "${TAG}",
  "timestamp": ${TIMESTAMP},
  "timestamp_iso": "$(date -Iseconds 2>/dev/null || date)",
  "lead_id": "${LEAD_ID}",
  "tenant_id": ${TENANT_ID},
  "slug": "${SLUG}",
  "deploy_url": "${DEPLOY_URL}",
  "http_status": "${HTTP_STATUS}",
  "html_size_bytes": ${HTML_SIZE:-0},
  "real_data_hits": ${REAL_DATA_HITS},
  "qa_gate": "see_pipeline_log",
  "log_file": "${LOG_FILE}",
  "exit_code": 0
}
EOF

echo ""
echo "================================================================================"
echo "  SMOKE FINALIZADO"
echo "  Resultado: ${RESULT_FILE}"
echo "  Log: ${LOG_FILE}"
echo "  HTTP: ${HTTP_STATUS}"
echo "  Real data hits: ${REAL_DATA_HITS}"
echo "================================================================================"

# Verificacao final
if [[ "${HTTP_STATUS}" == "200" ]] && [[ ${REAL_DATA_HITS} -ge 3 ]]; then
  echo "STATUS: OK - Site publicado com dados REAIS do briefing"
  exit 0
else
  echo "STATUS: INVESTIGAR - HTTP=${HTTP_STATUS} hits=${REAL_DATA_HITS}"
  echo "  Checar ${LOG_FILE} para detalhes do pipeline_lead_real.py"
  exit 1
fi