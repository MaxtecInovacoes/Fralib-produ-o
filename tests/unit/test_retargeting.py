"""Testes do modulo de retargeting."""
import pytest

from backend.services.retargeting import (
    RETARGET_TEMPLATES,
    decide_retarget,
    run_retargeting,
)


class TestDecideRetarget:
    def test_menos_30_dias_nao_retarget(self):
        d = decide_retarget(days_since_last=15, stage="lost")
        assert d.angle == "archive"

    def test_30_dias_check_in(self):
        d = decide_retarget(days_since_last=35, stage="lost")
        assert d.angle == "check_in"
        assert "Oi {nome}" in d.message_template

    def test_60_dias_case_study(self):
        d = decide_retarget(days_since_last=70, stage="opt_out")
        assert d.angle == "case_study"
        assert "triplicou" in d.message_template.lower() or "caso" in d.message_template.lower()

    def test_90_dias_special_offer(self):
        d = decide_retarget(days_since_last=95, stage="lost")
        assert d.angle == "special_offer"

    def test_120_dias_archives(self):
        d = decide_retarget(days_since_last=130, stage="lost")
        assert d.angle == "archive"
        assert d.message_template == ""

    def test_won_before_nunca_retarget(self):
        d = decide_retarget(days_since_last=400, stage="lost", won_before=True)
        assert d.angle == "archive"

    def test_opt_out_com_contagem_nunca_retarget(self):
        d = decide_retarget(days_since_last=60, stage="opt_out", opt_out_count=1)
        assert d.angle == "archive"


class TestTemplates:
    def test_check_in_tem_nome_e_link(self):
        tpl = RETARGET_TEMPLATES["check_in"]
        assert "{nome}" in tpl
        assert "{link_site}" in tpl
        assert "{segmento}" in tpl

    def test_case_study_menciona_resultado(self):
        tpl = RETARGET_TEMPLATES["case_study"]
        assert any(kw in tpl.lower() for kw in ["triplicou", "cresceu", "aumentou", "resultado"])

    def test_special_offer_e_oferta_real(self):
        tpl = RETARGET_TEMPLATES["special_offer"]
        assert any(kw in tpl.lower() for kw in ["oferta", "especial", "condicao"])


class TestRunRetargetingDryRun:
    def test_dry_run_sem_enviar(self):
        from unittest.mock import MagicMock
        engine = MagicMock()
        send_cb = MagicMock()
        # Mock connection
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        engine.connect.return_value.__enter__.return_value = mock_conn

        stats = run_retargeting(engine, apply=False, send_callback=send_cb)
        assert stats["matched"] == 0
        assert stats["sent"] == 0
        send_cb.assert_not_called()
