#!/usr/bin/env python3
"""Sprint 12.15: Expand ALL segments + parallel smoke tests."""
import subprocess, sys, os

# All segments + sub-segments FraLib
SEGMENTS = [
    # (keyword, label, cta_primary, cta_secondary, hero_desc, svc_labels, alt_img, lifestyle_title, lifestyle_desc, nav_labels)
    ("barbearia", "barbearia", "Agendar horario", "Ver servicos",
     "Barbearia premium com barbeiros experientes e ambiente climatizado.",
     ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"],
     "Barbeiro em barbearia", "Tradicao em cada corte",
     "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes.",
     ["Servicos", "Galeria", "Contato"]),

    ("academia", "academia", "Comecar treino", "Ver estrutura",
     "Academia completa com treino funcional, alunos acompanhados e ambiente moderno.",
     ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"],
     "Alunos em treino fitness", "Energia e constancia",
     "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar.",
     ["Treinos", "Galeria", "Contato"]),

    ("restaurante", "restaurante", "Fazer reserva", "Ver menu",
     "Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor.",
     ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"],
     "Restaurante", "Experiencia gastronomica",
     "Cada prato preparado com cuidado para proporcionar uma experiencia unica.",
     ["Cardapio", "Galeria", "Reservar"]),

    ("clinica", "clinica", "Agendar consulta", "Conhecer servicos",
     "Clinica com profissionais experientes e tratamentos personalizados para seu bem-estar.",
     ["Consulta", "Tratamento", "Avaliacao", "Procedimento", "Retorno"],
     "Clinica", "Cuidado e acolhimento",
     "Ambiente preparado para recebe-lo com conforto e seguranca em cada atendimento.",
     ["Servicos", "Galeria", "Contato"]),

    ("imobiliaria", "imobiliaria", "Ver imoveis", "Falar corretor",
     "Imobiliaria com imoveis selecionados e atendimento personalizado para suas necessidades.",
     ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"],
     "Imovel", "Seu proximo imovel",
     "Encontre o imovel ideal com quem entende do mercado local.",
     ["Imoveis", "Galeria", "Contato"]),

    ("nutricionista", "nutricionista", "Agendar consulta", "Ver planos",
     "Nutricionista com plano alimentar personalizado para seus objetivos de saude.",
     ["Avaliacao", "Plano alimentar", "Acompanhamento", "Suplementacao", "Bioimpedancia"],
     "Nutricionista", "Nutricao de verdade",
     "Transforme sua alimentacao com acompanhamento profissional cientifico.",
     ["Servicos", "Galeria", "Contato"]),

    ("advocacia", "advocacia", "Falar com advogado", "Ver areas",
     "Escritorio de advocacia com experiencia em diversas areas do direito.",
     ["Consulta", "Contratos", "Processos", "Assessoria", "Recursos"],
     "Escritorio de advocacia", "Direito com seriedade",
     "Atendimento juridico transparente e dedicado a sua causa.",
     ["Areas", "Galeria", "Contato"]),

    ("ecommerce", "ecommerce", "Ver produtos", "Ver ofertas",
     "Loja online com produtos selecionados e entrega para todo o Brasil.",
     ["Produtos", "Frete", "Troca", "Atendimento", "Garantia"],
     "Produtos", "Qualidade garantida",
     "Produtos selecionados com cuidado para atender suas necessidades.",
     ["Produtos", "Ofertas", "Contato"]),

    ("petshop", "petshop", "Agendar servico", "Ver produtos",
     "Pet shop com produtos e servicos para o bem-estar do seu pet.",
     ["Banho", "Tosa", "Consulta", "Produtos", "Creche"],
     "Pet shop", "Amor pelos animais",
     "Cuidamos do seu pet como se fosse nosso. Amor e dedicacao em cada servico.",
     ["Servicos", "Produtos", "Contato"]),

    ("hotel", "hotel", "Reservar", "Ver quartos",
     "Hospedagem com conforto, localizacao privilegiada e atendimento diferenciado.",
     ["Quartos", "Cafe da manha", "Estacionamento", "Wi-Fi", "Piscina"],
     "Hotel", "Sua casa longe de casa",
     "Conforto e acolhimento para tornar sua estadia inesquecivel.",
     ["Quartos", "Servicos", "Reservar"]),

    ("salao_beleza", "salao_beleza", "Agendar horario", "Ver servicos",
     "Salao de beleza com profissionais capacitados e ambiente acolhedor.",
     ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"],
     "Salao de beleza", "Beleza e bem-estar",
     "Transformamos seu visual com tecnicas modernas e produtos de qualidade.",
     ["Servicos", "Galeria", "Contato"]),

    ("fisioterapia", "fisioterapia", "Agendar sessao", "Ver tratamentos",
     "Fisioterapia com atendimento personalizado para reabilitacao e qualidade de vida.",
     ["Avaliacao", "Tratamento", "RPG", "Acupuntura", "Pilates"],
     "Fisioterapia", "Movimento com saude",
     "Recupere sua qualidade de vida com tratamento fisioterapêutico humanizado.",
     ["Servicos", "Galeria", "Contato"]),

    ("escola", "escola", "Matricular", "Ver cursos",
     "Instituicao de ensino com metodologia moderna e corpo docente qualificado.",
     ["Matricula", "Cursos", "Talleres", "Eventos", "Biblioteca"],
     "Escola", "Educacao que transforma",
     "Formando cidadaos preparados para o futuro com excelencia e valores.",
     ["Cursos", "Eventos", "Contato"]),

    ("autoescola", "autoescola", "Matricular", "Ver categorias",
     "Autoescola com aprovacao garantida e atendimento moderno.",
     ["Aulas teoricas", "Aulas praticas", "Simulado", "Exame", "CNH"],
     "Autoescola", "Sua habilitacao na mao",
     "Metodologia comprovada para voce passar no DETRAN de primeira.",
     ["Categorias", "Simulado", "Contato"]),

    ("oficina", "oficina", "Agendar servico", "Ver servicos",
     "Oficina mecanica com profissionais experientes e equipamentos modernos.",
     ["Revisao", "Diagnostico", "Reparos", "Pintura", "Eletrica"],
     "Oficina mecanica", "Seu carro em boas maos",
     "Servico de qualidade com transparencia e compromisso com seu veiculo.",
     ["Servicos", "Galeria", "Contato"]),

    ("farmacia", "farmacia", "Ver produtos", "Ver promocoes",
     "Farmacia com variedade de medicamentos e atendimento personalizado.",
     ["Medicamentos", "Manipulacao", "Dermocosmeticos", "Atendimento", "Delivery"],
     "Farmacia", "Saude e bem-estar",
     "Farmacêuticos capacitados para orientar sobre medicamentos e cuidados.",
     ["Produtos", "Promocoes", "Contato"]),

    ("crossfit", "crossfit", "Comecar treino", "Ver box",
     "Box de CrossFit com estrutura completa e coaches certificados.",
     ["WOD", "Treino funcional", "Halterofilismo", "Gymnastics", "Avaliacao"],
     "CrossFit box", "CrossFit comunidade",
     "Uma comunidade dedicada ao fitness funcional e superacao diaria.",
     ["WOD", "Galeria", "Contato"]),

    ("pizzaria", "pizzaria", "Fazer pedido", "Ver cardapio",
     "Pizzaria com pizzas artesanais feitas com ingredientes selecionados.",
     ["Pizzas", "Bebidas", "Sobremesas", "Entrega", "Reservas"],
     "Pizzaria", "Pizza artesanal",
     "Massa fresca e ingredientes selecionados para uma pizza perfeita.",
     ["Cardapio", "Pedidos", "Contato"]),

    ("hamburgueria", "hamburgueria", "Fazer pedido", "Ver cardapio",
     "Hamburgueria artesanal com recipes exclusivas e ambiente descolado.",
     ["Hamburgueres", "Porcoes", "Bebidas", "Sobremesas", "Delivery"],
     "Hamburgueria artesanal", "Artesanal e irresistivel",
     "Carne de qualidade, paes fresquinhos e molhos da casa.",
     ["Cardapio", "Pedidos", "Contato"]),

    ("cafeteria", "cafeteria", "Ver cardapio", "Reservar espaco",
     "Cafeteria com cafes especiais e ambiente aconchegante para trabalho ou encontro.",
     ["Cafes", "Bebidas", "Salgados", "Doces", "Almocos"],
     "Cafeteria", "O melhor do cafe",
     "Graos selecionados e preparo Artesanal para o cafe perfeito.",
     ["Cardapio", "Eventos", "Contato"]),

    ("barbearia_premium", "barbearia_premium", "Agendar horario", "Ver servicos",
     "Barbearia premium com servicos exclusivos e ambiente sofisticado.",
     ["Corte", "Barba", "Pigmentacao", "Tratamento", "Hidratacao"],
     "Barbearia premium", "Premium experiencia",
     "Um espaco exclusivo para o homem moderno que valoriza estilo e qualidade.",
     ["Servicos", "Galeria", "Contato"]),

    ("dentista", "dentista", "Agendar consulta", "Ver tratamentos",
     "Odontologia com tratamentos modernos e atendimento humanizado.",
     ["Limpeza", "Clareamento", "Implante", "Ortodontia", "Emergencia"],
     "Consultorio odontologico", "Seu sorriso perfecto",
     "Tecnologia de ponta e carinho em cada tratamento para seu sorriso.",
     ["Tratamentos", "Galeria", "Contato"]),

    ("psicologo", "psicologo", "Agendar sessao", "Ver abordagens",
     "Psicologia com atendimento humanizado para suas necessidades emocionais.",
     ["Consulta", "Terapia", "Avaliacao", "Diagnostico", "Acompanhamento"],
     "Consultorio de psicologia", "Cuidado emocional",
     "Um espaco seguro para falar sobre seus sentimentos e desenvolver seu potencial.",
     ["Abordagens", "Galeria", "Contato"]),

    (" Dermatologia", "dermatologia", "Agendar consulta", "Ver tratamentos",
     "Dermatologia com tratamentos esteticos e clinicos para sua pele.",
     ["Consulta", "Tratamento", "Estetica", "Procedimentos", "Mapeamento"],
     "Dermatologia", "Pele saudavel",
     "Diagnostico e tratamento especializado para todas as necessidades da sua pele.",
     ["Tratamentos", "Estetica", "Contato"]),

    ("design", "design", "Ver portfolio", "Falar comigo",
     "Design com solucoes criativas para sua marca ou projeto.",
     ["Identidade visual", "Web design", "UI/UX", "Redes sociais", "Impressos"],
     "Design", "Criatividade que transforma",
     "Projetos que comunicam sua essencia e conectam com seu pubblico.",
     ["Portfolio", "Servicos", "Contato"]),

    ("fotografo", "fotografo", "Ver portfolio", "Fazer orcamento",
     "Fotografia com servicos para eventos, casamentos eBOOKs corporativos.",
     ["Eventos", "Casamentos", "Books", "Corporativo", "Produtos"],
     "Fotografia", "Momentos eternizados",
     "Capturamos momentos e emocoes com sensibilidade e tecnica.",
     ["Portfolio", "Pacotes", "Contato"]),
]

