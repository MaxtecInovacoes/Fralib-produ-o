#!/usr/bin/env python3
"""Regenerate site with new patches."""

import sys
import os
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.services.openui_renderer import build_openui_document

# Test data - academia-pipeline-teste
facts = {
    "business": {
        "name": "Academia Pipeline Teste",
        "segment": "Academia de Musculação",
        "city": "Curitiba",
        "state": "PR",
        "phone": "41999998888",
        "whatsapp": "41999998888",
        "email": "contato@academia.com",
        "address": "Rua Teste 123, Curitiba, PR",
        "rating": "4.8",
        "hours": "06:00-22:00"
    },
    "contact": {
        "name": "João da Academia",
        "email": "joao@academia.com",
        "phone": "41999998888"
    }
}

# HTML content (simulado)
body_html = """
<div class="min-h-screen bg-gray-50">
  <header class="bg-white shadow-sm">
    <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex items-center">
          <h1 class="text-2xl font-bold text-gray-900">Academia Pipeline Teste</h1>
        </div>
      </div>
    </nav>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <section class="text-center py-20">
      <h2 class="text-4xl font-bold mb-6">Bem-vindo à Academia Pipeline Teste</h2>
      <p class="text-xl text-gray-600 mb-8">Transforme seu corpo, transforme sua vida</p>
      <img src="https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=1200&q=80" alt="Academia" class="rounded-lg shadow-lg mx-auto">
    </section>

    <section class="grid md:grid-cols-3 gap-8 my-16">
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-xl font-semibold mb-3">Musculação</h3>
        <p class="text-gray-600">Equipamentos modernos e atualizados</p>
      </div>
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-xl font-semibold mb-3">Aulas em Grupo</h3>
        <p class="text-gray-600">Spinning, Yoga, Zumba e muito mais</p>
      </div>
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-xl font-semibold mb-3">Personal Trainer</h3>
        <p class="text-gray-600">Profissionais qualificados para você</p>
      </div>
    </section>

    <section class="bg-blue-50 p-8 rounded-lg my-16">
      <h2 class="text-2xl font-bold mb-4">Horário de Funcionamento</h2>
      <p class="text-lg">Segunda a Sexta: 06:00 às 22:00</p>
      <p class="text-lg">Sábado: 08:00 às 20:00</p>
      <p class="text-lg">Domingo: 09:00 às 18:00</p>
    </section>

    <section class="text-center my-16">
      <h2 class="text-3xl font-bold mb-6">Entre em Contato</h2>
      <p class="text-xl mb-4">Rua Teste 123, Curitiba, PR</p>
      <p class="text-xl mb-4">WhatsApp: (41) 99999-8888</p>
      <p class="text-xl">contato@academia.com</p>
    </section>
  </main>

  <footer class="bg-gray-800 text-white py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
      <p>&copy; 2025 Academia Pipeline Teste. Todos os direitos reservados.</p>
    </div>
  </footer>
</div>
"""

# Generate document
document = build_openui_document(body_html, facts=facts)

# Save to file
output_path = ROOT / "academia-pipeline-teste-new.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(document)

print(f"Site gerado em: {output_path}")
print(f"Tamanho: {len(document)} bytes")

# Quick validation
checks = [
    ("twitter:title", "name=\"twitter:title\"" in document.lower()),
    ("twitter:card", "name=\"twitter:card\"" in document.lower()),
    ("twitter:description", "name=\"twitter:description\"" in document.lower()),
    ("Preload LCP", "rel=\"preload\" as=\"image\"" in document.lower()),
    ("Skip link count", document.count("Pular para o conteúdo")),
    ("CSS :has()", ":has(" in document),
    ("CSS color-mix()", "color-mix(" in document),
    ("CSS @container", "@container" in document),
    ("CSS subgrid", "subgrid" in document),
    ("prefers-reduced-motion", "prefers-reduced-motion" in document),
    ("LGPD banner", "data-lgpd-banner" in document),
    ("Motion runtime", "data-parallax" in document or "data-reveal" in document)
]

print("\n=== VALIDAÇÃO ===")
for name, check in checks:
    status = "✅" if check else "❌"
    print(f"{status} {name}: {check}")