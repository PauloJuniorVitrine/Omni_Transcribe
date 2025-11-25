# TranscribeFlow / Omni Transcribe

Pipeline completo para transcrição (ASR), pós-edição e entrega, com FastAPI + frontend estático e empacotamento para Windows.

## Requisitos
- Python 3.11
- Node 20
- (Opcional) ffmpeg/pydub para chunking local; NSIS (Windows) para gerar instalador

## Setup rápido
1. Garanta Python 3.11 e Node 20 instalados.
2. Crie o ambiente virtual: `py -m venv .venv`.
3. Ative o venv:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
4. Instale dependências Python/JS:
   ```bash
   pip install -r requirements.txt
   npm ci
   ```
5. Use `scripts/run_transcribeflow.ps1` (ou `scripts/run_transcribeflow.bat` em batch) para iniciar localmente com a stack completa.  
   O watcher (`scripts/watch_inbox.py` ou `src/interfaces/cli/watch_inbox.py`) popula automaticamente a `inbox/`.

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
Workflow em `.github/workflows/ci-cd.yml` (ordem obrigatória):
1. backend: ruff + pytest (com cobertura mínima) usando cache de `pip`.
2. frontend: eslint + jest + `npm run typecheck:contracts` (geração OpenAPI + TS) usando cache `pip`/`npm`.
3. e2e: Playwright + stub server.
4. load: k6 smoke contra stub (`tests/performance/load_smoke.js`).
5. build-windows: PyInstaller + NSIS (só roda após os testes).

Cada job publica artefatos relevantes (`artifacts/**`, `test-results`). Tags `v*` também disparam esta mesma pipeline completa.

## Configuração / segredos
Principais variáveis (definir em ambiente/Actions secrets):
- `OPENAI_API_KEY` (ou `CHATGPT_API_KEY`)
- `CREDENTIALS_SECRET_KEY` (cofre runtime, se usar)
- `DOWNLOAD_TOKEN_SECRET` (opcional; se omitido usa `WEBHOOK_SECRET` para assinar links de download)
- `APP_ENV`, diretórios `BASE_*`, limites (`MAX_AUDIO_SIZE_MB`, `OPENAI_CHUNK_*`)
- ASR local: defina `ASR_ENGINE=local` e `LOCAL_WHISPER_MODEL_SIZE` (tiny, base, small, medium, large-v2, large-v3, turbo). `large-v3` = máxima precisão open-source; `turbo` = latência menor.
- ASR OpenAI: `OPENAI_WHISPER_MODEL` (ex.: gpt-4o-transcribe/gpt-4o-transcribe-diarize), `OPENAI_WHISPER_RESPONSE_FORMAT` (verbose_json/text/json/diarized_json), `OPENAI_WHISPER_CHUNKING_STRATEGY` (necessário para diarize).
- Webhooks/integrações opcionais: `ALERT_WEBHOOK_URL`, `METRICS_WEBHOOK_URL`, `GOTRANSCRIPT_API_KEY`, `S3_*`, OAuth (`OAUTH_*`)
- Em produção não habilite `TEST_MODE` nem `SKIP_RUNTIME_CREDENTIALS_VERIFY`. Rotacione chaves expostas e mantenha `.env` fora do git.
- Autenticação: fora de `TEST_MODE` é obrigatória sessão OAuth; sessões inexistentes/expiradas retornam 401 (downloads, upload, revisão, templates, etc.).

## Estrutura principal
- `src/` domínio, aplicação, infraestrutura, interfaces (CLI/HTTP/Web)
- `tests/` unit, integration, e2e, performance
- `scripts/` utilitários, build EXE
- `installers/windows/` script NSIS
- `.github/workflows/` pipelines
