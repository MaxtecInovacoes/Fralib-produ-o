#!/usr/bin/env bash
# =============================================================================
# test_email_send.sh - Enviar email de teste via Resend API
# =============================================================================
# Uso:
#   ./test_email_send.sh                    # usa variaveis do .env
#   ./test_email_send.sh "seu@email.com"   # override destinatario
#
# Requer:
#   - curl
#   - RESEND_API_KEY e FROM_EMAIL em ../.env (ou exportados)
#   - Opcional: mail-tester.com para score de spam
#
# Saida esperada:
#   {"id": "xxx", "from": "...", "to": [...], "created_at": "..."}
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(cd "$SCRIPT_DIR/.." && pwd)/.env"

# Carregar .env se existir
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

# Variaveis obrigatorias
RESEND_API_KEY="${RESEND_API_KEY:-}"
FROM_EMAIL="${FROM_EMAIL:-noreply@seunegociofralib.site}"
APP_URL="${APP_URL:-https://seunegociofralib.site}"

# Destinatario: argumento ou valor padrao
DESTinatario="${1:-}"

# Destinatario padrao se nao informado
if [[ -z "$DESTinatario" ]]; then
  DESTinatario="teste-spam-$(date +%s)@mail-tester.com"
  echo "[INFO] Nenhum destinatario informado. Usando mail-tester: $DESTinatario"
  echo "[INFO] Registre este endereco em https://mail-tester.com ANTES de executar."
  echo ""
fi

# Validacao
if [[ -z "$RESEND_API_KEY" ]]; then
  echo "[ERRO] RESEND_API_KEY nao esta definida." >&2
  echo "  Edite .env ou export RESEND_API_KEY=re_xxx" >&2
  exit 1
fi

echo "========================================"
echo " Teste de Envio de Email - FraLib"
echo "========================================"
echo "  De:    $FROM_EMAIL"
echo "  Para:  $DESTinatario"
echo "  API:   https://api.resend.com/emails"
echo "========================================"
echo ""

# HTML do email de teste
HTML_PAYLOAD=$(cat <<'MAIL'
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>Teste FraLib OS</title>
</head>
<body style="margin:0;padding:0;background-color:#08080c;font-family:Arial,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%">
<tr>
<td align="center" style="padding:40px 16px;">
<table cellpadding="0" cellspacing="0" width="100%" style="max-width:520px;">
<tr>
<td style="padding-bottom:24px;text-align:center;">
<img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib OS" width="120" />
</td>
</tr>
<tr>
<td style="background:#12121a;border-radius:12px;border:1px solid #1e1e2e;padding:40px;">
<h1 style="margin:0 0 16px;font-size:18px;color:#ffffff;">Teste de Email</h1>
<p style="margin:0 0 16px;font-size:14px;color:#a1a1aa;">
Este email foi enviado automaticamente pelo servico <strong>FraLib OS</strong>
via Resend API para verificar a entrega correta.
</p>
<p style="margin:0;font-size:12px;color:#52525b;">
Se voce recebeu esta mensagem, o servico de email esta funcionando.
</p>
</td>
</tr>
<tr>
<td style="padding-top:24px;text-align:center;">
<p style="margin:0;font-size:11px;color:#3f3f46;">FraLib OS - Sites com IA para negocios locais</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>
MAIL
)

# Construir payload JSON (escapar HTML para JSON)
PAYLOAD=$(jq -n \
  --arg from "FraLib <${FROM_EMAIL}>" \
  --arg to "$DESTinatario" \
  --argjson html "$HTML_PAYLOAD" \
  '{
    from: $from,
    to: [$to],
    subject: "[TESTE] Email FraLib funcionando",
    html: $html
  }'
)

# Enviar via curl
echo "[INFO] Enviando requisicao para api.resend.com..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "https://api.resend.com/emails" \
  -H "Authorization: Bearer ${RESEND_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "[HTTP $HTTP_CODE]"
echo ""

if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "201" ]]; then
  echo "[OK] Email enviado com sucesso!"
  echo ""
  echo "Resposta da API:"
  echo "$BODY" | jq .
  echo ""

  # Verificar se dominio tem SPF/DKIM/DMARC
  DOMAIN=$(echo "$FROM_EMAIL" | sed 's/.*@//')
  echo "========================================"
  echo " Verificacao de Autenticacao DNS"
  echo "========================================"
  echo ""
  echo "Checando registros para: $DOMAIN"
  echo ""
  echo "SPF:"
  dig +short TXT "$DOMAIN" 2>/dev/null | grep -i spf || echo "  (nao encontrado)"
  echo ""
  echo "DKIM (resend._domainkey):"
  dig +short TXT "resend._domainkey.$DOMAIN" 2>/dev/null | head -1 || echo "  (nao encontrado)"
  echo ""
  echo "DMARC:"
  dig +short TXT "_dmarc.$DOMAIN" 2>/dev/null | head -1 || echo "  (nao encontrado)"
  echo ""

else
  echo "[ERRO] Falha ao enviar email."
  echo ""
  echo "Resposta da API:"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  echo ""
  exit 1
fi
