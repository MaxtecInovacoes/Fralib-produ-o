#!/usr/bin/env python3
"""Sprint 14.6: regenera sites de nutricionista com codigo novo.

Pega cada lead pelo ID, extrai facts do DB, chama render_site_with_builder
que rebuilda o bundle Vite com o codigo Sprint 14.6 (counter rotation,
10 hero class variants, 5 font variants, 5 cta variants).

Uso:
  python3 scripts/regenerate_lead.py <lead_id> [<lead_id> ...]
"""
import os
import sys

# Setup path
sys.path.insert(0, '/root/fralib')
sys.path.insert(0, '/root/fralib/backend')

from dotenv import load_dotenv
load_dotenv('/root/fralib/.env')

from database import SessionLocal, inicializar_database
from sqlalchemy import text

inicializar_database()


def regenerate(lead_id):
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT id, user_id, nome, segmento, cidade,
                       telefone, whatsapp, rating, total_avaliacoes, address,
                       services, horarios, description, diferenciais
                FROM leads WHERE id = :id
            """),
            {"id": lead_id}
        ).fetchone()

        if not row:
            print(f"  Lead {lead_id} nao encontrado")
            return False

        facts = {
            "business": {
                "name": row[2], "nome": row[2], "business_name": row[2],
                "segmento": row[3], "segment": row[3], "subnicho": "nutricionista_esportiva",
                "cidade": row[4], "city": row[4],
                "whatsapp": row[6] or row[5] or "", "phone": row[6] or row[5] or "",
                "rating": str(row[7] or 5.0),
                "total_avaliacoes": str(row[8] or 21),
                "address": row[9] or "", "endereco": row[9] or "",
                "services": row[10] or ["Atendimento personalizado", "Plano alimentar", "Acompanhamento"],
                "horarios": row[11] or "",
                "description": row[12] or "",
                "diferenciais": row[13] or ["Atendimento personalizado"],
            },
            "segmento": row[3],
            "city": row[4],
            "subnicho": "nutricionista_esportiva",
        }

        # Calcula o counter pelo # de sites ja gerados
        n_existing = db.execute(
            text("SELECT COUNT(*) FROM site_generation_log WHERE tenant_id=:t AND subnicho=:s"),
            {"t": row[1], "s": "nutricionista_esportiva"}
        ).scalar() or 0
        facts["business"]["__counter"] = n_existing

        # Buscar/calcular variation via pipeline
        from backend.services.variation_seed import get_variation
        from backend.services.archetype_resolver import (
            archetype_for_segment, resolve_archetype_variation
        )
        var = get_variation(facts, counter=n_existing)
        archetype = archetype_for_segment("nutricionista")
        av = resolve_archetype_variation(
            archetype, var,
            subnicho="nutricionista_esportiva",
            counter=n_existing,
        )
        facts["variation"] = {
            "counter": n_existing,
            "hero_layout": var.hero_layout,
            "motion_style": var.motion_style,
            "copy_voice": var.copy_voice,
            "layout_variant": av["layout_variant"],
            "motion_variant": av["motion_variant"],
            "copy_variant": av["copy_variant"],
            "hero_classes": av["hero_classes"],
            "section_order": av["section_order"],
            "archetype": archetype,
        }

        # Render via builder_worker
        from backend.services.builder_worker import render_site_with_builder
        result = render_site_with_builder(
            facts,
            tenant_id=row[1],
            job_id=f"regen-{lead_id}",
            target="landing-page",
            publication_url=f"https://seunegociofralib.site/sites/{row[1]}/{row[2].lower().replace(' ', '-').replace('|', '').replace(',', '').replace('.', '')}/",
        )
        print(f"  Lead {lead_id} ({row[2]}): {result.get('status', '?')}")
        return True
    except Exception as e:
        print(f"  Lead {lead_id} ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/regenerate_lead.py <lead_id> [<lead_id> ...]")
        sys.exit(1)
    for lid in sys.argv[1:]:
        print(f"[regen] {lid}")
        regenerate(lid)
