"""Test SDR system prompt generation for user 2 with empty history."""
from backend.core.database import engine
from sqlalchemy import text
import asyncio

# Load user 2 settings
from backend.services.sdr_settings import (
    normalize_sdr_settings, fetch_sdr_settings, build_sdr_system_prompt,
    get_sdr_settings_runtime,
)
from backend.core.database import SessionLocal

db = SessionLocal()
settings_raw = fetch_sdr_settings(db, 2)
print('=== SETTINGS BRUTOS (user 2) ===')
print('  agent_name:', settings_raw.get('agent_name'))
print('  objective:', settings_raw.get('objective'))
print('  custom_knowledge length:', len(settings_raw.get('custom_knowledge', '')))
print('  personality length:', len(settings_raw.get('personality', '')))

# Gera system prompt
from backend.agents.sdr_langgraph.prompts import (
    get_persona_text, FRANZ_PERSONA,
)
from backend.agents.sdr_langgraph.tools import load_rag
from backend.agents.sdr_langgraph.agent import agent_system_overlay

rag_context = load_rag("franz")
print()
print('=== RAG carregado (load_rag) ===')
print('  len:', len(rag_context))
print('  preview (first 300):', rag_context[:300])
print()
print('=== PERSONA TEXTO (consultivo) ===')
print('  len:', len(get_persona_text('consultivo')))
print('  preview (first 200):', get_persona_text('consultivo')[:200])

# Simula build do system
base = (
    get_persona_text('consultivo') + "\n\n" +
    agent_system_overlay({}) + "\n\n" +
    "[stage]\n\n" +
    rag_context
)
print()
print('=== BASE (persona + overlay + stage + rag) ===')
print('  len:', len(base))
print('  contains "biblioteca"?', 'biblioteca' in base.lower())
print('  contains "1499"?', '1499' in base)
print('  contains "RAG"?', 'RAG' in base)

full = build_sdr_system_prompt(base, settings_raw)
print()
print('=== FULL SYSTEM (com tenant block) ===')
print('  len:', len(full))
print('  contains "biblioteca"?', 'biblioteca' in full.lower())
print('  contains "1499"?', '1499' in full)
print('  contains "Sou o Franz"?', 'Sou o Franz' in full)
print('  contains "Sou Franz"?', 'Sou Franz' in full)
print('  contains "Hello, how"?', 'Hello, how' in full)
print('  contains "library"?', 'library' in full.lower())
print('  contains "book"?', 'book' in full.lower())
print('  contains "publishing"?', 'publishing' in full.lower())
print('  contains "publish"?', 'publish' in full.lower())
print('  contains "editora"?', 'editora' in full.lower())
print('  contains "site pronto"?', 'site pronto' in full.lower())
print('  contains "customer-facing"?', 'customer-facing' in full.lower())
print()
print('  --- preview first 1500 chars (PERSONA) ---')
print(full[:1500])
print()
print('  --- preview chars 1500-4500 (RAG) ---')
print(full[1500:4500])
print()
print('  --- preview last 500 chars (tenant block) ---')
print(full[-500:])
db.close()
