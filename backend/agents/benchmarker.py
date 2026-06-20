"""
benchmarker.py - Analisador de concorrencia para sites de mesmo segmento.

Recebe nicho + cidade e retorna insights sobre o que os top 5 sites concorrentes
oferecem, incluindo estrutura comum, CTAs, cores e secoes.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Padroes por nicho - fallback inteligente
# Estrutura: nicho -> dados de referencia
NICHO_PATTERNS: dict[str, dict[str, Any]] = {
    "academia": {
        "estrutura_comum": "hero-fullscreen + foto-instrutor + planos-grid + depoimentos",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#ff4444", "#222222", "#ffffff"],
        "secoes_obrigatorias": ["planos", "horarios", "localizacao", "depoimentos", "faq"],
        "diferenciacao_sugerida": "Adicionar calculadora de IMC e teste fisico gratuito",
        "elementos_extras": ["tabela de precos visivel", "fotos da academia", "bio do instrutor"],
    },
    "crossfit": {
        "estrutura_comum": "video-hero + wods-do-dia + precos + localizacao",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#e74c3c", "#111111", "#f39c12"],
        "secoes_obrigatorias": ["wod", "horarios", "precificacao", "equipe", "localizacao"],
        "diferenciacao_sugerida": "Gamificacao com ranking de alunos e desafios mensais",
        "elementos_extras": ["wod diario", "niveis de box", "certificacoes crossfit"],
    },
    "barbearia": {
        "estrutura_comum": "before-after + servicos + precos + agendamento",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#1a1a1a", "#c9a227", "#ffffff", "#8b4513"],
        "secoes_obrigatorias": ["servicos", "portifolio", "localizacao", "agendamento"],
        "diferenciacao_sugerida": "Sistema de fidelidade com cartela digital e promocoes",
        "elementos_extras": ["antes/depois", "equipe", "ambiente do espaco"],
    },
    "salao": {
        "estrutura_comum": "galeria-hero + servicos + precos + agendamento",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#ff69b4", "#ffffff", "#2c1810", "#d4a574"],
        "secoes_obrigatorias": ["servicos", "galeria", "promocoes", "agendamento"],
        "diferenciacao_sugerida": "Fotos de transformacao e secao de trends de cabelo 2026",
        "elementos_extras": ["looks famosos", "produtos usados", "antes/depois"],
    },
    "clinica": {
        "estrutura_comum": "foto-medico + especialidade + agendamento + convenios",
        "cta_predominante": "Telefone",
        "cores_tipicas": ["#0066cc", "#ffffff", "#f5f5f5", "#2c5282"],
        "secoes_obrigatorias": ["equipe medica", "especialidades", "convenios", "localizacao"],
        "diferenciacao_sugerida": "Agendamento online com escolha de horario e telemedicine",
        "elementos_extras": ["curriculo medico", "artigos educativos", "convenios aceitos"],
    },
    "odontologia": {
        "estrutura_comum": "hero-sorriso + tratamentos + implantodontia + agendamento",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#00bcd4", "#ffffff", "#006064", "#e0f7fa"],
        "secoes_obrigatorias": ["tratamentos", "equipe", "tecnologia", "localizacao"],
        "diferenciacao_sugerida": "Simulador de sorriso com IA e plano de tratamento digital",
        "elementos_extras": ["tecnologia 3d", "antes/depois", "faq dental"],
    },
    "estetica": {
        "estrutura_comum": "antes-after + servicos + promocoes + agendamento",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#e91e63", "#ffffff", "#fce4ec", "#9c27b0"],
        "secoes_obrigatorias": ["servicos", "antes-depois", "promocoes", "equipe"],
        "diferenciacao_sugerida": "Quiz de pele e recomendacao personalizada de tratamentos",
        "elementos_extras": ["produtos vendidos", "antes/depois", "depoimentos"],
    },
    "nutricionista": {
        "estrutura_comum": "hero-foto + abordagens + precos + contato",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#4caf50", "#ffffff", "#81c784", "#1b5e20"],
        "secoes_obrigatorias": ["abordagens", "sobre", "planos", "receitas"],
        "diferenciacao_sugerida": "Calculadora de IMC/GC e plano alimentar demo gratuito",
        "elementos_extras": ["calculadora nutricional", "receitas", "blog de alimentacao"],
    },
    "psicologia": {
        "estrutura_comum": "ambiente- acolhedor + abordagem + agendamento + informacoes",
        "cta_predominante": "Telefone",
        "cores_tipicas": ["#7e57c2", "#ffffff", "#ede7f6", "#311b92"],
        "secoes_obrigatorias": ["abordagens", "sobre mim", "faq", "localizacao"],
        "diferenciacao_sugerida": "Conteudo sobre sade mental e primeiro atendimento gratuito",
        "elementos_extras": ["artigos", "depoimentos anonimos", "convenios"],
    },
    "advocacia": {
        "estrutura_comum": "hero-formal + areas + experiencia + contato",
        "cta_predominante": "Telefone",
        "cores_tipicas": ["#37474f", "#ffffff", "#78909c", "#1a237e"],
        "secoes_obrigatorias": ["areas de atencao", "experiencia", "publicacoes", "contato"],
        "diferenciacao_sugerida": "Artigos sobre direitos e chatbot de triagem inicial",
        "elementos_extras": ["casos de sucesso", "oab", "publicacoes", "imprensa"],
    },
    "contabilidade": {
        "estrutura_comum": "hero-empresa + servicos + quem-serve + contato",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#1565c0", "#ffffff", "#e3f2fd", "#0d47a1"],
        "secoes_obrigatorias": ["servicos", "para-quem", "diferenciais", "contato"],
        "diferenciacao_sugerida": "Simulador de economia fiscal e checklist gratuito MEI",
        "elementos_extras": ["calculadora de impostos", "artigos", "faq contabil"],
    },
    "restaurante": {
        "estrutura_comum": "fotos-prato + cardapio + localizacao + reservas",
        "cta_predominante": "Reserva Online",
        "cores_tipicas": ["#d32f2f", "#ffffff", "#212121", "#ffeb3b"],
        "secoes_obrigatorias": ["cardapio", "galeria", "horarios", "localizacao"],
        "diferenciacao_sugerida": "Encomendas de festas e eventos com formulario de orcamento",
        "elementos_extras": ["cardapio sazonal", "chef", "resenhas google"],
    },
    "pizzaria": {
        "estrutura_comum": "pizzas-hero + cardapio + delivery + promocoes",
        "cta_predominante": "Pedido Online",
        "cores_tipicas": ["#e53935", "#ffffff", "#ffecb3", "#bf360c"],
        "secoes_obrigatorias": ["cardapio", "promocoes", "delivery", "localizacao"],
        "diferenciacao_sugerida": "Sistema de pedidos com feedback em tempo real e pix",
        "elementos_extras": ["combos", "bebidas", "sobremesa", "avaliacoes"],
    },
    "pet": {
        "estrutura_comum": "pets-hero + servicos + produtos + agendamento",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#8bc34a", "#ffffff", "#33691e", "#fff9c4"],
        "secoes_obrigatorias": ["banho tosa", "veterinario", "produtos", "agendamento"],
        "diferenciacao_sugerida": "App de controles de vacinacao e reminders de racao",
        "elementos_extras": ["raças atendidas", "urgencias", "galeria de pets"],
    },
    "farmacia": {
        "estrutura_comum": "hero-produtos + servicos + delivery + localizacao",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#43a047", "#ffffff", "#c8e6c9", "#1b5e20"],
        "secoes_obrigatorias": ["produtos", "servicos", "delivery", "horarios"],
        "diferenciacao_sugerida": "Chatbot para consulta de medicamentos e orcamentos",
        "elementos_extras": ["manipulacao", "delivery", "plantao 24h"],
    },
    "fotografia": {
        "estrutura_comum": "portfolio-hero + pacotes + portafolio + contato",
        "cta_predominante": "WhatsApp",
        "cores_tipicas": ["#424242", "#ffffff", "#9e9e9e", "#212121"],
        "secoes_obrigatorias": ["portfolio", "pacotes", "depoimentos", "contato"],
        "diferenciacao_sugerida": "Galeria com Lightbox interativo e preview online de ensaios",
        "elementos_extras": ["antes/depois", "equipe", "equipamentos"],
    },
}


def _match_nicho(nicho: str) -> str:
    """Encontra o nicho mais similar no dicionario."""
    nicho_lower = nicho.lower()

    # Match exato
    for key in NICHO_PATTERNS:
        if key in nicho_lower or nicho_lower in key:
            return key

    # Match parcial
    keywords_map = {
        "gym": "academia",
        "fitness": "academia",
        "musculacao": "academia",
        "barber": "barbearia",
        "cabelo": "salao",
        "beleza": "salao",
        "medic": "clinica",
        "dent": "odontologia",
        "dental": "odontologia",
        "skin": "estetica",
        "estetica": "estetica",
        "diet": "nutricionista",
        "nutri": "nutricionista",
        "psi": "psicologia",
        "psic": "psicologia",
        "jurid": "advocacia",
        "advog": "advocacia",
        "cont": "contabilidade",
        "contad": "contabilidade",
        "food": "restaurante",
        "cafe": "restaurante",
        "pizza": "pizzaria",
        "dog": "pet",
        "veter": "pet",
        "photo": "fotografia",
        "foto": "fotografia",
    }

    for keyword, nicho_key in keywords_map.items():
        if keyword in nicho_lower:
            return nicho_key

    # Default
    return "academia"


def analisar_concorrencia(nicho: str, cidade: str = "") -> dict[str, Any]:
    """
    Analisa concorrencia e retorna insights sobre o segmento.

    Args:
        nicho: Segmento/nicho do negocio (ex: "academia", "barbearia", "nutricionista")
        cidade: Cidade para contexto local (opcional)

    Returns:
        dict com:
            - nicho: Nicho processado
            - cidade: Cidade informada
            - patterns: Dict com:
                - estrutura_comum: Estrutura mais frequente
                - cta_predominante: Call-to-action mais usado
                - cores_tipicas: Lista de cores comuns
                - secoes_obrigatorias: Lista de secoes que concorrentes tem
            - diferenciacao_sugerida: Ideia para se destacar
            - elementos_extras: Elementos que a maioria tem

    Note:
        Por enquanto usa fallback inteligente baseado em nicho.
        TODO: Integracao futura com web search para analise real de sites.
    """
    nicho_normalizado = _match_nicho(nicho)

    if nicho_normalizado in NICHO_PATTERNS:
        patterns = NICHO_PATTERNS[nicho_normalizado]
        logger.info(f"[Benchmarker] Usando padroes para nicho: {nicho_normalizado}")
    else:
        patterns = NICHO_PATTERNS["academia"]
        logger.warning(f"[Benchmarker] Nicho '{nicho}' nao encontrado, usando default")

    return {
        "nicho": nicho_normalizado,
        "cidade": cidade or "local",
        "patterns": {
            "estrutura_comum": patterns["estrutura_comum"],
            "cta_predominante": patterns["cta_predominante"],
            "cores_tipicas": patterns["cores_tipicas"],
            "secoes_obrigatorias": patterns["secoes_obrigatorias"],
        },
        "diferenciacao_sugerida": patterns["diferenciacao_sugerida"],
        "elementos_extras": patterns.get("elementos_extras", []),
        "source": "fallback-inteligente",
    }


def get_nichos_disponiveis() -> list[str]:
    """Retorna lista de nichos suportados pelo fallback."""
    return list(NICHO_PATTERNS.keys())


def get_patterns_por_nicho(nicho: str) -> dict[str, Any]:
    """Retorna os patterns completos para um nicho especifico."""
    nicho_normalizado = _match_nicho(nicho)
    return NICHO_PATTERNS.get(nicho_normalizado, NICHO_PATTERNS["academia"])


# Exports
__all__ = [
    "analisar_concorrencia",
    "get_nichos_disponiveis",
    "get_patterns_por_nicho",
    "NICHO_PATTERNS",
]
