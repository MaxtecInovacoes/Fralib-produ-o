from backend.agents.html_quality_gate import (
    _phase6_contract_problems,
    sanitize_builder_html_for_publication,
)


def test_vite_publication_shell_gets_phase6_video_and_seo_contracts():
    html = """<!doctype html>
<html lang="pt-BR" data-renderer="builder">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FraLib Studio</title>
</head>
<body>
  <div id="root"></div>
</body>
</html>"""
    facts = {
        "business": {
            "name": "Academia Energia Total",
            "segment": "academia",
            "subniche": "fitness e treino",
            "city": "Curitiba",
            "address": "Rua Teste, 123",
            "phone": "5541999999999",
            "canonical_url": "https://energia.example.com/sites/2/academia-energia-total/",
        },
        "seo": {
            "canonical_url": "https://energia.example.com/sites/2/academia-energia-total/",
            "primary_terms": [
                "academia em curitiba",
                "treino funcional curitiba",
                "musculação perto de mim",
            ],
        },
        "media": {
            "photos": ["https://images.unsplash.com/photo-1517836357463-d25dfeac3438"],
            "videos": [
                "https://videos.pexels.com/video-files/3196220/3196220-hd_1280_720_25fps.mp4"
            ],
        },
        "design": {"archetype": "BOLD_ENERGY"},
    }

    public_html = sanitize_builder_html_for_publication(html, facts)
    low = public_html.lower()

    assert _phase6_contract_problems(public_html) == []
    assert '<title>Academia Energia Total | academia em Curitiba</title>' in public_html
    assert 'name="description"' in low
    assert 'name="keywords"' in low
    assert "academia em curitiba" in low
    assert 'data-hero-type="video"' in low
    assert "https://videos.pexels.com" in low
    assert "<video" in low and "autoplay" in low and "playsinline" in low
    assert "fralib-text-scramble" in low
    assert 'class="fralib-cursor-follower"' in low
    assert '<svg class="fralib-grain"' in low
    assert "cdn.jsdelivr.net/npm/gsap" in low
    assert "cdn.jsdelivr.net/npm/lenis" in low
    assert "fralib-theme-toggle" in low
