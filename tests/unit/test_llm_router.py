import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
backend_dir = ROOT / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ.setdefault("LITELLM_API_KEY", "test-key")
os.environ.setdefault("LITELLM_BASE_URL", "http://127.0.0.1:4000")

from services import llm_router


def test_llm_router_extracts_list_message_content(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "alpha"},
                                {"type": "text", "text": " beta"},
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            }

    monkeypatch.setattr(llm_router.requests, "post", lambda *args, **kwargs: FakeResponse())
    text, usage = llm_router._call_openai("model", "system", "user", 0.2, 100)

    assert text == "alpha beta"
    assert usage == {"input_tokens": 11, "output_tokens": 7}
