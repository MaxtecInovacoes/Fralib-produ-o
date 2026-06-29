#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar video animado da Copa do Mundo do Brasil
"""

import requests
import json
import time
from pathlib import Path

class WorldCupVideoGenerator:
    def __init__(self):
        self.kplabs_api = "https://api.kpalabz.com"
        self.kplabs_key = "sk-kpa-fa199fc49d1744a966e0ab4055ea5b11f39bc6bb24619465b68dbfbdc2e9746a"
        self.comfyui_url = "http://localhost:8188"

    def generate_world_cup_prompts(self):
        """Gerar prompts para video da Copa do Mundo"""
        print("Gerando prompts para video da Copa do Mundo...")

        # Prompts pre-definidos para a Copa do Mundo
        scenes = [
            {
                "scene_number": 1,
                "description": "Bandeira do Brasil sendo hasteada",
                "prompt": "Brazilian flag waving in the wind, green and yellow colors, epic cinematic lighting, dramatic clouds, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 2,
                "description": "Pelé driblando",
                "prompt": "Football legend Pelé dribbling, Brazilian stadium background, dramatic lighting, action pose, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 3,
                "description": "Neymar celebrando",
                "prompt": "Neymar celebrating goal, Brazilian jersey number 10, green and yellow confetti, happy crowd, epic moment, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 4,
                "description": "Torcida brasileira",
                "prompt": "Brazilian football fans celebrating, green and yellow colors, waving flags, packed stadium, festive atmosphere, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 5,
                "description": "Gol com fogos",
                "prompt": "Football goal celebration with fireworks, Brazilian colors, gold trophy, golden light rays, epic victory, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 6,
                "description": "Taça da Copa",
                "prompt": "Golden World Cup trophy, Brazilian colors, rays of light, floating in space, golden particles, majestic, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            },
            {
                "scene_number": 7,
                "description": "Brasil Campeao",
                "prompt": "Brazil champion text with trophy, green and yellow flames, fireworks, golden text, celebration, epic, masterpiece",
                "negative_prompt": "blurry, low quality, distorted"
            }
        ]

        return scenes

    def queue_workflow(self, workflow):
        """Enviar workflow para o ComfyUI"""
        try:
            response = requests.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("prompt_id")
        except Exception as e:
            print(f"Erro ao conectar com ComfyUI: {e}")
        return None

    def get_history(self, prompt_id):
        """Obter historico de execucoes"""
        try:
            response = requests.get(f"{self.comfyui_url}/history/{prompt_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def generate_world_cup_video(self):
        """Gerar video completo da Copa do Mundo"""
        print("=" * 60)
        print("GERADOR DE VIDEO - COPA DO MUNDO DO BRASIL")
        print("=" * 60)

        # Verificar conexao com ComfyUI
        try:
            response = requests.get(f"{self.comfyui_url}/system_stats", timeout=5)
            if response.status_code != 200:
                print("ERRO: ComfyUI nao esta rodando!")
                print("Execute primeiro: cd ComfyUI && python main.py")
                return
        except:
            print("ERRO: Nao foi possivel conectar ao ComfyUI!")
            print("Execute primeiro: cd ComfyUI && python main.py")
            return

        print("Conectado ao ComfyUI!")

        # Gerar prompts
        scenes = self.generate_world_cup_prompts()
        print(f"Gerando {len(scenes)} cenas...")

        # Mostrar cenas
        for scene in scenes:
            print(f"  {scene['scene_number']}. {scene['description']}")

        print("\nGerando imagens (verifique o ComfyUI em http://localhost:8188)...\n")

        # Gerar cada cena
        for scene in scenes:
            print(f"Gerando Cena {scene['scene_number']}: {scene['description']}")

            # Workflow simples para gerar imagem
            workflow = {
                "last_node_id": 10,
                "nodes": [
                    {
                        "id": 1,
                        "type": "CheckpointLoaderSimple",
                        "widgets_values": ["v1-5-pruned-emaonly.safetensors"]
                    },
                    {
                        "id": 2,
                        "type": "CLIPTextEncode",
                        "widgets_values": [scene["prompt"]]
                    },
                    {
                        "id": 3,
                        "type": "CLIPTextEncode",
                        "widgets_values": [scene["negative_prompt"]]
                    },
                    {
                        "id": 4,
                        "type": "EmptyLatentImage",
                        "widgets_values": [512, 512, 1]
                    },
                    {
                        "id": 5,
                        "type": "KSampler",
                        "widgets_values": [1020176, "fixed", 20, 7, "euler", "normal", 1]
                    },
                    {
                        "id": 6,
                        "type": "VAEDecode"
                    },
                    {
                        "id": 7,
                        "type": "SaveImage",
                        "widgets_values": [f"worldcup_scene_{scene['scene_number']}", "png"]
                    }
                ],
                "links": [
                    [1, 1, 0, 5, 0, "MODEL"],
                    [2, 2, 0, 5, 1, "CLIP"],
                    [3, 3, 0, 5, 2, "CLIP"],
                    [4, 4, 0, 5, 3, "LATENT"],
                    [5, 5, 0, 6, 0, "LATENT"],
                    [6, 1, 2, 6, 1, "VAE"],
                    [7, 6, 0, 7, 0, "IMAGE"]
                ],
                "version": 0.4
            }

            prompt_id = self.queue_workflow(workflow)
            if prompt_id:
                print(f"  Aguardando geracao...")
                time.sleep(3)
            else:
                print(f"  Falha ao enviar")

        print("\n" + "=" * 60)
        print("GERACAO CONCLUIDA!")
        print("=" * 60)
        print("\nVerifique as imagens em:")
        print("  C:/fralib/ComfyUI/output/")
        print("\nPara montar o video, execute:")
        print("  ffmpeg -framerate 8 -i output/worldcup_scene_%d.png -c:v libx264 video.mp4")

if __name__ == "__main__":
    generator = WorldCupVideoGenerator()
    generator.generate_world_cup_video()