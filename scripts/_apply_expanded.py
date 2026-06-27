#!/usr/bin/env python3
"""Apply expanded 19-segment block to vite_react_renderer.py."""
with open('C:/fralib/backend/services/vite_react_renderer.py', encoding='utf-8') as f:
    c = f.read()

new_block = '''
    if "barbearia" in segment or "barbeiro" in segment:
        svc_labels = ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"]
        hero_desc = "Barbearia premium com barbeiros experientes e ambiente climatizado."
        cta_primary = "Agendar horario"
        cta_secondary = "Ver servicos"
        alt_img = "Barbeiro em barbearia"
        lifestyle_title = "Tradicao em cada corte"
        lifestyle_desc = "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "academia" in segment or "fitness" in segment or "musculacao" in segment or "crossfit" in segment:
        svc_labels = ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"]
        hero_desc = "Academia completa com treino funcional, alunos acompanhados e ambiente moderno."
        cta_primary = "Comecar treino"
        cta_secondary = "Ver estrutura"
        alt_img = "Alunos em treino fitness"
        lifestyle_title = "Energia e constancia"
        lifestyle_desc = "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar."
        nav_items = [("Treinos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "restaurante" in segment or "bar " in segment or "pizzaria" in segment or "hamburgueria" in segment or "lanchonete" in segment or "cafeteria" in segment:
        svc_labels = ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"]
        hero_desc = "Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor."
        cta_primary = "Fazer reserva"
        cta_secondary = "Ver menu"
        alt_img = "Restaurante"
        lifestyle_title = "Experiencia gastronomica"
        lifestyle_desc = "Cada prato preparado com cuidado para proporcionar uma experiencia unica."
        nav_items = [("Cardapio", "#servicos"), ("Galeria", "#galeria"), ("Reservar", "#contato")]
    elif "clinica" in segment or "estetica" in segment or "dermatologia" in segment:
        svc_labels = ["Consulta", "Tratamento", "Avaliacao", "Procedimento", "Retorno"]
        hero_desc = "Clinica com profissionais experientes e tratamentos personalizados para seu bem-estar."
        cta_primary = "Agendar consulta"
        cta_secondary = "Conhecer servicos"
        alt_img = "Clinica"
        lifestyle_title = "Cuidado e acolhimento"
        lifestyle_desc = "Ambiente preparado para recebe-lo com conforto e seguranca em cada atendimento."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "imobiliaria" in segment or "imoveis" in segment:
        svc_labels = ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"]
        hero_desc = "Imobiliaria com imoveis selecionados e atendimento personalizado para suas necessidades."
        cta_primary = "Ver imoveis"
        cta_secondary = "Falar corretor"
        alt_img = "Imovel"
        lifestyle_title = "Seu proximo imovel"
        lifestyle_desc = "Encontre o imovel ideal com quem entende do mercado local."
        nav_items = [("Imoveis", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "nutricionista" in segment or "nutricao" in segment:
        svc_labels = ["Avaliacao", "Plano alimentar", "Acompanhamento", "Suplementacao", "Bioimpedancia"]
        hero_desc = "Nutricionista com plano alimentar personalizado para seus objetivos de saude."
        cta_primary = "Agendar consulta"
        cta_secondary = "Ver planos"
        alt_img = "Nutricionista"
        lifestyle_title = "Nutricao de verdade"
        lifestyle_desc = "Transforme sua alimentacao com acompanhamento profissional cientifico."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "advocacia" in segment or "advogado" in segment:
        svc_labels = ["Consulta", "Contratos", "Processos", "Assessoria", "Recursos"]
        hero_desc = "Escritorio de advocacia com experiencia em diversas areas do direito."
        cta_primary = "Falar com advogado"
        cta_secondary = "Ver areas"
        alt_img = "Escritorio de advocacia"
        lifestyle_title = "Direito com seriedade"
        lifestyle_desc = "Atendimento juridico transparente e dedicado a sua causa."
        nav_items = [("Areas", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "odonto" in segment or "dentista" in segment:
        svc_labels = ["Limpeza", "Clareamento", "Implante", "Ortodontia", "Emergencia"]
        hero_desc = "Odontologia com tratamentos modernos e atendimento humanizado."
        cta_primary = "Agendar consulta"
        cta_secondary = "Ver tratamentos"
        alt_img = "Consultorio odontologico"
        lifestyle_title = "Seu sorriso perfeito"
        lifestyle_desc = "Tecnologia de ponta e carinho em cada tratamento para seu sorriso."
        nav_items = [("Tratamentos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "ecommerce" in segment or "loja" in segment or "roupas" in segment:
        svc_labels = ["Produtos", "Frete", "Troca", "Atendimento", "Garantia"]
        hero_desc = "Loja online com produtos selecionados e entrega para todo o Brasil."
        cta_primary = "Ver produtos"
        cta_secondary = "Ver ofertas"
        alt_img = "Produtos"
        lifestyle_title = "Qualidade garantida"
        lifestyle_desc = "Produtos selecionados com cuidado para atender suas necessidades."
        nav_items = [("Produtos", "#servicos"), ("Ofertas", "#galeria"), ("Contato", "#contato")]
    elif "petshop" in segment or "pet " in segment:
        svc_labels = ["Banho", "Tosa", "Consulta", "Produtos", "Creche"]
        hero_desc = "Pet shop com produtos e servicos para o bem-estar do seu pet."
        cta_primary = "Agendar servico"
        cta_secondary = "Ver produtos"
        alt_img = "Pet shop"
        lifestyle_title = "Amor pelos animais"
        lifestyle_desc = "Cuidamos do seu pet como se fosse nosso. Amor e dedicacao em cada servico."
        nav_items = [("Servicos", "#servicos"), ("Produtos", "#galeria"), ("Contato", "#contato")]
    elif "hotel" in segment or "pousada" in segment or "hostel" in segment:
        svc_labels = ["Quartos", "Cafe da manha", "Estacionamento", "Wi-Fi", "Piscina"]
        hero_desc = "Hospedagem com conforto, localizacao privilegiada e atendimento diferenciado."
        cta_primary = "Reservar"
        cta_secondary = "Ver quartos"
        alt_img = "Hotel"
        lifestyle_title = "Sua casa longe de casa"
        lifestyle_desc = "Conforto e acolhimento para tornar sua estadia inesquecivel."
        nav_items = [("Quartos", "#servicos"), ("Servicos", "#galeria"), ("Reservar", "#contato")]
    elif "salao_beleza" in segment or "beleza" in segment or "manicure" in segment or "cabelo" in segment:
        svc_labels = ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"]
        hero_desc = "Salao de beleza com profissionais capacitados e ambiente acolhedor."
        cta_primary = "Agendar horario"
        cta_secondary = "Ver servicos"
        alt_img = "Salao de beleza"
        lifestyle_title = "Beleza e bem-estar"
        lifestyle_desc = "Transformamos seu visual com tecnicas modernas e produtos de qualidade."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "fisioterapia" in segment or "fisio" in segment:
        svc_labels = ["Avaliacao", "Tratamento", "RPG", "Acupuntura", "Pilates"]
        hero_desc = "Fisioterapia com atendimento personalizado para reabilitacao e qualidade de vida."
        cta_primary = "Agendar sessao"
        cta_secondary = "Ver tratamentos"
        alt_img = "Fisioterapia"
        lifestyle_title = "Movimento com saude"
        lifestyle_desc = "Recupere sua qualidade de vida com tratamento fisioterapêutico humanizado."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "escola" in segment or "cursinho" in segment or "idiomas" in segment or "musica" in segment or "informatica" in segment:
        svc_labels = ["Matricula", "Cursos", "Talleres", "Eventos", "Biblioteca"]
        hero_desc = "Instituicao de ensino com metodologia moderna e corpo docente qualificado."
        cta_primary = "Matricular"
        cta_secondary = "Ver cursos"
        alt_img = "Escola"
        lifestyle_title = "Educacao que transforma"
        lifestyle_desc = "Formando cidadaos preparados para o futuro com excelencia e valores."
        nav_items = [("Cursos", "#servicos"), ("Eventos", "#galeria"), ("Contato", "#contato")]
    elif "autoescola" in segment:
        svc_labels = ["Aulas teoricas", "Aulas praticas", "Simulado", "Exame", "CNH"]
        hero_desc = "Autoescola com aprovacao garantida e atendimento moderno."
        cta_primary = "Matricular"
        cta_secondary = "Ver categorias"
        alt_img = "Autoescola"
        lifestyle_title = "Sua habilitacao na mao"
        lifestyle_desc = "Metodologia comprovada para voce passar no DETRAN de primeira."
        nav_items = [("Categorias", "#servicos"), ("Simulado", "#galeria"), ("Contato", "#contato")]
    elif "oficina" in segment or "mecanica" in segment or "eletrica" in segment or "pintura" in segment:
        svc_labels = ["Revisao", "Diagnostico", "Reparos", "Pintura", "Eletrica"]
        hero_desc = "Oficina mecanica com profissionais experientes e equipamentos modernos."
        cta_primary = "Agendar servico"
        cta_secondary = "Ver servicos"
        alt_img = "Oficina mecanica"
        lifestyle_title = "Seu carro em boas maos"
        lifestyle_desc = "Servico de qualidade com transparencia e compromisso com seu veiculo."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "farmacia" in segment or "manipulacao" in segment:
        svc_labels = ["Medicamentos", "Manipulacao", "Dermocosmeticos", "Atendimento", "Delivery"]
        hero_desc = "Farmacia com variedade de medicamentos e atendimento personalizado."
        cta_primary = "Ver produtos"
        cta_secondary = "Ver promocoes"
        alt_img = "Farmacia"
        lifestyle_title = "Saude e bem-estar"
        lifestyle_desc = "Farmacêuticos capacitados para orientar sobre medicamentos e cuidados."
        nav_items = [("Produtos", "#servicos"), ("Promocoes", "#galeria"), ("Contato", "#contato")]
    elif "psicologo" in segment or "psicologia" in segment:
        svc_labels = ["Consulta", "Terapia", "Avaliacao", "Diagnostico", "Acompanhamento"]
        hero_desc = "Psicologia com atendimento humanizado para suas necessidades emocionais."
        cta_primary = "Agendar sessao"
        cta_secondary = "Ver abordagens"
        alt_img = "Consultorio de psicologia"
        lifestyle_title = "Cuidado emocional"
        lifestyle_desc = "Um espaco seguro para falar sobre seus sentimentos e desenvolver seu potencial."
        nav_items = [("Abordagens", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "fotografo" in segment or "fotografia" in segment or "design" in segment or "grafico" in segment:
        svc_labels = ["Eventos", "Casamentos", "Books", "Corporativo", "Produtos"]
        hero_desc = "Fotografia com servicos para eventos, casamentos e books corporativos."
        cta_primary = "Ver portfolio"
        cta_secondary = "Fazer orcamento"
        alt_img = "Fotografia"
        lifestyle_title = "Momentos eternizados"
        lifestyle_desc = "Capturamos momentos e emocoes com sensibilidade e tecnica."
        nav_items = [("Portfolio", "#servicos"), ("Pacotes", "#galeria"), ("Contato", "#contato")]
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]

    else:
        svc_labels = ["Servico 1", "Servico 2", "Servico 3", "Servico 4", "Servico 5"]
        hero_desc = f"{name}: servicos de qualidade com atendimento personalizado em {city}."
        cta_primary = "Saiba mais"
        cta_secondary = "Ver servicos"
        alt_img = f"{name}"
        lifestyle_title = "Experiencia unica"
        lifestyle_desc = f"Atendimento dedicado para garantir sua satisfacao em {city}."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]

    # END of segment-aware block - def component follows'''

