"""
copy_angles.py
==============

Framework de ângulos de copy por (nicho, subnicho, público).

Implementa os 8 frameworks clássicos de copywriting com type hints, NamedTuples
imutáveis e exemplos reais de copywriters brasileiros. Cada framework define
templates de hook, body e CTA, além de tags para recomendar o ângulo mais
adequado conforme nicho, subnicho e polo estético.

Polos estéticos suportados: SOFT, BOLD, CORPORATE, MINIMAL.
"""

from __future__ import annotations

from typing import NamedTuple, Optional


# ==============================================================================
# ESTRUTURA DE DADOS
# ==============================================================================


class CopyAngle(NamedTuple):
    """Estrutura imutável que define um ângulo/framework de copy.

    Attributes:
        framework: nome canônico do framework (ex.: "StoryBrand").
        hook_template: template do gancho inicial (1-2 frases de impacto).
        body_template: template do corpo do copy (desenvolvimento).
        cta_template: template do call-to-action final.
        best_for_nichos: nichos onde o framework performa melhor.
        best_for_polos: polos estéticos onde o framework combina mais.
        public_examples: exemplos reais de copywriters brasileiros.
    """

    framework: str
    hook_template: str
    body_template: str
    cta_template: str
    best_for_nichos: tuple[str, ...]
    best_for_polos: tuple[str, ...]
    public_examples: tuple[str, ...]


# ==============================================================================
# 1. STORYBRAND (Donald Miller)
# ==============================================================================
# Estrutura: Personagem (cliente) tem um Problema e encontra um Guide (você)
# que tem um Plano e chama para Ação, mostrando o que evita fracasso.

_STORYBRAND = CopyAngle(
    framework="StoryBrand",
    hook_template=(
        "Você não é o herói dessa história. Seu cliente é. E ele está "
        "perdido em {nicho} há {tempo}."
    ),
    body_template=(
        "1. Personagem: o {publico} quer {desejo}, mas trava no {problema}. "
        "2. Guide: nós já ajudamos {quantidade} {publico} a passar por isso. "
        "3. Plano: em {etapas} passos simples, levamos você de {antes} "
        "para {depois}. "
        "4. Falha em evitar: continuar fazendo {erro_comum} custa {custo}."
    ),
    cta_template=(
        "Agende sua conversa gratuita de diagnóstico. Vamos desenhar seu "
        "plano em 15 minutos — sem compromisso."
    ),
    best_for_nichos=(
        "advocacia",
        "clinica",
        "consultoria",
        "educacao",
        "coaching",
    ),
    best_for_polos=("CORPORATE", "MINIMAL", "SOFT"),
    public_examples=(
        "Érico Rocha (advogados) — usa o personagem como cliente ansioso",
        "Paulo Cuenca (clínicas) — guia como médico humanizado",
        "Pedro Sobrinho (mentor) — herói é o aluno em transição",
    ),
)


# ==============================================================================
# 2. PAS (Dan Kennedy)
# ==============================================================================
# Estrutura: Problem → Agitate → Solution. Clássico para resposta direta.

_PAS = CopyAngle(
    framework="PAS",
    hook_template=(
        "Cansado de {problema_dores} em {nicho}? Não é falta de esforço — "
        "é falta de método."
    ),
    body_template=(
        "PROBLEMA: hoje você acorda e a primeira coisa que sente é {dor}. "
        "AGITAR: enquanto você tenta {tatica_fracassada}, seu concorrente "
        "fechou {resultado_concorrente}. A cada semana que passa, a distância "
        "aumenta {consequencia}. "
        "SOLUÇÃO: com {metodo}, em {prazo} você {resultado_real}."
    ),
    cta_template=(
        "Clique abaixo e receba o passo a passo. Vagas limitadas nesta turma."
    ),
    best_for_nichos=(
        "academia",
        "marketing",
        "infoproduto",
        "imobiliaria",
        "fintech",
    ),
    best_for_polos=("BOLD", "CORPORATE"),
    public_examples=(
        "Caio Carneiro — PAS clássico em lançamentos digitais",
        "Bruno Perônico — PAS agressivo com agitação visceral para Bold",
        "Dan Kennedy (EUA, referência original) — copy de controle em newsletters",
    ),
)


# ==============================================================================
# 3. AIDA
# ==============================================================================
# Estrutura: Attention → Interest → Desire → Action. Modelo clássico de 1898.

