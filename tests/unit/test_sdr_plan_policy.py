import os
import sys
from datetime import datetime, timedelta


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from services.credits_manager import plano_tem_sdr


def test_trial_active_has_sdr_for_full_experience():
    expires = datetime.utcnow() + timedelta(days=1)

    assert plano_tem_sdr("trial", "trial", expires) is True


def test_trial_expired_blocks_sdr():
    expires = datetime.utcnow() - timedelta(seconds=1)

    assert plano_tem_sdr("trial", "trial", expires) is False


def test_starter_never_has_sdr():
    assert plano_tem_sdr("starter", "ativo", None) is False


def test_paid_sdr_plans_work_unless_blocked():
    assert plano_tem_sdr("pro", "ativo", None) is True
    assert plano_tem_sdr("agency", "ativo", None) is True
    assert plano_tem_sdr("ilimitado", "ativo", None) is True
    assert plano_tem_sdr("pro", "inadimplente", None) is False
