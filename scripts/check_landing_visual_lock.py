"""Fail if the locked landing visual layer changes.

Copy and SEO metadata may change, but the base visual CSS inside
frontend/partials/landing/_head.html is frozen by product decision.
"""

from hashlib import sha256
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LOCKED_FILES = {
    "frontend/partials/landing/_head.html": (
        "e619f96ef231dea8511894c4ddbe894f3b99295a03b767a7b42878d2b6b5e8f6"
    ),
}


def main() -> None:
    changed = []
    for rel, expected in LOCKED_FILES.items():
        path = ROOT / rel
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        style_match = re.search(r"<style>(.*?)</style>", normalized, re.S)
        if not style_match:
            changed.append(f"{rel}: style block not found")
            continue
        actual = sha256(style_match.group(1).encode("utf-8")).hexdigest()
        if actual != expected:
            changed.append(f"{rel}: {actual} != {expected}")

    if changed:
        raise SystemExit(
            "Landing visual lock failed. Do not change the landing visual/CSS "
            "without an explicit product approval.\n" + "\n".join(changed)
        )

    print("landing visual lock ok")


if __name__ == "__main__":
    main()
