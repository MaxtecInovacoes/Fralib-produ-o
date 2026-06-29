@echo off
chcp 65001 >nul
echo ================================================
echo      🇧🇷 GERADOR DE VÍDEO DA COPA DO MUNDO 🇧🇷
echo ================================================
echo.

echo 🎬 Este script vai gerar um vídeo animado sobre a Copa do Mundo
echo    com cenas icônicas do futebol brasileiro!
echo.

echo 📋 Passos:
echo    1. Gerar prompts detalhados com IA
echo    2. Criar cenas animadas com ComfyUI
echo    3. Montar vídeo final com FFmpeg
echo.

echo 🚀 Começando a geração...
echo.

python generate_world_cup_video.py

echo.
echo ================================================
echo ✅ Processo concluído!
echo.
echo 📁 Verifique a pasta "ComfyUI/output/world_cup_scene_*"
echo 🎬 Execute "create_world_cup_video.sh" para montar o vídeo
echo ================================================
pause