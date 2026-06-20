# Análise de Logs Centralizados (Loki/Elasticsearch) - FraLib

**Data:** 2026-06-20
**Autor:** Claude Code (Análise READ-ONLY)
**Objetivo:** Avaliar viabilidade de implementar agregação de logs centralizados

---

## Seção 1: Inventário de Logs Atuais

### 1.1 Sistema de Logs Python (Aplicação)

| Arquivo/Caminho | Tipo | Conteúdo | Rotação |
|-----------------|------|----------|---------|
| `logs/fralib.log` | Python logging | Log geral da aplicação | Configurável via `LOG_FILE` em `config.py` |
| `logs/builder_manifests/*.json` | JSON | Manifestos de builds | 70+ arquivos JSON |
| `logs/visual-tests/*.png` | Imagens | Testes visuais | Manual |

### 1.2 systemd (Journals) - PRODUÇÃO

| Serviço | SyslogIdentifier | Tipo Output | Política |
|---------|------------------|-------------|----------|
| `fralib-api` | `fralib-api` | journal (stdout/stderr) | `StandardOutput=journal` |
| `fralib-worker` | `fralib-worker` | journal (stdout/stderr) | `StandardOutput=journal` |
| `fralib-franz` | - | journal | systemd padrão |
| `fralib-wpp-listener` | - | journal | systemd padrão |
| `fralib-hermes` | - | journal | systemd padrão |

### 1.3 PM2 (Legado - ainda pode existir)

| Processo | Caminho Log | Status |
|---------|-------------|--------|
| `fralib` | `~/.pm2/logs/fralib-out.log` | Em coexistência (migration em progresso) |
| `fralib-worker` | `~/.pm2/logs/fralib-worker-out.log` | Em coexistência |
| `fralib-franz-worker` | `~/.pm2/logs/fralib-franz-worker-out.log` | Em coexistência |
| `fralib-hermes-watchdog` | `~/.pm2/logs/fralib-hermes-watchdog-out.log` | Em coexistência |
| `fralib-wpp-listener` | `~/.pm2/logs/fralib-wpp-listener-out.log` | Em coexistência |

### 1.4 Configuração de Logging Python

**Localização:** `backend/core/config.py`

```python
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/fralib.log")
```

**Padrões de Logging:**
- `worker.py`: `logging.basicConfig(level=logging.INFO, format='%(asctime)s [worker] %(levelname)s %(message)s')`
- `whatsapp_listener.py`: `logging.basicConfig(level=logging.INFO, format="[WPP-Listener] %(message)s")`
- `server.py`: Uvicorn com TokenMaskFilter (mascara tokens nos logs de acesso)

### 1.5 Padrão de Mascaramento (server.py)

```python
class _TokenMaskFilter(logging.Filter):
    # Máscara: token=valor, Bearer token, access_token=, jwt=, session=, code=
    _patterns = [
        r'(token=)[A-Za-z0-9\-_\.+=/]+',
        r'(Bearer\s+)[A-Za-z0-9\-_\.+=/]+',
        r'(access_token=)[A-Za-z0-9\-_\.+=/]+',
        r'(jwt=)[A-Za-z0-9\-_\.+=/]+',
        r'(session=)[A-Za-z0-9\-_\.+=/]+',
        r'(code=)[A-Za-z0-9\-_\.+=/]+',
        r'(refresh_token=)[A-Za-z0-9\-_\.+=/]+',
        r'(eyJ[A-Za-z0-9\-_\.+=/]{10,})',  # JWT completo
    ]
```

---

## Seção 2: Ferramentas já Disponíveis

### 2.1 Ferramentas de Observabilidade

| Ferramenta | Status | Observação |
|------------|--------|------------|
| **systemd/journalctl** | ATIVO | Logs centralizados via journal natively |
| **PM2** | EM COEXISTÊNCIA | Legacy, em migração para systemd |
| **Loki** | NAO INSTALADO | Não encontrado na VPS |
| **Elasticsearch** | NAO INSTALADO | Não encontrado |
| **Promtail** | NAO INSTALADO | Não encontrado |
| **Filebeat** | NAO INSTALADO | Não encontrado |
| **Grafana** | NAO INSTALADO | Não encontrado |

