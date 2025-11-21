# CI/CD Design Notes

Plataforma: GitHub Actions (`.github/workflows/system-validation.yml`).

Decisao: adaptar a pipeline existente substituindo-a por um fluxo linear que impone a ordem rigidamente: unit -> integration -> e2e -> load -> build. A antiga rodava algumas suites em paralelo (JS/Python, load antes de e2e) e fazia build a partir de `run_job.py`. Agora o build so ocorre apos todos os testes passarem e usa o launcher oficial `launcher_gui.py`.

Estagios:
1) tests_unit (pytest unit + lint/test JS)  
2) tests_integration (pytest integration)  
3) tests_e2e (Playwright, com trace e reporter junit)  
4) tests_load (pytest tests/performance)  
5) build_executable (PyInstaller em Windows, depende de todos os testes)

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
