"""
Canva OAuth PKCE Authorization Script
Executa: python canva_oauth_auth.py
"""
import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

# ============================================
# CONFIGURAÇÕES - PREENCHA AQUI
# ============================================
CLIENT_ID = os.getenv("CANVA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CANVA_CLIENT_SECRET", "")
REDIRECT_URI = "http://127.0.0.1:3333/callback"
TOKEN_FILE = "canva_token.json"

# Scopes necessários
SCOPES = [
    "app:read", "app:write",
    "asset:read", "asset:write",
    "design:content:read", "design:content:write",
    "design:meta:read",
    "profile:read"
]

class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        if self.path.startswith("/callback"):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "code" in params:
                OAuthHandler.auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body style='font-family:Arial;text-align:center;padding:50px;background:#1a1a2e;color:white'><h1 style='color:#00d4aa'>Authorized!</h1><p>The code was captured. Closing...</p><script>setTimeout(() => window.close(), 2000)</script></body></html>")
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Erro: codigo nao encontrado</h1></body></html>")

            # Para o servidor
            time.sleep(1)
            self.server.shutdown()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silencia logs

def generate_pkce():
    """Gera code_verifier e code_challenge para PKCE"""
    code_verifier = secrets.token_urlsafe(64)[:128]
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge

def build_auth_url(code_challenge, state):
    """Constrói URL de autorização"""
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"https://www.canva.com/api/oauth/authorize?{urlencode(params)}"

def exchange_code_for_token(code, code_verifier):
    """Troca authorization_code por access_token"""
    import urllib.request
    import urllib.error

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
        "client_id": CLIENT_ID,
    }

    # Basic Auth com client_id:client_secret
    import base64
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    req = urllib.request.Request(
        "https://api.canva.com/rest/v1/oauth/token",
        data=urlencode(data).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise Exception(f"Token exchange failed: {e.code} - {error_body}")

def main():
    global CLIENT_ID, CLIENT_SECRET

    # Verifica credenciais
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ ERRO: Preciso do CANVA_CLIENT_ID e CANVA_CLIENT_SECRET")
        print()
        print("Configure no .env ou exporte as variáveis:")
        print("  Windows: set CANVA_CLIENT_ID=seu_client_id")
        print("           set CANVA_CLIENT_SECRET=seu_client_secret")
        print()
        print("Ou preencha diretamente no script.")
        print()
        print("Criando app Canva:")
        print("1. Vai em https://www.canva.com/developers")
        print("2. Cria uma nova integração")
        print("3. Copia o Client ID e Client Secret")
        return False

    print("=" * 50)
    print("🔐 CANVA OAUTH AUTHORIZATION")
    print("=" * 50)
    print()

    # Gera PKCE
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    # Constrói URL
    auth_url = build_auth_url(code_challenge, state)

    print(f"✅ Client ID: {CLIENT_ID[:10]}...{CLIENT_ID[-4:]}")
    print(f"📍 Redirect URI: {REDIRECT_URI}")
    print()
    print("🌐 Abrindo navegador para autorização...")
    print()

    # Abre navegador
    webbrowser.open(auth_url)

    # Inicia servidor local
    print("⏳ Aguardando autorização...")
    server = HTTPServer(("127.0.0.1", 3333), OAuthHandler)

    # Configura timeout
    server.timeout = 300  # 5 minutos

    while OAuthHandler.auth_code is None:
        server.handle_request()

    code = OAuthHandler.auth_code
    print()
    print("✅ Code capturado!")
    print()
    print("🔄 Trocando code por token...")

    try:
        token_data = exchange_code_for_token(code, code_verifier)

        if "access_token" in token_data:
            # Salva token
            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f, indent=2)

            print()
            print("=" * 50)
            print("🎉 SUCESSO! Token salvo em", TOKEN_FILE)
            print("=" * 50)
            print()
            print(f"Access Token: {token_data.get('access_token', '')[:20]}...")
            print(f"Token Type: {token_data.get('token_type', '')}")
            print(f"Expires In: {token_data.get('expires_in', '')} segundos")
            if "refresh_token" in token_data:
                print(f"Refresh Token: {token_data.get('refresh_token', '')[:20]}...")
            return True
        else:
            print("❌ ERRO: Resposta inválida do token exchange")
            print(json.dumps(token_data, indent=2))
            return False

    except Exception as e:
        print()
        print("❌ ERRO na troca de token:", str(e))
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)