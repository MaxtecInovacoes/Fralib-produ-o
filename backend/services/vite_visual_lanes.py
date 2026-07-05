from __future__ import annotations

import re
import unicodedata
from typing import Any

from .vite_liquid_components import infer_aesthetic_pole


_LANE_KEYS = ["lane_a", "lane_b", "lane_c", "lane_d", "lane_e", "lane_f", "lane_g", "lane_h", "lane_i", "lane_j", "lane_k", "lane_l", "lane_m", "lane_n", "lane_o", "lane_p"]


# Aliases para nomes divergentes: lanes existentes com nomes "curtos"
# (barber-*, nutri-*) continuam funcionando, mas o registry canônico usa
# nomes completos (barbearia-*, nutricionista-*). Esse mapeamento é
# aplicado tanto em resolve_visual_lane quanto em helpers de lookup.
_LANE_ID_ALIASES: dict[str, str] = {
    # Barbearia (nomes curtos → canônico)
    "barber-atelier-light": "barbearia-atelier-light",
    "barber-brutal-mono": "barbearia-brutal-mono",
    "barber-copper-smoke": "barbearia-copper-smoke",
    "barber-heritage-reserve": "barbearia-heritage-reserve",
    "barber-midnight-club": "barbearia-midnight-club",
    "barber-old-money-green": "barbearia-old-money-green",
    "barber-street-red": "barbearia-street-red",
    "barber-studio-mono": "barbearia-studio-mono",
    # Nutricionista (nomes curtos → canônico)
    "nutri-botanical-editorial": "nutricionista-botanical-editorial",
    "nutri-clinical-soft": "nutricionista-clinical-soft",
    "nutri-coastal-light": "nutricionista-coastal-light",
    "nutri-family-table": "nutricionista-family-table",
    "nutri-hormone-care": "nutricionista-hormone-care",
    "nutri-performance-fuel": "nutricionista-performance-fuel",
    "nutri-premium-clinic": "nutricionista-premium-clinic",
    "nutri-sports-lab": "nutricionista-sports-lab",
}


def _canonicalize_lane_id(lane_id: str) -> str:
    """Resolve aliases: 'barber-foo' → 'barbearia-foo'."""
    if not lane_id:
        return lane_id
    return _LANE_ID_ALIASES.get(str(lane_id).strip(), str(lane_id).strip())


def _normalize_family_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _segment_family(segment: str, subnicho: str = "") -> str:
    """Resolve the visual lane family from the canonical niche vocabulary.

    Keep this selector deliberately broader than the lane catalog: if a lane
    family exists for a niche, ordinary segment labels must reach it instead of
    silently falling back to `default`.
    """
    raw = _normalize_family_text(f"{segment} {subnicho}")
    checks: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("barbearia", ("barbearia", "barbear", "barbeiro", "barba", "corte masculino")),
        ("salao", ("salao", "cabeleireiro", "cabelo", "manicure", "pedicure", "escova", "mechas")),
        ("nutricionista", ("nutricionista", "nutricao", "nutricional", "nutri ")),
        ("estetica", ("estetica", "estetic", "spa", "facial", "pele", "harmoniz", "botox", "preenchimento")),
        ("academia", ("academia", "crossfit", "cross fit", "muscul", "fitness", "funcional", "personal", "pilates", "yoga")),
        ("advogado", ("advogado", "advocacia", "juridico", "juridica", "direito", "trabalhista", "familia")),
        ("clinica", ("clinica", "medica", "medico", "consulta", "exame", "diagnostico")),
        ("dentista", ("dentista", "odontologia", "odontologico", "odonto", "implante", "clareamento")),
        ("energia_solar", ("energia solar", "fotovoltaica", "painel solar", "solar", "inversor", "cemig")),
        ("imobiliaria", ("imobiliaria", "imovel", "imoveis", "apartamento", "casa", "aluguel", "venda")),
        ("oficina", ("oficina", "mecanica", "mecanico", "auto pecas", "autopecas", "automotivo", "carro")),
        ("pet_shop", ("pet shop", "petshop", "veterinario", "veterinaria", "banho", "tosa", " pet ")),
        ("restaurante", ("restaurante", "pizzaria", "hamburgueria", "cafeteria", "padaria", "delivery", "cardapio")),
        ("salao", ("salao", "cabeleireiro", "cabelo", "manicure", "pedicure", "escova", "mechas")),
    )
    padded = f" {raw} "
    for family, tokens in checks:
        if any(token in padded for token in tokens):
            return family
    return "default"


