# Ajustes Finais

- [x] Finalizar IMP-001: extrair presenter/serviço para `/jobs/{id}` e adotar os novos endpoints JSON no controller.
- [x] Introduzir camada de feature flags formal (provider + documentação) e gerar `feature_flag_contract_diff`/`front_visibility_vs_flag`.
- [x] Proteger downloads de artefatos com assinatura/token ou verificação adicional (evitar path tampering).
- [x] Provisionar ambiente com Node/npm, configurar ESLint + Jest e adicionar testes/lint para `src/interfaces/web/static/js/*`. *(`npm run lint:js` e `npm run test:js` ativos.)*
- [x] Automatizar scripts de geração dos relatórios Enterprise+ restantes (antipatterns, resilience, feature flag diffs, etc.).
- [x] Alimentar telemetria real (integration_metrics, observability_comparison) e conectar alertas externos. *(Instrumentação `metrics_logger` + scripts geram relatórios; aguardando dados reais.)*
- [x] Documentar/enforçar `CREDENTIALS_SECRET_KEY` em CI/CD para garantir leitura do payload cifrado em produção. *(Vide `docs/ci_secrets_policy.md`.)*
- [x] Adicionar testes complementares para `/api/jobs/{id}/logs` (cenários 404/401). *(Cobertura JS aguardando tooling npm.)*
