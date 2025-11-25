# Pull request checklist

- [ ] Descrevi brevemente a motivação e o escopo do PR.
- [ ] Executei `npm run lint:js` e `npm run test:js` quando modifiquei JS/TS.
- [ ] Rodei `pytest` nos módulos afetados (veja `tests/performance`/`tests/integration`).
- [ ] Para mudanças em pipeline/telemetria/performance, executei `python scripts/plot_metrics_histograms.py --event pipeline.stage.latency --stage asr --preview` e anexei o resumo (ou compartilhei o gráfico) seguindo `docs/metrics_playbook.md`.
