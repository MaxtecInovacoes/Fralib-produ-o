"""Update runtime .env files from stdin JSON without printing secret values."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ENV_PATH = Path("/opt/ai-stack/.env")

ALLOWED_KEYS = {
    "GITHUB_MODELS_API_KEY_1",
    "GITHUB_MODELS_API_KEY_2",
    "GITHUB_MODELS_API_KEY_3",
    "GITHUB_MODELS_API_KEY_4",
    "GEMINI_API_KEY_1",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "GROQ_API_KEY_1",
    "GROQ_API_KEY_2",
    "GROQ_API_KEY_3",
    "GROQ_API_KEY_4",
    "OPENROUTER_API_KEY_1",
    "OPENROUTER_API_KEY_2",
    "OPENROUTER_API_KEY_3",
    "OPENROUTER_API_KEY_4",
    "LITELLM_API_KEY",
    "LITELLM_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "FRALIB_PROXY_LIGHT_MODEL",
    "FRALIB_PROXY_DEFAULT_MODEL",
    "FRALIB_PROXY_BUILDER_MODEL",
}

REMOVABLE_KEYS = ALLOWED_KEYS | {"APIPROMAX_API_KEY", "XAI_API_KEY_1"}


def _parse_env(path: Path) -> tuple[list[str], dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value
    return lines, values


def _render_env(lines: list[str], values: dict[str, str], removed: set[str] | None = None) -> str:
    removed = removed or set()
    seen: set[str] = set()
    rendered: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            rendered.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in removed:
            continue
        if key in values:
            rendered.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            rendered.append(line)
    for key in sorted(values):
        if key not in seen:
            rendered.append(f"{key}={values[key]}")
    return "\n".join(rendered).rstrip() + "\n"


def _load_payload() -> dict[str, str]:
    raw = os.sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"stdin JSON invalido: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("stdin JSON deve ser um objeto {VAR: valor}")
    clean: dict[str, str] = {}
    for key, value in payload.items():
        if key not in ALLOWED_KEYS:
            raise SystemExit(f"variavel nao permitida: {key}")
        text = str(value or "").strip()
        if text:
            clean[key] = text
    if not clean:
        raise SystemExit("nenhuma variavel valida recebida")
    return clean


def main() -> None:
    parser = argparse.ArgumentParser(description="Atualiza secrets do LiteLLM sem ecoar valores")
    parser.add_argument("--path", default=str(DEFAULT_ENV_PATH))
    parser.add_argument("--stdin-json", action="store_true", help="Le atualizacoes de variaveis pelo stdin")
    parser.add_argument("--unset", action="append", default=[], help="Remove variavel permitida do .env")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    payload = _load_payload() if args.stdin_json else {}
    unset_keys = {str(key or "").strip() for key in args.unset if str(key or "").strip()}
    invalid_unset = sorted(unset_keys - REMOVABLE_KEYS)
    if invalid_unset:
        raise SystemExit(f"variavel nao removivel: {', '.join(invalid_unset)}")
    if not payload and not unset_keys:
        raise SystemExit("nenhuma variavel valida recebida")
    lines, current = _parse_env(path)
    current.update(payload)
    for key in unset_keys:
        current.pop(key, None)
    output = _render_env(lines, current, removed=unset_keys)

    keys = ", ".join(sorted(payload))
    removed = ", ".join(sorted(unset_keys))
    if not args.apply:
        print(f"DRY RUN: atualizaria {len(payload)} variavel(is): {keys or '-'}")
        if unset_keys:
            print(f"DRY RUN: removeria {len(unset_keys)} variavel(is): {removed}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, path.with_suffix(path.suffix + f".bak.{stamp}"))
    path.write_text(output, encoding="utf-8")
    path.chmod(0o600)
    print(f"Atualizado {path}: {len(payload)} variavel(is): {keys or '-'}")
    if unset_keys:
        print(f"Removido de {path}: {len(unset_keys)} variavel(is): {removed}")


if __name__ == "__main__":
    main()
