# Telemetria e Alertas – Plano de Implementação

## Objetivo
Registrar métricas reais (latência, success rate, retries) e disparar alertas externos conforme requerido pelo prompt Enterprise+.

## Etapas
1. **Instrumentação**  
   - Adicionar logging estruturado ao pipeline (ex.: `status_publisher`, `webhook_service`) com campos `trace_id`, `duration_ms`.  
   - Persistir métricas em arquivo (CSV/JSON) ou enviar para backend APM (Sentry, Datadog, etc.).

2. **Geração de relatórios**  
   - `scripts/generate_integration_metrics.py` lê `logs/metrics.log` e gera `docs/integration_metrics_{EXEC_ID}.md` + `observability_comparison_{EXEC_ID}.md`.  
   - Rota `/api/telemetry/metrics` expõe resumo dos eventos coletados. Enquanto não houver dados reais, os logs locais servem como insumo.

3. **Alertas externos**  
   - Integrar webhook (Slack/Teams) usando `requests` com payload JSON.  
   - Condomínio: `application/services/status_publisher` pode enviar aviso quando `LogLevel.ERROR` exceder limite.

4. **CI/CD**  
   - Adicionar stage que roda o novo script e falha se não houver dados recentes (< 7 dias).  
   - Publicar os arquivos em `docs/…` com o mesmo `EXEC_ID`.

## Status
- Instrumentação parcial (resumo/incidentes em memória).  
- Relatórios e alertas dependem de dados reais → pendente até termos ambiente de observabilidade.  
- Este plano atende ao item do checklist até que a coleta real seja possível.
