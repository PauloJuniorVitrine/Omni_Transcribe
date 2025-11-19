# Plano de Integrações Externas — EXEC_ID 20251113T103533Z_MSJTU6

Aplicando **CoCoT** (comprovação por requisitos do prompt, causalidade via dependências reais, contexto TranscribeFlow, tendência com práticas modernas) e **ToT** (analisando alternativas antes da decisão), estruturamos o roadmap das integrações pendentes. Cada iniciativa segue as fases **Preparação → Implementação → Validação**, inclui riscos, métricas e checkpoints de rollback.

---

## 1. GoTranscript / Cliente (Upload + Tracking)

### Contexto
- Situação atual: geração do pacote ZIP já ocorre localmente, mas não existe integração que faça upload automático nem registro de protocolo.
- Impacto: requisito FUNC-007 permanece parcialmente manual; falta registro auditável do status de entrega.

### Análise ToT
| Alternativa | Prós | Contras | Decisão |
|-------------|------|---------|---------|
| A) Manter upload manual guiado apenas por instruções | Zero esforço técnico imediato | Sem rastreabilidade, alto risco operacional | ❌ |
| B) Script HTTP direto contra portal GoTranscript (se API disponível) | Automação completa | Exige autenticação segura e manuseio de credenciais | ✅ |
| C) Automação via navegador headless | Contorna ausência de API | Instável e frágil para CI/CD | ❌ |

### Plano Sequencial
1. **Preparação**
   - Mapear contratos da API GoTranscript (ou especificação fornecida pelo cliente); armazenar credenciais em `.env` (`GOTRANSCRIPT_API_KEY`, `GOTRANSCRIPT_BASE_URL`).
   - Definir modelo `DeliveryRecord` em `domain/entities` e repositório correspondente para rastrear uploads, status e códigos de retorno.
   - Criar feature flag `GOTRANSCRIPT_ENABLED` para ativar/desativar integração sem retrabalho.
2. **Implementação**
   - Adicionar `GotranscriptClient` em `src/infrastructure/api/` com métodos `submit_package()` e `fetch_status()`, usando retry/backoff compartilhado.
   - Estender `RegisterDelivery` use case para acionar o client após geração do ZIP e registrar resultado no log CSV/Sheets.
   - Propagar tracing (trace_id do webhook) aos uploads para correlação.
3. **Validação**
   - Criar testes de integração simulando a API (responses gravadas em `tests/integration/mocks/gotranscript`).
   - Adicionar monitor de SLA: `delivery_success_rate`, `avg_delivery_latency_ms`, `fallback_count`.
   - Planejar rollback automático: se 3 falhas consecutivas ocorrerem, desabilitar flag e mover pacote para `rejected/` com justificativa.

### Cronograma e Indicadores
- **Semana 1**: descoberta + ajustes de domínio.
- **Semana 2**: client + caso de uso.
- **Semana 3**: testes + hardening (metas: sucesso ≥ 99%, latência média < 2s).
- **Riscos**: variação de contrato, limites de API, expiração de credenciais.

---

## 2. Storage S3 / Backup e Google Sheets

### Contexto
- CSV local já cumpre registro mínimo, porém precisamos backup externo (S3/MinIO) e sincronização com planilha corporativa (Sheets) conforme requisito FUNC-008.

### Análise ToT
| Alternativa | Prós | Contras | Decisão |
|-------------|------|---------|---------|
| A) Permanecer apenas com CSV | Simplicidade | Não atende regra de redundância / reporting | ❌ |
| B) Implementar cliente S3 e Sheets em paralelo | Responde todos requisitos de uma vez | Maior esforço simultâneo, porém dependências semelhantes | ✅ |
| C) Usar apenas Sheets (sem S3) | Atende reporting | Falta redundância/backup | ❌ |

### Plano Sequencial
1. **Preparação**
   - Definir variáveis `.env` (`S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `GOOGLE_SERVICE_ACCOUNT_JSON`).
   - Criar abstrações em `domain/ports/services.py` para `BackupStoragePort` e `SheetPort`.
2. **Implementação**
   - Cliente S3 (`src/infrastructure/api/storage_client.py`) com upload multipart e soma SHA-256 para auditoria; backups enviados após pacote aprovado.
   - Cliente Sheets (`src/infrastructure/api/sheets_client.py`) usando service account; sincronizar `log.csv` em lote (batch update) com tags de status.
   - Atualizar `sheet_service` para aceitar implementação dual (CSV local + Sheets) usando Strategy/feature flag.
3. **Validação**
   - Testes integration/in-memory: usar `moto` ou `minio` local para S3 e mocks Google (gspread) com fixtures reais.
   - Métricas: `backup_success_rate`, `sheet_sync_latency_ms`, `pending_rows`.
   - Alertas: se `backup_success_rate < 95%` em 24h, disparar log para futuro canal Slack/Email.

### Cronograma e Indicadores
- **Semana 1**: ports + clientes básicos.
- **Semana 2**: integração nos casos de uso + testes.
- **Semana 3**: observabilidade, retries e documentação operacional.
- **Riscos**: limites de API do Google, custos de armazenamento, latência de rede. Mitigação via retries + batch.

---

## 3. Observabilidade & Segurança Cruzada

| Elemento | Ação | Métrica alvo |
|----------|------|--------------|
| Webhooks | Persistir `snapshot_metrics()` em `logs/observability.json` a cada chamada; expor endpoint interno `/metrics/webhooks` | Gap < 5% entre métricas locais e logs |
| Segredos | Rotacionar arquivo `webhook_integrations.json` via script em `scripts/rotate_webhook_secret.py` (hash com timestamp) | Nenhum segredo com idade > 90 dias |
| Rollback | Registrar em `/docs/rollback_integrations_{EXEC_ID}.md` qualquer desativação automática | SLA rollback < 5 min |

---

## 4. Backlog Priorizado (Criticidade)

| ID | Integração | Criticidade | Justificativa CoCoT | Status |
|----|------------|-------------|---------------------|--------|
| IMP-INT-01 | GoTranscript Upload API | Alta | Único caminho para automatizar entrega (RULE-005) | 🔲 Pendente |
| IMP-INT-02 | Backup S3 | Alta | Exigência de redundância e compliance | 🔲 Pendente |
| IMP-INT-03 | Google Sheets Sync | Média/Alta | Transparência operacional + reports executivos | 🔲 Pendente |
| IMP-INT-04 | Observabilidade Webhooks | Média | Necessário para auditorias e métricas definidas | 🔲 Pendente |

---

### Referências Operacionais
- `src/infrastructure/container/components_delivery.py` — ponto de injeção para services futuros.
- `docs/integration_map_20251113T103533Z_MSJTU6.md` — mapa atual de integrações (mantido em sincronia com este plano).
- `CHANGE_SUMMARY.md` & `REVIEW_LOG.md` — registrar cada avanço seguindo governança estabelecida.

> Próxima ação recomendada: iniciar IMP-INT-01 (GoTranscript) criando portas e variáveis de ambiente, antes de evoluir para S3/Sheets, garantindo que a cadeia de entrega esteja automatizada fim a fim.
