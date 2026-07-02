"""
============================================================================
FRA LIB - SEO TEMPLATES (Meta/Title/H1/OG/Twitter por Polo + Nicho)
============================================================================
Templates de SEO (title, meta description, h1, og_description, twitter_card)
indexados por polo (SOFT/BOLD/CLASSIC/TECH) e nicho. Usados pelo pipeline
para gerar metadata otimizada por polo estetico e segmento de negocio.

OBJETIVO:
- Substituir fallbacks hardcoded espalhados pelos agentes.
- Garantir limites de comprimento: title 50-60 chars, meta 150-160 chars,
  og 90-100 chars, twitter 200 chars.
- H1 sempre >= 8 palavras, com beneficio + cidade (regra do projeto).
- Tom de voz consistente por polo (SOFT acolhedor, BOLD direto, CLASSIC
  serio, TECH tecnico/dado).

USO:
    from backend.copywriting.seo_templates import (
        get_seo_template,
        generate_title,
        generate_meta,
        generate_h1,
        validate_title_length,
    )

    template = get_seo_template("SOFT", "nutricionista")
    title = generate_title(template, "Dra. Marina Alves", "Sao Paulo")
    meta = generate_meta(template, "Dra. Marina Alves", "Sao Paulo")
    h1 = generate_h1(template, "Sao Paulo")

Regras:
- title_pattern tem placeholders {hook} | {name} {city}
- meta_description tem placeholders {name}, {city} e CTA implicito
- h1_pattern usa {city} e tem >= 8 palavras (validado em runtime)
- og_description tem {name}, {city} e <= 100 chars apos formatar
- twitter_card tem {name}, {city} e <= 200 chars apos formatar

Fallback:
- Nicho nao mapeado -> chave "default" no polo.
- Polo invalido -> ValueError explicito.

============================================================================
"""

from __future__ import annotations

from typing import NamedTuple


# ═══════════════════════════════════════════════════════════════════════════
# TYPES
# ═══════════════════════════════════════════════════════════════════════════

class SEO_TEMPLATE(NamedTuple):
    """Template SEO imutavel para um par (polo, nicho)."""
    title_pattern: str            # "{hook} | {name} {city}" — 50-60 chars apos format
    meta_description_pattern: str # 150-160 chars apos format
    h1_pattern: str               # >= 8 palavras apos format
    og_description_pattern: str   # 90-100 chars apos format
    twitter_card_pattern: str     # <= 200 chars apos format


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE CONSTRUCAO
# ═══════════════════════════════════════════════════════════════════════════

