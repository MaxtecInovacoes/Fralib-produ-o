from __future__ import annotations

from datetime import datetime
from typing import Any

import secrets

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_user_by_email(db: Session, email: str):
    return db.execute(
        text(
            "SELECT id, email, password_hash, status, email_confirmado FROM users "
            "WHERE LOWER(email) = LOWER(:email)"
        ),
        {"email": email},
    ).fetchone()


def get_user_by_email_basic(db: Session, email: str):
    return db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).fetchone()


def count_recent_trials_by_ip(db: Session, client_ip: str):
    return db.execute(text("""
        SELECT COUNT(*) FROM users
        WHERE registro_ip = :ip AND criado_em::timestamp > NOW() - INTERVAL '30 days'
    """), {"ip": client_ip}).fetchone()


def create_user_trial(
    db: Session,
    *,
    email: str,
    nome: str,
    password_hash: str,
    now: str,
    trial_expires: str,
    confirm_token: str,
    confirm_expires: str,
    client_ip: str,
    telefone: str,
) -> None:
    sql = """INSERT INTO users (email, nome, name, password_hash, senha_hash, plano, plan, role, status,
              creditos, creditos_max, trial_expires_at, criado_em, email_confirmado, confirm_token, confirm_expires, registro_ip, telefone)
              VALUES (:email, :nome, :nome, :hash, :hash, 'trial', 'free', 'user', 'trial',
              1, 1, :trial_exp, :now, false, :ctoken, :cexp, :ip, :tel)"""
    db.execute(
        text(sql),
        {
            "email": email,
            "nome": nome,
            "hash": password_hash,
            "now": now,
            "trial_exp": trial_expires,
            "ctoken": confirm_token,
            "cexp": confirm_expires,
            "ip": client_ip,
            "tel": telefone,
        },
    )
    db.commit()


def get_user_id_by_email(db: Session, email: str):
    return db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).fetchone()


def get_confirmation_user(db: Session, token: str):
    return db.execute(
        text("SELECT id, confirm_expires FROM users WHERE confirm_token = :token"),
        {"token": token},
    ).fetchone()


def confirm_user_email(db: Session, user_id: int) -> None:
    db.execute(
        text("UPDATE users SET email_confirmado=true, confirm_token=NULL, confirm_expires=NULL WHERE id=:id"),
        {"id": user_id},
    )
    db.commit()


def resend_confirmation_token(db: Session, user_id: int, confirm_token: str, confirm_expires: str) -> None:
    db.execute(
        text("UPDATE users SET confirm_token=:token, confirm_expires=:expires WHERE id=:id"),
        {"token": confirm_token, "expires": confirm_expires, "id": user_id},
    )
    db.commit()


def get_reset_user(db: Session, email: str):
    return db.execute(
        text("SELECT id, nome FROM users WHERE lower(email) = lower(:email) AND status != 'desativado'"),
        {"email": email},
    ).fetchone()


def set_reset_token(db: Session, user_id: int, reset_token: str, reset_expires: str) -> None:
    db.execute(
        text("UPDATE users SET reset_token=:token, reset_expires=:expires WHERE id=:id"),
        {"token": reset_token, "expires": reset_expires, "id": user_id},
    )
    db.commit()


def get_user_reset_by_token(db: Session, token: str):
    return db.execute(
        text("SELECT id, reset_expires FROM users WHERE reset_token = :token"),
        {"token": token},
    ).fetchone()


def set_new_password(db: Session, user_id: int, new_hash: str) -> None:
    db.execute(
        text("UPDATE users SET password_hash=:hash, senha_hash=:hash, reset_token=NULL, reset_expires=NULL WHERE id=:id"),
        {"hash": new_hash, "id": user_id},
    )
    db.commit()


def get_me_user(db: Session, user_id: int):
    return db.execute(
        text("SELECT id, email, status FROM users WHERE id = :id"),
        {"id": user_id},
    ).fetchone()


def get_twofa_enabled(db: Session, user_id: int):
    return db.execute(
        text("SELECT totp_enabled FROM users WHERE id=:id"),
        {"id": user_id},
    ).fetchone()


def disable_twofa(db: Session, user_id: int) -> None:
    db.execute(
        text("UPDATE users SET totp_enabled=false, totp_secret=NULL WHERE id=:id"),
        {"id": user_id},
    )
    db.commit()


def get_license_by_email(db: Session, email: str):
    return db.execute(text("SELECT id FROM licencas WHERE email = :email"), {"email": email}).fetchone()


def insert_license_trial(db: Session, *, lic_id: str, cliente: str, email: str, now: str, trial_expires: str) -> None:
    lic_chave = secrets.token_urlsafe(16)
    db.execute(text("""
        INSERT INTO licencas (id, cliente, email, plano, valor, chave, status, data, expira)
        VALUES (:id, :cliente, :email, :plano, :valor, :chave, :status, :data, :expira)
    """), {
        "id": lic_id,
        "cliente": cliente,
        "email": email,
        "plano": "trial",
        "valor": 0,
        "chave": lic_chave,
        "status": "ativa",
        "data": now,
        "expira": trial_expires,
    })
    db.commit()


def get_config_pipeline_by_user(db: Session, user_id: int):
    return db.execute(
        text("SELECT id FROM config_pipeline WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()


def insert_config_pipeline(db: Session, user_id: int) -> None:
    db.execute(text("""
        INSERT INTO config_pipeline (user_id, nicho, cidade, pipeline_status, volume_leads_target)
        VALUES (:uid, '', '', 'parado', 10)
    """), {"uid": user_id})
    db.commit()

