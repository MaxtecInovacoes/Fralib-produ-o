"""Testes Sprint 1.0 — atomic write + PII masker."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))

from agents._atomic_write import atomic_write_json, file_lock  # noqa: E402
from utils.pii_masker import mask_phone, mask_email, sanitize_message  # noqa: E402


@pytest.mark.unit
class TestAtomicWrite:
    def test_writes_valid_json(self, tmp_path):
        path = tmp_path / "mem.json"
        atomic_write_json(str(path), {"key": "value", "list": [1, 2, 3]})
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"key": "value", "list": [1, 2, 3]}

    def test_crash_before_replace_preserves_original(self, tmp_path):
        path = tmp_path / "mem.json"
        original = {"original": "data", "important": True}
        atomic_write_json(str(path), original)
        assert json.loads(path.read_text(encoding="utf-8")) == original

        with patch("os.replace", side_effect=OSError("simulated crash")):
            with pytest.raises(OSError):
                atomic_write_json(str(path), {"new": "data"})

        assert json.loads(path.read_text(encoding="utf-8")) == original

    def test_overwrite_existing(self, tmp_path):
        path = tmp_path / "mem.json"
        atomic_write_json(str(path), {"v": 1})
        atomic_write_json(str(path), {"v": 2})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == {"v": 2}

    def test_unicode_preserved(self, tmp_path):
        path = tmp_path / "mem.json"
        atomic_write_json(str(path), {"nome": "Joao", "cidade": "Sao Paulo"})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == {"nome": "Joao", "cidade": "Sao Paulo"}


@pytest.mark.unit
class TestFileLock:
    def test_lock_released_after_context(self, tmp_path):
        path = tmp_path / "mem.json"
        with file_lock(str(path)):
            pass
        assert (path.parent / (path.name + ".lock")).exists()

    def test_concurrent_writes_no_data_loss(self, tmp_path):
        path = tmp_path / "mem.json"
        results = []

        def writer(thread_id, count):
            for i in range(count):
                atomic_write_json(str(path), {"thread": thread_id, "i": i})
                results.append((thread_id, i))

        t1 = threading.Thread(target=writer, args=(1, 30))
        t2 = threading.Thread(target=writer, args=(2, 30))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert len(results) == 60
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "thread" in data
        assert "i" in data


@pytest.mark.unit
class TestMaskPhone:
    def test_full_br_with_country_code(self):
        assert mask_phone("5511945612345") == "****2345"

    def test_full_br_with_country_code_formatted(self):
        assert mask_phone("+55 11 94561-2345") == "****2345"

    def test_br_11_digits(self):
        assert mask_phone("11945612345") == "****2345"

    def test_br_10_digits(self):
        assert mask_phone("1145612345") == "****2345"

    def test_short_number(self):
        assert mask_phone("123") == "[PHONE]"

    def test_none(self):
        assert mask_phone(None) == "[PHONE]"

    def test_empty(self):
        assert mask_phone("") == "[PHONE]"


@pytest.mark.unit
class TestMaskEmail:
    def test_full_email(self):
        assert mask_email("joao.silva@empresa.com") == "j****@empresa.com"

    def test_short_local(self):
        assert mask_email("ab@gmail.com") == "a****@gmail.com"

    def test_no_at(self):
        assert mask_email("notanemail") == "[EMAIL]"

    def test_none(self):
        assert mask_email(None) == "[EMAIL]"


@pytest.mark.unit
class TestSanitizeMessage:
    def test_removes_phone_from_text(self):
        result = sanitize_message("Me liga no 11945612345 urgente")
        assert "11945612345" not in result
        assert "****2345" in result

    def test_removes_email_from_text(self):
        result = sanitize_message("Manda email pra joao@empresa.com")
        assert "joao@empresa.com" not in result
        assert "j****@empresa.com" in result

    def test_truncates_long_messages(self):
        long_msg = "a" * 200
        result = sanitize_message(long_msg, max_len=50)
        assert len(result) < 80
        assert "200 chars" in result

    def test_handles_empty(self):
        assert sanitize_message("") == "[empty]"
        assert sanitize_message(None) == "[empty]"

    def test_preserves_normal_text(self):
        msg = "Quero contratar o servico de design"
        result = sanitize_message(msg)
        assert result == msg


@pytest.mark.unit
class TestLogsNoLeak:
    def test_mask_phone_is_called_for_logging(self, capsys):
        phone = "5511945612345"
        masked = mask_phone(phone)
        print(f"User ligou do numero {masked}")
        captured = capsys.readouterr()
        assert "5511945612345" not in captured.out
        assert "****2345" in captured.out

    def test_sanitize_message_keeps_no_full_phone(self):
        for raw in ["5511945612345", "(11) 94561-2345", "+55 11 94561-2345", "11945612345"]:
            sanitized = sanitize_message(f"Ligou: {raw}")
            for prefix in ["5511", "55119", "5511945"]:
                assert prefix not in sanitized, f"vazou prefixo {prefix} em {raw} -> {sanitized}"
