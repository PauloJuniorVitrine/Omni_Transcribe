# TranscribeFlow / Omni Transcribe

Pipeline completo para transcrição (ASR), pós-edição e entrega, com FastAPI + frontend estático e empacotamento para Windows.

## Requisitos
- Python 3.11
- Node 20
- (Opcional) ffmpeg/pydub para chunking local; NSIS (Windows) para gerar instalador

## Setup rápido
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm ci
```

## Testes e qualidade
- Lint Python: `ruff check src tests`
- Backend (unit + integration + cobertura 80%): `pytest --maxfail=1 --cov=src --cov-report=xml --cov-fail-under=80`
- Frontend (unit): `npm run test:js -- --runInBand --ci`
- Lint JS: `npm run lint:js`
- E2E (Playwright): `npm run test:e2e` (instale browsers: `npx playwright install --with-deps`)
- Carga (k6): `k6 run tests/performance/load_smoke.js` (usa `/health`)

## Build Windows
- EXE: `scripts/build_executable_windows.ps1` (PyInstaller gera `dist/TranscribeFlow.exe`)
- Instalador (NSIS): `makensis installers/windows/transcribeflow.nsi` → `dist/TranscribeFlow-Setup.exe`

## CI/CD (GitHub Actions)
Workflow em `.github/workflows/ci-cd.yml`:
1. backend: ruff + pytest (cobertura 80%)
2. frontend: lint + jest
3. e2e: Playwright
4. load: k6 smoke
5. build-windows: PyInstaller + NSIS (só roda após todos os testes)

Tags `v*` também disparam o pipeline (ideal para releases).

## Configuração / segredos
Principais variáveis (definir em ambiente/Actions secrets):
- `OPENAI_API_KEY` (ou `CHATGPT_API_KEY`)
- `CREDENTIALS_SECRET_KEY` (cofre runtime, se usar)
- `APP_ENV`, diretórios `BASE_*`, limites (`MAX_AUDIO_SIZE_MB`, `OPENAI_CHUNK_*`)
- Webhooks/integrações opcionais: `ALERT_WEBHOOK_URL`, `METRICS_WEBHOOK_URL`, `GOTRANSCRIPT_API_KEY`, `S3_*`, OAuth (`OAUTH_*`)
- Em produção não habilite `TEST_MODE` nem `SKIP_RUNTIME_CREDENTIALS_VERIFY`. Rotacione chaves expostas e mantenha `.env` fora do git.

## Estrutura principal
- `src/` domínio, aplicação, infraestrutura, interfaces (CLI/HTTP/Web)
- `tests/` unit, integration, e2e, performance
- `scripts/` utilitários, build EXE
- `installers/windows/` script NSIS
- `.github/workflows/` pipelines
