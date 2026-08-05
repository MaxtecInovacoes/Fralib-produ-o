"""
keyword_research.py - Pesquisa de keywords transacionais por nicho+cidade
Cache PostgreSQL 30 dias. Roda em paralelo com o Hunter na FASE 1.

Objetivo: descobrir o que as pessoas estão buscando que CONVERTE DINHEIRO
no nicho — não design, não UI, mas intenção de compra real.
"""
import os, re, time, hashlib, requests
from datetime import datetime, timedelta

# Queries focadas em intenção transacional/comercial por nicho
# "o que as pessoas buscam quando querem PAGAR por esse serviço"
QUERIES_TRANSACIONAIS = {
    "academia":       "academia {cidade} preço mensalidade matrícula perto",
    "crossfit":       "crossfit {cidade} aula experimental preço matrícula",
    "barbearia":      "barbearia {cidade} corte masculino agendamento preço",
    "salao":          "salão de beleza {cidade} progressiva coloração agendamento",
    "clinica":        "clínica médica {cidade} consulta particular agendamento preço",
    "odontologia":    "dentista {cidade} implante clareamento consulta preço",
    "estetica":       "clínica estética {cidade} tratamento preço agendamento",
    "nutricionista":  "nutricionista {cidade} consulta preço plano alimentar",
    "psicologia":     "psicólogo {cidade} consulta particular preço agendamento",
    "advocacia":      "advogado {cidade} consulta honorários trabalhista",
    "contabilidade":  "contador {cidade} MEI abertura empresa preço",
    "imobiliaria":    "imobiliária {cidade} apartamento comprar alugar",
    "restaurante":    "restaurante {cidade} delivery reserva cardápio",
    "pizzaria":       "pizzaria {cidade} delivery pedido promoção",
    "padaria":        "padaria {cidade} encomenda bolo pão artesanal",
    "pet":            "pet shop {cidade} banho tosa veterinário preço",
    "farmacia":       "farmácia {cidade} manipulação delivery plantão",
    "escola":         "escola {cidade} matrícula mensalidade ensino",
    "auto_pecas":     "mecânica {cidade} orçamento revisão preço",
    "arquitetura":    "arquiteto {cidade} projeto residencial preço",
    "fotografia":     "fotógrafo {cidade} ensaio casamento preço",
}

# Queries de concorrência — quem está rankeando e o que oferecem
QUERIES_CONCORRENCIA = {
    "academia":       "melhor academia {cidade} avaliações",
    "barbearia":      "melhor barbearia {cidade} avaliações",
    "nutricionista":  "melhor nutricionista {cidade} avaliações resultado",
    "odontologia":    "melhor dentista {cidade} avaliações implante",
    "estetica":       "melhor clínica estética {cidade} resultado antes depois",
    "restaurante":    "melhor restaurante {cidade} avaliações",
    "advocacia":      "melhor advogado {cidade} trabalhista resultado",
}


