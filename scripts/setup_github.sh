#!/bin/bash
# =============================================================================
# setup_github.sh - Configura token do GitHub para backup automatico
# =============================================================================
# Uso: ./scripts/setup_github.sh SEU_TOKEN
# Exemplo: ./scripts/setup_github.sh SEU_TOKEN_GITHUB_AQUI
# =============================================================================

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TOKEN="$1"
REPO_URL="https://github.com/MaxtecInovacoes/Fralib-produ-o.git"

if [ -z "$TOKEN" ]; then
    echo -e "${RED}ERRO: precisa passar o token como argumento${NC}"
    echo ""
    echo "Como criar o token:"
    echo "  1. https://github.com/settings/tokens"
    echo "  2. Generate new token (classic)"
    echo "  3. Marque apenas 'repo'"
    echo "  4. Copie o token"
    echo ""
    echo "Uso: ./scripts/setup_github.sh SEU_TOKEN_GITHUB_AQUI"
    exit 1
fi

echo "==========================================="
echo "  Configurando GitHub Backup"
echo "==========================================="
echo ""

# Configurar remote com token embutido
AUTHED_URL="https://${TOKEN}@github.com/MaxtecInovacoes/Fralib-produ-o.git"
git remote set-url github "$AUTHED_URL" 2>&1

echo "[1/3] Remote do GitHub configurado com token"
echo ""

# Testar conexão
echo "[2/3] Testando conexão com GitHub..."
if git ls-remote github master >/dev/null 2>&1; then
    echo -e "  ${GREEN}[OK] Conexao com GitHub funcionando!${NC}"
else
    echo -e "  ${RED}[ERRO] Nao conseguiu conectar. Verifique o token.${NC}"
    exit 1
fi

echo ""

# Fazer primeiro push
echo "[3/3] Fazendo primeiro push para GitHub..."
if git push github master 2>&1; then
    echo -e "  ${GREEN}[OK] Codigo enviado para GitHub!${NC}"
    echo ""
    echo "==========================================="
    echo -e "  ${GREEN}CONFIGURACAO COMPLETA!${NC}"
    echo "==========================================="
    echo ""
    echo "Agora todo commit sera enviado automaticamente para:"
    echo "  - VPS (origin)"
    echo "  - GitHub (backup nuvem)"
    echo ""
    echo "Veja seu codigo em:"
    echo "  https://github.com/MaxtecInovacoes/Fralib-produ-o"
else
    echo -e "  ${YELLOW}[WARN] Push falhou. Tente manualmente:${NC}"
    echo "  git push github master"
fi

echo ""
echo "IMPORTANTE: o token foi salvo na URL do remote."
echo "Para remover depois: git remote set-url github $REPO_URL"