# Keywords that map to each segment (order matters: most specific first)
SEGMENT_MAP = [
    ("barbearia_premium", "barbearia_premium", "Agendar horario", "Ver servicos",
     "Barbearia premium com servicos exclusivos e ambiente sofisticado.",
     ["Corte", "Barba", "Pigmentacao", "Tratamento", "Hidratacao"],
     "Barbearia premium", "Premium experiencia",
     "Um espaco exclusivo para o homem moderno.",
     ["Servicos", "Galeria", "Contato"]),
    ("barbearia", "barbearia", "Agendar horario", "Ver servicos",
     "Barbearia premium com barbeiros experientes e ambiente climatizado.",
     ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"],
     "Barbeiro em barbearia", "Tradicao em cada corte",
     "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes.",
     ["Servicos", "Galeria", "Contato"]),
    ("barbeiro", "barbearia", "Agendar horario", "Ver servicos",
     "Barbearia premium com barbeiros experientes.",
     ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"],
     "Barbeiro em barbearia", "Tradicao em cada corte",
     "Um espaco dedicado ao cuidado masculino.",
     ["Servicos", "Galeria", "Contato"]),
    ("academia", "academia", "Comecar treino", "Ver estrutura",
     "Academia completa com treino funcional, alunos acompanhados e ambiente moderno.",
     ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"],
     "Alunos em treino fitness", "Energia e constancia",
     "Um espaco para criar rotina, encontrar orientacao e manter frequencia.",
     ["Treinos", "Galeria", "Contato"]),
    ("fitness", "academia", "Comecar treino", "Ver estrutura",
     "Academia completa com treino funcional.",
     ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"],
     "Academia fitness", "Energia e constancia",
     "Um espaco para transformar seu corpo e sua vida.",
     ["Treinos", "Galeria", "Contato"]),
    ("crossfit", "crossfit", "Comecar treino", "Ver box",
     "Box de CrossFit com estrutura completa e coaches certificados.",
     ["WOD", "Treino funcional", "Halterofilismo", "Gymnastics", "Avaliacao"],
     "CrossFit box", "CrossFit comunidade",
     "Uma comunidade dedicada ao fitness funcional e superacao diaria.",
     ["WOD", "Galeria", "Contato"]),
    ("musculacao", "academia", "Comecar treino", "Ver estrutura",
     "Academia com musculacao orientada por profissionais.",
     ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"],
     "Academia musculacao", "Energia e constancia",
     "Equipamentos modernos e acompanhamento profissional.",
     ["Treinos", "Galeria", "Contato"]),
    ("restaurante", "restaurante", "Fazer reserva", "Ver menu",
     "Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor.",
     ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"],
     "Restaurante", "Experiencia gastronomica",
     "Cada prato preparado com cuidado para proporcionar uma experiencia unica.",
     ["Cardapio", "Galeria", "Reservar"]),
    ("pizzaria", "pizzaria", "Fazer pedido", "Ver cardapio",
     "Pizzaria artesanal com massas frescas e ingredientes selecionados.",
     ["Pizzas", "Bebidas", "Sobremesas", "Entrega", "Reservas"],
     "Pizzaria", "Pizza artesanal",
     "Massa fresca e ingredientes selecionados para uma pizza perfeita.",
     ["Cardapio", "Pedidos", "Contato"]),
    ("hamburgueria", "hamburgueria", "Fazer pedido", "Ver cardapio",
     "Hamburgueria artesanal com receitas exclusivas.",
     ["Hamburgueres", "Porcoes", "Bebidas", "Sobremesas", "Delivery"],
     "Hamburgueria artesanal", "Artesanal e irresistivel",
     "Carne de qualidade, paes fresquinhos e molhos da casa.",
     ["Cardapio", "Pedidos", "Contato"]),
    ("lanchonete", "restaurante", "Fazer pedido", "Ver cardapio",
     "Lanchonete com lanches feitos na hora e ambiente familiar.",
     ["Lanches", "Bebidas", "Porcoes", "Sobremesas", "Delivery"],
     "Lanchonete", "Lanches na hora",
     "Lanches fresquinhos feitos com ingredientes de qualidade.",
     ["Cardapio", "Pedidos", "Contato"]),
    ("bar", "restaurante", "Ver cardapio", "Reservar",
     "Bar com drinks especiais e ambiente descontraido.",
     ["Drinks", "Cervejas", "Porcoes", "Shows", "Reservas"],
     "Bar", "Boa conversa",
     "Ambiente descontraido para reunir amigos e famille.",
     ["Cardapio", "Eventos", "Contato"]),
    ("cafeteria", "cafeteria", "Ver cardapio", "Reservar espaco",
     "Cafeteria com cafes especiais e ambiente aconchegante.",
     ["Cafes", "Bebidas", "Salgados", "Doces", "Almocos"],
     "Cafeteria", "O melhor do cafe",
     "Graos selecionados e preparo Artesanal para o cafe perfeito.",
     ["Cardapio", "Eventos", "Contato"]),
    ("clinica", "clinica", "Agendar consulta", "Conhecer servicos",
     "Clinica com profissionais experientes e tratamentos personalizados.",
     ["Consulta", "Tratamento", "Avaliacao", "Procedimento", "Retorno"],
     "Clinica", "Cuidado e acolhimento",
     "Ambiente preparado para recebe-lo com conforto e seguranca.",
     ["Servicos", "Galeria", "Contato"]),
    ("estetica", "clinica", "Agendar horario", "Ver tratamentos",
     "Clinica estetica com tratamentos modernos para seu bem-estar.",
     ["Tratamentos", "Estetica", "Avaliacao", "Procedimentos", "Skin care"],
     "Clinica estetica", "Beleza e saude",
     "Tratamentos esteticos com tecnologia e cuidado personalizado.",
     ["Tratamentos", "Galeria", "Contato"]),
    ("medic", "clinica", "Agendar consulta", "Ver especialidades",
     "Clinica medica com diversas especialidades e atendimento humanizado.",
     ["Consulta", "Exames", "Especialidades", "Procedimentos", "Urgencia"],
     "Clinica medica", "Saude em primeiro lugar",
     "Profissionais capacitados para cuidar da sua saude.",
     ["Especialidades", "Exames", "Contato"]),
    ("odonto", "dentista", "Agendar consulta", "Ver tratamentos",
     "Odontologia com tratamentos modernos e atendimento humanizado.",
     ["Limpeza", "Clareamento", "Implante", "Ortodontia", "Emergencia"],
     "Consultorio odontologico", "Seu sorriso perfecto",
     "Tecnologia de ponta e carinho em cada tratamento para seu sorriso.",
     ["Tratamentos", "Galeria", "Contato"]),
    ("dentista", "dentista", "Agendar consulta", "Ver tratamentos",
     "Odontologia com tratamentos modernos e atendimento humanizado.",
     ["Limpeza", "Clareamento", "Implante", "Ortodontia", "Emergencia"],
     "Consultorio odontologico", "Seu sorriso perfecto",
     "Tecnologia de ponta e carinho em cada tratamento para seu sorriso.",
     ["Tratamentos", "Galeria", "Contato"]),
    ("imobiliaria", "imobiliaria", "Ver imoveis", "Falar corretor",
     "Imobiliaria com imoveis selecionados e atendimento personalizado.",
     ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"],
     "Imovel", "Seu proximo imovel",
     "Encontre o imovel ideal com quem entende do mercado local.",
     ["Imoveis", "Galeria", "Contato"]),
    ("imoveis", "imobiliaria", "Ver imoveis", "Falar corretor",
     "Imobiliaria com imoveis selecionados para compra e locacao.",
     ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"],
     "Imovel", "Seu proximo imovel",
     "Encontre o imovel ideal com quem entende do mercado local.",
     ["Imoveis", "Galeria", "Contato"]),
    ("nutricionista", "nutricionista", "Agendar consulta", "Ver planos",
     "Nutricionista com plano alimentar personalizado.",
     ["Avaliacao", "Plano alimentar", "Acompanhamento", "Suplementacao", "Bioimpedancia"],
     "Nutricionista", "Nutricao de verdade",
     "Transforme sua alimentacao com acompanhamento profissional cientifico.",
     ["Servicos", "Galeria", "Contato"]),
    ("nutricao", "nutricionista", "Agendar consulta", "Ver planos",
     "Nutricao com planos alimentares personalizados para seus objetivos.",
     ["Avaliacao", "Plano alimentar", "Acompanhamento", "Suplementacao", "Bioimpedancia"],
     "Nutricao", "Nutricao de verdade",
     "Alimentacao inteligente para uma vida mais saudavel.",
     ["Servicos", "Galeria", "Contato"]),
    ("advocacia", "advocacia", "Falar com advogado", "Ver areas",
     "Escritorio de advocacia com experiencia em diversas areas do direito.",
     ["Consulta", "Contratos", "Processos", "Assessoria", "Recursos"],
     "Escritorio de advocacia", "Direito com seriedade",
     "Atendimento juridico transparente e dedicado a sua causa.",
     ["Areas", "Galeria", "Contato"]),
    ("advogado", "advocacia", "Falar com advogado", "Ver areas",
     "Advogado com experiencia em diversas areas do direito.",
     ["Consulta", "Contratos", "Processos", "Assessoria", "Recursos"],
     "Advocacia", "Direito com seriedade",
     "Atendimento juridico transparente e dedicado a sua causa.",
     ["Areas", "Galeria", "Contato"]),
    ("ecommerce", "ecommerce", "Ver produtos", "Ver ofertas",
     "Loja online com produtos selecionados e entrega para todo o Brasil.",
     ["Produtos", "Frete", "Troca", "Atendimento", "Garantia"],
     "Produtos", "Qualidade garantida",
     "Produtos selecionados com cuidado para atender suas necessidades.",
     ["Produtos", "Ofertas", "Contato"]),
    ("petshop", "petshop", "Agendar servico", "Ver produtos",
     "Pet shop com produtos e servicos para o bem-estar do seu pet.",
     ["Banho", "Tosa", "Consulta", "Produtos", "Creche"],
     "Pet shop", "Amor pelos animais",
     "Cuidamos do seu pet como se fosse nosso.",
     ["Servicos", "Produtos", "Contato"]),
    ("pet ", "petshop", "Agendar servico", "Ver produtos",
     "Pet shop com produtos e servicos para o seu pet.",
     ["Banho", "Tosa", "Consulta", "Produtos", "Creche"],
     "Pet shop", "Amor pelos animais",
     "Cuidamos do seu pet como se fosse nosso.",
     ["Servicos", "Produtos", "Contato"]),
    ("hotel", "hotel", "Reservar", "Ver quartos",
     "Hospedagem com conforto, localizacao privilegiada e atendimento diferenciado.",
     ["Quartos", "Cafe da manha", "Estacionamento", "Wi-Fi", "Piscina"],
     "Hotel", "Sua casa longe de casa",
     "Conforto e acolhimento para tornar sua estadia inesquecivel.",
     ["Quartos", "Servicos", "Reservar"]),
    ("pousada", "hotel", "Reservar", "Ver quartos",
     "Pousada com ambiente familiar e localizacao privilegiada.",
     ["Quartos", "Cafe da manha", "Wi-Fi", "Estacionamento", "Piscina"],
     "Pousada", "Hospitalidade familiar",
     "Ambiente acolhedor para sua estadia com carinho e conforto.",
     ["Quartos", "Servicos", "Reservar"]),
    ("salao_beleza", "salao_beleza", "Agendar horario", "Ver servicos",
     "Salao de beleza com profissionais capacitados e ambiente acolhedor.",
     ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"],
     "Salao de beleza", "Beleza e bem-estar",
     "Transformamos seu visual com tecnicas modernas e produtos de qualidade.",
     ["Servicos", "Galeria", "Contato"]),
    ("beleza", "salao_beleza", "Agendar horario", "Ver servicos",
     "Salao de beleza com profissionais capacitados.",
     ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"],
     "Salao de beleza", "Beleza e bem-estar",
     "Transformamos seu visual com tecnicas modernas.",
     ["Servicos", "Galeria", "Contato"]),
    ("fisioterapia", "fisioterapia", "Agendar sessao", "Ver tratamentos",
     "Fisioterapia com atendimento personalizado para reabilitacao.",
     ["Avaliacao", "Tratamento", "RPG", "Acupuntura", "Pilates"],
     "Fisioterapia", "Movimento com saude",
     "Recupere sua qualidade de vida com tratamento humanizado.",
     ["Servicos", "Galeria", "Contato"]),
    ("fisio", "fisioterapia", "Agendar sessao", "Ver tratamentos",
     "Fisioterapia com atendimento personalizado.",
     ["Avaliacao", "Tratamento", "RPG", "Acupuntura", "Pilates"],
     "Fisioterapia", "Movimento com saude",
     "Recupere sua qualidade de vida.",
     ["Servicos", "Galeria", "Contato"]),
    ("escola", "escola", "Matricular", "Ver cursos",
     "Instituicao de ensino com metodologia moderna e corpo docente qualificado.",
     ["Matricula", "Cursos", "Talleres", "Eventos", "Biblioteca"],
     "Escola", "Educacao que transforma",
     "Formando cidadaos preparados para o futuro com excelencia.",
     ["Cursos", "Eventos", "Contato"]),
    ("cursinho", "escola", "Matricular", "Ver cursos",
     "Cursinho com preparacao para vestibulares e concursos.",
     ["Cursos", "Simulados", "Aulas", "Material", "Monitoria"],
     "Cursinho", "Preparacao garantida",
     "Metodologia testada para sua aprovacao.",
     ["Cursos", "Simulados", "Contato"]),
    ("autoescola", "autoescola", "Matricular", "Ver categorias",
     "Autoescola com aprovacao garantida e atendimento moderno.",
     ["Aulas teoricas", "Aulas praticas", "Simulado", "Exame", "CNH"],
     "Autoescola", "Sua habilitacao na mao",
     "Metodologia comprovada para voce passar no DETRAN.",
     ["Categorias", "Simulado", "Contato"]),
    ("oficina", "oficina", "Agendar servico", "Ver servicos",
     "Oficina mecanica com profissionais experientes e equipamentos modernos.",
     ["Revisao", "Diagnostico", "Reparos", "Pintura", "Eletrica"],
     "Oficina mecanica", "Seu carro em boas maos",
     "Servico de qualidade com transparencia e compromisso.",
     ["Servicos", "Galeria", "Contato"]),
    ("farmacia", "farmacia", "Ver produtos", "Ver promocoes",
     "Farmacia com variedade de medicamentos e atendimento personalizado.",
     ["Medicamentos", "Manipulacao", "Dermocosmeticos", "Atendimento", "Delivery"],
     "Farmacia", "Saude e bem-estar",
     "Farmacêuticos capacitados para orientar sobre medicamentos.",
     ["Produtos", "Promocoes", "Contato"]),
    ("manipulacao", "farmacia", "Ver produtos", "Fazer orcamento",
     "Farmacia de manipulacao com receitas personalizadas.",
     ["Manipulacao", "Orcamento", "Dermocosmeticos", "Fitoterapicos", "Homeopatia"],
     "Farmacia de manipulacao", "Medicamentos personalizados",
     "Formulas manipuladas com qualidade e precisao.",
     ["Produtos", "Orcamento", "Contato"]),
    ("psicologo", "psicologo", "Agendar sessao", "Ver abordagens",
     "Psicologia com atendimento humanizado para suas necessidades emocionais.",
     ["Consulta", "Terapia", "Avaliacao", "Diagnostico", "Acompanhamento"],
     "Consultorio de psicologia", "Cuidado emocional",
     "Um espaco seguro para falar sobre seus sentimentos.",
     ["Abordagens", "Galeria", "Contato"]),
    ("psicologia", "psicologo", "Agendar sessao", "Ver abordagens",
     "Psicologia com atendimento humanizado.",
     ["Consulta", "Terapia", "Avaliacao", "Diagnostico", "Acompanhamento"],
     "Psicologia", "Cuidado emocional",
     "Um espaco seguro para falar sobre seus sentimentos.",
     ["Abordagens", "Galeria", "Contato"]),
    ("dermatologia", "dermatologia", "Agendar consulta", "Ver tratamentos",
     "Dermatologia com tratamentos esteticos e clinicos para sua pele.",
     ["Consulta", "Tratamento", "Estetica", "Procedimentos", "Mapeamento"],
     "Dermatologia", "Pele saudavel",
     "Diagnostico e tratamento especializado para sua pele.",
     ["Tratamentos", "Estetica", "Contato"]),
    ("design", "design", "Ver portfolio", "Falar comigo",
     "Design com solucoes criativas para sua marca ou projeto.",
     ["Identidade visual", "Web design", "UI/UX", "Redes sociais", "Impressos"],
     "Design", "Criatividade que transforma",
     "Projetos que comunicam sua essencia e conectam com seu pubblico.",
     ["Portfolio", "Servicos", "Contato"]),
    ("fotografo", "fotografo", "Ver portfolio", "Fazer orcamento",
     "Fotografia com servicos para eventos, casamentos eBOOKs.",
     ["Eventos", "Casamentos", "Books", "Corporativo", "Produtos"],
     "Fotografia", "Momentos eternizados",
     "Capturamos momentos e emocoes com sensibilidade e tecnica.",
     ["Portfolio", "Pacotes", "Contato"]),
]

