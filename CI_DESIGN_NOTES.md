# CI/CD Design Notes

Plataforma: GitHub Actions (`.github/workflows/system-validation.yml`).

Decisao: pipeline linear e sequencial, sem paralelismo entre suites. A ordem real no workflow `system-validation.yml` e: validate_secrets -> sast_and_secretscan -> tests_unit -> contracts_api (OpenAPI + Jest contracts + Playwright smoke) -> tests_integration -> tests_e2e -> tests_load -> build_executable (PyInstaller) -> build_installer -> test_installer -> publish_artifacts. O build ocorre somente apos todas as suites passarem e usa o launcher oficial `launcher_gui.py`.

Estagios:
1) validate_secrets (pulavel em forks)  
2) sast_and_secretscan (bandit, trivy, eslint)  
3) tests_unit (pytest unit + lint/test JS)  
4) contracts_api (pytest contratos, OpenAPI TS gen + tsc, Jest contrato, Playwright contratos)  
5) tests_integration (pytest integration)  
6) tests_e2e (Playwright, com trace e reporter junit)  
7) tests_load (pytest tests/performance)  
8) build_executable (PyInstaller em Windows)  
9) build_installer (gera installer com exe)  
10) test_installer (smoke do installer)  
11) publish_artifacts (expoe exe/installer e artefatos)

Fail-fast: cada job depende do anterior via `needs`, entao se um falha, os seguintes nao rodam. Artefatos de logs/junit/traces sao sempre publicados com `if: always()`.

Entradas/segredos:
- `OPENAI_API_KEY`, `CREDENTIALS_SECRET_KEY`, `RUNTIME_CREDENTIALS_KEY` devem vir de secrets. Defaults seguros (fakes) foram colocados no env para nao quebrar pipelines de PR, mas use secrets reais no repo.

Comandos chave:
- Unit: `pytest tests/unit --junitxml=...`
- Integration: `pytest tests/integration --junitxml=...`
- E2E: `npx playwright test --trace on --reporter=junit`
- Load: `pytest tests/performance --junitxml=...`
- Build: `pyinstaller launcher_gui.py --name TranscribeFlow --onefile --paths src`

Artefatos:
- `unit-artifacts`, `integration-artifacts`, `e2e-artifacts` (inclui traces em `playwright-report`/`test-results`), `load-artifacts`, `transcribeflow-exe`.

Execucao local equivalente:
- Unit: `pytest tests/unit -q && npm run lint:js && npm run test:js`
- Integration: `pytest tests/integration -q`
- E2E: `PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install && npm run test:e2e`
- Load: `pytest tests/performance -q`
- Build: `pip install pyinstaller && pyinstaller launcher_gui.py --name TranscribeFlow --onefile --paths src`
