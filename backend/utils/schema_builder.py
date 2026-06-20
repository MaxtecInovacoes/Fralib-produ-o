"""SchemaBuilder — Schema JSON-LD + sitemap + robots. Zero LLM."""
import json, re, os
from datetime import datetime

CATEGORIA_SCHEMA = {
    "academia": "GymFitness", "crossfit": "GymFitness", "pilates": "GymFitness",
    "hamburgueria": "Restaurant", "restaurante": "Restaurant", "pizzaria": "Restaurant",
    "churrascaria": "Restaurant", "bar": "BarOrPub", "café": "CafeOrCoffeeShop",
    "dentista": "Dentist", "nutricionista": "DieteticClinic",
    "barbearia": "BarberShop", "salão": "BeautySalon", "estética": "BeautySalon",
    "pet": "PetStore", "clínica": "MedicalClinic", "advocacia": "LegalService",
    "mecânica": "AutoRepair", "hotel": "Hotel",
}


def mapear_tipo(segmento):
    if not segmento:
        return "LocalBusiness"
    s = segmento.lower()
    for k, v in CATEGORIA_SCHEMA.items():
        if k in s:
            return v
    return "LocalBusiness"


def normalizar_horarios(horarios):
    """Converte horarios vindos do scraper/DB para dict dia -> horario."""
    if not horarios:
        return {}
    if isinstance(horarios, dict):
        return horarios
    if isinstance(horarios, list):
        normalizados = {}
        for item in horarios:
            if isinstance(item, dict):
                dia = (
                    item.get("dia")
                    or item.get("day")
                    or item.get("label")
                    or item.get("name")
                )
                horario = (
                    item.get("horario")
                    or item.get("hours")
                    or item.get("time")
                    or item.get("value")
                    or item.get("text")
                )
                if dia:
                    normalizados[str(dia).strip()] = str(horario or "").strip()
                continue
            if isinstance(item, str) and item.strip():
                texto = item.strip()
                parts = (
                    texto.split("\t", 1)
                    if "\t" in texto
                    else re.split(r"\s{2,}|:\s+", texto, maxsplit=1)
                )
                dia = parts[0].strip()
                horario = parts[1].strip() if len(parts) > 1 else ""
                if dia:
                    normalizados[dia] = horario
        return normalizados
    return {}


def gerar_schema(lead_data, deploy_url):
    schema = {
        "@context": "https://schema.org",
        "@type": mapear_tipo(lead_data.get("segmento", "")),
        "name": lead_data.get("nome", ""),
        "url": deploy_url,
    }
    tel = lead_data.get("telefone", "")
    if tel:
        nums = re.sub(r'[^\d]', '', tel)
        schema["telephone"] = f"+55{nums}" if len(nums) == 11 else tel
    cidade = lead_data.get("cidade", "")
    if cidade:
        schema["address"] = {"@type": "PostalAddress", "addressLocality": cidade, "addressCountry": "BR"}
        schema["areaServed"] = {"@type": "City", "name": cidade}
    rating = lead_data.get("rating")
    if rating:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": rating,
            "reviewCount": lead_data.get("total_reviews", 5),
            "bestRating": 5,
        }
    horarios = normalizar_horarios(lead_data.get("horarios", {}))
    if horarios:
        DIAS = {
            "segunda": "Monday", "terca": "Tuesday", "terça": "Tuesday",
            "quarta": "Wednesday", "quinta": "Thursday", "sexta": "Friday",
            "sabado": "Saturday", "sábado": "Saturday", "domingo": "Sunday",
        }
        specs = []
        for dia, h in horarios.items():
            if not h or "fechado" in str(h).lower():
                continue
            dia_en = next((v for k, v in DIAS.items() if k in dia.lower()), None)
            if not dia_en:
                continue
            for periodo in str(h).replace("–", "-").replace("—", "-").split(","):
                m = re.search(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', periodo)
                if m:
                    specs.append({
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": dia_en,
                        "opens": m.group(1),
                        "closes": m.group(2),
                    })
        if specs:
            schema["openingHoursSpecification"] = specs
    fotos = lead_data.get("fotos_unsplash", lead_data.get("fotos", []))
    if fotos:
        first = fotos[0]
        if isinstance(first, str):
            schema["image"] = first
        elif isinstance(first, dict):
            schema["image"] = first.get("url", "")
    return '<script type="application/ld+json">\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n</script>'


def gerar_sitemap(deploy_url):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        f'    <loc>{deploy_url}</loc>\n'
        f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>'
    )


def gerar_robots(deploy_url):
    return f"User-agent: *\nAllow: /\n\nSitemap: {deploy_url.rstrip('/')}/sitemap.xml"


def agrupar_horarios(horarios):
    """Agrupa dias com mesmo horario. Ex: 'Seg a Sex: 06:00-21:00'"""
    if not horarios:
        return ["Horarios nao disponiveis"]
    ORDEM = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    ABREV = {"segunda": "Seg", "terca": "Ter", "quarta": "Qua", "quinta": "Qui", "sexta": "Sex", "sabado": "Sab", "domingo": "Dom"}
    norm = {}
    for dia, h in horarios.items():
        d = dia.lower().replace("-feira", "").replace("á", "a").replace("ç", "c")
        norm[d] = "Fechado" if (not h or "fechado" in str(h).lower()) else h.strip()
    grupos, i = [], 0
    while i < len(ORDEM):
        dia = ORDEM[i]
        horario = norm.get(dia, "Fechado")
        j = i + 1
        while j < len(ORDEM) and norm.get(ORDEM[j], "Fechado") == horario:
            j += 1
        if j - i == 7:
            grupos.append(f"Todos os dias: {horario}")
        elif j - i == 1:
            grupos.append(f"{ABREV[dia]}: {horario}")
        else:
            grupos.append(f"{ABREV[dia]} a {ABREV[ORDEM[j-1]]}: {horario}")
        i = j
    return grupos


def injetar_schema_no_html(html, lead_data, deploy_url, site_dir):
    """Injeta schema no HTML e cria sitemap+robots. Retorna HTML modificado."""
    schema_tag = gerar_schema(lead_data, deploy_url)
    if "application/ld+json" in (html or ""):
        pass
    elif "</head>" in html:
        html = html.replace("</head>", f"{schema_tag}\n</head>")
    elif "</body>" in html:
        html = html.replace("</body>", f"{schema_tag}\n</body>")
    else:
        html = f"{schema_tag}\n{html}"
    os.makedirs(site_dir, exist_ok=True)
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(gerar_sitemap(deploy_url))
    with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(gerar_robots(deploy_url))
    return html
