"""
backend/copywriting/polo_voice.py

Voz distinta por polo estetico. Cada polo (SOFT, BOLD, CLASSIC, TECH) possui
vocabulario proprio, palavras proibidas, estruturas de frase, gatilhos mentais,
tons proibidos, headlines e CTAs de exemplo em PT-BR.

A funcao validate_copy_against_voice(cop, polo) audita um copy contra a voz
do polo, retornando (problemas, sugestoes).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class PoloVoice:
    """Define a voz canonica de um polo estetico."""

    name: str
    description: str
    vocabulary: Tuple[str, ...]
    avoid_words: Tuple[str, ...]
    sentence_structures: Tuple[str, ...]
    mental_triggers: Tuple[str, ...]
    forbidden_tone: Tuple[str, ...]
    example_headlines: Tuple[str, ...]
    example_ctas: Tuple[str, ...]
    segments: Tuple[str, ...] = field(default_factory=tuple)

    def all_problem_tokens(self) -> Tuple[str, ...]:
        """Tokens que, quando aparecem no copy, disparam problemas."""
        return self.avoid_words + self.forbidden_tone


# -----------------------------------------------------------------------------
# SOFT  - Nutricao, Estetica, Pet Shop, Salao
# -----------------------------------------------------------------------------
SOFT = PoloVoice(
    name="SOFT",
    description=(
        "Voz afetuosa e cuidadora para servicos que cuidam do corpo, "
        "do pet ou do bem-estar: falar com calma, respeito e presenca."
    ),
    segments=("nutricao", "estetica", "pet_shop", "salao"),
    vocabulary=(
        "cuidar",
        "acolhimento",
        "ritual",
        "calma",
        "presenca",
        "transformacao silenciosa",
        "cada detalhe",
        "voce merece",
        "com afeto",
        "intencional",
        "com calma",
        "bem-estar",
        "escuta",
        "delicadeza",
    ),
    avoid_words=(
        "agressivo",
        "rendimento",
        "agora",
        "ultima chance",
        "garanta ja",
        "explodir",
        "machucar",
    ),
    sentence_structures=(
        "Voce + verbo suave + complemento afetuoso",
        "Cada + substantivo singular + e um + substantivo ritual",
        "Aqui + a gente + verbo no presente + com cuidado",
        "Quando voce + substantivo, + frase gentil de retorno",
        "E um + substantivo de cuidado + para voce",
        "Permita-se + infinitivo suave",
    ),
    mental_triggers=(
        "pertencimento",
        "autocuidado",
        "ritual",
        "prova de cuidado",
        "micro-progresso",
        "validacao emocional",
    ),
    forbidden_tone=(
        "agressivo",
        "apressado",
        "militar",
        "vendedor insistente",
    ),
    example_headlines=(
        "Cuidar de voce e o nosso oficio.",
        "Onde o tempo desacelera e a beleza respira.",
        "Cada visita, um ritual.",
        "Um espaco feito para voce voltar a si.",
        "Seu corpo merece essa pausa.",
    ),
    example_ctas=(
        "Agende um horario com a gente.",
        "Reserve um momento para voce.",
        "Vem conhecer nosso espaco.",
        "Quando quiser, estamos aqui.",
        "Marca no whats e a gente te espera.",
    ),
)


# -----------------------------------------------------------------------------
# BOLD  - Academia, Crossfit, Oficina, Eventos
# -----------------------------------------------------------------------------
BOLD = PoloVoice(
    name="BOLD",
    description=(
        "Voz direta, visceral e provocadora para publico que responde a "
        "confronto positivo e identidade tribal: falar sem filtro e sem desculpa."
    ),
    segments=("academia", "crossfit", "oficina", "eventos"),
    vocabulary=(
        "agora",
        "supere",
        "constancia",
        "sem desculpa",
        "faca",
        "aguentar",
        "quebrar limite",
        "raiz",
        "real",
        "sem filtro",
        "agressivo",
        "verdade",
        "cansa",
        "motivacao",
        "treino pesado",
    ),
    avoid_words=(
        "suave",
        "calma",
        "acolhimento",
        "talvez",
        "pode ser",
        "delicado",
        "contemplacao",
    ),
    sentence_structures=(
        "Voce + verbo imperativo + complemento duro",
        "Nao + frase de confronto curto",
        "O + substantivo + nao + verbo no presente",
        "Quando + condicao dura, + consequencia direta",
        "Sem + substantivo, + consequencia radical",
        "Constancia + e + substantivo forte",
    ),
    mental_triggers=(
        "prova",
        "comparacao social",
        "identidade tribal",
        "confronto positivo",
        "urgencia",
        "escassez",
    ),
    forbidden_tone=(
        "suave",
        "conivente",
        "academico",
        "decorativo",
    ),
    example_headlines=(
        "A academia nao te espera. O mundo nao te espera. Nem a proxima segunda.",
        "Voce nao esta cansado. Esta confortavel.",
        "O ferro nao mente. O espelho, entao...",
        "O resultado nao vem de motivacao. Vem de repeticao.",
        "Sua versao fraca nao merece o titulo.",
    ),
    example_ctas=(
        "Bora. Hoje.",
        "Clica e comeca agora.",
        "Para de enrolar. Inicia.",
        "Bate o martelo. Matricula ja.",
        "Vem treinar. So fala quem faz.",
    ),
)


# -----------------------------------------------------------------------------
# CLASSIC  - Advogado, Clinica, Dentista, Contador
# -----------------------------------------------------------------------------
CLASSIC = PoloVoice(
    name="CLASSIC",
    description=(
        "Voz tecnica e institucional para profissoes reguladas: transmitir "
        "metodo, sigilo, jurisprudencia e anos de experiencia."
    ),
    segments=("advogado", "clinica", "dentista", "contador"),
    vocabulary=(
        "sigilo",
        "responsabilidade",
        "tecnica",
        "analise",
        "metodo",
        "fundamentado",
        "comprovado",
        "jurisprudencia",
        "anamnese",
        "diagnostico",
        "etica",
        "protocolo",
        "documentacao",
        " parecer",
    ),
    avoid_words=(
        "arrasa",
        "viral",
        "maneiro",
        "foda-se",
        "agressivo",
        "meme",
        "trend",
    ),
    sentence_structures=(
        "Cada + substantivo de caso + e um + substantivo tecnico",
        "Analise + substantivo, decisao + substantivo tecnico",
        "Ha + numero + anos + verbo no gerundio + objeto institucional",
        "Conforme + referencia tecnica, + frase prudente",
        "O + substantivo institucional + requer + substantivo tecnico",
        "Antes de + acao, + substantivo tecnico",
    ),
    mental_triggers=(
        "autoridade tecnica",
        "prova documentada",
        "caso de sucesso",
        "reconhecimento",
        "experiencia",
        "selo institucional",
    ),
    forbidden_tone=(
        "espalhafatoso",
        "juvenil",
        "provocativo",
        "irreverente",
    ),
    example_headlines=(
        "Analise tecnica, decisao fundamentada.",
        "Cada caso e um processo, nao um palpite.",
        "Ha 18 anos defendendo o que e seu.",
        "Seu caso nao e o primeiro. E por isso que a gente resolve.",
        "Diagnostico antes de qualquer intervencao.",
    ),
    example_ctas=(
        "Agende uma consulta tecnica.",
        "Solicite uma analise inicial.",
        "Converse com nosso escritorio.",
        "Marque uma avaliacao sem compromisso.",
        "Pedir parecer tecnico agora.",
    ),
)


# -----------------------------------------------------------------------------
# TECH  - Energia Solar, SaaS, Arquitetura, Startups
# -----------------------------------------------------------------------------
TECH = PoloVoice(
    name="TECH",
    description=(
        "Voz racional e orientada a dados para produtos tecnologicos: falar "
        "em numeros, ROI, eficiencia e rastreabilidade."
    ),
    segments=("energia_solar", "saas", "arquitetura", "startups"),
    vocabulary=(
        "dados",
        "eficiencia",
        "ROI",
        "monitoramento",
        "performance",
        "automatizacao",
        "inteligencia",
        "rastreamento",
        "tecnologia proprietaria",
        "API",
        "kWh",
        "latencia",
        "throughput",
        "benchmark",
        "integracao",
    ),
    avoid_words=(
        "milagre",
        "magico",
        "revolucionario",
        "vai mudar sua vida",
        "transformador total",
        "inacreditavel",
    ),
    sentence_structures=(
        "Painel de + substantivo tecnico + que + verbo no presente",
        "Sua + substantivo mensuravel + calculada em + numero + cenarios",
        "Tecnologia + que + verbo mensuravel + em + prazo numerico",
        "X% + de + substantivo mensuravel + em + unidade de tempo",
        "Monitore + substantivo + em tempo real",
        "Reduza + substantivo + em + percentual",
    ),
    mental_triggers=(
        "racionalidade",
        "comparacao",
        "especificidade",
        "prova tecnica",
        "social proof tech",
        "transparencia metrica",
    ),
    forbidden_tone=(
        "místico",
        "espiritual",
        "vendedor de televenta",
        "motivacional vazio",
    ),
    example_headlines=(
        "Painel de monitoramento que mostra cada kWh em tempo real.",
        "Sua economia calculada em 14 cenarios diferentes.",
        "Tecnologia que se paga em 4,7 anos.",
        "Latencia media de 38ms. SLA documentado.",
        "API propria, dados seus. Sem lock-in.",
    ),
    example_ctas=(
        "Ver demo tecnica agora.",
        "Calcular ROI personalizado.",
        "Baixar documentacao tecnica.",
        "Solicitar prova de conceito.",
        "Agendar integracao exploratoria.",
    ),
)


# -----------------------------------------------------------------------------
# Registro canonico e helpers
# -----------------------------------------------------------------------------
POLO_VOICES: Dict[str, PoloVoice] = {
    "SOFT": SOFT,
    "BOLD": BOLD,
    "CLASSIC": CLASSIC,
    "TECH": TECH,
}


_VALID_POLOS = frozenset(POLO_VOICES.keys())


def get_polo_voice(polo: str) -> PoloVoice:
    """Retorna a PoloVoice canonica para o polo informado.

    Aceita nomes canonicos (SOFT/BOLD/CLASSIC/TECH) ou nomes normalizados
    em minusculas (soft/bold/classic/tech). Levanta ValueError se nao
    existir.
    """
    if not isinstance(polo, str):
        raise ValueError("polo deve ser string")

    key = polo.strip().upper()
    if key in POLO_VOICES:
        return POLO_VOICES[key]

    raise ValueError(
        f"Polo desconhecido: {polo!r}. Validos: {sorted(_VALID_POLOS)}"
    )


def _tokenize(text: str) -> List[str]:
    """Tokeniza em palavras minusculas preservando acentos."""
    import re

    if not text:
        return []
    return [t for t in re.findall(r"[\w'-]+", text.lower()) if t]


def _contains_any(text_lower: str, phrases: Tuple[str, ...]) -> List[str]:
    """Retorna as frases de `phrases` que aparecem como substring em
    `text_lower`."""
    found: List[str] = []
    for phrase in phrases:
        token = phrase.strip().lower()
        if not token:
            continue
        if token in text_lower:
            found.append(phrase)
    return found


def _suggestion_for(token: str, voice: PoloVoice) -> str:
    """Constroi uma sugestao de substituicao para um termo proibido."""
    # Heuristica simples: se o token casa com uma avoid_word, sugerimos
    # a primeira palavra do vocabulario proprio. Para tons proibidos,
    # devolvemos uma recomendacao generica de tom.
    avoid_lower = {w.strip().lower() for w in voice.avoid_words}
    if token.lower() in avoid_lower:
        replacement = voice.vocabulary[0] if voice.vocabulary else "termo do polo"
        return (
            f"Trocar '{token}' por algo da voz {voice.name}, "
            f"por exemplo: '{replacement}'."
        )
    return (
        f"Reescrever '{token}' mantendo o tom {voice.name} "
        f"(veja example_headlines e example_ctas)."
    )


def validate_copy_against_voice(
    cop: str, polo: str
) -> Tuple[List[str], List[str]]:
    """Audita um copy contra a voz canonica do polo.

    Retorna (problemas, sugestoes):
      - problemas: lista de avisos sobre termos proibidos, tons proibidos
        ou ausencia de vocabulario proprio;
      - sugestoes: lista de recomendacoes acionaveis para alinhar o copy
        a voz do polo.

    Nao levanta excecao quando o polo e invalido: retorna problemas
    descrevendo o erro, para que o caller registre e siga adiante.
    """
    problemas: List[str] = []
    sugestoes: List[str] = []

    if not isinstance(cop, str) or not cop.strip():
        problemas.append("Copy vazio ou invalido.")
        return problemas, sugestoes

    try:
        voice = get_polo_voice(polo)
    except ValueError as exc:
        problemas.append(str(exc))
        return problemas, sugestoes

    text_lower = cop.lower()

    # 1) avoid_words proibidas
    bad_words = _contains_any(text_lower, voice.avoid_words)
    for bad in bad_words:
        msg = f"Termo proibido no polo {voice.name}: '{bad}'."
        problemas.append(msg)
        sugestoes.append(_suggestion_for(bad, voice))

    # 2) tons proibidos (interpretacao por substring simples)
    bad_tones = _contains_any(text_lower, voice.forbidden_tone)
    for tone in bad_tones:
        msg = f"Tom proibido no polo {voice.name}: '{tone}'."
        problemas.append(msg)
        sugestoes.append(
            f"Reduzir o tom '{tone}' e reescrever usando vocabulary/{voice.name}."
        )

    # 3) sinais positivos: presenca de vocabulario proprio
    own_vocab_hits = _contains_any(text_lower, voice.vocabulary)
    if not own_vocab_hits:
        problemas.append(
            f"Copy sem vocabulario proprio de {voice.name} "
            f"(ex: {', '.join(voice.vocabulary[:3])})."
        )
        sugestoes.append(
            "Introduzir pelo menos uma expressao canonica de "
            f"{voice.name}. Sugestoes: "
            f"{', '.join(voice.vocabulary[:5])}."
        )

    # 4) tamanho minimo: copy muito curto costuma fugir da voz
    tokens = _tokenize(cop)
    if len(tokens) < 6:
        problemas.append(
            "Copy muito curto para carregar a voz canonica do polo."
        )
        sugestoes.append(
            f"Expandir usando estruturas como: "
            f"{voice.sentence_structures[0]}."
        )

    # 5) ausencia de CTA ou headline-style: quando nao houver sinal de CTA
    cta_signals = ("agende", "clica", "marque", "vamos", "bora", "solicite",
                   "agendar", "fale", "reserve", "chame", "ver demo",
                   "calcular", "baixar")
    if not any(sig in text_lower for sig in cta_signals):
        sugestoes.append(
            "Acrescentar um CTA no padrao "
            f"{voice.name}. Sugestoes: "
            f"{', '.join(voice.example_ctas[:3])}."
        )

    # 6) ausencia de headline/gancho: quando o copy nao contiver nenhum
    # termo de vocabulario proprio nem sinais de CTA, sinalizar.
    if not own_vocab_hits and not any(
        sig in text_lower for sig in cta_signals
    ):
        problemas.append(
            "Copy sem vocabulario proprio e sem CTA: nao conecta "
            f"com a voz {voice.name}."
        )
        sugestoes.append(
            "Reescrever usando example_headlines como ancora: "
            f"{voice.example_headlines[0]}"
        )

    return problemas, sugestoes


__all__ = [
    "PoloVoice",
    "SOFT",
    "BOLD",
    "CLASSIC",
    "TECH",
    "POLO_VOICES",
    "get_polo_voice",
    "validate_copy_against_voice",
]