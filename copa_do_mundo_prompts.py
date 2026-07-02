"""Script para gerar prompts para video da Copa do Mundo.

Usa a API KPLabs para criar prompts detalhados.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# SEGURANÇA (Sprint 12.x): chave NUNCA hardcoded — obrigatória via env var.
KPLABS_API_KEY = os.environ.get("KPLABS_API_KEY")
if not KPLABS_API_KEY:
    raise RuntimeError(
        "KPLABS_API_KEY nao configurada. Defina no .env antes de usar este script."
    )


class CopaDoMundoPromptGenerator:
    def __init__(self) -> None:
        self.kplabs_api: str = "https://api.kpalabz.com"
        self.kplabs_key: str = KPLABS_API_KEY  # carregada de variável de ambiente

    def gerar_prompts_copa_mundo(self):
        """Gerar prompts detalhados para video da Copa do Mundo"""

        prompt = """
        Crie 7 prompts detalhados para um video animado da Copa do Mundo do Brasil.
        Cada prompt deve descrever uma cena diferente.

        CENA 1: Abertura - Mostrar a bandeira do Brasil se movendo com efeito de vento, cores verde e amarelo brilhante

        CENA 2: Lendas do Futebol - Pelé driblando com estilo, mostrando skills lendários

        CENA 3: Neymar - O craque brasileiro fazendo jogadas spectaculares

        CENA 4: Torcida - Torcida brasileira cantando e dançando no estadio

        CENA 5: Gol - Comemoração com confetes verde e amarelo voando

        CENA 6: Taça - A taça da Copa do Mundo brilhando em ouro

        CENA 7: Finale - Texto "BRASIL CAMPEAO" com fogo verde e amarelo

        Para cada cena, retorne:
        1. O prompt em ingles para geracao de imagem
        2. Estilo: anime, cinematografico
        3. Descricao em portugues

        Retorne em formato JSON assim:
        [
            {
                "cena": 1,
                "titulo": "Abertura",
                "prompt_ingles": "descricao em ingles para Stable Diffusion",
                "estilo": "anime cinematografico",
                "descricao": "descricao em portugues"
            }
        ]
        """

        print("=" * 60)
        print("GERADOR DE PROMPTS - COPA DO MUNDO DO BRASIL")
        print("=" * 60)
        print("\nConectando à API KPLabs...")

        try:
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
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("Prompts gerados com sucesso!\n")

                # Extrair JSON
                try:
                    # Tentar encontrar JSON na resposta
                    start = content.find('[')
                    end = content.rfind(']') + 1
                    if start != -1 and end != 0:
                        scenes = json.loads(content[start:end])
                    else:
                        scenes = [{"cena": i+1, "titulo": f"Cena {i+1}", "prompt_ingles": content, "estilo": "anime", "descricao": "Gerado"} for i in range(7)]

                    return scenes

                except json.JSONDecodeError:
                    print("Erro ao processar JSON. Mostrando resposta completa:\n")
                    print(content)
                    return []

            else:
                print(f"Erro na API: {response.status_code}")
                print(response.text)
                return []

        except Exception as e:
            print(f"Erro: {e}")
            return []

    def salvar_prompts(self, scenes, filename="prompts_copa_mundo.txt"):
        """Salvar prompts em arquivo"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("PROMPTS PARA VIDEO DA COPA DO MUNDO DO BRASIL\n")
            f.write("=" * 60 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for scene in scenes:
                f.write(f"CENA {scene['cena']}: {scene.get('titulo', '')}\n")
                f.write(f"  Prompt: {scene.get('prompt_ingles', '')}\n")
                f.write(f"  Estilo: {scene.get('estilo', 'anime')}\n")
                f.write(f"  Descricao: {scene.get('descricao', '')}\n")
                f.write("\n" + "-" * 40 + "\n\n")

        print(f"\nPrompts salvos em: {filename}")
        return filename

    def gerar_script_para_video(self, scenes, filename="script_video.sh"):
        """Gerar script para criar video com FFmpeg"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("#!/bin/bash\n")
            f.write("# Script para gerar video da Copa do Mundo\n\n")
            f.write("# Aps gerar as imagens, use este comando:\n")
            f.write("# ffmpeg -framerate 8 -i cena_%d.png -c:v libx264 -pix_fmt yuv420p video_copa.mp4\n\n")
            f.write("# Ou para melhor qualidade:\n")
            f.write("# ffmpeg -framerate 12 -i cena_%d.png -vf \"scale=1280:720\" -c:v libx264 -crf 18 video_copa.mp4\n\n")

            f.write("\n# Lista de cenas:\n")
            for scene in scenes:
                f.write(f"# Cena {scene['cena']}: {scene.get('titulo', '')}\n")
                f.write(f"# Prompt: {scene.get('prompt_ingles', '')}\n\n")

        print(f"Script salvo em: {filename}")

def main():
    generator = CopaDoMundoPromptGenerator()
    scenes = generator.gerar_prompts_copa_mundo()

    if scenes:
        # Salvar prompts
        generator.salvar_prompts(scenes)

        # Gerar script
        generator.gerar_script_para_video(scenes)

        print("\n" + "=" * 60)
        print("SUGESTO: Use estes prompts em:")
        print("1. DALL-E (OpenAI) para gerar imagens")
        print("2. Midjourney para gerar imagens")
        print("3. Stable Diffusion local")
        print("4. ComfyUI com AnimateDiff")
        print("=" * 60)
    else:
        print("\nNao foi possivel gerar os prompts.")

if __name__ == "__main__":
    main()