
def get_essential_skills(agente: str) -> list[str]:
    """Retorna apenas skills essenciais para evitar timeout"""
    essential = {
        'caio': [],  # Caio não precisa de skills
        'theo': ['design-system'],  # Apenas design system
        'liam': ['ui-ux-pro-max', 'design-system'],  # Apenas 2 principais
        'liz': []  # Liz não precisa de skills
    }
    return essential.get(agente, [])


"""
Sistema de carregamento automático de skills
Versão: 1.0
Data: 2026-04-27
"""
import os
from pathlib import Path
from typing import List, Dict, Optional

SKILLS_DIR = Path("/root/ui-ux-pro-max-skill/.claude/skills")

def ler_skill(skill_name: str) -> str:
    """
    Lê guidelines de uma skill

    Args:
        skill_name: Nome da skill (ex: "ui-ux-pro-max" ou "schema-markup")

    Returns:
        Conteúdo do SKILL.md ou string vazia
    """
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"

    if not skill_path.exists():
        print(f"[Skills] ⚠️ Skill {skill_name} não encontrada em {skill_path}")

        # ✅ NOVO: Tentar path alternativo
        alt_path = Path.home() / ".claude" / "skills" / skill_name / "SKILL.md"
        if alt_path.exists():
            print(f"[Skills] ✅ Skill {skill_name} encontrada em path alternativo: {alt_path}")
            skill_path = alt_path
        else:
            print(f"[Skills] ❌ Skill {skill_name} não encontrada em nenhum path")
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
                print(f"[Skills] ⚠️ Erro ao ler bloco {bloco_path}: {eb}")

        content = content[:25000]  # Limite aumentado para leitura completa
        print(f"[Skills] ✅ Skill {skill_name} carregada ({len(content)} chars, {len(blocos)} blocos extras)")
        return content

    except Exception as e:
        print(f"[Skills] ❌ Erro ao ler skill {skill_name}: {e}")
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

    for skill in skills:
        guidelines = ler_skill(skill)
        if guidelines:
            guidelines_completo += f"\n\n{'='*60}\n# SKILL: {skill}\n{'='*60}\n\n{guidelines}\n"
            skills_carregadas.append(skill)

    if skills_carregadas:
        print(f"[Skills] 🎯 {len(skills_carregadas)} skills ativadas: {', '.join(skills_carregadas)}")
    else:
        print(f"[Skills] ⚠️ Nenhuma skill carregada")

    return guidelines_completo


# Configuração: Skills por agente
SKILLS_POR_AGENTE = {
    "theo": [
        "brand",           # Branding e identidade visual
        "design"           # Princípios de design
    ],
    "designer": [
        "ui-ux-pro-max",   # UI/UX profissional
        "design",          # Princípios de design
        "design-system",   # Sistema de design
        "ui-styling"       # Estilização de UI
    ],
    "liam": [
        "ui-ux-pro-max",   # UI/UX profissional
        "design",          # Orquestrador de design unificado
        "design-taste-frontend",  # ANTI-EMOJI, min-h-[100dvh], bias correction
        "design-system",   # Token architecture + motion principles
        "ui-styling"       # Awwwards-tier, high-end visual design
    ],
    "liz": [
        "design-system"    # Validação de design system
    ]
}


def get_skills_agente(agente: str, essential_only: bool = True) -> List[str]:
    """Retorna lista de skills para um agente"""
    return SKILLS_POR_AGENTE.get(agente, [])
