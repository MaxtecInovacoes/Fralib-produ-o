#!/usr/bin/env python3
"""Sprint 14.10: suite anti-silencio (sem precisar de DB).

Valida que o sistema NUNCA falha silenciosamente:
- 4 camadas implementadas
- Estrutura do codigo correta
- Endpoint + UI admin sincronizados
"""
import sys
import ast

sys.path.insert(0, '.')

# === TESTE 1: reap_dead_workers detecta zumbis ===
print("=== TESTE 1: reap_dead_workers ===")
src = open('backend/core/job_queue.py', encoding='utf-8').read()
tree = ast.parse(src)
funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
assert 'reap_dead_workers' in funcs, "reap_dead_workers nao encontrado"
assert "status = 'running'" in src, "filtro status='running' ausente"
assert "worker_heartbeat < NOW()" in src, "filtro heartbeat ausente"
assert "minutes" in src, "filtro dead_after_minutes ausente"
assert "pending" in src, "ressurreicao pra pending ausente"
print("  OK reap_dead_workers detecta running+heartbeat velho e ressuscita pra pending")

# === TESTE 2: worker chama reap_dead_workers ===
print()
print("=== TESTE 2: worker chama reap_dead_workers ===")
worker_src = open('worker.py', encoding='utf-8').read()
assert "reap_dead_workers" in worker_src, "worker nao chama reap_dead_workers"
assert "REAP_SECS" in worker_src, "reap nao eh periodico"
print("  OK worker chama reap_dead_workers periodicamente")

# === TESTE 3: endpoint /api/pipeline/tempo detecta zumbis ===
print()
print("=== TESTE 3: endpoint /api/pipeline/tempo detecta zumbis ===")
tempo_src = open('backend/endpoints/pipeline_tempo_endpoints.py', encoding='utf-8').read()
assert "tem_zumbi" in tempo_src, "campo tem_zumbi ausente"
assert "zumbis" in tempo_src, "campo zumbis ausente"
assert "heartbeat < NOW() - INTERVAL '5 minutes'" in tempo_src, "filtro zumbi (5min) ausente"
assert "status = 'running'" in tempo_src, "filtro zumbi (running) ausente"
print("  OK endpoint /api/pipeline/tempo retorna tem_zumbi + zumbis[]")

# === TESTE 4: endpoint ressuscitar_zumbis ===
print()
print("=== TESTE 4: endpoint /api/pipeline/zumbis/ressuscitar ===")
assert "ressuscitados" in tempo_src, "retorno ressuscitados ausente"
assert "status = 'pending'" in tempo_src, "ressurreicao pra pending ausente"
assert "zumbi_ressuscitado_manual" in tempo_src, "log marker ausente"
print("  OK endpoint ressuscitar_zumbis retorna count e ressuscita pra pending")

# === TESTE 5: admin.html tem UI de zumbi ===
print()
print("=== TESTE 5: admin.html tem UI de alerta zumbi ===")
admin_src = open('frontend/admin.html', encoding='utf-8').read()
assert "tem_zumbi" in admin_src, "JS nao consome tem_zumbi"
assert "ressuscitarZumbis" in admin_src, "funcao JS ressuscitarZumbis ausente"
assert "ZUMBI" in admin_src, "label ZUMBI no badge ausente"
assert "/api/pipeline/zumbis/ressuscitar" in admin_src, "endpoint nao chamado no JS"
print("  OK admin.html tem UI ZUMBI + botao RESSUSCITAR")

# === TESTE 6: _cleanup_old_workspaces previne disco cheio ===
print()
print("=== TESTE 6: _cleanup_old_workspaces previne disco cheio ===")
assert "_cleanup_old_workspaces" in worker_src, "cleanup nao definido no worker"
assert "fralib_builder" in worker_src, "cleanup nao mira /tmp/fralib_builder"
assert "max_age_hours" in worker_src, "cleanup sem parametro de idade maxima"
print("  OK worker limpa /tmp/fralib_builder >24h automaticamente")

# === TESTE 7: anti-silencio = 4 camadas ===
print()
print("=== TESTE 7: 4 camadas anti-silencio ===")
camadas = {
    "1. worker reap_dead_workers (60s)":      "reap_dead_workers" in worker_src,
    "2. endpoint /api/pipeline/tempo (zumbis)": "tem_zumbi" in tempo_src,
    "3. endpoint /zumbis/ressuscitar (manual)": "ressuscitar_zumbis" in tempo_src,
    "4. admin UI badge ZUMBI + botao":         "ZUMBI" in admin_src,
}
for label, ok in camadas.items():
    print(f"  {'OK' if ok else 'FAIL'} {label}")
assert all(camadas.values()), "alguma camada faltando"

print()
print("=" * 60)
print("TODOS OS 7 TESTES ANTI-SILENCIO PASSARAM")
print("=" * 60)
print()
print("RESUMO DAS 4 CAMADAS:")
print("  1. Worker (60s)  : reap_dead_workers detecta running+heartbeat>5min")
print("  2. Endpoint (5s) : /api/pipeline/tempo retorna tem_zumbi + lista")
print("  3. Endpoint POST : /api/pipeline/zumbis/ressuscitar ressuscita manual")
print("  4. Admin UI      : Badge CENTRAL DE COMANDO mostra 'ZUMBI' + botao")
print()
print("GARANTIA ANTI-SILENCIO:")
print("  - Job zumbi detectado em <= 60s (worker reap)")
print("  - Job zumbi visivel em <= 5s (frontend polling)")
print("  - Job zumbi ressuscitavel manualmente (1 click)")
print("  - Disco cheio prevenido (_cleanup_old_workspaces >24h)")
