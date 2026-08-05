SELECT id, nome, cidade, segmento, user_id, briefing_json
FROM leads
WHERE briefing_json IS NOT NULL
  AND briefing_json != ''
  AND LEFT(TRIM(briefing_json), 1) = '{'
  AND RIGHT(TRIM(briefing_json), 1) = '}'
LIMIT 5;