_AIDA = CopyAngle(
    framework="AIDA",
    hook_template=(
        "ATENÇÃO: {estatistica_chocante} sobre {nicho}. O que ninguém te conta."
    ),
    body_template=(
        "INTERESSE: a maioria dos {publico} faz {pratica_comum}, mas os 5% "
        "que fazem {pratica_elite} colhem {resultado_elite}. "
        "DESEJO: imagine abrir o painel e ver {cena_desejada}. Em {prazo}, "
        "isso vira rotina — não exceção. "
        "AÇÃO: comece hoje com {oferta_inicial}."
    ),
    cta_template=(
        "Garanta sua vaga agora. Próxima turma abre em 48h."
    ),
    best_for_nichos=(
        "ecommerce",
        "infoproduto",
        "academia",
        "clinica",
        "imobiliaria",
    ),
    best_for_polos=("BOLD", "MINIMAL", "CORPORATE"),
    public_examples=(
        "Pedro Sobrinho — AIDA direto ao ponto para academia (Borba energy)",
        "Érico Rocha — AIDA em VSL de lançamento",
        "Russell Brunson (EUA) — AIDA em scripts de webinar",
    ),
)


# ==============================================================================
# 4. BEFORE-AFTER-BRIDGE (Jon Benson)
# ==============================================================================
# Estrutura: estado atual (Before) → estado desejado (After) → mecanismo (Bridge).

_BAB = CopyAngle(
    framework="Before-After-Bridge",
    hook_template=(
        "Antes: {estado_atual}. Depois: {estado_desejado}. A ponte: {metodo}."
    ),
    body_template=(
        "BEFORE: você está preso em {sintoma} — {consequencia_diaria}. "
        "AFTER: ao aplicar {metodo}, em {prazo} você conquista {beneficios}, "
        "volta a {ritual_desejado} e sente {emocao_final}. "
        "BRIDGE: o método tem {numero_etapas} etapas: "
        "(1) {etapa_1}, "
        "(2) {etapa_2}, "
        "(3) {etapa_3}. "
        "Cada etapa leva {tempo_etapa}."
    ),
    cta_template=(
        "Entre na lista de espera. Avisamos antes de abrir para o público."
    ),
    best_for_nichos=(
        "academia",
        "nutricao",
        "clinica",
        "marketing",
        "educacao",
        "coaching",
    ),
    best_for_polos=("SOFT", "MINIMAL", "CORPORATE"),
    public_examples=(
        "Jon Benson (EUA, criador) — BAB para vídeos de vendas (VSL)",
        "Pedro Sobrinho — BAB aplicado a transformação corporal",
        "Thiago Finch (BR) — BAB para nutrição clínica",
    ),
)


# ==============================================================================
# 5. SOCIAL PROOF CASCADE
# ==============================================================================
# Estrutura: manchete → prova específica → prova geral → prova do autor.

_SOCIAL_PROOF = CopyAngle(
    framework="Social Proof Cascade",
    hook_template=(
        "{numero_clientes}+ {publico} em {nicho} já passaram por aqui. "
        "Veja o que dizem."
    ),
    body_template=(
        "MANCHETE: {headline_resultado}. "
        "PROVA ESPECÍFICA: {narrativa_cliente_com_nome_e_idade} — "
        "antes {antes_numerico}, depois {depois_numerico}. "
        "PROVA GERAL: {porcentagem}% dos clientes relatam {beneficio_comum} "
        "nas primeiras {prazo_inicial}. "
        "PROVA DO AUTOR: {credenciais_autor} — {numeros_autor}."
    ),
    cta_template=(
        "Entre para o próximo grupo. Vagas abertas enquanto houver calendário."
    ),
    best_for_nichos=(
        "clinica",
        "educacao",
        "advocacia",
        "imobiliaria",
        "consultoria",
        "academia",
    ),
    best_for_polos=("SOFT", "CORPORATE", "MINIMAL"),
    public_examples=(
        "Paulo Cuenca — prova social em abundância para clínicas",
        "Caio Carneiro — cascata de depoimentos em página de vendas",
        "Marie Forleo (referência) — prova + storytelling do autor",
    ),
)


# ==============================================================================
# 6. CONTRARIAN / REFRAME
# ==============================================================================
# Estrutura: você está fazendo errado → não faça X, faça Y → insight contraintuitivo.

