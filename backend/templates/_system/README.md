# FraLib 4-Axis Variation System

> Sistema deterministico de variacao visual para o OpenUI builder.
> Gera **uma combinacao coerente de 4 (na verdade 5) eixos visuais** para
> cada lead, baseado em `(lead_id, segmento)`.

---

## Os 4 (+1) Eixos

| # | Eixo | Cardinalidade | Onde mora |
|---|------|---------------|-----------|
| 1 | **ESTETICA**   | 6 opcoes   | `variation.py:ESTETICAS` |
| 2 | **TEMA**       | 10 opcoes  | `variation.py:THEMES` + `themes.css` |
| 3 | **TIPOGRAFIA** | 5 familias | `tokens.css` + `variation.py:TYPOGRAPHIES` |
| 4 | **LAYOUT**     | 3 tipos    | `variation.py:LAYOUTS` |
| 5 | **MOTION**     | 3 levels   | `tokens.css` + `variation.py:MOTIONS` |

### Os 6 valores de ESTETICA

- `BOLD_ENERGY`  — agressivo, alto contraste, cinematic motion
- `EDITORIAL`    — serif, magazine layout, suave
- `MINIMAL`      — zen, whitespace, motion quase imperceptivel
- `KINETIC`      — cyberpunk, interativo, transicoes marcadas
- `SCROLL`       — scrollytelling, magazine, longo
- `IMMERSIVE_3D` — bold + glassmorphism, cinematic motion

### Os 10 TEMAS

```
bold-dark   bold-red   kinetic-acid   trust-navy   trust-elite
zen-pure    zen-warm   editorial-cream   glassmorphism   brutalist-mono
```

### As 5 TIPOGRAFIAS

```
Inter, Playfair Display, JetBrains Mono, Space Grotesk, IBM Plex Sans
```

### Os 3 LAYOUTS

- `centered`  — max-width 1200px, gutter 24px, conteudo centralizado
- `magazine`  — max-width 1440px, gutter 32px, grid assimetrico
- `bento`     — max-width 1320px, gutter 20px, grid modular 2D

### Os 3 MOTION levels

| Level      | Duration | Easing                                | Uso                  |
|------------|----------|---------------------------------------|----------------------|
| subtle     | 0.3s     | ease-out                              | hover, micro         |
| medium     | 0.6s     | cubic-bezier(0.4, 0, 0.2, 1)          | section fade         |
| cinematic  | 1.2s     | cubic-bezier(0.16, 1, 0.3, 1)         | hero, page transitions|

---

## Como funciona

1. **Seed deterministico**:
   `seed = int(hashlib.md5(f"{lead_id}:{segmento}").hexdigest(), 16)`

2. Cada `select_*()` cria seu proprio `random.Random(seed)` (com salt)
   para garantir escolhas independentes mas reproduziveis.

3. **Coerencia**: a matriz `COHERENCE` mapeia cada estetica para os
   `(themes_validos, motions_validas, preferred_typography, preferred_layout)`
   compativeis. Ex: `BOLD_ENERGY` nao aceita `zen-pure`.

4. **`generate_variation()`** orquestra os 5 selectores e monta o dict
   final com `template_path` + `css_vars_inline` (bloco `<style>`
   pronto para injecao no `<head>`).

### Exemplo de uso

```python
from backend.templates._system import generate_variation

v = generate_variation(lead_id=42, segmento="clinica_estetica")
# {
#   'estetica': 'EDITORIAL',
#   'theme': 'editorial-cream',
#   'typography': 'Playfair Display',
#   'layout': 'magazine',
#   'motion': 'medium',
#   'template_path': '/.../templates/editorial/index.html',
#   'css_vars_inline': '<style id="fralib-variation-inline">...'
# }
```

---

## Matriz de Combinacoes Validas

A funcao `count_valid_combinations()` retorna o numero total de combinacoes
validas (produto cartesiano restrito pela matriz `COHERENCE`).

Total atual: **ver `python -c "from backend.templates._system.variation import count_valid_combinations; print(count_valid_combinations())"`**

Breakdown por estetica:

| Estetica      | Temas | Tipografias | Layouts | Motions | Subtotal |
|---------------|-------|-------------|---------|---------|----------|
| BOLD_ENERGY   |   4   |      3      |    3    |    1    |    36    |
| EDITORIAL     |   3   |      2      |    3    |    1    |    18    |
| MINIMAL       |   2   |      2      |    3    |    1    |    12    |
| KINETIC       |   4   |      2      |    3    |    2    |    48    |
| SCROLL        |   4   |      3      |    3    |    2    |    72    |
| IMMERSIVE_3D  |   4   |      2      |    3    |    1    |    24    |
| **TOTAL**     |       |             |         |         | **210**  |

