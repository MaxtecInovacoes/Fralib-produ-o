"""
LLM Provider - Google Gemini.

Chamadas para API Google Gemini via SDK google-generativeai.
"""

import os
from typing import Optional

# Configurações do ambiente
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_BASE_URL = os.getenv("GOOGLE_BASE_URL")


class GoogleProviderError(Exception):
    """Exceção base para erros do provider Google."""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class GoogleRateLimitError(GoogleProviderError):
    """Exceção para rate limit (429)."""
    def __init__(self, message: str, retry_after: int = 0):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class GoogleProvider:
    """Provider para chamadas Google Gemini."""

    # Mapeamento de modelos
    MODEL_MAP = {
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
        "gemini-ultra": "gemini-1.0-ultra",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GOOGLE_API_KEY
        self._client = None

    def is_available(self) -> bool:
        """Verifica se o provider está configurado."""
        return bool(self.api_key)

    def _get_client(self):
        """Lazy-load do cliente SDK."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise GoogleProviderError(
                    "google-generativeai não instalado. Execute: pip install google-generativeai"
                )
        return self._client

    def _normalize_model(self, model: str) -> str:
        """Normaliza nome do modelo."""
        return self.MODEL_MAP.get(model, model)

    def call(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada LLM via API Gemini.

        Args:
            model: Nome do modelo (gemini-pro, gemini-flash, etc)
            system: Prompt de sistema
            user: Mensagem do usuário
            temperature: Temperatura (0.0 - 1.0)
            max_tokens: Máximo de tokens de saída

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        client = self._get_client()
        model_name = self._normalize_model(model)

        try:
            gen_model = client.GenerativeModel(model_name)

            # Combina system + user em uma única mensagem
            prompt = f"{system}\n\n{user}" if system else user

            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            response = gen_model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            text = response.text or ""

            # Tenta extrair usage (nem sempre disponível na resposta)
            usage = {"input_tokens": 0, "output_tokens": 0}
            if hasattr(response, 'usage_metadata'):
                metadata = response.usage_metadata
                usage = {
                    "input_tokens": getattr(metadata, 'prompt_token_count', 0) or 0,
                    "output_tokens": getattr(metadata, 'candidates_token_count', 0) or 0,
                }

            return text, usage

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                raise GoogleRateLimitError(f"Rate limit: {str(e)[:200]}")
            if "quota" in error_msg:
                raise GoogleRateLimitError(f"Quota exceeded: {str(e)[:200]}")
            raise GoogleProviderError(f"Erro Gemini: {str(e)[:200]}")

    def call_with_retry(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_attempts: int = 3,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada com retry automático.

        Args:
            max_attempts: Número máximo de tentativas

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        import time as _time

        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return self.call(
                    model=model,
                    system=system,
                    user=user,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except GoogleRateLimitError as e:
                last_error = e
                if attempt < max_attempts:
                    wait = min(e.retry_after, 60) if e.retry_after else 15 * attempt
                    print(f"[Google] Rate limit - aguardando {wait}s (tentativa {attempt}/{max_attempts})")
                    _time.sleep(wait)
            except GoogleProviderError as e:
                last_error = e
                if attempt < max_attempts:
                    wait = 5 * attempt
                    print(f"[Google] Erro - aguardando {wait}s (tentativa {attempt}/{max_attempts})")
                    _time.sleep(wait)

        raise last_error or GoogleProviderError(f"Falhou após {max_attempts} tentativas")

    def list_models(self) -> list:
        """Lista modelos disponíveis."""
        client = self._get_client()
        try:
            return [m.name for m in client.list_models()]
        except Exception as e:
            print(f"[Google] Erro ao listar modelos: {e}")
            return []


# Instância singleton
_provider_instance = None

def get_google_provider() -> GoogleProvider:
    """Retorna instância singleton do provider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = GoogleProvider()
    return _provider_instance
