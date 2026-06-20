import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from agents.pipeline_checkpoint import gerar_pipeline_id
from agents.pipeline_identity import inferir_segmento_por_nome


@pytest.mark.unit
def test_crosstraining_lead_is_crossfit_not_generic_academia():
    assert inferir_segmento_por_nome("Alfa Crosstraining", "academia") == "crossfit"


@pytest.mark.unit
def test_pipeline_id_is_lead_specific_for_same_search():
    alfa = gerar_pipeline_id(
        2,
        "Alfa Crosstraining",
        "academia",
        "Campina Grande do Sul",
        lead_id="9b6bc76f-155f-4b5f-aed2-c0fb6b01f961",
    )
    aquaflex = gerar_pipeline_id(
        2,
        "Aquaflex Jardim Paulista",
        "natacao",
        "Campina Grande do Sul",
        lead_id="aad9ed26-67ba-413f-a21d-532d00633fb7",
    )

    assert alfa != aquaflex
    assert alfa.startswith("u2-alfa-crosstraining-crossfit-campina-grande-do-sul")
    assert "academia-campina-grande-do-sul" not in alfa