(Tipografia conta como restricao suave: se `preferred_typography` esta
definido para a estetica, usa apenas essas; senao, todas as 5 familias.)

---

## Como adicionar um NOVO TEMA

1. Edite `themes.css` e adicione o bloco:
   ```css
   [data-theme="meu-novo-tema"] {
     --color-bg-light: #...;
     --color-bg-dark:  #...;
     --color-fg:       #...;
     --color-muted:    #...;
     --color-accent:   #...;
     /* opcional: */
     --font-display:   "...";
     --font-body:      "...";
   }
   ```

2. Adicione o slug em `variation.py:THEMES`.

3. Atualize a matriz `COHERENCE` para incluir o tema nas esteticas
   compativeis (ex: se for um tema bold, adicione em `BOLD_ENERGY`).

4. (Opcional) Crie uma pagina de preview no diretorio apropriado.

5. Rode `python tests/test_variation_system.py` para garantir que
   o novo tema aparece em `THEMES` e que os testes de coerencia
   continuam passando.

## Como adicionar uma NOVA ESTETICA

1. Crie o template HTML canonico em
   `backend/templates/<slug>/index.html`.

2. Adicione a constante em `variation.py:ESTETICAS`.

3. Adicione a regra em `COHERENCE`:
   ```python
   "MINHA_NOVA": {
       "themes": ["tema1", "tema2"],
       "motions": ["medium", "cinematic"],
       "preferred_typography": ["Inter", "Space Grotesk"],
       "preferred_layout": ["bento", "magazine"],
   },
   ```

4. Atualize o mapping em `_template_path_for()` para apontar para
   o diretorio criado no passo 1.

5. Adicione 1 teste em `tests/test_variation_system.py` que valide
   a coerencia da nova estetica.

---

## Integracao com o OpenUI builder

No OpenUI builder (`backend/services/openui_renderer.py`), o fluxo ideal:

```python
from backend.templates._system import generate_variation

def render_site(lead_id: int, segmento: str, prd: dict) -> str:
    v = generate_variation(lead_id, segmento)

    # 1. Carrega template canonico da estetica sorteada
    with open(v["template_path"], encoding="utf-8") as f:
        html = f.read()

    # 2. Injeta CSS vars inline (tema + tipografia + layout + motion)
    html = html.replace("{{CSS_VARS_INLINE}}", v["css_vars_inline"])

    # 3. Injeta data-theme no <body> para ativar o tema do themes.css
    html = html.replace("<body>", f'<body data-theme="{v["theme"]}">')

    # 4. (Ja existente) Substitui {{CONTEUDO_*}} pelos blocos do PRD
    html = apply_prd_to_template(html, prd)

    return html
```

> **Importante**: o `data-theme="..."` no `<body>` e o `<style>` inline
> trabalham em conjunto: o `data-theme` ativa o bloco de cores no
> `themes.css`, enquanto o inline sobrescreve `--motion-*` e `--layout-*`
> (que nao dependem do tema).

---

## Estrutura de arquivos

```
backend/templates/_system/
├── __init__.py            # exporta as 6 funcoes publicas
├── tokens.css             # design tokens base (ortogonais a tema)
├── themes.css             # 10 temas (cada um = bloco [data-theme="..."])
├── variation.py           # logica deterministica (seed + coerencia)
└── README.md              # este arquivo

tests/
└── test_variation_system.py   # 6 testes standalone
```

---

## Limites conhecidos

- **Tipografia dupla**: alguns temas (editorial-cream, trust-navy,
  trust-elite, zen-warm, brutalist-mono) ja definem `--font-display`
  proprio. Quando o lead sorteia uma tipografia diferente, o builder
  precisa sobrescrever manualmente (futuro: gerar `--font-display`
  tambem no `css_vars_inline`).

- **Segmento influence**: o parametro `segmento` afeta o seed mas NAO
  influencia a escolha de estetica/tema. Mapeamentos semanticos
  (ex: "clinica_estetica" -> EDITORIAL) devem ficar no Nicho agent,
  nao aqui. Este modulo eh puramente deterministico combinatorio.

- **Cache invalidation**: como o output depende apenas de
  `(lead_id, segmento)`, o cache key eh trivial. Mas se houver
  override manual (ex: lead VIP pediu tema especifico), o cache
  precisa ser invalidado pelo override_id.