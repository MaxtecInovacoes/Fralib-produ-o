"""SDR Playbooks canônicos por nicho (Sprint 3A).

Define NICHO_PLAYBOOKS com 8 nichos canônicos + fallback "default".
Cada playbook tem:
- perguntas_obrigatorias: lista de perguntas que devem ser feitas (em ordem sugerida)
- red_flags: sinais de lead frio que devem encerrar qualificação rápido
- objecoes_comuns: objeções típicas com respostas canônicas
- gatilhos_conversao: palavras/argumentos que tendem a converter
- tom_recomendado: tom do Franz (consultivo, energetico, premium, etc)
- frase_hook_inicial: primeira frase do funil (template)

Função principal:
- get_nicho_playbook(nicho) -> dict (sempre retorna, fallback "default")

Não usa LLM. Lookup direto em dict (O(1)).
"""
from __future__ import annotations

from typing import Optional

# ════════════════════════════════════════════════════════════════════
# PLAYBOOKS CANÔNICOS POR NICHO
# ════════════════════════════════════════════════════════════════════

NICHO_PLAYBOOKS: dict[str, dict] = {
    "academia_crossfit": {
        "perguntas_obrigatorias": [
            "capacidade_max_alunos",
            "horario_pico",
            "concorrente_principal",
            "taxa_evasao_mensal",
            "investe_em_marketing",
        ],
        "red_flags": [
            "sem_instagram",
            "sem_whatsapp_ativo",
            "rating_abaixo_4.0",
            "menos_de_50_reviews",
            "sem_site_e_sem_instagram",
        ],
        "objecoes_comuns": {
            "muito_caro": "Academia que cobra R$ 150+ converte 2x mais — analise mostra ROI em 3 meses.",
            "sem_tempo": "Setup leva 2 min. Depois você publica no ar com seu WhatsApp linkado.",
            "ja_tem_personal": "Site capta lead que personal não alcança. Funciona como equipe de marketing 24/7.",
            "clientes_poucos": "Justamente — site traz os clientes que você ainda não tem.",
        },
        "gatilhos_conversao": [
            "familia",
            "resultado_real",
            "horario_flexivel",
            "crossfit_competicao",
            "comunidade",
        ],
        "tom_recomendado": "energetico, direto, focado em resultado",
        "frase_hook_inicial": "Eai! Vi que vocês tão no crossfit — quanto tempo de operação?",
        "objecao_silencio_max_horas": 18,
    },
    "nutricionista_esportiva": {
        "perguntas_obrigatorias": [
            "atende_presencial_ou_online",
            "media_pacientes_mes",
            "ticket_medio_consulta",
            "nicho_atleta_ou_amador",
            "possui_conteudo_para_leads",
        ],
        "red_flags": [
            "sem_instagram",
            "sem_cref_se_atletica",
            "menos_de_20_reviews",
            "site_inativo_ha_mais_de_1_ano",
        ],
        "objecoes_comuns": {
            "muito_caro": "Site capta 5-10 leads/mês — basta 1 converter pra pagar o investimento.",
            "sem_tempo": "Você não precisa mexer — a gente atualiza. Leva 5 min do seu tempo.",
            "ja_tem_consultorio": "Site traz lead novo, consultório fideliza. Complementam.",
            "resultado_nao_garanto": "Não precisa garantir. Site mostra método e depoimentos — lead se convence.",
        },
        "gatilhos_conversao": [
            "antes_de_prova",
            "ganho_massa",
            "emagrecimento_saudavel",
            "performance",
            "depoimento_paciente",
        ],
        "tom_recomendado": "consultivo, empático, baseado em ciência",
        "frase_hook_inicial": "Oi! Você atende mais atleta ou público geral? Pergunto pra mostrar exemplos do seu nicho.",
        "objecao_silencio_max_horas": 30,
    },
    "barbearia_premium": {
        "perguntas_obrigatorias": [
            "media_atendimentos_dia",
            "ticket_medio_corte",
            "possui_agendamento_online",
            "investe_em_barba",
            "cliente_recorrente_ou_novo",
        ],
        "red_flags": [
            "rating_abaixo_4.3",
            "sem_agendamento",
            "instagram_sem_feed_ha_3_meses",
            "preco_muito_abaixo_media_regiao",
        ],
        "objecoes_comuns": {
            "caro": "Barbearia premium cobra R$ 60+ — site passa credibilidade que justifica.",
            "sem_tempo": "15 min pra aprovar, depois é no automático.",
            "ja_tenho_cliente": "Site traz cliente novo, fidelização você já faz.",
            "instagram_ja_resolve": "Instagram é vitrine, site é loja. Quem fecha é site.",
        },
        "gatilhos_conversao": [
            "barba_bigode",
            "corte_agendado",
            "vip",
            "noivo_pacote",
        ],
        "tom_recomendado": "direto, confiante, estilo brotherhood",
        "frase_hook_inicial": "Salve! Vi que vocês tão com agenda aberta — como tá o movimento no sábado?",
        "objecao_silencio_max_horas": 12,
    },
    "restaurante_familiar": {
        "perguntas_obrigatorias": [
            "media_clientes_dia",
            "ticket_medio",
            "possui_delivery",
            "cardapio_tamanho",
            "horario_pico",
        ],
        "red_flags": [
            "sem_whatsapp_visivel",
            "rating_abaixo_4.0",
            "site_com_cardapio_desatualizado",
            "sem_instagram",
        ],
        "objecoes_comuns": {
            "delivery_ja_resolve": "iFood cobra 27%. Site próprio fica com 100% da margem.",
            "cliente_ja_conhece": "Conhece, mas pede pelo site? O site traz cliente NOVO.",
            "caro": "Site custa menos que 1 mês de iFood Pro.",
        },
        "gatilhos_conversao": [
            "familia",
            "almoço_exec",
            "delivery_proprio",
            "ambiente_familiar",
        ],
        "tom_recomendado": "caloroso, acolhedor, focado em experiência",
        "frase_hook_inicial": "Oi! Vi o cardápio de vocês — atende mais almoço ou jantar?",
        "objecao_silencio_max_horas": 24,
    },
    "clinica_estetica": {
        "perguntas_obrigatorias": [
            "procedimentos_top3",
            "ticket_medio",
            "possui_antes_e_depois",
            "investe_em_trafego_pago",
            "possui_anamnese_digital",
        ],
        "red_flags": [
            "sem_instagram_com_fotos_reais",
            "sem_alvara_visible",
            "rating_abaixo_4.3",
            "preco_muito_abaixo_concorrencia",
        ],
        "objecoes_comuns": {
            "muito_caro": "Site capta lead qualificado, não curioso. ROI em 2-3 conversões.",
            "ja_tenho_marketing": "Marketing sem site perde 40% do lead. Site completa o funil.",
            "resultado_depende_paciente": "Por isso site mostra antes/depois — lead se convence antes de marcar.",
        },
        "gatilhos_conversao": [
            "antes_e_depois",
            "procedimento_especifico",
            "parcelamento",
            "depoimento",
        ],
        "tom_recomendado": "premium, técnico, focado em resultado",
        "frase_hook_inicial": "Olá! Vocês fazem mais qual procedimento? Quero mostrar o site ideal pro seu carro-chefe.",
        "objecao_silencio_max_horas": 36,
    },
    "advocacia_trabalhista": {
        "perguntas_obrigatorias": [
            "area_atuacao_especifica",
            "media_processos_mes",
            "atende_pj_ou_clt",
            "possui_consultoria_preventiva",
            "ticket_medio_honorario",
        ],
        "red_flags": [
            "sem_oab_visivel",
            "sem_especializacao_clara",
            "site_com_mais_de_2_anos_sem_atualizar",
        ],
        "objecoes_comuns": {
            "cliente_ja_chega_indicado": "Indicação esfria. Site aquece lead novo.",
            "marketing_advocacia_e_limitado": "Conforme OAB — site institucional é 100% permitido.",
            "caro": "1 processo ganho paga 12 meses de site.",
        },
        "gatilhos_conversao": [
            "direito_trabalhista",
            "rescisao_indireta",
            "horas_extras",
            "assedio_moral",
        ],
        "tom_recomendado": "serio, tecnico, empatico",
        "frase_hook_inicial": "Bom dia. Atende mais pessoa física ou empresa? Pra eu calibrar o site pro seu público.",
        "objecao_silencio_max_horas": 48,
    },
    "ecommerce_basico": {
        "perguntas_obrigatorias": [
            "nicho_produtos",
            "ticket_medio",
            "possui_estoque_proprio",
            "faturamento_mensal_estimado",
            "investe_em_trafego_pago",
        ],
        "red_flags": [
            "sem_metricas_basicas",
            "sem_instagram",
            "dependencia_100_marketplace",
            "margem_abaixo_de_30",
        ],
        "objecoes_comuns": {
            "marketplace_ja_resolve": "Marketplace cobra 16-20%. Site próprio = 100% seu.",
            "caro": "Site capta lead qualificado. 1 venda = 6 meses de site pagos.",
            "sem_tempo": "Catálogo leva 5 min. Site fica no ar em 48h.",
        },
        "gatilhos_conversao": [
            "frete_gratis",
            "parcelamento",
            "desconto_primeira_compra",
            "avaliacao_verificada",
        ],
        "tom_recomendado": "comercial, objetivo, focado em conversao",
        "frase_hook_inicial": "Eai! Vi que vocês vendem online — Shopee, Mercado Livre ou site próprio?",
        "objecao_silencio_max_horas": 18,
    },
    "default": {
        "perguntas_obrigatorias": [
            "segmento_principal",
            "ticket_medio",
            "media_clientes_mes",
            "investe_em_marketing",
            "principal_desafio_hoje",
        ],
        "red_flags": [
            "sem_instagram",
            "sem_whatsapp",
            "rating_abaixo_4.0",
            "sem_presenca_digital",
        ],
        "objecoes_comuns": {
            "caro": "Site capta lead qualificado. 1 cliente novo paga o investimento.",
            "sem_tempo": "15 min pra aprovar, depois a gente opera.",
            "ja_tenho_site": "Site novo capta melhor que site antigo. Auditoria inclusa.",
            "nao_preciso": "Hoje 70% do consumidor pesquisa online antes de comprar.",
        },
        "gatilhos_conversao": [
            "resultado_real",
            "depoimento",
            "garantia",
            "frete_gratis",
        ],
        "tom_recomendado": "consultivo, descubra o que lead precisa antes de vender",
        "frase_hook_inicial": "Oi! Vi que vocês tão em [segmento]. Qual o maior desafio hoje?",
        "objecao_silencio_max_horas": 24,
    },
}