def _get_db_conn():
    """Conexão PostgreSQL via DATABASE_URL do ambiente"""
    import psycopg2
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL não encontrada no ambiente")
    m = re.search(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(\S+)', db_url)
    if not m:
        raise ValueError("DATABASE_URL com formato inválido")
    user, pwd, host, port, db = m.groups()
    return psycopg2.connect(host=host, port=int(port), dbname=db, user=user, password=pwd)


def _garantir_tabela():
    """Cria tabela keyword_cache se não existir."""
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keyword_cache (
                id SERIAL PRIMARY KEY,
                segmento TEXT NOT NULL,
                cidade TEXT NOT NULL,
                dados TEXT NOT NULL,
                atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(segmento, cidade)
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[KW] Erro ao criar tabela: {e}")


def _cache_get(segmento: str, cidade: str) -> str | None:
    """Retorna dados do cache se válidos (< 30 dias)."""
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT dados, atualizado_em FROM keyword_cache WHERE segmento=%s AND cidade=%s",
            (segmento.lower(), cidade.lower())
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        dados, atualizado_em = row
        if datetime.now() - atualizado_em < timedelta(days=30):
            print(f"[KW] Cache HIT: {segmento} em {cidade} (atualizado {atualizado_em.strftime('%d/%m/%Y')})")
            return dados
        print(f"[KW] Cache EXPIRADO: {segmento} em {cidade} — renovando")
        return None
    except Exception as e:
        print(f"[KW] Erro cache_get: {e}")
        return None


def _cache_set(segmento: str, cidade: str, dados: str):
    """Salva ou atualiza cache."""
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO keyword_cache (segmento, cidade, dados, atualizado_em)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (segmento, cidade) DO UPDATE
                SET dados = EXCLUDED.dados, atualizado_em = NOW()
        """, (segmento.lower(), cidade.lower(), dados))
        conn.commit()
        conn.close()
        print(f"[KW] Cache salvo: {segmento} em {cidade}")
    except Exception as e:
        print(f"[KW] Erro cache_set: {e}")


def _jina_buscar(query: str, timeout: int = 15) -> str:
    """Busca via Jina AI Reader — retorna texto markdown do resultado."""
    try:
        url = "https://r.jina.ai/https://www.google.com/search?q=" + requests.utils.quote(query)
        headers = {"X-Return-Format": "markdown", "X-Timeout": str(timeout)}
        jina_key = os.getenv("JINA_API_KEY", "")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"
        resp = requests.get(url, headers=headers, timeout=timeout + 5)
        if resp.status_code == 200:
            return resp.text[:3000]
        return ""
    except Exception as e:
        print(f"[KW] Jina erro: {e}")
        return ""


def _extrair_keywords_do_texto(texto: str, segmento: str, cidade: str) -> list:
    """Extrai termos de busca relevantes do texto retornado pelo Jina."""
    keywords = []
    linhas = texto.split("\n")
    for linha in linhas:
        linha = linha.strip()
        if not linha or len(linha) < 10 or len(linha) > 120:
            continue
        # Filtrar linhas que parecem queries de busca (contêm cidade ou segmento)
        seg_lower = segmento.lower()
        cid_lower = cidade.lower()
        linha_lower = linha.lower()
        if cid_lower in linha_lower or seg_lower in linha_lower:
            # Limpar markdown
            linha = re.sub(r'[\*\#\[\]\(\)\`]', '', linha).strip()
            if linha and linha not in keywords:
                keywords.append(linha)
                if len(keywords) >= 15:
                    break
    return keywords


def pesquisar_keywords_nicho(segmento: str, cidade: str) -> str:
    """
    Pesquisa keywords transacionais do nicho+cidade via Jina.
    Cache 30 dias no PostgreSQL.
    Retorna string formatada para injetar no prompt do ArquitetoMestre.
    """
    _garantir_tabela()

    # Verificar cache
    cached = _cache_get(segmento, cidade)
    if cached:
        return cached

    print(f"[KW] Pesquisando keywords: {segmento} em {cidade}...")

    seg_lower = segmento.lower()

    # Encontrar query transacional para o nicho
    query_transacional = None
    for key, q in QUERIES_TRANSACIONAIS.items():
        if key in seg_lower:
            query_transacional = q.format(cidade=cidade)
            break
    if not query_transacional:
        query_transacional = f"{segmento} {cidade} preço agendamento consulta"

    # Query de concorrência (opcional)
    query_concorrencia = None
    for key, q in QUERIES_CONCORRENCIA.items():
        if key in seg_lower:
            query_concorrencia = q.format(cidade=cidade)
            break

    # Buscar via Jina
    texto_transacional = _jina_buscar(query_transacional)
    texto_concorrencia = _jina_buscar(query_concorrencia) if query_concorrencia else ""

    # Extrair keywords
    kw_transacionais = _extrair_keywords_do_texto(texto_transacional, segmento, cidade)
    kw_concorrencia = _extrair_keywords_do_texto(texto_concorrencia, segmento, cidade) if texto_concorrencia else []

    # Google Suggest para volume real
    suggest_terms = []
    try:
        suggest_url = (
            "https://suggestqueries.google.com/complete/search"
            "?client=firefox&hl=pt-BR&q="
            + requests.utils.quote(f"{segmento} {cidade}")
        )
        resp = requests.get(suggest_url, timeout=5)
        if resp.status_code == 200:
            import json
            data = json.loads(resp.text)
            suggest_terms = data[1][:8] if len(data) > 1 else []
    except Exception:
        pass

    # Montar resultado formatado
    linhas = [f"=== KEYWORD RESEARCH: {segmento.upper()} em {cidade.upper()} ==="]
    linhas.append(f"Atualizado: {datetime.now().strftime('%d/%m/%Y')}")
    linhas.append("")

    if suggest_terms:
        linhas.append("BUSCAS REAIS (Google Suggest — o que as pessoas digitam):")
        for t in suggest_terms:
            linhas.append(f"  - {t}")
        linhas.append("")

    if kw_transacionais:
        linhas.append("INTENÇÃO TRANSACIONAL (pessoas prontas para pagar):")
        for kw in kw_transacionais[:8]:
            linhas.append(f"  - {kw}")
        linhas.append("")

    if kw_concorrencia:
        linhas.append("CONCORRÊNCIA LOCAL (o que os líderes do nicho oferecem):")
        for kw in kw_concorrencia[:5]:
            linhas.append(f"  - {kw}")
        linhas.append("")

    linhas.append("INSTRUÇÃO: Use estas keywords naturalmente no H1, subtítulos, CTAs e meta description.")
    linhas.append("Priorize as de intenção transacional — são as que convertem em clientes pagantes.")

    resultado = "\n".join(linhas)

    # Salvar no cache
    _cache_set(segmento, cidade, resultado)

    return resultado
