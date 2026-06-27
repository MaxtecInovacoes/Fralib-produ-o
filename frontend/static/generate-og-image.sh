#!/bin/bash

# Instalar dependências se necessário
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não encontrado. Instale o Node.js primeiro."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm não encontrado. Instale o npm primeiro."
    exit 1
fi

# Instalar Puppeteer
echo "📦 Instalando Puppeteer..."
npm install puppeteer

# Gerar imagem
echo "🎨 Gerando imagem OG..."
node generate-og-image.js

if [ -f "og-image.png" ]; then
    echo "✅ Imagem OG gerada com sucesso!"
    echo "📍 Caminho: C:/fralib/frontend/static/og-image.png"
    echo "🔗 Copie este arquivo para o diretório raiz do site para funcionar corretamente"
else
    echo "❌ Falha ao gerar imagem OG"
    exit 1
fi