def get_nicho_playbook(nicho: str) -> dict:
    """Retorna playbook canonico do nicho (sempre retorna, fallback "default").

    Args:
        nicho: segmento canonico (academia_crossfit, nutricionista_esportiva, etc).
                Se vazio, None ou nao mapeado, retorna "default".

    Returns:
        Dict com chaves: perguntas_obrigatorias, red_flags, objecoes_comuns,
        gatilhos_conversao, tom_recomendado, frase_hook_inicial,
        objecao_silencio_max_horas.
    """
    if not nicho:
        return NICHO_PLAYBOOKS["default"]
    # Normaliza: lowercase, strip
    nicho_norm = str(nicho).lower().strip().replace(" ", "_").replace("-", "_")
    if nicho_norm in NICHO_PLAYBOOKS:
        return NICHO_PLAYBOOKS[nicho_norm]
    # Fallback 1: tenta match parcial (e.g. "academia_crossfit_sp" -> "academia_crossfit")
    for canonical in NICHO_PLAYBOOKS:
        if canonical != "default" and canonical in nicho_norm:
            return NICHO_PLAYBOOKS[canonical]
    # Fallback 2: default
    return NICHO_PLAYBOOKS["default"]


def list_nichos() -> list[str]:
    """Lista todos os nichos com playbook canonico (incluindo default)."""
    return list(NICHO_PLAYBOOKS.keys())


def format_playbook_for_prompt(playbook: dict) -> str:
    """Formata playbook para injecao no system prompt (bullets curtos)."""
    lines: list[str] = []
    lines.append(f"TOM RECOMENDADO: {playbook.get('tom_recomendado', 'consultivo')}")
    lines.append("")
    lines.append("PERGUNTAS OBRIGATORIAS (em ordem sugerida):")
    for i, p in enumerate(playbook.get("perguntas_obrigatorias", [])[:5], 1):
        lines.append(f"  {i}. {p}")
    lines.append("")
    lines.append("RED FLAGS (lead frio - encerre rapido):")
    for rf in playbook.get("red_flags", [])[:5]:
        lines.append(f"  - {rf}")
    lines.append("")
    lines.append("GATILHOS DE CONVERSAO (argumentos que convertem):")
    for g in playbook.get("gatilhos_conversao", [])[:5]:
        lines.append(f"  - {g}")
    return "\n".join(lines)
