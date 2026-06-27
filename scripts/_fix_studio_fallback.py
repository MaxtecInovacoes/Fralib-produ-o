#!/usr/bin/env python3
"""Fix studio fallback: make segment-aware + fix literal \n."""
import re

filepath = '/root/fralib/backend/services/vite_react_renderer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'def _generate_studio_fallback_files(facts'
end_marker = '    return prepare_vite_project_files(files, facts=safe_facts)\n\n\ndef extract_requested'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f'ERROR: markers not found. start={start_idx}, end={end_idx}')
    exit(1)

print(f'Found function at {start_idx}-{end_idx}, len={end_idx-start_idx}')

new_func = '''def _generate_studio_fallback_files(facts: dict[str, Any] | None = None) -> dict[str, str]:
    """Compatibility fallback for tests and emergency local Studio rendering."""
    safe_facts = facts or {}
    business = safe_facts.get("business") if isinstance(safe_facts.get("business"), dict) else {}
    name = business.get("name") or safe_facts.get("name") or "FraLib"
    phone = str(business.get("whatsapp") or business.get("phone") or "41999999999")
    rating = str(business.get("rating") or "4.8")
    city = str(business.get("city") or business.get("cidade") or safe_facts.get("cidade") or "Curitiba")
    segment = str(business.get("segment") or business.get("segmento") or "servicos").lower()
    hero_img = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1600&q=82"
    gallery_img = "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=1400&q=82"

    # Sprint 12.14: segment-aware content (fixes hardcoded academia contamination)
    if "barbearia" in segment or "barbeiro" in segment:
        svc_labels = ["Corte", "Barba", "Sobrancelha", "Pigmentacao", "Hidratacao"]
        hero_desc = "Barbearia premium com barbeiros experientes, produtos importados e ambiente climatizado."
        cta_primary = "Agendar horario"
        cta_secondary = "Ver servicos"
        alt_img = "Barbeiro em barbearia"
        lifestyle_title = "Tradicao em cada corte"
        lifestyle_desc = "Um espaco dedicado ao cuidado masculino, com atendimento personalizado e toalhas quentes."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "academia" in segment or "fitness" in segment or "crossfit" in segment or "musculacao" in segment:
        svc_labels = ["Musculacao", "Treino funcional", "Spinning", "Crossfit", "Avaliacao"]
        hero_desc = "Academia completa com treino funcional, alunos acompanhados e ambiente moderno."
        cta_primary = "Comecar treino"
        cta_secondary = "Ver estrutura"
        alt_img = "Alunos em treino fitness"
        lifestyle_title = "Energia e constancia"
        lifestyle_desc = "Um espaco para criar rotina, encontrar orientacao e manter frequencia sem complicar."
        nav_items = [("Treinos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "restaurante" in segment or "bar" in segment or "caf" in segment:
        svc_labels = ["Pratos", "Menu", "Reservas", "Eventos", "Delivery"]
        hero_desc = "Restaurante com pratos feitos com ingredientes selecionados e ambiente acolhedor."
        cta_primary = "Fazer reserva"
        cta_secondary = "Ver menu"
        alt_img = "Restaurante"
        lifestyle_title = "Experiencia gastronomica"
        lifestyle_desc = "Cada prato preparado com cuidado para proporcionar uma experiencia unica."
        nav_items = [("Cardapio", "#servicos"), ("Galeria", "#galeria"), ("Reservar", "#contato")]
    elif "clinica" in segment or "estetica" in segment or "medic" in segment:
        svc_labels = ["Consulta", "Tratamento", "Avaliacao", "Procedimento", "Retorno"]
        hero_desc = "Clinica com profissionais experientes e tratamentos personalizados para seu bem-estar."
        cta_primary = "Agendar consulta"
        cta_secondary = "Conhecer servicos"
        alt_img = "Clinica"
        lifestyle_title = "Cuidado e acolhimento"
        lifestyle_desc = "Ambiente preparado para recebe-lo com conforto e seguranca em cada atendimento."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    elif "imobiliaria" in segment or "imoveis" in segment:
        svc_labels = ["Venda", "Locacao", "Avaliacao", "Consultoria", "Lancamentos"]
        hero_desc = "Imobiliaria com imoveis selecionados e atendimento personalizado para suas necessidades."
        cta_primary = "Ver imoveis"
        cta_secondary = "Falar corretor"
        alt_img = "Imovel"
        lifestyle_title = "Seu proximo imovel"
        lifestyle_desc = "Encontre o imovel ideal com quem entende do mercado local."
        nav_items = [("Imoveis", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]
    else:
        svc_labels = ["Servico 1", "Servico 2", "Servico 3", "Servico 4", "Servico 5"]
        hero_desc = f"{name}: servicos de qualidade com atendimento personalizado em {city}."
        cta_primary = "Saiba mais"
        cta_secondary = "Ver servicos"
        alt_img = f"{name}"
        lifestyle_title = "Experiencia unica"
        lifestyle_desc = f"Atendimento dedicado para garantir sua satisfacao em {city}."
        nav_items = [("Servicos", "#servicos"), ("Galeria", "#galeria"), ("Contato", "#contato")]

    def component(export_name: str, body: str, *, imports: str = "") -> str:
        return f"""{imports}
export function {export_name}() {{
{body}
}}

export default {export_name};
"""

    dense_cards = "\n".join(
        f'<div className="rounded-3xl border border-white/10 bg-white/[.04] p-5 text-white"><strong className="block text-xl text-emerald-200">0{i}</strong><span className="text-sm text-zinc-300">{svc_labels[i-1]}</span></div>'
        for i in range(1, 6)
    )
    nav_links = "\n".join(
        f'<a className="hover:text-white" href="{href}">{label}</a>'
        for label, href in nav_items
    )
    services_articles = "\n".join(
        f'<article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">{svc_labels[i]}</h3><p className="mt-3 text-zinc-400">Atendimento de qualidade.</p></article>'
        for i in range(min(3, len(svc_labels)))
    )

    files = {
        "src/components/Navbar.tsx": component(
            "Navbar",
            f"""  const [open, setOpen] = useState(false);
  useEffect(() => {{
    const onScroll = () => setOpen(window.scrollY > 24);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);
  return (
    <nav className={{`fixed inset-x-4 top-4 z-50 rounded-3xl border px-5 py-3 backdrop-blur ${{open ? 'border-white/20 bg-zinc-950/90' : 'border-white/10 bg-white/5'}}`}}>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <a className="min-w-0 truncate text-sm font-black uppercase tracking-[0.24em] text-emerald-200" href="#top">{name}</a>
        <div className="hidden items-center gap-5 text-sm text-zinc-200 md:flex">
          {nav_links}
        </div>
        <a className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-bold text-zinc-950 max-sm:px-3 max-sm:text-xs" href="tel:{phone}">{cta_primary}</a>
      </div>
    </nav>
  );
""",
            imports="import { useEffect, useState } from 'react';",
        ),
        "src/components/HeroSection.tsx": component(
            "HeroSection",
            f"""  useEffect(() => {{
    gsap.fromTo('[data-hero-copy]', {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7 }});
  }}, []);
  return (
    <section id="top" className="relative isolate overflow-hidden bg-zinc-950 px-6 pb-24 pt-36 text-white">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,.24),transparent_32%),linear-gradient(135deg,#050505,#101827)]" />
      <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[1.05fr_.95fr]">
        <motion.div data-hero-copy initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} className="space-y-7">
          <p className="inline-flex rounded-full border border-emerald-300/30 bg-emerald-300/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.24em] text-emerald-200">{segment} em {city}</p>
          <h1 className="text-[clamp(3rem,8vw,6.6rem)] font-black leading-[.9] tracking-[-.07em]">{name}</h1>
          <p className="max-w-2xl text-lg leading-8 text-zinc-300">{hero_desc}</p>
          <div className="flex flex-wrap gap-3">
            <a className="rounded-full bg-emerald-300 px-6 py-3 font-black text-zinc-950" href="tel:{phone}">{cta_primary}</a>
            <a className="rounded-full border border-white/20 px-6 py-3 font-semibold text-white" href="#galeria">{cta_secondary}</a>
          </div>
          <div className="grid max-w-lg grid-cols-3 gap-3 text-sm">{dense_cards}</div>
        </motion.div>
        <div className="relative"><img className="aspect-[4/5] w-full rounded-[2rem] object-cover shadow-2xl ring-1 ring-white/10" src="{hero_img}" alt="{alt_img}" loading="eager" decoding="async" /></div>
      </div>
    </section>
  );
""",
            imports="import { motion } from 'motion/react';\nimport gsap from 'gsap';\nimport { useEffect } from 'react';",
        ),
        "src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Nossos servicos</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;"""),
        "src/components/GallerySection.tsx": component("GallerySection", f"""  return <section id="galeria" className="bg-zinc-900 px-6 py-24 text-white"><div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-2"><img className="h-96 w-full rounded-[2rem] object-cover" src="{hero_img}" alt="{alt_img}" loading="lazy" decoding="async" /><img className="h-96 w-full rounded-[2rem] object-cover" src="{gallery_img}" alt="{alt_img}" loading="lazy" decoding="async" /></div></section>;"""),
        "src/components/LifestyleSection.tsx": component("LifestyleSection", f"""  return <section className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl rounded-[2rem] border border-white/10 bg-emerald-300/10 p-8"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">experiencia</p><h2 className="mt-3 text-4xl font-black">{lifestyle_title}</h2><p className="mt-4 max-w-3xl text-zinc-300">{lifestyle_desc}</p></div></section>;"""),
        "src/components/BookingModal.tsx": component("BookingModal", f"""  const [open, setOpen] = useState(false);
  return <div className="bg-zinc-950 px-6 py-12 text-center text-white"><button className="rounded-full bg-white px-6 py-3 font-black text-zinc-950" onClick={{() => setOpen(true)}}>Falar no WhatsApp</button>{{open && <div className="fixed inset-0 z-[80] grid place-items-center bg-black/70 p-6"><div className="max-w-md rounded-3xl bg-white p-6 text-left text-zinc-950"><h3 className="text-2xl font-black">Fale com {name}</h3><p className="mt-3">Telefone {phone}. {name}, avaliacao {rating} em {city}.</p><button className="mt-5 rounded-full bg-zinc-950 px-5 py-2 text-white" onClick={{() => setOpen(false)}}>Fechar</button></div></div>}}</div>;""", imports="import { useState } from 'react';"),
        "src/components/ContactCTA.tsx": component("ContactCTA", f"""  return <section id="contato" className="bg-emerald-300 px-6 py-20 text-zinc-950"><div className="mx-auto flex max-w-6xl flex-col gap-5 md:flex-row md:items-center md:justify-between"><div><p className="text-sm font-bold uppercase tracking-[0.2em]">contato</p><h2 className="text-4xl font-black">Entre em contato</h2><p className="mt-2 font-semibold">WhatsApp {phone} - avaliacao {rating} em {city}</p></div><a className="rounded-full bg-zinc-950 px-7 py-4 font-black text-white" href="tel:{phone}">Ligar agora</a></div></section>;"""),
        "src/components/Footer.tsx": component("Footer", f"""  return <footer className="bg-zinc-950 px-6 py-10 text-zinc-400"><div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4"><span className="font-bold text-white">{name}</span><span>{segment} - {city} - {phone}</span></div></footer>;"""),
        "src/pages/Index.tsx": """import { Navbar } from '../components/Navbar';
import { HeroSection } from '../components/HeroSection';
import { ServicesSection } from '../components/ServicesSection';
import { GallerySection } from '../components/GallerySection';
import { LifestyleSection } from '../components/LifestyleSection';
import { BookingModal } from '../components/BookingModal';
import { ContactCTA } from '../components/ContactCTA';
import { Footer } from '../components/Footer';

export default function Index() {
  return <main className="min-h-screen bg-zinc-950 text-zinc-50"><Navbar /><HeroSection /><ServicesSection /><GallerySection /><LifestyleSection /><BookingModal /><ContactCTA /><Footer /></main>;
}
""",
    }
    return prepare_vite_project_files(files, facts=safe_facts)


def extract_requested'''

new_content = content[:start_idx] + new_func + content[end_idx:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f'OK: replaced {end_idx-start_idx} chars with {len(new_func)} chars')
print(f'Total file size: {len(new_content)}')
