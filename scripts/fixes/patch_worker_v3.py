#!/usr/bin/env python3
"""Patch worker.py: add fallback lead_data when lead not found in DB."""
import re

with open("/opt/fralib/worker.py") as f:
    s = f.read()

# Find the payload["lead_data"] = { block and add else fallback
old = '''                payload["lead_data"] = {
                        "nome": lead_row[0],
                        "cidade": lead_row[1],
                        "telefone": lead_row[2],
                        "segmento": lead_row[3],
                        "rating": float(lead_row[4]) if lead_row[4] is not None else None,
                        "reviews_count": int(_dados.get("reviews_count") or _dados.get("total_avaliacoes") or len(_dados.get("reviews", []))),
                        "fotos": _dados.get("fotos", []),
                        "website": _dados.get("website", ""),
                        "whatsapp": _dados.get("whatsapp") or lead_row[2],
                        "endereco": _dados.get("endereco", ""),
                        "market_intelligence": _dados.get("market_intelligence"),
                        "descricao": _dados.get("descricao", ""),
                    }'''

new = '''                payload["lead_data"] = {
                        "nome": lead_row[0],
                        "cidade": lead_row[1],
                        "telefone": lead_row[2],
                        "segmento": lead_row[3],
                        "rating": float(lead_row[4]) if lead_row[4] is not None else None,
                        "reviews_count": int(_dados.get("reviews_count") or _dados.get("total_avaliacoes") or len(_dados.get("reviews", []))),
                        "fotos": _dados.get("fotos", []),
                        "website": _dados.get("website", ""),
                        "whatsapp": _dados.get("whatsapp") or lead_row[2],
                        "endereco": _dados.get("endereco", ""),
                        "market_intelligence": _dados.get("market_intelligence"),
                        "descricao": _dados.get("descricao", ""),
                    }
                else:
                    payload["lead_data"] = {
                        "nome": payload.get("segmento", "Lead").title(),
                        "cidade": payload.get("cidade", ""),
                        "telefone": "",
                        "segmento": payload.get("segmento", ""),
                        "rating": None,
                        "reviews_count": 0,
                        "fotos": [],
                        "website": "",
                        "whatsapp": "",
                        "endereco": "",
                        "market_intelligence": None,
                        "descricao": "",
                    }'''

if old in s:
    s = s.replace(old, new)
    open("/opt/fralib/worker.py", "w").write(s)
    print("OK: patched worker.py with fallback lead_data")
else:
    print("ERROR: pattern not found")
