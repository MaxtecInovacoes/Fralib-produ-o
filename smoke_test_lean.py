"""Smoke-test do builder enxuto (LEAN single-shot)."""
import json, sys, time
sys.path.insert(0, '/app/backend')

from backend.agents.builder.agent import render_site


class FakePRD:
    pass


prd = FakePRD()
prd.business_name = 'Academia Teste Lean'
prd.segmento = 'academia'
prd.cidade = 'São Paulo'
prd.design_system_slug = 'corporate-trust'
prd.color_palette = type('CP', (), {'model_dump': lambda self: {
    'primary': '#1a56db', 'secondary': '#4b5563', 'accent': '#1a56db',
    'background': '#ffffff', 'surface': '#f5f7fa', 'text': '#111827',
    'border': '#e5e7eb', 'muted': '#6b7280', 'radius': '4px',
}})()
prd.typography = {'heading': 'Source Serif 4', 'body': 'Source Sans 3', 'border_radius': '4px'}
prd.visual_dna = {}
prd.photos = ['https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1600&q=80']
prd.address = 'Av. Paulista, 1000 - São Paulo, SP'
prd.phone = '(11) 99999-9999'
prd.whatsapp = '5511999999999'
prd.hours = {'seg-sexta': '06:00-23:00', 'sábado': '08:00-18:00', 'domingo': 'Fechado'}
prd.reviews_count = 3
prd.reviews_rating = 4.8
prd.reviews_list = [
    {'author': 'Maria S.', 'rating': 5, 'text': 'Melhor academia da região!'},
    {'author': 'João P.', 'rating': 5, 'text': 'Estrutura completa!'},
    {'author': 'Ana L.', 'rating': 4, 'text': 'Ótimo custo-benefício!'},
]
prd.faq_questions = [
    {'q': 'Quais são os horários?', 'a': 'Seg-Sex 06:00-23:00.'},
    {'q': 'Tem avaliação física?', 'a': 'Sim, incluída no plano.'},
    {'q': 'Como funciona o trial?', 'a': '1 semana grátis.'},
]
prd.seo_keywords = ['academia são paulo', 'musculação sp']
prd.ctas = [{'label': 'Aula experimental grátis', 'href': '#contato'}]
prd.value_props = ['Sem taxa de matrícula', 'Acesso 24h', 'Profissionais certificados']
prd.dark_mode = False
prd.instrucao_criativa_para_dev = (
    'Arquétipo corporate-trust: profissional, limpo, confiável. '
    'Use tons de azul e cinza. Hero com imagem de academia profissional.'
)
prd.anti_patterns = ['stock photos genéricas', 'ctas genéricos']
prd.schema_org_types = ['LocalBusiness']
prd.google_maps_embed = ''
prd.logo_url = ''
prd.videos = []
prd.components_21dev = ['hero', 'diferenciais', 'planos', 'depoimentos', 'faq', 'contato']
prd.horarios = {'seg-sexta': '06:00-23:00', 'sábado': '08:00-18:00', 'domingo': 'Fechado'}
prd.faixa_preco = 'R$ 89/mês'
prd.competitor_analysis = ''
prd.animations = []
prd.media_plan = []
prd.layout_dna = {}
prd.design_system = {}
prd.motion_directives = {}
prd.site_build_plan = {}
prd.requirements_contract = {}
prd.creative_direction = {}
prd.niche_brief = {}
prd.variation_blueprint = {}
prd.sections = []
prd._run_id = 'test-lean'
prd._lead_id = 'test-lead-abc'
prd._lead_data = {'nome': 'Academia Teste Lean'}

print('=== CALLING LEAN render_site ===')
t0 = time.time()
result = render_site(prd, usar_llm=True)
elapsed = time.time() - t0

print(f'success={result.success}')
print(f'model={result.model}')
print(f'error={result.error}')
print(f'html_bytes={len(result.html)}')
print(f'time={elapsed:.1f}s')
print(f'has_doctype={"<!DOCTYPE" in result.html}')
print(f'has_html={"<html" in result.html.lower()}')
print(f'has_body={"<body" in result.html.lower()}')
print(f'has_main={"<main" in result.html.lower()}')
print(f'has_h1={"<h1" in result.html.lower()}')
print(f'has_aos={"AOS" in result.html}')
print(f'has_design_tokens={"--brand-primary" in result.html}')
print(f'sections_found={"<section" in result.html.lower()}')
print(f'faq_details={"<details" in result.html.lower()}')
print(f'contact_phone={"(11) 99999-9999" in result.html}')
print(f'review_maria={"Maria S" in result.html}')
print(f'first_300_chars={result.html[:300]!r}')
