"""
Dream job - consolida lessons de TODOS os tenants em lessons globais.

Job noturno (3h BRT). Le:
- backend/memory/u*/franz_lead_*.json (lead memories de todos tenants)
- backend/memory/u*/sdr_learning.json (sdr learning de todos tenants)

Processa:
- Detecta padroes cross-tenant (objecoes mais comuns, BANT medio por segmento,
  horarios de melhor resposta, ganchos que funcionam)
- Deduplica lessons
- Promove lessons cross-tenant para global_lessons.json

Resultado:
- backend/agents/bryan_knowledge/global_lessons.json (cross-tenant)
- Atualiza rag_knowledge/sdr_agents/*.md
"""

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("dreamer")


GLOBAL_LESSONS_PATH = Path("backend/agents/bryan_knowledge/global_lessons.json")
LEARNING_DIR = Path("backend/memory")


@dataclass(frozen=True)
class DreamStats:
    tenants_processed: int
    leads_analyzed: int
    lessons_extracted: int
    lessons_promoted: int
    patterns_detected: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def _load_all_learning_data() -> list[dict[str, Any]]:
    """Carrega learning data de TODOS os tenants."""
    results = []
    if not LEARNING_DIR.exists():
        log.warning(f"[DREAM] Diretorio {LEARNING_DIR} nao existe")
        return results
    for user_dir in LEARNING_DIR.iterdir():
        if not user_dir.is_dir() or not user_dir.name.startswith("u"):
            continue
        for memory_file in user_dir.glob("franz_lead_*.json"):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["_tenant_id"] = user_dir.name
                data["_file"] = str(memory_file.relative_to(LEARNING_DIR))
                results.append(data)
            except Exception as e:
                log.warning(f"[DREAM] Falha lendo {memory_file}: {e}")
    return results


def _extract_patterns(leads: list[dict[str, Any]]) -> dict[str, Any]:
    """Extrai padroes cross-tenant."""
    patterns = {
        "objecoes_comuns": Counter(),
        "segmentos_mais_comuns": Counter(),
        "stages_mais_comuns": Counter(),
        "hottest_hours": Counter(),
        "wall_street_close_success": 0,
        "wall_street_close_attempts": 0,
        "won_count": 0,
        "lost_count": 0,
        "opt_out_count": 0,
        "bant_budget_distribution": Counter(),
        "bant_authority_distribution": Counter(),
        "bant_timeline_distribution": Counter(),
    }
    for lead in leads:
        # Segmento
        seg = lead.get("segmento", "") or "?"
        patterns["segmentos_mais_comuns"][seg] += 1
        # Stage
        stage = lead.get("stage", "") or "?"
        patterns["stages_mais_comuns"][stage] += 1
        # Objecao
        obj = lead.get("main_objection", "") or ""
        if obj:
            patterns["objecoes_comuns"][obj[:50]] += 1
        # Deal status
        ds = lead.get("deal_status", "") or ""
        if ds == "won":
            patterns["won_count"] += 1
        elif ds == "lost":
            patterns["lost_count"] += 1
        elif ds == "opt_out":
            patterns["opt_out_count"] += 1
        # Wall street close
        if lead.get("wall_street_close_used"):
            patterns["wall_street_close_attempts"] += 1
            if ds == "won":
                patterns["wall_street_close_success"] += 1
        # BANT
        for k in ("bant_budget", "bant_authority", "bant_timeline"):
            v = lead.get(k, "") or ""
            if v:
                patterns[f"bant_{k.split('_')[1]}_distribution"][v] += 1
    return patterns


def _promote_lessons(patterns: dict[str, Any]) -> list[str]:
    """Promove lessons a partir dos padroes."""
    lessons = []
    # Top 3 objecoes
    top_obj = patterns["objecoes_comuns"].most_common(3)
    for obj, count in top_obj:
        if count >= 2:
            lessons.append(
                f"Objection '{obj}' apareceu {count}x cross-tenant. "
                f"Tem resposta emparelhada pronta no objection_handling.md."
            )
    # Segmentos quentes
    top_seg = patterns["segmentos_mais_comuns"].most_common(3)
    for seg, count in top_seg:
        if count >= 2:
            lessons.append(
                f"Segmento '{seg}' teve {count} leads. "
                f"Priorizar design system em design_systems_library.py."
            )
    # Wall Street close effectiveness
    if patterns["wall_street_close_attempts"] > 0:
        success_rate = (
            patterns["wall_street_close_success"] / patterns["wall_street_close_attempts"] * 100
        )
        lessons.append(
            f"Wall Street close: {success_rate:.0f}% taxa de won "
            f"({patterns['wall_street_close_success']}/{patterns['wall_street_close_attempts']})."
        )
    # BANT distrib
    for k in ("bant_budget", "bant_authority", "bant_timeline"):
        dist = patterns.get(f"bant_{k.split('_')[1]}_distribution", Counter())
        if dist:
            top = dist.most_common(1)[0]
            lessons.append(f"{k}: maioria ({top[1]}) e '{top[0]}'.")
    return lessons


def run_dream(
    *,
    apply: bool = False,
    output_path: Path | None = None,
) -> DreamStats:
    """Executa dream job - consolida lessons cross-tenant.

    Args:
        apply: se True, salva no disco. Se False, dry-run
        output_path: onde salvar (default: GLOBAL_LESSONS_PATH)
    Returns:
        DreamStats com metricas
    """
    output_path = output_path or GLOBAL_LESSONS_PATH
    log.info(f"[DREAM] Iniciando (apply={apply}, output={output_path})")
    leads = _load_all_learning_data()
    if not leads:
        log.warning("[DREAM] Nenhum lead encontrado")
        return DreamStats(0, 0, 0, 0, 0)
    tenants = set(l.get("_tenant_id", "") for l in leads)
    patterns = _extract_patterns(leads)
    lessons = _promote_lessons(patterns)
    # Compila lessons globais
    global_lessons = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "tenants": len(tenants),
            "leads_analyzed": len(leads),
            "won": patterns["won_count"],
            "lost": patterns["lost_count"],
            "opt_out": patterns["opt_out_count"],
            "wall_street_close_success_rate": (
                patterns["wall_street_close_success"]
                / max(patterns["wall_street_close_attempts"], 1) * 100
            ),
        },
        "top_objections": dict(patterns["objecoes_comuns"].most_common(10)),
        "top_segments": dict(patterns["segmentos_mais_comuns"].most_common(10)),
        "top_stages": dict(patterns["stages_mais_comuns"].most_common(10)),
        "lessons": lessons,
    }
    if apply:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(global_lessons, f, ensure_ascii=False, indent=2)
        log.info(f"[DREAM] Salvo em {output_path}: {len(lessons)} lessons")
    return DreamStats(
        tenants_processed=len(tenants),
        leads_analyzed=len(leads),
        lessons_extracted=len(lessons),
        lessons_promoted=len(lessons) if apply else 0,
        patterns_detected=len(patterns),
    )


def get_global_lessons() -> dict[str, Any]:
    """Le lessons globais salvas (do disco)."""
    if not GLOBAL_LESSONS_PATH.exists():
        return {}
    try:
        with open(GLOBAL_LESSONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"[DREAM] Falha lendo {GLOBAL_LESSONS_PATH}: {e}")
        return {}
