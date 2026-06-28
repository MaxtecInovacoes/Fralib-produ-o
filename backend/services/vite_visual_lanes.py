from __future__ import annotations

from typing import Any


_LANE_KEYS = ["lane_a", "lane_b", "lane_c", "lane_d"]


def _segment_family(segment: str, subnicho: str = "") -> str:
    raw = f"{segment} {subnicho}".lower()
    if any(token in raw for token in ("barbear", "barber", "barbeiro")):
        return "barbearia"
    if any(token in raw for token in ("nutri", "nutric")):
        return "nutricionista"
    if any(token in raw for token in ("academia", "crossfit", "muscul", "fitness", "funcional", "personal")):
        return "academia"
    return "default"


_LANES: dict[str, list[dict[str, Any]]] = {
    "academia": [
        {
            "id": "academia-iron-pulse",
            "name": "Iron Pulse",
            "fallback_palette": {"primary": "#ff4d2d", "secondary": "#6b0f1a", "bg_dark": "#0a0a0a", "bg_light": "#1b1b1b", "text_dark": "#111111"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "glass"},
            "copy": {"hero_badge": "Treino de alta intensidade", "about_kicker": "Método", "about_title": "Estrutura, carga e constância para evoluir em {city}.", "about_body": "{name} organiza o treino com leitura de objetivo, rotina e progressão de carga sem prometer atalhos.", "gallery_title": "Estrutura real, ritmo forte e presença local.", "gallery_intro": "Cada quadro reforça o ambiente, a densidade visual e a sensação de treino sério em {city}.", "reviews_title": "Resultados percebidos por quem já pisa no treino.", "reviews_intro": "A prova social entra como confiança local, não como decoração.", "faq_title": "Perguntas antes da primeira série.", "faq_intro": "Respostas curtas para matrícula, aula experimental e rotina.", "location_title": "Treine em {city} com rota direta.", "location_intro": "Contato e endereço aparecem sem atrito para não perder o clique.", "lifestyle_kicker": "Experiência", "contact_kicker": "Próximo passo"},
        },
        {
            "id": "academia-neon-grid",
            "name": "Neon Grid",
            "fallback_palette": {"primary": "#41ffd9", "secondary": "#1c2bff", "bg_dark": "#061018", "bg_light": "#dffcf7", "text_dark": "#051018"},
            "blocks": {"hero_variant": "video", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Treino com presença visual", "about_kicker": "Cenário", "about_title": "Ambiente noturno, energia alta e CTA sem ruído.", "about_body": "{name} aparece com linguagem mais futurista, foco em movimento e impacto visual para {city}.", "gallery_title": "Frames que parecem trailer, não catálogo.", "gallery_intro": "A galeria enfatiza luz, suor, equipamento e a atmosfera que sustenta a marca.", "reviews_title": "Sinais locais em fluxo contínuo.", "reviews_intro": "Depoimentos, score e cidade entram no ritmo da página.", "faq_title": "O que o aluno pergunta antes de entrar.", "faq_intro": "FAQ mais direto, pensado para conversão rápida no mobile.", "location_title": "Chegue pelo canal oficial.", "location_intro": "Tudo aponta para ação imediata, sem menus mortos.", "lifestyle_kicker": "Pulso", "contact_kicker": "Ação"},
        },
        {
            "id": "academia-sunset-track",
            "name": "Sunset Track",
            "fallback_palette": {"primary": "#ff7a00", "secondary": "#7f2d00", "bg_dark": "#14110f", "bg_light": "#fff1e2", "text_dark": "#1d130c"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Treino com acolhimento e disciplina", "about_kicker": "Rotina", "about_title": "Disciplina diária com linguagem mais humana.", "about_body": "{name} conversa com quem quer resultado consistente, mas também precisa encaixar o treino na vida real em {city}.", "gallery_title": "Treino visto de perto, sem pose vazia.", "gallery_intro": "As imagens reforçam constância, detalhe e clareza visual.", "reviews_title": "Confiança construída na rotina.", "reviews_intro": "A reputação local entra como prova de recorrência e cuidado.", "faq_title": "Dúvidas de quem vai começar ou voltar.", "faq_intro": "Resposta curta, sem jargão e sem inventar regra que o lead não confirmou.", "location_title": "Tudo pronto para visitar e começar.", "location_intro": "Mapa mental simples: cidade, endereço, contato e CTA.", "lifestyle_kicker": "Constância", "contact_kicker": "Convite"},
        },
        {
            "id": "academia-graphite-core",
            "name": "Graphite Core",
            "fallback_palette": {"primary": "#d9d9d9", "secondary": "#7a7a7a", "bg_dark": "#090909", "bg_light": "#efefef", "text_dark": "#111111"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stacked_cards", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Treino técnico", "about_kicker": "Precisão", "about_title": "Uma academia com leitura mais sóbria e técnica.", "about_body": "{name} assume composição limpa, mais contraste e mensagem menos promocional para destacar processo e estrutura.", "gallery_title": "Volume, técnica e acabamento visual.", "gallery_intro": "A narrativa privilegia forma, materiais e execução.", "reviews_title": "Credibilidade tratada como editorial.", "reviews_intro": "A seção de prova social deixa de parecer carrossel genérico.", "faq_title": "Perguntas objetivas antes da matrícula.", "faq_intro": "Sem excesso de texto e sem promessas irreais.", "location_title": "Presença local organizada.", "location_intro": "Informação funcional para quem quer decidir sem desvio.", "lifestyle_kicker": "Técnica", "contact_kicker": "Fechamento"},
        },
    ],
    "nutricionista": [
        {
            "id": "nutri-botanical-editorial",
            "name": "Botanical Editorial",
            "fallback_palette": {"primary": "#255b45", "secondary": "#c6a96c", "bg_dark": "#18392c", "bg_light": "#f8f5ee", "text_dark": "#173128"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Acompanhamento nutricional", "about_kicker": "Escuta", "about_title": "Consulta com escuta, estratégia e plano aplicável.", "about_body": "{name} aparece com linguagem mais editorial para valorizar acolhimento, método e atendimento local em {city}.", "gallery_title": "Consultório, rotina e sinais de confiança.", "gallery_intro": "A galeria mostra textura, alimento, ambiente e contexto humano.", "reviews_title": "O que os pacientes percebem no acompanhamento.", "reviews_intro": "A prova social entra com tom clínico e sem exagero publicitário.", "faq_title": "Dúvidas antes da consulta.", "faq_intro": "O visitante entende agenda, retorno, convênio e formato de atendimento.", "location_title": "Atendimento em {city} com acesso claro.", "location_intro": "Contato e localização aparecem com calma e legibilidade.", "lifestyle_kicker": "Cuidado", "contact_kicker": "Agendamento"},
        },
        {
            "id": "nutri-clinical-soft",
            "name": "Clinical Soft",
            "fallback_palette": {"primary": "#7ea08c", "secondary": "#3d5a4a", "bg_dark": "#f2efe8", "bg_light": "#ffffff", "text_dark": "#22362c"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Nutrição clínica com clareza", "about_kicker": "Processo", "about_title": "Informação leve, clínica e fácil de absorver.", "about_body": "{name} usa uma direção mais clara para reforçar confiança, leitura confortável e atendimento estruturado.", "gallery_title": "Ambiente claro e confiança gradual.", "gallery_intro": "Menos impacto dramático, mais serenidade e organização.", "reviews_title": "Credibilidade para marcar a primeira consulta.", "reviews_intro": "A reputação local sustenta o clique sem barulho visual.", "faq_title": "Perguntas práticas do primeiro atendimento.", "faq_intro": "FAQ pensado para reduzir ansiedade e simplificar a decisão.", "location_title": "Consultório e contato em evidência.", "location_intro": "Tudo legível, direto e com foco em conversão saudável.", "lifestyle_kicker": "Clareza", "contact_kicker": "Consulta"},
        },
        {
            "id": "nutri-performance-fuel",
            "name": "Performance Fuel",
            "fallback_palette": {"primary": "#e36b4d", "secondary": "#572b49", "bg_dark": "#1f1420", "bg_light": "#fff2ea", "text_dark": "#241826"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "glass"},
            "copy": {"hero_badge": "Nutrição para performance", "about_kicker": "Energia", "about_title": "Uma leitura mais esportiva para quem vive rotina intensa.", "about_body": "{name} assume tom de performance quando o contexto pede treino, recuperação e estratégia nutricional mais ativa.", "gallery_title": "Alimentação, performance e disciplina visual.", "gallery_intro": "A composição mistura detalhe, movimento e materiais ligados à rotina de treino.", "reviews_title": "Sinais de confiança em movimento.", "reviews_intro": "Cards e ritmo mais vivos para contextos esportivos.", "faq_title": "Perguntas de quem quer começar rápido.", "faq_intro": "Mais dinâmica, menos contemplativa.", "location_title": "Atendimento rápido, rota clara.", "location_intro": "O visitante entende onde está e como falar em segundos.", "lifestyle_kicker": "Performance", "contact_kicker": "Entrada"},
        },
        {
            "id": "nutri-coastal-light",
            "name": "Coastal Light",
            "fallback_palette": {"primary": "#2f8f9d", "secondary": "#d9b382", "bg_dark": "#f7fbfb", "bg_light": "#ffffff", "text_dark": "#16343a"},
            "blocks": {"hero_variant": "video", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Nutrição com leveza e direção", "about_kicker": "Bem-estar", "about_title": "Atmosfera mais leve sem perder autoridade.", "about_body": "{name} ganha uma assinatura mais respirada para nichos de saúde, longevidade e reeducação alimentar.", "gallery_title": "Leveza visual com informação útil.", "gallery_intro": "A página respira mais e evita densidade excessiva.", "reviews_title": "Opiniões tratadas como confiança de marca.", "reviews_intro": "A prova social fica menos promocional e mais editorial.", "faq_title": "Perguntas antes de cuidar da rotina.", "faq_intro": "Respostas claras para quem está comparando profissionais.", "location_title": "Atenda-se em {city} sem ruído.", "location_intro": "Contato, endereço e CTA em arranjo mais calmo.", "lifestyle_kicker": "Leveza", "contact_kicker": "Conversa"},
        },
    ],
    "barbearia": [
        {
            "id": "barber-heritage-reserve",
            "name": "Heritage Reserve",
            "fallback_palette": {"primary": "#c9a96a", "secondary": "#3d2a18", "bg_dark": "#0d0b0a", "bg_light": "#f4ede3", "text_dark": "#1b130f"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Barbearia premium", "about_kicker": "Ritual", "about_title": "Corte, barba e acabamento com leitura clássica.", "about_body": "{name} assume uma estética mais refinada para valorizar detalhe, atendimento e experiência presencial em {city}.", "gallery_title": "Textura, aço, couro e acabamento.", "gallery_intro": "A galeria precisa parecer parte do ritual, não um mosaico genérico.", "reviews_title": "Clientes que percebem detalhe e atendimento.", "reviews_intro": "A prova social reforça consistência, não exagero.", "faq_title": "Antes de reservar o horário.", "faq_intro": "Perguntas práticas sobre agenda, serviços e localização.", "location_title": "Visite a barbearia em {city}.", "location_intro": "Tudo aponta para reserva e presença local.", "lifestyle_kicker": "Atmosfera", "contact_kicker": "Reserva"},
        },
        {
            "id": "barber-studio-mono",
            "name": "Studio Mono",
            "fallback_palette": {"primary": "#f1f1f1", "secondary": "#555555", "bg_dark": "#090909", "bg_light": "#efefef", "text_dark": "#151515"},
            "blocks": {"hero_variant": "center", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte com direção contemporânea", "about_kicker": "Design", "about_title": "Assinatura visual sóbria, gráfica e precisa.", "about_body": "{name} entra numa linha mais contemporânea, com menos ornamento e mais contraste limpo.", "gallery_title": "Monocromia, recorte e presença.", "gallery_intro": "O visual privilegia sombra, forma e acabamento.", "reviews_title": "Confiança tratada com voz mais editorial.", "reviews_intro": "Menos excesso, mais recorte e clareza.", "faq_title": "Tudo o que importa antes de reservar.", "faq_intro": "Perguntas curtas para acelerar a escolha.", "location_title": "Agende e chegue sem ruído.", "location_intro": "O CTA precisa parecer inevitável.", "lifestyle_kicker": "Estilo", "contact_kicker": "Reserva"},
        },
        {
            "id": "barber-copper-smoke",
            "name": "Copper Smoke",
            "fallback_palette": {"primary": "#b96d3c", "secondary": "#4e281b", "bg_dark": "#160f0d", "bg_light": "#f6ece6", "text_dark": "#231511"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "glass"},
            "copy": {"hero_badge": "Corte e barba com atmosfera noturna", "about_kicker": "Presença", "about_title": "Uma barbearia mais quente, escura e cinematográfica.", "about_body": "{name} ganha contraste de cobre e fumaça para enfatizar ritual, noite e personalidade.", "gallery_title": "Luz baixa, metal quente e acabamento forte.", "gallery_intro": "O visual trabalha atmosfera e proximidade.", "reviews_title": "Sinais locais em ritmo mais vivo.", "reviews_intro": "A prova social pode ganhar movimento sem parecer aleatória.", "faq_title": "Perguntas para quem quer reservar hoje.", "faq_intro": "Menos texto e mais ação.", "location_title": "Localização e contato no mesmo pulso.", "location_intro": "A página fecha com sensação de convite imediato.", "lifestyle_kicker": "Noite", "contact_kicker": "Agende"},
        },
        {
            "id": "barber-midnight-club",
            "name": "Midnight Club",
            "fallback_palette": {"primary": "#8b7cf7", "secondary": "#1d153d", "bg_dark": "#080712", "bg_light": "#f2efff", "text_dark": "#16112e"},
            "blocks": {"hero_variant": "video", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Barbearia com assinatura autoral", "about_kicker": "Assinatura", "about_title": "Direção mais ousada para marcas que querem parecer únicas.", "about_body": "{name} assume uma linha mais autoral, com luz fria, composição noturna e CTA de reserva como foco central.", "gallery_title": "Uma estética de clube privado.", "gallery_intro": "O site precisa parecer menos genérico e mais memorável.", "reviews_title": "Reputação local com recorte de marca.", "reviews_intro": "A confiança vem sem perder identidade visual.", "faq_title": "O que o cliente quer saber antes do corte.", "faq_intro": "Objetivo, curto e acionável.", "location_title": "Chegue pelo contato oficial.", "location_intro": "A navegação fecha em reserva direta.", "lifestyle_kicker": "Assinatura", "contact_kicker": "Horário"},
        },
    ],
    "default": [
        {
            "id": "default-professional-dark",
            "name": "Professional Dark",
            "fallback_palette": {"primary": "#4f46e5", "secondary": "#1f2937", "bg_dark": "#0b1220", "bg_light": "#f8fafc", "text_dark": "#0f172a"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "glass"},
            "copy": {"hero_badge": "Atendimento local", "about_kicker": "Direção", "lifestyle_kicker": "Presença", "contact_kicker": "Contato"},
        },
        {
            "id": "default-editorial-light",
            "name": "Editorial Light",
            "fallback_palette": {"primary": "#0f766e", "secondary": "#155e75", "bg_dark": "#ffffff", "bg_light": "#f0fdfa", "text_dark": "#0f172a"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Serviço local", "about_kicker": "Clareza", "lifestyle_kicker": "Confiança", "contact_kicker": "Próximo passo"},
        },
        {
            "id": "default-conversion-bold",
            "name": "Conversion Bold",
            "fallback_palette": {"primary": "#ea580c", "secondary": "#7c2d12", "bg_dark": "#111827", "bg_light": "#fff7ed", "text_dark": "#111827"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Contato direto", "about_kicker": "Impacto", "lifestyle_kicker": "Presença", "contact_kicker": "Ação"},
        },
        {
            "id": "default-cinematic-soft",
            "name": "Cinematic Soft",
            "fallback_palette": {"primary": "#9333ea", "secondary": "#4338ca", "bg_dark": "#0f0a1f", "bg_light": "#f5f3ff", "text_dark": "#1f1235"},
            "blocks": {"hero_variant": "video", "services_variant": "stacked_cards", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Experiência local", "about_kicker": "Atmosfera", "lifestyle_kicker": "Marca", "contact_kicker": "Fechamento"},
        },
    ],
}


def resolve_visual_lane(
    *,
    segment: str = "",
    subnicho: str = "",
    visual_lane: str = "",
) -> dict[str, Any]:
    family = _segment_family(segment, subnicho)
    lanes = _LANES.get(family) or _LANES["default"]
    try:
        index = _LANE_KEYS.index(str(visual_lane or "").strip())
    except ValueError:
        index = 0
    return {
        "family": family,
        **lanes[index % len(lanes)],
    }
