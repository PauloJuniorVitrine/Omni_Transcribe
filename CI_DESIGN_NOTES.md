# CI/CD Design Notes

Plataforma: GitHub Actions (`.github/workflows/ci-cd.yml`).

Decisão: pipeline sequencial — cada job depende do anterior via `needs`, garantindo que falhas barram os próximos estágios. A ordem atual é:
1. backend: `ruff check` + `pytest --maxfail=1 --cov=src` (cachê de `pip`).
2. frontend: `npm run lint:js`, `npm run test:js`, `npm run typecheck:contracts` (gera OpenAPI + tipagens TS); usa cache pip/npm.
3. e2e: `npm run test:e2e` contra o stub server (`scripts/stub_server.py`).
4. load: `k6 run tests/performance/load_smoke.js` contra o stub exposto em localhost.
5. build-windows: `pyinstaller launcher_gui.py` + NSIS instalador (usa o script oficial `launcher_gui.py`).

Cada job publica os artefatos relevantes (`artifacts/**`, `test-results`, cobertura JS) com `if: always()`.

Entradas/segredos:
- `OPENAI_API_KEY`, `CHATGPT_API_KEY`, `CREDENTIALS_SECRET_KEY`, `RUNTIME_CREDENTIALS_KEY` via secrets. Defaults programados nos workflows evitam quebra de PRs com testes locais.
- `DOWNLOAD_TOKEN_SECRET`/`WEBHOOK_SECRET` devem ser fortes em produção; o app falha no start se ambos forem fracos.

Comandos chave locais:
- Backend: `ruff check src tests && pytest --maxfail=1 --cov=src --cov-report=xml`.
- Frontend: `npm ci && npm run lint:js && npm run test:js && npm run typecheck:contracts`.
- E2E: `PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install --with-deps && npm run test:e2e`.
- Load: `k6 run tests/performance/load_smoke.js`.
- Build: `pip install pyinstaller && pyinstaller launcher_gui.py --name TranscribeFlow --onefile --paths src`.
