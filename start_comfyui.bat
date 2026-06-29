@echo off
echo ========================================
echo  Iniciando ComfyUI com AnimateDiff
echo ========================================

echo.
echo 1. Instalando dependências necessárias...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r ComfyUI/requirements.txt
pip install -r ComfyUI/custom_nodes/ComfyUI-AnimateDiff-Evolved/requirements.txt

echo.
echo 2. Baixando modelos necessários...
echo.
echo Você precisa baixar os seguintes modelos:
echo - Modelos Stable Diffusion (v1-5-pruned-emaonly.safetensors)
echo - Modelos AnimateDiff (motion-clipboard-v1.safetensors)
echo.
echo Coloque-os nas pastas:
echo - ComfyUI/models/checkpoints/
echo - ComfyUI/models/diffusion_models/
echo.

echo 3. Iniciando ComfyUI...
cd ComfyUI
python main.py

echo.
echo ========================================
echo  ComfyUI iniciado!
echo  Acesse: http://localhost:8188
echo ========================================
pause