_CONTRARIAN = CopyAngle(
    framework="Contrarian/Reframe",
    hook_template=(
        "Pare de fazer {pratica_comum}. Está sabotando seu resultado em {nicho}."
    ),
    body_template=(
        "INSIGHT: a maioria dos {publico} acredita que {crenca_limitante}. "
        "Estão errados. "
        "REFRAME: o que funciona de verdade é {pratica_contra_intuitiva}. "
        "Por quê? Porque {explicacao_mecanismo}. "
        "EVIDÊNCIA: dados de {fonte} mostram que {estatistica_reforco}. "
        "QUEBRA DE PARADIGMA: enquanto você {habito_antigo}, quem aplica "
        "{novo_habito} colhe {resultado_novo}."
    ),
    cta_template=(
        "Quer ver como aplicar o oposto? Baixe o guia gratuito (link abaixo)."
    ),
    best_for_nichos=(
        "marketing",
        "fintech",
        "educacao",
        "coaching",
        "infoproduto",
        "consultoria",
    ),
    best_for_polos=("BOLD", "MINIMAL"),
    public_examples=(
        "Pedro Adão — contrarian clássico para marketing digital",
        "Russell Brunson (EUA) — reframe em DotCom Secrets",
        "Nathalia Arcuri — finanças com quebra de crenças populares",
    ),
)


# ==============================================================================
# 7. AUTHORITY / FOUNDER STORY
# ==============================================================================
# Estrutura: credencial → luta → virada → missão.

_AUTHORITY = CopyAngle(
    framework="Authority/Founder Story",
    hook_template=(
        "Há {anos} anos eu {situacao_inicial}. Hoje {resultado_atual}. "
        "Aqui está o que aprendi."
    ),
    body_template=(
        "CREDENCIAL: {titulos_e_experiencia} — mas nada disso importou "
        "quando {luta_inicial}. "
        "LUTA: perdi {consequencia_negativa}. Quase {decisao_dolorosa}. "
        "VIRADA: descobri {insight_transformador} e, em {prazo}, "
        "conquistei {primeiro_resultado}. "
        "MISSÃO: ajudei {quantidade_pessoas} a {transformacao_coletiva}. "
        "Agora é sua vez."
    ),
    cta_template=(
        "Se minha história falou com você, o próximo capítulo pode ser nosso."
    ),
    best_for_nichos=(
        "coaching",
        "consultoria",
        "educacao",
        "clinica",
        "advocacia",
        "marketing",
    ),
    best_for_polos=("SOFT", "CORPORATE"),
    public_examples=(
        "Érico Rocha — founder story em escala para lançamento",
        "Bruno Perônico — founder story agressivo para mentorias Bold",
        "Alex Hormozi (EUA, referência) — $100M Leads com origem no fundo do poço",
    ),
)


# ==============================================================================
# 8. SPECIFICITY BIAS
# ==============================================================================
# Estrutura: números específicos + datas + locais + restrições.
# Aumenta conversão em 30%+ segundo Cialdini e estudos de landing pages.

_SPECIFICITY = CopyAngle(
    framework="Specificity Bias",
    hook_template=(
        "Em {data_especifica}, {numero_clientes} {publico} de {cidade} "
        "fecharam {resultado_especifico}. Restam {vagas_restantes} vagas."
    ),
    body_template=(
        "NÚMEROS: {percentual_1}% atingem {meta_1} em {prazo_1}. "
        "{percentual_2}% atingem {meta_2} em {prazo_2}. "
        "DATAS: turma abre {data_abertura}, encerra {data_encerramento}, "
        "encontro ao vivo em {data_evento} às {horario}. "
        "LOCAL: {local_ou_plataforma}. "
        "RESTRIÇÃO: limite de {limite_vagas} vagas; sem gravação após {data_limite_acesso}. "
        "PROVA: {numero_casos_documentados} casos documentados entre "
        "{periodo_inicio} e {periodo_fim}."
    ),
    cta_template=(
        "Reserve sua vaga com {valor_simbólico}. Restam {vagas_restantes} de {total_vagas}."
    ),
    best_for_nichos=(
        "academia",
        "imobiliaria",
        "clinica",
        "educacao",
        "infoproduto",
        "marketing",
        "advocacia",
    ),
    best_for_polos=("BOLD", "CORPORATE", "MINIMAL"),
    public_examples=(
        "Bruno Perônico — Specificity em contagem regressiva agressiva",
        "Pedro Sobrinho — Specificity em turmas de academia com vagas limitadas",
        "Alex Hormozi (EUA) — $100M Offers com restrições e datas precisas",
    ),
)


# ==============================================================================
# REGISTRO CENTRAL
# ==============================================================================


COPY_ANGLES: dict[str, CopyAngle] = {
    "storybrand": _STORYBRAND,
    "pas": _PAS,
    "aida": _AIDA,
    "bab": _BAB,
    "social_proof": _SOCIAL_PROOF,
    "contrarian": _CONTRARIAN,
    "authority": _AUTHORITY,
    "specificity": _SPECIFICITY,
}