_LANES: dict[str, list[dict[str, Any]]] = {
    "academia": [
        {
            "id": "academia-iron-pulse",
            "name": "Iron Pulse",
            "fallback_palette": {"primary": "#ff4d2d", "secondary": "#6b0f1a", "bg_dark": "#0a0a0a", "bg_light": "#1b1b1b", "text_dark": "#111111"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Treino de alta intensidade", "about_kicker": "Método", "about_title": "Estrutura, carga e constância para evoluir em {city}.", "about_body": "{name} organiza o treino com leitura de objetivo, rotina e progressão de carga.", "gallery_title": "Estrutura real, ritmo forte e rotina local.", "gallery_intro": "Cada quadro reforça ambiente, equipamento e sensação de treino sério em {city}.", "reviews_title": "Resultados percebidos por quem já pisa no treino.", "reviews_intro": "Avaliações, cidade e contato ajudam a decidir com segurança.", "faq_title": "Perguntas antes da primeira série.", "faq_intro": "Respostas curtas para matrícula, aula experimental e rotina.", "location_title": "Treine em {city} com rota direta.", "location_intro": "Contato e endereço aparecem sem atrito para não perder o clique.", "lifestyle_kicker": "Experiência", "contact_kicker": "Contato"},
        },
        {
            "id": "academia-neon-grid",
            "name": "Neon Grid",
            "fallback_palette": {"primary": "#41ffd9", "secondary": "#1c2bff", "bg_dark": "#061018", "bg_light": "#dffcf7", "text_dark": "#051018"},
            "blocks": {"hero_variant": "video", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Treino com presença visual", "about_kicker": "Cenário", "about_title": "Ambiente noturno, energia alta e WhatsApp claro.", "about_body": "{name} apresenta movimento, intensidade e informação útil para {city}.", "gallery_title": "Frames com energia de treino em andamento.", "gallery_intro": "A galeria enfatiza luz, suor, equipamento e atmosfera da academia.", "reviews_title": "Sinais locais em fluxo contínuo.", "reviews_intro": "Depoimentos, avaliação e cidade reforçam confiança.", "faq_title": "O que o aluno pergunta antes de entrar.", "faq_intro": "FAQ direto, pensado para decisão rápida no mobile.", "location_title": "Fale pelo WhatsApp.", "location_intro": "Endereço e contato ficam visíveis para ação imediata.", "lifestyle_kicker": "Pulso", "contact_kicker": "Ação"},
        },
        {
            "id": "academia-sunset-track",
            "name": "Sunset Track",
            "fallback_palette": {"primary": "#ff7a00", "secondary": "#7f2d00", "bg_dark": "#14110f", "bg_light": "#fff1e2", "text_dark": "#1d130c"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Treino com acolhimento e disciplina", "about_kicker": "Rotina", "about_title": "Disciplina diária com linguagem mais humana.", "about_body": "{name} conversa com quem quer resultado consistente, mas também precisa encaixar o treino na vida real em {city}.", "gallery_title": "Treino visto de perto, sem pose vazia.", "gallery_intro": "As imagens reforçam constância, detalhe e clareza visual.", "reviews_title": "Confiança construída na rotina.", "reviews_intro": "A reputação entra como sinal de recorrência e cuidado.", "faq_title": "Dúvidas de quem vai começar ou voltar.", "faq_intro": "Resposta curta, sem jargão e com orientação prática.", "location_title": "Tudo pronto para visitar e começar.", "location_intro": "Mapa simples: cidade, endereço, contato e WhatsApp.", "lifestyle_kicker": "Constância", "contact_kicker": "Convite"},
        },
        {
            "id": "academia-graphite-core",
            "name": "Graphite Core",
            "fallback_palette": {"primary": "#d9d9d9", "secondary": "#7a7a7a", "bg_dark": "#090909", "bg_light": "#efefef", "text_dark": "#111111"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stacked_cards", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Treino técnico", "about_kicker": "Precisão", "about_title": "Uma academia com leitura mais sóbria e técnica.", "about_body": "{name} apresenta composição limpa, mais contraste e mensagem menos promocional para destacar processo e estrutura.", "gallery_title": "Volume, técnica e acabamento visual.", "gallery_intro": "A sequência privilegia forma, materiais e execução.", "reviews_title": "Credibilidade com leitura direta.", "reviews_intro": "Avaliações aparecem com clareza para quem está comparando academias.", "faq_title": "Perguntas objetivas antes da matrícula.", "faq_intro": "Sem excesso de texto e sem promessas irreais.", "location_title": "Endereço e contato organizados.", "location_intro": "Informação funcional para quem quer decidir sem desvio.", "lifestyle_kicker": "Técnica", "contact_kicker": "Fechamento"},
        },
    ],
    "nutricionista": [
        {
            "id": "nutri-botanical-editorial",
            "name": "Botanical Editorial",
            "fallback_palette": {"primary": "#d8a64a", "secondary": "#2f5b47", "bg_dark": "#17382d", "bg_light": "#fbf6ea", "text_dark": "#173128"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Acompanhamento nutricional", "about_kicker": "Escuta", "about_title": "Consulta com escuta, estratégia e plano aplicável.", "about_body": "{name} organiza acolhimento, método e atendimento local em {city}.", "gallery_title": "Consultório, rotina e sinais de confiança.", "gallery_intro": "Consulta, preparo e rotina aparecem com clareza para quem quer decidir sem pressa.", "reviews_title": "O que os pacientes percebem no acompanhamento.", "reviews_intro": "Avaliações entram como sinal de confiança clínica, com linguagem objetiva e confiável.", "faq_title": "Dúvidas antes da consulta.", "faq_intro": "Perguntas diretas sobre agenda, retorno, convênio e formato de atendimento.", "location_title": "Atendimento em {city} com acesso claro.", "location_intro": "Contato e localização aparecem com calma e legibilidade.", "lifestyle_kicker": "Cuidado", "contact_kicker": "Agendamento"},
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
            "fallback_palette": {"primary": "#00a676", "secondary": "#273469", "bg_dark": "#101820", "bg_light": "#eefaf4", "text_dark": "#14231f"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Nutrição para performance", "about_kicker": "Energia", "about_title": "Rotina alimentar para treinar, recuperar e manter constância.", "about_body": "{name} conecta alimentação, rotina e acompanhamento para pacientes que querem evoluir com método em {city}.", "gallery_title": "Alimentos, consulta e rotina em composição ativa.", "gallery_intro": "As imagens destacam preparo, orientação e hábitos possíveis para o dia a dia.", "reviews_title": "Confiança para quem quer acompanhamento consistente.", "reviews_intro": "Avaliações, cidade e contato ajudam o paciente a decidir com segurança.", "faq_title": "Perguntas de quem quer começar rápido.", "faq_intro": "Respostas diretas sobre consulta, retorno e forma de atendimento.", "location_title": "Atendimento em {city} com rota clara.", "location_intro": "Endereço, WhatsApp e próximos passos ficam visíveis em poucos segundos.", "lifestyle_kicker": "Performance", "contact_kicker": "Entrada"},
        },
        {
            "id": "nutri-coastal-light",
            "name": "Coastal Light",
            "fallback_palette": {"primary": "#2f8f9d", "secondary": "#d9b382", "bg_dark": "#f7fbfb", "bg_light": "#ffffff", "text_dark": "#16343a"},
            "blocks": {"hero_variant": "video", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Nutrição com leveza e direção", "about_kicker": "Bem-estar", "about_title": "Atmosfera mais leve sem perder autoridade.", "about_body": "{name} organiza acompanhamento para saúde, longevidade e reeducação alimentar.", "gallery_title": "Leveza visual com informação útil.", "gallery_intro": "A página respira mais e evita densidade excessiva.", "reviews_title": "Opiniões tratadas como confiança de marca.", "reviews_intro": "Avaliações aparecem com menos pressão e mais clareza.", "faq_title": "Perguntas antes de cuidar da rotina.", "faq_intro": "Respostas claras para quem está comparando profissionais.", "location_title": "Atendimento em {city} sem complicação.", "location_intro": "Contato, endereço e WhatsApp em arranjo mais calmo.", "lifestyle_kicker": "Leveza", "contact_kicker": "Conversa"},
        },
    ],
    "barbearia": [
        {
            "id": "barber-heritage-reserve",
            "name": "Heritage Reserve",
            "fallback_palette": {"primary": "#c9a96a", "secondary": "#3d2a18", "bg_dark": "#0d0b0a", "bg_light": "#f4ede3", "text_dark": "#1b130f"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Barbearia premium", "about_kicker": "Ritual", "about_title": "Corte, barba e acabamento com leitura clássica.", "about_body": "{name} valoriza detalhe, atendimento e experiência presencial em {city}.", "gallery_title": "Textura, aço, couro e acabamento.", "gallery_intro": "Ambiente, serviço e detalhes do ritual entram em primeiro plano.", "reviews_title": "Clientes que percebem detalhe e atendimento.", "reviews_intro": "Avaliações reforçam consistência no atendimento.", "faq_title": "Antes de reservar o horário.", "faq_intro": "Perguntas práticas sobre agenda, serviços e localização.", "location_title": "Visite a barbearia em {city}.", "location_intro": "Reserva, endereço e contato ficam juntos.", "lifestyle_kicker": "Atmosfera", "contact_kicker": "Reserva"},
        },
        {
            "id": "barber-studio-mono",
            "name": "Studio Mono",
            "fallback_palette": {"primary": "#f1f1f1", "secondary": "#555555", "bg_dark": "#090909", "bg_light": "#efefef", "text_dark": "#151515"},
            "blocks": {"hero_variant": "center", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte com direção contemporânea", "about_kicker": "Design", "about_title": "Identidade sóbria, gráfica e precisa.", "about_body": "{name} entra numa linha mais contemporânea, com menos ornamento e mais contraste limpo.", "gallery_title": "Monocromia, recorte e presença.", "gallery_intro": "As imagens privilegiam sombra, forma e acabamento.", "reviews_title": "Confiança tratada com voz mais editorial.", "reviews_intro": "Menos excesso, mais recorte e clareza.", "faq_title": "Tudo o que importa antes de reservar.", "faq_intro": "Perguntas curtas para acelerar a escolha.", "location_title": "Agende e chegue sem complicação.", "location_intro": "O WhatsApp fica direto para reserva.", "lifestyle_kicker": "Estilo", "contact_kicker": "Reserva"},
        },
        {
            "id": "barber-copper-smoke",
            "name": "Copper Smoke",
            "fallback_palette": {"primary": "#b96d3c", "secondary": "#4e281b", "bg_dark": "#160f0d", "bg_light": "#f6ece6", "text_dark": "#231511"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte e barba com atmosfera noturna", "about_kicker": "Presença", "about_title": "Uma barbearia mais quente, escura e cinematográfica.", "about_body": "{name} usa contraste de cobre e luz baixa para enfatizar ritual, noite e personalidade.", "gallery_title": "Luz baixa, metal quente e acabamento forte.", "gallery_intro": "Atmosfera, proximidade e acabamento aparecem com luz mais intensa.", "reviews_title": "Sinais locais em ritmo mais vivo.", "reviews_intro": "Avaliações podem ganhar movimento sem perder clareza.", "faq_title": "Perguntas para quem quer reservar hoje.", "faq_intro": "Menos texto e mais ação.", "location_title": "Localização e contato no mesmo pulso.", "location_intro": "O fechamento conduz para reserva direta.", "lifestyle_kicker": "Noite", "contact_kicker": "Agende"},
        },
        {
            "id": "barber-midnight-club",
            "name": "Midnight Club",
            "fallback_palette": {"primary": "#8b7cf7", "secondary": "#1d153d", "bg_dark": "#080712", "bg_light": "#f2efff", "text_dark": "#16112e"},
            "blocks": {"hero_variant": "video", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Barbearia com assinatura autoral", "about_kicker": "Assinatura", "about_title": "Direção mais ousada para marcas que querem parecer únicas.", "about_body": "{name} assume uma linha mais autoral, com luz fria, composição noturna e CTA de reserva como foco central.", "gallery_title": "Uma estética de clube privado.", "gallery_intro": "Presença menos genérica, mais memorável e pronta para reserva.", "reviews_title": "Reputação local com recorte de marca.", "reviews_intro": "A confiança vem sem perder identidade visual.", "faq_title": "O que o cliente quer saber antes do corte.", "faq_intro": "Objetivo, curto e acionável.", "location_title": "Fale pelo WhatsApp.", "location_intro": "A jornada fecha em reserva direta.", "lifestyle_kicker": "Assinatura", "contact_kicker": "Horário"},
        },
    ],
    "advogado": [
        {
            "id": "advogado-statute-noir",
            "name": "Statute Noir",
            "fallback_palette": {"primary": "#c9a14a", "secondary": "#1a120b", "bg_dark": "#0b0805", "bg_light": "#f5efe3", "text_dark": "#15100a"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Advocacia com autoridade clássica", "about_kicker": "Tribunal", "about_title": "Leitura sóbria, argumento forte e presença que sustenta a causa.", "about_body": "{name} organiza a defesa e o atendimento jurídico com discrição, método e linguagem firme para clientes em {city}.", "gallery_title": "Biblioteca, tribunal e detalhe da escrita jurídica.", "gallery_intro": "Tradição, livros, códigos e ambiente reservado sustentam a leitura do escritório.", "reviews_title": "Casos conduzidos com responsabilidade e prova local.", "reviews_intro": "Depoimentos aparecem como histórico de atendimento, sem expor clientes.", "faq_title": "Antes de contratar a banca.", "faq_intro": "Respostas claras sobre honorários, prazos, documentos e estratégia inicial.", "location_title": "Atendimento jurídico em {city} com sigilo.", "location_intro": "Endereço, rota e contato entram com discrição e clareza editorial.", "lifestyle_kicker": "Tradição", "contact_kicker": "Consulta"},
        },
        {
            "id": "advogado-lex-meridian",
            "name": "Lex Meridian",
            "fallback_palette": {"primary": "#d6b86a", "secondary": "#0f1d3a", "bg_dark": "#0a1326", "bg_light": "#f4f1e7", "text_dark": "#0d172e"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Advocacia técnica e estratégica", "about_kicker": "Estratégia", "about_title": "Atuação jurídica com método, leitura precisa e postura firme.", "about_body": "{name} conduz causas com análise técnica, petição bem escrita e atendimento direto para quem procura representação em {city}.", "gallery_title": "Documento, jurisprudência e ambiente do escritório.", "gallery_intro": "Rigor, biblioteca, código civil e presença editorial criam contexto de decisão.", "reviews_title": "Confiança construída em caso a caso.", "reviews_intro": "A reputação aparece como sinal de técnica e acompanhamento.", "faq_title": "O cliente quer saber antes de assinar procuração.", "faq_intro": "FAQ enxuto sobre honorários, contrato, prazos e primeiras medidas.", "location_title": "Escritório de advocacia em {city}.", "location_intro": "O contato fica objetivo para consulta inicial sem ruído.", "lifestyle_kicker": "Método", "contact_kicker": "Procuração"},
        },
    ],
    "clinica": [
        {
            "id": "clinica-medical-trust",
            "name": "Medical Trust",
            "fallback_palette": {"primary": "#1f3a68", "secondary": "#ffffff", "bg_dark": "#0a182d", "bg_light": "#eef4fb", "text_dark": "#0b1c33"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Clínica com atendimento médico responsável", "about_kicker": "Diagnóstico", "about_title": "Consulta, exame e acompanhamento com leitura clínica clara.", "about_body": "{name} organiza agenda médica, especialidades e exames para pacientes que procuram atendimento estruturado em {city}.", "gallery_title": "Consultório, recepção e ambiente assistencial.", "gallery_intro": "Espaço limpo, equipe, sala de exame e circulação do paciente orientam a escolha.", "reviews_title": "Reputação construída em cada consulta.", "reviews_intro": "Avaliações entram como sinal de confiança clínica e bom atendimento.", "faq_title": "Perguntas antes de marcar a consulta.", "faq_intro": "Respostas sobre convênio, particular, exames e documentação.", "location_title": "Atendimento médico em {city} com rota clara.", "location_intro": "Endereço, telefone e WhatsApp aparecem sem ruído visual.", "lifestyle_kicker": "Cuidado clínico", "contact_kicker": "Agendar consulta"},
        },
        {
            "id": "clinica-care-plus",
            "name": "Care Plus",
            "fallback_palette": {"primary": "#2c5697", "secondary": "#dfe9f5", "bg_dark": "#f3f7fc", "bg_light": "#ffffff", "text_dark": "#102a4d"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Cuidado médico completo para a família", "about_kicker": "Acompanhamento", "about_title": "Clínica geral, especialidades e exames em um só lugar.", "about_body": "{name} integra consulta, retorno e exames preventivos para famílias e pacientes que querem continuidade de cuidado em {city}.", "gallery_title": "Atendimento humanizado, equipe e estrutura.", "gallery_intro": "Recepção, consultório, equipe multidisciplinar e sala de espera criam segurança para a primeira visita.", "reviews_title": "Pacientes que voltam e indicam a clínica.", "reviews_intro": "As avaliações reforçam acolhimento, agilidade e qualidade do atendimento.", "faq_title": "Dúvidas frequentes do primeiro atendimento.", "faq_intro": "Convênio, documentação, agendamento e retorno em respostas curtas.", "location_title": "Clínica próxima em {city} com fácil acesso.", "location_intro": "Endereço e WhatsApp médico ficam lado a lado para decisão rápida.", "lifestyle_kicker": "Família", "contact_kicker": "Marcar"},
        },
    ],
    "dentista": [
        {
            "id": "dentista-smile-care",
            "name": "Smile Care",
            "fallback_palette": {"primary": "#5ec8e3", "secondary": "#0f3b66", "bg_dark": "#062235", "bg_light": "#eefaff", "text_dark": "#0a2841"},
            "blocks": {"hero_variant": "video", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Odontologia com clareza e acolhimento", "about_kicker": "Sorriso", "about_title": "Limpeza, clareamento e tratamento odontológico com leitura leve.", "about_body": "{name} combina consulta, avaliação e plano odontológico para pacientes que querem um sorriso saudável em {city}.", "gallery_title": "Consultório, cadeira e detalhe do atendimento.", "gallery_intro": "Ambiente claro, equipamento moderno e equipe cuidadosa reduzem a dúvida antes da avaliação.", "reviews_title": "Pacientes que voltam para a próxima consulta.", "reviews_intro": "Avaliações reforçam atendimento sem dor, agilidade e resultado visível.", "faq_title": "Antes de marcar no dentista.", "faq_intro": "Respostas rápidas sobre convênio odontológico, particular e primeira avaliação.", "location_title": "Consultório odontológico em {city}.", "location_intro": "Endereço e contato direto para agendamento da avaliação.", "lifestyle_kicker": "Sorriso", "contact_kicker": "Avaliação"},
        },
        {
            "id": "dentista-clinical-white",
            "name": "Clinical White",
            "fallback_palette": {"primary": "#3fb6cf", "secondary": "#dff5fb", "bg_dark": "#ffffff", "bg_light": "#f6fcfd", "text_dark": "#103a4c"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Clínica odontológica clean e técnica", "about_kicker": "Procedimento", "about_title": "Implante, ortodontia e estética dental em ambiente clínico claro.", "about_body": "{name} apresenta especialidades odontológicas, plano de tratamento e retorno programado para pacientes em {city}.", "gallery_title": "Equipamento, sala clínica e resultado do tratamento.", "gallery_intro": "Consultório, tecnologia e plano de tratamento dão base para pedir orçamento.", "reviews_title": "Casos resolvidos com técnica e cuidado.", "reviews_intro": "Reputação local sustenta a escolha sem ruído de marketing.", "faq_title": "Perguntas sobre tratamento e orçamento.", "faq_intro": "Respostas claras sobre implantes, aparelho, clareamento e formas de pagamento.", "location_title": "Atendimento odontológico em {city}.", "location_intro": "O contato para orçamento e primeira consulta fica objetivo.", "lifestyle_kicker": "Estética dental", "contact_kicker": "Orçamento"},
        },
    ],
    "pet_shop": [
        {
            "id": "pet-shop-patudo",
            "name": "Patudo",
            "fallback_palette": {"primary": "#3f7a4a", "secondary": "#c89b3c", "bg_dark": "#1a2a1f", "bg_light": "#f7f1e1", "text_dark": "#1c2a1d"},
            "blocks": {"hero_variant": "center", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Pet shop com carinho e rotina", "about_kicker": "Cuidado animal", "about_title": "Banho, tosa e produtos pensados para o dia a dia do pet.", "about_body": "{name} cuida de cães e gatos com ambiente tranquilo, equipe paciente e atendimento próximo para tutores de {city}.", "gallery_title": "Banho, tosa e olhar carinhoso do pet.", "gallery_intro": "Pets atendidos, cuidado visível e ambiente do pet shop ajudam o tutor a decidir.", "reviews_title": "Tutores que voltam toda semana.", "reviews_intro": "Avaliações reforçam cuidado, paciência e carinho da equipe.", "faq_title": "Antes de levar o pet para tosa.", "faq_intro": "Respostas sobre agendamento, vacinas, porte do animal e produtos.", "location_title": "Pet shop em {city} com fácil chegada.", "location_intro": "Endereço e WhatsApp aparecem lado a lado para marcar o banho.", "lifestyle_kicker": "Carinho", "contact_kicker": "Agendar banho"},
        },
        {
            "id": "pet-shop-pet-care-pro",
            "name": "Pet Care Pro",
            "fallback_palette": {"primary": "#b95a3a", "secondary": "#5a8c4a", "bg_dark": "#2a1612", "bg_light": "#fbf0e3", "text_dark": "#2a1814"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Pet shop completo e profissional", "about_kicker": "Atendimento completo", "about_title": "Banho, tosa, veterinária e ração em um só lugar.", "about_body": "{name} oferece serviço completo para pets com agendamento, equipe treinada e cuidado veterinário de rotina em {city}.", "gallery_title": "Loja, consultório e rotina dos pets atendidos.", "gallery_intro": "Prateleira, equipe, pet sentado e ambiente limpo reforçam cuidado recorrente.", "reviews_title": "Confiança construída com cada tutor.", "reviews_intro": "Avaliações aparecem como prova de cuidado recorrente e atendimento sério.", "faq_title": "Dúvidas antes da primeira visita.", "faq_intro": "FAQ sobre agendamento, pacotes, vacinas e delivery de ração.", "location_title": "Pet shop profissional em {city}.", "location_intro": "Endereço, contato e WhatsApp prontos para a primeira visita.", "lifestyle_kicker": "Cuidado pro", "contact_kicker": "Reservar"},
        },
    ],
    "salao": [
        {
            "id": "salao-glow-studio",
            "name": "Glow Studio",
            "fallback_palette": {"primary": "#d8a3b5", "secondary": "#c9a14a", "bg_dark": "#2a1620", "bg_light": "#fdf1ee", "text_dark": "#2a1620"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Salão de beleza com brilho próprio", "about_kicker": "Brilho", "about_title": "Coloração, corte e finalização com leitura feminina e calorosa.", "about_body": "{name} atende clientes que buscam cor, corte e tratamento capilar com ambiente acolhedor em {city}.", "gallery_title": "Cabelo, espelho e detalhe do salão.", "gallery_intro": "Escova, mechas, espelho e clima de salão ajudam a imaginar o atendimento.", "reviews_title": "Clientes que indicam o salão para amigas.", "reviews_intro": "Avaliações reforçam resultado, atendimento e ambiente bonito.", "faq_title": "Antes de marcar no salão.", "faq_intro": "Respostas sobre coloração, tempo de atendimento, preço e agendamento.", "location_title": "Salão de beleza em {city} com fácil acesso.", "location_intro": "Endereço e WhatsApp prontos para fechar o próximo horário.", "lifestyle_kicker": "Brilho", "contact_kicker": "Reservar horário"},
        },
        {
            "id": "salao-mirror-room",
            "name": "Mirror Room",
            "fallback_palette": {"primary": "#e7c87a", "secondary": "#b86b86", "bg_dark": "#f7ecd6", "bg_light": "#ffffff", "text_dark": "#3a2418"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Salão com atmosfera de espelho e champagne", "about_kicker": "Ritual", "about_title": "Corte, escova e estética com experiência mais editorial.", "about_body": "{name} propõe um ritual de beleza com espelhos, luz quente e equipe que entende o estilo da cliente em {city}.", "gallery_title": "Espelho, luz quente e detalhe do ritual.", "gallery_intro": "Bancada, produto, cadeira e resultado do atendimento criam uma leitura mais sofisticada.", "reviews_title": "Experiência que vira indicação.", "reviews_intro": "Avaliações reforçam o clima, o atendimento e a durabilidade do resultado.", "faq_title": "Antes de reservar o ritual.", "faq_intro": "FAQ curto sobre agendamento, combos, manicure e pacotes.", "location_title": "Salão em {city} com atmosfera reservada.", "location_intro": "Endereço, contato e WhatsApp para marcar o próximo ritual.", "lifestyle_kicker": "Ritual", "contact_kicker": "Reservar"},
        },
    ],
    "estetica": [
        {
            "id": "estetica-clinic-ivory",
            "name": "Clinic Ivory",
            "fallback_palette": {"primary": "#8f6a4f", "secondary": "#4b2f25", "bg_dark": "#2a201c", "bg_light": "#f8f3ee", "text_dark": "#1e1714"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Estética com cuidado e técnica", "about_kicker": "Cuidado", "about_title": "Pele, conforto e autoestima com leitura clara.", "about_body": "{name} apresenta tratamentos, ambiente e WhatsApp para quem busca cuidado estético em {city}.", "gallery_title": "Textura, calma e detalhes do atendimento.", "gallery_intro": "As imagens reforçam pele, sala, toque e sensação de cuidado presencial.", "reviews_title": "Avaliações que ajudam a escolher com segurança.", "reviews_intro": "Reputação, atendimento e localização aparecem com leitura tranquila.", "faq_title": "Dúvidas antes da avaliação.", "faq_intro": "Perguntas diretas sobre agenda, procedimentos e WhatsApp.", "location_title": "Atendimento estético em {city}.", "location_intro": "Endereço e contato ficam visíveis para marcar a avaliação.", "lifestyle_kicker": "Ambiente", "contact_kicker": "Agendamento"},
        },
        {
            "id": "estetica-chrome-spa",
            "name": "Chrome Spa",
            "fallback_palette": {"primary": "#0f8f84", "secondary": "#1f4f52", "bg_dark": "#082f34", "bg_light": "#edf8f6", "text_dark": "#0b2f31"},
            "blocks": {"hero_variant": "video", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Spa urbano", "about_kicker": "Ritual", "about_title": "Um espaço de beleza com ritmo calmo e presença moderna.", "about_body": "{name} combina tratamentos, acolhimento e acesso rápido pelo WhatsApp em {city}.", "gallery_title": "Luz, pele e rotina de autocuidado.", "gallery_intro": "Atmosfera limpa, detalhes de tratamento e contexto humano deixam o agendamento mais natural.", "reviews_title": "Confiança para marcar o primeiro horário.", "reviews_intro": "Avaliações aparecem junto de serviços e contato para facilitar a escolha.", "faq_title": "O que perguntar antes de agendar.", "faq_intro": "FAQ curto sobre avaliação, atendimento e preparo.", "location_title": "Chegue ao cuidado em {city}.", "location_intro": "Rota, telefone e WhatsApp entram no mesmo bloco.", "lifestyle_kicker": "Spa", "contact_kicker": "Consulta"},
        },
        {
            "id": "estetica-rose-clay",
            "name": "Rose Clay",
            "fallback_palette": {"primary": "#b85c4d", "secondary": "#6d2f38", "bg_dark": "#2d1418", "bg_light": "#fff2ee", "text_dark": "#2a1416"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Beleza com presença", "about_kicker": "Transformação", "about_title": "Tratamentos com acolhimento, detalhe e confiança.", "about_body": "{name} valoriza uma jornada estética confortável, com contato simples para quem está em {city}.", "gallery_title": "Corpo, pele e ambiente em composição quente.", "gallery_intro": "A sequência visual aproxima cuidado, textura e resultado esperado sem exagero.", "reviews_title": "Quem já conhece ajuda a decidir.", "reviews_intro": "Avaliações e serviços entram com tom humano e direto.", "faq_title": "Antes de chamar no WhatsApp.", "faq_intro": "Respostas simples para agenda, avaliação e atendimento.", "location_title": "Endereço e beleza no mesmo caminho.", "location_intro": "Tudo para marcar sem perder tempo.", "lifestyle_kicker": "Toque", "contact_kicker": "Marcar"},
        },
        {
            "id": "estetica-noir-gold",
            "name": "Noir Gold",
            "fallback_palette": {"primary": "#d6ad60", "secondary": "#18120d", "bg_dark": "#090705", "bg_light": "#f4eee2", "text_dark": "#1c150f"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Estética premium", "about_kicker": "Experiência", "about_title": "Cuidado estético com atmosfera mais exclusiva.", "about_body": "{name} apresenta ambiente, serviços e agendamento em uma leitura mais elegante para {city}.", "gallery_title": "Luz baixa, textura e acabamento de clínica premium.", "gallery_intro": "Detalhe, conforto e sensação de atendimento reservado reforçam a decisão.", "reviews_title": "Reputação com leitura premium.", "reviews_intro": "Avaliações, cidade e contato sustentam a decisão sem poluir a página.", "faq_title": "Perguntas antes de reservar.", "faq_intro": "Serviços, localização e WhatsApp em linguagem objetiva.", "location_title": "Reserve em {city} com acesso claro.", "location_intro": "Contato e endereço fecham a jornada sem atrito.", "lifestyle_kicker": "Premium", "contact_kicker": "Reserva"},
        },
    ],
    "default": [
        {
            "id": "default-professional-dark",
            "name": "Professional Dark",
            "fallback_palette": {"primary": "#4f46e5", "secondary": "#1f2937", "bg_dark": "#0b1220", "bg_light": "#f8fafc", "text_dark": "#0f172a"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
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

    "restaurante": [
        {
            "id": "restaurante-prato-certo",
            "name": "Prato Certo",
            "fallback_palette": {"primary": "#7a1a2b", "secondary": "#c9a14a", "bg_dark": "#2a1014", "bg_light": "#f7efe2", "text_dark": "#2a1014"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Casa de comida com identidade local" , "about_kicker": "Receita" , "about_title": "Prato bem feito, ambiente acolhedor e decisão sem complicação." , "about_body": "{name} organiza menu, carta e atendimento para uma refeição bem resolvida em {city}." , "gallery_title": "Prato, mesa e atmosfera de casa cheia." , "gallery_intro": "As imagens reforçam comida, serviço e sensação de estar bem recebido." , "reviews_title": "Avaliações que aproximam o cliente da casa." , "reviews_intro": "Reputação, prato e cidade sustentam a escolha de visitar." , "faq_title": "Perguntas antes de reservar a mesa." , "faq_intro": "Respostas curtas sobre cardápio, reserva, delivery e horários." , "location_title": "Visite a casa em {city} com acesso claro." , "location_intro": "Endereço, cardápio e WhatsApp aparecem sem poluição visual." , "lifestyle_kicker": "Mesa" , "contact_kicker": "Reserva" },
        },
        {
            "id": "restaurante-forno-livre",
            "name": "Forno Livre",
            "fallback_palette": {"primary": "#4f6b2a", "secondary": "#c9a14a", "bg_dark": "#1a2010", "bg_light": "#f4ecd6", "text_dark": "#1a2010"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stacked_cards", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Forno aberto, massa e sabor de verdade" , "about_kicker": "Forno" , "about_title": "Padaria e pizzaria com forno visível e leitura mais humana." , "about_body": "{name} apresenta fornada, atendimento e cardápio para quem busca comida feita com calma em {city}." , "gallery_title": "Massa, fermento e detalhe do forno." , "gallery_intro": "A galeria aproxima o cliente do processo e do sabor." , "reviews_title": "Clientes que voltam pelo sabor e pela confiança." , "reviews_intro": "Depoimentos reforçam regularidade e cuidado com a receita." , "faq_title": "Antes de pedir ou retirar no balcão." , "faq_intro": "FAQ direto sobre entrega, reserva e horários de fornada." , "location_title": "Encontre o forno em {city}." , "location_intro": "Endereço, WhatsApp e cardápio fecham a página com calor e clareza." , "lifestyle_kicker": "Receita" , "contact_kicker": "Pedido" },
        },
    ],
    "oficina": [
        {
            "id": "oficina-torque-box",
            "name": "Torque Box",
            "fallback_palette": {"primary": "#e10600", "secondary": "#1a1a1a", "bg_dark": "#0a0a0a", "bg_light": "#f5f5f5", "text_dark": "#111111"},
            "blocks": {"hero_variant": "split", "services_variant": "stats_then_cards", "reviews_variant": "score_wall", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Oficina mecânica de verdade" , "about_kicker": "Mecânica" , "about_title": "Diagnóstico, mão de obra e peça certa para rodar em {city}." , "about_body": "{name} organiza revisão, reparo e atendimento com leitura direta, orçamento claro e serviço executado." , "gallery_title": "Oficina em ação, ferramenta na mão e carro resolvido." , "gallery_intro": "Cada imagem mostra bancada, elevador, peça e o ritmo de uma oficina que entrega." , "reviews_title": "Clientes que voltaram e indicaram." , "reviews_intro": "Avaliações locais reforçam confiança antes de deixar o carro na oficina." , "faq_title": "Perguntas antes de levar o carro." , "faq_intro": "Respostas curtas sobre orçamento, prazo, peça e garantia." , "location_title": "Traga o carro na oficina em {city}." , "location_intro": "Endereço, WhatsApp e rota aparecem juntos para facilitar a chegada." , "lifestyle_kicker": "Torque" , "contact_kicker": "Diagnóstico" },
        },
        {
            "id": "oficina-garage-iron",
            "name": "Garage Iron",
            "fallback_palette": {"primary": "#f5c518", "secondary": "#2b2b2b", "bg_dark": "#121212", "bg_light": "#efece4", "text_dark": "#1a1a1a"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stacked_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Oficina com estrutura industrial" , "about_kicker": "Estrutura" , "about_title": "Bancada, elevador e equipe para serviço pesado em {city}." , "about_body": "{name} mostra oficina, equipe e atendimento com linguagem direta, sem prometer o que não cumpre." , "gallery_title": "Aço, elevador, motor e ferramental pesado." , "gallery_intro": "Espaço, equipamento e rotina de oficina séria reduzem o risco antes do orçamento." , "reviews_title": "Reputação construída em serviço bem feito." , "reviews_intro": "Depoimentos e nota local ajudam a decidir com menos risco." , "faq_title": "O que perguntar antes de deixar o carro." , "faq_intro": "FAQ direto sobre diagnóstico, prazo, pagamento e garantia." , "location_title": "Encontre a oficina em {city}." , "location_intro": "Mapa, contato e WhatsApp fecham a página com chamada clara." , "lifestyle_kicker": "Garagem" , "contact_kicker": "Orçamento" },
        },
    ],
    "energia_solar": [
        {
            "id": "energia-solar-sun-pure",
            "name": "Sun Pure",
            "fallback_palette": {"primary": "#7cb342", "secondary": "#1565c0", "bg_dark": "#f4f9ec", "bg_light": "#ffffff", "text_dark": "#1a2e1a"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Energia solar para residências e empresas" , "about_kicker": "Economia" , "about_title": "Energia limpa, conta menor e retorno previsível em {city}." , "about_body": "{name} dimensiona o sistema solar, cuida da instalação e acompanha a geração com leitura clara para o cliente." , "gallery_title": "Telhado, painel e luz natural como matéria-prima." , "gallery_intro": "Imagens de projetos instalados reforçam a sensação de economia e cuidado técnico." , "reviews_title": "Clientes que viram a conta cair." , "reviews_intro": "Avaliações e cases locais sustentam a decisão de investir em solar." , "faq_title": "Perguntas antes de instalar energia solar." , "faq_intro": "Respostas curtas sobre payback, financiamento, homologação e garantia." , "location_title": "Atendimento solar em {city}." , "location_intro": "Simulação, contato e endereço aparecem no mesmo bloco para ação imediata." , "lifestyle_kicker": "Sol" , "contact_kicker": "Simular" },
        },
        {
            "id": "energia-solar-tech-grid",
            "name": "Tech Grid",
            "fallback_palette": {"primary": "#1565c0", "secondary": "#f5c518", "bg_dark": "#0a1729", "bg_light": "#eef4fb", "text_dark": "#0a1729"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "editorial_case", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Energia solar com leitura técnica" , "about_kicker": "Tecnologia" , "about_title": "Projeto, instalação e monitoramento para gerar mais em {city}." , "about_body": "{name} entra com engenharia, dimensionamento preciso e monitoramento de geração para quem quer resultado mensurável." , "gallery_title": "Painéis, inversores e dados de geração em destaque." , "gallery_intro": "A galeria privilegia projeto, tecnologia instalada e prova de performance." , "reviews_title": "Cases e números de quem economiza todo mês." , "reviews_intro": "Resultados e depoimentos reforçam credibilidade técnica da empresa." , "faq_title": "Dúvidas técnicas antes de fechar projeto." , "faq_intro": "FAQ objetivo sobre kWh, payback, homologação e vida útil do sistema." , "location_title": "Projeto solar em {city} com equipe técnica." , "location_intro": "O contato fecha com simulação, WhatsApp técnico e rota para visita." , "lifestyle_kicker": "Grid" , "contact_kicker": "Projeto" },
        },
    ],
    "imobiliaria": [
        {
            "id": "imobiliaria-key-modern",
            "name": "Key Modern",
            "fallback_palette": {"primary": "#c9a14a", "secondary": "#5a3a1a", "bg_dark": "#f7f1e3", "bg_light": "#ffffff", "text_dark": "#2a1f10"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Imóveis selecionados com curadoria" , "about_kicker": "Curadoria" , "about_title": "Apartamentos e casas bem localizados para morar ou investir em {city}." , "about_body": "{name} apresenta imóveis com visita organizada, negociação transparente e acompanhamento até a entrega das chaves." , "gallery_title": "Ambientes, fachada e detalhe de acabamento." , "gallery_intro": "As imagens reforçam planta, iluminação e o cuidado com cada imóvel da carteira." , "reviews_title": "Compradores e locatários que fecharam bem." , "reviews_intro": "Cases de clientes sustentam a confiança antes de agendar visita." , "faq_title": "Perguntas antes de agendar visita." , "faq_intro": "Respostas sobre documentação, financiamento, visita e proposta." , "location_title": "Imóveis em {city} com atendimento próximo." , "location_intro": "Endereço, WhatsApp e agenda de visitas aparecem no mesmo bloco." , "lifestyle_kicker": "Chave" , "contact_kicker": "Visita" },
        },
        {
            "id": "imobiliaria-loft-elegance",
            "name": "Loft Elegance",
            "fallback_palette": {"primary": "#b8893a", "secondary": "#3d2817", "bg_dark": "#1d140a", "bg_light": "#f0e6d2", "text_dark": "#1d140a"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stats_then_cards", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Imóveis premium e atendimento reservado" , "about_kicker": "Excelência" , "about_title": "Imóveis de alto padrão com curadoria e discrição em {city}." , "about_body": "{name} atende clientes que buscam exclusividade, com portfólio selecionado, visita privada e negociação sob medida." , "gallery_title": "Arquitetura, luz e acabamento de alto padrão." , "gallery_intro": "As imagens valorizam planta, metragem, design e o silêncio de um imóvel bem escolhido." , "reviews_title": "Clientes que fecharam negócios exclusivos." , "reviews_intro": "Reputação construída em discrição, presença e resultado de longo prazo." , "faq_title": "Perguntas antes de uma visita privada." , "faq_intro": "FAQ sobre agenda reservada, documentação, proposta e sigilo." , "location_title": "Imóveis premium em {city}." , "location_intro": "Atendimento fecha com contato direto, agenda reservada e rota sob medida." , "lifestyle_kicker": "Loft" , "contact_kicker": "Reservar" },
        },
    ],
    "barbearia": [
        {
            "id": "barbearia-heritage-reserve",
            "name": "Heritage Reserve",
            "fallback_palette": {"primary": "#c9a96a", "secondary": "#3d2a18", "bg_dark": "#0d0b0a", "bg_light": "#f4ede3", "text_dark": "#1b130f"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Barbearia clássica" , "about_kicker": "Ritual" , "about_title": "Corte, barba e acabamento com leitura clássica em {city}." , "about_body": "{name} valoriza detalhe, atendimento e experiência presencial para quem procura barbearia de verdade." , "gallery_title": "Couro, aço, espelho e ritual." , "gallery_intro": "Ambiente, serviço e detalhes do ritual clássico aparecem com leitura direta." , "reviews_title": "Clientes que percebem detalhe e atendimento." , "reviews_intro": "Avaliações reforçam consistência, acabamento e recorrência." , "faq_title": "Perguntas antes de reservar o horário." , "faq_intro": "Respostas curtas sobre agenda, serviços e localização." , "location_title": "Visite a barbearia em {city}." , "location_intro": "Reserva, endereço e contato aparecem juntos." , "lifestyle_kicker": "Atmosfera" , "contact_kicker": "Reserva" },
        },
        {
            "id": "barbearia-studio-mono",
            "name": "Studio Mono",
            "fallback_palette": {"primary": "#f1f1f1", "secondary": "#555555", "bg_dark": "#090909", "bg_light": "#efefef", "text_dark": "#151515"},
            "blocks": {"hero_variant": "center", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte com direção contemporânea" , "about_kicker": "Design" , "about_title": "Identidade sóbria, gráfica e precisa em {city}." , "about_body": "{name} entra numa linha mais contemporânea, com menos ornamento e mais contraste limpo." , "gallery_title": "Monocromia, recorte e presença." , "gallery_intro": "As imagens privilegiam sombra, forma e acabamento." , "reviews_title": "Confiança tratada com voz editorial." , "reviews_intro": "Menos excesso, mais recorte e clareza." , "faq_title": "Tudo o que importa antes de reservar." , "faq_intro": "Perguntas curtas para acelerar a escolha." , "location_title": "Agende e chegue sem complicação." , "location_intro": "O WhatsApp fica direto para reserva." , "lifestyle_kicker": "Estilo" , "contact_kicker": "Reserva" },
        },
        {
            "id": "barbearia-copper-smoke",
            "name": "Copper Smoke",
            "fallback_palette": {"primary": "#b96d3c", "secondary": "#4e281b", "bg_dark": "#160f0d", "bg_light": "#f6ece6", "text_dark": "#231511"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte e barba com atmosfera noturna" , "about_kicker": "Presença" , "about_title": "Uma barbearia quente, escura e cinematográfica em {city}." , "about_body": "{name} usa contraste de cobre e luz baixa para enfatizar ritual, noite e personalidade." , "gallery_title": "Luz baixa, metal quente e acabamento forte." , "gallery_intro": "As imagens aproximam atmosfera, acabamento e proximidade no atendimento." , "reviews_title": "Sinais locais em ritmo mais vivo." , "reviews_intro": "Avaliações podem ganhar movimento sem perder clareza." , "faq_title": "Perguntas para quem quer reservar hoje." , "faq_intro": "Menos texto e mais ação." , "location_title": "Localização e contato no mesmo pulso." , "location_intro": "O fechamento conduz para reserva direta." , "lifestyle_kicker": "Noite" , "contact_kicker": "Agende" },
        },
        {
            "id": "barbearia-midnight-club",
            "name": "Midnight Club",
            "fallback_palette": {"primary": "#8b7cf7", "secondary": "#1d153d", "bg_dark": "#080712", "bg_light": "#f2efff", "text_dark": "#16112e"},
            "blocks": {"hero_variant": "video", "services_variant": "stacked_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Barbearia com assinatura autoral" , "about_kicker": "Assinatura" , "about_title": "Direção ousada para marcas que querem parecer únicas." , "about_body": "{name} assume uma linha mais autoral, com luz fria, composição noturna e CTA de reserva como foco central." , "gallery_title": "Uma estética de clube privado." , "gallery_intro": "Presença menos genérica, mais memorável e pronta para reserva." , "reviews_title": "Reputação local com recorte de marca." , "reviews_intro": "A confiança vem sem perder identidade visual." , "faq_title": "O que o cliente quer saber antes do corte." , "faq_intro": "Objetivo, curto e acionável." , "location_title": "Fale pelo WhatsApp." , "location_intro": "A jornada fecha em reserva direta." , "lifestyle_kicker": "Assinatura" , "contact_kicker": "Horário" },
        },
    ],
}


# DEPRECATED (Sprint 12.x): _FAMILY_COPY_DEFAULTS existe apenas como fallback
# para labels de navegacao (nav_about, nav_services, etc) que ainda nao foram
# migradas para nicho_registry. Fonte unica de verdade:
# backend/config/nicho_registry.py::NichoConfig.copy_defaults
#
# Codigo novo deve usar get_family_copy_defaults() abaixo (que consulta
# o registry primeiro e cai aqui apenas se nao houver).
_FAMILY_COPY_DEFAULTS: dict[str, dict[str, str]] = {
    "academia": {
        "nav_about": "Estrutura",
        "nav_services": "Modalidades",
        "nav_gallery": "Ambiente",
        "nav_reviews": "Resultados",
        "nav_faq": "Dúvidas",
        "nav_location": "Local",
        "nav_lifestyle": "Ritmo",
        "nav_contact": "Matrícula",
        "services_kicker": "Treino",
        "gallery_kicker": "Ambiente",
        "reviews_kicker": "Reputação",
        "faq_kicker": "Dúvidas reais",
        "location_kicker": "Presença local",
        "location_cta_kicker": "Acesso",
        "location_cta_primary": "Falar no WhatsApp",
        "location_cta_secondary": "Ver contato",
        "modal_kicker": "Contato",
        "about_card_1_title": "Estrutura pronta",
        "about_card_1_text": "{name} aparece com ambiente, cidade e proposta alinhados para quem quer treinar em {city}.",
        "about_card_2_title": "Modalidades visíveis",
        "about_card_2_text": "Musculação, funcional ou aula experimental entram com leitura objetiva e sem promessa vazia.",
        "about_card_3_title": "Decisão rápida",
        "about_card_3_text": "Contato, prova local e CTA final trabalham para reduzir atrito na entrada.",
        "about_city_label": "Cidade",
        "about_aside_body": "Leitura direta para quem compara estrutura, localização e o melhor momento para começar.",
        "services_city_body": "Estrutura, ritmo e decisão aparecem organizados para facilitar a matrícula.",
        "contact_card_label": "WhatsApp",
        "contact_primary_label": "Falar no WhatsApp",
        "contact_secondary_label": "Abrir contato",
        "footer_contact_label": "Contato",
        "footer_location_label": "Local",
        "footer_privacy_note": "Dados factuais e privacidade preservada.",
        "contact_sub": "Envie uma mensagem para confirmar horários disponíveis, visita e primeiro treino.",
    },
    "nutricionista": {
        "nav_about": "Método",
        "nav_services": "Consulta",
        "nav_gallery": "Consultório",
        "nav_reviews": "Pacientes",
        "nav_faq": "Perguntas",
        "nav_location": "Localização",
        "nav_lifestyle": "Rotina",
        "nav_contact": "Agenda",
        "services_kicker": "Acompanhamento",
        "gallery_kicker": "Contexto",
        "reviews_kicker": "Confiança",
        "faq_kicker": "Perguntas práticas",
        "location_kicker": "Consultório",
        "location_cta_kicker": "Agenda",
        "location_cta_primary": "Agendar WhatsApp",
        "location_cta_secondary": "Ver localização",
        "modal_kicker": "Consulta",
        "about_card_1_title": "Escuta clínica",
        "about_card_1_text": "{name} aparece com consulta, cidade e contexto organizados para uma decisão mais tranquila em {city}.",
        "about_card_2_title": "Plano aplicável",
        "about_card_2_text": "A proposta valoriza acompanhamento, rotina e clareza sobre o que acontece antes e depois da consulta.",
        "about_card_3_title": "Contato claro",
        "about_card_3_text": "WhatsApp, endereço e CTA final fecham a jornada com legibilidade e confiança.",
        "about_city_label": "Atendimento",
        "about_aside_body": "Uma composição mais serena para quem precisa entender método, consultório e como marcar sem ansiedade.",
        "services_city_body": "Cidade, contato e método aparecem juntos para dar clareza antes da primeira consulta.",
        "contact_card_label": "Canal de agendamento",
        "contact_primary_label": "Agendar WhatsApp",
        "contact_secondary_label": "Abrir contato",
        "footer_contact_label": "Contato",
        "footer_location_label": "Consultório",
        "footer_privacy_note": "Privacidade preservada no atendimento.",
        "contact_sub": "Envie uma mensagem para confirmar agenda, modalidade de consulta e retorno.",
    },
    "barbearia": {
        "nav_about": "Ritual",
        "nav_services": "Serviços",
        "nav_gallery": "Atmosfera",
        "nav_reviews": "Clientes",
        "nav_faq": "Reserva",
        "nav_location": "Endereço",
        "nav_lifestyle": "Estilo",
        "nav_contact": "Agendar",
        "services_kicker": "Serviços",
        "gallery_kicker": "Atmosfera",
        "reviews_kicker": "Clientes",
        "faq_kicker": "Antes da reserva",
        "location_kicker": "Endereço",
        "location_cta_kicker": "Reserva",
        "location_cta_primary": "Reservar pelo WhatsApp",
        "location_cta_secondary": "Ver rota",
        "modal_kicker": "Reserva",
        "about_card_1_title": "Corte com assinatura",
        "about_card_1_text": "{name} apresenta endereço, estilo e leitura clara para quem procura corte e barba em {city}.",
        "about_card_2_title": "Ritual bem definido",
        "about_card_2_text": "Serviços, acabamento e atmosfera entram como parte da experiência, não como lista genérica.",
        "about_card_3_title": "Reserva direta",
        "about_card_3_text": "Contato, localização e CTA final foram montados para fechar horário sem rodeio.",
        "about_city_label": "Base local",
        "about_aside_body": "Reserva, localização e identidade forte conduzem a visita para horário marcado.",
        "services_city_body": "Serviços, endereço e reserva ficam organizados para decisão rápida.",
        "contact_card_label": "Canal de reserva",
        "contact_primary_label": "Reservar no WhatsApp",
        "contact_secondary_label": "Abrir contato",
        "footer_contact_label": "Reserva",
        "footer_location_label": "Endereço",
        "footer_privacy_note": "Privacidade preservada no atendimento.",
        "contact_sub": "Reserve pelo WhatsApp e confirme horário, serviço e endereço antes de sair.",
    },
    "estetica": {
        "nav_about": "Cuidado",
        "nav_services": "Tratamentos",
        "nav_gallery": "Ambiente",
        "nav_reviews": "Avaliações",
        "nav_faq": "Perguntas",
        "nav_location": "Local",
        "nav_lifestyle": "Experiência",
        "nav_contact": "Agendar",
        "services_kicker": "Tratamentos",
        "gallery_kicker": "Ambiente",
        "reviews_kicker": "Reputação",
        "faq_kicker": "Antes da avaliação",
        "location_kicker": "Local",
        "location_cta_kicker": "Agenda",
        "location_cta_primary": "Agendar WhatsApp",
        "location_cta_secondary": "Ver contato",
        "modal_kicker": "Agendamento",
        "about_card_1_title": "Avaliação estética",
        "about_card_1_text": "{name} apresenta tratamentos, cidade e contato para quem busca cuidado estético em {city}.",
        "about_card_2_title": "Cuidado com conforto",
        "about_card_2_text": "Serviços, ambiente e preparo aparecem com leitura simples antes da avaliação.",
        "about_card_3_title": "Agendamento claro",
        "about_card_3_text": "WhatsApp, endereço e próximos passos ajudam a marcar sem caminho confuso.",
        "about_city_label": "Atendimento",
        "about_aside_body": "A página reúne tratamentos, localização e WhatsApp para facilitar a primeira conversa.",
        "services_city_body": "Tratamentos, avaliação e agendamento aparecem com leitura clara.",
        "contact_card_label": "Canal de agendamento",
        "contact_primary_label": "Agendar WhatsApp",
        "contact_secondary_label": "Abrir contato",
        "footer_contact_label": "Contato",
        "footer_location_label": "Local",
        "footer_privacy_note": "Privacidade preservada no atendimento.",
        "contact_sub": "Envie uma mensagem para confirmar avaliação, procedimento e melhor horário.",
    },
    "default": {
        "nav_about": "Sobre",
        "nav_services": "Serviços",
        "nav_gallery": "Visual",
        "nav_reviews": "Avaliações",
        "nav_faq": "Perguntas",
        "nav_location": "Local",
        "nav_lifestyle": "Presença",
        "nav_contact": "Contato",
        "services_kicker": "Serviços",
        "gallery_kicker": "Visual",
        "reviews_kicker": "Reputação",
        "faq_kicker": "Perguntas",
        "location_kicker": "Local",
        "location_cta_kicker": "Contato",
        "location_cta_primary": "Falar no WhatsApp",
        "location_cta_secondary": "Ver contato",
        "modal_kicker": "Contato",
        "about_card_1_title": "Presença local",
        "about_card_1_text": "{name} aparece com cidade, contato e contexto alinhados para quem está em {city}.",
        "about_card_2_title": "Serviço principal",
        "about_card_2_text": "As frentes de atendimento ficam organizadas para leitura rápida e decisão sem complicação.",
        "about_card_3_title": "Marca em contexto",
        "about_card_3_text": "Ambiente, imagem e composição sustentam o estilo do negócio com leitura clara.",
        "about_city_label": "Cidade",
        "about_aside_body": "Contato direto e informação clara para quem está decidindo agora.",
        "services_city_body": "Estrutura organizada para leitura rápida e decisão mais clara.",
        "contact_card_label": "WhatsApp",
        "contact_primary_label": "Falar no WhatsApp",
        "contact_secondary_label": "Abrir contato",
        "footer_contact_label": "Contato",
        "footer_location_label": "Local",
        "footer_privacy_note": "Dados factuais e privacidade preservada.",
        "contact_sub": "Envie uma mensagem para confirmar atendimento, endereço e melhor horário.",
    },
}


_LANE_REMIXES: dict[str, list[dict[str, Any]]] = {
    "academia": [
        {
            "id": "academia-competition-redline",
            "name": "Competition Redline",
            "fallback_palette": {"primary": "#ff1010", "secondary": "#f5f5f5", "bg_dark": "#050505", "bg_light": "#f3f3f3", "text_dark": "#111111"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stats_then_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Treino competitivo", "about_kicker": "Performance", "about_title": "Energia de prova, rotina forte e presença sem promessa vazia.", "about_body": "{name} ganha uma direção mais atlética para quem procura intensidade, horários claros e decisão rápida em {city}.", "gallery_title": "Carga, suor e composição de impacto.", "gallery_intro": "As imagens entram com contraste alto, marca forte e sensação de treino em andamento.", "reviews_title": "Reputação para quem compara estrutura e ritmo.", "reviews_intro": "Score, cidade e contato aparecem com linguagem direta.", "faq_title": "Antes de puxar o primeiro treino.", "faq_intro": "Perguntas curtas sobre matrícula, aula experimental e modalidade.", "location_title": "Rota rápida para começar em {city}.", "location_intro": "Contato, endereço e CTA fecham a página com urgência controlada.", "lifestyle_kicker": "Competição", "contact_kicker": "Partida"},
        },
        {
            "id": "academia-recovery-lab",
            "name": "Recovery Lab",
            "fallback_palette": {"primary": "#66e3c4", "secondary": "#264653", "bg_dark": "#eef8f5", "bg_light": "#ffffff", "text_dark": "#17312d"},
            "blocks": {"hero_variant": "split", "services_variant": "split_editorial", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Treino com técnica e cuidado", "about_kicker": "Equilíbrio", "about_title": "Força, mobilidade e constância com leitura mais limpa.", "about_body": "{name} apresenta treino orientado, rotina clara e ambiente acolhedor para quem quer evoluir com conforto.", "gallery_title": "Movimento, cuidado e espaço respirado.", "gallery_intro": "A seção reúne orientação, equipamento e rotina sustentável.", "reviews_title": "Confiança para quem está começando ou voltando.", "reviews_intro": "Avaliações ajudam a entender a experiência de outros alunos.", "faq_title": "Dúvidas antes de encaixar o treino na rotina.", "faq_intro": "Sem jargão e sem pressão artificial.", "location_title": "Comece em {city} com informação clara.", "location_intro": "O contato aparece como agendamento simples.", "lifestyle_kicker": "Cuidado", "contact_kicker": "Começo"},
        },
        {
            "id": "academia-urban-box",
            "name": "Urban Box",
            "fallback_palette": {"primary": "#facc15", "secondary": "#222222", "bg_dark": "#0b0b0b", "bg_light": "#fff7cc", "text_dark": "#181818"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stacked_cards", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Treino urbano", "about_kicker": "Ritmo", "about_title": "Uma academia com linguagem de rua, foco e endereço claro.", "about_body": "{name} destaca rotina, modalidades e decisão sem enrolação.", "gallery_title": "Blocos fortes, equipamento e cidade.", "gallery_intro": "A página ganha ritmo mais direto e menos aparência de template.", "reviews_title": "Sinais locais que sustentam a escolha.", "reviews_intro": "A reputação aparece junto da decisão de contato.", "faq_title": "O que decidir antes de entrar.", "faq_intro": "Perguntas rápidas para levar ao WhatsApp.", "location_title": "Chegue ao treino em {city}.", "location_intro": "A rota de ação é curta: ver, entender, falar.", "lifestyle_kicker": "Rua", "contact_kicker": "Entrada"},
        },
        {
            "id": "academia-endurance-blue",
            "name": "Endurance Blue",
            "fallback_palette": {"primary": "#38bdf8", "secondary": "#0f172a", "bg_dark": "#07111f", "bg_light": "#eaf6ff", "text_dark": "#0f172a"},
            "blocks": {"hero_variant": "video", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Treino de longo prazo", "about_kicker": "Evolução", "about_title": "Constância, resistência e experiência mais premium.", "about_body": "{name} apresenta ritmo mais cinematográfico para quem procura estrutura, acompanhamento e progresso em {city}.", "gallery_title": "Uma sequência visual de evolução.", "gallery_intro": "Percurso, rotina e progresso aparecem como continuidade de treino.", "reviews_title": "Credibilidade para continuar voltando.", "reviews_intro": "Depoimentos e sinais locais reforçam permanência.", "faq_title": "Antes de manter a rotina.", "faq_intro": "Perguntas para entender encaixe, horário e contato.", "location_title": "Endereço com rota limpa.", "location_intro": "O fechamento deixa o WhatsApp claro.", "lifestyle_kicker": "Evolução", "contact_kicker": "Ritmo"},
        },
    ],
    "nutricionista": [
        {
            "id": "nutri-hormone-care",
            "name": "Hormone Care",
            "fallback_palette": {"primary": "#9f7aea", "secondary": "#2f2546", "bg_dark": "#f7f2ff", "bg_light": "#ffffff", "text_dark": "#251f33"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Nutrição com escuta e precisão", "about_kicker": "Acolhimento", "about_title": "Cuidado nutricional com leitura delicada e estratégica.", "about_body": "{name} acolhe consultas que pedem escuta, rotina e acompanhamento próximo.", "gallery_title": "Detalhes leves, consultório e confiança.", "gallery_intro": "A página evita excesso clínico e melhora a sensação de cuidado.", "reviews_title": "Pacientes, confiança e evolução possível.", "reviews_intro": "Avaliações aparecem sem tom agressivo.", "faq_title": "Perguntas antes da primeira consulta.", "faq_intro": "Tudo com linguagem clara e sem pressão.", "location_title": "Atendimento em {city} com acesso simples.", "location_intro": "Endereço e contato aparecem com calma e legibilidade.", "lifestyle_kicker": "Cuidado", "contact_kicker": "Consulta"},
        },
        {
            "id": "nutri-family-table",
            "name": "Family Table",
            "fallback_palette": {"primary": "#d49a3a", "secondary": "#3e5f45", "bg_dark": "#fff8ee", "bg_light": "#ffffff", "text_dark": "#2a251b"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Alimentação possível na vida real", "about_kicker": "Rotina", "about_title": "Estratégia nutricional que cabe na mesa e na semana.", "about_body": "{name} apresenta organização alimentar sem radicalismo.", "gallery_title": "Comida, rotina e orientação clara.", "gallery_intro": "A página troca estética fria por proximidade e clareza.", "reviews_title": "Confiança de quem sentiu o processo acontecer.", "reviews_intro": "Depoimentos aparecem com tom de continuidade.", "faq_title": "Antes de mudar a rotina alimentar.", "faq_intro": "Perguntas sobre consulta, retorno e acompanhamento.", "location_title": "Agende em {city} sem complicar.", "location_intro": "Contato e localização ficam no mesmo raciocínio.", "lifestyle_kicker": "Mesa", "contact_kicker": "Agenda"},
        },
        {
            "id": "nutri-sports-lab",
            "name": "Sports Lab",
            "fallback_palette": {"primary": "#b7ff3c", "secondary": "#111827", "bg_dark": "#101318", "bg_light": "#f3ffe1", "text_dark": "#111827"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stats_then_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Nutrição esportiva com método", "about_kicker": "Performance", "about_title": "Plano alimentar para quem mede evolução, treino e rotina.", "about_body": "{name} assume uma direção mais esportiva quando o lead pede intensidade, objetivo e acompanhamento técnico.", "gallery_title": "Energia, treino e estratégia visual.", "gallery_intro": "A composição conversa com rotina ativa e decisão rápida.", "reviews_title": "Prova para quem compara performance e confiança.", "reviews_intro": "Score e depoimentos entram com mais impacto.", "faq_title": "Antes de ajustar treino e alimentação.", "faq_intro": "FAQ curto, prático e direto ao WhatsApp.", "location_title": "Atendimento esportivo em {city}.", "location_intro": "A rota para marcar consulta fica evidente.", "lifestyle_kicker": "Performance", "contact_kicker": "Plano"},
        },
        {
            "id": "nutri-premium-clinic",
            "name": "Premium Clinic",
            "fallback_palette": {"primary": "#d6b86a", "secondary": "#102a43", "bg_dark": "#0d1f31", "bg_light": "#f7f2e7", "text_dark": "#102033"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stacked_cards", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Atendimento nutricional premium", "about_kicker": "Autoridade", "about_title": "Consultório com presença elegante e decisão segura.", "about_body": "{name} reforça autoridade, privacidade e atendimento bem conduzido.", "gallery_title": "Consultório, detalhe e acabamento de marca.", "gallery_intro": "A página usa respiro e contraste para comunicar cuidado mais exclusivo.", "reviews_title": "Confiança tratada com cuidado editorial.", "reviews_intro": "A reputação aparece como autoridade local.", "faq_title": "Perguntas de quem busca atendimento qualificado.", "faq_intro": "Informação objetiva sem banalizar a consulta.", "location_title": "Localização e contato com leitura premium.", "location_intro": "O WhatsApp final mantém elegância e clareza.", "lifestyle_kicker": "Autoridade", "contact_kicker": "Agendar"},
        },
    ],
    "barbearia": [
        {
            "id": "barber-old-money-green",
            "name": "Old Money Green",
            "fallback_palette": {"primary": "#d9b86c", "secondary": "#12392d", "bg_dark": "#071c16", "bg_light": "#f3ead8", "text_dark": "#14221c"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Barbearia clássica", "about_kicker": "Tradição", "about_title": "Corte com aparência de clube reservado e atenção ao detalhe.", "about_body": "{name} ganha uma presença mais elegante para valorizar tradição, reserva e acabamento em {city}.", "gallery_title": "Madeira, metal e ritual em composição premium.", "gallery_intro": "A galeria deixa de parecer catálogo e vira atmosfera.", "reviews_title": "Clientes que voltam pelo atendimento e acabamento.", "reviews_intro": "A reputação é tratada como confiança recorrente.", "faq_title": "Antes de reservar o horário.", "faq_intro": "Serviços, agenda e chegada em linguagem direta.", "location_title": "Encontre a barbearia em {city}.", "location_intro": "Contato e endereço fecham a reserva sem atrito.", "lifestyle_kicker": "Tradição", "contact_kicker": "Reserva"},
        },
        {
            "id": "barber-street-red",
            "name": "Street Red",
            "fallback_palette": {"primary": "#ef233c", "secondary": "#111111", "bg_dark": "#050505", "bg_light": "#f7f7f7", "text_dark": "#111111"},
            "blocks": {"hero_variant": "fullbleed", "services_variant": "stats_then_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte urbano", "about_kicker": "Atitude", "about_title": "Uma barbearia com presença forte, direta e memorável.", "about_body": "{name} assume uma linha mais urbana quando a marca precisa parecer atual, rápida e com personalidade.", "gallery_title": "Rua, contraste e acabamento em destaque.", "gallery_intro": "O visual trabalha impacto e clareza no primeiro scroll.", "reviews_title": "Prova local com energia de marca.", "reviews_intro": "Score e comentários entram com ritmo mais agressivo.", "faq_title": "O que saber antes de chamar.", "faq_intro": "FAQ curto para levar o usuário direto ao WhatsApp.", "location_title": "Reserve em {city} sem enrolação.", "location_intro": "Endereço, contato e ação aparecem no mesmo bloco.", "lifestyle_kicker": "Atitude", "contact_kicker": "Chamar"},
        },
        {
            "id": "barber-atelier-light",
            "name": "Atelier Light",
            "fallback_palette": {"primary": "#1f2937", "secondary": "#c9a46a", "bg_dark": "#f6f1ea", "bg_light": "#ffffff", "text_dark": "#1f2937"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Barbearia autoral", "about_kicker": "Atelier", "about_title": "Corte e barba com estética mais clara, limpa e autoral.", "about_body": "{name} funciona como atelier de atendimento, com foco em detalhe e experiência sem peso visual excessivo.", "gallery_title": "Acabamento, luz e proximidade.", "gallery_intro": "A composição respira mais e valoriza o trabalho manual.", "reviews_title": "Clientes e confiança com tom mais humano.", "reviews_intro": "Avaliações ficam leves, mas convincentes.", "faq_title": "Perguntas antes do atendimento.", "faq_intro": "Informação prática sobre serviço, reserva e chegada.", "location_title": "Chegue com clareza em {city}.", "location_intro": "Contato e rota aparecem sem poluição.", "lifestyle_kicker": "Atelier", "contact_kicker": "Horário"},
        },
        {
            "id": "barber-brutal-mono",
            "name": "Brutal Mono",
            "fallback_palette": {"primary": "#ffffff", "secondary": "#000000", "bg_dark": "#000000", "bg_light": "#eeeeee", "text_dark": "#111111"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "split_editorial", "reviews_variant": "card_marquee", "faq_variant": "inline", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Corte sem excesso", "about_kicker": "Contraste", "about_title": "Uma barbearia com linguagem gráfica, seca e marcante.", "about_body": "{name} usa alto contraste e composição mais ousada para fugir da página escura comum.", "gallery_title": "Preto, branco e recorte preciso.", "gallery_intro": "A identidade vem da composição, não de ornamento.", "reviews_title": "Reputação em blocos fortes.", "reviews_intro": "Avaliações ganham peso visual e leitura rápida.", "faq_title": "Perguntas objetivas.", "faq_intro": "Sem discurso longo: serviço, horário, contato.", "location_title": "Endereço e reserva no mesmo golpe.", "location_intro": "O fechamento entrega clareza e impacto.", "lifestyle_kicker": "Contraste", "contact_kicker": "Reservar"},
        },
    ],
    "default": [
        {
            "id": "default-health-trust",
            "name": "Health Trust",
            "fallback_palette": {"primary": "#0ea5a4", "secondary": "#164e63", "bg_dark": "#ecfeff", "bg_light": "#ffffff", "text_dark": "#12343b"},
            "blocks": {"hero_variant": "split", "services_variant": "stacked_cards", "reviews_variant": "quote_spotlight", "faq_variant": "panel", "location_variant": "split_local", "surface_style": "soft_tint"},
            "copy": {"hero_badge": "Atendimento com confiança", "about_kicker": "Cuidado", "lifestyle_kicker": "Confiança", "contact_kicker": "Agendar"},
        },
        {
            "id": "default-local-craft",
            "name": "Local Craft",
            "fallback_palette": {"primary": "#b45309", "secondary": "#365314", "bg_dark": "#1c160f", "bg_light": "#fff7ed", "text_dark": "#21160d"},
            "blocks": {"hero_variant": "center", "services_variant": "split_editorial", "reviews_variant": "editorial_case", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "solid"},
            "copy": {"hero_badge": "Serviço local com presença", "about_kicker": "Ofício", "lifestyle_kicker": "Detalhe", "contact_kicker": "Contato"},
        },
        {
            "id": "default-technical-precision",
            "name": "Technical Precision",
            "fallback_palette": {"primary": "#60a5fa", "secondary": "#1e293b", "bg_dark": "#0f172a", "bg_light": "#eff6ff", "text_dark": "#0f172a"},
            "blocks": {"hero_variant": "asymmetric", "services_variant": "stats_then_cards", "reviews_variant": "score_wall", "faq_variant": "inline", "location_variant": "split_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Serviço técnico", "about_kicker": "Precisão", "lifestyle_kicker": "Processo", "contact_kicker": "Solicitar"},
        },
        {
            "id": "default-hospitality-warm",
            "name": "Hospitality Warm",
            "fallback_palette": {"primary": "#f97316", "secondary": "#7c2d12", "bg_dark": "#21130b", "bg_light": "#fff3e8", "text_dark": "#24150c"},
            "blocks": {"hero_variant": "video", "services_variant": "split_editorial", "reviews_variant": "card_marquee", "faq_variant": "panel", "location_variant": "feature_local", "surface_style": "outline"},
            "copy": {"hero_badge": "Experiência local", "about_kicker": "Recepção", "lifestyle_kicker": "Ambiente", "contact_kicker": "Reservar"},
        },
    ],
}


_LANE_COPY_ENRICHMENTS: dict[str, dict[str, str]] = {
    "academia-graphite-core": {"services_kicker": "Equipamento de precisão pra quem leva a sério", "gallery_kicker": "Carga, barra e número — sem enrolação", "reviews_kicker": "Relatos de quem troca estação por progresso", "faq_kicker": "Tudo que o aluno técnico quer saber", "location_cta_title": "Seu treino técnico começa em {city}", "location_cta_body": "A Graphite Core fica em {city} com estrutura de musculação, área de força e orientação técnica baseada em carga, repetição e progresso medido.", "contact_headline": "Chama o time da barra"},
    "academia-iron-pulse": {"services_kicker": "Treino real", "gallery_kicker": "Carga e ambiente", "reviews_kicker": "Prova local", "faq_kicker": "Antes da primeira série", "location_cta_title": "Fale com a equipe e entre no ritmo.", "location_cta_body": "WhatsApp, endereço e decisão aparecem juntos para não perder impulso.", "contact_headline": "Pronto para começar o treino com estrutura de verdade?"},
    "academia-neon-grid": {"services_kicker": "Programas forjados sob luz neon", "gallery_kicker": "Madrugadas que viraram progresso", "reviews_kicker": "Alunos que trocaram o bar pelo suor", "faq_kicker": "Tira-dúvidas de quem treina depois do expediente", "location_cta_title": "Sua próxima sessão pulsa em {city}", "location_cta_body": "A Neon Grid opera em {city} com turmas noturnas, ambientes climatizados e equipamento de musculação e funcional pensado pra quem chega depois do último metrô.", "contact_headline": "Liga pro time da grade"},
    "academia-sunset-track": {"services_kicker": "Treinos que cabem entre o trabalho e o pôr do sol", "gallery_kicker": "Final de tarde que vira série pesada", "reviews_kicker": "Histórias de quem encaixou o treino no dia cheio", "faq_kicker": "Perguntas de quem quer começar ainda hoje", "location_cta_title": "Seu último suspiro do dia vem em {city}", "location_cta_body": "A Sunset Track atende em {city} no horário que o expediente libera: musculação, funcional e acompanhamento pra quem começou ontem e pra quem já carrega barra há anos.", "contact_headline": "Fala com o time do entardecer"},
    "advogado-lex-meridian": {"services_kicker": "Método jurídico do diagnóstico à decisão", "gallery_kicker": "Documentos que sustentaram cada tese", "reviews_kicker": "Clientes atendidos em prazos críticos", "faq_kicker": "Tira-dúvidas sobre andamento processual", "location_cta_title": "Acompanhamento jurídico em {city}", "location_cta_body": "A Lex Meridian opera em {city} com metodologia própria: análise de autos, parecer técnico e plano de ação processual pra cada cliente.", "contact_headline": "Marque sua consulta técnica"},
    "advogado-statute-noir": {"services_kicker": "Atuação firme em tribunal e sala de audiência", "gallery_kicker": "Casos que exigiram argumento, não promessa", "reviews_kicker": "Clientes que chegaram com dúvida e saíram com sentença", "faq_kicker": "Questões sobre processo, prazo e estratégia", "location_cta_title": "Atendimento jurídico presencial em {city}", "location_cta_body": "O escritório Statute Noir atende em {city} com foco em causas cíveis, criminais e empresariais defendidas com peças técnicas e sustentação oral.", "contact_headline": "Fale direto com a banca"},
    "barbearia-copper-smoke": {"services_kicker": "Calor de toalha, brilho de navalha, silêncio de charuto", "gallery_kicker": "Noites que viraram ritual", "reviews_kicker": "Homens que pediram outra hora só pra continuar", "faq_kicker": "Como funciona o ritual noturno", "location_cta_title": "Atendimento noturno reservado em {city}", "location_cta_body": "A Copper Smoke opera em {city} em horário estendido, com poucos clientes por noite, bebida de cortesia e foco em quem quer sair de lá refeito.", "contact_headline": "Garanta sua noite"},
    "barbearia-heritage-reserve": {"services_kicker": "Corte, barba e ritual em couro e navalha", "gallery_kicker": "Mosaicos do ofício, poltrona por poltrona", "reviews_kicker": "Homens que voltaram a se olhar no espelho", "faq_kicker": "Tudo que o barbeiro experiente já respondeu", "location_cta_title": "Seu próximo ritual de cuidado em {city}", "location_cta_body": "A Heritage Reserve recebe em {city} clientes que valorizam atendimento agendado, ambiente reservado e o ritmo antigo do barbeiro.", "contact_headline": "Reserve sua poltrona"},
    "barbearia-midnight-club": {"services_kicker": "Atendimento fechado pra poucos nomes", "gallery_kicker": "Mosaicos do salão privado", "reviews_kicker": "Sócios que indicam sem precisar explicar", "faq_kicker": "Como entrar na agenda do clube", "location_cta_title": "Sócios recebem em {city}", "location_cta_body": "A Midnight Club atende em {city} exclusivamente por indicação e assinatura, com bar, lounge e barbearia num único endereço reservado.", "contact_headline": "Peça acesso ao clube"},
    "barbearia-studio-mono": {"services_kicker": "Corte editorial, barba esculpida, olhar limpo", "gallery_kicker": "Ensaios visuais que ditam referência", "reviews_kicker": "Clientes saídos de capa sem precisar de convite", "faq_kicker": "O que muda entre estúdio e barbearia comum", "location_cta_title": "Studio de imagem masculina em {city}", "location_cta_body": "A Studio Mono atende em {city} com agenda curta, atendimento individual e acabamento pensado pra quem trata corte como parte do estilo.", "contact_headline": "Agende sua sessão"},
    "barber-copper-smoke": {"services_kicker": "Noite e acabamento", "gallery_kicker": "Luz baixa e cobre", "reviews_kicker": "Sinais locais", "faq_kicker": "Perguntas de quem quer reservar hoje", "location_cta_title": "Abra o WhatsApp e puxe sua reserva.", "location_cta_body": "Contato, rota e sensação de convite trabalham no mesmo pulso visual.", "contact_headline": "Vamos confirmar seu horário e deixar o corte na agenda?"},
    "barber-heritage-reserve": {"services_kicker": "Corte e ritual", "gallery_kicker": "Detalhe e textura", "reviews_kicker": "Clientes recorrentes", "faq_kicker": "Antes do horário", "location_cta_title": "Reserve pelo WhatsApp e veja a rota.", "location_cta_body": "A reserva fecha o site com presença clássica, rota objetiva e menos fricção.", "contact_headline": "Quer garantir seu horário com corte, barba e acabamento bem alinhados?"},
    "barber-midnight-club": {"services_kicker": "Marca autoral", "gallery_kicker": "Clube e atmosfera", "reviews_kicker": "Reputação de marca", "faq_kicker": "O cliente quer saber", "location_cta_title": "Fale pelo WhatsApp e feche a reserva.", "location_cta_body": "A navegação termina em contato direto, identidade forte e caminho sem distrações.", "contact_headline": "Pronto para reservar um horário com assinatura mais autoral?"},
    "barber-studio-mono": {"services_kicker": "Assinatura contemporânea", "gallery_kicker": "Forma e recorte", "reviews_kicker": "Confiança editorial", "faq_kicker": "Antes de reservar", "location_cta_title": "Agende sem excesso de conversa.", "location_cta_body": "O CTA é seco, direto e acompanhado de localização para fechar a decisão na hora.", "contact_headline": "Seu próximo corte pode ser marcado agora, sem complicação."},
    "clinica-care-plus": {"services_kicker": "Cuidado que começa antes do consultório", "gallery_kicker": "Famílias e pacientes que viraram rotina", "reviews_kicker": "Histórias de quem foi ouvido antes de examinado", "faq_kicker": "Tira-dúvidas sobre primeira consulta", "location_cta_title": "Cuidado clínico pra família toda em {city}", "location_cta_body": "A Care Plus atende em {city} com equipe multidisciplinar, prontuário unificado e acompanhamento que respeita o ritmo de crianças, adultos e idosos.", "contact_headline": "Agende pra quem você cuida"},
    "clinica-medical-trust": {"services_kicker": "Equipe médica, exames e encaminhamento ágil", "gallery_kicker": "Instalações que transmitem segurança clínica", "reviews_kicker": "Pacientes atendidos sem fila e sem pressa", "faq_kicker": "Convênios, exames e preparo de consulta", "location_cta_title": "Atendimento clínico em {city}", "location_cta_body": "A Medical Trust atende em {city} com profissionais habilitados, recepção organizada e estrutura pra consulta, exame e retorno no mesmo fluxo.", "contact_headline": "Fale com a recepção"},
    "default-cinematic-soft": {"services_kicker": "Atendimento conduzido por narrativa", "gallery_kicker": "Quadros do antes, durante e depois", "reviews_kicker": "Clientes que contam como foi atendido", "faq_kicker": "Tudo que o cliente costuma perguntar", "location_cta_title": "Atendimento presencial em {city}", "location_cta_body": "O atendimento presencial acontece em {city} com agenda marcada, escuta inicial e plano combinado antes da execução.", "contact_headline": "Fale com o time"},
    "default-conversion-bold": {"services_kicker": "Direto ao ponto, sem enrolação", "gallery_kicker": "Resultados registrados em entrega", "reviews_kicker": "Quem fechou e voltou pra fechar de novo", "faq_kicker": "Resposta curta pra dúvida curta", "location_cta_title": "Resposta rápida em {city}", "location_cta_body": "Atendimento objetivo em {city} com orçamento em até 24 horas, escopo fechado por escrito e prazo cumprido no combinado.", "contact_headline": "Manda a dúvida"},
    "default-health-trust": {"services_kicker": "Atendimento certificado e documentado", "gallery_kicker": "Instalações, equipe e procedimentos", "reviews_kicker": "Pacientes e clientes que recomendaram", "faq_kicker": "Dúvidas mais frequentes resolvidas", "location_cta_title": "Atendimento presencial em {city}", "location_cta_body": "A estrutura funciona em {city} com equipe registrada, ambiente limpo e procedimento seguido de acordo com protocolo da categoria.", "contact_headline": "Fale com a recepção"},
    "default-local-craft": {"services_kicker": "Ofício feito à mão, no bairro", "gallery_kicker": "Detalhes do trabalho local", "reviews_kicker": "vizinhos que voltaram e indicaram", "faq_kicker": "Prazo, orçamento e retirada", "location_cta_title": "Atendimento local em {city}", "location_cta_body": "O trabalho é feito em {city} sob encomenda, com prazo combinado, material escolhido junto e entrega registrada peça a peça.", "contact_headline": "Venha conhecer o ateliê"},
    "dentista-clinical-white": {"services_kicker": "Ambiente branco, técnica apurada, plano claro", "gallery_kicker": "Procedimentos registrados passo a passo", "reviews_kicker": "Pacientes que aprovaram o plano antes da cadeira", "faq_kicker": "Materiais, anestesia e tempo de recuperação", "location_cta_title": "Consultório odontológico em {city}", "location_cta_body": "A Clinical White opera em {city} com consultórios claros, esterilização visível e plano odontológico explicado antes de qualquer procedimento.", "contact_headline": "Venha pro consultório"},
    "dentista-smile-care": {"services_kicker": "Odontologia que devolve vontade de sorrir", "gallery_kicker": "Antes e depois que mudaram a autoimagem", "reviews_kicker": "Pacientes que voltaram a sorrir em foto", "faq_kicker": "Dúvidas sobre clareamento, lente e implante", "location_cta_title": "Seu novo sorriso começa em {city}", "location_cta_body": "A Smile Care atende em {city} com clínica completa, equipe de dentistas e estrutura pra clareamento, lente, implante e ortodontia.", "contact_headline": "Marque sua avaliação"},
    "energia-solar-sun-pure": {"services_kicker": "Energia limpa monitorada em tempo real", "gallery_kicker": "Telhados instalados em diferentes perfis", "reviews_kicker": "Proprietários acompanhando geração pelo celular", "faq_kicker": "Dúvidas sobre payback e homologação", "location_cta_title": "Sua usina solar fica em {city}", "location_cta_body": "A Sun Pure instala em {city} sistemas fotovoltaicos com monitoramento por aplicativo, homologação na concessionária e manutenção programada.", "contact_headline": "Simule sua economia"},
    "energia-solar-tech-grid": {"services_kicker": "Performance medida, ROI calculado, dado exposto", "gallery_kicker": "Geração em kWh registrada mês a mês", "reviews_kicker": "Faturas que chegaram zeradas por conta própria", "faq_kicker": "Comparativo entre marcas e potências", "location_cta_title": "Engenharia fotovoltaica em {city}", "location_cta_body": "A Tech Grid projeta e instala em {city} sistemas solares com análise de consumo, simulação financeira por fase e laudo técnico pra cada telhado.", "contact_headline": "Peça o estudo técnico"},
    "estetica-chrome-spa": {"services_kicker": "Tecnologia e cuidado manual no mesmo protocolo", "gallery_kicker": "Aparelhos e mãos trabalhando lado a lado", "reviews_kicker": "Clientes que sentiram diferença na primeira sessão", "faq_kicker": "Tecnologias usadas e contraindicações", "location_cta_title": "Spa tecnológico em {city}", "location_cta_body": "A Chrome Spa opera em {city} unindo equipamentos de estética avançada e técnicas manuais, com avaliação prévia e plano de sessões registrado.", "contact_headline": "Agende sua sessão"},
    "estetica-clinic-ivory": {"services_kicker": "Procedimentos faciais e corporais de alta costura", "gallery_kicker": "Atendimento em luz natural e marfim", "reviews_kicker": "Clientes que voltaram a se olhar sem pressa", "faq_kicker": "Cuidados antes e depois de cada protocolo", "location_cta_title": "Sua próxima sessão estética em {city}", "location_cta_body": "A Clinic Ivory atende em {city} com protocolos personalizados, ambiente em marfim e profissionais habilitados em estética facial e corporal.", "contact_headline": "Reserve sua avaliação"},
    "estetica-noir-gold": {"services_kicker": "Tratamentos premium em ambiente preto e dourado", "gallery_kicker": "Detalhes do lounge reservado", "reviews_kicker": "Clientes atendidas com hora marcada e sem fila", "faq_kicker": "Diferenciais do atendimento premium", "location_cta_title": "Estética premium em {city}", "location_cta_body": "A Noir Gold recebe em {city} poucas clientes por turno, com protocolo individual, produtos importados e lounge preparado pra esperar e sair refeita.", "contact_headline": "Fale com a concierge"},
    "estetica-rose-clay": {"services_kicker": "Cuidado facial com calor de terracota", "gallery_kicker": "Retratos do ritual em rosa e argila", "reviews_kicker": "Mulheres que reencontraram o próprio reflexo", "faq_kicker": "Rotina de skincare entre as sessões", "location_cta_title": "Ritual de beleza em {city}", "location_cta_body": "A Rose Clay recebe em {city} clientes que buscam hidratação profunda, massagem modeladora e protocolos faciais em atmosfera feminina e calma.", "contact_headline": "Marque seu horário"},
    "imobiliaria-key-modern": {"services_kicker": "Portfólio de imóveis prontos pra morar", "gallery_kicker": "Apartamentos por bairro e metragem", "reviews_kicker": "Compradores atendidos do plantão à escritura", "faq_kicker": "Dúvidas sobre financiamento e ITBI", "location_cta_title": "Seu próximo imóvel fica em {city}", "location_cta_body": "A Key Modern atua em {city} com catálogo atualizado de apartamentos e casas, visita agendada e acompanhamento de proposta até a escritura.", "contact_headline": "Peça a curadoria"},
    "imobiliaria-loft-elegance": {"services_kicker": "Loft, cobertura e alto-padrão sob medida", "gallery_kicker": "Acabamentos que fecham a venda sozinhos", "reviews_kicker": "Negócios fechados acima de sete dígitos", "faq_kicker": "Como funciona a busca personalizada", "location_cta_title": "Imóveis alto-padrão em {city}", "location_cta_body": "A Loft Elegance intermedia em {city} imóveis de alto padrão com tour agendado, análise de documentação e discrição em toda a negociação.", "contact_headline": "Fale com o corretor"},
    "nutri-botanical-editorial": {"services_kicker": "Consulta e método", "gallery_kicker": "Consultório e rotina", "reviews_kicker": "Pacientes", "faq_kicker": "Antes da consulta", "location_cta_title": "Agende com calma e contato direto.", "location_cta_body": "Consultório, WhatsApp e próximos passos aparecem sem poluição visual.", "contact_headline": "Pronto para começar um acompanhamento nutricional com direção clara?"},
    "nutri-clinical-soft": {"services_kicker": "Atendimento clínico", "gallery_kicker": "Ambiente claro", "reviews_kicker": "Confiança gradual", "faq_kicker": "Perguntas do primeiro atendimento", "location_cta_title": "Veja o consultório e fale sem atrito.", "location_cta_body": "Tudo foi organizado para leitura confortável, decisão rápida e contato saudável.", "contact_headline": "Quer tirar dúvidas e marcar sua primeira consulta?"},
    "nutri-coastal-light": {"services_kicker": "Cuidado nutricional", "gallery_kicker": "Leveza com contexto", "reviews_kicker": "Opiniões de confiança", "faq_kicker": "Dúvidas antes de cuidar da rotina", "location_cta_title": "Fale com leveza, mas com direção.", "location_cta_body": "Consultório, contato e ação aparecem num arranjo mais calmo e muito mais legível.", "contact_headline": "Sua consulta pode começar com uma conversa mais clara."},
    "nutri-performance-fuel": {"services_kicker": "Estratégia e performance", "gallery_kicker": "Rotina ativa", "reviews_kicker": "Resultados percebidos", "faq_kicker": "Perguntas de quem quer começar logo", "location_cta_title": "Confirme pelo WhatsApp e avance com segurança.", "location_cta_body": "A rota de contato aparece com mais energia para quem compara profissionais e quer agir agora.", "contact_headline": "Vamos transformar objetivo em rotina alimentar aplicável?"},
    "nutricionista-botanical-editorial": {"services_kicker": "Consultório verde, escuta longa, plano sob medida", "gallery_kicker": "Pranchas, chás e prataria do consultório", "reviews_kicker": "Pacientes que aderiram sem cortar o que amam", "faq_kicker": "Dúvidas sobre consulta inicial e retorno", "location_cta_title": "Atendimento nutricional em {city}", "location_cta_body": "A Botanical Editorial atende em {city} com consulta ampla, plano alimentar escrito em detalhe e retorno programado pra cada etapa.", "contact_headline": "Agende sua primeira escuta"},
    "nutricionista-clinical-soft": {"services_kicker": "Acompanhamento clínico leve e contínuo", "gallery_kicker": "Consultório claro entre sessões", "reviews_kicker": "Pacientes que sustentaram o plano por meses", "faq_kicker": "Exames pedidos e frequência de retorno", "location_cta_title": "Consultório de nutrição em {city}", "location_cta_body": "A Clinical Soft opera em {city} com protocolos pra emagrecimento, ganho de massa e reeducação alimentar, sempre com retorno programado.", "contact_headline": "Marque sua consulta"},
    "nutricionista-coastal-light": {"services_kicker": "Alimentação leve pra longevidade sem radicalismo", "gallery_kicker": "Refeições que cabem na rotina", "reviews_kicker": "Pacientes que trocaram dieta por estilo", "faq_kicker": "Como funciona o plano de manutenção", "location_cta_title": "Nutrição pra vida toda em {city}", "location_cta_body": "A Coastal Light atende em {city} com plano alimentar baseado em comida de verdade, ajuste sazonal e suporte direto entre as consultas.", "contact_headline": "Comece pelo cardápio"},
    "nutricionista-performance-fuel": {"services_kicker": "Planejamento alimentar pra hora do jogo", "gallery_kicker": "Atletas em fase de corte e carga", "reviews_kicker": "Marcas pessoais com peso e composição no alvo", "faq_kicker": "Suplementos, carboidrato e janela de treino", "location_cta_title": "Nutrição esportiva em {city}", "location_cta_body": "A Performance Fuel atende em {city} atletas amadores e profissionais com plano pra treino, competição e recuperação, ajustado semana a semana.", "contact_headline": "Bora pro próximo PR"},
    "oficina-garage-iron": {"services_kicker": "Mecânica pesada, motor e transmissão", "gallery_kicker": "Oficina aberta, sem esconder o que faz", "reviews_kicker": "Frotistas e motoristas que indicam", "faq_kicker": "Prazo de retífica e peças paralelas", "location_cta_title": "Oficina de peso em {city}", "location_cta_body": "A Garage Iron atende em {city} serviços de motor, câmbio, suspensão e elétrica com orçamento detalhado antes de tirar a chave do contato.", "contact_headline": "Fala direto com o mestre"},
    "oficina-torque-box": {"services_kicker": "Diagnóstico rápido e torque conferido", "gallery_kicker": "Carros atendidos no chão da oficina", "reviews_kicker": "Motoristas que saíram sem voltar no dia seguinte", "faq_kicker": "Peças usadas, garantia e prazo", "location_cta_title": "Diagnóstico automotivo em {city}", "location_cta_body": "A Torque Box opera em {city} com scanner, alinhamento, geometria e serviço mecânico entregue no mesmo dia quando o escopo permite.", "contact_headline": "Traga o carro pra bancada"},
    "pet-shop-patudo": {"services_kicker": "Banho, tosa e carinho olho no olho", "gallery_kicker": "Cães e gatos prontos pro passeio", "reviews_kicker": "Donos que recebem foto do antes e depois", "faq_kicker": "Vacina, agendamento e retirada", "location_cta_title": "Cuidado animal em {city}", "location_cta_body": "O Patudo atende em {city} com banho, tosa, venda de ração e acessórios, sempre com fila organizada e devolução do bicho cheirando casa.", "contact_headline": "Traga o bicho pra cuidar"},
    "pet-shop-pet-care-pro": {"services_kicker": "Veterinária, exames e vacinação", "gallery_kicker": "Consultórios e internação leve", "reviews_kicker": "Tutores que entenderam o diagnóstico", "faq_kicker": "Vacina, castração e retorno", "location_cta_title": "Saúde animal em {city}", "location_cta_body": "A Pet Care Pro atende em {city} com veterinários de prontidão, exames laboratoriais, vacinação e orientação nutricional por espécie.", "contact_headline": "Agende a consulta do pet"},
    "restaurante-forno-livre": {"services_kicker": "Massa fresca, forno aberto e madeira no chão", "gallery_kicker": "Bordas, massas e tempos de forno", "reviews_kicker": "Clientes que pediram outra rodada sem olhar o cardápio", "faq_kicker": "Reserva, retirada e massa do dia", "location_cta_title": "Pizza de forno a lenha em {city}", "location_cta_body": "O Forno Livre roda em {city} com forno a lenha, massa fermentada natural e cardápio curto pra pizzaria — clássico, especial e doce.", "contact_headline": "Garanta sua mesa"},
    "restaurante-prato-certo": {"services_kicker": "Comida caseira servida no mesmo prato de sempre", "gallery_kicker": "Mesa do almoço, do jantar e do fim de semana", "reviews_kicker": "Famílias que repetiram mais de uma vez na semana", "faq_kicker": "Cardápio diário e opções pra levar", "location_cta_title": "Mesa servida em {city}", "location_cta_body": "O Prato Certo funciona em {city} com buffet por quilo no almoço, prato executivo no jantar e marmita pesada pra quem quer comer bem em casa.", "contact_headline": "Reserve a mesa"},
    "salao-glow-studio": {"services_kicker": "Brilho, cor e luz próprias pra cada madeixa", "gallery_kicker": "Antes e depois de mechas, cortes e luzes", "reviews_kicker": "Clientes que voltaram a se filmar pra foto", "faq_kicker": "Descoloração, cronograma e manutenção", "location_cta_title": "Seu novo brilho começa em {city}", "location_cta_body": "O Glow Studio atende em {city} com coloração, corte, cauterização e protocolos capilares pensados pra manter o fio saudável entre as visitas.", "contact_headline": "Agende sua cor"},
    "salao-mirror-room": {"services_kicker": "Espelho, técnica e olhar editorial", "gallery_kicker": "Bastidores de editorial e teste de luz", "reviews_kicker": "Clientes que saíram com corte de capa", "faq_kicker": "Diferença entre corte técnico e corte comum", "location_cta_title": "Salão editorial em {city}", "location_cta_body": "A Mirror Room atende em {city} com hora marcada, diagnóstico de visagismo e acabamento registrado pra cada cliente que senta na cadeira.", "contact_headline": "Marque sua sessão"},
}



def _lane_variant_defaults(lane_id: str) -> dict[str, str]:
    """Per-lane defaults for pricing/stats visual variants.

    Deterministic mapping from lane id to layout choice. Keeps the lane
    catalog compact while ensuring each lane gets a distinct feel.
    """
    if not lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "inline_hero_stats"}

    if lane_id.endswith("-iron-pulse") or "iron-pulse" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}
    if lane_id.endswith("-neon-grid") or "neon-grid" in lane_id:
        return {"pricing_variant": "single_plan", "stats_variant": "mosaic_grid"}
    if lane_id.endswith("-sunset-track") or "sunset-track" in lane_id:
        return {"pricing_variant": "editorial_plan", "stats_variant": "vertical_stack"}
    if lane_id.endswith("-graphite-core") or "graphite-core" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}

    if "premium-clinic" in lane_id or "noir-gold" in lane_id:
        return {"pricing_variant": "editorial_plan", "stats_variant": "vertical_stack"}
    if "sports-lab" in lane_id or "performance-fuel" in lane_id:
        return {"pricing_variant": "single_plan", "stats_variant": "mosaic_grid"}
    if "botanical-editorial" in lane_id or "coastal-light" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}
    if "clinical-soft" in lane_id or "rose-clay" in lane_id:
        return {"pricing_variant": "editorial_plan", "stats_variant": "inline_hero_stats"}

    if "midnight-club" in lane_id or "brutal-mono" in lane_id:
        return {"pricing_variant": "single_plan", "stats_variant": "mosaic_grid"}
    if "copper-smoke" in lane_id or "street-red" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}
    if "atelier-light" in lane_id or "studio-mono" in lane_id:
        return {"pricing_variant": "editorial_plan", "stats_variant": "inline_hero_stats"}
    if "heritage-reserve" in lane_id or "old-money-green" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "vertical_stack"}

    if "local-craft" in lane_id or "hospitality-warm" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}
    if "technical-precision" in lane_id or "cinematic-soft" in lane_id:
        return {"pricing_variant": "single_plan", "stats_variant": "mosaic_grid"}
    if "editorial-light" in lane_id or "health-trust" in lane_id:
        return {"pricing_variant": "editorial_plan", "stats_variant": "inline_hero_stats"}
    if "professional-dark" in lane_id or "conversion-bold" in lane_id:
        return {"pricing_variant": "plan_grid", "stats_variant": "dedicated_band"}

    return {"pricing_variant": "plan_grid", "stats_variant": "inline_hero_stats"}


def _lane_attitude_with_boosts(
    lane_id: str,
    prompt_priority: str | None = None,
    tier: str | None = None,
) -> dict[str, str]:
    """Physical design tokens — supports optional boosts from prompt_priority and tier.

    Quick Win (feedback 2026-07-02):
      - Sistema era unidimensional (nicho -> polo + intensity).
      - Agora aceita boosts por prompt_priority e tier em wellness lanes.
      - Defaults nao dependem desses sinais (fallback estavel).
    """
    lane_id = str(lane_id or "")

    # ── Wellness lanes: health-trust, botanical-editorial, clinical-soft, etc.
    WELLNESS_LANES = (
        "botanical-editorial",
        "clinical-soft",
        "coastal-light",
        "clinic-ivory",
        "rose-clay",
        "health-trust",
        "editorial-light",
    )
    is_wellness = any(token in lane_id for token in WELLNESS_LANES)

    # ── Collect base tokens ────────────────────────────────────────────────
    if not lane_id:
        base = {
            "aesthetic_mode": "balanced",
            "spacing_density": "normal",
            "radius_mode": "balanced",
            "container_strategy": "contained",
            "typography_scale": "strong",
            "heading_style": "clean",
            "surface_depth": "elevated",
            "overlap_mode": "none",
            "motion_intensity": "composed",
            "image_treatment": "clean",
        }

    elif any(token in lane_id for token in ("iron-pulse", "neon-grid", "brutal-mono", "street-red", "conversion-bold")):
        base = {
            "aesthetic_mode": "impact",
            "spacing_density": "compressed",
            "radius_mode": "sharp",
            "container_strategy": "edge_to_edge",
            "typography_scale": "heroic",
            "heading_style": "condensed",
            "surface_depth": "cutout",
            "overlap_mode": "strong",
            "motion_intensity": "sharp",
            "image_treatment": "high_contrast",
        }

    elif any(token in lane_id for token in ("graphite-core", "studio-mono", "technical-precision")):
        base = {
            "aesthetic_mode": "technical",
            "spacing_density": "normal",
            "radius_mode": "sharp",
            "container_strategy": "wide",
            "typography_scale": "strong",
            "heading_style": "condensed",
            "surface_depth": "bordered",
            "overlap_mode": "subtle",
            "motion_intensity": "composed",
            "image_treatment": "duotone",
        }

    elif is_wellness:
        base = {
            "aesthetic_mode": "wellness",
            "spacing_density": "spacious",
            "radius_mode": "soft",
            "container_strategy": "contained",
            "typography_scale": "soft",
            "heading_style": "editorial",
            "surface_depth": "elevated",
            "overlap_mode": "none",
            "motion_intensity": "minimal",
            "image_treatment": "clean",
        }

    elif any(token in lane_id for token in ("heritage-reserve", "noir-gold", "midnight-club", "premium-clinic", "old-money-green", "copper-smoke")):
        base = {
            "aesthetic_mode": "premium",
            "spacing_density": "spacious",
            "radius_mode": "balanced",
            "container_strategy": "wide",
            "typography_scale": "strong",
            "heading_style": "editorial",
            "surface_depth": "bordered",
            "overlap_mode": "subtle",
            "motion_intensity": "cinematic",
            "image_treatment": "grain",
        }

    elif any(token in lane_id for token in ("performance-fuel", "sports-lab", "cinematic-soft")):
        base = {
            "aesthetic_mode": "dynamic",
            "spacing_density": "normal",
            "radius_mode": "balanced",
            "container_strategy": "wide",
            "typography_scale": "strong",
            "heading_style": "kinetic",
            "surface_depth": "cutout",
            "overlap_mode": "subtle",
            "motion_intensity": "cinematic",
            "image_treatment": "high_contrast",
        }

    else:
        base = {
            "aesthetic_mode": "balanced",
            "spacing_density": "normal",
            "radius_mode": "balanced",
            "container_strategy": "contained",
            "typography_scale": "strong",
            "heading_style": "clean",
            "surface_depth": "elevated",
            "overlap_mode": "none",
            "motion_intensity": "composed",
            "image_treatment": "clean",
        }

    # ── Boost: wellness lanes respond to prompt_priority ───────────────────
    if is_wellness and prompt_priority:
        pp = prompt_priority.lower()
        if pp == "trust":
            # "Academia High Fitness" caso: wellness lane com sinal de
            # confianca. motion sobe de minimal -> visible (presenca discreta).
            base["motion_intensity"] = "visible"
        elif pp == "presence":
            # presenca maxima: motion sobe para sharp.
            base["motion_intensity"] = "sharp"

    # ── Boost: tier multiplier on all lanes ───────────────────────────────
    if tier:
        tier_upper = tier.upper()
        current = base["motion_intensity"]
        if tier_upper in ("ELITE", "PREMIUM"):
            if current == "minimal":
                base["motion_intensity"] = "visible"
            elif current == "visible":
                base["motion_intensity"] = "composed"
            elif current == "composed":
                base["motion_intensity"] = "cinematic"

    return base


def _lane_attitude_defaults(lane_id: str) -> dict[str, str]:
    """Physical design tokens that make existing blocks behave like liquid blocks."""
    return _lane_attitude_with_boosts(lane_id)


def get_family_copy_defaults(family: str) -> dict[str, str]:
    """Helper canonico para obter labels de copy por family/nicho.

    Sprint 12.x: consulta nicho_registry primeiro (fonte unica). Cai em
    _FAMILY_COPY_DEFAULTS legacy apenas se o nicho nao existir no registry
    (caso de nichos que ainda nao foram migrados, ex: contabilidade, escola).
    """
    try:
        from backend.config.nicho_registry import get_nicho_config
        cfg = get_nicho_config(family)
        # Montar shape legado (nav_*, services_kicker, etc) a partir do registry
        # Pool de labels disponiveis no nicho:
        nav_pool = [
            ("nav_about", cfg.copy_defaults.tone.split(",")[0].strip().capitalize()),
            ("nav_services", "Servicos"),
            ("nav_gallery", "Galeria"),
            ("nav_reviews", "Avaliacoes"),
            ("nav_faq", "Duvidas"),
            ("nav_location", "Localizacao"),
            ("nav_lifestyle", "Estilo"),
            ("nav_contact", cfg.copy_defaults.cta_primary),
        ]
        out = {k: v for k, v in nav_pool}
        out["services_kicker"] = "Servicos"
        out["gallery_kicker"] = "Galeria"
        out["reviews_kicker"] = "Avaliacoes"
        out["faq_kicker"] = "Duvidas"
        out["location_kicker"] = "Localizacao"
        out["contact_kicker"] = cfg.copy_defaults.cta_primary
        return out
    except Exception:
        # Fallback para dict legacy
        return dict(_FAMILY_COPY_DEFAULTS.get(family, _FAMILY_COPY_DEFAULTS.get("default", {})))


def resolve_visual_lane(
    *,
    segment: str = "",
    subnicho: str = "",
    visual_lane: str = "",
    tags: list[str] | None = None,
    description: str = "",
    prompt_priority: str | None = None,
    tier: str | None = None,
    counter: int = 0,
) -> dict[str, Any]:
    family = _segment_family(segment, subnicho)
    lanes = list(_LANES.get(family) or _LANES["default"])
    remixes = _LANE_REMIXES.get(family)
    if remixes is None and family == "default":
        remixes = _LANE_REMIXES.get("default")
    lanes.extend(remixes or [])
    try:
        base_index = _LANE_KEYS.index(str(visual_lane or "").strip())
    except ValueError:
        base_index = 0
    # Counter-shift: garante variedade entre leads sequenciais.
    # counter=0 -> lanes[base_index], counter=1 -> lanes[base_index+1], etc.
    counter_offset = int(counter) if counter else 0
    lane_index = (base_index + counter_offset) % len(lanes)
    lane = dict(lanes[lane_index])
    lane_blocks = dict(lane.get("blocks") or {})
    variant_defaults = _lane_variant_defaults(str(lane.get("id") or ""))
    # Quick Win (feedback 2026-07-02): boosts de prompt_priority e tier
    # agora chegam aqui e afetam motion_intensity em wellness lanes.
    attitude_defaults = _lane_attitude_with_boosts(
        str(lane.get("id") or ""),
        prompt_priority=prompt_priority,
        tier=tier,
    )
    for key, value in {**variant_defaults, **attitude_defaults}.items():
        lane_blocks.setdefault(key, value)
    lane["blocks"] = lane_blocks
    lane_copy = dict(_FAMILY_COPY_DEFAULTS.get(family, {}))
    lane_copy.update(_LANE_COPY_ENRICHMENTS.get(str(lane.get("id") or ""), {}))
    lane_copy.update(lane.get("copy") or {})
    lane["copy"] = lane_copy

    # Inferir polo estético para Blocos Líquidos
    pole_info = infer_aesthetic_pole(
        segment=segment,
        subniche=subnicho,
        tags=tags,
        description=description,
        tier=tier,
    )

    return {
        "family": family,
        **lane,
        # Adicionar informações do polo para Blocos Líquidos
        "pole": pole_info["pole"],
        "pole_heat": pole_info["heat"],
        "pole_temperature": pole_info["temperature"],
        "pole_display_mode": pole_info["display_mode"],
        "pole_tokens": pole_info["tokens"],
    }