### 2.2 Migração PM2 → systemd (Concluída)

**Documentação:** `docs/MIGRATION_PM2_TO_SYSTEMD.md`
**Data da migração:** 2026-06-20
**Status:** Coexistência (ambos rodando, systemd é preferencial)

O documento de migração já menciona:
> "Logs centralizados via journalctl" como ganho
> "Pronto pra Loki/Elasticsearch no futuro"

---

## Seção 3: Estimativa de Volume Diário

### 3.1 Base de Cálculo

| Métrica | Valor | Fonte |
|---------|-------|-------|
| Servicos ativos | 5 | fralib-api, worker, franz, wpp-listener, hermes |
| LOG_LEVEL padrão | INFO | config.py |
| Tamanho médio linha log | ~200 bytes | Estimativa |
| Logs por segundo (pico) | ~10 | Estimativa baseada em atividade |
| Logs por dia (estimativa) | 50.000 - 200.000 | Varia com uso de pipeline |

### 3.2 Volume Estimado

| Cenário | Logs/Dia | Tamanho/Dia (compressão) |
|---------|----------|---------------------------|
| Tranquilo (sem pipeline) | ~50.000 | ~10 MB (gzip) |
| Normal (5 pipelines/hora) | ~100.000 | ~20 MB (gzip) |
| Pico (20 pipelines/hora) | ~200.000 | ~40 MB (gzip) |
| **Mensal (estimado)** | ~3-5 milhões | **~600 MB - 1.2 GB/mês** |

### 3.3 Retention Atual

| Local | Retention | Método |
|-------|-----------|--------|
| journalctl | Default do systemd (~7 dias) | journalctl --vacuum-time |
| PM2 logs | Sem rotação automática | Manual ou logrotate |
| logs/fralib.log | Nenhum (crescimento infinito) | Necessário configurar |

---

## Seção 4: Top 10 Logs Críticos

### 4.1 Categorias de Logs Críticos

| # | Categoria | Log Source | Criticidade | PII? |
|---|-----------|------------|-------------|-------|
| 1 | **Auth/Erros de Login** | `auth_endpoints.py` | CRITICAL | Email, IP |
| 2 | **Pagamentos/Falhas MP** | `mercadopago_*` | CRITICAL | Dados financeiros |
| 3 | **Pipeline/Erros de Build** | `worker.py`, `pipeline_*` | HIGH | Lead ID, tenant |
| 4 | **LLM/Erros de AI** | `llm_router.py`, `provider_alerts` | HIGH | Tokens, custos |
| 5 | **WhatsApp/Mensagens** | `whatsapp_listener.py` | HIGH | Telefone, mensagem |
| 6 | **Hercules/Alertas** | `alerting.py` | HIGH | Métricas internas |
| 7 | **Jobs/Queue Fails** | `job_queue` | MEDIUM | Job ID, tenant |
| 8 | **SDR/Mensagens Enviadas** | `sdr_langgraph/*` | MEDIUM | Lead data |
| 9 | **Health Checks** | `site_health_check.py` | LOW | URLs |
| 10 | **Rate Limits** | `rate_limiter.py` | LOW | IP |

### 4.2 Padrões de Log Identificados

**Formato worker:**
```
%(asctime)s [worker] %(levelname)s %(message)s
```

**Formato WhatsApp:**
```
[WPP-Listener] %(message)s
```

**Log de API (uvicorn):**
```
IP - - "METHOD /path HTTP/1.1" STATUS - -
```

---

## Seção 5: Arquitetura Proposta

### 5.1 Opção A: Promtail + Loki + Grafana (RECOMENDADO)

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS 187.77.37.72                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ fralib-api   │    │ fralib-worker│    │ systemd       │  │
│  │ (journal)    │    │ (journal)    │    │ journal       │  │
│  └──────┬───────┘    └──────┬───────┘    └───────┬───────┘  │
│         │                   │                     │         │
│         └───────────────────┼─────────────────────┘         │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │   Promtail      │                      │
│                    │ (journald)      │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │     Loki        │                      │
│                    │ (local/docker) │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │    Grafana      │                      │
│                    │ (dashboards)   │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

