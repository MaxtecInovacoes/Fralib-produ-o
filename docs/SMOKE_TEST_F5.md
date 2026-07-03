# F5 — Smoke Test Manual em Staging/Produção

**Pré-requisito:** branch `codex/fase-0-1-autonomous` merged em `master` (deploy automático reinicia backend).
**Quando rodar:** antes de fechar release / após deploy de nova fase.

---

## Briefing canônico (fixo, não mude)

```
segmento:    restaurante
cidade:      São Paulo
whatsapp:    11999998877  →  wa.me/5511999998877
endereço:    Rua Augusta 1500
maps_url:    https://maps.google.com/?q=restaurante+bella+napoli
tier:        ELITE
```

Use nome consistente (`Restaurante Bella Napoli` ou outro) — o que importa é o slug.

---

## Checklist de execução (no navegador/servidor)

### 1. Disparar geração
- Acessar https://seunegociofralib.site
- Login como superadmin
- Criar lead com o briefing canônico acima
- Acionar `pipeline/iniciar`

### 2. Conferir HTML deployado (FASE A4 + B3 + G)

```bash
# Buscar HTML publicado
curl -s "https://seunegociofralib.site/sites/<tenant>/<slug>/" > /tmp/site.html

# Tokens OKLch presentes (B3)
grep -oE "oklch\([^)]+\)" /tmp/site.html | head -5
# Esperado: ver lightness/chroma/hue reais do briefing, não cores genéricas

# SEM fallbacks hardcoded (A4)
! grep -E "Negócio local|sua cidade|atendimento local|#contato|Lorem ipsum" /tmp/site.html
# Esperado: exit code 1 (nenhuma string proibida presente)

# Telefone REAL no link (B1)
grep -oE "wa.me/[0-9]+" /tmp/site.html
# Esperado: wa.me/5511999998877

# Endereço real no HTML
grep -i "augusta" /tmp/site.html
# Esperado: 1+ match com o endereço informado

# Maps URL real (não placeholder)
grep -oE 'maps.google[^"]+' /tmp/site.html | head -1
# Esperado: URL do briefing ou gerada a partir do endereço
```

### 3. Conferir logs do servidor (FASE C6)

```bash
ssh root@187.77.37.72 "tail -n 500 /var/log/fralib/blog_cron.log 2>/dev/null; \
  find /root/fralib -name '*.log' -mmin -10 -exec tail -n 50 {} \;" | \
  grep -E "retry_attempt|qg_verdict|quality_guardian" | tail -30
```

Esperado ver por agente:
```json
{"event":"retry_attempt","agent":"design_director","attempt":1,"max_attempts":3,...}
{"event":"retry_attempt","agent":"unsplash_fetcher","attempt":1,"max_attempts":3,...}
```

### 4. Conferir Quality Guardian no estado (FASE G)

```sql
-- No banco postgres do VPS
SELECT run_id, qg_history, qg_verdict->>'decision' as decision,
       qg_verdict->>'overall_score' as score
FROM pipeline_state
ORDER BY created_at DESC LIMIT 5;
```

Esperado:
- `decision = "deploy"` ou `"deploy_with_warning"`
- `score >= 5.0`
- `qg_history` contém entrada com `attempt`, `score`, `decision`

Se aparecer `block` ou `score < 5.0`: investigar feedback no log e (se apropriado) deixar o loop QG-retry trabalhar — se na 3ª correção ainda bloquear, é sinal de bug no builder.

---

## Rollback se houver regressão

```bash
# No servidor
cd /root/repos/fralib
git log --oneline -5
git checkout cc2de8df  # volta pra último commit bom conhecido
systemctl restart fralib-backend  # ou pm2 restart, conforme deploy
```

---

## Resultado esperado (resumo executivo)

✅ HTML com tokens OKLch reais (lightness/chroma/hue calculados do briefing)
✅ Telefone `wa.me/5511999998877` no lugar de `#contato`
✅ Endereço e Maps URL reais, não placeholders
✅ Logs estruturados com `event=retry_attempt` por agente transiente
✅ QG verdict = `deploy` ou `deploy_with_warning`
✅ Se houver block, QG-retry corrige em até 3 rodadas antes de desistir

---

## Smoke test automatizado (sem rede)

Para validar localmente sem depender de servidor/auth:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from backend.agents.quality_guardian import run_quality_guardian
html = open('tests/fixtures/html_canonico.html').read()
v = run_quality_guardian(html)
assert v.decision in ('deploy', 'deploy_with_warning'), f'QG bloqueou: {v.feedback}'
assert all(s not in html.lower() for s in ['negocio local', 'sua cidade', '#contato', 'lorem ipsum'])
assert 'wa.me/5511999998877' in html
print(f'OK local: score={v.overall_score:.1f} decision={v.decision}')
"
```

Este já foi validado: score 7.8/10, decision=deploy.

---

*Validação manual referencia F5 do plano 2026-07-02 + FASE G de QG-retry (commit `a50a6ca3`).*