def build_elif_chain():
    """Build the expanded if/elif chain for all segments."""
    lines = []
    for i, (kw, seg, cta1, cta2, hero_desc, svcs, alt, lt_title, lt_desc, nav) in enumerate(SEGMENT_MAP):
        # Build svc_labels as Python list repr
        svc_repr = "[" + ", ".join(f'"{s}"' for s in svcs) + "]"
        # Build nav_items as Python list of tuples
        nav_repr = "[" + ", ".join(f'("{n}", "#{'servicos' if n.lower() in ['servicos','tratamentos','categorias','servicos2'] else n.lower() if n.lower()=='wod' else 'servicos' if n.lower()=='cardapio' else 'servicos' if n.lower()=='quartos' else n.lower()}")' for n in nav) + "]"

        svc_str = ", ".join(f'"{s}"' for s in svcs)
        nav_str = ", ".join(f'("{n}", "#servicos")' for n in nav)

        svc_list = ", ".join(f'"{s}"' for s in svcs)
        nav_list = ", ".join(f'("{n}", "#servicos")' for n in nav)

        # Smart nav hrefs
        nav_hrefs = []
        for n in nav:
            nl = n.lower()
            if nl == 'servicos' or nl == 'tratamentos' or nl == 'categorias':
                href = '#servicos'
            elif nl == 'wod':
                href = '#servicos'
            elif nl == 'cardapio':
                href = '#servicos'
            elif nl == 'quartos':
                href = '#servicos'
            elif nl == 'portflio' or nl == 'portfolio':
                href = '#galeria'
            elif nl == 'reservar':
                href = '#contato'
            elif nl == 'pedidos':
                href = '#contato'
            else:
                href = '#contato'
            nav_hrefs.append(f'("{n}", "{href}")')

        nav_str = ", ".join(nav_hrefs)

        if i == 0:
            start = f'    if "{kw}" in segment:'
        else:
            start = f'    elif "{kw}" in segment:'

        block = f'''{start}
        svc_labels = [{svc_str}]
        hero_desc = "{hero_desc}"
        cta_primary = "{cta1}"
        cta_secondary = "{cta2}"
        alt_img = "{alt}"
        lifestyle_title = "{lt_title}"
        lifestyle_desc = "{lt_desc}"
        nav_items = [{nav_str}]'''
        lines.append(block)

    return "\n".join(lines)

