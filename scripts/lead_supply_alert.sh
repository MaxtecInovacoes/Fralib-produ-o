#!/bin/bash
#
# lead_supply_alert.sh - Alert logging and notification script
# Usage: lead_supply_alert.sh <severity> <title> <message>
# Severity: CRITICAL, warning, info
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="/var/log/lead_supply_alerts.log"
RESEND_API_URL="https://api.resend.com/emails"

# Default values (can be overridden by env vars)
RESEND_FROM_EMAIL="${RESEND_FROM_EMAIL:-alerts@leadsupply.com.br}"
RESEND_TO_EMAIL="${RESEND_TO_EMAIL:-admin@leadsupply.com.br}"

# Validate arguments
if [ $# -lt 3 ]; then
    echo -e "${RED}ERROR: Missing arguments${NC}" >&2
    echo "Usage: $0 <severity> <title> <message>" >&2
    echo "  severity: CRITICAL, warning, info" >&2
    exit 1
fi

SEVERITY="$1"
TITLE="$2"
MESSAGE="$3"

# Validate severity
case "${SEVERITY^^}" in
    CRITICAL|WARNING|INFO)
        SEVERITY_UPPER="${SEVERITY^^}"
        ;;
    *)
        echo -e "${RED}ERROR: Invalid severity '$SEVERITY'. Must be CRITICAL, warning, or info${NC}" >&2
        exit 1
        ;;
esac

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log to file
log_message="[${TIMESTAMP}] [${SEVERITY_UPPER}] [${TITLE}] ${MESSAGE}"
echo "${log_message}" >> "${LOG_FILE}" 2>/dev/null || {
    echo "WARNING: Could not write to ${LOG_FILE}" >&2
}

# Color and display based on severity
case "${SEVERITY_UPPER}" in
    CRITICAL)
        COLOR="${RED}"
        echo -e "${COLOR}[CRITICAL] [${TITLE}]${NC} ${MESSAGE}"
        ;;
    WARNING)
        COLOR="${YELLOW}"
        echo -e "${COLOR}[WARNING] [${TITLE}]${NC} ${MESSAGE}"
        ;;
    INFO)
        COLOR="${GREEN}"
        echo -e "${COLOR}[INFO] [${TITLE}]${NC} ${MESSAGE}"
        ;;
esac

# Send email for CRITICAL and WARNING only
if [ "${SEVERITY_UPPER}" = "CRITICAL" ] || [ "${SEVERITY_UPPER}" = "WARNING" ]; then
    if [ -n "${RESEND_API_KEY:-}" ]; then
        echo "Sending email notification via Resend API..."

        # Escape JSON special characters
        ESCAPED_TITLE=$(echo "${TITLE}" | sed 's/"/\\"/g' | sed "s/'/'/g")
        ESCAPED_MESSAGE=$(echo "${MESSAGE}" | sed 's/"/\\"/g' | sed "s/'/'/g")

        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${RESEND_API_URL}" \
            -H "Authorization: Bearer ${RESEND_API_KEY}" \
            -H "Content-Type: application/json" \
            -d "{
                \"from\": \"${RESEND_FROM_EMAIL}\",
                \"to\": [\"${RESEND_TO_EMAIL}\"],
                \"subject\": \"[${SEVERITY_UPPER}] ${TITLE}\",
                \"html\": \"<h2>${ESCAPED_TITLE}</h2><p>${ESCAPED_MESSAGE}</p><hr><p><em>Timestamp: ${TIMESTAMP}</em></p>\"
            }")

        HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)
        BODY=$(echo "${RESPONSE}" | sed '$d')

        if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "201" ]; then
            echo -e "${GREEN}Email sent successfully${NC}"
        else
            echo -e "${YELLOW}Failed to send email. HTTP code: ${HTTP_CODE}${NC}" >&2
            echo "Response: ${BODY}" >&2
        fi
    else
        echo -e "${YELLOW}RESEND_API_KEY not set - skipping email notification${NC}" >&2
    fi
fi

exit 0
