"""Tests para env-from-dotenv.py."""
import sys
import os
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HELPER = PROJECT_ROOT / "infra" / "systemd" / "env-from-dotenv.py"


class TestHelperExists:
    def test_helper_exists(self):
        assert HELPER.exists(), f"Helper nao encontrado: {HELPER}"

    def test_helper_is_python(self):
        content = HELPER.read_text(encoding="utf-8")
        assert "def parse_dotenv" in content
        assert "def write_systemd_env" in content


class TestHelperParse:
    """Testa parser de .env."""

    def test_simple_key_value(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("FOO=bar\n")
        result = subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(tmp_path / "out.env")],
            capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        out = (tmp_path / "out.env").read_text(encoding="utf-8")
        assert 'FOO="bar"' in out

    def test_with_quotes(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text('KEY="value with spaces"\n')
        subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(tmp_path / "out.env")],
            capture_output=True, text=True
        )
        out = (tmp_path / "out.env").read_text(encoding="utf-8")
        assert 'KEY="value with spaces"' in out

    def test_ignores_comments(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("# comment\nFOO=bar\n# another\nBAZ=qux\n")
        subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(tmp_path / "out.env")],
            capture_output=True, text=True
        )
        out = (tmp_path / "out.env").read_text(encoding="utf-8")
        assert 'FOO="bar"' in out
        assert 'BAZ="qux"' in out
        assert "# comment" not in out

    def test_ignores_blank_lines(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text("\n\nFOO=bar\n\n\n")
        subprocess.run(
            [sys.executable, str(HELPER), str(env_file), str(tmp_path / "out.env")],
            capture_output=True, text=True
        )
        out = (tmp_path / "out.env").read_text(encoding="utf-8")
        assert 'FOO="bar"' in out

    def test_real_fralib_env(self, tmp_path):
        """Testa com o .env real do projeto (se existir)."""
        real_env = Path("/root/fralib/.env")
        if not real_env.exists():
            pytest.skip("Skipping real env test (path not Windows-friendly)")
        out_file = tmp_path / "fralib.env"
        result = subprocess.run(
            [sys.executable, str(HELPER), str(real_env), str(out_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert out_file.exists()


class TestHelperError:
    def test_nonexistent_input(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(HELPER), "/tmp/does_not_exist_xyz.env", str(tmp_path / "out.env")],
            capture_output=True, text=True
        )
        assert result.returncode != 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))