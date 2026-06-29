@echo off
echo ========================================
echo  Iniciando ComfyUI Simples
echo ========================================

echo.
echo 1. Criando versao simplificada do ComfyUI...
mkdir ComfyUI_Simple 2>nul
cd ComfyUI_Simple

echo.
echo 2. Criando arquivos basicos...
echo import torch > main.py
echo import sys > main.py
echo import os > main.py
echo.
echo print("ComfyUI Simples iniciado!") >> main.py
echo print("Acesse: http://localhost:8188") >> main.py
echo.
echo from http.server import HTTPServer, SimpleHTTPRequestHandler >> main.py
echo.
echo class ComfyHandler(SimpleHTTPRequestHandler): >> main.py
echo     def do_GET(self): >> main.py
echo         if self.path == '/': >> main.py
echo             self.send_response(200) >> main.py
echo             self.send_header('Content-type', 'text/html') >> main.py
echo             self.end_headers() >> main.py
echo             self.wfile.write(b'^__^') >> main.py
echo             return >> main.py
echo         else: >> main.py
echo             super().do_GET() >> main.py
echo.
echo if __name__ == "__main__": >> main.py
echo     server = HTTPServer(('localhost', 8188), ComfyHandler) >> main.py
echo     print("Server started on port 8188") >> main.py
echo     server.serve_forever() >> main.py

echo.
echo 3. Criando interface web basica...
mkdir templates 2>nul
echo ^<!DOCTYPE html^> > templates/index.html
echo ^<html^> >> templates/index.html
echo ^<head^> >> templates/index.html
echo     ^<title^>ComfyUI Simples^</title^> >> templates/index.html
echo ^</head^> >> templates/index.html
echo ^<body^> >> templates/index.html
echo     ^<h1^>ComfyUI Simples^</h1^> >> templates/index.html
echo     ^<p^>Para gerar videos, use o script Python^</p^> >> templates/index.html
echo     ^<p^>Ou instale o ComfyUI completo:^</p^> >> templates/index.html
echo     ^<ol^> >> templates/index.html
echo         ^<li^>Baixe um modelo Stable Diffusion^</li^> >> templates/index.html
echo         ^<li^>Coloque em models/checkpoints^</li^> >> templates/index.html
echo         ^<li^>Use o script generate_world_cup_video.py^</li^> >> templates/index.html
echo     ^</ol^> >> templates/index.html
echo ^</body^> >> templates/index.html
echo ^</html^> >> templates/index.html

echo.
echo 4. Iniciando servidor web...
python main.py

echo.
echo ========================================
echo  Servidor iniciado!
echo  Acesse: http://localhost:8188
echo ========================================
pause