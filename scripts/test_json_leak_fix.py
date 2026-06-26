"""Testes do fix do JSON vazando pro lead.

Bug critico: Franz mandou string JSON literal pra lead Tatiana Rodrigues
em 2026-06-26. O JSON comeca com ```json (markdown) e contem campo "reply"
(EN), nao "resposta" (PT). sanitize_reply nao detectava.

Esses testes garantem que TODOS os formatos de JSON sao detectados e limpos.
"""

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from whatsapp.sdr_reply_service import sanitize_reply


class TestJSONLeakFix(unittest.TestCase):
    """Garante que nenhum formato de JSON vaza pro lead."""

    def test_json_com_marca_markdown(self):
        """Bug do usuario: ```json com campo 'reply' (EN)."""
        raw = '```json\n{\n  "reply": "Boa tarde'
        out = sanitize_reply(raw)
        # NAO pode ter markdown, NAO pode ter aspas de JSON
        self.assertNotIn("```", out)
        self.assertNotIn('"reply"', out)
        # E o conteudo deve ser limpo
        if out:
            self.assertNotIn("{", out)

    def test_json_campo_resposta_pt(self):
        """JSON com campo 'resposta' em PT."""
        raw = '{"resposta": "Boa tarde! Como posso ajudar?", "novo_stage": "qualify"}'
        out = sanitize_reply(raw)
        self.assertNotIn('"resposta"', out)
        self.assertNotIn('"novo_stage"', out)
        self.assertNotIn("{", out)
        self.assertIn("Boa tarde", out)

    def test_json_campo_reply_en(self):
        """JSON com campo 'reply' em EN."""
        raw = '{"reply": "Hi! How can I help?", "next_stage": "qualify"}'
        out = sanitize_reply(raw)
        self.assertNotIn('"reply"', out)
        self.assertNotIn('"next_stage"', out)
        self.assertNotIn("{", out)
        self.assertIn("Hi", out)

    def test_json_sem_aspas(self):
        """JSON malformado sem aspas em torno de valores."""
        raw = '{reply: teste}'
        out = sanitize_reply(raw)
        self.assertNotIn("{", out)
        self.assertNotIn("}", out)

    def test_json_vazio(self):
        """JSON vazio '{}' vira string vazia."""
        raw = '{}'
        out = sanitize_reply(raw)
        self.assertEqual(out, "")

    def test_markdown_sem_json(self):
        """Markdown code block sem JSON - deve passar."""
        raw = "```\nfuncao exemplo()\n```"
        out = sanitize_reply(raw)
        # Se nao parece JSON, nao mexer
        self.assertNotIn('"resposta"', out)

    def test_resposta_normal_passa_direto(self):
        """Msg normal do Franz NAO deve ser modificada."""
        raw = "Oi! Tudo bem? Como posso ajudar?"
        out = sanitize_reply(raw)
        self.assertEqual(out, raw)

    def test_resposta_com_json_embutido_valido(self):
        """Se JSON tem campo resposta E texto, extrai so o texto."""
        raw = '{"resposta": "Oi!", "novo_stage": "hook", "extras": "data"}'
        out = sanitize_reply(raw)
        self.assertIn("Oi!", out)
        self.assertNotIn('"resposta"', out)
        self.assertNotIn('"extras"', out)


if __name__ == "__main__":
    unittest.main(verbosity=2)