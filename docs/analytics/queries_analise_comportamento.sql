-- ============================================================================
-- FraLib OS — Queries de Análise de Comportamento da Landing
-- ============================================================================
-- Use estas queries para entender ONDE os usuários saem e O QUE melhorar.
-- Tabela: landing_analytics (session_id, evento, valor_extra, ip_hash, ua_hash)
-- ============================================================================


-- ============================================================================
-- 1. VISÃO GERAL: Total de sessões e taxa de bounce
-- ============================================================================
WITH sessoes AS (
    SELECT
        session_id,
        MIN(criado_em) AS primeira_visita,
        MAX(criado_em) AS ultima_visita,
        COUNT(*) AS total_eventos,
        BOOL_OR(evento = 'bounce') AS foi_bounce
    FROM landing_analytics
    WHERE criado_em >= NOW() - INTERVAL '7 days'
    GROUP BY session_id
)
SELECT
    COUNT(*) AS total_sessoes,
    COUNT(*) FILTER (WHERE foi_bounce) AS bounces,
    ROUND(100.0 * COUNT(*) FILTER (WHERE foi_bounce) / COUNT(*), 2) AS bounce_rate_pct,
    ROUND(AVG(total_eventos), 2) AS media_eventos_por_sessao
FROM sessoes;


-- ============================================================================
-- 2. SCROLL DEPTH: Quantos usuários chegam até cada profundidade
-- ============================================================================
-- Mostra a % de usuários que rolam até 25%, 50%, 75%, 90%, 100%
-- Útil para identificar ONDE os usuários abandonam a página
WITH sessoes_unicas AS (
    SELECT DISTINCT session_id
    FROM landing_analytics
    WHERE criado_em >= NOW() - INTERVAL '7 days'
      AND evento = 'view'
),
scroll_depth AS (
    SELECT
        SPLIT_PART(valor_extra, '|', 1)::INT AS depth_pct,
        SPLIT_PART(valor_extra, '|', 2) AS section_id,
        session_id
    FROM landing_analytics
    WHERE evento = 'scroll_depth'
      AND criado_em >= NOW() - INTERVAL '7 days'
)
SELECT
    depth_pct,
    COUNT(DISTINCT session_id) AS usuarios_alcancaram,
    COUNT(DISTINCT section_id) AS secoes_diferentes,
    ROUND(100.0 * COUNT(DISTINCT session_id) / (SELECT COUNT(*) FROM sessoes_unicas), 2) AS pct_usuarios
FROM scroll_depth
GROUP BY depth_pct
ORDER BY depth_pct;


-- ============================================================================
-- 3. SEÇÕES COM MAIS ABANDONO: Onde os usuários saem?
-- ============================================================================
-- Mostra a última seção visível antes do exit
-- CRÍTICO: Seção com mais exit = ponto de fricção
WITH ultimas_secoes AS (
    SELECT
        session_id,
        valor_extra AS exit_section,
        ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY criado_em DESC) AS rn
    FROM landing_analytics
    WHERE evento = 'exit_section'
      AND criado_em >= NOW() - INTERVAL '7 days'
)
SELECT
    COALESCE(exit_section, 'unknown') AS secao,
    COUNT(*) AS total_exits,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_exits
FROM ultimas_secoes
WHERE rn = 1
GROUP BY exit_section
ORDER BY total_exits DESC;


-- ============================================================================
-- 4. FUNIL DE CONVERSÃO: Onde perdemos usuários?
-- ============================================================================
-- Mostra a % de usuários que completa cada etapa do funil
-- visit → scroll_25 → scroll_50 → cta_clicked → form_viewed → form_submitted
WITH etapas AS (
    SELECT
        session_id,
        BOOL_OR(evento = 'view')                  AS visit,
        BOOL_OR(evento = 'funnel_scroll_25')      AS scroll_25,
        BOOL_OR(evento = 'funnel_scroll_50')      AS scroll_50,
        BOOL_OR(evento = 'funnel_cta_clicked')    AS cta_clicked,
        BOOL_OR(evento = 'funnel_form_viewed')    AS form_viewed,
        BOOL_OR(evento = 'funnel_form_submitted') AS form_submitted
    FROM landing_analytics
    WHERE criado_em >= NOW() - INTERVAL '7 days'
    GROUP BY session_id
),
totais AS (
    SELECT
        COUNT(*) AS total_visit,
        COUNT(*) FILTER (WHERE visit)          AS n_visit,
        COUNT(*) FILTER (WHERE scroll_25)      AS n_scroll_25,
        COUNT(*) FILTER (WHERE scroll_50)      AS n_scroll_50,
        COUNT(*) FILTER (WHERE cta_clicked)    AS n_cta_clicked,
        COUNT(*) FILTER (WHERE form_viewed)    AS n_form_viewed,
        COUNT(*) FILTER (WHERE form_submitted) AS n_form_submitted
    FROM etapas
)
SELECT
    'visit'           AS etapa, n_visit          AS usuarios,
    ROUND(100.0 * n_visit / total_visit, 2)        AS pct_do_total,
    NULL::FLOAT                                        AS pct_da_etapa_anterior
