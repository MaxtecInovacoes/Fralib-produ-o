import os
import sys
sys.path.insert(0, "/root/fralib/backend/agents")
from agent_rag import get_agent_temperature, buscar_contexto_rag, mark_rag_used
from validation_enforcer import require_rag
from color_extractor import gerar_paleta_completa as _gerar_paleta
from llm_direct import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL
import base64 as _b64
import re as _re_id
import requests as _req
from alex_models import AlexInput, AlexOutput, ALEX_INSTRUCTIONS, gerar_design_tokens
from alex_logo import limpar_url_google, processar_logo, remover_fundo, vetorizar_logo
from alex_fotos import processar_fotos, converter_para_webp, upscale_foto, redimensionar_foto, gerar_thumbnail, baixar_imagem_seguro, obter_dimensoes, obter_tamanho_arquivo
from alex_cores import extrair_paleta, rgb_para_hex, classificar_fotos_por_tipo, calcular_economia


@require_rag("Alex")
def processar_imagens(input_data: AlexInput) -> AlexOutput:
    temperature = get_agent_temperature("alex")
    rag_alex = buscar_contexto_rag("cores logo imagens segmento", "alex")
    mark_rag_used("Alex")
    print("[Alex] RAG: " + str(len(rag_alex)) + " chars")

    slug = input_data.slug or "temp_" + str(abs(hash(input_data.nome)))[:8]
    assets_dir = "/var/www/fralib/sites/" + slug + "/assets"
    os.makedirs(assets_dir, exist_ok=True)

    print("[ALEX] 1/6 Baixando imagens...")
    todas_fotos_data = processar_fotos(input_data.fotos, assets_dir=assets_dir)
    todas_webp = todas_fotos_data["fotos_webp"]

    print("[ALEX] 2/6 Identificando logo via Claude Vision...")
    logo_url_identificada = None
    try:
        cp = []
        idx_list = []
        for i, f2 in enumerate(todas_webp[:9]):
            local = f2.get("webp", "")
            if local and local.startswith("/var/www/") and os.path.exists(local):
                with open(local, "rb") as img_f:
                    d = _b64.b64encode(img_f.read()).decode("utf-8")
                cp.append({"type": "image", "source": {"type": "base64", "media_type": "image/webp", "data": d}})
                cp.append({"type": "text", "text": "[Imagem " + str(i+1) + "]"})
                idx_list.append(i)
        if cp:
            cp.append({"type": "text", "text": "Analise imagens de " + input_data.segmento + " chamado " + input_data.nome + ". Identifique LOGO e FACHADA. Responda APENAS: LOGO:N FACHADA:N"})
            ua = ANTHROPIC_BASE_URL + "/v1/messages"
            hd = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            pl = {"model": "claude-sonnet-4-6", "max_tokens": 30, "temperature": 0.0, "system": "Identifica logo e fachada. Responda apenas no formato solicitado.", "messages": [{"role": "user", "content": cp}]}
            r = _req.post(ua, headers=hd, json=pl, timeout=60)
            r.raise_for_status()
            resp = next((b["text"].strip() for b in r.json().get("content", []) if b.get("type") == "text"), "")
            import re as _re2
            lm = _re2.search(r"LOGO:(\d+)", resp)
            if lm and int(lm.group(1)) > 0:
                ix = int(lm.group(1)) - 1
                if 0 <= ix < len(idx_list):
                    logo_url_identificada = todas_webp[idx_list[ix]].get("webp") or todas_webp[idx_list[ix]].get("original")
                    print("[ALEX] Logo identificada: imagem " + str(ix+1))
    except Exception as e:
        print("[ALEX] Vision falhou: " + str(e))
        raise

    logo_original_url = logo_url_identificada or (todas_webp[0].get("original", "") if todas_webp else "")
    fotos_sem_logo = [f2 for f2 in todas_webp if f2.get("webp") != logo_url_identificada]

    print("[ALEX] 3/6 Processando logo...")
    logo_data = processar_logo(logo_original_url, assets_dir=assets_dir)

    print("[ALEX] 4/6 Extraindo paleta...")
    logo_url_para_cores = logo_data.get("logo_original") or logo_data.get("logo_webp") or logo_data.get("logo_png")
    fotos_webp_locais = []
    for f2 in (fotos_sem_logo or []):
        p = f2.get("webp") or f2.get("original", "") if isinstance(f2, dict) else str(f2)
        if p and os.path.exists(p): fotos_webp_locais.append(p)
        if len(fotos_webp_locais) >= 6: break
    fotos_para_cores = fotos_webp_locais if fotos_webp_locais else (input_data.fotos or [])[:6]
    paleta_ce = _gerar_paleta(logo_url=logo_url_para_cores, fotos=fotos_para_cores)
    paleta = {
        "primaria": paleta_ce.get("primaria", "#374151"),
        "secundaria": paleta_ce.get("secundaria", "#f9fafb"),
        "acento": paleta_ce.get("acento", "#e85d04"),
        "complementar_1": paleta_ce.get("background", "#ffffff"),
        "complementar_2": paleta_ce.get("texto", "#1f2937"),
    }

    print("[ALEX] 5/6 Calculando economia...")
    economia = calcular_economia(input_data.fotos, todas_webp)

    design_tokens = gerar_design_tokens(paleta, is_dark=False)
    print("[ALEX] 6/6 Classificando fotos...")
    fotos_data = {"fotos_webp": fotos_sem_logo, "qualidade": todas_fotos_data["qualidade"], "total_upscaled": todas_fotos_data["total_upscaled"]}
    fotos_classificadas = classificar_fotos_por_tipo(fotos_data["fotos_webp"], input_data.segmento)

    output = AlexOutput(
        logo_svg=logo_data.get("logo_svg"),
        logo_webp=logo_data["logo_webp"],
        logo_png=logo_data["logo_png"],
        logo_original=logo_data["logo_original"],
        paleta=paleta,
        design_tokens=design_tokens,
        fotos_webp=fotos_data["fotos_webp"],
        fotos_qualidade=fotos_data["qualidade"],
        fotos_classificadas=fotos_classificadas,
        total_fotos=len(fotos_sem_logo),
        total_upscaled=fotos_data["total_upscaled"],
        total_size_original=economia["original_mb"],
        total_size_otimizado=economia["otimizado_mb"],
        economia_percentual=economia["economia_percentual"],
        assets_dir=assets_dir,
    )
    print("[ALEX] Processamento completo!")
    return output
