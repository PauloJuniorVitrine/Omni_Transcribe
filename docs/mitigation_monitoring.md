# Mitigações e Acompanhamento

Para transformar o item 7 em práticas concretas, este guia descreve como registrar responsáveís, checkpoints, validações de alertas e a lógica de monitoramento contínuo alinhada a CoCoT/ToT/ReAct.

## 1. Responsabilidades e tempo

| Componente | Responsável sugerido | Frequência | Checkpoint | Notas CoCoT |
| --- | --- | --- | --- | --- |
| Documentação central (`docs/architecture_overview.md`, `docs/visualizations.md`, `docs/metrics_playbook.md`) | Time de engenharia + DevOps | Após cada alteração na pipeline/interfaces | Atualizar diagramas/descrições + checklist | Garantir visão plena antes de PR |
| Histograma de latência (`logs/metrics_histograms.json`) | Engenharia de backend | Diário (pre-release) | Rodar `scripts/plot_metrics_histograms.py` + anexar ao PR | ToT: comparar múltiplos buckets/estágios |
| Alertas `accuracy.guard.alert` | Equipe de UX/QA + SRE | Sempre que trabalho novo em accuracy | Validar false positives via flag `accuracy.guard` e alert_dispatcher | ReAct: simular alertas com dados falsos antes de ativar |
| Uploads API `POST /api/uploads` | Time de integrações/segurança | Antes de abrir endpoints públicos | Gerar token com `GET /api/uploads/token` e consumir via script | Documentar TTL/assinatura e retomar se necessário |

## 2. Validação de alertas falsos

- Use `feature_flags.json`/variáveis (`ALERT_WEBHOOK_URL`, `METRICS_WEBHOOK_URL`) para segmentar ligações.  
- Quando um novo alerta `accuracy.guard.alert` surge, consulte `logs/alerts.log` para confirmar score + WER; registre qualquer falso positivo na planilha de revisão e ajuste `accuracy_threshold` ou `reference_transcript` conforme necessário.  
- Para evitar alertas repetidos, crie uma rotina semanal (no monitoramento ou via script) que conte alertas por job_id e recomende limitação via feature flag se exceder 3 ocorrências no mesmo dia.

## 3. Acompanhamento de métricas

- Execute `python scripts/plot_metrics_histograms.py --event pipeline.stage.latency --stage asr --success true --preview` antes de releases; capture o gráfico para facilitar a revisão.  
- Compare `pipeline.stage.latency` com `pipeline.retry.triggered` e `logs/alerts.log` para detectar regressões; se bucket `>=200`ms estiver em alta, marque na planilha de mitigação e dispare análise post-mortem.  
- Documente resultados no ticket/PR (incluindo prints do script) e relate no checklist PR para garantir responsabilidade.

## 4. Checklist de monitoramento (revisão contínua)

1. Verifique se os diagramas estão atualizados (docs/architecture, docs/visualizations).  
2. Confirme que o histograma foi gerado e analisado (`scripts/plot_metrics_histograms.py …`).  
3. Execute `pytest` nos módulos afetados e valide os alertas registrados em `logs/alerts.log`.  
4. Use o template `.github/pull_request_template.md` como gatekeeper: quem revisar deve confirmar que a seção está preenchida.  

Referencie este playbook sempre que o pipeline for modificado para manter o ciclo CoCoT/ToT/ReAct ativo.
