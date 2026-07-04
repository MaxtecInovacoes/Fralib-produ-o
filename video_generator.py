"""Script para gerar vídeos usando ComfyUI com prompts da API KPLabs."""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# SEGURANÇA (Sprint 12.x): chave NUNCA hardcoded — obrigatória via env var.
KPLABS_API_KEY = os.environ.get("KPLABS_API_KEY")
if not KPLABS_API_KEY:
    raise RuntimeError(
        "KPLABS_API_KEY nao configurada. Defina no .env antes de usar este script."
    )


class VideoGenerator:
    def __init__(self) -> None:
        # Configurações — chave via env var (nunca mais hardcoded)
        self.kplabs_api: str = "https://ia.namehost.com.br"
        self.kplabs_key: str = KPLABS_API_KEY
        self.comfyui_url: str = "http://localhost:8188"

        # Diretórios
        self.base_dir: Path = Path("C:/fralib/ComfyUI")
        self.input_dir: Path = self.base_dir / "input"
        self.output_dir: Path = self.base_dir / "output"

        # Criar diretórios necessários
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def generate_detailed_prompts(self, script):
        """Usar Claude 3 via KPLabs para gerar prompts detalhados"""
        print("Gerando prompts detalhados com KPLabs...")

        prompt = f"""
        Com base neste roteiro, gere prompts detalhados para cada cena:

        Roteiro: {script}

        Para cada cena, retorne em formato JSON:
        {{
            "scene_number": 1,
            "description": "Descrição visual detalhada",
            "prompt": "Prompt para Stable Diffusion",
            "negative_prompt": "O que evitar na imagem",
            "duration": 5,
            "style": "anime style"
        }}

        Retorne apenas o JSON válido, sem outras explicações.
        """

        response = requests.post(
            f"{self.kplabs_api}/v1/messages",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.kplabs_key}"
            },
            json={
                "model": "claude-3-opus-20240229",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # Extrair JSON da resposta
            start = content.find('[')
            end = content.rfind(']') + 1
            return json.loads(content[start:end])
        else:
            print(f"Erro na API KPLabs: {response.status_code}")
            return []

    def create_comfyui_workflow(self, scenes):
        """Criar workflow do ComfyUI para gerar vídeo"""
        print("Criando workflow do ComfyUI...")

        # Workflow básico com AnimateDiff
        workflow = {
            "last_node_id": 10,
            "last_link_id": 10,
            "nodes": [
                {
                    "id": 1,
                    "type": "CLIPTextEncode",
                    "pos": [50, 50],
                    "size": {"0": 422.84503173828125, "1": 164.61553955078125},
                    "flags": {},
                    "order": 0,
                    "mode": "default",
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "CLIP",
                            "type": "CLIP",
                            "links": [2],
                            "slot_index": 0
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "CLIPTextEncode"
                    },
                    "widgets_values": ["robot walking through futuristic city"]
                },
                {
                    "id": 2,
                    "type": "CheckpointLoaderSimple",
                    "pos": [50, 250],
                    "size": {"0": 315.815, "1": 98.34375},
                    "flags": {},
                    "order": 1,
                    "mode": "default",
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "MODEL",
                            "type": "MODEL",
                            "links": [3],
                            "slot_index": 0
                        },
                        {
                            "name": "CLIP",
                            "type": "CLIP",
                            "links": [4],
                            "slot_index": 1
                        },
                        {
                            "name": "VAE",
                            "type": "VAE",
                            "links": [5],
                            "slot_index": 2
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "CheckpointLoaderSimple"
                    },
                    "widgets_values": ["v1-5-pruned-emaonly.safetensors"]
                },
                {
                    "id": 3,
                    "type": "KSampler",
                    "pos": [50, 450],
                    "size": {"0": 315, "1": 262},
                    "flags": {},
                    "order": 2,
                    "mode": "default",
                    "inputs": [
                        {
                            "name": "model",
                            "type": "MODEL",
                            "link": 3
                        },
                        {
                            "name": "positive",
                            "type": "CLIP",
                            "link": 4
                        },
                        {
                            "name": "negative",
                            "type": "CLIP",
                            "link": 6
                        },
                        {
                            "name": "latent_image",
                            "type": "LATENT",
                            "link": 7
                        }
                    ],
                    "outputs": [
                        {
                            "name": "LATENT",
                            "type": "LATENT",
                            "links": [8],
                            "slot_index": 0
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "KSampler"
                    },
                    "widgets_values": [1020176, "fixed", 20, 7, "euler", "normal", 1]
                },
                {
                    "id": 4,
                    "type": "CLIPTextEncode",
                    "pos": [50, 50],
                    "size": {"0": 422.84503173828125, "1": 164.61553955078125},
                    "flags": {},
                    "order": 0,
                    "mode": "default",
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "CLIP",
                            "type": "CLIP",
                            "links": [6],
                            "slot_index": 0
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "CLIPTextEncode"
                    },
                    "widgets_values": ["blurry, bad quality, distorted"]
                },
                {
                    "id": 5,
                    "type": "EmptyLatentImage",
                    "pos": [50, 350],
                    "size": {"0": 315, "1": 106},
                    "flags": {},
                    "order": 1,
                    "mode": "default",
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "LATENT",
                            "type": "LATENT",
                            "links": [7],
                            "slot_index": 0
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "EmptyLatentImage"
                    },
                    "widgets_values": [512, 512, 1]
                },
                {
                    "id": 6,
                    "type": "VAEDecode",
                    "pos": [50, 650],
                    "size": {"0": 210, "1": 46},
                    "flags": {},
                    "order": 3,
                    "mode": "default",
                    "inputs": [
                        {
                            "name": "samples",
                            "type": "LATENT",
                            "link": 8
                        },
                        {
                            "name": "vae",
                            "type": "VAE",
                            "link": 5
                        }
                    ],
                    "outputs": [
                        {
                            "name": "IMAGE",
                            "type": "IMAGE",
                            "links": [9],
                            "slot_index": 0
                        }
                    ],
                    "properties": {
                        "Node name for S&R": "VAEDecode"
                    },
                    "widgets_values": []
                },
                {
                    "id": 7,
                    "type": "SaveImage",
                    "pos": [50, 750],
                    "size": {"0": 210.76458740234375, "1": 106},
                    "flags": {},
                    "order": 4,
                    "mode": "default",
                    "inputs": [
                        {
                            "name": "images",
                            "type": "IMAGE",
                            "link": 9
                        }
                    ],
                    "outputs": [],
                    "properties": {
                        "Node name for S&R": "SaveImage",
                        "Node name for S&R::Filename": "robot_scene_1"
                    },
                    "widgets_values": ["output/robot_scene_1.png", "png"]
                }
            ],
            "links": [
                [2, 1, 0, 3, 0, "CLIP"],
                [3, 2, 0, 3, 0, "MODEL"],
                [4, 2, 1, 3, 1, "CLIP"],
                [5, 2, 2, 5, 0, "VAE"],
                [6, 4, 0, 3, 2, "CLIP"],
                [7, 5, 0, 3, 3, "LATENT"],
                [8, 3, 0, 6, 0, "LATENT"],
                [9, 6, 0, 7, 0, "IMAGE"]
            ],
            "groups": [],
            "config": {},
            "extra": {},
            "version": 0.4
        }

        return workflow

    def queue_workflow(self, workflow):
        """Enviar workflow para o ComfyUI"""
        print("Enviando workflow para ComfyUI...")

        response = requests.post(
            f"{self.comfyui_url}/prompt",
            json={"prompt": workflow}
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao enviar workflow: {response.status_code}")
            return None

    def get_queue_status(self):
        """Verificar status da fila do ComfyUI"""
        response = requests.get(f"{self.comfyui_url}/queue")
        if response.status_code == 200:
            return response.json()
        return None

    def get_history(self, number):
        """Obter histórico de execuções"""
        response = requests.get(f"{self.comfyui_url}/history/{number}")
        if response.status_code == 200:
            return response.json()
        return None

    def generate_video_from_script(self, script, output_filename="output_video"):
        """Função principal: gerar vídeo a partir de roteiro"""
        print("Iniciando geração de vídeo...")

        # 1. Gerar prompts com KPLabs
        scenes = self.generate_detailed_prompts(script)
        if not scenes:
            print("Nenhuma cena gerada")
            return

        print(f"Gerando {len(scenes)} cenas...")

        # 2. Gerar cada cena
        all_frames = []
        for i, scene in enumerate(scenes):
            print(f"\nProcessando Cena {i+1}: {scene['description']}")

            # Atualizar prompt no workflow
            workflow = self.create_comfyui_workflow([scene])

            # Enviar para ComfyUI
            prompt_id = self.queue_workflow(workflow)
            if prompt_id:
                # Aguardar conclusão
                while True:
                    history = self.get_history(prompt_id)
                    if history and str(prompt_id) in history:
                        if history[str(prompt_id)]['status'] == 'success':
                            break
                        elif history[str(prompt_id)]['status'] == 'error':
                            print(f"Erro na geração da cena {i+1}")
                            break
                    time.sleep(2)

            # Mover imagens geradas para pasta final
            scene_output = self.output_dir / f"scene_{i+1}"
            scene_output.mkdir(exist_ok=True)

            # Encontrar imagens geradas
            for file in self.output_dir.glob("*.png"):
                if "robot_scene" in file.name:
                    new_name = scene_output / f"frame_{file.name}"
                    file.rename(new_name)

        print("\nGeração de cenas concluída!")
        print(f"Imagens salvas em: {self.output_dir}")
        print("Você pode agora usar um editor de vídeo para montar as cenas.")

        # 3. Criar script de montagem
        self.create_video_script(scenes, output_filename)

    def create_video_script(self, scenes, output_filename):
        """Criar script para montagem do vídeo"""
        script_content = f"""#!/bin/bash
# Script de montagem de vídeo com FFmpeg

# Configurações
FRAMES_PER_SCENE=16
FPS=8
OUTPUT_VIDEO="{output_filename}.mp4"

# Criar vídeo
ffmpeg \\
  -framerate {FPS} \\
  -i output/scene_%d/frame_%d.png \\
  -c:v libx264 \\
  -pix_fmt yuv420p \\
  -crf 18 \\
  -preset slow \\
  "{OUTPUT_VIDEO}"

echo "Vídeo final criado: $OUTPUT_VIDEO"
"""

        with open(self.base_dir / "create_video.sh", "w") as f:
            f.write(script_content)

        print(f"\nScript de montagem criado: {self.base_dir}/create_video.sh")
        print("Execute este script para montar o vídeo final.")

# Exemplo de uso
if __name__ == "__main__":
    generator = VideoGenerator()

    # Exemplo de roteiro
    script = """
    CENA 1: Robô começa a andar por uma rua futurista com neon
    CENA 2: O robô encontra um alienígena
    CENA 3: Eles conversam e se tornam amigos
    """

    # Gerar vídeo
    generator.generate_video_from_script(script)