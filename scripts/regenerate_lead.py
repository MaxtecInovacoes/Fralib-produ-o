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
sys.path.insert(0, '/root/fralib/backend/core')

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts"))
from _env import load_env  # noqa: E402  — B4 DRY
load_env()

from backend.core.database import SessionLocal, inicializar_database
from sqlalchemy import text

# Pula inicializar_database se causar lock (assume schema ja criado)
try:
    inicializar_database()
except Exception as _e:
    print(f"[regen] inicializar_database pulou: {_e}")


def regenerate(lead_id):
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT id, user_id, nome, segmento, cidade,
                       telefone, telefone_whatsapp, score, briefing_json
                FROM leads WHERE id = :id
            """),
            {"id": lead_id}
        ).fetchone()

        if not row:
            print(f"  Lead {lead_id} nao encontrado")
            return False

        # Tenta extrair dados do briefing_json (ja contem todos os facts do lead)
        rating = 5.0
        reviews = 21
        address = ""
        services_list = ["Atendimento personalizado", "Plano alimentar", "Acompanhamento"]
        diferenciais_list = ["Atendimento personalizado"]
        if row[8]:
            try:
                bj = json.loads(row[8])
                rating = float(bj.get("rating") or bj.get("score") or 5.0)
                reviews = int(bj.get("total_avaliacoes") or bj.get("reviews_count") or 21)
                address = bj.get("address") or bj.get("endereco") or ""
                svcs = bj.get("services") or bj.get("servicos")
                if isinstance(svcs, list) and svcs:
                    services_list = svcs
                difs = bj.get("diferenciais")
                if isinstance(difs, list) and difs:
                    diferenciais_list = difs
            except Exception:
                pass

        facts = {
            "business": {
                "name": row[2], "nome": row[2], "business_name": row[2],
                "segmento": row[3], "segment": row[3], "subnicho": "nutricionista_esportiva",
                "cidade": row[4], "city": row[4],
                "whatsapp": row[6] or row[5] or "", "phone": row[6] or row[5] or "",
                "rating": str(rating),
                "total_avaliacoes": str(reviews),
                "address": address, "endereco": address,
                "services": services_list,
                "horarios": "",
                "description": "",
                "diferenciais": diferenciais_list,
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
        from backend.services.builder_worker import render_site_with_builder, copy_builder_dist
        result = render_site_with_builder(
            facts,
            tenant_id=row[1],
            job_id=f"regen-{lead_id}",
            target="landing-page",
            publication_url=f"https://seunegociofralib.site/sites/{row[1]}/{row[2].lower().replace(' ', '-').replace('|', '').replace(',', '').replace('.', '')}/",
        )
        print(f"  Lead {lead_id} ({row[2]}): {result.get('status', '?')}")

        # Sprint 14.7: publica resultado no /var/www/<slug>/
        try:
            output_dir = result.get("output_dir", "")
            if output_dir:
                # Determina slug do nome do lead
                import re as _re
                _slug = _re.sub(r'[^a-z0-9-]+', '-', row[2].lower()).strip('-')
                publish_dir = f"/var/www/fralib/sites/{row[1]}/{_slug}"
                from backend.services.builder_worker import copy_builder_dist
                copy_builder_dist(output_dir, publish_dir)
                print(f"  -> publicado em {publish_dir}")
        except Exception as pub_err:
            print(f"  WARN: publicacao falhou: {pub_err}")
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