# Find boundaries
old_start = '    if "barbearia" in segment or "barbeiro" in segment:'
old_end = '    def component('

old_start_idx = c.find(old_start)
old_end_idx = c.find(old_end)

if old_start_idx < 0 or old_end_idx < 0:
    print(f'ERROR: start={old_start_idx}, end={old_end_idx}')
    for kw in ['barbearia', 'academia', 'def component']:
        idx = c.find(kw)
        print(f'  {kw[:40]}: {idx}')
else:
    before = c[:old_start_idx]
    after = "\n" + c[old_end_idx:]  # prepend newline to avoid joining
    new_c = before + new_block + after

    try:
        compile(new_c, 'vite_react_renderer.py', 'exec')
        # Count segments
        n = new_block.count('\n    elif ') + (1 if '\n    if ' in new_block else 0)
        print(f'SYNTAX: OK ({len(new_c)} chars, delta: {len(new_c)-len(c):+d})')
        print(f'SEGMENTS: {n} elif branches + 1 if + 1 else = {n+2} total')
        with open('C:/fralib/backend/services/vite_react_renderer.py', 'w', encoding='utf-8') as f:
            f.write(new_c)
        print('WRITTEN OK')
    except SyntaxError as e:
        print(f'SYNTAX ERROR line {e.lineno}: {e.msg}')
        print(e.text)
