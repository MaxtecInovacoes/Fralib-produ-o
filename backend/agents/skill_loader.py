
def get_essential_skills(agente: str) -> list[str]:
    """Retorna apenas skills essenciais para evitar timeout"""
    essential = {
        'caio': [],
        'agente_nicho': [],
        'agente_variacao': [],
        'arquiteto_mestre': ['design-with-taste'],
        'builder_renderer': ['site_skill_pack'],
        'validador': [],
        'bryan': [],
    }
    return essential.get(agente, [])


"""
Sistema de carregamento automático de skills
Versão: 1.0
Data: 2026-04-27
"""
import os
from pathlib import Path
from typing import List


def _skill_roots() -> list[Path]:
    """Candidate skill roots for VPS, local Codex, and legacy Claude installs."""
    roots: list[Path] = []
    for raw in (os.getenv("FRALIB_SKILLS_DIRS") or "").split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw.strip()))
    agents_dir = Path(__file__).resolve().parent
    repo_root = agents_dir.parents[1] if len(agents_dir.parents) > 1 else Path.cwd()
    home = Path.home()
    roots.extend(
        [
            agents_dir / "skill_packs",
            repo_root / ".agents" / "skills",
            Path("/root/ui-ux-pro-max-skill/.claude/skills"),
            Path("/root/.agents/skills"),
            Path("/root/.codex/skills"),
            Path("/root/.claude/skills"),
            home / ".agents" / "skills",
            home / ".codex" / "skills",
            home / ".claude" / "skills",
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _resolve_skill_path(skill_name: str) -> Path | None:
    for root in _skill_roots():
        path = root / skill_name / "SKILL.md"
        if path.exists():
            return path
    return None

def ler_skill(skill_name: str) -> str:
    """
    Lê guidelines de uma skill

    Args:
        skill_name: Nome da skill (ex: "ui-ux-pro-max" ou "schema-markup")

    Returns:
        Conteúdo do SKILL.md ou string vazia
    """
    skill_path = _resolve_skill_path(skill_name)
    if not skill_path:
        checked = ", ".join(str(root) for root in _skill_roots())
        print(f"[Skills] ERRO Skill {skill_name} nao encontrada. Roots: {checked}")
        return ""

    try:
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Carregar blocos numerados: SKILL_1.md, SKILL_2.md, etc.
        import glob as _glob
        skill_dir = skill_path.parent
        blocos = sorted(_glob.glob(str(skill_dir / "SKILL_*.md")))
        for bloco_path in blocos:
            try:
                with open(bloco_path, 'r', encoding='utf-8') as fb:
                    content += "\n\n" + fb.read()
            except Exception as eb:
                print(f"[Skills] WARN Erro ao ler bloco {bloco_path}: {eb}")

        max_chars = int(os.getenv("FRALIB_SKILL_MAX_CHARS") or "8000")
        content = content[:max_chars]
        print(f"[Skills] OK Skill {skill_name} carregada ({len(content)} chars, {len(blocos)} blocos extras)")
        return content

    except Exception as e:
        print(f"[Skills] ERRO ao ler skill {skill_name}: {e}")
        return ""


def carregar_skills(skills: List[str]) -> str:
    """
    Carrega múltiplas skills e combina guidelines

    Args:
        skills: Lista de nomes de skills

    Returns:
        Guidelines combinadas de todas as skills
    """
    guidelines_completo = ""
    skills_carregadas = []
    max_total_chars = int(os.getenv("FRALIB_SKILLS_TOTAL_MAX_CHARS") or "12000")

    for skill in skills:
        guidelines = ler_skill(skill)
        if guidelines:
            bloco = f"\n\n{'='*60}\n# SKILL: {skill}\n{'='*60}\n\n{guidelines}\n"
            restante = max_total_chars - len(guidelines_completo)
            if restante <= 0:
                print(f"[Skills] WARN Limite total atingido; pulando {skill}")
                continue
            guidelines_completo += bloco[:restante]
            skills_carregadas.append(skill)

    if skills_carregadas:
        print(f"[Skills] {len(skills_carregadas)} skills ativadas: {', '.join(skills_carregadas)}")
    else:
        print("[Skills] WARN Nenhuma skill carregada")

    return guidelines_completo


# Configuração: Skills por agente
SKILLS_POR_AGENTE = {
    "agente_nicho": [],
    "agente_variacao": [],
    "arquiteto_mestre": [
        "design-with-taste",
    ],
    "designer": [
        "impeccable",
        "design-with-taste",
        "emil-design-eng",
        "design-motion-principles",
    ],
    "builder_renderer": ["site_skill_pack"],
    "caio": [],
    "bryan": [],
    "validador": [
        # Gate atual e deterministico; validador LLM fica standby.
    ]
}


def get_skills_agente(agente: str, essential_only: bool = True) -> List[str]:
    """Retorna lista de skills para um agente"""
    agente = (agente or "").lower()
    if agente == "builder_renderer" and os.getenv("FRALIB_BUILDER_FULL_SKILLS", "0") != "0":
        return get_essential_skills("builder_renderer")
    return SKILLS_POR_AGENTE.get(agente, [])
