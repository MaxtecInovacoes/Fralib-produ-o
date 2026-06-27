#!/bin/bash
# ===========================================
# FraLib OS - Script de Deploy/Update
# ===========================================
# Uso: bash update.sh
# ===========================================

set -e

echo "🔄 FraLib OS - Atualizando..."
echo "================================"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Diretório do projeto (ajuste se necessário)
PROJECT_DIR="/var/www/fralib"

# Verifica se o diretório existe
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Diretório não encontrado: $PROJECT_DIR${NC}"
    echo "   Ajuste PROJECT_DIR no script ou execute do diretório correto."
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${YELLOW}📁 Diretório: $(pwd)${NC}"

# Mostra commits recentes
echo ""
echo "📋 Últimos commits:"
git log --oneline -5

# Pull das atualizações
echo ""
echo -e "${YELLOW}⬇️  Fazendo git pull...${NC}"
git pull origin master

# Verifica se houve mudanças
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pull concluído com sucesso!${NC}"
else
    echo -e "${RED}❌ Erro no git pull${NC}"
    exit 1
fi

# Limpa cache do Nginx
echo ""
echo -e "${YELLOW}🔄 Recarregando Nginx...${NC}"
sudo systemctl reload nginx 2>/dev/null || sudo service nginx reload 2>/dev/null || echo "   (Nginx não encontrado, pulando...)"

# Limpa cache do Apache (se usar Apache)
sudo systemctl reload apache2 2>/dev/null || sudo service apache2 reload 2>/dev/null || echo "   (Apache não encontrado, pulando...)"

# Limpa cache do PHP-FPM (se usar)
sudo systemctl reload php-fpm 2>/dev/null || sudo systemctl reload php* 2>/dev/null || echo "   (PHP-FPM não encontrado, pulando...)"

# Verifica se as otimizações foram aplicadas
echo ""
echo -e "${YELLOW}🔍 Verificando otimizações...${NC}"

OPTIMIZACOES=$(curl -s https://seunegociofralib.site/ | grep -c "preconnect" || echo "0")
echo "   - Preconnect tags: $OPTIMIZACOES"

# Verifica se Meta Pixel está no head (não deveria estar)
META_PIXEL=$(curl -s https://seunegociofralib.site/ | grep -A2 "Meta Pixel" | grep -c "<script>" || echo "0")
echo "   - Meta Pixel no head: $META_PIXEL (esperado: 0)"

echo ""
echo -e "${GREEN}🎉 Atualização concluída!${NC}"
echo ""
echo "📊 Próximos passos:"
echo "   1. Teste PageSpeed: https://pagespeed.web.dev"
echo "   2. Verifique se LCP melhorou (<2.5s)"
echo "   3. Teste no celular em navegação anônima"
echo ""