FROM totais
UNION ALL SELECT 'scroll_25',      n_scroll_25,
    ROUND(100.0 * n_scroll_25 / total_visit, 2),
    ROUND(100.0 * n_scroll_25 / n_visit, 2)
FROM totais
UNION ALL SELECT 'scroll_50',      n_scroll_50,
    ROUND(100.0 * n_scroll_50 / total_visit, 2),
    ROUND(100.0 * n_scroll_50 / n_scroll_25, 2)
FROM totais
UNION ALL SELECT 'cta_clicked',    n_cta_clicked,
    ROUND(100.0 * n_cta_clicked / total_visit, 2),
    ROUND(100.0 * n_cta_clicked / n_scroll_50, 2)
FROM totais
UNION ALL SELECT 'form_viewed',    n_form_viewed,
    ROUND(100.0 * n_form_viewed / total_visit, 2),
    ROUND(100.0 * n_form_viewed / n_cta_clicked, 2)
FROM totais
UNION ALL SELECT 'form_submitted', n_form_submitted,
    ROUND(100.0 * n_form_submitted / total_visit, 2),
    ROUND(100.0 * n_form_submitted / n_form_viewed, 2)
FROM totais
ORDER BY
    CASE etapa
        WHEN 'visit'           THEN 1
        WHEN 'scroll_25'       THEN 2
        WHEN 'scroll_50'       THEN 3
        WHEN 'cta_clicked'     THEN 4
        WHEN 'form_viewed'     THEN 5
        WHEN 'form_submitted'  THEN 6
    END;


-- ============================================================================
-- 5. CTAs MAIS CLICADOS: Qual CTA converte mais?
-- ============================================================================
SELECT
    evento,
    COUNT(*) AS total_clicks,
    COUNT(DISTINCT session_id) AS usuarios_unicos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_do_total
FROM landing_analytics
WHERE evento LIKE 'click_%'
  AND criado_em >= NOW() - INTERVAL '7 days'
GROUP BY evento
ORDER BY total_clicks DESC;


-- ============================================================================
-- 6. SEÇÕES MAIS VISTAS: Em qual seção os usuários passam mais tempo?
-- ============================================================================
-- Identifica seções populares = mantenha; seções pouco vistas = remova ou reposicione
SELECT
    valor_extra AS section_id,
    COUNT(*) AS views,
    COUNT(DISTINCT session_id) AS usuarios_unicos
FROM landing_analytics
WHERE evento = 'section_view'
  AND criado_em >= NOW() - INTERVAL '7 days'
GROUP BY section_id
ORDER BY views DESC;


-- ============================================================================
-- 7. TEMPO MÉDIO DE PERMANÊNCIA
-- ============================================================================
SELECT
    ROUND(AVG(valor_extra::INT), 2) AS media_segundos,
    MIN(valor_extra::INT) AS min_segundos,
    MAX(valor_extra::INT) AS max_segundos,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_extra::INT) AS mediana_segundos
FROM landing_analytics
WHERE evento = 'time_spent'
  AND criado_em >= NOW() - INTERVAL '7 days';


-- ============================================================================
-- 8. SESSÕES QUE VIRAM ATÉ O FINAL (100% scroll)
-- vs SESSÕES QUE ABANDONARAM CEDO
-- ============================================================================
WITH completas AS (
    SELECT DISTINCT session_id
    FROM landing_analytics
    WHERE evento = 'scroll_depth'
      AND valor_extra LIKE '100|%'
      AND criado_em >= NOW() - INTERVAL '7 days'
),
abandono_precoce AS (
    SELECT DISTINCT session_id
    FROM landing_analytics
    WHERE evento = 'scroll_depth'
      AND valor_extra LIKE '25|%'
      AND criado_em >= NOW() - INTERVAL '7 days'
)
SELECT
    'completas_100' AS tipo,
    COUNT(*) AS sessoes
FROM completas
UNION ALL
SELECT
    'abandono_precoce_25' AS tipo,
    COUNT(*) AS sessoes
FROM abandono_precoce;


-- ============================================================================
-- 9. DIAGNÓSTICO DE PÁGINA: Heatmap por seção
-- ============================================================================
-- Cruzamento: qual seção + qual profundidade = quantos usuários
-- Matriz: rows=seção, cols=depth
SELECT
    SPLIT_PART(valor_extra, '|', 2) AS secao,
    SPLIT_PART(valor_extra, '|', 1) AS depth_pct,
    COUNT(DISTINCT session_id) AS usuarios
FROM landing_analytics
WHERE evento = 'scroll_depth'
  AND criado_em >= NOW() - INTERVAL '7 days'
GROUP BY secao, depth_pct
ORDER BY secao, depth_pct::INT;
