# Gerador de Vídeos com ComfyUI e KPLabs

Este sistema permite gerar vídeos a partir de roteiros usando:
- **KPLabs API**: Para expandir roteiros em prompts detalhados
- **ComfyUI + AnimateDiff**: Para gerar imagens e animações
- **FFmpeg**: Para montar o vídeo final

## Instalação

### 1. Pré-requisitos
- Python 3.8+
- GPU com suporte a CUDA (recomendado)
- Pelo menos 8GB de VRAM

### 2. Instalação
```bash
# Baixar e instalar dependências
start_comfyui.bat

# Ou manualmente:
cd ComfyUI
pip install -r requirements.txt
pip install -r custom_nodes/ComfyUI-AnimateDiff-Evolved/requirements.txt
```

### 3. Download de Modelos
Baixe os modelos e coloque nas pastas correspondentes:

#### Modelos Stable Diffusion
- Baixe de: https://huggingface.co/runwayml/stable-diffusion-v1-5
- Salve em: `ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors`

#### Modelos AnimateDiff
- Baixe de: https://huggingface.co/guoyww/AnimateDiff
- Salve em: `ComfyUI/models/diffusion_models/motion-clipboard-v1.safetensors`

## Uso

### Método 1: Usando o script Python
```python
from video_generator import VideoGenerator

generator = VideoGenerator()

# Seu roteiro
script = """
CENA 1: Robô começa a andar por uma rua futurista
CENA 2: O robô encontra um alienígena
CENA 3: Eles se tornam amigos
"""

# Gerar vídeo
generator.generate_video_from_script(script)
```

### Método 2: Interface Web
1. Inicie o ComfyUI:
```bash
cd ComfyUI
python main.py
```

2. Acesse: http://localhost:8188

3. Use o workflow de AnimateDiff para gerar cenas

## Fluxo de Trabalho

1. **Escreva o roteiro**
   - Descreva cenas simplesmente
   - O sistema expandirá em prompts detalhados

2. **Geração de cenas**
   - Cada cena é gerada como uma sequência de frames
   - AnimateDiff adiciona movimento às imagens

3. **Montagem final**
   - Use FFmpeg para juntar as cenas
   - Adicione áudio se necessário

## Exemplo de Workflow no ComfyUI

```
[CLIPTextEncode] → [CheckpointLoaderSimple] → [KSampler] 
     ↓                    ↓                    ↓
[Prompt] → [Modelo SD] → [Frames animados]
     ↓
[VAEDecode] → [SaveImage]
```

## Dicas

1. **Qualidade**: Use prompts específicos para resultados melhores
2. **Performance**: Reduza a resolução se for lento
3. **Estilo**: Use LoRAs para estilos específicos
4. **Movimento**: Ajuste o motion strength no AnimateDiff

## Troubleshooting

- **Erro de memória**: Reduza o batch size ou resolução
- **Modelos não encontrados**: Verifique os caminhos dos downloads
- **API KPLABS**: Verifique sua chave de API

## Próximos Passos

1. Implementar áudio com ElevenLabs
2. Adicionar LoRAs para estilos específicos
3. Criar templates de workflows pré-configurados
4. Implementar batch processing para múltiplos vídeos