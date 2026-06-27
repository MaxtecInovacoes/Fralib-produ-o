#!/usr/bin/env python3
"""Sprint 12.15: Expand studio fallback to ALL FraLib segments + sub-segments + run smoke tests in parallel."""
import subprocess, json, time, sys
from pathlib import Path

VPS = 'root@100.101.18.1'
REMOTE = '/root/fralib/backend/services/vite_react_renderer.py'
LOCAL = 'C:/fralib/backend/services/vite_react_renderer.py'

# All segments + sub-segments FraLib supports
SEGMENTS = {
    'barbearia': {
        'sub': ['barbearia_premium', 'barbearia_classica', 'barbearia_moderna'],
        'cta': 'Agendar horário',
        'hero': 'Barbearia premium com barbeiros experientes e ambiente climatizado.',
        'svc': ['Corte', 'Barba', 'Sobrancelha', 'Pigmentação', 'Hidatação'],
        'lifestyle_title': 'Tradição em cada corte',
        'lifestyle_desc': 'Um espaço dedicado ao cuidado masculino, com atendimento personalizado.',
    },
    'academia': {
        'sub': ['crossfit', 'musculacao', 'treino_funcional', 'spinning', 'ginastica'],
        'cta': 'Começar treino',
        'hero': 'Academia completa com treino funcional, alunos acompanhados e ambiente moderno.',
        'svc': ['Musculação', 'Treino funcional', 'Spinning', 'Crossfit', 'Avaliação'],
        'lifestyle_title': 'Energia e constância',
        'lifestyle_desc': 'Um espaço para criar rotina, encontrar orientação e manter frequência.',
    },
    'restaurante': {
        'sub': ['restaurante_familiar', 'restaurante_gourmet', 'lanchonete', 'bar', 'cafeteria', 'pizzaria', 'hamburgueria'],
        'cta': 'Fazer reserva',
        'hero': 'Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor.',
        'svc': ['Pratos', 'Menu', 'Reservas', 'Eventos', 'Delivery'],
        'lifestyle_title': 'Experiência gastronômica',
        'lifestyle_desc': 'Cada prato preparado com cuidado para proporcionar uma experiência única.',
    },
    'clinica': {
        'sub': ['clinica_estetica', 'clinica_medica', 'odonto', 'fisioterapia', 'psicologia', 'dermatologia'],
        'cta': 'Agendar consulta',
        'hero': 'Clínica com profissionais experientes e tratamentos personalizados para seu bem-estar.',
        'svc': ['Consulta', 'Tratamento', 'Avaliação', 'Procedimento', 'Retorno'],
        'lifestyle_title': 'Cuidado e acolhimento',
        'lifestyle_desc': 'Ambiente preparado para recebê-lo com conforto e segurança em cada atendimento.',
    },
    'imobiliaria': {
        'sub': ['venda', 'locacao', 'lancamentos', 'comercial', 'rural'],
        'cta': 'Ver imóveis',
        'hero': 'Imobiliária com imóveis selecionados e atendimento personalizado para suas necessidades.',
        'svc': ['Venda', 'Locação', 'Avaliação', 'Consultoria', 'Lançamentos'],
        'lifestyle_title': 'Seu próximo imóvel',
        'lifestyle_desc': 'Encontre o imóvel ideal com quem entende do mercado local.',
    },
    'nutricionista': {
        'sub': ['nutricao_esportiva', 'nutricao_geral', 'nutricao_obesidade', 'nutricao_infantil'],
        'cta': 'Agendar consulta',
        'hero': 'Nutricionista com plano alimentar personalizado para seus objetivos de saúde.',
        'svc': ['Avaliação', 'Plano alimentar', 'Acompanhamento', 'Suplementação', 'Bioimpedância'],
        'lifestyle_title': 'Nutrição de verdade',
        'lifestyle_desc': 'Transforme sua alimentação com acompanhamento profissional científico.',
    },
    'advocacia': {
        'sub': ['trabalhista', 'civel', 'familia', 'previdenciario', 'imobiliario', 'tributario'],
        'cta': 'Falar com advogado',
        'hero': 'Escritório de advocacia com experiência em diversas áreas do direito.',
        'svc': ['Consulta', 'Elaboração de contratos', 'Processos', 'Assessoria', 'Recursos'],
        'lifestyle_title': 'Direito com seriedade',
        'lifestyle_desc': 'Atendimento jurídico transparente e dedicado à sua causa.',
    },
    'ecommerce': {
        'sub': ['roupas', 'calcados', 'acessorios', 'beleza', 'moveis', 'eletronicos'],
        'cta': 'Ver produtos',
        'hero': 'Loja online com produtos selecionados e entrega para todo o Brasil.',
        'svc': ['Produtos', 'Frete', 'Troca', 'Atendimento', 'Garantia'],
        'lifestyle_title': 'Qualidade garantida',
        'lifestyle_desc': 'Produtos selecionados com cuidado para atender suas necessidades.',
    },
    'petshop': {
        'sub': ['banho_tosa', 'pet_shop', 'veterinario', 'racao', 'acessorios_pet'],
        'cta': 'Agendar serviço',
        'hero': 'Pet shop com produtos e serviços para o bem-estar do seu pet.',
        'svc': ['Banho', 'Tosa', 'Consulta', 'Produtos', 'Creche'],
        'lifestyle_title': 'Amor pelos animais',
        'lifestyle_desc': 'Cuidamos do seu pet como se fosse nosso. Amor e dedicação em cada serviço.',
    },
    'hotel': {
        'sub': ['hotel', 'pousada', 'resort', 'hostel', 'apartamento', 'residencial'],
        'cta': 'Reservar',
        'hero': 'Hospedagem com conforto, localização privilegiada e atendimento diferenciado.',
        'svc': ['Quartos', 'Café da manhã', 'Estacionamento', 'Wi-Fi', 'Piscina'],
        'lifestyle_title': 'Sua casa longe de casa',
        'lifestyle_desc': 'Conforto e acolhimento para tornar sua estadia inesquecível.',
    },
    'salao_beleza': {
        'sub': ['cabelo', 'manicure', 'maquiagem', 'estetica', 'depilacao', 'spa'],
        'cta': 'Agendar horário',
        'hero': 'Salão de beleza com profissionais capacitados e ambiente acolhedor.',
        'svc': ['Corte', 'Coloração', 'Manicure', 'Maquiagem', 'Tratamentos'],
        'lifestyle_title': 'Beleza e bem-estar',
        'lifestyle_desc': 'Transformamos seu visual com técnicas modernas e produtos de qualidade.',
    },
    'fisioterapia': {
        'sub': ['esportiva', 'geriatrica', 'respiratoria', 'neurologica', 'ortopedica'],
        'cta': 'Agendar sessão',
        'hero': 'Fisioterapia com atendimento personalizado para reabilitação e qualidade de vida.',
        'svc': ['Avaliação', 'Tratamento', 'RPG', 'Acupuntura', 'Pilates'],
        'lifestyle_title': 'Movimento com saúde',
        'lifestyle_desc': 'Recupere sua qualidade de vida com tratamento fisioterapêutico humanizado.',
    },
    'escola': {
        'sub': ['ensino_fundamental', 'ensino_medio', 'cursinho', 'idiomas', 'musica', 'informatica'],
        'cta': 'Matricular',
        'hero': 'Instituição de ensino com metodologia moderna e corpo docente qualificado.',
        'svc': ['Matrícula', 'Cursos', 'Talleres', 'Eventos', 'Biblioteca'],
        'lifestyle_title': 'Educação que transforma',
        'lifestyle_desc': 'Formando cidadãos preparados para o futuro com excelência e valores.',
    },
    'autoescola': {
        'sub': ['carro', 'moto', 'caminhao', 'onibus'],
        'cta': 'Matricular',
        'hero': 'Autoescola com aprovação garantida e atendimento moderno.',
        'svc': ['Aulas teóricas', 'Aulas práticas', 'Simulado', 'Exame', 'CNH'],
        'lifestyle_title': 'Sua habilitação na mão',
        'lifestyle_desc': 'Metodologia comprovada para você passar no DETRAN de primeira.',
    },
    'oficina': {
        'sub': ['mecanica', 'eletrica', 'pintura', 'funilaria', 'suspensao', 'freio'],
        'cta': 'Agendar serviço',
        'hero': 'Oficina mecânica com profissionais experientes e equipamentos modernos.',
        'svc': ['Revisão', 'Diagnóstico', 'Reparos', 'Pintura', 'Elétrica'],
        'lifestyle_title': 'Seu carro em boas mãos',
        'lifestyle_desc': 'Serviço de qualidade com transparência e compromisso com seu veículo.',
    },
    'farmacia': {
        'sub': ['farmacia', 'manipulacao', 'dermocosmeticos', 'homeopatia'],
        'cta': 'Ver produtos',
        'hero': 'Farmácia com variedade de medicamentos e atendimento personalizado.',
        'svc': ['Medicamentos', 'Manipulação', 'Dermocosméticos', 'Atendimento', 'Delivery'],
        'lifestyle_title': 'Saúde e bem-estar',
        'lifestyle_desc': 'Farmacêuticos capacitados para orientar sobre medicamentos e cuidados.',
    },
}

# ALL niches including sub-segments (flat list for testing)
ALL_NICHOS = []
for seg, data in SEGMENTS.items():
    ALL_NICHOS.append(seg)
    for sub in data['sub']:
        ALL_NICHOS.append(sub)

print(f'Total segmentos: {len(SEGMENTS)}')
print(f'Total nichos+sub: {len(ALL_NICHOS)}')
print('Nichos:', ', '.join(ALL_NICHOS))