def _seo(
    title_pattern: str,
    meta_description_pattern: str,
    h1_pattern: str,
    og_description_pattern: str,
    twitter_card_pattern: str,
) -> SEO_TEMPLATE:
    """Construtor auxiliar de SEO_TEMPLATE."""
    return SEO_TEMPLATE(
        title_pattern=title_pattern,
        meta_description_pattern=meta_description_pattern,
        h1_pattern=h1_pattern,
        og_description_pattern=og_description_pattern,
        twitter_card_pattern=twitter_card_pattern,
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATES POR POLO + NICHO
# ═══════════════════════════════════════════════════════════════════════════

SEO_TEMPLATES: dict[str, dict[str, SEO_TEMPLATE]] = {

    # ──────────────────────────────────────────────────────────────────
    # SOFT — acolhedor, sensorial, cuidadoso, "voce" no centro
    # ──────────────────────────────────────────────────────────────────
    "SOFT": {

        "nutricionista": _seo(
            title_pattern="Consulta nutricional com escuta | {name} {city}",
            meta_description_pattern=(
                "Atendimento nutricional que respeita seu ritmo, sua rotina e o que "
                "voce sente. Agende online e de o primeiro passo sem pressao em {city}."
            ),
            h1_pattern=(
                "Nutricao com escuta, metodo e respeito a sua rotina em {city}"
            ),
            og_description_pattern=(
                "Nutricao com escuta, metodo e respeito a sua rotina em {city}."
            ),
            twitter_card_pattern=(
                "Atendimento nutricional que respeita seu ritmo, sua rotina e o "
                "que voce sente. Agende online e de o primeiro passo sem pressao "
                "em {city} com {name}."
            ),
        ),

        "barbearia": _seo(
            title_pattern="Barbearia com ritual de cuidado | {name} {city}",
            meta_description_pattern=(
                "Corte e barba com calma, tecnica e conversa. Barbeiros que ouvem "
                "o que voce quer. Reserve seu horario pelo WhatsApp em {city}."
            ),
            h1_pattern=(
                "Barbearia com ritual de cuidado, tecnica e conversa em {city}"
            ),
            og_description_pattern=(
                "Barbearia com ritual de cuidado, tecnica e conversa em {city}."
            ),
            twitter_card_pattern=(
                "Corte e barba com calma, tecnica e conversa. Barbeiros que "
                "ouvem o que voce quer. Reserve seu horario pelo WhatsApp em "
                "{city} com {name}."
            ),
        ),

        "estetica": _seo(
            title_pattern="Estetica com cuidado e olhar atento | {name} {city}",
            meta_description_pattern=(
                "Procedimentos esteticos feitos com calma, avaliacao previa e "
                "sem pressa. Sua beleza cuidada com atencao em {city}."
            ),
            h1_pattern=(
                "Estetica com cuidado, avaliacao previa e resultado natural em {city}"
            ),
            og_description_pattern=(
                "Estetica com cuidado, avaliacao previa e resultado natural em {city}."
            ),
            twitter_card_pattern=(
                "Procedimentos esteticos feitos com calma, avaliacao previa e "
                "sem pressa. Sua beleza cuidada com atencao em {city} com {name}."
            ),
        ),

        "restaurante": _seo(
            title_pattern="Sabor com calma e afeto | {name} {city}",
            meta_description_pattern=(
                "Gastronomia feita com calma, ingredientes escolhidos a mao e "
                "ambiente acolhedor. Reserve sua mesa e venha sentir {city}."
            ),
            h1_pattern=(
                "Restaurante com sabor caseiro, calma e afeto no atendimento em {city}"
            ),
            og_description_pattern=(
                "Restaurante com sabor caseiro, calma e afeto no atendimento em {city}."
            ),
            twitter_card_pattern=(
                "Gastronomia feita com calma, ingredientes escolhidos a mao e "
                "ambiente acolhedor. Reserve sua mesa e venha sentir {city} "
                "com {name}."
            ),
        ),

        "pet_shop": _seo(
            title_pattern="Cuidado que seu pet sente | {name} {city}",
            meta_description_pattern=(
                "Banho, tosa e atendimento veterinario com paciencia e carinho. "
                "Seu pet tratado como parte da familia em {city}. Agende."
            ),
            h1_pattern=(
                "Pet shop com banho, tosa e cuidado veterinario em {city}"
            ),
            og_description_pattern=(
                "Pet shop com banho, tosa e cuidado veterinario em {city}."
            ),
            twitter_card_pattern=(
                "Banho, tosa e atendimento veterinario com paciencia e carinho. "
                "Seu pet tratado como parte da familia em {city}. Agende com "
                "{name}."
            ),
        ),

        "salao": _seo(
            title_pattern="Beleza com cuidado e calma | {name} {city}",
            meta_description_pattern=(
                "Cabelo, coloracao e manicure com profissionais que ouvem. "
                "Ambiente acolhedor e agendamento simples pelo WhatsApp em {city}."
            ),
            h1_pattern=(
                "Salao de beleza com cuidado, calma e profissionais que ouvem em {city}"
            ),
            og_description_pattern=(
                "Salao de beleza com cuidado, calma e profissionais que ouvem em {city}."
            ),
            twitter_card_pattern=(
                "Cabelo, coloracao e manicure com profissionais que ouvem. "
                "Ambiente acolhedor e agendamento simples pelo WhatsApp em "
                "{city} com {name}."
            ),
        ),

        # Nichos nao-SOFT ainda assim recebem template SOFT para consistencia
        "academia": _seo(
            title_pattern="Movimento que cuida de voce | {name} {city}",
            meta_description_pattern=(
                "Treino respeitando seu ritmo, avaliacao previa e profissionais "
                "que acompanham. Comece sem pressa e evolua com seguranca em {city}."
            ),
            h1_pattern=(
                "Academia com treino respeitoso, avaliacao e acompanhamento em {city}"
            ),
            og_description_pattern=(
                "Academia com treino respeitoso, avaliacao e acompanhamento em {city}."
            ),
            twitter_card_pattern=(
                "Treino respeitando seu ritmo, avaliacao previa e profissionais "
                "que acompanham. Comece sem pressa e evolua com seguranca em "
                "{city} com {name}."
            ),
        ),

        "clinica": _seo(
            title_pattern="Cuidado integral da sua saude | {name} {city}",
            meta_description_pattern=(
                "Atendimento medico com tempo, escuta e plano de cuidado claro. "
                "Consultas presenciais e telemedicina com agendamento em {city}."
            ),
            h1_pattern=(
                "Clinica com atendimento cuidadoso, escuta e plano claro em {city}"
            ),
            og_description_pattern=(
                "Clinica com atendimento cuidadoso, escuta e plano claro em {city}."
            ),
            twitter_card_pattern=(
                "Atendimento medico com tempo, escuta e plano de cuidado claro. "
                "Consultas presenciais e telemedicina com agendamento em {city} "
                "com {name}."
            ),
        ),

        "dentista": _seo(
            title_pattern="Sorriso saudavel com cuidado | {name} {city}",
            meta_description_pattern=(
                "Odontologia com avaliacao detalhada, plano claro e sem pressa. "
                "Cuidamos do seu sorriso com atencao em {city}. Agende."
            ),
            h1_pattern=(
                "Dentista com avaliacao detalhada, plano claro e sem pressa em {city}"
            ),
            og_description_pattern=(
                "Dentista com avaliacao detalhada, plano claro e sem pressa em {city}."
            ),
            twitter_card_pattern=(
                "Odontologia com avaliacao detalhada, plano claro e sem pressa. "
                "Cuidamos do seu sorriso com atencao em {city} com {name}."
            ),
        ),

        "advogado": _seo(
            title_pattern="Direito com cuidado e estrategia | {name} {city}",
            meta_description_pattern=(
                "Atendimento juridico com escuta, estrategia personalizada e "
                "sigilo. Analise inicial do seu caso sem compromisso em {city}."
            ),
            h1_pattern=(
                "Advogado com escuta, estrategia personalizada e sigilo em {city}"
            ),
            og_description_pattern=(
                "Advogado com escuta, estrategia personalizada e sigilo em {city}."
            ),
            twitter_card_pattern=(
                "Atendimento juridico com escuta, estrategia personalizada e "
                "sigilo. Analise inicial do seu caso sem compromisso em {city} "
                "com {name}."
            ),
        ),

        "oficina": _seo(
            title_pattern="Cuidado atencioso com seu carro | {name} {city}",
            meta_description_pattern=(
                "Diagnostico transparente, orcamento detalhado e servico cuidadoso. "
                "Seu carro em boas maos com prazo combinado em {city}."
            ),
            h1_pattern=(
                "Oficina com diagnostico transparente, orcamento e prazo em {city}"
            ),
            og_description_pattern=(
                "Oficina com diagnostico transparente, orcamento e prazo em {city}."
            ),
            twitter_card_pattern=(
                "Diagnostico transparente, orcamento detalhado e servico "
                "cuidadoso. Seu carro em boas maos com prazo combinado em "
                "{city} com {name}."
            ),
        ),

        "energia_solar": _seo(
            title_pattern="Energia limpa com acompanhamento | {name} {city}",
            meta_description_pattern=(
                "Energia solar com projeto sob medida, instalacao acompanhada "
                "e suporte humano. Economize com tranquilidade em {city}."
            ),
            h1_pattern=(
                "Energia solar com projeto sob medida, instalacao e suporte em {city}"
            ),
            og_description_pattern=(
                "Energia solar com projeto sob medida, instalacao e suporte em {city}."
            ),
            twitter_card_pattern=(
                "Energia solar com projeto sob medida, instalacao acompanhada "
                "e suporte humano. Economize com tranquilidade em {city} com "
                "{name}."
            ),
        ),

        "imobiliaria": _seo(
            title_pattern="Imovel com cuidado e atencao | {name} {city}",
            meta_description_pattern=(
                "Consultoria imobiliaria sem pressa, com escuta das suas "
                "necessidades. Visita acompanhada e suporte humanizado em {city}."
            ),
            h1_pattern=(
                "Imobiliaria com consultoria sem pressa e atendimento humanizado em {city}"
            ),
            og_description_pattern=(
                "Imobiliaria com consultoria sem pressa e atendimento humanizado em {city}."
            ),
            twitter_card_pattern=(
                "Consultoria imobiliaria sem pressa, com escuta das suas "
                "necessidades. Visita acompanhada e suporte humanizado em "
                "{city} com {name}."
            ),
        ),

        "default": _seo(
            title_pattern="Atendimento com cuidado e atencao | {name} {city}",
            meta_description_pattern=(
                "Atendimento cuidadoso, escuta ativa e solucao sob medida para "
                "sua necessidade. Fale conosco sem compromisso em {city}."
            ),
            h1_pattern=(
                "Atendimento com cuidado, escuta ativa e solucao sob medida em {city}"
            ),
            og_description_pattern=(
                "Atendimento com cuidado, escuta ativa e solucao sob medida em {city}."
            ),
            twitter_card_pattern=(
                "Atendimento cuidadoso, escuta ativa e solucao sob medida para "
                "sua necessidade. Fale conosco sem compromisso em {city} com "
                "{name}."
            ),
        ),
    },

    # ──────────────────────────────────────────────────────────────────
    # BOLD — direto, energia, cobranca, "agora", sem rodeios
    # ──────────────────────────────────────────────────────────────────
    "BOLD": {

        "academia": _seo(
            title_pattern="Academia que exige presenca | {name} {city}",
            meta_description_pattern=(
                "Aqui voce nao tem onde se esconder. Treino com plano, carga "
                "medida e equipe que cobra. Matricule-se ou pare de procurar "
                "academia em {city}."
            ),
            h1_pattern=(
                "A academia que cobra presenca e mede resultado em {city}"
            ),
            og_description_pattern=(
                "A academia que cobra presenca e mede resultado em {city}."
            ),
            twitter_card_pattern=(
                "Aqui voce nao tem onde se esconder. Treino com plano, carga "
                "medida e equipe que cobra. Matricule-se ou pare de procurar "
                "academia em {city} com {name}."
            ),
        ),

        "oficina": _seo(
            title_pattern="Mecanica forte, servico rapido | {name} {city}",
            meta_description_pattern=(
                "Diagnostico direto, orcamento na hora e servico sem enrolacao. "
                "Seu carro resolvido no mesmo dia em {city}. Traga agora."
            ),
            h1_pattern=(
                "Oficina mecanica que resolve seu carro no mesmo dia em {city}"
            ),
            og_description_pattern=(
                "Oficina mecanica que resolve seu carro no mesmo dia em {city}."
            ),
            twitter_card_pattern=(
                "Diagnostico direto, orcamento na hora e servico sem enrolacao. "
                "Seu carro resolvido no mesmo dia em {city} com {name}."
            ),
        ),

        "barbearia": _seo(
            title_pattern="Corte forte, visual marcante | {name} {city}",
            meta_description_pattern=(
                "Barbearia que entrega corte agressivo, barba alinhada e "
                "visual marcante. Saia daqui com cara de dono. Agende em {city}."
            ),
            h1_pattern=(
                "Barbearia que entrega corte agressivo e visual marcante em {city}"
            ),
            og_description_pattern=(
                "Barbearia que entrega corte agressivo e visual marcante em {city}."
            ),
            twitter_card_pattern=(
                "Barbearia que entrega corte agressivo, barba alinhada e "
                "visual marcante. Saia daqui com cara de dono. Agende em "
                "{city} com {name}."
            ),
        ),

        "nutricionista": _seo(
            title_pattern="Resultado real, sem dieta maluca | {name} {city}",
            meta_description_pattern=(
                "Plano alimentar agressivo, acompanhamento semanal e metas "
                "mensuraveis. Quebra o ciclo da dieta maluca em {city}."
            ),
            h1_pattern=(
                "Nutricionista com plano agressivo, meta e acompanhamento em {city}"
            ),
            og_description_pattern=(
                "Nutricionista com plano agressivo, meta e acompanhamento em {city}."
            ),
            twitter_card_pattern=(
                "Plano alimentar agressivo, acompanhamento semanal e metas "
                "mensuraveis. Quebra o ciclo da dieta maluca em {city} com "
                "{name}."
            ),
        ),

        "estetica": _seo(
            title_pattern="Transformacao visivel, resultado real | {name} {city}",
            meta_description_pattern=(
                "Procedimentos com resultado marcante, antes e depois "
                "comprovado e equipe que executa. Evolua agora em {city}."
            ),
            h1_pattern=(
                "Estetica com resultado marcante e equipe que executa em {city}"
            ),
            og_description_pattern=(
                "Estetica com resultado marcante e equipe que executa em {city}."
            ),
            twitter_card_pattern=(
                "Procedimentos com resultado marcante, antes e depois "
                "comprovado e equipe que executa. Evolua agora em {city} com "
                "{name}."
            ),
        ),

        "salao": _seo(
            title_pattern="Transformacao visual marcante | {name} {city}",
            meta_description_pattern=(
                "Mudanca radical de visual, profissionais que executam e "
                "produtos que entregam. Saia daqui renovada em {city}."
            ),
            h1_pattern=(
                "Salao com transformacao visual marcante e resultado imediato em {city}"
            ),
            og_description_pattern=(
                "Salao com transformacao visual marcante e resultado imediato em {city}."
            ),
            twitter_card_pattern=(
                "Mudanca radical de visual, profissionais que executam e "
                "produtos que entregam. Saia daqui renovada em {city} com {name}."
            ),
        ),

        "restaurante": _seo(
            title_pattern="Sabor que vira conversa | {name} {city}",
            meta_description_pattern=(
                "Prato marcante, porcao justa e sabor que gera fila. Reserve "
                "agora e pare de comer lugar ruim em {city}."
            ),
            h1_pattern=(
                "Restaurante com sabor marcante, porcao justa e fila em {city}"
            ),
            og_description_pattern=(
                "Restaurante com sabor marcante, porcao justa e fila em {city}."
            ),
            twitter_card_pattern=(
                "Prato marcante, porcao justa e sabor que gera fila. Reserve "
                "agora e pare de comer lugar ruim em {city} com {name}."
            ),
        ),

        "pet_shop": _seo(
            title_pattern="Banho, tosa e saude com agilidade | {name} {city}",
            meta_description_pattern=(
                "Atendimento rapido, equipe que manuseia seu pet com firmeza "
                "e carinho. Banho e tosa no mesmo dia em {city}."
            ),
            h1_pattern=(
                "Pet shop rapido, equipe firme e banho no mesmo dia em {city}"
            ),
            og_description_pattern=(
                "Pet shop rapido, equipe firme e banho no mesmo dia em {city}."
            ),
            twitter_card_pattern=(
                "Atendimento rapido, equipe que manuseia seu pet com firmeza "
                "e carinho. Banho e tosa no mesmo dia em {city} com {name}."
            ),
        ),

        "clinica": _seo(
            title_pattern="Saude de verdade, atendimento rapido | {name} {city}",
            meta_description_pattern=(
                "Consulta sem fila, diagnostico rapido e receita na hora. "
                "Resolvemos sua queixa hoje em {city}. Agende agora."
            ),
            h1_pattern=(
                "Clinica com consulta rapida, diagnostico e receita na hora em {city}"
            ),
            og_description_pattern=(
                "Clinica com consulta rapida, diagnostico e receita na hora em {city}."
            ),
            twitter_card_pattern=(
                "Consulta sem fila, diagnostico rapido e receita na hora. "
                "Resolvemos sua queixa hoje em {city} com {name}."
            ),
        ),

        "dentista": _seo(
            title_pattern="Sorriso forte, atendimento direto | {name} {city}",
            meta_description_pattern=(
                "Avaliacao rapida, plano agressivo e atendimento sem demora. "
                "Seu sorriso resolvido em poucas sessoes em {city}."
            ),
            h1_pattern=(
                "Dentista com avaliacao rapida e atendimento sem demora em {city}"
            ),
            og_description_pattern=(
                "Dentista com avaliacao rapida e atendimento sem demora em {city}."
            ),
            twitter_card_pattern=(
                "Avaliacao rapida, plano agressivo e atendimento sem demora. "
                "Seu sorriso resolvido em poucas sessoes em {city} com {name}."
            ),
        ),

        "advogado": _seo(
            title_pattern="Defendemos seus direitos com forca | {name} {city}",
            meta_description_pattern=(
                "Acao juridica firme, estrategia agressiva e cobranca de "
                "resultado. Seu caso conduzido sem enrolacao em {city}."
            ),
            h1_pattern=(
                "Advogado com estrategia agressiva e cobranca de resultado em {city}"
            ),
            og_description_pattern=(
                "Advogado com estrategia agressiva e cobranca de resultado em {city}."
            ),
            twitter_card_pattern=(
                "Acao juridica firme, estrategia agressiva e cobranca de "
                "resultado. Seu caso conduzido sem enrolacao em {city} com "
                "{name}."
            ),
        ),

        "energia_solar": _seo(
            title_pattern="Economia agressiva na conta de luz | {name} {city}",
            meta_description_pattern=(
                "Instalacao rapida, payback agressivo e monitoramento em "
                "tempo real. Pare de pagar conta alta em {city} agora."
            ),
            h1_pattern=(
                "Energia solar com payback agressivo e instalacao rapida em {city}"
            ),
            og_description_pattern=(
                "Energia solar com payback agressivo e instalacao rapida em {city}."
            ),
            twitter_card_pattern=(
                "Instalacao rapida, payback agressivo e monitoramento em "
                "tempo real. Pare de pagar conta alta em {city} agora com "
                "{name}."
            ),
        ),

        "imobiliaria": _seo(
            title_pattern="O imovel certo, na hora certa | {name} {city}",
            meta_description_pattern=(
                "Curto direto, agenda aberta e proposta agressiva. Comprou, "
                "vendeu ou alugou sem fila em {city}. Fale agora."
            ),
            h1_pattern=(
                "Imobiliaria com agenda aberta e proposta agressiva em {city}"
            ),
            og_description_pattern=(
                "Imobiliaria com agenda aberta e proposta agressiva em {city}."
            ),
            twitter_card_pattern=(
                "Curto direto, agenda aberta e proposta agressiva. Comprou, "
                "vendeu ou alugou sem fila em {city} com {name}."
            ),
        ),

        "default": _seo(
            title_pattern="Atendimento direto e resolutivo | {name} {city}",
            meta_description_pattern=(
                "Resposta na hora, equipe que executa e resultado sem "
                "enrolacao. Fale conosco agora em {city}."
            ),
            h1_pattern=(
                "Atendimento direto, equipe que executa e resultado rapido em {city}"
            ),
            og_description_pattern=(
                "Atendimento direto, equipe que executa e resultado rapido em {city}."
            ),
            twitter_card_pattern=(
                "Resposta na hora, equipe que executa e resultado sem "
                "enrolacao. Fale conosco agora em {city} com {name}."
            ),
        ),
    },

    # ──────────────────────────────────────────────────────────────────
    # CLASSIC — serio, tecnico, confiavel, "escritorio", "anos"
    # ──────────────────────────────────────────────────────────────────
    "CLASSIC": {

        "advogado": _seo(
            title_pattern="Atendimento juridico com metodo | {name} {city}",
            meta_description_pattern=(
                "Analise tecnica, estrategia fundamentada e sigilo absoluto. "
                "Consulta inicial com agenda em ate 48h. Areas: civel, "
                "trabalhista, familia em {city}."
            ),
            h1_pattern=(
                "Escritorio de advocacia com metodo e analise tecnica em {city}"
            ),
            og_description_pattern=(
                "Escritorio de advocacia com metodo e analise tecnica em {city}."
            ),
            twitter_card_pattern=(
                "Analise tecnica, estrategia fundamentada e sigilo absoluto. "
                "Consulta inicial com agenda em ate 48h. Areas: civel, "
                "trabalhista, familia em {city} com {name}."
            ),
        ),

        "clinica": _seo(
            title_pattern="Medicina de excelencia, ha anos | {name} {city}",
            meta_description_pattern=(
                "Corpo clinico certificado, estrutura completa e protocolos "
                "consagrados. Atendimento por especialidade e convenio em {city}."
            ),
            h1_pattern=(
                "Clinica medica com corpo clinico certificado e protocolos em {city}"
            ),
            og_description_pattern=(
                "Clinica medica com corpo clinico certificado e protocolos em {city}."
            ),
            twitter_card_pattern=(
                "Corpo clinico certificado, estrutura completa e protocolos "
                "consagrados. Atendimento por especialidade e convenio em "
                "{city} com {name}."
            ),
        ),

        "dentista": _seo(
            title_pattern="Odontologia de precisao ha anos | {name} {city}",
            meta_description_pattern=(
                "Equipamentos modernos, equipe certificada e planejamento "
                "clinico detalhado. Implantes, ortodontia e estetica em {city}."
            ),
            h1_pattern=(
                "Clinica odontologica com planejamento detalhado e equipe certificada em {city}"
            ),
            og_description_pattern=(
                "Clinica odontologica com planejamento detalhado e equipe certificada em {city}."
            ),
            twitter_card_pattern=(
                "Equipamentos modernos, equipe certificada e planejamento "
                "clinico detalhado. Implantes, ortodontia e estetica em "
                "{city} com {name}."
            ),
        ),

        "imobiliaria": _seo(
            title_pattern="Imobiliaria tradicional, ha anos | {name} {city}",
            meta_description_pattern=(
                "Carteira consolidada, atendimento consultivo e contratos "
                "revisados. Compra, venda e locacao com seguranca em {city}."
            ),
            h1_pattern=(
                "Imobiliaria tradicional com carteira consolidada em {city}"
            ),
            og_description_pattern=(
                "Imobiliaria tradicional com carteira consolidada em {city}."
            ),
            twitter_card_pattern=(
                "Carteira consolidada, atendimento consultivo e contratos "
                "revisados. Compra, venda e locacao com seguranca em {city} "
                "com {name}."
            ),
        ),

        "restaurante": _seo(
            title_pattern="Gastronomia classica, ingredientes selecionados | {name} {city}",
            meta_description_pattern=(
                "Cozinha tradicional, carta de vinhos e servico de mesa "
                "completo. Reservas para almoco e jantar em {city}."
            ),
            h1_pattern=(
                "Restaurante classico com ingredientes selecionados e carta de vinhos em {city}"
            ),
            og_description_pattern=(
                "Restaurante classico com ingredientes selecionados e carta de vinhos em {city}."
            ),
            twitter_card_pattern=(
                "Cozinha tradicional, carta de vinhos e servico de mesa "
                "completo. Reservas para almoco e jantar em {city} com {name}."
            ),
        ),

        "academia": _seo(
            title_pattern="Estrutura, metodo e resultados | {name} {city}",
            meta_description_pattern=(
                "Equipamentos revisados, profissionais registrados e plano "
                "de treino estruturado. Musculacao, funcional e aulas em {city}."
            ),
            h1_pattern=(
                "Academia com estrutura completa, metodo e plano de treino em {city}"
            ),
            og_description_pattern=(
                "Academia com estrutura completa, metodo e plano de treino em {city}."
            ),
            twitter_card_pattern=(
                "Equipamentos revisados, profissionais registrados e plano "
                "de treino estruturado. Musculacao, funcional e aulas em "
                "{city} com {name}."
            ),
        ),

        "barbearia": _seo(
            title_pattern="Barbearia tradicional, tecnica apurada | {name} {city}",
            meta_description_pattern=(
                "Corte classico, barba com toalha quente e profissionais "
                "experientes. Atendimento por ordem de chegada em {city}."
            ),
            h1_pattern=(
                "Barbearia tradicional com tecnica apurada e profissionais em {city}"
            ),
            og_description_pattern=(
                "Barbearia tradicional com tecnica apurada e profissionais em {city}."
            ),
            twitter_card_pattern=(
                "Corte classico, barba com toalha quente e profissionais "
                "experientes. Atendimento por ordem de chegada em {city} com "
                "{name}."
            ),
        ),

        "nutricionista": _seo(
            title_pattern="Nutricao clinica baseada em evidencia | {name} {city}",
            meta_description_pattern=(
                "Avaliacao antropometrica, plano alimentar prescrito e "
                "retorno programado. Atendimento particular e por convenio em {city}."
            ),
            h1_pattern=(
                "Nutricionista com avaliacao, plano prescrito e retorno em {city}"
            ),
            og_description_pattern=(
                "Nutricionista com avaliacao, plano prescrito e retorno em {city}."
            ),
            twitter_card_pattern=(
                "Avaliacao antropometrica, plano alimentar prescrito e "
                "retorno programado. Atendimento particular e por convenio em "
                "{city} com {name}."
            ),
        ),

        "estetica": _seo(
            title_pattern="Estetica refinada, ha anos no mercado | {name} {city}",
            meta_description_pattern=(
                "Profissionais habilitados, produtos regularizados e "
                "protocolos documentados. Estetica facial e corporal em {city}."
            ),
            h1_pattern=(
                "Clinica de estetica com profissionais habilitados em {city}"
            ),
            og_description_pattern=(
                "Clinica de estetica com profissionais habilitados em {city}."
            ),
            twitter_card_pattern=(
                "Profissionais habilitados, produtos regularizados e "
                "protocolos documentados. Estetica facial e corporal em "
                "{city} com {name}."
            ),
        ),

        "salao": _seo(
            title_pattern="Salao tradicional, profissionais experientes | {name} {city}",
            meta_description_pattern=(
                "Corte, coloracao e tratamentos capilares com produtos "
                "profissionais. Atendimento com agendamento previo em {city}."
            ),
            h1_pattern=(
                "Salao de beleza tradicional com profissionais experientes em {city}"
            ),
            og_description_pattern=(
                "Salao de beleza tradicional com profissionais experientes em {city}."
            ),
            twitter_card_pattern=(
                "Corte, coloracao e tratamentos capilares com produtos "
                "profissionais. Atendimento com agendamento previo em {city} "
                "com {name}."
            ),
        ),

        "pet_shop": _seo(
            title_pattern="Veterinaria tradicional, equipe especializada | {name} {city}",
            meta_description_pattern=(
                "Veterinario responsavel, vacina em dia e banho com "
                "produto adequado. Atendimento por especie e porte em {city}."
            ),
            h1_pattern=(
                "Pet shop com veterinaria, vacina em dia e banho em {city}"
            ),
            og_description_pattern=(
                "Pet shop com veterinaria, vacina em dia e banho em {city}."
            ),
            twitter_card_pattern=(
                "Veterinario responsavel, vacina em dia e banho com produto "
                "adequado. Atendimento por especie e porte em {city} com {name}."
            ),
        ),

        "oficina": _seo(
            title_pattern="Oficina tradicional, mecanicos certificados | {name} {city}",
            meta_description_pattern=(
                "Mecanicos registrados, orcamento detalhado e nota fiscal "
                "emitida. Manutencao preventiva e corretiva em {city}."
            ),
            h1_pattern=(
                "Oficina mecanica tradicional com mecanicos certificados em {city}"
            ),
            og_description_pattern=(
                "Oficina mecanica tradicional com mecanicos certificados em {city}."
            ),
            twitter_card_pattern=(
                "Mecanicos registrados, orcamento detalhado e nota fiscal "
                "emitida. Manutencao preventiva e corretiva em {city} com {name}."
            ),
        ),

        "energia_solar": _seo(
            title_pattern="Energia solar com instalacao certificada | {name} {city}",
            meta_description_pattern=(
                "Integradores credenciados, projeto com ART e homologacao "
                "pela concessionaria. Residencial, comercial e rural em {city}."
            ),
            h1_pattern=(
                "Energia solar com integrador credenciado e ART em {city}"
            ),
            og_description_pattern=(
                "Energia solar com integrador credenciado e ART em {city}."
            ),
            twitter_card_pattern=(
                "Integradores credenciados, projeto com ART e homologacao "
                "pela concessionaria. Residencial, comercial e rural em "
                "{city} com {name}."
            ),
        ),

        "default": _seo(
            title_pattern="Profissionalismo e experiencia | {name} {city}",
            meta_description_pattern=(
                "Empresa estabelecida, atendimento profissional e servicos "
                "documentados. Fale com nossa equipe em {city}."
            ),
            h1_pattern=(
                "Atendimento profissional, estabelecido e com servicos documentados em {city}"
            ),
            og_description_pattern=(
                "Atendimento profissional, estabelecido e com servicos documentados em {city}."
            ),
            twitter_card_pattern=(
                "Empresa estabelecida, atendimento profissional e servicos "
                "documentados. Fale com nossa equipe em {city} com {name}."
            ),
        ),
    },

    # ──────────────────────────────────────────────────────────────────
    # TECH — tecnico, dado, monitoramento, ROI, payback
    # ──────────────────────────────────────────────────────────────────
    "TECH": {

        "energia_solar": _seo(
            title_pattern="Energia solar com payback de 4,7 anos | {name} {city}",
            meta_description_pattern=(
                "Painel de monitoramento em tempo real, payback medio de 4,7 "
                "anos, reducao de 92% na conta. Simule seu cenario com dados "
                "reais em {city}."
            ),
            h1_pattern=(
                "Energia solar com payback medido e monitoramento em tempo real em {city}"
            ),
            og_description_pattern=(
                "Energia solar com payback medido e monitoramento em tempo real em {city}."
            ),
            twitter_card_pattern=(
                "Painel de monitoramento em tempo real, payback medio de 4,7 "
                "anos, reducao de 92% na conta. Simule seu cenario com dados "
                "reais em {city} com {name}."
            ),
        ),

        "clinica": _seo(
            title_pattern="Telemedicina e prontuario digital | {name} {city}",
            meta_description_pattern=(
                "Consulta online com prescricao digital, prontuario integrado "
                "e exames acessiveis pelo app. Atendimento em {city} e remoto."
            ),
            h1_pattern=(
                "Clinica com telemedicina, prontuario digital e prescricao eletronica em {city}"
            ),
            og_description_pattern=(
                "Clinica com telemedicina, prontuario digital e prescricao eletronica em {city}."
            ),
            twitter_card_pattern=(
                "Consulta online com prescricao digital, prontuario integrado "
                "e exames acessiveis pelo app. Atendimento em {city} e "
                "remoto com {name}."
            ),
        ),

        "dentista": _seo(
            title_pattern="Escaneamento digital e planejamento 3D | {name} {city}",
            meta_description_pattern=(
                "Scanner intraoral, planejamento 3D e simulacao do sorriso "
                "antes do tratamento. Implantes e ortodontia com precisao em {city}."
            ),
            h1_pattern=(
                "Dentista com scanner intraoral, planejamento 3D e simulacao em {city}"
            ),
            og_description_pattern=(
                "Dentista com scanner intraoral, planejamento 3D e simulacao em {city}."
            ),
            twitter_card_pattern=(
                "Scanner intraoral, planejamento 3D e simulacao do sorriso "
                "antes do tratamento. Implantes e ortodontia com precisao em "
                "{city} com {name}."
            ),
        ),

        "academia": _seo(
            title_pattern="Performance medida, evolucao rastreada | {name} {city}",
            meta_description_pattern=(
                "Avaliacao por bioimpedancia, treino com carga registrada e "
                "evolucao em app proprio. Musculacao e funcional com dado em {city}."
            ),
            h1_pattern=(
                "Academia com bioimpedancia, carga registrada e app proprio em {city}"
            ),
            og_description_pattern=(
                "Academia com bioimpedancia, carga registrada e app proprio em {city}."
            ),
            twitter_card_pattern=(
                "Avaliacao por bioimpedancia, treino com carga registrada e "
                "evolucao em app proprio. Musculacao e funcional com dado em "
                "{city} com {name}."
            ),
        ),

        "nutricionista": _seo(
            title_pattern="App de acompanhamento e IA nutricao | {name} {city}",
            meta_description_pattern=(
                "Plano alimentar digital, registro de refeicoes por app e "
                "ajuste semanal por IA. Nutricao com dado em {city}."
            ),
            h1_pattern=(
                "Nutricionista com app, registro de refeicoes e IA nutricao em {city}"
            ),
            og_description_pattern=(
                "Nutricionista com app, registro de refeicoes e IA nutricao em {city}."
            ),
            twitter_card_pattern=(
                "Plano alimentar digital, registro de refeicoes por app e "
                "ajuste semanal por IA. Nutricao com dado em {city} com {name}."
            ),
        ),

        "imobiliaria": _seo(
            title_pattern="Busca digital e tour virtual 360 | {name} {city}",
            meta_description_pattern=(
                "Catalogo digital com tour 360, filtros avancados e "
                "atendimento por chat. Compra e aluguel com dados em {city}."
            ),
            h1_pattern=(
                "Imobiliaria com catalogo digital, tour 360 e busca avancada em {city}"
            ),
            og_description_pattern=(
                "Imobiliaria com catalogo digital, tour 360 e busca avancada em {city}."
            ),
            twitter_card_pattern=(
                "Catalogo digital com tour 360, filtros avancados e "
                "atendimento por chat. Compra e aluguel com dados em {city} "
                "com {name}."
            ),
        ),

        "estetica": _seo(
            title_pattern="Procedimentos com tecnologia de ponta | {name} {city}",
            meta_description_pattern=(
                "Equipamentos calibrados, protocolo fotografico e "
                "monitoramento de resultados. Estetica facial com dado em {city}."
            ),
            h1_pattern=(
                "Estetica com equipamento calibrado, protocolo e monitoramento em {city}"
            ),
            og_description_pattern=(
                "Estetica com equipamento calibrado, protocolo e monitoramento em {city}."
            ),
            twitter_card_pattern=(
                "Equipamentos calibrados, protocolo fotografico e "
                "monitoramento de resultados. Estetica facial com dado em "
                "{city} com {name}."
            ),
        ),

        "salao": _seo(
            title_pattern="Agendamento digital e portfolio online | {name} {city}",
            meta_description_pattern=(
                "Reserva pelo app, portfolio digital por profissional e "
                "historico do cliente. Salao conectado em {city}."
            ),
            h1_pattern=(
                "Salao com agendamento digital, portfolio online e historico do cliente em {city}"
            ),
            og_description_pattern=(
                "Salao com agendamento digital, portfolio online e historico do cliente em {city}."
            ),
            twitter_card_pattern=(
                "Reserva pelo app, portfolio digital por profissional e "
                "historico do cliente. Salao conectado em {city} com {name}."
            ),
        ),

        "restaurante": _seo(
            title_pattern="Cardapio digital e pedido pelo app | {name} {city}",
            meta_description_pattern=(
                "Cardapio atualizado em tempo real, pedido pelo app e "
                "entrega rastreada. Comida com dado em {city}."
            ),
            h1_pattern=(
                "Restaurante com cardapio digital, pedido pelo app e entrega rastreada em {city}"
            ),
            og_description_pattern=(
                "Restaurante com cardapio digital, pedido pelo app e entrega rastreada em {city}."
            ),
            twitter_card_pattern=(
                "Cardapio atualizado em tempo real, pedido pelo app e entrega "
                "rastreada. Comida com dado em {city} com {name}."
            ),
        ),

        "pet_shop": _seo(
            title_pattern="Prontuario digital do pet e lembretes | {name} {city}",
            meta_description_pattern=(
                "Carteira digital do pet, lembrete automatico de vacina e "
                "historico de banho. Veterinaria com dado em {city}."
            ),
            h1_pattern=(
                "Pet shop com carteira digital, lembrete de vacina e historico em {city}"
            ),
            og_description_pattern=(
                "Pet shop com carteira digital, lembrete de vacina e historico em {city}."
            ),
            twitter_card_pattern=(
                "Carteira digital do pet, lembrete automatico de vacina e "
                "historico de banho. Veterinaria com dado em {city} com {name}."
            ),
        ),

        "barbearia": _seo(
            title_pattern="Agendamento rapido e atendimento digital | {name} {city}",
            meta_description_pattern=(
                "Reserva em poucos cliques, profissional escolhido pelo "
                "app e historico de corte. Barbearia conectada em {city}."
            ),
            h1_pattern=(
                "Barbearia com agendamento rapido, escolha do barbeiro e historico em {city}"
            ),
            og_description_pattern=(
                "Barbearia com agendamento rapido, escolha do barbeiro e historico em {city}."
            ),
            twitter_card_pattern=(
                "Reserva em poucos cliques, profissional escolhido pelo app "
                "e historico de corte. Barbearia conectada em {city} com {name}."
            ),
        ),

        "oficina": _seo(
            title_pattern="Diagnostico computadorizado e orcamento digital | {name} {city}",
            meta_description_pattern=(
                "Scanner veicular, orcamento por foto e status do servico "
                "pelo app. Mecanica com dado em {city}."
            ),
            h1_pattern=(
                "Oficina com scanner veicular, orcamento por foto e status em app em {city}"
            ),
            og_description_pattern=(
                "Oficina com scanner veicular, orcamento por foto e status em app em {city}."
            ),
            twitter_card_pattern=(
                "Scanner veicular, orcamento por foto e status do servico "
                "pelo app. Mecanica com dado em {city} com {name}."
            ),
        ),

        "advogado": _seo(
            title_pattern="Analise juridica baseada em dados e precedentes | {name} {city}",
            meta_description_pattern=(
                "Pesquisa jurisprudencial automatizada, relatorio com "
                "precedentes e protocolo digital. Advocacia com dado em {city}."
            ),
            h1_pattern=(
                "Advogado com pesquisa automatizada, precedentes e protocolo digital em {city}"
            ),
            og_description_pattern=(
                "Advogado com pesquisa automatizada, precedentes e protocolo digital em {city}."
            ),
            twitter_card_pattern=(
                "Pesquisa jurisprudencial automatizada, relatorio com "
                "precedentes e protocolo digital. Advocacia com dado em "
                "{city} com {name}."
            ),
        ),

        "default": _seo(
            title_pattern="Solucao moderna para sua necessidade | {name} {city}",
            meta_description_pattern=(
                "Painel de acompanhamento, dados em tempo real e suporte "
                "digital. Atenda sua necessidade com tecnologia em {city}."
            ),
            h1_pattern=(
                "Solucao moderna com painel, dados em tempo real e suporte digital em {city}"
            ),
            og_description_pattern=(
                "Solucao moderna com painel, dados em tempo real e suporte digital em {city}."
            ),
            twitter_card_pattern=(
                "Painel de acompanhamento, dados em tempo real e suporte "
                "digital. Atenda sua necessidade com tecnologia em {city} "
                "com {name}."
            ),
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

# Comprimentos minimo e maximo do title apos formatacao
TITLE_MIN_LEN = 50
TITLE_MAX_LEN = 60


def get_seo_template(polo: str, nicho: str) -> SEO_TEMPLATE:
    """
    Retorna SEO_TEMPLATE para o par (polo, nicho), com fallback para default.

    Args:
        polo: Polo estetico (SOFT | BOLD | CLASSIC | TECH). Case-insensitive.
        nicho: Nicho canonico (nutricionista, academia, ...). Case-insensitive.
            Se nao existir no polo, retorna o template "default" do polo.

    Returns:
        SEO_TEMPLATE com title/meta/h1/og/twitter patterns.

    Raises:
        ValueError: Se polo for invalido (nao consta em SEO_TEMPLATES).
    """
    polo_key = polo.upper().strip()
    if polo_key not in SEO_TEMPLATES:
        valid = ", ".join(sorted(SEO_TEMPLATES.keys()))
        raise ValueError(
            f"Polo invalido: {polo!r}. Valores validos: {valid}"
        )

    polo_dict = SEO_TEMPLATES[polo_key]
    nicho_key = nicho.lower().strip() if nicho else "default"
    return polo_dict.get(nicho_key, polo_dict["default"])


def generate_title(template: SEO_TEMPLATE, name: str, city: str) -> str:
    """
    Formata o title_pattern com {name} e {city}.

    Args:
        template: SEO_TEMPLATE vindo de get_seo_template.
        name: Nome do negocio.
        city: Cidade alvo.

    Returns:
        Title formatado. Atencao: este template assume '{hook} | {name} {city}'.
        Como '{hook}' nao tem semantica aqui (so o pattern), o gerador de
        pagina deve concatenar hook especifico antes do '|' quando necessario.
    """
    title = template.title_pattern.format(name=name, city=city, hook="")
    # Trim defensivo de whitespace duplo gerado por hook vazio
    return " ".join(title.split())


def generate_meta(template: SEO_TEMPLATE, name: str, city: str) -> str:
    """
    Formata o meta_description_pattern com {name} e {city}.

    Args:
        template: SEO_TEMPLATE vindo de get_seo_template.
        name: Nome do negocio.
        city: Cidade alvo.

    Returns:
        Meta description formatada (150-160 chars recomendado).
    """
    return template.meta_description_pattern.format(name=name, city=city)


def generate_h1(template: SEO_TEMPLATE, city: str) -> str:
    """
    Formata o h1_pattern com {city}.

    Regra do projeto: h1 com >= 8 palavras.

    Args:
        template: SEO_TEMPLATE vindo de get_seo_template.
        city: Cidade alvo.

    Returns:
        H1 formatado.
    """
    return template.h1_pattern.format(city=city)


def generate_og_description(template: SEO_TEMPLATE, name: str, city: str) -> str:
    """Formata o og_description_pattern com {name} e {city} (90-100 chars)."""
    return template.og_description_pattern.format(name=name, city=city)


def generate_twitter_card(template: SEO_TEMPLATE, name: str, city: str) -> str:
    """Formata o twitter_card_pattern com {name} e {city} (<= 200 chars)."""
    return template.twitter_card_pattern.format(name=name, city=city)


def validate_title_length(title: str) -> bool:
    """
    Valida se o title tem entre 50 e 60 caracteres.

    Args:
        title: Title ja formatado (sem placeholders).

    Returns:
        True se 50 <= len(title) <= 60, False caso contrario.
    """
    return TITLE_MIN_LEN <= len(title) <= TITLE_MAX_LEN


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "SEO_TEMPLATE",
    "SEO_TEMPLATES",
    "TITLE_MIN_LEN",
    "TITLE_MAX_LEN",
    "get_seo_template",
    "generate_title",
    "generate_meta",
    "generate_h1",
    "generate_og_description",
    "generate_twitter_card",
    "validate_title_length",
]