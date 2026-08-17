"""Pipeline identity helpers.

Keeps lead-specific execution IDs and segment inference deterministic so cached
artifacts do not bleed between similar searches in the same city.
"""


import re
import unicodedata


SEGMENT_HINTS_BY_NAME = {
    "crosstraining": "crossfit",
    "cross training": "crossfit",
    "cross-training": "crossfit",
    "crossfit": "crossfit",
    "churrascaria": "churrascaria",
    "steakhouse": "churrascaria",
    "pizzaria": "pizzaria",
    "padaria": "padaria",
    "lanchonete": "lanchonete",
    "barbearia": "barbearia",
    "salao": "salao_beleza",
    "salão": "salao_beleza",
    "pet shop": "pet_shop",
}


def normalize_identity_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def inferir_segmento_por_nome(nome: str, segmento_atual: str = "") -> str:
    normalized_name = normalize_identity_text(nome)
    current = str(segmento_atual or "").strip()
    for hint, segmento in sorted(
        SEGMENT_HINTS_BY_NAME.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if normalize_identity_text(hint) in normalized_name:
            return segmento
    return current
