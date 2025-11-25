# Playbook de Métricas e Visualizações

Este guia complementa `docs/architecture_overview.md` e `docs/visualizations.md` e descreve como transformar os histogramas gerados em `logs/metrics_histograms.json` em insights acionáveis antes de cada release (CoCoT + ToT + ReAct).

## 1. O que o histograma contém

- `pipeline.stage.latency`: buckets (50ms) para cada etapa do pipeline (`asr`, `post_edit`, `artifacts`), com tag `success` para separar erros de sucessos.
- `pipeline.asr.chunk_count`: bucket unitário (`bucket_size=1`) anotando quantos chunks o ASR consumiu (tags `chunked=true/false`).
- Cada chave é `event|bucket_size=x|tag1=v1,tag2=v2` e os valores são dicionários bucket→contagem.

## 2. Exemplo de uso

Crie o script `scripts/plot_metrics_histograms.py` (descrito abaixo) e rode antes de releases/cargas críticas:

```bash
python scripts/plot_metrics_histograms.py --file logs/metrics_histograms.json --event pipeline.stage.latency --stage asr --preview
```

Ele:

1. Deserializa o JSON e seleciona buckets do evento (`--event` ou `pipeline.asr.chunk_count`).
2. Calcula p50/p95/p99 a partir das contagens agregadas.
3. (Opcional) Plota o histograma usando `matplotlib` se disponível; caso contrário, gera tabela textual.

Use o `--stage` + `--success` para comparar ocorrências com erros e detectar regressões (ToT: múltiplas perspectivas; ReAct: simular cenários antes de alertar). Atualize o `.github/pull_request_template.md` quando novos eventos ou buckets exigirem entradas adicionais; o template já lembra de anexar o resumo desse script ao PR. Use o script `scripts/monitor_metrics_dashboard.py` para gerar um painel textual rápido (p95 e alertas) e anexar um screenshot/descrição no PR junto do gráfico de `plot_metrics_histograms.py`.

## 3. Interpretação e alertas

- Trend detection: monitorar se p95 sobe acima de `pipeline.stage.latency` bucket 200ms para usuários simultâneos; se sim, correlacione com `logs/alerts.log`.
- Accuracy guard: cada `accuracy.guard.alert` já inclui score e WER no log (ver `TranscriptionAccuracyGuard`), então crie um painel que combina o evento `pipeline.retry.triggered` com os alerts para antecipar retrabalhos.

## 4. Divulgação

Incorpore esse playbook na validação de histórias críticas: execute o script, cheque os buckets relevantes, capture o gráfico e anexe ao pull request. Se o histograma evidenciar outliers, acione `notify_alert` (já disparado no pipeline) e registre no changelog visual.
