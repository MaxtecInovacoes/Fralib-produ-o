"""Normalizacao e resolucao de identidade de leads vindos do WhatsApp."""

import re
from typing import Callable

from sqlalchemy import create_engine, text


_TENANT_RE = re.compile(r"^fralib_user_(\d+)$")


def normalize_jid_number(jid: str) -> str:
    """Extrai apenas digitos de um JID/telefone do WhatsApp."""
    return re.sub(r"\D", "", str(jid or "").split("@")[0])


def user_id_from_tenant(tenant_id: str) -> int | None:
    """Converte tenant_id fralib_user_{N} para user_id inteiro."""
    if not tenant_id:
        return None
    match = _TENANT_RE.match(str(tenant_id))
    return int(match.group(1)) if match else None


def phone_variants(phone: str) -> list[str]:
    """Gera variantes brasileiras com/sem 55 e com/sem nono digito."""
    telefone = normalize_jid_number(phone)
    if not telefone:
        return []

    tel_com_55 = telefone if telefone.startswith("55") else "55" + telefone
    tel_sem_55 = telefone[2:] if telefone.startswith("55") and len(telefone) > 11 else telefone

    variantes = {tel_com_55, tel_sem_55}
    if len(tel_com_55) == 13 and tel_com_55[4] == "9":
        variantes.add(tel_com_55[:4] + tel_com_55[5:])
    if len(tel_com_55) == 12:
        variantes.add(tel_com_55[:4] + "9" + tel_com_55[4:])

    for variant in list(variantes):
        if variant.startswith("55") and len(variant) > 4:
            variantes.add(variant[2:])

    return sorted(variantes)


def resolve_lid_number(
    lid_number: str,
    whatsmeow_db_url: str = "",
    engine_factory: Callable[[str], object] = create_engine,
) -> str:
    """Resolve um LID para phone number real usando whatsmeow_lid_map."""
    if not whatsmeow_db_url:
        return lid_number

    db_url = whatsmeow_db_url.strip()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        eng = engine_factory(db_url)
        with eng.connect() as conn:
            row = conn.execute(
                text("SELECT pn FROM whatsmeow_lid_map WHERE lid=:lid"),
                {"lid": lid_number},
            ).fetchone()
            if row:
                return row[0]
    except Exception:
        return lid_number

    return lid_number


def find_lead_by_phone_or_jid(phone: str, user_id: int, engine):
    """Busca lead por variantes de telefone ou wpp_jid, sempre restrito ao tenant."""
    variantes = phone_variants(phone)

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, nome, segmento, cidade, sdr_stage, status,
                       COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, '') as tel_raw
                FROM leads
                WHERE user_id = :uid
                  AND regexp_replace(COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, ''), '\\D', '', 'g')
                      = ANY(:variantes)
                LIMIT 1
                """
            ),
            {"variantes": variantes, "uid": user_id},
        ).fetchone()
        if row:
            return row

        return conn.execute(
            text(
                """
                SELECT id, nome, segmento, cidade, sdr_stage, status,
                       COALESCE(NULLIF(telefone_whatsapp,''), NULLIF(whatsapp,''), telefone, '') as tel_raw
                FROM leads
                WHERE user_id = :uid AND wpp_jid = :jid
                LIMIT 1
                """
            ),
            {"jid": phone, "uid": user_id},
        ).fetchone()
