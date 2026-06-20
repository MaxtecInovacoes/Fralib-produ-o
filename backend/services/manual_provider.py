"""Lead Provider: Manual (CSV upload and direct entry)."""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ManualProvider:
    """Lead provider for manual lead entry and CSV uploads.

    Strategy: "manual" — Accepts leads provided directly by the user
    (via API payload or CSV file upload) and inserts them into lead_inventory
    without performing any external search.
    """

    name = "manual"

    # Column name aliases accepted from CSV / payload
    COLUMN_ALIASES: dict[str, str] = {
        "nome": "nome",
        "name": "nome",
        "razao_social": "nome",
        "razaosocial": "nome",
        "cidade": "cidade",
        "city": "cidade",
        "local": "cidade",
        "segmento": "segmento",
        "nicho": "segmento",
        "niche": "segmento",
        "categoria": "segmento",
        "telefone": "telefone",
        "phone": "telefone",
        "fone": "telefone",
        "whatsapp": "whatsapp",
        "wa": "whatsapp",
        "tel": "telefone",
        "telefone1": "telefone",
        "endereco": "endereco",
        "endereço": "endereco",
        "address": "endereco",
        "rua": "endereco",
        "website": "website",
        "site": "website",
        "url": "website",
        "rating": "rating",
        "avaliacao": "rating",
        "estrelas": "rating",
        "total_avaliacoes": "total_avaliacoes",
        "reviews_count": "total_avaliacoes",
        "avaliacoes": "total_avaliacoes",
        "maps_url": "maps_url",
        "place_id": "place_id",
        "placeid": "place_id",
    }

    def __init__(self, db: Session, tenant_id: int, config: dict[str, Any]):
        self.db = db
        self.tenant_id = tenant_id
        self.config = config

    # ---- public API ----

    def store_candidates(
        self,
        candidates: list[dict[str, Any]],
        segmento: str | None = None,
        cidade: str | None = None,
    ) -> list[tuple[str, bool]]:
        """Store each candidate dict into lead_inventory.

        Args:
            candidates: List of lead dicts with optional fields.
            segmento: Fallback segmento if not present in each candidate.
            cidade: Fallback cidade if not present in each candidate.

        Returns list of (inventory_id, was_inserted) tuples.
        """
        stored: list[tuple[str, bool]] = []
        for raw in candidates:
            inv_id, inserted = self._store_candidate(raw, segmento, cidade)
            stored.append((inv_id, inserted))
        return stored

    def parse_csv(
        self,
        csv_content: str | bytes,
        delimiter: str = ";",
        encoding: str = "utf-8",
    ) -> list[dict[str, Any]]:
        """Parse CSV content into a list of lead dicts.

        Handles BOM, mixed delimiters, and flexible column names.
        """
        if isinstance(csv_content, bytes):
            csv_content = csv_content.decode(encoding, errors="replace").lstrip(
                "﻿"
            )

        # Normalize line endings
        csv_content = csv_content.replace("\r\n", "\n").replace("\r", "\n")

        # Detect delimiter if it looks wrong
        sample = csv_content[:500]
        if "\t" in sample and delimiter == ";":
            delimiter = "\t"

        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
        leads: list[dict[str, Any]] = []

        for row in reader:
            if not row:
                continue
            # Map aliases to canonical names
            mapped: dict[str, str] = {}
            for raw_key, raw_value in row.items():
                if raw_key is None:
                    continue
                key = str(raw_key).strip().lower()
                canonical = self.COLUMN_ALIASES.get(key, key)
                value = str(raw_value or "").strip()
                if value:
                    mapped[canonical] = value

            if not mapped.get("nome"):
                continue

            # Normalize phone digits
            for phone_field in ("telefone", "whatsapp"):
                if phone_field in mapped:
                    digits = re.sub(r"\D+", "", mapped[phone_field])
                    if digits.startswith("55") and len(digits) > 11:
                        digits = digits[2:]
                    mapped[phone_field] = digits

            # Normalize rating
            if "rating" in mapped:
                try:
                    mapped["rating"] = str(
                        max(0.0, min(5.0, float(mapped["rating"].replace(",", "."))))
                    )
                except (ValueError, AttributeError):
                    mapped.pop("rating", None)

            leads.append(mapped)

        return leads

    def validate_candidate(self, candidate: dict[str, Any]) -> tuple[bool, str]:
        """Validate a single candidate lead.

        Returns (is_valid, error_message).
        """
        if not candidate.get("nome"):
            return False, "nome obrigatorio"
        nome = str(candidate.get("nome") or "").strip()
        if len(nome) < 2:
            return False, "nome muito curto"
        if len(nome) > 255:
            return False, "nome muito longo"

        cidade = str(candidate.get("cidade") or "").strip()
        if not cidade:
            return False, "cidade obrigatoria"
        if len(cidade) > 120:
            return False, "cidade muito longa"

        telefone = str(candidate.get("telefone") or "").strip()
        whatsapp = str(candidate.get("whatsapp") or "").strip()
        website = str(candidate.get("website") or "").strip()

        if not telefone and not whatsapp and not website and not cidade:
            return False, "sem identificador unico (telefone, whatsapp ou website)"

        return True, ""

    # ---- internal helpers ----

    def _store_candidate(
        self,
        candidate: dict[str, Any],
        segmento: str | None = None,
        cidade: str | None = None,
    ) -> tuple[str, bool]:
        """Insert a single candidate into lead_inventory (deduplication-aware)."""
        raw = self._normalize(candidate)
        raw["segmento"] = raw.get("segmento") or segmento or ""
        raw["cidade"] = raw.get("cidade") or cidade or ""

        if not raw.get("nome"):
            return "", False

        key = self._dedupe_key(raw)
        inv_id = uuid.uuid4().hex

        row = self.db.execute(
            text(
                """
                INSERT INTO lead_inventory (
                    id, tenant_id, origem, segmento, cidade, nome, telefone, whatsapp,
                    rating, reviews_count, website, endereco, maps_url, place_id,
                    dedupe_key, status, score_caio, tier, dados, atualizado_em
                )
                VALUES (
                    :id, :uid, 'manual', :segmento, :cidade, :nome, :telefone, :whatsapp,
                    :rating, :reviews_count, :website, :endereco, :maps_url, :place_id,
                    :dedupe, 'raw', :score, :tier, CAST(:dados AS jsonb), NOW()
                )
                ON CONFLICT (tenant_id, dedupe_key) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": inv_id,
                "uid": self.tenant_id,
                "segmento": raw.get("segmento") or "",
                "cidade": raw.get("cidade") or "",
                "nome": raw.get("nome", "")[:255],
                "telefone": raw.get("telefone") or "",
                "whatsapp": raw.get("whatsapp") or "",
                "rating": float(raw.get("rating") or 0.0),
                "reviews_count": int(raw.get("total_avaliacoes") or 0),
                "website": raw.get("website") or "",
                "endereco": raw.get("endereco") or "",
                "maps_url": raw.get("maps_url") or "",
                "place_id": raw.get("place_id") or "",
                "dedupe": key,
                "score": 0,
                "tier": "",
                "dados": json.dumps(raw, ensure_ascii=False, default=str),
            },
        ).fetchone()
        self.db.commit()

        if row:
            self._log("success", f"Lead manual inserido: {raw.get('nome')}")
            return str(row[0]), True

        existing = self.db.execute(
            text(
                "SELECT id FROM lead_inventory WHERE tenant_id=:uid AND dedupe_key=:dedupe"
            ),
            {"uid": self.tenant_id, "dedupe": key},
        ).fetchone()
        return str(existing[0]) if existing else inv_id, False

    def _normalize(self, lead: Any) -> dict[str, Any]:
        """Convert any lead representation into a plain dict."""
        if isinstance(lead, dict):
            return {k: v for k, v in lead.items() if k is not None}
        if hasattr(lead, "model_dump"):
            return lead.model_dump()
        if hasattr(lead, "dict"):
            return lead.dict()
        return dict(getattr(lead, "__dict__", {}) or {})

    def _dedupe_key(self, lead: dict[str, Any]) -> str:
        import hashlib
        import re

        place = str(lead.get("place_id") or "").strip().lower()
        if place:
            marker = f"place:{place}"
        else:
            digits = re.sub(
                r"\D+", "",
                str(lead.get("whatsapp") or lead.get("telefone") or ""),
            )
            if digits.startswith("55") and len(digits) > 11:
                digits = digits[2:]
            website = re.sub(
                r"^https?://(www\.)?",
                "",
                str(lead.get("website") or "").strip().lower(),
            ).split("/")[0]
            nome = self._slug(str(lead.get("nome") or ""))
            cidade = self._slug(str(lead.get("cidade") or ""))
            endereco = self._slug(str(lead.get("endereco") or ""))[:48]
            if digits:
                marker = f"phone:{digits}"
            elif website:
                marker = f"web:{website}"
            else:
                marker = f"name:{nome}:{cidade}:{endereco}"
        return hashlib.sha1(f"{self.tenant_id}:{marker}".encode("utf-8")).hexdigest()

    @staticmethod
    def _slug(value: str) -> str:
        import re
        import unicodedata

        norm = (
            unicodedata.normalize("NFKD", value or "")
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")

    def _log(self, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        from lead_supply_engine import _event

        _event(self.db, self.tenant_id, "manual", level, message, payload)
