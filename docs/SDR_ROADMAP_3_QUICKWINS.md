# Roadmap SDR FraLib — 3 Quick Wins Priorizados

> **Base**: auditoria #41 (7 capacidades SDR vs frameworks), sdr_gateway.py, sdr_langgraph/state.py,
> bryan_knowledge/ (objection_handling.md, segment_insights.json, winning_patterns.md).
>
> **Premissa**: a infraestrutura já existe (LeadMemory, StageEnum, ValidTransitions, RAG, multi-agent
> handoff). Os quick wins adicionam capacidades *pontuais* sem reescrever o grafo.
>
> **Métrica alvo**: aumentar taxa de conversão frio→quente (atual implícita < 5%) em **+3-8 pp** e
> reduzir opt-out por objeção mal-tratada em **−30%**.

---

## Quick Win #1 — Cold Outreach Inteligente Segment-Aware

### Nome
**Hook selector por segmento + horário + rating** (camada de personalização do primeiro envio)

### Esforço
**6 h** (2 h model + 2 h integração no nó `hook` + 1 h config + 1 h testes)

### Arquivos a criar/modificar

| Tipo | Caminho | Mudança |
|---|---|---|
| Criar | `backend/services/sdr_cold_outreach.py` | Novo módulo com `select_hook_variant()` |
| Criar | `backend/services/__init__.py` | Exportar |
| Modificar | `backend/agents/sdr_langgraph/state.py` | Adicionar campo `hook_variant: str` ao `SDRState` |
| Modificar | `backend/agents/sdr_langgraph/nodes/intent_detector.py` (ou nó `hook`) | Chamar seletor antes do LLM |
| Modificar | `backend/agents/bryan_knowledge/segment_insights.json` | Adicionar campo `hook_variants` por segmento |

### Código Python de exemplo (esquelético)

```python
"""Cold outreach inteligente: escolhe hook baseado em segmento + horário + rating."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json

HookVariant = Literal["data", "case", "presente", "dor", "concorrente"]


@dataclass(frozen=True)
class LeadSignals:
    segmento: str
    rating: float
    cidade: str
    hora_local: int  # 0-23


@dataclass(frozen=True)
class HookDecision:
    variant: HookVariant
    template_key: str
    ab_test_bucket: str  # "A" | "B" | "C" | "D"
    reason: str


def _load_insights(path: str = "backend/agents/bryan_knowledge/segment_insights.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_hook_variant(signals: LeadSignals, lead_id: str) -> HookDecision:
    """Seleciona variante de hook personalizada para cold outreach."""
    insights = _load_insights()
    seg = (signals.segmento or "").lower()
    seg_data = insights.get(seg, {})
    best_time = seg_data.get("best_time", "")  # ex: "9h-11h"

    # Bucket A/B determinístico por lead_id
    bucket = "ABCD"[hash(lead_id) % 4]

    # Rating baixo + concorrente conhecido → hook de dor
    if signals.rating < 3.5 and seg_data.get("pain_triggers"):
        return HookDecision("dor", f"{seg}.dor.rating_baixo", bucket, "rating baixo + pain trigger")

    # Dentro do best_time → hook case (social proof)
    if _is_in_window(signals.hora_local, best_time):
        return HookDecision("case", f"{seg}.case.horario_nobre", bucket, "horário nobre")

    # Fora do best_time → hook presente (curto, objetivo)
    return HookDecision("presente", f"{seg}.presente.default", bucket, "default")


def _is_in_window(hora: int, window: str) -> bool:
    """Parseia '9h-11h' e checa se hora está dentro."""
    if not window:
        return False
    try:
        start, end = window.replace("h", "").split("-")
        return int(start) <= hora <= int(end)
    except (ValueError, AttributeError):
        return False
```

