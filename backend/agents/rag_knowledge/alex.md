# Conhecimento RAG - Alex (Processamento de Imagens)

## Missao
Processar imagens do lead, extrair paleta real do logo, salvar assets persistentes.
Os assets do Alex sao usados por todos os agentes seguintes - qualidade aqui = qualidade no site.

## Regras de Salvamento

### SEMPRE salvar em assets_dir persistente
- Caminho: /var/www/fralib/sites/{slug}/assets/
- NUNCA salvar apenas em /tmp/ (expira e quebra o site)
- Logo: assets_dir/logo.webp e assets_dir/logo.svg (se vetorizavel)
- Fotos: assets_dir/foto_1.webp, foto_2.webp, etc.
- Thumbnails: assets_dir/thumb_1.webp, thumb_2.webp, etc.

## Classificacao de Imagens

### Logo (usar como identidade visual)
- Aspect ratio proximo de 1:1 (0.8 a 1.2)
- Largura menor que 1000px
- Se logo_url vier do Hunter, usar diretamente sem classificar

### Fotos (usar no site)
- Aspect ratio diferente de 1:1
- Largura maior que 1000px geralmente
- Processar: redimensionar para max 1920px, converter para WebP

## Extracao de Paleta

### Ordem de prioridade
1. Extrair do logo (ColorThief - 5 cores dominantes)
2. Se logo indisponivel, extrair da primeira foto
3. Se nenhuma imagem disponivel, usar paleta neutra profissional

### Paletas neutras por segmento (fallback)
- Academia: primaria=#1a1a2e, secundaria=#16213e, acento=#e94560
- Clinica: primaria=#0077b6, secundaria=#f0f4f8, acento=#00b4d8
- Restaurante: primaria=#2d1b00, secundaria=#f5e6d3, acento=#c9a227
- Barbearia: primaria=#1a1a1a, secundaria=#2d2d2d, acento=#c9a227
- Padaria: primaria=#5c3d2e, secundaria=#f5e6d3, acento=#e07b39
- Padrao: primaria=#2C3E50, secundaria=#34495E, acento=#E74C3C

## Qualidade de Imagens

### WebP (sempre converter)
- Logo: qualidade 90
- Fotos principais: qualidade 85
- Thumbnails: qualidade 80, largura 400px

### Upscale (quando necessario)
- Fotos com largura < 800px: marcar para upscale
- Usar Real-ESRGAN quando disponivel

## Saida Esperada (AlexOutput)

Campos obrigatorios:
- logo_webp: caminho absoluto em assets_dir
- logo_png: caminho absoluto em assets_dir
- paleta: dict com primaria, secundaria, acento, complementar_1, complementar_2
- fotos_webp: lista com webp e thumbnail em assets_dir
- assets_dir: caminho completo /var/www/fralib/sites/{slug}/assets/
