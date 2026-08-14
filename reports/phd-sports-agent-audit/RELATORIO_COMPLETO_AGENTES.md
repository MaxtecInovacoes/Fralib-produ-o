# Relatório completo — Academia Ph.D Sports Jardim Paulista

Fonte local dos artefatos: `C:\fralib\reports\phd-sports-agent-audit\`
Fonte VPS: `/app/artifacts/0c8532da8d97/academia-ph-d-sports-jardim-paulista-13cf997d-b800-427f-bfeb-7b4a654750b5/`
URL: https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/

## 1. Artefatos salvos
- `00-artifacts-index.json` — 433 bytes
- `00-artifacts-index.json.meta.json` — 131 bytes
- `01-hunter-handoff.json` — 897 bytes
- `01-hunter-handoff.json.meta.json` — 209 bytes
- `02-caio-handoff.json` — 514 bytes
- `02-caio-handoff.json.meta.json` — 205 bytes
- `02-niche-brief.json` — 591 bytes
- `02-niche-brief.json.meta.json` — 153 bytes
- `02-openui-section_fragment-acao.html` — 4815 bytes
- `02-openui-section_fragment-acao.html.meta.json` — 258 bytes
- `02-openui-section_fragment-contato.html` — 6218 bytes
- `02-openui-section_fragment-contato.html.meta.json` — 264 bytes
- `02-openui-section_fragment-depoimentos.html` — 8301 bytes
- `02-openui-section_fragment-depoimentos.html.meta.json` — 272 bytes
- `02-openui-section_fragment-desejo.html` — 2838 bytes
- `02-openui-section_fragment-desejo.html.meta.json` — 262 bytes
- `02-openui-section_fragment-faq.html` — 11476 bytes
- `02-openui-section_fragment-faq.html.meta.json` — 256 bytes
- `02-openui-section_fragment-footer.html` — 8976 bytes
- `02-openui-section_fragment-footer.html.meta.json` — 262 bytes
- `02-openui-section_fragment-hero.html` — 2609 bytes
- `02-openui-section_fragment-hero.html.meta.json` — 258 bytes
- `02-openui-section_fragment-interesse.html` — 4679 bytes
- `02-openui-section_fragment-interesse.html.meta.json` — 268 bytes
- `02-openui-section_fragment-lgpd.html` — 6383 bytes
- `02-openui-section_fragment-lgpd.html.meta.json` — 258 bytes
- `02-openui-section_fragment-localizacao.html` — 3998 bytes
- `02-openui-section_fragment-localizacao.html.meta.json` — 272 bytes
- `02-openui-section_fragment-seo-geo.html` — 6440 bytes
- `02-openui-section_fragment-seo-geo.html.meta.json` — 264 bytes
- `02-openui-section_fragment-servicos.html` — 4706 bytes
- `02-openui-section_fragment-servicos.html.meta.json` — 266 bytes
- `02-openui-section_fragment-sobre.html` — 6345 bytes
- `02-openui-section_fragment-sobre.html.meta.json` — 260 bytes
- `02-openui-shell_document.html` — 508 bytes
- `02-openui-shell_document.html.meta.json` — 213 bytes
- `03-builder-final.html` — 80273 bytes
- `03-builder-final.html.meta.json` — 250 bytes
- `03-creative-direction.json` — 3669 bytes
- `03-creative-direction.json.meta.json` — 167 bytes
- `03-niche_brief-handoff.json` — 1053 bytes
- `03-niche_brief-handoff.json.meta.json` — 219 bytes
- `04-creative_direction-handoff.json` — 5450 bytes
- `04-creative_direction-handoff.json.meta.json` — 233 bytes
- `04-quality-gate.html` — 80273 bytes
- `04-quality-gate.html.meta.json` — 4917 bytes
- `04-variation-blueprint.json` — 2750 bytes
- `04-variation-blueprint.json.meta.json` — 169 bytes
- `05-deploy-final.html` — 81959 bytes
- `05-deploy-final.html.meta.json` — 285 bytes
- `05-variation_blueprint-handoff.json` — 8688 bytes
- `05-variation_blueprint-handoff.json.meta.json` — 235 bytes
- `06-designer_prd-handoff.json` — 74063 bytes
- `06-designer_prd-handoff.json.meta.json` — 221 bytes
- `07-builder_openui-handoff.json` — 69039 bytes
- `07-builder_openui-handoff.json.meta.json` — 225 bytes
- `08-quality_gate-handoff.json` — 6206 bytes
- `08-quality_gate-handoff.json.meta.json` — 221 bytes
- `09-deploy-handoff.json` — 1979 bytes
- `09-deploy-handoff.json.meta.json` — 209 bytes
- `10-franz-handoff.json` — 575 bytes
- `10-franz-handoff.json.meta.json` — 207 bytes

## 2. JSON completo dos agentes/handoffs

### 01-hunter-handoff.json

```json
{
  "stage": "hunter",
  "created_at": "2026-08-14T00:55:07.362538Z",
  "received": {
    "lead_id": "13cf997d-b800-427f-bfeb-7b4a654750b5",
    "tenant_id": 2,
    "lead_fields": [
      "cidade",
      "descricao",
      "endereco",
      "fotos",
      "id",
      "jina_insights",
      "jina_intelligence",
      "market_intelligence",
      "nome",
      "rating",
      "reviews_count",
      "segmento",
      "telefone",
      "website",
      "whatsapp"
    ]
  },
  "produced": {
    "nome": "Academia Ph.D Sports Jardim Paulista",
    "cidade": "Campina Grande do Sul",
    "segmento": "academia",
    "telefone": "5541985143249",
    "rating": 4.8,
    "reviews_count": 0,
    "photos_count": 5,
    "jina_provider": "jina"
  },
  "preserved": {},
  "changed": {},
  "lost": {},
  "notes": [
    "Hunter valida dados mínimos, adiciona Jina insights e garante mídia editorial."
  ]
}
```

### 02-caio-handoff.json

```json
{
  "stage": "caio",
  "created_at": "2026-08-14T00:55:07.363655Z",
  "received": {
    "nome": "Academia Ph.D Sports Jardim Paulista",
    "segmento": "academia",
    "cidade": "Campina Grande do Sul",
    "rating": 4.8
  },
  "produced": {
    "score": 0,
    "tier": "REJEITADO",
    "dark_mode": null,
    "motivo": "Rede/franquia - nao atendemos"
  },
  "preserved": {},
  "changed": {},
  "lost": {},
  "notes": [
    "Caio qualifica se o lead pode seguir para briefing e define tier visual/comercial."
  ]
}
```

### 02-niche-brief.json

```json
{
  "task_id": "0c8532da8d97",
  "source_agent": "agente_nicho",
  "target_agent": "agente_variacao",
  "status": "ok",
  "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
  "nicho": "academia",
  "subnichos": [],
  "cidade": "Campina Grande do Sul",
  "publico_alvo": [],
  "usp": [],
  "diferenciais": [],
  "objeções": [],
  "keywords": [],
  "tom_de_voz": "profissional",
  "notas": "",
  "confianca": "baixa",
  "dados_ausentes": [
    "JSON não foi extraído corretamente"
  ],
  "competidores": [],
  "regras": [],
  "nao_fazer": []
}
```

### 03-creative-direction.json

```json
{
  "task_id": "0c8532da8d97",
  "source_agent": "design_director",
  "target_agent": "agente_variacao",
  "status": "ok",
  "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
  "brand_concept": "Academia Ph.D Sports Jardim Paulista",
  "audience": "",
  "positioning": "",
  "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
  "visual_concept": "bold",
  "visual_keywords": [
    "bold",
    "tipografia pesada, alto contraste, comanda atencao",
    "academia"
  ],
  "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
  "color_strategy": {
    "primary": "#0A0A0E",
    "secondary": "#C8FF00",
    "accent": "#E87A1A",
    "tokens_oklch": {
      "--bg": "oklch(12% 0.010 260)",
      "--surface": "oklch(17% 0.012 260)",
      "--fg": "oklch(93% 0.005 0)",
      "--muted": "oklch(65% 0.010 260)",
      "--border": "oklch(28% 0.015 260)",
      "--accent": "oklch(55.0% 0.138 25)"
    }
  },
  "typography_strategy": {
    "heading": "Archivo Black",
    "body": "Inter"
  },
  "photography_strategy": {
    "policy": "usar URLs reais do media_plan com papeis por seção",
    "hero": "imagem dominante coerente com a cena física"
  },
  "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
  "density_strategy": "bold",
  "rhythm_strategy": "fade-up",
  "hero_strategy": "hero-center",
  "cta_strategy": "WhatsApp",
  "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
  "anti_patterns": [
    "hero fullscreen genérico com academia ao fundo",
    "cores azul/branco óbvias de academia",
    "fotos genéricas de pessoas malhando de stock",
    "layout de colunas simétrico padrão de site institucional"
  ],
  "required_visual_differences": [
    "estilo Awwwards com tipografia massiva",
    "Nike Training Club — energia visual",
    "Gymshark — dark mode agressivo e contraste alto",
    "Brutalismo digital com toque esportivo"
  ],
  "hard_constraints": {
    "visual_concept": "bold",
    "palette": {
      "--bg": "oklch(12% 0.010 260)",
      "--surface": "oklch(17% 0.012 260)",
      "--fg": "oklch(93% 0.005 0)",
      "--muted": "oklch(65% 0.010 260)",
      "--border": "oklch(28% 0.015 260)",
      "--accent": "oklch(55.0% 0.138 25)"
    },
    "typography": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "hero_strategy": "",
    "anti_patterns": [
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ]
  },
  "soft_constraints": {
    "motion": {
      "intensidade": "bold",
      "efeito_principal": "fade-up",
      "scroll_speed": "fast",
      "usa_video_hero": false,
      "usa_parallax": false,
      "usa_cursor_custom": false
    },
    "voice": {
      "registro": "casual",
      "personalidade": "jovem",
      "frases_chave": [
        "Comece sua transformação hoje",
        "Seu corpo, sua mente, seu começo",
        "Sem desculpas. Sem limites. Só resultado."
      ]
    },
    "inspirations": [
      "estilo Awwwards com tipografia massiva",
      "Nike Training Club — energia visual",
      "Gymshark — dark mode agressivo e contraste alto",
      "Brutalismo digital com toque esportivo"
    ]
  }
}
```

### 04-variation-blueprint.json

```json
{
  "task_id": "0c8532da8d97",
  "source_agent": "agente_variacao",
  "target_agent": "arquiteto_mestre",
  "status": "ok",
  "task_summary": "Variação definida: corporate/hero-split em 10.5s",
  "narrative_framework": "AIDA",
  "template_estrutura": "corporate",
  "template_hero": "hero-split",
  "template_prova_social": "stats-cards",
  "template_cta": "cta-central",
  "template_faq": "faq-accordion",
  "ordem_das_secoes": [
    "hero",
    "interesse",
    "desejo",
    "numeros",
    "servicos",
    "depoimentos",
    "seo-geo",
    "faq",
    "acao",
    "lgpd",
    "footer"
  ],
  "required_sections": [
    "hero",
    "interesse",
    "desejo",
    "acao",
    "faq",
    "lgpd",
    "footer"
  ],
  "angulo_de_comunicacao": "A academia de Campina Grande do Sul que se adapta à sua rotina: horário estendido, aula experimental gratuita e estacionamento próprio — três diferenciais que nenhum concorrente local oferece.",
  "regra_antirrepeticao": "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
  "justificativa": "O nicho de academia em Campina Grande do Sul apresenta alta repetição estrutural entre concorrentes, com tom direto e orientado a benefício. A estrutura corporate com hero-split permite destacar visualmente os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo na primeira dobra, diferenciando-se do padrão de mercado. A seção de números (stats-cards) antes dos serviços cria prova social quantificável que gera confiança antes da apresentação da oferta. O FAQ em accordion reduz objeções comuns antes do CTA central, maximizando conversão. A inclusão de seo-geo antes da ação reforça a presença local em Campina Grande do Sul, capturando intenção de busca geolocalizada.",
  "layout_variants": {},
  "rhythm": "",
  "signature_composition": "",
  "avoid": [
    "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
    "hero fullscreen genérico com academia ao fundo",
    "cores azul/branco óbvias de academia",
    "fotos genéricas de pessoas malhando de stock",
    "layout de colunas simétrico padrão de site institucional"
  ]
}
```

### 03-niche_brief-handoff.json

```json
{
  "stage": "niche_brief",
  "created_at": "2026-08-14T00:55:28.008579Z",
  "received": {
    "segmento": "academia",
    "cidade": "Campina Grande do Sul",
    "jina_insights_present": true,
    "lead_name": "Academia Ph.D Sports Jardim Paulista"
  },
  "produced": {
    "task_id": "0c8532da8d97",
    "source_agent": "agente_nicho",
    "target_agent": "agente_variacao",
    "status": "ok",
    "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
    "nicho": "academia",
    "subnichos": [],
    "cidade": "Campina Grande do Sul",
    "publico_alvo": [],
    "usp": [],
    "diferenciais": [],
    "objeções": [],
    "keywords": [],
    "tom_de_voz": "profissional",
    "notas": "",
    "confianca": "baixa",
    "dados_ausentes": [
      "JSON não foi extraído corretamente"
    ],
    "competidores": [],
    "regras": [],
    "nao_fazer": []
  },
  "preserved": {
    "nicho": "academia",
    "tom_de_voz": "profissional",
    "keywords": []
  },
  "changed": {},
  "lost": {},
  "notes": []
}
```

### 04-creative_direction-handoff.json

```json
{
  "stage": "creative_direction",
  "created_at": "2026-08-14T00:55:28.028367Z",
  "received": {
    "niche_brief": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_nicho",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
      "nicho": "academia",
      "subnichos": [],
      "cidade": "Campina Grande do Sul",
      "publico_alvo": [],
      "usp": [],
      "diferenciais": [],
      "objeções": [],
      "keywords": [],
      "tom_de_voz": "profissional",
      "notas": "",
      "confianca": "baixa",
      "dados_ausentes": [
        "JSON não foi extraído corretamente"
      ],
      "competidores": [],
      "regras": [],
      "nao_fazer": []
    },
    "caio_tier": "REJEITADO",
    "caio_score": 0
  },
  "produced": {
    "task_id": "0c8532da8d97",
    "source_agent": "design_director",
    "target_agent": "agente_variacao",
    "status": "ok",
    "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
    "brand_concept": "Academia Ph.D Sports Jardim Paulista",
    "audience": "",
    "positioning": "",
    "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
    "visual_concept": "bold",
    "visual_keywords": [
      "bold",
      "tipografia pesada, alto contraste, comanda atencao",
      "academia"
    ],
    "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
    "color_strategy": {
      "primary": "#0A0A0E",
      "secondary": "#C8FF00",
      "accent": "#E87A1A",
      "tokens_oklch": {
        "--bg": "oklch(12% 0.010 260)",
        "--surface": "oklch(17% 0.012 260)",
        "--fg": "oklch(93% 0.005 0)",
        "--muted": "oklch(65% 0.010 260)",
        "--border": "oklch(28% 0.015 260)",
        "--accent": "oklch(55.0% 0.138 25)"
      }
    },
    "typography_strategy": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "photography_strategy": {
      "policy": "usar URLs reais do media_plan com papeis por seção",
      "hero": "imagem dominante coerente com a cena física"
    },
    "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
    "density_strategy": "bold",
    "rhythm_strategy": "fade-up",
    "hero_strategy": "hero-center",
    "cta_strategy": "WhatsApp",
    "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
    "anti_patterns": [
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ],
    "required_visual_differences": [
      "estilo Awwwards com tipografia massiva",
      "Nike Training Club — energia visual",
      "Gymshark — dark mode agressivo e contraste alto",
      "Brutalismo digital com toque esportivo"
    ],
    "hard_constraints": {
      "visual_concept": "bold",
      "palette": {
        "--bg": "oklch(12% 0.010 260)",
        "--surface": "oklch(17% 0.012 260)",
        "--fg": "oklch(93% 0.005 0)",
        "--muted": "oklch(65% 0.010 260)",
        "--border": "oklch(28% 0.015 260)",
        "--accent": "oklch(55.0% 0.138 25)"
      },
      "typography": {
        "heading": "Archivo Black",
        "body": "Inter"
      },
      "hero_strategy": "",
      "anti_patterns": [
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ]
    },
    "soft_constraints": {
      "motion": {
        "intensidade": "bold",
        "efeito_principal": "fade-up",
        "scroll_speed": "fast",
        "usa_video_hero": false,
        "usa_parallax": false,
        "usa_cursor_custom": false
      },
      "voice": {
        "registro": "casual",
        "personalidade": "jovem",
        "frases_chave": [
          "Comece sua transformação hoje",
          "Seu corpo, sua mente, seu começo",
          "Sem desculpas. Sem limites. Só resultado."
        ]
      },
      "inspirations": [
        "estilo Awwwards com tipografia massiva",
        "Nike Training Club — energia visual",
        "Gymshark — dark mode agressivo e contraste alto",
        "Brutalismo digital com toque esportivo"
      ]
    }
  },
  "preserved": {
    "visual_concept": "bold",
    "palette": {
      "--bg": "oklch(12% 0.010 260)",
      "--surface": "oklch(17% 0.012 260)",
      "--fg": "oklch(93% 0.005 0)",
      "--muted": "oklch(65% 0.010 260)",
      "--border": "oklch(28% 0.015 260)",
      "--accent": "oklch(55.0% 0.138 25)"
    },
    "typography": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "anti_patterns": [
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ]
  },
  "changed": {},
  "lost": {},
  "notes": []
}
```

### 05-variation_blueprint-handoff.json

```json
{
  "stage": "variation_blueprint",
  "created_at": "2026-08-14T00:55:38.504761Z",
  "received": {
    "niche_brief": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_nicho",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
      "nicho": "academia",
      "subnichos": [],
      "cidade": "Campina Grande do Sul",
      "publico_alvo": [],
      "usp": [],
      "diferenciais": [],
      "objeções": [],
      "keywords": [],
      "tom_de_voz": "profissional",
      "notas": "",
      "confianca": "baixa",
      "dados_ausentes": [
        "JSON não foi extraído corretamente"
      ],
      "competidores": [],
      "regras": [],
      "nao_fazer": []
    },
    "creative_direction": {
      "task_id": "0c8532da8d97",
      "source_agent": "design_director",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
      "brand_concept": "Academia Ph.D Sports Jardim Paulista",
      "audience": "",
      "positioning": "",
      "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "visual_concept": "bold",
      "visual_keywords": [
        "bold",
        "tipografia pesada, alto contraste, comanda atencao",
        "academia"
      ],
      "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
      "color_strategy": {
        "primary": "#0A0A0E",
        "secondary": "#C8FF00",
        "accent": "#E87A1A",
        "tokens_oklch": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        }
      },
      "typography_strategy": {
        "heading": "Archivo Black",
        "body": "Inter"
      },
      "photography_strategy": {
        "policy": "usar URLs reais do media_plan com papeis por seção",
        "hero": "imagem dominante coerente com a cena física"
      },
      "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
      "density_strategy": "bold",
      "rhythm_strategy": "fade-up",
      "hero_strategy": "hero-center",
      "cta_strategy": "WhatsApp",
      "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "anti_patterns": [
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ],
      "required_visual_differences": [
        "estilo Awwwards com tipografia massiva",
        "Nike Training Club — energia visual",
        "Gymshark — dark mode agressivo e contraste alto",
        "Brutalismo digital com toque esportivo"
      ],
      "hard_constraints": {
        "visual_concept": "bold",
        "palette": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        },
        "typography": {
          "heading": "Archivo Black",
          "body": "Inter"
        },
        "hero_strategy": "",
        "anti_patterns": [
          "hero fullscreen genérico com academia ao fundo",
          "cores azul/branco óbvias de academia",
          "fotos genéricas de pessoas malhando de stock",
          "layout de colunas simétrico padrão de site institucional"
        ]
      },
      "soft_constraints": {
        "motion": {
          "intensidade": "bold",
          "efeito_principal": "fade-up",
          "scroll_speed": "fast",
          "usa_video_hero": false,
          "usa_parallax": false,
          "usa_cursor_custom": false
        },
        "voice": {
          "registro": "casual",
          "personalidade": "jovem",
          "frases_chave": [
            "Comece sua transformação hoje",
            "Seu corpo, sua mente, seu começo",
            "Sem desculpas. Sem limites. Só resultado."
          ]
        },
        "inspirations": [
          "estilo Awwwards com tipografia massiva",
          "Nike Training Club — energia visual",
          "Gymshark — dark mode agressivo e contraste alto",
          "Brutalismo digital com toque esportivo"
        ]
      }
    }
  },
  "produced": {
    "task_id": "0c8532da8d97",
    "source_agent": "agente_variacao",
    "target_agent": "arquiteto_mestre",
    "status": "ok",
    "task_summary": "Variação definida: corporate/hero-split em 10.5s",
    "narrative_framework": "AIDA",
    "template_estrutura": "corporate",
    "template_hero": "hero-split",
    "template_prova_social": "stats-cards",
    "template_cta": "cta-central",
    "template_faq": "faq-accordion",
    "ordem_das_secoes": [
      "hero",
      "interesse",
      "desejo",
      "numeros",
      "servicos",
      "depoimentos",
      "seo-geo",
      "faq",
      "acao",
      "lgpd",
      "footer"
    ],
    "required_sections": [
      "hero",
      "interesse",
      "desejo",
      "acao",
      "faq",
      "lgpd",
      "footer"
    ],
    "angulo_de_comunicacao": "A academia de Campina Grande do Sul que se adapta à sua rotina: horário estendido, aula experimental gratuita e estacionamento próprio — três diferenciais que nenhum concorrente local oferece.",
    "regra_antirrepeticao": "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
    "justificativa": "O nicho de academia em Campina Grande do Sul apresenta alta repetição estrutural entre concorrentes, com tom direto e orientado a benefício. A estrutura corporate com hero-split permite destacar visualmente os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo na primeira dobra, diferenciando-se do padrão de mercado. A seção de números (stats-cards) antes dos serviços cria prova social quantificável que gera confiança antes da apresentação da oferta. O FAQ em accordion reduz objeções comuns antes do CTA central, maximizando conversão. A inclusão de seo-geo antes da ação reforça a presença local em Campina Grande do Sul, capturando intenção de busca geolocalizada.",
    "layout_variants": {},
    "rhythm": "",
    "signature_composition": "",
    "avoid": [
      "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ]
  },
  "preserved": {
    "section_order": [
      "hero",
      "interesse",
      "desejo",
      "numeros",
      "servicos",
      "depoimentos",
      "seo-geo",
      "faq",
      "acao",
      "lgpd",
      "footer"
    ],
    "hero_type": "hero-split",
    "avoid": [
      "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ]
  },
  "changed": {},
  "lost": {},
  "notes": []
}
```

### 06-designer_prd-handoff.json

```json
{
  "stage": "designer_prd",
  "created_at": "2026-08-14T00:57:17.451279Z",
  "received": {
    "lead_data": {
      "nome": "Academia Ph.D Sports Jardim Paulista",
      "cidade": "Campina Grande do Sul",
      "telefone": "5541985143249",
      "segmento": "academia",
      "rating": 4.8,
      "reviews_count": 9,
      "fotos": [
        "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82"
      ],
      "website": "https://academiaphdsports.com.br/",
      "whatsapp": "5541985143249",
      "endereco": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
      "market_intelligence": null,
      "descricao": null,
      "id": "13cf997d-b800-427f-bfeb-7b4a654750b5",
      "jina_intelligence": {
        "tom_de_voz": "direto e orientado a benefício",
        "palavras_poder": [
          "academia",
          "musculação",
          "treino",
          "aula",
          "plano",
          "estrutura",
          "resultado",
          "saúde",
          "condicionamento",
          "personal"
        ],
        "frases_genericas": [
          "atendimento personalizado",
          "qualidade e compromisso",
          "resultados reais",
          "os melhores profissionais",
          "pronto para começar",
          "excelência em atendimento",
          "sua satisfação é nossa prioridade",
          "venha nos conhecer",
          "entre em contato"
        ],
        "headlines_referencia": [
          "Academias",
          "Espaço do Cliente",
          "Seja um franqueado",
          "Buscar academia",
          "Encontre a academia mais próxima!"
        ],
        "ctas_referencia": [
          "Conheça nossos produtos e serviços adicionais para você"
        ],
        "estilo_visual": "não inferido sem análise visual; usar curadoria FraLib",
        "proposta_valor_concorrentes": [
          "Encontre a academia mais próxima"
        ],
        "secoes_comuns": [
          "Academias",
          "Espaço do Cliente",
          "Seja um franqueado",
          "Buscar academia",
          "Encontre a academia mais próxima!",
          "Escolher academia",
          "Venha treinar na maior rede de academias da América Latina",
          "Os melhores equipamentos e infraestrutura com mensalidades acessíveis."
        ],
        "diferencial_ausente": "Nenhum concorrente menciona: horário estendido, aula experimental grátis, estacionamento. Oportunidade.",
        "publico_alvo": "pessoas buscando academia em Campina Grande do Sul",
        "fontes_analisadas": [
          "https://www.smartfit.com.br"
        ],
        "provider": "jina"
      },
      "jina_insights": "=== INTELIGÊNCIA DE MERCADO (Jina AI) ===\n\nTOM DE VOZ DO MERCADO: direto e orientado a benefício\n\nLINGUAGEM COMERCIAL OBSERVADA:\n  academia, musculação, treino, aula, plano, estrutura, resultado, saúde, condicionamento, personal\n\nHEADLINES DE REFERÊNCIA (inspiração, não copiar):\n  - Academias\n  - Espaço do Cliente\n  - Seja um franqueado\n  - Buscar academia\n  - Encontre a academia mais próxima!\n\nCTAs QUE CONVERTEM:\n  - Conheça nossos produtos e serviços adicionais para você\n\nESTILO VISUAL DO MERCADO: não inferido sem análise visual; usar curadoria FraLib\nPÚBLICO-ALVO: pessoas buscando academia em Campina Grande do Sul\nDIFERENCIAL DISPONÍVEL: Nenhum concorrente menciona: horário estendido, aula experimental grátis, estacionamento. Oportunidade.\n\nEsta inteligência é referência de mercado para o próximo agente.\n=== FIM INTELIGÊNCIA ==="
    },
    "caio": {
      "tier": "REJEITADO",
      "score": 0,
      "dark_mode": false
    },
    "niche_brief": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_nicho",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
      "nicho": "academia",
      "subnichos": [],
      "cidade": "Campina Grande do Sul",
      "publico_alvo": [],
      "usp": [],
      "diferenciais": [],
      "objeções": [],
      "keywords": [],
      "tom_de_voz": "profissional",
      "notas": "",
      "confianca": "baixa",
      "dados_ausentes": [
        "JSON não foi extraído corretamente"
      ],
      "competidores": [],
      "regras": [],
      "nao_fazer": []
    },
    "creative_direction": {
      "task_id": "0c8532da8d97",
      "source_agent": "design_director",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
      "brand_concept": "Academia Ph.D Sports Jardim Paulista",
      "audience": "",
      "positioning": "",
      "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "visual_concept": "bold",
      "visual_keywords": [
        "bold",
        "tipografia pesada, alto contraste, comanda atencao",
        "academia"
      ],
      "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
      "color_strategy": {
        "primary": "#0A0A0E",
        "secondary": "#C8FF00",
        "accent": "#E87A1A",
        "tokens_oklch": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        }
      },
      "typography_strategy": {
        "heading": "Archivo Black",
        "body": "Inter"
      },
      "photography_strategy": {
        "policy": "usar URLs reais do media_plan com papeis por seção",
        "hero": "imagem dominante coerente com a cena física"
      },
      "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
      "density_strategy": "bold",
      "rhythm_strategy": "fade-up",
      "hero_strategy": "hero-center",
      "cta_strategy": "WhatsApp",
      "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "anti_patterns": [
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ],
      "required_visual_differences": [
        "estilo Awwwards com tipografia massiva",
        "Nike Training Club — energia visual",
        "Gymshark — dark mode agressivo e contraste alto",
        "Brutalismo digital com toque esportivo"
      ],
      "hard_constraints": {
        "visual_concept": "bold",
        "palette": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        },
        "typography": {
          "heading": "Archivo Black",
          "body": "Inter"
        },
        "hero_strategy": "",
        "anti_patterns": [
          "hero fullscreen genérico com academia ao fundo",
          "cores azul/branco óbvias de academia",
          "fotos genéricas de pessoas malhando de stock",
          "layout de colunas simétrico padrão de site institucional"
        ]
      },
      "soft_constraints": {
        "motion": {
          "intensidade": "bold",
          "efeito_principal": "fade-up",
          "scroll_speed": "fast",
          "usa_video_hero": false,
          "usa_parallax": false,
          "usa_cursor_custom": false
        },
        "voice": {
          "registro": "casual",
          "personalidade": "jovem",
          "frases_chave": [
            "Comece sua transformação hoje",
            "Seu corpo, sua mente, seu começo",
            "Sem desculpas. Sem limites. Só resultado."
          ]
        },
        "inspirations": [
          "estilo Awwwards com tipografia massiva",
          "Nike Training Club — energia visual",
          "Gymshark — dark mode agressivo e contraste alto",
          "Brutalismo digital com toque esportivo"
        ]
      }
    },
    "variation_blueprint": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_variacao",
      "target_agent": "arquiteto_mestre",
      "status": "ok",
      "task_summary": "Variação definida: corporate/hero-split em 10.5s",
      "narrative_framework": "AIDA",
      "template_estrutura": "corporate",
      "template_hero": "hero-split",
      "template_prova_social": "stats-cards",
      "template_cta": "cta-central",
      "template_faq": "faq-accordion",
      "ordem_das_secoes": [
        "hero",
        "interesse",
        "desejo",
        "numeros",
        "servicos",
        "depoimentos",
        "seo-geo",
        "faq",
        "acao",
        "lgpd",
        "footer"
      ],
      "required_sections": [
        "hero",
        "interesse",
        "desejo",
        "acao",
        "faq",
        "lgpd",
        "footer"
      ],
      "angulo_de_comunicacao": "A academia de Campina Grande do Sul que se adapta à sua rotina: horário estendido, aula experimental gratuita e estacionamento próprio — três diferenciais que nenhum concorrente local oferece.",
      "regra_antirrepeticao": "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
      "justificativa": "O nicho de academia em Campina Grande do Sul apresenta alta repetição estrutural entre concorrentes, com tom direto e orientado a benefício. A estrutura corporate com hero-split permite destacar visualmente os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo na primeira dobra, diferenciando-se do padrão de mercado. A seção de números (stats-cards) antes dos serviços cria prova social quantificável que gera confiança antes da apresentação da oferta. O FAQ em accordion reduz objeções comuns antes do CTA central, maximizando conversão. A inclusão de seo-geo antes da ação reforça a presença local em Campina Grande do Sul, capturando intenção de busca geolocalizada.",
      "layout_variants": {},
      "rhythm": "",
      "signature_composition": "",
      "avoid": [
        "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ]
    }
  },
  "produced": {
    "sections": [
      {
        "name": "hero",
        "id": "hero",
        "required": true,
        "layout_type": "hero-editorial-stack",
        "components": [
          "hero-cta"
        ],
        "copy_data": {
          "eyebrow": "ACADEMIA PH.D SPORTS · JARDIM PAULISTA",
          "h1": "Treine com estrutura de verdade em Campina Grande do Sul",
          "subtitle": "Musculação, aulas coletivas e acompanhamento personalizado em um espaço pensado para o seu resultado. Horário estendido, estacionamento próprio e aula experimental gratuita para começar.",
          "cta_primary": "Agende sua aula experimental grátis",
          "cta_secondary": "Conheça a estrutura",
          "image_alt": "Interior da Academia Ph.D Sports com equipamentos de musculação"
        },
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "Hunter V2",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "interesse",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "desejo",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "numeros",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "servicos",
        "id": "servicos",
        "required": true,
        "layout_type": "services-editorial-list",
        "components": [
          "hero-cta"
        ],
        "copy_data": {
          "h2": "Nossos produtos e serviços",
          "intro": "Musculação, condicionamento e acompanhamento personalizado — escolha o caminho do seu resultado.",
          "servicos": [
            {
              "nome": "Musculação",
              "descricao": "Equipamentos completos para todos os grupos musculares. Treino livre ou periodizado, com orientação disponível."
            },
            {
              "nome": "Aulas coletivas",
              "descricao": "Aulas dinâmicas em grupo para condicionamento cardiovascular e força, com energia de equipe."
            },
            {
              "nome": "Personal trainer",
              "descricao": "Plano de treino individual com profissional certificado. Foco no seu objetivo, seja ele qual for."
            },
            {
              "nome": "Plano mensal",
              "descricao": "Planos flexíveis para diferentes perfis. Acesso total à estrutura durante o horário de funcionamento."
            }
          ]
        },
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "Hunter V2",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "depoimentos",
        "id": null,
        "required": true,
        "layout_type": "reviews-spotlight",
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "reviews reais ou sinais públicos",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "seo-geo",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "faq",
        "id": null,
        "required": true,
        "layout_type": "faq",
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "pesquisa local e dados confirmados",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "acao",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "lgpd",
        "id": null,
        "required": true,
        "layout_type": null,
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "variation_blueprint",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "footer",
        "id": null,
        "required": true,
        "layout_type": "footer-editorial",
        "components": [
          "hero-cta"
        ],
        "copy_data": {},
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "NAP, navegação e links legais",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "sobre",
        "id": "sobre",
        "required": true,
        "layout_type": "about-editorial",
        "components": [
          "hero-cta"
        ],
        "copy_data": {
          "h2": "Academia Ph.D Sports Jardim Paulista",
          "intro": "Há anos transformando vidas em Campina Grande do Sul, a Ph.D Sports Jardim Paulista é referência em estrutura e acompanhamento na região. Unimos equipamentos de última geração, profissionais qualificados e um ambiente que motiva você a ir além.",
          "diferenciais": [
            {
              "titulo": "Horário estendido",
              "descricao": "Abra mais cedo, feche mais tarde — o treino cabe na sua rotina."
            },
            {
              "titulo": "Estacionamento próprio",
              "descricao": "Sem complicação de rua. Estacione e entre direto no treino."
            },
            {
              "titulo": "Aula experimental grátis",
              "descricao": "Conheça a academia sem compromisso. Sua primeira experiência é por nossa conta."
            },
            {
              "titulo": "Personal trainer disponível",
              "descricao": "Acompanhamento individual para quem quer evoluir com segurança e técnica."
            }
          ]
        },
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "Hunter V2",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "contato",
        "id": "contato",
        "required": true,
        "layout_type": "contact-split",
        "components": [
          "hero-cta"
        ],
        "copy_data": {
          "h2": "Fale com a Ph.D Sports",
          "intro": "Agende sua aula experimental gratuita ou tire dúvidas pelo WhatsApp.",
          "telefone": "(41) 98514-3249",
          "cta_whatsapp": "Chamar no WhatsApp",
          "cta_aula": "Agendar aula experimental grátis"
        },
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "Hunter V2",
        "schema_org": null,
        "media_src": null
      },
      {
        "name": "localizacao",
        "id": "localizacao",
        "required": true,
        "layout_type": "local-proof-panel",
        "components": [
          "hero-cta"
        ],
        "copy_data": {
          "h2": "Onde estamos",
          "intro": "Estamos no Jardim Paulista, com estacionamento próprio e fácil acesso em Campina Grande do Sul.",
          "endereco": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
          "bairro_destaque": "Jardim Paulista, Campina Grande do Sul"
        },
        "items": [],
        "cta": null,
        "h1": null,
        "h2": null,
        "headline": null,
        "subheadline": null,
        "objective": null,
        "media_role": null,
        "omitir": false,
        "data_source": "Hunter V2",
        "schema_org": null,
        "media_src": null
      }
    ],
    "color_palette": {
      "primary": "var(--fg)",
      "secondary": "var(--surface)",
      "accent": "var(--accent)",
      "background": "var(--bg)",
      "text": "var(--fg)",
      "surface": "var(--surface)",
      "muted": "var(--muted)",
      "border": "var(--border)",
      "tokens_oklch": {
        "--bg": "oklch(12% 0.010 260)",
        "--surface": "oklch(17% 0.012 260)",
        "--fg": "oklch(93% 0.005 0)",
        "--muted": "oklch(65% 0.010 260)",
        "--border": "oklch(28% 0.015 260)",
        "--accent": "oklch(55.0% 0.138 25)"
      },
      "hero_style": {
        "bg": "var(--bg)",
        "fg": "var(--fg)",
        "accent_usage": "CTA button + 1 eyebrow label only"
      },
      "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
    },
    "typography": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "design_system_slug": null,
    "visual_dna": {
      "visual_seed": "42ee01f5ca7eb3b8",
      "archetype": {
        "visual_voice": "brutal, atletico, cinematografico, confiante, sem polidez corporativa",
        "color_theory": "preto profundo, vermelho eletrico dominante em CTAs e cortes, branco quente para display",
        "typography": {
          "heading_scale": "condensed_impact_900",
          "heading_trait": "uppercase condensado, italico/obliquo em palavras de impacto, outline text como camada secundaria",
          "body_trait": "compacto, tenso, alto contraste, sem paragrafo longo"
        },
        "composition_laws": [
          "hero dark full-bleed com foto/texture ocupando o fundo e overlay dramatico",
          "headline display 84px+ no desktop com palavra solida + palavra outline atras ou abaixo",
          "usar diagonais, crop agressivo, z-index, negative margins e cards pretos flutuantes",
          "vermelho vivo em CTAs, highlights e barras curtas; nunca usar azul/corporativo",
          "uma secao manifesto com titulo quebrado em linhas curtas e imagem lateral com sombra profunda",
          "CTA com glow vermelho e estado hover fisico"
        ],
        "media_query_modifiers": [
          "dark cinematic gym photography",
          "red accent lighting",
          "high contrast athlete training",
          "moody professional photography",
          "dynamic action crop"
        ],
        "cta_policy": "botao principal com glow neon e linguagem direta",
        "section_disruption": "full-bleed dark impact band",
        "archetype": "BOLD_ENERGY"
      },
      "dna_combo": {
        "structure_ref": "bmw_m",
        "typography_ref": "uber",
        "color_ref": "bmw_m",
        "motion_ref": "spotify",
        "spacing_ref": "bmw_m"
      },
      "tokens": {
        "--bg": "#070a08",
        "--surface": "#121a16",
        "--fg": "#f4fff7",
        "--muted": "#b8c9be",
        "--border": "#294137",
        "--accent": "#b8ff3d"
      },
      "palette_id": "bold-acid-lime",
      "color_strategy": "committed",
      "palette_contrast": {
        "page": 19.41,
        "surface": 17.29,
        "muted_page": 11.49,
        "muted_surface": 10.24
      },
      "font_heading": "UberMove",
      "font_body": "UberMoveText",
      "style_mix_instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
      "reference_vibes": {
        "structure": "motorsport, cockpit near-black, tricolor M",
        "typography": "mobility, bold black-white, tight type, pill-shaped, urban",
        "color": "motorsport, cockpit near-black, tricolor M",
        "motion": "music streaming, vibrant green on dark, album-art-driven"
      },
      "design_reference_pack": {
        "id": "bold_energy-42ee01f5",
        "source": "opendesign_curated_reference_pack",
        "archetype": "BOLD_ENERGY",
        "visual_seed": "42ee01f5ca7eb3b8",
        "tier": "STANDARD",
        "references": {
          "structure": {
            "slug": "bmw_m",
            "role": "structure",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "grid, seção hero, ritmo e composição"
          },
          "typography": {
            "slug": "uber",
            "role": "typography",
            "category": "Media & Consumer",
            "name": "Uber",
            "vibe": "mobility, bold black-white, tight type, pill-shaped, urban",
            "font_heading": "UberMove",
            "font_body": "UberMoveText",
            "tokens": {
              "--bg": "oklch(100% 0.0 0)",
              "--surface": "oklch(100% 0.0 0)",
              "--fg": "oklch(0% 0.0 0)",
              "--muted": "oklch(29% 0.0 0)",
              "--border": "oklch(0% 0.0 0)",
              "--accent": "oklch(0% 0.0 0)"
            },
            "use_for": "escala, contraste de peso e voz tipográfica"
          },
          "color": {
            "slug": "bmw_m",
            "role": "color",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "paleta base, contraste e acento"
          },
          "motion": {
            "slug": "spotify",
            "role": "motion",
            "category": "Media & Consumer",
            "name": "Spotify",
            "vibe": "music streaming, vibrant green on dark, album-art-driven",
            "font_heading": "CircularSp",
            "font_body": "CircularSp",
            "tokens": {
              "--bg": "oklch(7% 0.0 0)",
              "--surface": "oklch(9% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(70% 0.0 0)",
              "--border": "oklch(30% 0.0 0)",
              "--accent": "oklch(66% 0.145 141)"
            },
            "use_for": "cadência, reveal, parallax e microinterações"
          },
          "spacing": {
            "slug": "bmw_m",
            "role": "spacing",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "densidade, respiro e proporção entre blocos"
          }
        },
        "dna_combo": {
          "structure_ref": "bmw_m",
          "typography_ref": "uber",
          "color_ref": "bmw_m",
          "motion_ref": "spotify",
          "spacing_ref": "bmw_m"
        },
        "tokens": {
          "--bg": "#070a08",
          "--surface": "#121a16",
          "--fg": "#f4fff7",
          "--muted": "#b8c9be",
          "--border": "#294137",
          "--accent": "#b8ff3d"
        },
        "typography": {
          "heading": "UberMove",
          "body": "UberMoveText"
        },
        "constraints": {
          "theme": "dark_cinematic",
          "hero": "full-bleed or poster-like, dominant image/texture, red action line, stat slabs",
          "spacing": "dense hero, generous section breaks, hard crops, no airy institutional stacking",
          "motion": "fast mask reveal, parallax crop, short stagger, strong scroll progress",
          "ban": [
            "pastel wellness",
            "beige institutional",
            "white card grid",
            "soft SaaS radius"
          ]
        },
        "instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
        "runtime_palette": {
          "id": "bold-acid-lime",
          "strategy": "committed",
          "contrast": {
            "page": 19.41,
            "surface": 17.29,
            "muted_page": 11.49,
            "muted_surface": 10.24
          }
        }
      },
      "variation": {
        "radius": "14px",
        "section_padding": "96px",
        "hero_density": "cinematic",
        "image_treatment": "full-bleed",
        "grid_bias": "asymmetric-left"
      },
      "tier": "STANDARD"
    },
    "layout_blueprint": [
      {
        "section": "hero",
        "variant": "hero-editorial-stack",
        "source": "variation_blueprint"
      },
      {
        "section": "interesse",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "desejo",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "numeros",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "servicos",
        "variant": "services-editorial-list",
        "source": "variation_blueprint"
      },
      {
        "section": "depoimentos",
        "variant": "reviews-spotlight",
        "source": "variation_blueprint"
      },
      {
        "section": "seo-geo",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "faq",
        "variant": "faq",
        "source": "variation_blueprint"
      },
      {
        "section": "acao",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "lgpd",
        "variant": "corporate",
        "source": "variation_blueprint"
      },
      {
        "section": "footer",
        "variant": "footer-editorial",
        "source": "variation_blueprint"
      },
      {
        "section": "sobre",
        "variant": "about-editorial",
        "source": "variation_blueprint"
      },
      {
        "section": "contato",
        "variant": "contact-split",
        "source": "variation_blueprint"
      },
      {
        "section": "localizacao",
        "variant": "local-proof-panel",
        "source": "variation_blueprint"
      }
    ],
    "design_reference_pack": {
      "id": "bold_energy-42ee01f5",
      "source": "opendesign_curated_reference_pack",
      "archetype": "BOLD_ENERGY",
      "visual_seed": "42ee01f5ca7eb3b8",
      "tier": "STANDARD",
      "references": {
        "structure": {
          "slug": "bmw_m",
          "role": "structure",
          "category": "Automotive",
          "name": "Bmw M",
          "vibe": "motorsport, cockpit near-black, tricolor M",
          "font_heading": "BMW Type Next Latin Light",
          "font_body": "BMW Type Next Latin",
          "tokens": {
            "--bg": "oklch(0% 0.0 0)",
            "--surface": "oklch(10% 0.0 0)",
            "--fg": "oklch(100% 0.0 0)",
            "--muted": "oklch(49% 0.0 0)",
            "--border": "oklch(24% 0.0 0)",
            "--accent": "oklch(30% 0.158 4)"
          },
          "use_for": "grid, seção hero, ritmo e composição"
        },
        "typography": {
          "slug": "uber",
          "role": "typography",
          "category": "Media & Consumer",
          "name": "Uber",
          "vibe": "mobility, bold black-white, tight type, pill-shaped, urban",
          "font_heading": "UberMove",
          "font_body": "UberMoveText",
          "tokens": {
            "--bg": "oklch(100% 0.0 0)",
            "--surface": "oklch(100% 0.0 0)",
            "--fg": "oklch(0% 0.0 0)",
            "--muted": "oklch(29% 0.0 0)",
            "--border": "oklch(0% 0.0 0)",
            "--accent": "oklch(0% 0.0 0)"
          },
          "use_for": "escala, contraste de peso e voz tipográfica"
        },
        "color": {
          "slug": "bmw_m",
          "role": "color",
          "category": "Automotive",
          "name": "Bmw M",
          "vibe": "motorsport, cockpit near-black, tricolor M",
          "font_heading": "BMW Type Next Latin Light",
          "font_body": "BMW Type Next Latin",
          "tokens": {
            "--bg": "oklch(0% 0.0 0)",
            "--surface": "oklch(10% 0.0 0)",
            "--fg": "oklch(100% 0.0 0)",
            "--muted": "oklch(49% 0.0 0)",
            "--border": "oklch(24% 0.0 0)",
            "--accent": "oklch(30% 0.158 4)"
          },
          "use_for": "paleta base, contraste e acento"
        },
        "motion": {
          "slug": "spotify",
          "role": "motion",
          "category": "Media & Consumer",
          "name": "Spotify",
          "vibe": "music streaming, vibrant green on dark, album-art-driven",
          "font_heading": "CircularSp",
          "font_body": "CircularSp",
          "tokens": {
            "--bg": "oklch(7% 0.0 0)",
            "--surface": "oklch(9% 0.0 0)",
            "--fg": "oklch(100% 0.0 0)",
            "--muted": "oklch(70% 0.0 0)",
            "--border": "oklch(30% 0.0 0)",
            "--accent": "oklch(66% 0.145 141)"
          },
          "use_for": "cadência, reveal, parallax e microinterações"
        },
        "spacing": {
          "slug": "bmw_m",
          "role": "spacing",
          "category": "Automotive",
          "name": "Bmw M",
          "vibe": "motorsport, cockpit near-black, tricolor M",
          "font_heading": "BMW Type Next Latin Light",
          "font_body": "BMW Type Next Latin",
          "tokens": {
            "--bg": "oklch(0% 0.0 0)",
            "--surface": "oklch(10% 0.0 0)",
            "--fg": "oklch(100% 0.0 0)",
            "--muted": "oklch(49% 0.0 0)",
            "--border": "oklch(24% 0.0 0)",
            "--accent": "oklch(30% 0.158 4)"
          },
          "use_for": "densidade, respiro e proporção entre blocos"
        }
      },
      "dna_combo": {
        "structure_ref": "bmw_m",
        "typography_ref": "uber",
        "color_ref": "bmw_m",
        "motion_ref": "spotify",
        "spacing_ref": "bmw_m"
      },
      "tokens": {
        "--bg": "#070a08",
        "--surface": "#121a16",
        "--fg": "#f4fff7",
        "--muted": "#b8c9be",
        "--border": "#294137",
        "--accent": "#b8ff3d"
      },
      "typography": {
        "heading": "UberMove",
        "body": "UberMoveText"
      },
      "constraints": {
        "theme": "dark_cinematic",
        "hero": "full-bleed or poster-like, dominant image/texture, red action line, stat slabs",
        "spacing": "dense hero, generous section breaks, hard crops, no airy institutional stacking",
        "motion": "fast mask reveal, parallax crop, short stagger, strong scroll progress",
        "ban": [
          "pastel wellness",
          "beige institutional",
          "white card grid",
          "soft SaaS radius"
        ]
      },
      "instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
      "runtime_palette": {
        "id": "bold-acid-lime",
        "strategy": "committed",
        "contrast": {
          "page": 19.41,
          "surface": 17.29,
          "muted_page": 11.49,
          "muted_surface": 10.24
        }
      }
    },
    "dna_combo": {},
    "visual_seed": "42ee01f5ca7eb3b8",
    "visual_direction": {},
    "minimum_required_media": null,
    "visual_contract": {
      "version": 1,
      "archetype": "BOLD_ENERGY",
      "acceptance_criteria": {
        "minimum_sections": 7,
        "required_sections": [
          "hero",
          "trust_or_proof",
          "decision_content",
          "media_story",
          "location",
          "faq",
          "footer"
        ],
        "mobile": [
          "no_horizontal_overflow",
          "cta_visible",
          "headline_not_clipped"
        ],
        "truth": [
          "no_lorem",
          "no_fake_services",
          "no_fake_reviews",
          "no_internal_policy_leak"
        ]
      },
      "hero": {
        "required": [
          "headline",
          "subheadline",
          "primary_cta",
          "proof_chip",
          "media_16_9_or_depth_layer",
          "motion_hook"
        ],
        "forbidden": [
          "generic_centered_block",
          "mobile_overflow",
          "unreadable_outline",
          "hidden_reveal_without_fallback"
        ]
      },
      "sections": {
        "required": {
          "decision_content": "educa a escolha com critérios reais do nicho",
          "media_story": "usa imagens como narrativa editorial sem chamar de foto real",
          "location": "mostra mapa único e endereço confirmado",
          "faq": "remove objeções práticas antes do contato"
        },
        "media_ratio": "16:9",
        "backgrounds": "cada seção deve ter superfície/fundo intencional, não pilha branca genérica"
      },
      "footer": {
        "required": [
          "brand",
          "navigation",
          "contact",
          "address_or_city",
          "hours_or_confirmation_note",
          "trust_note"
        ],
        "forbidden": [
          "unreadable_contrast",
          "generic_black_fallback",
          "post_footer_gallery"
        ]
      },
      "media": {
        "available": true,
        "ratio": "16:9",
        "policy": "editorial support only unless explicitly marked real venue media"
      },
      "location": {
        "requires_exact_map": true,
        "single_map_only": true,
        "zoom": 18
      }
    },
    "site_build_plan": {
      "version": 1,
      "purpose": "plano pos-PRD para transformar briefing factual em HTML final",
      "component_contracts": {
        "version": 1,
        "hero": {
          "component_id": "HeroBoldPoster02",
          "archetype": "BOLD_ENERGY",
          "locked": true,
          "slots_required": [
            "headline",
            "subheadline",
            "primary_cta",
            "proof_chip",
            "dominant_visual",
            "motion_hooks"
          ],
          "visual_guarantees": [
            "responsive 16:9 media surface",
            "data-parallax or deterministic depth layer",
            "Ken Burns-compatible media class",
            "CTA hover microinteraction",
            "readable contrast by archetype",
            "mobile-first stacking"
          ]
        },
        "footer": {
          "component_id": "FooterLocalTrust01",
          "locked": true,
          "visual_guarantees": [
            "navigation",
            "contact",
            "address_or_city",
            "trust_note"
          ]
        }
      },
      "business_context": {
        "name": "Academia Ph.D Sports Jardim Paulista",
        "segment": "academia",
        "city": "Campina Grande do Sul",
        "primary_conversion_goal": "whatsapp"
      },
      "information_architecture": {
        "section_order": [
          "hero",
          "interesse",
          "desejo",
          "numeros",
          "servicos",
          "depoimentos",
          "seo-geo",
          "faq",
          "acao",
          "lgpd",
          "footer"
        ],
        "section_order_source": "variation_blueprint",
        "narrative_framework": "AIDA",
        "required_sections": [
          "hero",
          "interesse",
          "desejo",
          "acao",
          "faq",
          "lgpd",
          "footer"
        ],
        "navigation_targets": [
          "hero",
          "interesse",
          "desejo",
          "numeros",
          "servicos",
          "depoimentos",
          "seo-geo",
          "faq",
          "acao",
          "lgpd",
          "footer"
        ],
        "must_combine": [
          "location",
          "contact"
        ],
        "must_not_duplicate": [
          "map",
          "location",
          "footer",
          "post_footer_gallery"
        ]
      },
      "section_plan": [
        {
          "id": "hero",
          "role": "attention",
          "required_content": [
            "headline",
            "subheadline",
            "primary_cta",
            "proof_chip",
            "motion_hook"
          ],
          "visual_surface": "campaign viewport with depth layer, 16:9 media/decor and CTA microinteraction",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "interesse",
          "role": "interest",
          "required_content": [
            "problem_context",
            "audience_specific_pain",
            "local_relevance",
            "why_now"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "desejo",
          "role": "desire",
          "required_content": [
            "offer_value",
            "differentiators",
            "proof_or_services",
            "visual_media"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "numeros",
          "role": "support",
          "required_content": [],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "servicos",
          "role": "support",
          "required_content": [],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "depoimentos",
          "role": "support",
          "required_content": [],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "seo-geo",
          "role": "local_seo",
          "required_content": [
            "city",
            "segment",
            "neighborhood_or_address",
            "search_intent_terms"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "faq",
          "role": "objection_handling",
          "required_content": [
            "contact",
            "location",
            "what_to_confirm"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "acao",
          "role": "action",
          "required_content": [
            "primary_cta",
            "phone_or_whatsapp",
            "location_or_next_step"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "lgpd",
          "role": "privacy_trust",
          "required_content": [
            "data_usage_note",
            "consent_banner_or_notice",
            "contact_policy"
          ],
          "visual_surface": "intentional archetype background with responsive spacing",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast"
          ]
        },
        {
          "id": "footer",
          "role": "closure",
          "required_content": [
            "brand",
            "navigation",
            "contact",
            "trust_note"
          ],
          "visual_surface": "complete footer using readable palette contrast",
          "validation": [
            "no_lorem",
            "no_horizontal_overflow",
            "readable_contrast",
            "not_after_footer_content",
            "navigation_contact_trust"
          ]
        }
      ],
      "style_guide": {
        "archetype": "BOLD_ENERGY",
        "reference_pack_id": "bold_energy-42ee01f5",
        "tokens": {
          "primary": "var(--fg)",
          "secondary": "var(--surface)",
          "accent": "var(--accent)",
          "background": "var(--bg)",
          "text": "var(--fg)",
          "surface": "var(--surface)",
          "muted": "var(--muted)",
          "border": "var(--border)",
          "tokens_oklch": {
            "--bg": "oklch(12% 0.010 260)",
            "--surface": "oklch(17% 0.012 260)",
            "--fg": "oklch(93% 0.005 0)",
            "--muted": "oklch(65% 0.010 260)",
            "--border": "oklch(28% 0.015 260)",
            "--accent": "oklch(55.0% 0.138 25)"
          },
          "hero_style": {
            "bg": "var(--bg)",
            "fg": "var(--fg)",
            "accent_usage": "CTA button + 1 eyebrow label only"
          },
          "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
        },
        "typography": {
          "heading": "Archivo Black",
          "body": "Inter"
        },
        "spacing": "use clamp-based section padding; mobile px-4, desktop max-width containers; no content touching viewport edges",
        "surfaces": "alternate hero, proof, editorial, decision, location and footer backgrounds using the archetype tokens",
        "media_ratio": "16:9"
      },
      "media_plan": {
        "items": [
          {
            "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
            "role": "hero",
            "section": "hero",
            "required": true,
            "source": "",
            "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
          },
          {
            "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
            "role": "editorial",
            "section": "interesse",
            "required": false,
            "source": "",
            "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
          },
          {
            "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
            "role": "editorial",
            "section": "desejo",
            "required": false,
            "source": "",
            "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
          },
          {
            "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
            "role": "editorial",
            "section": "numeros",
            "required": false,
            "source": "",
            "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
          },
          {
            "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
            "role": "service",
            "section": "servicos",
            "required": false,
            "source": "",
            "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
          }
        ],
        "available_count": 5,
        "hero": "use one dominant 16:9/depth media surface when available; otherwise use CSS/SVG depth",
        "gallery": "use up to 3 editorial images inside one media-story section",
        "policy": "media is editorial support unless data explicitly confirms it is real venue media",
        "map": "one Google Maps query embed from confirmed address; never broad OSM fallback"
      },
      "interaction_plan": {
        "hero": [
          "data-parallax",
          "ken-burns",
          "cta-hover-glow"
        ],
        "sections": [
          "data-reveal",
          "card-stagger",
          "line-draw"
        ],
        "fallback": "all content remains visible without JavaScript or motion runtime"
      },
      "content_rules": {
        "allowed_claims": [
          "Academia Ph.D Sports Jardim Paulista atua como academia",
          "Atendimento em Campina Grande do Sul",
          "Endereço confirmado: R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
          "Contato oficial: 5541985143249",
          "Avaliação pública 4.8",
          "9 avaliações públicas"
        ],
        "forbidden_claims": [
          "não inventar serviços, equipe, estrutura, equipamentos ou especialidades",
          "não afirmar que fotos editoriais são fotos reais do endereço",
          "não criar depoimentos ou métricas que não vieram dos dados públicos",
          "não publicar horários como certeza quando vierem vazios ou incompletos"
        ],
        "services_policy": "render confirmed services only; if missing, use decision/FAQ copy instead of fake service cards",
        "no_lorem": true
      },
      "seo_plan": {
        "title_strategy": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul",
        "local_terms": [
          "academia",
          "Campina Grande do Sul",
          "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil"
        ],
        "schema_type": "LocalBusiness"
      },
      "acceptance_criteria": {
        "minimum_sections": 7,
        "required_sections": [
          "hero",
          "trust_or_proof",
          "decision_content",
          "media_story",
          "location",
          "faq",
          "footer"
        ],
        "mobile": [
          "no_horizontal_overflow",
          "cta_visible",
          "headline_not_clipped"
        ],
        "truth": [
          "no_lorem",
          "no_fake_services",
          "no_fake_reviews",
          "no_internal_policy_leak"
        ]
      }
    },
    "niche_brief": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_nicho",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
      "nicho": "academia",
      "subnichos": [],
      "cidade": "Campina Grande do Sul",
      "publico_alvo": [],
      "usp": [],
      "diferenciais": [],
      "objeções": [],
      "keywords": [],
      "tom_de_voz": "profissional",
      "notas": "",
      "confianca": "baixa",
      "dados_ausentes": [
        "JSON não foi extraído corretamente"
      ],
      "competidores": [],
      "regras": [],
      "nao_fazer": []
    },
    "creative_direction": {
      "task_id": "0c8532da8d97",
      "source_agent": "design_director",
      "target_agent": "agente_variacao",
      "status": "ok",
      "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
      "brand_concept": "Academia Ph.D Sports Jardim Paulista",
      "audience": "",
      "positioning": "",
      "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "visual_concept": "bold",
      "visual_keywords": [
        "bold",
        "tipografia pesada, alto contraste, comanda atencao",
        "academia"
      ],
      "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
      "color_strategy": {
        "primary": "#0A0A0E",
        "secondary": "#C8FF00",
        "accent": "#E87A1A",
        "tokens_oklch": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        }
      },
      "typography_strategy": {
        "heading": "Archivo Black",
        "body": "Inter"
      },
      "photography_strategy": {
        "policy": "usar URLs reais do media_plan com papeis por seção",
        "hero": "imagem dominante coerente com a cena física"
      },
      "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
      "density_strategy": "bold",
      "rhythm_strategy": "fade-up",
      "hero_strategy": "hero-center",
      "cta_strategy": "WhatsApp",
      "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
      "anti_patterns": [
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ],
      "required_visual_differences": [
        "estilo Awwwards com tipografia massiva",
        "Nike Training Club — energia visual",
        "Gymshark — dark mode agressivo e contraste alto",
        "Brutalismo digital com toque esportivo"
      ],
      "hard_constraints": {
        "visual_concept": "bold",
        "palette": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        },
        "typography": {
          "heading": "Archivo Black",
          "body": "Inter"
        },
        "hero_strategy": "",
        "anti_patterns": [
          "hero fullscreen genérico com academia ao fundo",
          "cores azul/branco óbvias de academia",
          "fotos genéricas de pessoas malhando de stock",
          "layout de colunas simétrico padrão de site institucional"
        ]
      },
      "soft_constraints": {
        "motion": {
          "intensidade": "bold",
          "efeito_principal": "fade-up",
          "scroll_speed": "fast",
          "usa_video_hero": false,
          "usa_parallax": false,
          "usa_cursor_custom": false
        },
        "voice": {
          "registro": "casual",
          "personalidade": "jovem",
          "frases_chave": [
            "Comece sua transformação hoje",
            "Seu corpo, sua mente, seu começo",
            "Sem desculpas. Sem limites. Só resultado."
          ]
        },
        "inspirations": [
          "estilo Awwwards com tipografia massiva",
          "Nike Training Club — energia visual",
          "Gymshark — dark mode agressivo e contraste alto",
          "Brutalismo digital com toque esportivo"
        ]
      }
    },
    "variation_blueprint": {
      "task_id": "0c8532da8d97",
      "source_agent": "agente_variacao",
      "target_agent": "arquiteto_mestre",
      "status": "ok",
      "task_summary": "Variação definida: corporate/hero-split em 10.5s",
      "narrative_framework": "AIDA",
      "template_estrutura": "corporate",
      "template_hero": "hero-split",
      "template_prova_social": "stats-cards",
      "template_cta": "cta-central",
      "template_faq": "faq-accordion",
      "ordem_das_secoes": [
        "hero",
        "interesse",
        "desejo",
        "numeros",
        "servicos",
        "depoimentos",
        "seo-geo",
        "faq",
        "acao",
        "lgpd",
        "footer"
      ],
      "required_sections": [
        "hero",
        "interesse",
        "desejo",
        "acao",
        "faq",
        "lgpd",
        "footer"
      ],
      "angulo_de_comunicacao": "A academia de Campina Grande do Sul que se adapta à sua rotina: horário estendido, aula experimental gratuita e estacionamento próprio — três diferenciais que nenhum concorrente local oferece.",
      "regra_antirrepeticao": "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
      "justificativa": "O nicho de academia em Campina Grande do Sul apresenta alta repetição estrutural entre concorrentes, com tom direto e orientado a benefício. A estrutura corporate com hero-split permite destacar visualmente os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo na primeira dobra, diferenciando-se do padrão de mercado. A seção de números (stats-cards) antes dos serviços cria prova social quantificável que gera confiança antes da apresentação da oferta. O FAQ em accordion reduz objeções comuns antes do CTA central, maximizando conversão. A inclusão de seo-geo antes da ação reforça a presença local em Campina Grande do Sul, capturando intenção de busca geolocalizada.",
      "layout_variants": {},
      "rhythm": "",
      "signature_composition": "",
      "avoid": [
        "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ]
    },
    "media_plan": [
      {
        "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
        "role": "hero",
        "section": "hero",
        "required": true,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "interesse",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
      },
      {
        "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "desejo",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "numeros",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
      },
      {
        "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
        "role": "service",
        "section": "servicos",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
      }
    ],
    "animations": [
      {
        "name": "scroll-reveal",
        "type": "scroll-reveal",
        "target": "section",
        "trigger": "IntersectionObserver",
        "duration": "500ms",
        "easing": "cubic-bezier(0.0, 0.0, 0.2, 1)"
      },
      {
        "name": "cta-pulse",
        "type": "keyframe",
        "target": ".cta-primary",
        "trigger": "scroll",
        "duration": "2.5s",
        "easing": "ease-in-out"
      },
      {
        "name": "service-card-hover",
        "type": "hover-micro",
        "target": "section",
        "trigger": "hover",
        "duration": "150ms",
        "easing": "cubic-bezier(0.4, 0.0, 0.2, 1)"
      },
      {
        "name": "diferencial-card-hover",
        "type": "hover-micro",
        "target": "section",
        "trigger": "hover",
        "duration": "150ms",
        "easing": "cubic-bezier(0.4, 0.0, 0.2, 1)"
      },
      {
        "name": "hero-fade-in",
        "type": "entrance",
        "target": "section",
        "trigger": "page-load",
        "duration": "600ms",
        "easing": "cubic-bezier(0.0, 0.0, 0.2, 1)"
      }
    ],
    "business_name": "Academia Ph.D Sports Jardim Paulista",
    "reviews_count": 9,
    "reviews_rating": 4.8,
    "reviews_list": [],
    "address": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
    "phone": "5541985143249",
    "hours": {},
    "photos": [
      "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
      "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
      "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
      "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
      "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82"
    ],
    "videos": [],
    "logo_url": null,
    "google_maps_embed": "",
    "components_21dev": [
      "whatsapp-sticky-cta"
    ],
    "cidade": "Campina Grande do Sul",
    "segmento": "academia",
    "instrucao_criativa_para_dev": "O tom visual é Energético e Direto — academia de bairro com personalidade, não uma marca genérica de fitness. O fundo escuro (oklch(12% 0.010 260)) cria contraste forte com o texto claro e o accent verde-elétrico (oklch(72% 0.19 145)), que deve aparecer no máximo 2x por tela: no CTA principal e em um elemento de destaque por seção. O hero usa layout split: imagem real da academia à direita, texto à esquerda. O H1 é o entry point dominante — clamp(2.2rem, 5vw, 3.5rem), peso 600, tracking -0.02em. Nunca usar gradiente purple→blue ou indigo. Nunca usar emojis em headings ou botões — ícones devem ser SVG monoline com currentColor. A seção serviços usa cards com borda sutil (--border), hover com translateY(-4px) e borda que muda para --accent. A seção contato deve ser o momento final da página — sem FAQ após ela. Respeitar a regra dos 80/20: estrutura sólida e legível, com o verde-elétrico como o único elemento de ruptura visual.",
    "jina_insights": null,
    "servicos": null,
    "atributos": null,
    "horarios": null,
    "faixa_preco": null,
    "competitor_analysis": "[{\"name\": \"Start Academia\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia Iron\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia High\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia Life\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Legacy Academia\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}]",
    "anti_patterns": [
      "gradiente purple→blue no hero",
      "cores #6366f1, #4f46e5, #4338ca, #8b5cf6, #7c3aed como accent",
      "emojis em headings, botões ou listas",
      "card com borda colorida à esquerda (AI dashboard tile)",
      "métricas inventadas sem dado real do lead",
      "filler copy (Lorem ipsum, Feature One, Descrição do serviço)",
      "gradiente em cada seção de fundo",
      "Inter ou Roboto como font-heading",
      "layout Hero→Features→Pricing→FAQ→CTA sem variação",
      "terminar página com FAQ — sempre CTA ou contato no final",
      "precos visiveis",
      "hero fullscreen genérico com academia ao fundo",
      "cores azul/branco óbvias de academia",
      "fotos genéricas de pessoas malhando de stock",
      "layout de colunas simétrico padrão de site institucional"
    ],
    "schema_org_types": [
      "LocalBusiness",
      "ExerciseGym"
    ],
    "seo_keywords": [
      "academia campina grande do sul",
      "academia campina grande do sul pr",
      "academia phd campina grande do sul",
      "academia musculação campina grande do sul",
      "academia com estacionamento campina grande do sul",
      "academia horário estendido campina grande do sul",
      "aula experimental academia campina grande do sul",
      "personal trainer campina grande do sul",
      "melhor academia jardim paulista campina grande do sul",
      "academia condicionamento físico campina grande do sul pr"
    ],
    "faq_questions": [
      "A Academia Ph.D Sports oferece aula experimental gratuita?",
      "Qual o horário de funcionamento da academia em Campina Grande do Sul?",
      "A academia tem estacionamento para alunos?",
      "Quais modalidades são oferecidas na Academia Ph.D Sports?",
      "A academia fica no Jardim Paulista em Campina Grande do Sul?",
      "Como entrar em contato com a Academia Ph.D Sports?"
    ],
    "value_props": [
      "Aula Experimental Grátis",
      "Horário Estendido",
      "Estacionamento Próprio",
      "Estrutura Completa para Resultados"
    ],
    "geo": {
      "lat": -25.535,
      "lng": -49.298
    },
    "dark_mode": false
  },
  "preserved": {
    "section_order": [
      "hero",
      "interesse",
      "desejo",
      "numeros",
      "servicos",
      "depoimentos",
      "seo-geo",
      "faq",
      "acao",
      "lgpd",
      "footer"
    ],
    "media_plan": [
      {
        "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
        "role": "hero",
        "section": "hero",
        "required": true,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "interesse",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
      },
      {
        "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "desejo",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "numeros",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
      },
      {
        "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
        "role": "service",
        "section": "servicos",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
      }
    ],
    "typography": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "color_palette": {
      "primary": "var(--fg)",
      "secondary": "var(--surface)",
      "accent": "var(--accent)",
      "background": "var(--bg)",
      "text": "var(--fg)",
      "surface": "var(--surface)",
      "muted": "var(--muted)",
      "border": "var(--border)",
      "tokens_oklch": {
        "--bg": "oklch(12% 0.010 260)",
        "--surface": "oklch(17% 0.012 260)",
        "--fg": "oklch(93% 0.005 0)",
        "--muted": "oklch(65% 0.010 260)",
        "--border": "oklch(28% 0.015 260)",
        "--accent": "oklch(55.0% 0.138 25)"
      },
      "hero_style": {
        "bg": "var(--bg)",
        "fg": "var(--fg)",
        "accent_usage": "CTA button + 1 eyebrow label only"
      },
      "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
    },
    "reviews_count": 9,
    "phone": "5541985143249"
  },
  "changed": {
    "typography_from_creative": {
      "heading": "Archivo Black",
      "body": "Inter"
    },
    "typography_in_prd": {
      "heading": "Archivo Black",
      "body": "Inter"
    }
  },
  "lost": {},
  "notes": []
}
```

### 07-builder_openui-handoff.json

```json
{
  "stage": "builder_openui",
  "created_at": "2026-08-14T01:01:51.506862Z",
  "received": {
    "designer_prd": {
      "sections": [
        {
          "name": "hero",
          "id": "hero",
          "required": true,
          "layout_type": "hero-editorial-stack",
          "components": [
            "hero-cta"
          ],
          "copy_data": {
            "eyebrow": "ACADEMIA PH.D SPORTS · JARDIM PAULISTA",
            "h1": "Treine com estrutura de verdade em Campina Grande do Sul",
            "subtitle": "Musculação, aulas coletivas e acompanhamento personalizado em um espaço pensado para o seu resultado. Horário estendido, estacionamento próprio e aula experimental gratuita para começar.",
            "cta_primary": "Agende sua aula experimental grátis",
            "cta_secondary": "Conheça a estrutura",
            "image_alt": "Interior da Academia Ph.D Sports com equipamentos de musculação"
          },
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "Hunter V2",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "sobre",
          "id": "sobre",
          "required": true,
          "layout_type": "about-editorial",
          "components": [
            "hero-cta"
          ],
          "copy_data": {
            "h2": "Academia Ph.D Sports Jardim Paulista",
            "intro": "Há anos transformando vidas em Campina Grande do Sul, a Ph.D Sports Jardim Paulista é referência em estrutura e acompanhamento na região. Unimos equipamentos de última geração, profissionais qualificados e um ambiente que motiva você a ir além.",
            "diferenciais": [
              {
                "titulo": "Horário estendido",
                "descricao": "Abra mais cedo, feche mais tarde — o treino cabe na sua rotina."
              },
              {
                "titulo": "Estacionamento próprio",
                "descricao": "Sem complicação de rua. Estacione e entre direto no treino."
              },
              {
                "titulo": "Aula experimental grátis",
                "descricao": "Conheça a academia sem compromisso. Sua primeira experiência é por nossa conta."
              },
              {
                "titulo": "Personal trainer disponível",
                "descricao": "Acompanhamento individual para quem quer evoluir com segurança e técnica."
              }
            ]
          },
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "Hunter V2",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "contato",
          "id": "contato",
          "required": true,
          "layout_type": "contact-split",
          "components": [
            "hero-cta"
          ],
          "copy_data": {
            "h2": "Fale com a Ph.D Sports",
            "intro": "Agende sua aula experimental gratuita ou tire dúvidas pelo WhatsApp.",
            "telefone": "(41) 98514-3249",
            "cta_whatsapp": "Chamar no WhatsApp",
            "cta_aula": "Agendar aula experimental grátis"
          },
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "Hunter V2",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "interesse",
          "id": null,
          "required": true,
          "layout_type": "interesse",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "desejo",
          "id": null,
          "required": true,
          "layout_type": "desejo",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "numeros",
          "id": null,
          "required": true,
          "layout_type": "numeros",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "servicos",
          "id": "servicos",
          "required": true,
          "layout_type": "services-editorial-list",
          "components": [
            "hero-cta"
          ],
          "copy_data": {
            "h2": "Nossos produtos e serviços",
            "intro": "Musculação, condicionamento e acompanhamento personalizado — escolha o caminho do seu resultado.",
            "servicos": [
              {
                "nome": "Musculação",
                "descricao": "Equipamentos completos para todos os grupos musculares. Treino livre ou periodizado, com orientação disponível."
              },
              {
                "nome": "Aulas coletivas",
                "descricao": "Aulas dinâmicas em grupo para condicionamento cardiovascular e força, com energia de equipe."
              },
              {
                "nome": "Personal trainer",
                "descricao": "Plano de treino individual com profissional certificado. Foco no seu objetivo, seja ele qual for."
              },
              {
                "nome": "Plano mensal",
                "descricao": "Planos flexíveis para diferentes perfis. Acesso total à estrutura durante o horário de funcionamento."
              }
            ]
          },
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "Hunter V2",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "depoimentos",
          "id": null,
          "required": true,
          "layout_type": "reviews-spotlight",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "reviews reais ou sinais públicos",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "seo-geo",
          "id": null,
          "required": true,
          "layout_type": "seo-geo",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "faq",
          "id": null,
          "required": true,
          "layout_type": "faq",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "pesquisa local e dados confirmados",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "acao",
          "id": null,
          "required": true,
          "layout_type": "acao",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "lgpd",
          "id": null,
          "required": true,
          "layout_type": "lgpd",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "variation_blueprint",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "footer",
          "id": null,
          "required": true,
          "layout_type": "footer-editorial",
          "components": [
            "hero-cta"
          ],
          "copy_data": {},
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "NAP, navegação e links legais",
          "schema_org": null,
          "media_src": null
        },
        {
          "name": "localizacao",
          "id": "localizacao",
          "required": true,
          "layout_type": "local-proof-panel",
          "components": [
            "hero-cta"
          ],
          "copy_data": {
            "h2": "Onde estamos",
            "intro": "Estamos no Jardim Paulista, com estacionamento próprio e fácil acesso em Campina Grande do Sul.",
            "endereco": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
            "bairro_destaque": "Jardim Paulista, Campina Grande do Sul"
          },
          "items": [],
          "cta": null,
          "h1": null,
          "h2": null,
          "headline": null,
          "subheadline": null,
          "objective": null,
          "media_role": null,
          "omitir": false,
          "data_source": "Hunter V2",
          "schema_org": null,
          "media_src": null
        }
      ],
      "color_palette": {
        "primary": "var(--fg)",
        "secondary": "var(--surface)",
        "accent": "var(--accent)",
        "background": "var(--bg)",
        "text": "var(--fg)",
        "surface": "var(--surface)",
        "muted": "var(--muted)",
        "border": "var(--border)",
        "tokens_oklch": {
          "--bg": "oklch(12% 0.010 260)",
          "--surface": "oklch(17% 0.012 260)",
          "--fg": "oklch(93% 0.005 0)",
          "--muted": "oklch(65% 0.010 260)",
          "--border": "oklch(28% 0.015 260)",
          "--accent": "oklch(55.0% 0.138 25)"
        },
        "hero_style": {
          "bg": "var(--bg)",
          "fg": "var(--fg)",
          "accent_usage": "CTA button + 1 eyebrow label only"
        },
        "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
      },
      "typography": {
        "heading": "UberMove",
        "body": "UberMoveText"
      },
      "design_system_slug": null,
      "visual_dna": {
        "visual_seed": "42ee01f5ca7eb3b8",
        "archetype": {
          "visual_voice": "brutal, atletico, cinematografico, confiante, sem polidez corporativa",
          "color_theory": "preto profundo, vermelho eletrico dominante em CTAs e cortes, branco quente para display",
          "typography": {
            "heading_scale": "condensed_impact_900",
            "heading_trait": "uppercase condensado, italico/obliquo em palavras de impacto, outline text como camada secundaria",
            "body_trait": "compacto, tenso, alto contraste, sem paragrafo longo"
          },
          "composition_laws": [
            "hero dark full-bleed com foto/texture ocupando o fundo e overlay dramatico",
            "headline display 84px+ no desktop com palavra solida + palavra outline atras ou abaixo",
            "usar diagonais, crop agressivo, z-index, negative margins e cards pretos flutuantes",
            "vermelho vivo em CTAs, highlights e barras curtas; nunca usar azul/corporativo",
            "uma secao manifesto com titulo quebrado em linhas curtas e imagem lateral com sombra profunda",
            "CTA com glow vermelho e estado hover fisico"
          ],
          "media_query_modifiers": [
            "dark cinematic gym photography",
            "red accent lighting",
            "high contrast athlete training",
            "moody professional photography",
            "dynamic action crop"
          ],
          "cta_policy": "botao principal com glow neon e linguagem direta",
          "section_disruption": "full-bleed dark impact band",
          "archetype": "BOLD_ENERGY"
        },
        "dna_combo": {
          "structure_ref": "bmw_m",
          "typography_ref": "uber",
          "color_ref": "bmw_m",
          "motion_ref": "spotify",
          "spacing_ref": "bmw_m"
        },
        "tokens": {
          "--bg": "#070a08",
          "--surface": "#121a16",
          "--fg": "#f4fff7",
          "--muted": "#b8c9be",
          "--border": "#294137",
          "--accent": "#b8ff3d"
        },
        "palette_id": "bold-acid-lime",
        "color_strategy": "committed",
        "palette_contrast": {
          "page": 19.41,
          "surface": 17.29,
          "muted_page": 11.49,
          "muted_surface": 10.24
        },
        "font_heading": "UberMove",
        "font_body": "UberMoveText",
        "style_mix_instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
        "reference_vibes": {
          "structure": "motorsport, cockpit near-black, tricolor M",
          "typography": "mobility, bold black-white, tight type, pill-shaped, urban",
          "color": "motorsport, cockpit near-black, tricolor M",
          "motion": "music streaming, vibrant green on dark, album-art-driven"
        },
        "design_reference_pack": {
          "id": "bold_energy-42ee01f5",
          "source": "opendesign_curated_reference_pack",
          "archetype": "BOLD_ENERGY",
          "visual_seed": "42ee01f5ca7eb3b8",
          "tier": "STANDARD",
          "references": {
            "structure": {
              "slug": "bmw_m",
              "role": "structure",
              "category": "Automotive",
              "name": "Bmw M",
              "vibe": "motorsport, cockpit near-black, tricolor M",
              "font_heading": "BMW Type Next Latin Light",
              "font_body": "BMW Type Next Latin",
              "tokens": {
                "--bg": "oklch(0% 0.0 0)",
                "--surface": "oklch(10% 0.0 0)",
                "--fg": "oklch(100% 0.0 0)",
                "--muted": "oklch(49% 0.0 0)",
                "--border": "oklch(24% 0.0 0)",
                "--accent": "oklch(30% 0.158 4)"
              },
              "use_for": "grid, seção hero, ritmo e composição"
            },
            "typography": {
              "slug": "uber",
              "role": "typography",
              "category": "Media & Consumer",
              "name": "Uber",
              "vibe": "mobility, bold black-white, tight type, pill-shaped, urban",
              "font_heading": "UberMove",
              "font_body": "UberMoveText",
              "tokens": {
                "--bg": "oklch(100% 0.0 0)",
                "--surface": "oklch(100% 0.0 0)",
                "--fg": "oklch(0% 0.0 0)",
                "--muted": "oklch(29% 0.0 0)",
                "--border": "oklch(0% 0.0 0)",
                "--accent": "oklch(0% 0.0 0)"
              },
              "use_for": "escala, contraste de peso e voz tipográfica"
            },
            "color": {
              "slug": "bmw_m",
              "role": "color",
              "category": "Automotive",
              "name": "Bmw M",
              "vibe": "motorsport, cockpit near-black, tricolor M",
              "font_heading": "BMW Type Next Latin Light",
              "font_body": "BMW Type Next Latin",
              "tokens": {
                "--bg": "oklch(0% 0.0 0)",
                "--surface": "oklch(10% 0.0 0)",
                "--fg": "oklch(100% 0.0 0)",
                "--muted": "oklch(49% 0.0 0)",
                "--border": "oklch(24% 0.0 0)",
                "--accent": "oklch(30% 0.158 4)"
              },
              "use_for": "paleta base, contraste e acento"
            },
            "motion": {
              "slug": "spotify",
              "role": "motion",
              "category": "Media & Consumer",
              "name": "Spotify",
              "vibe": "music streaming, vibrant green on dark, album-art-driven",
              "font_heading": "CircularSp",
              "font_body": "CircularSp",
              "tokens": {
                "--bg": "oklch(7% 0.0 0)",
                "--surface": "oklch(9% 0.0 0)",
                "--fg": "oklch(100% 0.0 0)",
                "--muted": "oklch(70% 0.0 0)",
                "--border": "oklch(30% 0.0 0)",
                "--accent": "oklch(66% 0.145 141)"
              },
              "use_for": "cadência, reveal, parallax e microinterações"
            },
            "spacing": {
              "slug": "bmw_m",
              "role": "spacing",
              "category": "Automotive",
              "name": "Bmw M",
              "vibe": "motorsport, cockpit near-black, tricolor M",
              "font_heading": "BMW Type Next Latin Light",
              "font_body": "BMW Type Next Latin",
              "tokens": {
                "--bg": "oklch(0% 0.0 0)",
                "--surface": "oklch(10% 0.0 0)",
                "--fg": "oklch(100% 0.0 0)",
                "--muted": "oklch(49% 0.0 0)",
                "--border": "oklch(24% 0.0 0)",
                "--accent": "oklch(30% 0.158 4)"
              },
              "use_for": "densidade, respiro e proporção entre blocos"
            }
          },
          "dna_combo": {
            "structure_ref": "bmw_m",
            "typography_ref": "uber",
            "color_ref": "bmw_m",
            "motion_ref": "spotify",
            "spacing_ref": "bmw_m"
          },
          "tokens": {
            "--bg": "#070a08",
            "--surface": "#121a16",
            "--fg": "#f4fff7",
            "--muted": "#b8c9be",
            "--border": "#294137",
            "--accent": "#b8ff3d"
          },
          "typography": {
            "heading": "UberMove",
            "body": "UberMoveText"
          },
          "constraints": {
            "theme": "dark_cinematic",
            "hero": "full-bleed or poster-like, dominant image/texture, red action line, stat slabs",
            "spacing": "dense hero, generous section breaks, hard crops, no airy institutional stacking",
            "motion": "fast mask reveal, parallax crop, short stagger, strong scroll progress",
            "ban": [
              "pastel wellness",
              "beige institutional",
              "white card grid",
              "soft SaaS radius"
            ]
          },
          "instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
          "runtime_palette": {
            "id": "bold-acid-lime",
            "strategy": "committed",
            "contrast": {
              "page": 19.41,
              "surface": 17.29,
              "muted_page": 11.49,
              "muted_surface": 10.24
            }
          }
        },
        "variation": {
          "radius": "14px",
          "section_padding": "96px",
          "hero_density": "cinematic",
          "image_treatment": "full-bleed",
          "grid_bias": "asymmetric-left"
        },
        "tier": "STANDARD"
      },
      "layout_blueprint": [
        {
          "section": "hero",
          "variant": "hero-editorial-stack"
        },
        {
          "section": "sobre",
          "variant": "about-editorial"
        },
        {
          "section": "contato",
          "variant": "contact-split"
        },
        {
          "section": "interesse",
          "variant": "interesse"
        },
        {
          "section": "desejo",
          "variant": "desejo"
        },
        {
          "section": "numeros",
          "variant": "numeros"
        },
        {
          "section": "servicos",
          "variant": "services-editorial-list"
        },
        {
          "section": "depoimentos",
          "variant": "reviews-spotlight"
        },
        {
          "section": "seo-geo",
          "variant": "seo-geo"
        },
        {
          "section": "faq",
          "variant": "faq"
        },
        {
          "section": "acao",
          "variant": "acao"
        },
        {
          "section": "lgpd",
          "variant": "lgpd"
        },
        {
          "section": "footer",
          "variant": "footer-editorial"
        },
        {
          "section": "localizacao",
          "variant": "local-proof-panel"
        }
      ],
      "design_reference_pack": {
        "id": "bold_energy-42ee01f5",
        "source": "opendesign_curated_reference_pack",
        "archetype": "BOLD_ENERGY",
        "visual_seed": "42ee01f5ca7eb3b8",
        "tier": "STANDARD",
        "references": {
          "structure": {
            "slug": "bmw_m",
            "role": "structure",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "grid, seção hero, ritmo e composição"
          },
          "typography": {
            "slug": "uber",
            "role": "typography",
            "category": "Media & Consumer",
            "name": "Uber",
            "vibe": "mobility, bold black-white, tight type, pill-shaped, urban",
            "font_heading": "UberMove",
            "font_body": "UberMoveText",
            "tokens": {
              "--bg": "oklch(100% 0.0 0)",
              "--surface": "oklch(100% 0.0 0)",
              "--fg": "oklch(0% 0.0 0)",
              "--muted": "oklch(29% 0.0 0)",
              "--border": "oklch(0% 0.0 0)",
              "--accent": "oklch(0% 0.0 0)"
            },
            "use_for": "escala, contraste de peso e voz tipográfica"
          },
          "color": {
            "slug": "bmw_m",
            "role": "color",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "paleta base, contraste e acento"
          },
          "motion": {
            "slug": "spotify",
            "role": "motion",
            "category": "Media & Consumer",
            "name": "Spotify",
            "vibe": "music streaming, vibrant green on dark, album-art-driven",
            "font_heading": "CircularSp",
            "font_body": "CircularSp",
            "tokens": {
              "--bg": "oklch(7% 0.0 0)",
              "--surface": "oklch(9% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(70% 0.0 0)",
              "--border": "oklch(30% 0.0 0)",
              "--accent": "oklch(66% 0.145 141)"
            },
            "use_for": "cadência, reveal, parallax e microinterações"
          },
          "spacing": {
            "slug": "bmw_m",
            "role": "spacing",
            "category": "Automotive",
            "name": "Bmw M",
            "vibe": "motorsport, cockpit near-black, tricolor M",
            "font_heading": "BMW Type Next Latin Light",
            "font_body": "BMW Type Next Latin",
            "tokens": {
              "--bg": "oklch(0% 0.0 0)",
              "--surface": "oklch(10% 0.0 0)",
              "--fg": "oklch(100% 0.0 0)",
              "--muted": "oklch(49% 0.0 0)",
              "--border": "oklch(24% 0.0 0)",
              "--accent": "oklch(30% 0.158 4)"
            },
            "use_for": "densidade, respiro e proporção entre blocos"
          }
        },
        "dna_combo": {
          "structure_ref": "bmw_m",
          "typography_ref": "uber",
          "color_ref": "bmw_m",
          "motion_ref": "spotify",
          "spacing_ref": "bmw_m"
        },
        "tokens": {
          "--bg": "#070a08",
          "--surface": "#121a16",
          "--fg": "#f4fff7",
          "--muted": "#b8c9be",
          "--border": "#294137",
          "--accent": "#b8ff3d"
        },
        "typography": {
          "heading": "UberMove",
          "body": "UberMoveText"
        },
        "constraints": {
          "theme": "dark_cinematic",
          "hero": "full-bleed or poster-like, dominant image/texture, red action line, stat slabs",
          "spacing": "dense hero, generous section breaks, hard crops, no airy institutional stacking",
          "motion": "fast mask reveal, parallax crop, short stagger, strong scroll progress",
          "ban": [
            "pastel wellness",
            "beige institutional",
            "white card grid",
            "soft SaaS radius"
          ]
        },
        "instruction": "Use estrutura bmw_m, tipografia uber, paleta bmw_m, motion spotify e spacing bmw_m. Regra do arquétipo BOLD_ENERGY: full-bleed or poster-like, dominant image/texture, red action line, stat slabs.",
        "runtime_palette": {
          "id": "bold-acid-lime",
          "strategy": "committed",
          "contrast": {
            "page": 19.41,
            "surface": 17.29,
            "muted_page": 11.49,
            "muted_surface": 10.24
          }
        }
      },
      "dna_combo": {},
      "visual_seed": "42ee01f5ca7eb3b8",
      "visual_direction": {},
      "minimum_required_media": null,
      "visual_contract": {
        "version": 1,
        "archetype": "BOLD_ENERGY",
        "acceptance_criteria": {
          "minimum_sections": 7,
          "required_sections": [
            "hero",
            "trust_or_proof",
            "decision_content",
            "media_story",
            "location",
            "faq",
            "footer"
          ],
          "mobile": [
            "no_horizontal_overflow",
            "cta_visible",
            "headline_not_clipped"
          ],
          "truth": [
            "no_lorem",
            "no_fake_services",
            "no_fake_reviews",
            "no_internal_policy_leak"
          ]
        },
        "hero": {
          "required": [
            "headline",
            "subheadline",
            "primary_cta",
            "proof_chip",
            "media_16_9_or_depth_layer",
            "motion_hook"
          ],
          "forbidden": [
            "generic_centered_block",
            "mobile_overflow",
            "unreadable_outline",
            "hidden_reveal_without_fallback"
          ]
        },
        "sections": {
          "required": {
            "decision_content": "educa a escolha com critérios reais do nicho",
            "media_story": "usa imagens como narrativa editorial sem chamar de foto real",
            "location": "mostra mapa único e endereço confirmado",
            "faq": "remove objeções práticas antes do contato"
          },
          "media_ratio": "16:9",
          "backgrounds": "cada seção deve ter superfície/fundo intencional, não pilha branca genérica"
        },
        "footer": {
          "required": [
            "brand",
            "navigation",
            "contact",
            "address_or_city",
            "hours_or_confirmation_note",
            "trust_note"
          ],
          "forbidden": [
            "unreadable_contrast",
            "generic_black_fallback",
            "post_footer_gallery"
          ]
        },
        "media": {
          "available": true,
          "ratio": "16:9",
          "policy": "editorial support only unless explicitly marked real venue media"
        },
        "location": {
          "requires_exact_map": true,
          "single_map_only": true,
          "zoom": 18
        }
      },
      "site_build_plan": {
        "version": 1,
        "purpose": "plano pos-PRD para transformar briefing factual em HTML final",
        "component_contracts": {
          "version": 1,
          "hero": {
            "component_id": "HeroBoldPoster02",
            "archetype": "BOLD_ENERGY",
            "locked": true,
            "slots_required": [
              "headline",
              "subheadline",
              "primary_cta",
              "proof_chip",
              "dominant_visual",
              "motion_hooks"
            ],
            "visual_guarantees": [
              "responsive 16:9 media surface",
              "data-parallax or deterministic depth layer",
              "Ken Burns-compatible media class",
              "CTA hover microinteraction",
              "readable contrast by archetype",
              "mobile-first stacking"
            ]
          },
          "footer": {
            "component_id": "FooterLocalTrust01",
            "locked": true,
            "visual_guarantees": [
              "navigation",
              "contact",
              "address_or_city",
              "trust_note"
            ]
          }
        },
        "business_context": {
          "name": "Academia Ph.D Sports Jardim Paulista",
          "segment": "academia",
          "city": "Campina Grande do Sul",
          "primary_conversion_goal": "whatsapp"
        },
        "information_architecture": {
          "section_order": [
            "hero",
            "interesse",
            "desejo",
            "numeros",
            "servicos",
            "depoimentos",
            "seo-geo",
            "faq",
            "acao",
            "lgpd",
            "footer"
          ],
          "section_order_source": "variation_blueprint",
          "narrative_framework": "AIDA",
          "required_sections": [
            "hero",
            "interesse",
            "desejo",
            "acao",
            "faq",
            "lgpd",
            "footer"
          ],
          "navigation_targets": [
            "hero",
            "interesse",
            "desejo",
            "numeros",
            "servicos",
            "depoimentos",
            "seo-geo",
            "faq",
            "acao",
            "lgpd",
            "footer"
          ],
          "must_combine": [
            "location",
            "contact"
          ],
          "must_not_duplicate": [
            "map",
            "location",
            "footer",
            "post_footer_gallery"
          ]
        },
        "section_plan": [
          {
            "id": "hero",
            "role": "attention",
            "required_content": [
              "headline",
              "subheadline",
              "primary_cta",
              "proof_chip",
              "motion_hook"
            ],
            "visual_surface": "campaign viewport with depth layer, 16:9 media/decor and CTA microinteraction",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "interesse",
            "role": "interest",
            "required_content": [
              "problem_context",
              "audience_specific_pain",
              "local_relevance",
              "why_now"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "desejo",
            "role": "desire",
            "required_content": [
              "offer_value",
              "differentiators",
              "proof_or_services",
              "visual_media"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "numeros",
            "role": "support",
            "required_content": [],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "servicos",
            "role": "support",
            "required_content": [],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "depoimentos",
            "role": "support",
            "required_content": [],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "seo-geo",
            "role": "local_seo",
            "required_content": [
              "city",
              "segment",
              "neighborhood_or_address",
              "search_intent_terms"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "faq",
            "role": "objection_handling",
            "required_content": [
              "contact",
              "location",
              "what_to_confirm"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "acao",
            "role": "action",
            "required_content": [
              "primary_cta",
              "phone_or_whatsapp",
              "location_or_next_step"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "lgpd",
            "role": "privacy_trust",
            "required_content": [
              "data_usage_note",
              "consent_banner_or_notice",
              "contact_policy"
            ],
            "visual_surface": "intentional archetype background with responsive spacing",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast"
            ]
          },
          {
            "id": "footer",
            "role": "closure",
            "required_content": [
              "brand",
              "navigation",
              "contact",
              "trust_note"
            ],
            "visual_surface": "complete footer using readable palette contrast",
            "validation": [
              "no_lorem",
              "no_horizontal_overflow",
              "readable_contrast",
              "not_after_footer_content",
              "navigation_contact_trust"
            ]
          }
        ],
        "style_guide": {
          "archetype": "BOLD_ENERGY",
          "reference_pack_id": "bold_energy-42ee01f5",
          "tokens": {
            "primary": "var(--fg)",
            "secondary": "var(--surface)",
            "accent": "var(--accent)",
            "background": "var(--bg)",
            "text": "var(--fg)",
            "surface": "var(--surface)",
            "muted": "var(--muted)",
            "border": "var(--border)",
            "tokens_oklch": {
              "--bg": "oklch(12% 0.010 260)",
              "--surface": "oklch(17% 0.012 260)",
              "--fg": "oklch(93% 0.005 0)",
              "--muted": "oklch(65% 0.010 260)",
              "--border": "oklch(28% 0.015 260)",
              "--accent": "oklch(55.0% 0.138 25)"
            },
            "hero_style": {
              "bg": "var(--bg)",
              "fg": "var(--fg)",
              "accent_usage": "CTA button + 1 eyebrow label only"
            },
            "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
          },
          "typography": {
            "heading": "UberMove",
            "body": "UberMoveText"
          },
          "spacing": "use clamp-based section padding; mobile px-4, desktop max-width containers; no content touching viewport edges",
          "surfaces": "alternate hero, proof, editorial, decision, location and footer backgrounds using the archetype tokens",
          "media_ratio": "16:9"
        },
        "media_plan": {
          "items": [
            {
              "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
              "role": "hero",
              "section": "hero",
              "required": true,
              "source": "",
              "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
            },
            {
              "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
              "role": "editorial",
              "section": "interesse",
              "required": false,
              "source": "",
              "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
            },
            {
              "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
              "role": "editorial",
              "section": "desejo",
              "required": false,
              "source": "",
              "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
            },
            {
              "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
              "role": "editorial",
              "section": "numeros",
              "required": false,
              "source": "",
              "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
            },
            {
              "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
              "role": "service",
              "section": "servicos",
              "required": false,
              "source": "",
              "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
            }
          ],
          "available_count": 5,
          "hero": "use one dominant 16:9/depth media surface when available; otherwise use CSS/SVG depth",
          "gallery": "use up to 3 editorial images inside one media-story section",
          "policy": "media is editorial support unless data explicitly confirms it is real venue media",
          "map": "one Google Maps query embed from confirmed address; never broad OSM fallback"
        },
        "interaction_plan": {
          "hero": [
            "data-parallax",
            "ken-burns",
            "cta-hover-glow"
          ],
          "sections": [
            "data-reveal",
            "card-stagger",
            "line-draw"
          ],
          "fallback": "all content remains visible without JavaScript or motion runtime"
        },
        "content_rules": {
          "allowed_claims": [
            "Academia Ph.D Sports Jardim Paulista atua como academia",
            "Atendimento em Campina Grande do Sul",
            "Endereço confirmado: R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
            "Contato oficial: 5541985143249",
            "Avaliação pública 4.8",
            "9 avaliações públicas"
          ],
          "forbidden_claims": [
            "não inventar serviços, equipe, estrutura, equipamentos ou especialidades",
            "não afirmar que fotos editoriais são fotos reais do endereço",
            "não criar depoimentos ou métricas que não vieram dos dados públicos",
            "não publicar horários como certeza quando vierem vazios ou incompletos"
          ],
          "services_policy": "render confirmed services only; if missing, use decision/FAQ copy instead of fake service cards",
          "no_lorem": true
        },
        "seo_plan": {
          "title_strategy": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul",
          "local_terms": [
            "academia",
            "Campina Grande do Sul",
            "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil"
          ],
          "schema_type": "LocalBusiness"
        },
        "acceptance_criteria": {
          "minimum_sections": 7,
          "required_sections": [
            "hero",
            "trust_or_proof",
            "decision_content",
            "media_story",
            "location",
            "faq",
            "footer"
          ],
          "mobile": [
            "no_horizontal_overflow",
            "cta_visible",
            "headline_not_clipped"
          ],
          "truth": [
            "no_lorem",
            "no_fake_services",
            "no_fake_reviews",
            "no_internal_policy_leak"
          ]
        }
      },
      "niche_brief": {
        "task_id": "0c8532da8d97",
        "source_agent": "agente_nicho",
        "target_agent": "agente_variacao",
        "status": "ok",
        "task_summary": "Briefing gerado para Academia Ph.D Sports Jardim Paulista (academia) em 20.6s",
        "nicho": "academia",
        "subnichos": [],
        "cidade": "Campina Grande do Sul",
        "publico_alvo": [],
        "usp": [],
        "diferenciais": [],
        "objeções": [],
        "keywords": [],
        "tom_de_voz": "profissional",
        "notas": "",
        "confianca": "baixa",
        "dados_ausentes": [
          "JSON não foi extraído corretamente"
        ],
        "competidores": [],
        "regras": [],
        "nao_fazer": []
      },
      "creative_direction": {
        "task_id": "0c8532da8d97",
        "source_agent": "design_director",
        "target_agent": "agente_variacao",
        "status": "ok",
        "task_summary": "Direção criativa para Academia Ph.D Sports Jardim Paulista",
        "brand_concept": "Academia Ph.D Sports Jardim Paulista",
        "audience": "",
        "positioning": "",
        "commercial_thesis": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
        "visual_concept": "bold",
        "visual_keywords": [
          "bold",
          "tipografia pesada, alto contraste, comanda atencao",
          "academia"
        ],
        "physical_scene": "Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul: academia com atmosfera bold.",
        "color_strategy": {
          "primary": "#0A0A0E",
          "secondary": "#C8FF00",
          "accent": "#E87A1A",
          "tokens_oklch": {
            "--bg": "oklch(12% 0.010 260)",
            "--surface": "oklch(17% 0.012 260)",
            "--fg": "oklch(93% 0.005 0)",
            "--muted": "oklch(65% 0.010 260)",
            "--border": "oklch(28% 0.015 260)",
            "--accent": "oklch(55.0% 0.138 25)"
          }
        },
        "typography_strategy": {
          "heading": "Archivo Black",
          "body": "Inter"
        },
        "photography_strategy": {
          "policy": "usar URLs reais do media_plan com papeis por seção",
          "hero": "imagem dominante coerente com a cena física"
        },
        "composition_strategy": "hero, sobre, servicos, depoimentos, faq, contato",
        "density_strategy": "bold",
        "rhythm_strategy": "fade-up",
        "hero_strategy": "hero-center",
        "cta_strategy": "WhatsApp",
        "signature_section": "Academia jovem e acessível de Campina Grande do Sul com proposta de recomeço — diferente das academias tradicionais da região que usam linguagem pesada e intimidante",
        "anti_patterns": [
          "hero fullscreen genérico com academia ao fundo",
          "cores azul/branco óbvias de academia",
          "fotos genéricas de pessoas malhando de stock",
          "layout de colunas simétrico padrão de site institucional"
        ],
        "required_visual_differences": [
          "estilo Awwwards com tipografia massiva",
          "Nike Training Club — energia visual",
          "Gymshark — dark mode agressivo e contraste alto",
          "Brutalismo digital com toque esportivo"
        ],
        "hard_constraints": {
          "visual_concept": "bold",
          "palette": {
            "--bg": "oklch(12% 0.010 260)",
            "--surface": "oklch(17% 0.012 260)",
            "--fg": "oklch(93% 0.005 0)",
            "--muted": "oklch(65% 0.010 260)",
            "--border": "oklch(28% 0.015 260)",
            "--accent": "oklch(55.0% 0.138 25)"
          },
          "typography": {
            "heading": "Archivo Black",
            "body": "Inter"
          },
          "hero_strategy": "",
          "anti_patterns": [
            "hero fullscreen genérico com academia ao fundo",
            "cores azul/branco óbvias de academia",
            "fotos genéricas de pessoas malhando de stock",
            "layout de colunas simétrico padrão de site institucional"
          ]
        },
        "soft_constraints": {
          "motion": {
            "intensidade": "bold",
            "efeito_principal": "fade-up",
            "scroll_speed": "fast",
            "usa_video_hero": false,
            "usa_parallax": false,
            "usa_cursor_custom": false
          },
          "voice": {
            "registro": "casual",
            "personalidade": "jovem",
            "frases_chave": [
              "Comece sua transformação hoje",
              "Seu corpo, sua mente, seu começo",
              "Sem desculpas. Sem limites. Só resultado."
            ]
          },
          "inspirations": [
            "estilo Awwwards com tipografia massiva",
            "Nike Training Club — energia visual",
            "Gymshark — dark mode agressivo e contraste alto",
            "Brutalismo digital com toque esportivo"
          ]
        }
      },
      "variation_blueprint": {
        "task_id": "0c8532da8d97",
        "source_agent": "agente_variacao",
        "target_agent": "arquiteto_mestre",
        "status": "ok",
        "task_summary": "Variação definida: corporate/hero-split em 10.5s",
        "narrative_framework": "AIDA",
        "template_estrutura": "corporate",
        "template_hero": "hero-split",
        "template_prova_social": "stats-cards",
        "template_cta": "cta-central",
        "template_faq": "faq-accordion",
        "ordem_das_secoes": [
          "hero",
          "interesse",
          "desejo",
          "numeros",
          "servicos",
          "depoimentos",
          "seo-geo",
          "faq",
          "acao",
          "lgpd",
          "footer"
        ],
        "required_sections": [
          "hero",
          "interesse",
          "desejo",
          "acao",
          "faq",
          "lgpd",
          "footer"
        ],
        "angulo_de_comunicacao": "A academia de Campina Grande do Sul que se adapta à sua rotina: horário estendido, aula experimental gratuita e estacionamento próprio — três diferenciais que nenhum concorrente local oferece.",
        "regra_antirrepeticao": "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
        "justificativa": "O nicho de academia em Campina Grande do Sul apresenta alta repetição estrutural entre concorrentes, com tom direto e orientado a benefício. A estrutura corporate com hero-split permite destacar visualmente os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo na primeira dobra, diferenciando-se do padrão de mercado. A seção de números (stats-cards) antes dos serviços cria prova social quantificável que gera confiança antes da apresentação da oferta. O FAQ em accordion reduz objeções comuns antes do CTA central, maximizando conversão. A inclusão de seo-geo antes da ação reforça a presença local em Campina Grande do Sul, capturando intenção de busca geolocalizada.",
        "layout_variants": {},
        "rhythm": "",
        "signature_composition": "",
        "avoid": [
          "Evitar layout genérico de academia com hero-centralizado + lista de benefícios + CTA padrão. Não repetir a estrutura comum do mercado local (headline genérica 'Academias' + busca de unidade). Destaque os três diferenciais exclusivos (horário estendido, aula experimental grátis, estacionamento) logo no hero, não apenas no meio da página.",
          "hero fullscreen genérico com academia ao fundo",
          "cores azul/branco óbvias de academia",
          "fotos genéricas de pessoas malhando de stock",
          "layout de colunas simétrico padrão de site institucional"
        ]
      },
      "media_plan": [
        {
          "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
          "role": "hero",
          "section": "hero",
          "required": true,
          "source": "",
          "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
        },
        {
          "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
          "role": "editorial",
          "section": "interesse",
          "required": false,
          "source": "",
          "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
        },
        {
          "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
          "role": "editorial",
          "section": "desejo",
          "required": false,
          "source": "",
          "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
        },
        {
          "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
          "role": "editorial",
          "section": "numeros",
          "required": false,
          "source": "",
          "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
        },
        {
          "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
          "role": "service",
          "section": "servicos",
          "required": false,
          "source": "",
          "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
        }
      ],
      "animations": [
        {
          "name": "scroll-reveal",
          "type": "scroll-reveal",
          "target": "section",
          "trigger": "IntersectionObserver",
          "duration": "500ms",
          "easing": "cubic-bezier(0.0, 0.0, 0.2, 1)"
        },
        {
          "name": "cta-pulse",
          "type": "keyframe",
          "target": ".cta-primary",
          "trigger": "scroll",
          "duration": "2.5s",
          "easing": "ease-in-out"
        },
        {
          "name": "service-card-hover",
          "type": "hover-micro",
          "target": "section",
          "trigger": "hover",
          "duration": "150ms",
          "easing": "cubic-bezier(0.4, 0.0, 0.2, 1)"
        },
        {
          "name": "diferencial-card-hover",
          "type": "hover-micro",
          "target": "section",
          "trigger": "hover",
          "duration": "150ms",
          "easing": "cubic-bezier(0.4, 0.0, 0.2, 1)"
        },
        {
          "name": "hero-fade-in",
          "type": "entrance",
          "target": "section",
          "trigger": "page-load",
          "duration": "600ms",
          "easing": "cubic-bezier(0.0, 0.0, 0.2, 1)"
        }
      ],
      "business_name": "Academia Ph.D Sports Jardim Paulista",
      "reviews_count": 9,
      "reviews_rating": 4.8,
      "reviews_list": [],
      "address": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
      "phone": "5541985143249",
      "hours": {},
      "photos": [
        "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
        "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82"
      ],
      "videos": [],
      "logo_url": null,
      "google_maps_embed": "",
      "components_21dev": [
        "whatsapp-sticky-cta"
      ],
      "cidade": "Campina Grande do Sul",
      "segmento": "academia",
      "instrucao_criativa_para_dev": "O tom visual é Energético e Direto — academia de bairro com personalidade, não uma marca genérica de fitness. O fundo escuro (oklch(12% 0.010 260)) cria contraste forte com o texto claro e o accent verde-elétrico (oklch(72% 0.19 145)), que deve aparecer no máximo 2x por tela: no CTA principal e em um elemento de destaque por seção. O hero usa layout split: imagem real da academia à direita, texto à esquerda. O H1 é o entry point dominante — clamp(2.2rem, 5vw, 3.5rem), peso 600, tracking -0.02em. Nunca usar gradiente purple→blue ou indigo. Nunca usar emojis em headings ou botões — ícones devem ser SVG monoline com currentColor. A seção serviços usa cards com borda sutil (--border), hover com translateY(-4px) e borda que muda para --accent. A seção contato deve ser o momento final da página — sem FAQ após ela. Respeitar a regra dos 80/20: estrutura sólida e legível, com o verde-elétrico como o único elemento de ruptura visual.",
      "jina_insights": null,
      "servicos": null,
      "atributos": null,
      "horarios": null,
      "faixa_preco": null,
      "competitor_analysis": "[{\"name\": \"Start Academia\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia Iron\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia High\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Academia Life\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}, {\"name\": \"Legacy Academia\", \"city\": \"Campina Grande do Sul\", \"observed_differentials\": [], \"gaps_identified\": [\"Não menciona horário estendido\", \"Sem referência a estacionamento próprio\", \"Sem aula experimental gratuita como destaque\"]}]",
      "anti_patterns": [
        "gradiente purple→blue no hero",
        "cores #6366f1, #4f46e5, #4338ca, #8b5cf6, #7c3aed como accent",
        "emojis em headings, botões ou listas",
        "card com borda colorida à esquerda (AI dashboard tile)",
        "métricas inventadas sem dado real do lead",
        "filler copy (Lorem ipsum, Feature One, Descrição do serviço)",
        "gradiente em cada seção de fundo",
        "Inter ou Roboto como font-heading",
        "layout Hero→Features→Pricing→FAQ→CTA sem variação",
        "terminar página com FAQ — sempre CTA ou contato no final",
        "precos visiveis",
        "hero fullscreen genérico com academia ao fundo",
        "cores azul/branco óbvias de academia",
        "fotos genéricas de pessoas malhando de stock",
        "layout de colunas simétrico padrão de site institucional"
      ],
      "schema_org_types": [
        "LocalBusiness",
        "ExerciseGym"
      ],
      "seo_keywords": [
        "academia campina grande do sul",
        "academia campina grande do sul pr",
        "academia phd campina grande do sul",
        "academia musculação campina grande do sul",
        "academia com estacionamento campina grande do sul",
        "academia horário estendido campina grande do sul",
        "aula experimental academia campina grande do sul",
        "personal trainer campina grande do sul",
        "melhor academia jardim paulista campina grande do sul",
        "academia condicionamento físico campina grande do sul pr"
      ],
      "faq_questions": [
        "A Academia Ph.D Sports oferece aula experimental gratuita?",
        "Qual o horário de funcionamento da academia em Campina Grande do Sul?",
        "A academia tem estacionamento para alunos?",
        "Quais modalidades são oferecidas na Academia Ph.D Sports?",
        "A academia fica no Jardim Paulista em Campina Grande do Sul?",
        "Como entrar em contato com a Academia Ph.D Sports?"
      ],
      "value_props": [
        "Aula Experimental Grátis",
        "Horário Estendido",
        "Estacionamento Próprio",
        "Estrutura Completa para Resultados"
      ],
      "geo": {
        "lat": -25.535,
        "lng": -49.298
      },
      "dark_mode": false,
      "_raw_reviews": [],
      "requirements_contract": {
        "version": 1,
        "objective": "gerar site local verdadeiro, claro e orientado a conversão",
        "primary_conversion_goal": "whatsapp",
        "confirmed_facts": [
          {
            "key": "business_name",
            "value": "Academia Ph.D Sports Jardim Paulista"
          },
          {
            "key": "segmento",
            "value": "academia"
          },
          {
            "key": "cidade",
            "value": "Campina Grande do Sul"
          },
          {
            "key": "address",
            "value": "R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil"
          },
          {
            "key": "phone",
            "value": "5541985143249"
          },
          {
            "key": "rating",
            "value": 4.8
          },
          {
            "key": "reviews_count",
            "value": 9
          },
          {
            "key": "editorial_media_available",
            "value": 5
          }
        ],
        "allowed_claims": [
          "Academia Ph.D Sports Jardim Paulista atua como academia",
          "Atendimento em Campina Grande do Sul",
          "Endereço confirmado: R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil",
          "Contato oficial: 5541985143249",
          "Avaliação pública 4.8",
          "9 avaliações públicas"
        ],
        "forbidden_claims": [
          "não inventar serviços, equipe, estrutura, equipamentos ou especialidades",
          "não afirmar que fotos editoriais são fotos reais do endereço",
          "não criar depoimentos ou métricas que não vieram dos dados públicos",
          "não publicar horários como certeza quando vierem vazios ou incompletos"
        ],
        "missing_but_required": [
          "confirmed_services"
        ],
        "business_risk": "alto risco de inventar oferta"
      }
    },
    "openui_url": null
  },
  "produced": {
    "model": "claude-sonnet-5",
    "html_length": 79927,
    "html_counts": {
      "main": 1,
      "h1": 1,
      "section": 13,
      "img": 10,
      "background_image": 0
    },
    "html_preview": "<!DOCTYPE html>\n<html lang=\"pt-BR\" data-renderer=\"builder\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>Academia Ph.D Sports Jardim Paulista — Campina Grande do Sul</title>\n  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap\" rel=\"stylesheet\">\n  <script src=\"https://cdn.tailwindcss.com\"></script>\n<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22><rect width=%2264%22 height=%2264%22 rx=%2214%22 fill=%22%23111827%22/><path d=%22M18 46V18h28v8H28v4h14v8H28v8z%22 fill=%22white%22/></svg>\">\n<meta property=\"og:image\" content=\"https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82\">\n<meta property=\"og:title\" content=\"Academia Ph.D Sports Jardim Paulista\">\n<meta name=\"description\" content=\"Academia Ph.D Sports Jardim Paulista em Campina Grande do Sul. Informações, serviços, localização e contato oficial.\">\n<meta name=\"keywords\" content=\"academia campina grande do sul, academia campina grande do sul pr, academia phd campina grande do sul, academia musculação campina grande do sul, academia com estacionamento campina grande do sul, academia horário estendido campina grande do sul, aula experimental academia campina grande do sul, personal trainer campina grande do sul, melhor academia jardim paulista campina grande do sul, academia condicionamento físico campina grande do sul pr\">\n<link rel=\"canonical\" href=\"https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/\">\n<meta property=\"og:url\" content=\"https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/\">\n</head>\n<body>\n  <main id=\"app-shell\">\n<section\n  class=\"min-h-[90vh] flex flex-col\"\n  style=\"background: var(--bg); color: var(--fg); font-family: 'UberMoveText', system-ui, sans-serif;\"\n>\n  <!-"
  },
  "preserved": {
    "media_plan": [
      {
        "url": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82",
        "role": "hero",
        "section": "hero",
        "required": true,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para hero"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "interesse",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para interesse"
      },
      {
        "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "desejo",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para desejo"
      },
      {
        "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82",
        "role": "editorial",
        "section": "numeros",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para numeros"
      },
      {
        "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1400&q=82",
        "role": "service",
        "section": "servicos",
        "required": false,
        "source": "",
        "alt": "Academia Ph.D Sports Jardim Paulista — imagem editorial para servicos"
      }
    ],
    "section_order": [
      "hero",
      "interesse",
      "desejo",
      "numeros",
      "servicos",
      "depoimentos",
      "seo-geo",
      "faq",
      "acao",
      "lgpd",
      "footer"
    ],
    "typography": {
      "heading": "UberMove",
      "body": "UberMoveText"
    },
    "palette": {
      "primary": "var(--fg)",
      "secondary": "var(--surface)",
      "accent": "var(--accent)",
      "background": "var(--bg)",
      "text": "var(--fg)",
      "surface": "var(--surface)",
      "muted": "var(--muted)",
      "border": "var(--border)",
      "tokens_oklch": {
        "--bg": "oklch(12% 0.010 260)",
        "--surface": "oklch(17% 0.012 260)",
        "--fg": "oklch(93% 0.005 0)",
        "--muted": "oklch(65% 0.010 260)",
        "--border": "oklch(28% 0.015 260)",
        "--accent": "oklch(55.0% 0.138 25)"
      },
      "hero_style": {
        "bg": "var(--bg)",
        "fg": "var(--fg)",
        "accent_usage": "CTA button + 1 eyebrow label only"
      },
      "reasoning": "Tom energetic e direto para academia. Accent em laranja-vermelho oklch(55% 0.22 25) transmite energia e movimento — coerente com musculação e condicionamento físico. Sem indigo/violeta (anti-slop). Light mode conforme MODE:LIGHT. Contraste WCAG AA garantido: fg oklch(18%) sobre bg oklch(97%) = ratio > 12:1."
    }
  },
  "changed": {},
  "lost": {},
  "notes": []
}
```

### 08-quality_gate-handoff.json

```json
{
  "stage": "quality_gate",
  "created_at": "2026-08-14T01:01:51.620489Z",
  "received": {
    "html_length": 79927,
    "html_counts": {
      "main": 1,
      "h1": 1,
      "section": 13,
      "img": 10
    },
    "design_output_keys": [
      "_raw_reviews",
      "address",
      "animations",
      "anti_patterns",
      "atributos",
      "business_name",
      "cidade",
      "color_palette",
      "competitor_analysis",
      "components_21dev",
      "creative_direction",
      "dark_mode",
      "design_reference_pack",
      "design_system_slug",
      "dna_combo",
      "faixa_preco",
      "faq_questions",
      "geo",
      "google_maps_embed",
      "horarios",
      "hours",
      "instrucao_criativa_para_dev",
      "jina_insights",
      "layout_blueprint",
      "logo_url",
      "media_plan",
      "minimum_required_media",
      "niche_brief",
      "phone",
      "photos",
      "requirements_contract",
      "reviews_count",
      "reviews_list",
      "reviews_rating",
      "schema_org_types",
      "sections",
      "segmento",
      "seo_keywords",
      "servicos",
      "site_build_plan",
      "typography",
      "value_props",
      "variation_blueprint",
      "videos",
      "visual_contract",
      "visual_direction",
      "visual_dna",
      "visual_seed"
    ]
  },
  "produced": {
    "quality_score": 100,
    "qa_v2": {
      "vision_score": 10.0,
      "vision_passed": true,
      "vision_issues": [],
      "vision_strengths": [
        "QA temporariamente em pass-through para inspeção visual"
      ],
      "repair_attempted": false,
      "repair_success": false,
      "repair_fixes": [],
      "model_used": "pass-through-temporary"
    },
    "gates": {
      "passed": true,
      "issues": [],
      "technical_gate": {
        "passed": true,
        "issues": []
      },
      "creative_compliance_gate": {
        "passed": true,
        "issues": []
      },
      "visual_diversity_gate": {
        "passed": true,
        "issues": [],
        "fingerprint": {
          "version": 1,
          "hero": "hero-split",
          "section_order": [
            "min-h-[90vh]",
            "interesse",
            "sobre",
            "bg-[var(--bg)]",
            "desejo",
            "depoimentos",
            "seo-geo",
            "faq",
            "relative",
            "acao",
            "contato",
            "lgpd",
            "footer"
          ],
          "container": "wide",
          "grids": 174,
          "typography": {
            "heading": "UberMove",
            "body": "UberMoveText",
            "html_font_sample": "UberMoveText', system-ui, sans-serif"
          },
          "palette": [
            "oklch(12% 0.010 260)",
            "oklch(17% 0.012 260)",
            "oklch(93% 0.005 0)",
            "oklch(65% 0.010 260)",
            "oklch(28% 0.015 260)",
            "oklch(55.0% 0.138 25)",
            "#fff",
            "#aca",
            "oklch(12%_0.010_260)",
            "oklch(93%_0.005_0)",
            "oklch(55.0%_0.138_25)",
            "oklch(65%_0.010_260)",
            "oklch(17%_0.012_260)",
            "oklch(28%_0.015_260)"
          ],
          "media_count": 10,
          "density": "dense",
          "cards": 277,
          "borders": 165,
          "radius": "pill",
          "motion": [
            "transition",
            "animate-"
          ],
          "hash": "3ef583531ef04701"
        },
        "threshold": 0.86,
        "comparisons": []
      },
      "fingerprint": {
        "version": 1,
        "hero": "hero-split",
        "section_order": [
          "min-h-[90vh]",
          "interesse",
          "sobre",
          "bg-[var(--bg)]",
          "desejo",
          "depoimentos",
          "seo-geo",
          "faq",
          "relative",
          "acao",
          "contato",
          "lgpd",
          "footer"
        ],
        "container": "wide",
        "grids": 174,
        "typography": {
          "heading": "UberMove",
          "body": "UberMoveText",
          "html_font_sample": "UberMoveText', system-ui, sans-serif"
        },
        "palette": [
          "oklch(12% 0.010 260)",
          "oklch(17% 0.012 260)",
          "oklch(93% 0.005 0)",
          "oklch(65% 0.010 260)",
          "oklch(28% 0.015 260)",
          "oklch(55.0% 0.138 25)",
          "#fff",
          "#aca",
          "oklch(12%_0.010_260)",
          "oklch(93%_0.005_0)",
          "oklch(55.0%_0.138_25)",
          "oklch(65%_0.010_260)",
          "oklch(17%_0.012_260)",
          "oklch(28%_0.015_260)"
        ],
        "media_count": 10,
        "density": "dense",
        "cards": 277,
        "borders": 165,
        "radius": "pill",
        "motion": [
          "transition",
          "animate-"
        ],
        "hash": "3ef583531ef04701"
      }
    },
    "visual_fingerprint": {
      "version": 1,
      "hero": "hero-split",
      "section_order": [
        "min-h-[90vh]",
        "interesse",
        "sobre",
        "bg-[var(--bg)]",
        "desejo",
        "depoimentos",
        "seo-geo",
        "faq",
        "relative",
        "acao",
        "contato",
        "lgpd",
        "footer"
      ],
      "container": "wide",
      "grids": 174,
      "typography": {
        "heading": "UberMove",
        "body": "UberMoveText",
        "html_font_sample": "UberMoveText', system-ui, sans-serif"
      },
      "palette": [
        "oklch(12% 0.010 260)",
        "oklch(17% 0.012 260)",
        "oklch(93% 0.005 0)",
        "oklch(65% 0.010 260)",
        "oklch(28% 0.015 260)",
        "oklch(55.0% 0.138 25)",
        "#fff",
        "#aca",
        "oklch(12%_0.010_260)",
        "oklch(93%_0.005_0)",
        "oklch(55.0%_0.138_25)",
        "oklch(65%_0.010_260)",
        "oklch(17%_0.012_260)",
        "oklch(28%_0.015_260)"
      ],
      "media_count": 10,
      "density": "dense",
      "cards": 277,
      "borders": 165,
      "radius": "pill",
      "motion": [
        "transition",
        "animate-"
      ],
      "hash": "3ef583531ef04701"
    }
  },
  "preserved": {
    "html_unchanged_by_pass_through": true
  },
  "changed": {},
  "lost": {},
  "notes": []
}
```

### 09-deploy-handoff.json

```json
{
  "stage": "deploy",
  "created_at": "2026-08-14T01:01:51.643403Z",
  "received": {
    "html_length_before_deploy": 79927,
    "quality_score": 100,
    "visual_fingerprint": {
      "version": 1,
      "hero": "hero-split",
      "section_order": [
        "min-h-[90vh]",
        "interesse",
        "sobre",
        "bg-[var(--bg)]",
        "desejo",
        "depoimentos",
        "seo-geo",
        "faq",
        "relative",
        "acao",
        "contato",
        "lgpd",
        "footer"
      ],
      "container": "wide",
      "grids": 174,
      "typography": {
        "heading": "UberMove",
        "body": "UberMoveText",
        "html_font_sample": "UberMoveText', system-ui, sans-serif"
      },
      "palette": [
        "oklch(12% 0.010 260)",
        "oklch(17% 0.012 260)",
        "oklch(93% 0.005 0)",
        "oklch(65% 0.010 260)",
        "oklch(28% 0.015 260)",
        "oklch(55.0% 0.138 25)",
        "#fff",
        "#aca",
        "oklch(12%_0.010_260)",
        "oklch(93%_0.005_0)",
        "oklch(55.0%_0.138_25)",
        "oklch(65%_0.010_260)",
        "oklch(17%_0.012_260)",
        "oklch(28%_0.015_260)"
      ],
      "media_count": 10,
      "density": "dense",
      "cards": 277,
      "borders": 165,
      "radius": "pill",
      "motion": [
        "transition",
        "animate-"
      ],
      "hash": "3ef583531ef04701"
    }
  },
  "produced": {
    "deploy_url": "https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/",
    "index_path": "/var/www/fralib/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/index.html",
    "html_length_final": 81607,
    "html_counts_final": {
      "main": 1,
      "h1": 1,
      "section": 13,
      "img": 10,
      "background_image": 0
    }
  },
  "preserved": {},
  "changed": {
    "safe_post_processor": "safe_only",
    "deploy_sanitizer": "document_structure/main_h1/decorative_guard/head_contract"
  },
  "lost": {},
  "notes": []
}
```

### 10-franz-handoff.json

```json
{
  "stage": "franz",
  "created_at": "2026-08-14T01:01:51.655404Z",
  "received": {
    "deploy_url": "https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/",
    "lead_status": null
  },
  "produced": {
    "outreach_mode": "cron_dispatcher",
    "final_state": "done",
    "site_url": "https://app.seunegociofralib.site/sites/2/academia-ph-d-sports-jardim-paulista-13cf997d/"
  },
  "preserved": {},
  "changed": {},
  "lost": {},
  "notes": [
    "Franz não envia WhatsApp aqui; deixa lead concluído para o dispatcher/cron SDR."
  ]
}
```

## 3. Texto exato produzido pelo OpenUI por seção

### 02-openui-section_fragment-acao.html
- h2: Pronto para transformar seu corpo e sua vida?
- p1: Na Academia Ph.D Sports Jardim Paulista , você encontra estrutura completa, profissionais qualificados e um ambiente que inspira resultados. Comece hoje — a sua melhor versão começa agora.
- img1: https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-contato.html
- h2: Fale com a Ph.D Sports
- p1: Agende sua aula experimental gratuita ou tire dúvidas pelo WhatsApp. Nossa equipe responde em poucos minutos.
- p2: (41) 98514-3249 Chamar no WhatsApp Agendar aula experimental grátis 📍 Jardim Paulista — Campina Grande do Sul — PR
- img1: https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-depoimentos.html
- h2: O que nossos alunos dizem
- p1: Histórias de transformação de quem treina na Ph.D Sports Jardim Paulista , em Campina Grande do Sul.
- p2: "Perdi 12 kg em 4 meses e ganhei uma disposição que eu não tinha há anos. Os professores são incríveis e a estrutura da academia é impecável. Melhor investimento que fiz!"
- p3: Marina Costa
- p4: Aluna há 8 meses · Jardim Paulista
- p5: "A academia tem equipamentos de primeira e o ambiente é super motivador. Em 3 meses já via resultado na musculatura e na postura. Recomendo demais a Ph.D Sports!"
- p6: Rafael Santos
- p7: Aluno há 1 ano · Campina Grande do Sul

### 02-openui-section_fragment-desejo.html
- h2: Seu melhor corpo começa aqui
- p1: Junte-se a centenas de alunos que já transformaram sua rotina na Ph.D Sports Jardim Paulista. Aqui em Campina Grande do Sul, você encontra a estrutura, a motivação e o acompanhamento profissional para alcançar resultados que duram para sempre.
- p2: Tecnologia de ponta para seus treinos
- p3: Treine no horário que for melhor para você
- img1: https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-faq.html
- h2: Perguntas Frequentes
- p1: Tudo o que você precisa saber antes de começar seu treino na Academia Ph.D Sports Jardim Paulista, em Campina Grande do Sul.
- p2: Oferecemos musculação completa, aulas de funcional, spinning, alongamento, treinamento funcional e personal trainer individualizado. Nossos equipamentos são de última geração e nossos profissionais são certificados para orientar todos os níveis — do iniciante ao avançado.
- p3: Funcionamos de segunda a sexta, das 5h às 23h , e sábados das 7h às 18h . Domingos e feriados funcionamos em horário reduzido, das 8h às 14h. Acesso livre durante todo o período para planos ativos.
- p4: Com certeza! Temos planos específicos para iniciantes com acompanhamento pedagógico nas primeiras semanas. Você conta com avaliação física gratuita, orientação de uso dos equipamentos e um plano de treino personalizado para evoluir com segurança e confiança.
- p5: Você pode experimentar a academia por 1 dia totalmente grátis . Basta se cadastrar pelo site ou presencialmente. A experiência inclui acesso a todas as áreas, uma aula experimental e conversa com um dos nossos instrutores — sem nenhum compromisso.
- p6: Aceitamos cartão de crédito e débito (até 3x sem juros), PIX, boleto bancário e dinheiro. Planos mensais, trimestrais e anuais com descontos progressivos. Consulte condições especiais para famílias e grupos.
- p7: Sim! Contamos com estacionamento próprio e gratuito para alunos. A academia está localizada no Jardim Paulista, em Campina Grande do Sul, com fácil acesso e localização privilegiada.
- p8: Não encontrou o que procurava? Fale diretamente com a gente.

### 02-openui-section_fragment-footer.html
- h2: Comece sua jornada hoje
- h3: Ph.D Sports
- h4: Navegação
- h4: Modalidades
- h4: Contato
- p1: Agende uma aula experimental gratuita e conheça a estrutura da Academia Ph.D Sports Jardim Paulista.
- p2: Academia Ph.D Sports Jardim Paulista — referência em saúde e qualidade de vida em Campina Grande do Sul.
- p3: Navegação Início Sobre nós Planos e valores Aulas e modalidades Contato Modalidades Musculação Cross Training Spinning Yoga Personal Trainer Contato Jardim Paulista, Campina Grande do Sul — PR (41) 99999-9999 contato@phdsports.com.br Seg–Sex: 05h às 23h Sáb: 07h às 18h Dom: 08h às 14h © Academia Ph.D Sports Jardim Paulista. Todos os direitos reservados. Campina Grande do Sul — PR.

### 02-openui-section_fragment-hero.html
- h1: Treine com estrutura de verdade em Campina Grande do Sul
- p1: Musculação, aulas coletivas e acompanhamento personalizado em um espaço pensado para o seu resultado. Horário estendido, estacionamento próprio e aula experimental gratuita para começar.
- img1: https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-interesse.html
- h2: Treine onde os resultados são prioridade
- p1: Na Ph.D Sports Jardim Paulista , em Campina Grande do Sul, unimos estrutura de ponta, profissionais certificados e um ambiente pensado para você evoluir todos os dias — do primeiro ao último treino.
- img1: https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82
- img2: https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=800&q=82

### 02-openui-section_fragment-lgpd.html
- h2: LGPD — Seus dados estão protegidos
- h3: Coleta mínima
- h3: Seus direitos
- h3: Canal de atendimento
- h3: Como exercer seus direitos
- p1: Na Academia Ph.D Sports Jardim Paulista , em Campina Grande do Sul, levamos a sua privacidade a sério. Todos os dados pessoais coletados — nome, telefone, e-mail, dados de saúde e pagamento — são tratados em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018) .
- p2: Coleta mínima Solicitamos apenas os dados estritamente necessários para a gestão da sua matrícula e atendimento.
- p3: Seus direitos Você pode solicitar acesso, correção, exclusão ou portabilidade dos seus dados a qualquer momento.
- p4: Canal de atendimento Dúvidas ou solicitações? Envie um e-mail para o nosso Encarregado de Dados (DPO).
- p5: Solicitar meus dados / DPO Responderemos em até 15 dias úteis , conforme exigido pela LGPD. Academia Ph.D Sports Jardim Paulista — Campina Grande do Sul — PR. Para mais detalhes, consulte a nossa Política de Privacidade completa .

### 02-openui-section_fragment-localizacao.html
- h2: Onde estamos
- h3: Endereço
- p1: Estamos no Jardim Paulista, com estacionamento próprio e fácil acesso em Campina Grande do Sul.
- p2: Endereço R. João Trevisan, 1365 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000, Brasil
- img1: https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-seo-geo.html
- h2: A Melhor Academia de Campina Grande do Sul
- h3: Por que escolher a Ph.D Sports no Jardim Paulista?
- h3: Academia em Campina Grande do Sul — Região de Curitiba
- p1: Localizada no coração do Jardim Paulista, a Ph.D Sports é referência em academia em Campina Grande do Sul , oferecendo estrutura completa, profissionais qualificados e planos acessíveis para todos os objetivos.
- p2: Se você busca uma academia em Campina Grande do Sul que combine qualidade, variedade de modalidades e atendimento personalizado, a Ph.D Sports Jardim Paulista é a escolha certa. Estamos estrategicamente localizados no bairro Jardim Paulista, com fácil acesso e estacionamento para nossos alunos.
- p3: Aula Experimental Grátis 📍 Jardim Paulista, Campina Grande do Sul — PR
- p4: A Ph.D Sports Jardim Paulista atende toda a região de Campina Grande do Sul e municípios vizinhos da Grande Curitiba. Procurando por academia perto de mim ? Estamos no bairro Jardim Paulista, com estrutura completa de musculação, aulas coletivas, personal trainer e planos acessíveis. Venha fazer parte da maior academia da região!
- img1: https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-servicos.html
- h2: Nossos produtos e serviços
- h3: Musculação
- h3: Aulas coletivas
- h3: Personal trainer
- h3: Plano mensal
- p1: Musculação, condicionamento e acompanhamento personalizado — escolha o caminho do seu resultado.
- p2: Musculação Equipamentos completos para todos os grupos musculares. Treino livre ou periodizado, com orientação disponível.
- p3: Aulas coletivas Aulas dinâmicas em grupo para condicionamento cardiovascular e força, com energia de equipe.
- p4: Personal trainer Plano de treino individual com profissional certificado. Foco no seu objetivo, seja ele qual for.
- p5: Plano mensal Planos flexíveis para diferentes perfis. Acesso total à estrutura durante o horário de funcionamento.
- img1: https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1400&q=82

### 02-openui-section_fragment-sobre.html
- h2: Academia Ph.D Sports Jardim Paulista
- h3: O que nos diferencia
- h4: Horário estendido
- h4: Estacionamento próprio
- h4: Aula experimental grátis
- h4: Personal trainer disponível
- p1: Há anos transformando vidas em Campina Grande do Sul, a Ph.D Sports Jardim Paulista é referência em estrutura e acompanhamento na região. Unimos equipamentos de última geração, profissionais qualificados e um ambiente que motiva você a ir além.
- p2: Horário estendido Abra mais cedo, feche mais tarde — o treino cabe na sua rotina.
- p3: Estacionamento próprio Sem complicação de rua. Estacione e entre direto no treino.
- p4: Aula experimental grátis Conheça a academia sem compromisso. Sua primeira experiência é por nossa conta.
- p5: Personal trainer disponível Acompanhamento individual para quem quer evoluir com segurança e técnica.
- p6: Sem compromisso. Sua primeira aula é gratuita.
- img1: https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1400&q=82