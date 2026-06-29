# 🇧🇷 GERANDO VÍDEO DA COPA DO MUNDO 🇧🇷

## Passo a Passo Rápido

### 1. Instalar ComfyUI (se ainda não fez)
```bash
start_comfyui.bat
```

### 2. Baixar Modelos Necessários
- Stable Diffusion v1.5: https://huggingface.co/runwayml/stable-diffusion-v1-5
- AnimateDiff: https://huggingface.co/guoyww/AnimateDiff

Salve em:
- `ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors`
- `ComfyUI/models/diffusion_models/motion-clipboard-v1.safetensors`

### 3. Gerar Vídeo
```bash
start_world_cup_video.bat
```

### 4. Montar Vídeo Final
Após gerar todas as cenas, execute:
```bash
cd ComfyUI
./create_world_cup_video.sh
```

## O que será gerado:
- 7 cenas animadas da Copa do Mundo
- Estilo anime consistente
- Cores brasileiras (verde e amarelo)
- Vídeo final com ~35 segundos

## Dicas:
- Use GPU para geração mais rápida
- Ajuste os prompts no arquivo `world_cup_prompts.txt`
- Adicione áudio de comemeração brasileira no final