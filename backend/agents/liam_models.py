"""Modelos Pydantic do Liam"""
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

import time
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Agente Liam - Desenvolvedor Frontend
Versão HTTP Direto (sem Pydantic AI)
"""
import json
import re
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from llm_direct import call_claude
from agent_rag import format_rag_prompt, get_agent_temperature
# from prompt_templates import formatar_prompt_liam
from validation_layer import validar_html, gerar_prompt_retry


# Skills carregadas pelo liam.py via skill_loader
from color_enforcer import enforce_colors
from animation_injector import inject_animation_classes

# ===== MODELOS PYDANTIC =====

class LiamInput(BaseModel):
    """Entrada do Liam - Lead + Briefing do Theo"""
    nome: str
    cidade: str
    segmento: str
    telefone: str
    whatsapp: Optional[str] = None
    rating: Optional[float] = 0
    reviews: Optional[List[Dict[str, Any]]] = []
    fotos: Optional[List[str]] = []
    colors: Optional[Dict[str, Any]] = None
    briefing: str = Field(..., min_length=500)  # Briefing do Theo
    logo_url: Optional[str] = None  # Logo SVG/WebP do Alex
    assets_dir: str = ""  # Pasta de assets do Alex
    website: Optional[str] = None
    reviews_count: Optional[int] = 0  # Total de avaliacoes reais
    fotos_classificadas: Optional[Dict[str, Any]] = {}  # Classificacao Alex: {fachada, ambiente, equipamento, equipe}

class LiamOutput(BaseModel):
    """Saída do Liam - HTML completo"""
    html: str = Field(..., description="HTML completo do site")
    tamanho_kb: int = 0
    principios_aplicados: int = 18
    scripts_injetados: Optional[Dict[str, bool]] = None

# ===== MOTION SCRIPT =====