elif_chain = build_elif_chain()
print(f"Generated elif chain with {len(SEGMENT_MAP)} segments")

# Now generate the full function replacement
body = f'''
    if "barbearia" in segment or "barbeiro" in segment:
        svc_labels = ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"]
        hero_desc = "Barbearia premium com barbeiros experientes e ambiente climatizado."
        cta_primary = "Agendar horario"
        cta_secondary = "Ver servicos"
        alt_img = "Barbeiro em barbearia"
        lifestyle_title = "Tradicao em cada corte"
        lifestyle_desc = "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "academia" in segment or "fitness" in segment or "crossfit" in segment or "musculacao" in segment:
        svc_labels = ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"]
        hero_desc = "Academia completa com treino funcional, alunos acompanhados e ambiente moderno."
        cta_primary = "Comecar treino"
        cta_secondary = "Ver estrutura"
        alt_img = "Alunos em treino fitness"
        lifestyle_title = "Energia e constancia"
        lifestyle_desc = "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar."
        nav_items = [("Treinos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "restaurante" in segment or "bar" in segment or "caf" in segment or "pizzaria" in segment or "hamburgueria" in segment or "lanchonete" in segment:
        svc_labels = ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"]
        hero_desc = "Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor."
        cta_primary = "Fazer reserva"
        cta_secondary = "Ver menu"
        alt_img = "Restaurante"
        lifestyle_title = "Experiencia gastronomica"
        lifestyle_desc = "Cada prato preparado com cuidado para proporcionar uma experiencia unica."
        nav_items = [("Cardapio", "#servicos"), ("Galeria", "#galeria"), ("Reservar", "#contato")]
    elif "clinica" in segment or "estetica" in segment or "medic" in segment or "dermatologia" in segment or "psicologo" in segment or "psicologia" in segment or "fisioterapia" in segment or "fisio" in segment:
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
        lifestyle_title = "Seu sorriso perfecto"
        lifestyle_desc = "Tecnologia de ponta e carinho em cada tratamento para seu sorriso."
        nav_items = [("Tratamentos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "ecommerce" in segment or "loja" in segment or "roupas" in segment or "calcados" in segment:
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
    elif "salao_beleza" in segment or "beleza" in segment:
        svc_labels = ["Corte", "Coloracao", "Manicure", "Maquiagem", "Tratamentos"]
        hero_desc = "Salao de beleza com profissionais capacitados e ambiente acolhedor."
        cta_primary = "Agendar horario"
        cta_secondary = "Ver servicos"
        alt_img = "Salao de beleza"
        lifestyle_title = "Beleza e bem-estar"
        lifestyle_desc = "Transformamos seu visual com tecnicas modernas e produtos de qualidade."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "escola" in segment or "cursinho" in segment or "idiomas" in segment or "musica" in segment:
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
    elif "oficina" in segment or "mecanica" in segment or "freio" in segment or "suspensao" in segment:
        svc_labels = ["Revisao", "Diagnostico", "Reparos", "Pintura", "Eletrica"]
        hero_desc = "Oficina mecanica com profissionais experientes e equipamentos modernos."
        cta_primary = "Agendar servico"
        cta_secondary = "Ver servicos"
        alt_img = "Oficina mecanica"
        lifestyle_title = "Seu carro em boas maos"
        lifestyle_desc = "Servico de qualidade com transparencia e compromisso com seu veiculo."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "farmacia" in segment or "manipulacao" in segment or "dermocosmeticos" in segment:
        svc_labels = ["Medicamentos", "Manipulacao", "Dermocosmeticos", "Atendimento", "Delivery"]
        hero_desc = "Farmacia com variedade de medicamentos e atendimento personalizado."
        cta_primary = "Ver produtos"
        cta_secondary = "Ver promocoes"
        alt_img = "Farmacia"
        lifestyle_title = "Saude e bem-estar"
        lifestyle_desc = "Farmacêuticos capacitados para orientar sobre medicamentos e cuidados."
        nav_items = [("Produtos", "#servicos"), ("Promocoes", "#galeria"), ("Contato", "#contato")]
    elif "design" in segment or "grafico" in segment or "web design" in segment:
        svc_labels = ["Identidade visual", "Web design", "UI/UX", "Redes sociais", "Impressos"]
        hero_desc = "Design com solucoes criativas para sua marca ou projeto."
        cta_primary = "Ver portfolio"
        cta_secondary = "Falar comigo"
        alt_img = "Design"
        lifestyle_title = "Criatividade que transforma"
        lifestyle_desc = "Projetos que comunicam sua essencia e conectam com seu pubblico."
        nav_items = [("Portfolio", "#servicos"), ("Servicos", "#galeria"), ("Contato", "#contato")]
    elif "fotografo" in segment or "fotografia" in segment:
        svc_labels = ["Eventos", "Casamentos", "Books", "Corporativo", "Produtos"]
        hero_desc = "Fotografia com servicos para eventos, casamentos eBOOKs corporativos."
        cta_primary = "Ver portfolio"
        cta_secondary = "Fazer orcamento"
        alt_img = "Fotografia"
        lifestyle_title = "Momentos eternizados"
        lifestyle_desc = "Capturamos momentos e emocoes com sensibilidade e tecnica."
        nav_items = [("Portfolio", "#servicos"), ("Pacotes", "#galeria"), ("Contato", "#contato")]
    else:
        svc_labels = ["Servico 1", "Servico 2", "Servico 3", "Servico 4", "Servico 5"]
        hero_desc = f"{{name}}: servicos de qualidade com atendimento personalizado em {{city}}."
        cta_primary = "Saiba mais"
        cta_secondary = "Ver servicos"
        alt_img = f"{{name}}"
        lifestyle_title = "Experiencia unica"
        lifestyle_desc = f"Atendimento dedicado para garantir sua satisfacao em {{city}}."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
'''

print(f"Body length: {len(body)} chars")
print("Segments covered:", len([l for l in body.split('\n') if l.strip().startswith('elif') or l.strip().startswith('if ')]))
print("\nDone generating!")