# ==============================================================================
# SCORING / RECOMENDAÇÃO
# ==============================================================================


# Pesos heurísticos por framework para nichos onde brilham.
_NICHO_AFFINITY_BOOST: dict[str, dict[str, int]] = {
    "academia": {"bab": 2, "specificity": 2, "pas": 1, "aida": 1},
    "clinica": {"storybrand": 2, "social_proof": 2, "bab": 1, "authority": 1},
    "advocacia": {"storybrand": 2, "authority": 1, "social_proof": 1, "specificity": 1},
    "marketing": {"pas": 2, "contrarian": 2, "aida": 1, "specificity": 1},
    "infoproduto": {"aida": 2, "pas": 1, "specificity": 1, "bab": 1},
    "ecommerce": {"aida": 2, "specificity": 1, "social_proof": 1},
    "educacao": {"storybrand": 1, "bab": 1, "social_proof": 1, "authority": 1},
    "coaching": {"storybrand": 2, "authority": 2, "bab": 1},
    "consultoria": {"storybrand": 2, "authority": 1, "social_proof": 1},
    "imobiliaria": {"pas": 1, "social_proof": 1, "specificity": 2},
    "fintech": {"pas": 1, "contrarian": 1, "specificity": 1},
    "nutricao": {"bab": 2, "social_proof": 1, "specificity": 1},
}

# Pesos por polo: alguns frameworks combinam melhor com identidade visual.
_POLO_AFFINITY_BOOST: dict[str, dict[str, int]] = {
    "SOFT": {"bab": 2, "storybrand": 1, "social_proof": 1, "authority": 1},
    "BOLD": {"pas": 2, "contrarian": 2, "specificity": 1, "aida": 1},
    "CORPORATE": {"storybrand": 2, "social_proof": 1, "specificity": 1, "pas": 1},
    "MINIMAL": {"aida": 1, "bab": 1, "specificity": 1, "storybrand": 1},
}


def _normalize(s: str) -> str:
    """Normaliza string para comparação: minúsculo, sem acentos, sem espaços."""
    return (
        s.lower()
        .strip()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _score_framework(
    framework_key: str,
    nicho: Optional[str],
    subnicho: Optional[str],
    polo: Optional[str],
) -> int:
    """Calcula pontuação do framework com base em nicho, subnicho e polo."""
    score = 0
    nk = _normalize(nicho) if nicho else ""
    sk = _normalize(subnicho) if subnicho else ""
    pk = _normalize(polo) if polo else ""

    if nk:
        score += _NICHO_AFFINITY_BOOST.get(nk, {}).get(framework_key, 0) * 3
        # Bônus se o subnicho bater com a keyword do nicho.
        if sk and sk in nk:
            score += 1

    if pk:
        score += _POLO_AFFINITY_BOOST.get(pk, {}).get(framework_key, 0) * 2

    # Bônus leve por subnicho genérico quando informado.
    if sk:
        score += 1

    return score


def get_recommended_angle(
    nicho: str,
    subnicho: Optional[str] = None,
    polo: Optional[str] = None,
) -> CopyAngle:
    """Retorna o CopyAngle mais adequado para a combinação informada.

    Args:
        nicho: nicho principal (ex.: "academia", "clinica", "marketing").
        subnicho: subnicho opcional (ex.: "musculacao", "odontologia").
        polo: polo estético ("SOFT", "BOLD", "CORPORATE" ou "MINIMAL").

    Returns:
        O CopyAngle com maior pontuação. Em empate, mantém ordem de
        declaração do dicionário COPY_ANGLES.

    Examples:
        >>> angle = get_recommended_angle("academia", "musculacao", "BOLD")
        >>> angle.framework
        'PAS'
    """
    best_key: Optional[str] = None
    best_score: int = -1

    for key in COPY_ANGLES:
        current = _score_framework(key, nicho, subnicho, polo)
        if current > best_score:
            best_score = current
            best_key = key

    # Fallback defensivo: sempre há 8 entradas, mas cobre dicionário vazio.
    if best_key is None:
        best_key = next(iter(COPY_ANGLES))

    return COPY_ANGLES[best_key]


def list_frameworks() -> list[str]:
    """Lista todos os frameworks disponíveis (chaves canônicas)."""
    return list(COPY_ANGLES.keys())


__all__ = [
    "CopyAngle",
    "COPY_ANGLES",
    "get_recommended_angle",
    "list_frameworks",
]