### Ganho esperado
- **+2-4 pp taxa de resposta no hook** (personalização > template único)
- **−20% opt-out no primeiro envio** (hook relevante > pitch genérico)
- **Habilita A/B testing** via bucket determinístico (Quick Win #26 já em backlog)

### Teste sugerido

```python
# tests/test_sdr_cold_outreach.py
import pytest
from backend.services.sdr_cold_outreach import select_hook_variant, LeadSignals


@pytest.mark.unit
def test_rating_baixo_ativa_hook_dor():
    signals = LeadSignals(segmento="academia", rating=3.0, cidade="SP", hora_local=10)
    decision = select_hook_variant(signals, lead_id="abc123")
    assert decision.variant == "dor"
    assert "rating_baixo" in decision.template_key


@pytest.mark.unit
def test_horario_nobre_ativa_hook_case():
    signals = LeadSignals(segmento="restaurante", rating=4.5, cidade="RJ", hora_local=15)
    decision = select_hook_variant(signals, lead_id="xyz789")
    assert decision.variant == "case"
    assert decision.ab_test_bucket in "ABCD"


@pytest.mark.unit
def test_bucket_deterministico():
    """Mesmo lead_id → mesmo bucket em chamadas repetidas."""
    s = LeadSignals("comercio", 4.0, "MG", 9)
    d1 = select_hook_variant(s, "lead_42")
    d2 = select_hook_variant(s, "lead_42")
    assert d1.ab_test_bucket == d2.ab_test_bucket
```

---

## Quick Win #2 — Objection Handling Classifier + Resposta Emparelhada

### Nome
**Detector de objeção + roteamento para `winning_patterns.md`**

### Esforço
**8 h** (3 h classifier + 3 h integração no grafo + 1 h knowledge base + 1 h testes)

### Arquivos a criar/modificar

| Tipo | Caminho | Mudança |
|---|---|---|
| Criar | `backend/services/sdr_objection_classifier.py` | Classificador regex + LLM fallback |
| Modificar | `backend/agents/bryan_knowledge/objection_handling.md` | Adicionar YAML frontmatter parseável |
| Modificar | `backend/agents/sdr_langgraph/state.py` | Adicionar `detected_objection: str`, `objection_response: str` |
| Modificar | `backend/agents/sdr_langgraph/nodes/` (criar `objection_router.py`) | Nó que decide: scripted vs LLM |
| Modificar | `backend/services/sdr_gateway.py` | Permitir `direction="objection_response"` no guard |

### Código Python de exemplo (esquelético)

```python
"""Classificador de objeções + roteamento para resposta emparelhada."""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ObjectionType(str, Enum):
    NAO_INTERESSADO = "nao_interessado"
    JA_TENHO_SITE = "ja_tenho_site"
    QUANTO_CUSTA = "quanto_custa"
    SEM_DINHEIRO = "sem_dinheiro"
    MAIS_INFO = "mais_info"
    QUEM_E_VOCE = "quem_e_voce"
    OCUPADO = "ocupado"
    VOU_PENSAR = "vou_pensar"
    OUTRO = "outro"


@dataclass(frozen=True)
class ObjectionPattern:
    objection: ObjectionType
    keywords: tuple[str, ...]
    response_template: str
    max_followup_attempts: int  # quantas vezes responder antes de marcar lost
    next_stage_if_handled: str  # stage após resposta


# Knowledge base (espelha objection_handling.md)
OBJECTION_PATTERNS: tuple[ObjectionPattern, ...] = (
    ObjectionPattern(
        ObjectionType.NAO_INTERESSADO,
        ("nao tenho interesse", "nao quero", "para de mandar", "chato"),
        "Tranquilo! O site fica disponível se mudar de ideia. Boa sorte 👊",
        max_followup_attempts=0,  # respeitar 1x conforme regra
        next_stage_if_handled="opt_out",
    ),
    ObjectionPattern(
        ObjectionType.QUANTO_CUSTA,
        ("quanto custa", "quanto é", "qual o preço", "qual o valor"),
        "Depende do que você precisa. Me conta mais sobre o negócio primeiro?",
        max_followup_attempts=2,
        next_stage_if_handled="pain",
    ),
    ObjectionPattern(
        ObjectionType.VOU_PENSAR,
        ("vou pensar", "depois a gente vê", "qualquer coisa te chamo"),
        "Beleza! Fico por aqui. Followup em 48h com algo de valor.",
        max_followup_attempts=2,
        next_stage_if_handled="scheduled",
    ),
)


class ObjectionClassifier(Protocol):
    def classify(self, message: str) -> ObjectionType: ...


class RegexObjectionClassifier:
    """Classificador determinístico — fallback LLM se nenhum match."""

    def classify(self, message: str) -> ObjectionType:
        normalized = message.lower().strip()
        for pattern in OBJECTION_PATTERNS:
            if any(kw in normalized for kw in pattern.keywords):
                return pattern.objection
        return ObjectionType.OUTRO


def get_objection_response(message: str, classifier: ObjectionClassifier) -> tuple[ObjectionType, str, str]:
    """Retorna (objection, response_template, next_stage). None se OUTRO."""
    objection = classifier.classify(message)
    if objection == ObjectionType.OUTRO:
        return objection, "", "qualify"
    pattern = next(p for p in OBJECTION_PATTERNS if p.objection == objection)
    return objection, pattern.response_template, pattern.next_stage_if_handled
```

### Ganho esperado
- **−30% opt-out por objeção "não tenho interesse"** mal-tratada (resposta respeitosa imediata)
- **+5 pp qualificação em objeções "vou pensar"** (followup agendado em vez de lead abandonado)
- **Qualidade**: respostas determinísticas para objeções críticas (compliance + tom consistente)

### Teste sugerido

```python
# tests/test_sdr_objection_classifier.py
import pytest
from backend.services.sdr_objection_classifier import (
    RegexObjectionClassifier, get_objection_response, ObjectionType,
)


@pytest.mark.unit
@pytest.mark.parametrize("msg,expected", [
    ("Para de mandar msg, chato", ObjectionType.NAO_INTERESSADO),
    ("Quanto custa o site?", ObjectionType.QUANTO_CUSTA),
    ("Vou pensar e qualquer coisa te chamo", ObjectionType.VOU_PENSAR),
    ("Quem é você?", ObjectionType.QUEM_E_VOCE),
])
def test_classifica_objeções_comuns(msg, expected):
    c = RegexObjectionClassifier()
    assert c.classify(msg) == expected


@pytest.mark.unit
def test_nao_interessado_retorna_opt_out():
    _, response, next_stage = get_objection_response(
        "Não tenho interesse", RegexObjectionClassifier()
    )
    assert "Boa sorte" in response
    assert next_stage == "opt_out"


@pytest.mark.unit
def test_outro_nao_quebra():
    """Mensagem ambígua → OUTRO + stage neutro."""
    objection, response, next_stage = get_objection_response(
        "ok pode ser", RegexObjectionClassifier()
    )
    assert objection == ObjectionType.OUTRO
    assert response == ""
    assert next_stage == "qualify"
```

---

## Quick Win #3 — Follow-up Adaptativo com Retargeting por Silêncio

### Nome
**Follow-up scheduler inteligente** (cadência 24h/72h + skip se lead engajou)

### Esforço
**5 h** (2 h scheduler + 2 h endpoint cron + 1 h testes)

### Arquivos a criar/modificar

| Tipo | Caminho | Mudança |
|---|---|---|
| Criar | `backend/services/sdr_followup_scheduler.py` | Lógica de decisão de follow-up |
| Criar | `backend/endpoints/followup_endpoints.py` | Endpoint POST `/api/sdr/followup/run` |
| Modificar | `backend/agents/sdr_langgraph/state.py` | Adicionar `followup_due_at: str`, `last_engagement_at: str` |
| Modificar | `backend/services/sdr_gateway.py` | Aceitar cadência em `FOLLOWUP_STAGES` |
| Modificar | `backend/endpoints/cron_endpoints.py` | Wire do cron diário |

### Código Python de exemplo (esquelético)

```python
"""Decide se lead deve receber follow-up, e qual cadência."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from sqlalchemy import text

FollowupCadence = Literal["skip", "24h", "72h", "final_7d", "archive"]


@dataclass(frozen=True)
class FollowupDecision:
    cadence: FollowupCadence
    reason: str
    message_template: str
    next_run_at: datetime | None


def _has_recent_engagement(db, lead_id: str, hours: int = 24) -> bool:
    """Lead engajou (mensagem inbound) nas últimas N horas?"""
    row = db.execute(
        text("""
            SELECT 1 FROM interacoes
            WHERE lead_id = :lid
              AND direcao = 'entrada'
              AND criado_em > NOW() - (:h || ' hours')::interval
            LIMIT 1
        """),
        {"lid": lead_id, "h": str(hours)},
    ).fetchone()
    return bool(row)


def decide_followup(
    db,
    lead_id: str,
    *,
    stage: str,
    followup_count: int,
    last_outbound_at: datetime | None,
    rejection_count: int,
    segment: str,
) -> FollowupDecision:
    """Retorna decisão de follow-up baseada em sinais do lead."""

    # Regra 0: opt-out / 2 rejeições → archive
    if rejection_count >= 2:
        return FollowupDecision("archive", "limite de rejeições", "", None)

    # Regra 1: lead engajou nas últimas 24h → skip (humano assume)
    if _has_recent_engagement(db, lead_id, hours=24):
        return FollowupDecision("skip", "lead engajou recentemente", "", None)

    # Regra 2: cadence progressiva
    if followup_count == 0 and last_outbound_at:
        next_run = last_outbound_at + timedelta(hours=24)
        return FollowupDecision(
            "24h", "primeiro follow-up", "f1_light_checkin", next_run
        )

    if followup_count == 1:
        next_run = last_outbound_at + timedelta(hours=72) if last_outbound_at else None
        return FollowupDecision(
            "72h", "segundo follow-up", "f2_value_add", next_run
        )

    if followup_count == 2:
        next_run = last_outbound_at + timedelta(days=7) if last_outbound_at else None
        return FollowupDecision(
            "final_7d", "última tentativa", "f3_breakup_email", next_run
        )

    return FollowupDecision("archive", "exauriu cadência", "", None)


def run_pending_followups(db, *, apply: bool = False) -> dict[str, int]:
    """Job diário: processa leads com followup_due_at <= NOW()."""
    rows = db.execute(text("""
        SELECT id, sdr_stage, followup_count, last_outbound_at,
               rejection_count, segmento
        FROM leads
        WHERE followup_due_at IS NOT NULL
          AND followup_due_at <= NOW()
          AND sdr_stage NOT IN ('won', 'lost', 'opt_out')
    """)).fetchall()

    stats = {"matched": len(rows), "queued": 0, "skipped": 0, "archived": 0}
    for row in rows:
        decision = decide_followup(
            db, row[0],
            stage=row[1], followup_count=row[2],
            last_outbound_at=row[3], rejection_count=row[4],
            segment=row[5] or "",
        )
        if decision.cadence == "skip":
            stats["skipped"] += 1
            continue
        if decision.cadence == "archive":
            stats["archived"] += 1
            if apply:
                db.execute(text("UPDATE leads SET sdr_stage='lost' WHERE id=:id"),
                           {"id": row[0]})
            continue
        stats["queued"] += 1
        if apply:
            db.execute(
                text("""UPDATE leads
                        SET followup_due_at = :next_run,
                            followup_count = followup_count + 1
                        WHERE id = :id"""),
                {"id": row[0], "next_run": decision.next_run_at},
            )
    if apply and hasattr(db, "commit"):
        db.commit()
    return stats
```

### Ganho esperado
- **+3-5 pp reativação de leads "fantasma"** (cadência 24h/72h/7d captura quem pensou mas não respondeu)
- **−50% mensagens desperdiçadas** (skip automático se lead engajou)
- **Higiene**: archive automático após 2 rejeições (limita custo de WhatsApp + protege reputação)

### Teste sugerido

```python
# tests/test_sdr_followup_scheduler.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from backend.services.sdr_followup_scheduler import decide_followup, FollowupCadence


@pytest.mark.unit
def test_primeiro_followup_24h():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None  # sem engajamento
    decision = decide_followup(
        db, "L1", stage="intro", followup_count=0,
        last_outbound_at=datetime(2026, 6, 21, 10, 0),
        rejection_count=0, segment="academia",
    )
    assert decision.cadence == "24h"
    assert decision.next_run_at is not None


@pytest.mark.unit
def test_skip_se_engajou_24h():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (1,)  # engajou
    decision = decide_followup(
        db, "L2", stage="intro", followup_count=0,
        last_outbound_at=datetime.now() - timedelta(days=2),
        rejection_count=0, segment="restaurante",
    )
    assert decision.cadence == "skip"


@pytest.mark.unit
def test_archive_apos_2_rejeicoes():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    decision = decide_followup(
        db, "L3", stage="intro", followup_count=0,
        last_outbound_at=None, rejection_count=2, segment="comercio",
    )
    assert decision.cadence == "archive"


@pytest.mark.unit
def test_cadencia_progressiva():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    base = datetime(2026, 6, 21, 10, 0)
    d0 = decide_followup(db, "L", "intro", 0, base, 0, "x")
    d1 = decide_followup(db, "L", "intro", 1, base, 0, "x")
    d2 = decide_followup(db, "L", "intro", 2, base, 0, "x")
    assert (d0.cadence, d1.cadence, d2.cadence) == (
        FollowupCadence("24h"), FollowupCadence("72h"), FollowupCadence("final_7d")
    )
```

---

## Resumo executivo

| # | Quick Win | Esforço | Ganho principal | Dependências |
|---|---|---|---|---|
| 1 | Hook selector segment-aware | 6 h | +2-4 pp resposta hook | segment_insights.json (existe) |
| 2 | Objection classifier + scripted response | 8 h | −30% opt-out mal-tratado | objection_handling.md (existe) |
| 3 | Follow-up adaptativo com skip-on-engage | 5 h | +3-5 pp reativação fantasma | schema `followup_due_at` (criar migration) |

**Total**: ~19 h (≈ 2.5 dias úteis) para 3 quick wins que cobrem **3 das 7 capacidades SDR**
(identificadas como gaps na auditoria #41): outreach personalizado, objection handling, follow-up/retargeting.

**Ordem de execução recomendada**: #3 → #2 → #1
- #3 primeiro porque a migration de schema é blocker para os outros (se quiserem enriquecer follow-up com sinais de engajamento)
- #2 segundo porque o classificador é puro (sem dependência de schema)
- #1 terceiro porque precisa de dados de A/B para validar ganho real (roda em cima de #26 já em backlog)
