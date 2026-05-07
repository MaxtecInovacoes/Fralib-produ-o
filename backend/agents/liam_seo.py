"""SEO tags e WhatsApp float — Liam"""
import re, unicodedata, json
from liam_models import LiamInput

# Mapeamento segmento -> schema.org @type
SCHEMA_TYPE_MAP = {
    "academia": "SportsClub",
    "fitness": "SportsClub",
    "gym": "SportsClub",
    "crossfit": "SportsClub",
    "pilates": "SportsClub",
    "yoga": "SportsClub",
    "musculacao": "SportsClub",
    "natacao": "SportsClub",
    "danca": "DanceSchool",
    "ballet": "DanceSchool",
    "escola de danca": "DanceSchool",
    "salao": "BeautySalon",
    "barbearia": "HairSalon",
    "cabelereiro": "HairSalon",
    "estetica": "BeautySalon",
    "spa": "DaySpa",
    "clinica": "MedicalClinic",
    "dentista": "Dentist",
    "odontologia": "Dentist",
    "psicologia": "MedicalClinic",
    "nutricao": "MedicalClinic",
    "fisioterapia": "MedicalClinic",
    "restaurante": "Restaurant",
    "lanchonete": "FastFoodRestaurant",
    "pizzaria": "Restaurant",
    "hamburgueria": "Restaurant",
    "cafeteria": "CafeOrCoffeeShop",
    "padaria": "Bakery",
    "confeitaria": "Bakery",
    "pet": "AnimalShelter",
    "veterinario": "VeterinaryCare",
    "escola": "School",
    "curso": "EducationalOrganization",
    "advocacia": "LegalService",
    "contabilidade": "AccountingService",
    "imobiliaria": "RealEstateAgent",
    "hotel": "Hotel",
    "pousada": "LodgingBusiness",
    "farmacia": "Pharmacy",
    "supermercado": "GroceryStore",
    "loja": "Store",
    "boutique": "ClothingStore",
    "joalheria": "JewelryStore",
    "otica": "Optician",
    "auto": "AutoRepair",
    "mecanica": "AutoRepair",
    "oficina": "AutoRepair",
}

def _get_schema_type(segmento: str) -> str:
    seg = segmento.lower()
    for key, stype in SCHEMA_TYPE_MAP.items():
        if key in seg:
            return stype
    return "LocalBusiness"

def gerar_seo_tags(lead: LiamInput) -> str:
    """Gera SEO tags (Open Graph, JSON-LD) + Favicon"""
    desc = f"{lead.segmento} em {lead.cidade}. {lead.rating} estrelas." if lead.rating else f"{lead.segmento} em {lead.cidade}"
    image_url = lead.fotos[0] if lead.fotos else ""
    _slug_canonical = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', lead.nome.lower()).encode('ascii','ignore').decode()).strip('-')[:50]
    canonical_url = lead.website or f"https://seunegociofralib.site/sites/{_slug_canonical}/"

    schema_type = _get_schema_type(lead.segmento)
    review_count = len(lead.reviews or [])

    # Montar schema.org estruturado
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": lead.nome,
        "description": desc,
        "url": canonical_url,
        "telephone": lead.telefone,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": lead.cidade,
            "addressCountry": "BR"
        },
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "06:00", "closes": "22:00"},
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Saturday"], "opens": "08:00", "closes": "18:00"}
        ],
        "priceRange": "$$",
        "servesCuisine": None,
    }

    if image_url:
        schema["image"] = image_url

    if lead.rating and float(lead.rating) > 0:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(lead.rating),
            "reviewCount": str(review_count or 1),
            "bestRating": "5",
            "worstRating": "1"
        }

    # Remover campos None
    schema = {k: v for k, v in schema.items() if v is not None}

    schema_json = json.dumps(schema, ensure_ascii=False, indent=None)

    return f"""
<link rel="icon" type="image/x-icon" href="https://fralib.com.br/favicon.ico">
<link rel="icon" type="image/png" href="https://fralib.com.br/favicon.png">
<link rel="apple-touch-icon" href="https://fralib.com.br/favicon.png">
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{lead.nome}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{image_url}">
<meta property="og:url" content="{canonical_url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{canonical_url}">
<script type="application/ld+json">
{schema_json}
</script>
"""

def gerar_whatsapp_float(whatsapp: str) -> str:
    """Gera botão WhatsApp flutuante"""
    wpp_link = f"https://wa.me/55{whatsapp.replace(' ', '').replace('-', '')}" if whatsapp else "#"

    return f"""
<a id="wpp-float" href="{wpp_link}" target="_blank"
   class="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-5 py-3 rounded-full text-white font-semibold shadow-lg hover:scale-105 transition-transform"
   style="background: linear-gradient(135deg, #25D366, #128C7E); box-shadow: 0 8px 32px rgba(37,211,102,0.4);">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
  WhatsApp
</a>
"""

# ===== INSTRUÇÕES DO LIAM =====