**Vantagens:**
- Integração nativa com journald
- Baixo consumo de recursos
- Formato similar ao que já está em uso
- Gratuito e open-source
- Dashboards pré-configurados

### 5.2 Opção B: journald + Fluentd + Elasticsearch

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS 187.77.37.72                     │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │ systemd      │    │ journald     │                      │
│  │ services     │───►│              │                      │
│  └──────────────┘    └──────┬───────┘                      │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │   Fluentd       │                      │
│                    │ (parsing, filter)                      │
│                    └────────┬────────┘                      │
└─────────────────────────────┼───────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Elasticsearch     │
                    │  (Cloud/Remote)    │
                    └────────────────────┘
```

**Vantagens:**
- Elasticsearch mais maduro para busca
- Kibana para visualização
- Cloud providers oferecem managed Elasticsearch

**Desvantagens:**
- Custo de Elasticsearch cloud
- Fluentd mais complexo de configurar

### 5.3 Opção C: Promtail + Grafana Cloud (Cloud-hosted)

```
┌───────────────────────────────────────┐
│           VPS (Producer)              │
│  ┌─────────┐    ┌─────────────────┐  │
│  │journald │───►│ Promtail        │  │
│  └─────────┘    │ (scrapes local) │  │
│                 └────────┬────────┘  │
└──────────────────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │ Grafana     │
                    │ Cloud Loki  │
                    │ (managed)   │
                    └─────────────┘
