"""Lead Provider: Google Maps (place-based search via GoSom / Playwright)."""


import json
import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    pass


class MapsProvider:
    """Lead provider that uses GoSom / Playwright Google Maps scraping directly.

    Strategy: "maps" — Performs direct place extraction using the same
    `buscar_leads_google_maps` entry point but exposes a provider-specific
    interface focused on place_id extraction and structured place data.
    """

    name = "maps"

    def __init__(self, db: Session, tenant_id: int, config: dict[str, Any]):
        self.db = db
        self.tenant_id = tenant_id
        self.config = config

    # ---- public API ----

    async def search(
        self,
        segmentos: list[str],
        cidades: list[str],
        *,
        force: bool = False,
        force_fresh: bool = False,
        batch_limit: int = 8,
        score_minimo: int = 45,
        existing_names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search places on Google Maps for the given segmento/cidade pairs.

        Uses `buscar_leads_google_maps` from agente1_hunter_v2, which
        internally falls back from cache → GoSom → Playwright.
        """
        from utils.agente1_hunter_v2 import buscar_leads_google_maps

        results: list[dict[str, Any]] = []
        pairs = [(seg, cid) for seg in segmentos for cid in cidades]

        for segmento, cidade in pairs:
            if len(results) >= batch_limit:
                break
            try:
                leads = await buscar_leads_google_maps(
                    cidade=cidade,
                    segmento=segmento,
                    limite=max(1, batch_limit - len(results)),
                    leads_existentes=existing_names or set(),
                    force_fresh=bool(force_fresh),
                    user_id=self.tenant_id,
                    score_minimo=score_minimo,
                    aprovados_necessarios=max(1, batch_limit - len(results)),
                )
            except Exception as exc:
                self._log(
                    "error",
                    f"Maps falhou em {segmento}/{cidade}: {str(exc)[:180]}",
                )
                continue
            for candidate in leads or []:
                results.append(self._normalize_candidate(candidate, segmento, cidade))
                if len(results) >= batch_limit:
                    break
        return results

    def store_candidates(
        self,
        candidates: list[dict[str, Any]],
        segmento: str,
        cidade: str,
    ) -> list[tuple[str, bool]]:
        """Store each candidate into lead_inventory with maps origin."""
        stored: list[tuple[str, bool]] = []
        for candidate in candidates:
            inv_id, inserted = self._store_candidate(candidate, segmento, cidade)
            stored.append((inv_id, inserted))
        return stored

    # ---- internal helpers ----

    def _normalize_candidate(self, candidate: Any, segmento: str, cidade: str) -> dict[str, Any]:
        if hasattr(candidate, "model_dump"):
            raw = candidate.model_dump()
        elif hasattr(candidate, "dict"):
            raw = candidate.dict()
        elif isinstance(candidate, dict):
            raw = dict(candidate)
        else:
            raw = dict(getattr(candidate, "__dict__", {}) or {})

        lead = raw.get("lead", raw)
        lead["segmento"] = lead.get("segmento") or segmento
        lead["cidade"] = lead.get("cidade") or cidade
        return lead

    def _store_candidate(
        self,
        candidate: dict[str, Any],
        segmento: str,
        cidade: str,
    ) -> tuple[str, bool]:
        """Insert a single candidate into lead_inventory (deduplication-aware)."""
        lead = candidate.get("lead", candidate)
        raw = self._lead_to_dict(lead)
        raw["segmento"] = raw.get("segmento") or segmento
        raw["cidade"] = raw.get("cidade") or cidade

        key = self._dedupe_key(raw)
        inv_id = uuid.uuid4().hex

        score = int(
            float(
                getattr(candidate, "score", 0)
                or candidate.get("score", 0)
                or 0
            )
        )
        tier = str(
            getattr(candidate, "tier", "")
            or candidate.get("tier", "")
            or ""
        )
        raw["origem"] = "maps"

        row = self.db.execute(
            text(
                """
                INSERT INTO lead_inventory (
                    id, tenant_id, origem, segmento, cidade, nome, telefone, whatsapp,
                    rating, reviews_count, website, endereco, maps_url, place_id,
                    dedupe_key, status, score_caio, tier, dados, atualizado_em
                )
                VALUES (
                    :id, :uid, 'maps', :segmento, :cidade, :nome, :telefone, :whatsapp,
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
                "segmento": raw.get("segmento") or segmento,
                "cidade": raw.get("cidade") or cidade,
                "nome": raw.get("nome") or "Lead sem nome",
                "telefone": raw.get("telefone") or "",
                "whatsapp": raw.get("whatsapp") or "",
                "rating": raw.get("rating") or 0.0,
                "reviews_count": raw.get("total_avaliacoes")
                or len(raw.get("reviews") or []),
                "website": raw.get("website") or "",
                "endereco": raw.get("endereco") or "",
                "maps_url": raw.get("maps_url") or "",
                "place_id": raw.get("place_id") or "",
                "dedupe": key,
                "score": score,
                "tier": tier,
                "dados": json.dumps(raw, ensure_ascii=False, default=str),
            },
        ).fetchone()
        self.db.commit()

        if row:
            return str(row[0]), True

        existing = self.db.execute(
            text(
                "SELECT id FROM lead_inventory WHERE tenant_id=:uid AND dedupe_key=:dedupe"
            ),
            {"uid": self.tenant_id, "dedupe": key},
        ).fetchone()
        return str(existing[0]) if existing else inv_id, False

    def _lead_to_dict(self, lead: Any) -> dict[str, Any]:
        if isinstance(lead, dict):
            return dict(lead)
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
        import unicodedata

        norm = (
            unicodedata.normalize("NFKD", value or "")
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")

    def _log(self, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        from lead_supply_engine import _event

        _event(self.db, self.tenant_id, "maps", level, message, payload)