```

**Vantagens:**
- Sem necessidade de servidor para storage
- Escalabilidade automática
- Managed service

**Desvantagens:**
- Custo mensal (~$20-50/mês para 5GB)
- Dados na nuvem (LGPD considerations)

---

## Seção 6: Esforço Estimado por Abordagem

### 6.1 Opção A: Promtail + Loki + Grafana (Self-hosted)

| Tarefa | Tempo | Complexidade | Dependência |
|--------|-------|-------------|-------------|
| Instalar Promtail | 30 min | Baixa | Repositório Grafana |
| Configurar Promtail (journald) | 1 hora | Média | Entender journald |
| Instalar Loki (binário ou Docker) | 30 min | Baixa | - |
| Configurar Loki retention | 30 min | Média | Configuração YAML |
| Instalar Grafana | 30 min | Baixa | - |
| Configurar Datasource | 15 min | Baixa | - |
| Criar dashboards básicos | 2 horas | Média | Conhecimento Grafana |
| Pipeline JSON logs para Loki | 2 horas | Alta | Parser JSON |
| Testes de carga | 1 hora | Média | - |
| **TOTAL** | **~8 horas** | - | - |

### 6.2 Opção B: Journald direto para Loki

| Tarefa | Tempo | Complexidade |
|--------|-------|--------------|
| Configurar journald remote logging | 1 hora | Média |
| Setup Loki como receiver | 30 min | Baixa |
| Dashboard Prometheus/Grafana | 2 horas | Média |
| **TOTAL** | **~4 horas** | - |

### 6.3 Opção C: Grafana Cloud (Managed)

| Tarefa | Tempo | Complexidade |
|--------|-------|--------------|
| Criar conta Grafana Cloud | 15 min | Baixa |
| Instalar Grafana Agent | 30 min | Baixa |
| Configurar logs pipeline | 1 hora | Média |
| Criar dashboards | 2 horas | Média |
| **TOTAL** | **~4 horas** | - |

---

## Seção 7: Riscos LGPD

### 7.1 Dados Pessoais Potenciais em Logs

| Tipo de Dado | Presente nos Logs? | Mascaramento Atual |
|--------------|-------------------|-------------------|
| Email de usuário | SIM | NÃO mascarado |
| Telefone/WhatsApp | SIM | NÃO mascarado |
| Endereço IP | SIM | NÃO mascarado |
| Nome de lead | SIM | NÃO mascarado |
| Dados de pagamento | PARCIAL | Parcialmente mascarado |
| JWT Tokens | SIM | JÁ MASCARADO (TokenMaskFilter) |
| Senhas | NÃO | N/A |

### 7.2 Requisitos LGPD Identificados

**Base Legal Necessária:**
- Execução de contrato (logs operacionais)
- Legítimo interesse (segurança)
- Obrigação legal (auditoria)

**Ações Requeridas:**

| # | Ação | Prioridade | Esforço |
|---|------|-----------|---------|
| 1 | Anonimizar IPs em logs | ALTA | 1 dia |
| 2 | Mascarar telefones em logs | ALTA | 1 dia |
| 3 | Mascarar emails (parcialmente) | MÉDIA | 4 horas |
| 4 | Implementar retention policy | ALTA | 2 horas |
| 5 | Documentar propósito dos logs | MÉDIA | 2 horas |
| 6 | Adicionar consentimento no Terms | BAIXA | 1 hora |

### 7.3 Recomendações LGPD

1. **Minimização:** Apenas logar dados estritamente necessários
2. **Retention:** Definir política de retenção (sugestão: 30 dias para logs operacionais, 1 ano para logs de segurança)
3. **Acesso:** Restringir acesso aos logs a pessoal autorizado
4. **Criptografia:** Logs em repouso devem estar criptografados
5. **Anonimização:** Para analytics, usar dados agregados/anônimos

---

## Seção 8: Custo de Storage Estimado

### 8.1 Opção Self-hosted (Loki em VPS)

| Recurso | Tamanho | Custo Mensal |
|---------|---------|--------------|
| Storage para 30 dias | ~30 GB (compressão) | - (já incluso VPS) |
| Storage para 90 dias | ~90 GB | ~$5/mês (upgrade VPS ou volume) |
| Backup | ~50% overhead | ~$3/mês |

**Custo Total Self-hosted:** $0 - $10/mês (apenas se precisar expandir storage)

### 8.2 Opção Cloud (Grafana Cloud)

| Plano | Armazenamento | Custo Mensal |
|-------|--------------|--------------|
| Free Tier | 50GB/mês | $0 |
| Pro | 100GB | $20 |
| Advanced | 500GB | $50 |

### 8.3 Comparativo

| Critério | Self-hosted | Grafana Cloud |
|----------|-------------|---------------|
| Custo mensal | $0-10 | $0-50 |
| Manutenção | Alta | Baixa |
| Escalabilidade | Limitada | Alta |
| Backup | Manual | Automático |
| LGPD Compliance | Você controla | Verificar provider |

---

## Resumo Executivo

### Viabilidade: **ALTA**

O FraLib já está preparado para logs centralizados através da migração para systemd. A infraestrutura básica (journald) está em vigor. As principais vantagens são:

1. **Pronto para Loki:** Os arquivos .service já enviam logs para journald
2. **Promtail é leve:** Pode rodar na mesma VPS com impacto mínimo
3. **Custo-benefício:** Self-hosted é viável com ~$0 adicional
4. **LGPD:** Requer trabalho de mascaramento, mas é gerenciável

### Próximos Passos Recomendados

1. **Imediato (1 dia):** Configurar Promtail para scrapear journald
2. **Curto prazo (1 semana):** Instalar Loki + Grafana localmente
3. **Médio prazo (2 semanas):** Implementar mascaramento LGPD
4. **Longo prazo (1 mês):** Criar dashboards de alerting

### Alternativa Rápida (Se Precisar de Logs Agora)

Usar Grafana Cloud Free tier:
- 50GB/mês de logs
- Enough para 30 dias com compressão
- Zero setup infrastructure
- Começar em 15 minutos

---

## Referências

- `docs/MIGRATION_PM2_TO_SYSTEMD.md` - Documentação da migração
- `backend/core/config.py` - Configuração de logging
- `server.py` - TokenMaskFilter implementado
- `worker.py` - Worker logging
- `docs/POLITICA_PRIVACIDADE_LGPD_FRALIB.md` - Política LGPD
